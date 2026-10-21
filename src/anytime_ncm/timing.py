"""Diagnostic component timing and offline cost estimates; no online halting."""

import math
import time

from anytime_ncm.features import CausalFeatureTracker, PrefixObservation
from anytime_ncm.sudoku import validate_solution
from anytime_ncm.trajectories import LEVEL_LENGTHS

CUDA_COMPONENTS = ("prefix_assembly", "reconstruction", "decode_select")
HOST_COMPONENTS = ("transfer_ms", "text_ms", "verifier_ms", "policy_ms")


def finite_ms(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Timings must be finite, nonnegative milliseconds.")
    return float(value)


def host_region(operation):
    started = time.perf_counter_ns()
    result = operation()
    return result, finite_ms((time.perf_counter_ns() - started) / 1e6)


def cuda_region(operation):
    import torch
    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    torch.cuda.synchronize()
    started = time.perf_counter_ns()
    start.record()
    result = operation()
    end.record()
    end.synchronize()
    wall = (time.perf_counter_ns() - started) / 1e6
    return result, {"wall_ms": finite_ms(wall), "gpu_ms": finite_ms(start.elapsed_time(end))}


def reconstruct_at_depth(vq, codes, depth):
    """Cumulative full-resolution reconstruction reading only codes through depth."""
    import torch
    if type(depth) is not int or not 1 <= depth <= len(vq.levels):
        raise ValueError("Depth is outside the hierarchy.")
    with torch.no_grad():
        total = torch.zeros(codes.shape[0], vq.levels[-1], vq.embed_dim, device=codes.device, dtype=torch.float32)
        offset = 0
        for level, length in enumerate(vq.levels[:depth]):
            contribution = vq.embeddings[level](codes[:, offset:offset + length])
            if level != len(vq.levels) - 1:
                contribution = vq._up_to_full(contribution, level, vq.levels[-1])
            total.add_(vq._apply_quant_resi(contribution, level))
            offset += length
        return total


class GenerationObserver:
    """Non-mutating prehooks mark completed sampling before next-level embedding.

    No internal synchronization. The final marker follows original torch.cat.
    Generation feedback reconstruction belongs to the following stage.
    """

    def __init__(self, vq, *, event_factory=None, synchronize=None, clock=None):
        if event_factory is None:
            import torch
            event_factory = lambda: torch.cuda.Event(enable_timing=True)
            synchronize = torch.cuda.synchronize
        self.vq = vq
        self.events = [event_factory() for _ in range(len(vq.levels) + 1)]
        self.synchronize = synchronize
        self.clock = clock or time.perf_counter_ns
        self.next_marker = 0
        self.handles = []

    def mark(self, number):
        if number != self.next_marker:
            raise RuntimeError("Generation boundary order changed.")
        self.events[number].record()
        self.next_marker += 1

    def __enter__(self):
        self.synchronize()
        for level, embedding in enumerate(self.vq.embeddings[:-1], 1):
            def observe(module, args, number=level):
                self.mark(number)
                return None
            self.handles.append(embedding.register_forward_pre_hook(observe))
        self.started = self.clock()
        self.mark(0)
        return self

    def finish(self):
        self.mark(len(self.vq.levels))
        self.synchronize()
        wall = finite_ms((self.clock() - self.started) / 1e6)
        stages = [finite_ms(a.elapsed_time(b)) for a, b in zip(self.events[:-1], self.events[1:], strict=True)]
        return {"level_gpu_ms": stages, "wall_ms": wall,
                "host_residual_ms": max(0.0, wall - sum(stages))}

    def __exit__(self, *args):
        for handle in self.handles:
            handle.remove()


def verified_decision(valid):
    if type(valid) is not bool:
        raise ValueError("Verified decision accepts a current Boolean only.")
    return valid


def first_valid_exit(flags):
    if len(flags) != 12 or any(type(value) is not bool for value in flags):
        raise ValueError("Expected 12 Boolean validity flags.")
    return next((level for level, valid in enumerate(flags, 1) if valid), 12)


def estimate_costs(record, *, calibration=None):
    """All scheduled checks are charged, including all 12 on never-valid inputs."""
    calibration = calibration or {"cuda_region_wall_ms": 0.0, "marker_trace_wall_ms": 0.0, "host_region_ms": 0.0}
    cuda_allowance = finite_ms(calibration["cuda_region_wall_ms"])
    marker_allowance = finite_ms(calibration["marker_trace_wall_ms"]) / 12
    host_allowance = finite_ms(calibration["host_region_ms"])
    generation = record["generation"]
    if len(generation["level_gpu_ms"]) != 12 or len(record["levels"]) != 12:
        raise ValueError("Incomplete component profile.")
    stages = [max(0.0, finite_ms(value) - marker_allowance) for value in generation["level_gpu_ms"]]
    residual = finite_ms(generation["host_residual_ms"])
    prepare = max(0.0, finite_ms(record["input_prepare"]["wall_ms"]) - cuda_allowance)
    flags = [state["valid"] for state in record["levels"]]
    exit_level = first_valid_exit(flags)
    checks, final_output_cost = [], None
    for level, state in enumerate(record["levels"], 1):
        gpu = {name: max(0.0, finite_ms(state[name]["wall_ms"]) - cuda_allowance) for name in CUDA_COMPONENTS}
        cpu = {name: max(0.0, finite_ms(state[name]) - host_allowance) for name in HOST_COMPONENTS}
        finite_ms(state["features_ms"])  # measured, unused by verifier-only candidate
        output = gpu["reconstruction"] + gpu["decode_select"] + cpu["transfer_ms"] + cpu["text_ms"]
        check = output + cpu["verifier_ms"] + cpu["policy_ms"]
        if level < 12:
            check += gpu["prefix_assembly"]
        checks.append(check)
        final_output_cost = output
    baseline = prepare + residual + sum(stages) + final_output_cost
    candidate = prepare + residual + sum(stages[:exit_level]) + sum(checks[:exit_level])
    fixed = [prepare + residual + sum(stages[:k]) +
             sum(max(0.0, finite_ms(record["levels"][k - 1][name]["wall_ms"]) - cuda_allowance)
                 for name in ("reconstruction", "decode_select")) +
             sum(max(0.0, finite_ms(record["levels"][k - 1][name]) - host_allowance) for name in ("transfer_ms", "text_ms")) +
             (max(0.0, finite_ms(record["levels"][k - 1]["prefix_assembly"]["wall_ms"]) - cuda_allowance) if k < 12 else 0.0)
             for k in range(1, 13)]
    return {"baseline_ms": baseline, "candidate_ms": candidate, "fixed_ms": fixed,
            "exit_level": exit_level, "candidate_valid": any(flags), "baseline_valid": flags[-1],
            "skipped_levels": 12 - exit_level,
            "skipped_codes": sum(LEVEL_LENGTHS[exit_level:])}


def calibrate_instrumentation(repeats=100):
    import statistics
    import torch
    cuda, marker, host = [], [], []
    for _ in range(repeats):
        _, cost = cuda_region(lambda: None)
        cuda.append(cost["wall_ms"])
        _, cost = host_region(lambda: None)
        host.append(cost)
        events = [torch.cuda.Event(enable_timing=True) for _ in range(13)]
        torch.cuda.synchronize()
        started = time.perf_counter_ns()
        for event in events:
            event.record()
        events[-1].synchronize()
        marker.append((time.perf_counter_ns() - started) / 1e6)
    return {"repeats": repeats, "cuda_region_wall_ms": statistics.median(cuda),
            "marker_trace_wall_ms": statistics.median(marker), "host_region_ms": statistics.median(host),
            "raw_cuda_region_wall_ms": cuda, "raw_marker_trace_wall_ms": marker, "raw_host_region_ms": host,
            "scope": "empty timing regions and 13 CUDA-event markers; not a bound on all hook/launch perturbation"}


def profile_request(adapter, example, repeat):
    import torch
    with torch.no_grad():
        context, prepare = cuda_region(lambda: torch.tensor([example.puzzle], dtype=torch.long, device="cuda"))
        with GenerationObserver(adapter.vq) as observer:
            codes = adapter.generator.generate(None, context, temperature=0.0, top_k=0, top_p=1.0,
                                               cfg_scale=0.0, cfg_null_eos=adapter.tokenizer.pre_tokenizer.eos_token_id)
            generation = observer.finish()
        tracker, states = CausalFeatureTracker(), []
        for depth, length in enumerate(LEVEL_LENGTHS, 1):
            offset = sum(LEVEL_LENGTHS[:depth])
            prefix, assembly = cuda_region(lambda: torch.cat(
                [codes[:, sum(LEVEL_LENGTHS[:i]):sum(LEVEL_LENGTHS[:i + 1])] for i in range(depth)], dim=1))
            # Reconstruction accepts the assembled prefix and never reads future codes.
            latent, reconstruction = cuda_region(lambda: reconstruct_at_depth(adapter.vq, prefix, depth))
            ids, decode = cuda_region(lambda: adapter.pick_tokens(adapter.tokenizer.vqvae.decoder(latent)))
            raw, transfer = host_region(lambda: ids[0].cpu().tolist())
            text, text_ms = host_region(lambda: adapter.decode_ids(raw))
            verdict, verifier_ms = host_region(lambda: validate_solution(example.puzzle, raw))
            _, features_ms = host_region(lambda: tracker.observe(PrefixObservation(depth, length, offset, tuple(raw))))
            _, policy_ms = host_region(lambda: verified_decision(verdict.is_valid_solution))
            diagnostic = validate_solution(example.puzzle, raw, reference=example.reference)
            states.append({"level": depth, "prefix_assembly": assembly, "reconstruction": reconstruction,
                           "decode_select": decode, "transfer_ms": transfer, "text_ms": text_ms,
                           "verifier_ms": verifier_ms, "features_ms": features_ms, "policy_ms": policy_ms,
                           "valid": verdict.is_valid_solution, "reference_agreement": diagnostic.reference_agreement,
                           "decoded_ids": raw, "decoded_text": text})
        # A separate, unmodified upstream reconstruction checks the diagnostic path.
        final_ids, _ = adapter.decode_latent(adapter.vq.idx_to_z_q(codes))
        if final_ids[0].tolist() != states[-1]["decoded_ids"]:
            raise RuntimeError("Diagnostic final output differs from upstream reconstruction.")
        return {"schema_version": 1, "sample_id": example.identity, "dataset_index": example.index,
                "partition": example.partition, "repeat": repeat, "input_prepare": prepare,
                "generation": generation, "levels": states, "generated_codes": codes[0].tolist()}
