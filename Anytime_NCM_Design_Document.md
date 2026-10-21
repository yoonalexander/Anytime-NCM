# Anytime NCM
## Research and Engineering Design Document

**Version:** 1.2 (partial-decoding and holdout corrections; not experimentally validated)  
**Prepared:** October 20, 2026  
**Project type:** Reproducible machine-learning research and open-source tooling  
**Status:** Proposed, not yet implemented or experimentally validated  
**Upstream architecture:** [HazyResearch/ncm](https://github.com/HazyResearch/ncm)  
**Primary task:** Sudoku; subsequent tasks: German-to-English translation and XSum summarization  

---

## 1. Executive summary

**Anytime NCM** investigates whether a *fixed, pretrained Next-Concept Modeling (NCM)* model can decide, separately for every input, when to stop its coarse-to-fine generation hierarchy. Standard NCM runs every configured level, even if an intermediate decoded output is already useful or correct. Our research system will inspect partial reconstructions and, eventually, learn a lightweight stopping policy that minimizes computation without sacrificing an unacceptable amount of output quality.

This is **not** a proposal to train a new foundation model, a chatbot, or a frontend-first product. The first output is a rigorous experiment. The eventual result is a reproducible research repository, a measured quality-versus-latency comparison, and optionally a visual debugger.

**Primary question:** Can a per-example stopping policy improve the actual quality-versus-compute frontier relative to fixed-depth generation for the *same frozen NCM checkpoint*?

**First decision gate:** Using the released 12-level hard-Sudoku checkpoint, how often is a complete, valid solution available before the final level, and what is the measured potential savings from stopping at its first verifiably correct level?

### Success is not assumed

It may turn out that almost all usable outputs appear only at the final levels, that decoding/monitoring overhead erases the gains, or that simple rule-based validation beats learned policies. These are legitimate and publishable-in-spirit negative results if evaluated rigorously. Do **not** claim novel algorithms, speedups, safety improvements, or reproducibility until measured.

## 2. Background and evidence

Next-Concept Modeling was introduced by Kumbong et al. in October 2026. It uses a multiscale residual VQ-VAE tokenizer and a transformer that generates discrete latent codes one hierarchy level at a time, predicting all positions within each level in parallel. Nested dropout encourages useful partial reconstructions. The original work uses a fixed number of levels and explicitly identifies **input-dependent schedules** as future work.

The public repo includes pretrained tokenizers, generators, evaluation configs, and scripts for Sudoku, translation, summarization, and unconditional generation. The released hard-Sudoku config specifies **12 levels**, with **per-level code lengths 1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89**, `temperature: 0.0`, and `eval.n_docs: 2000` at the time of this design. The corresponding cumulative generated-code counts are **1, 3, 7, 13, 22, 35, 53, 79, 116, 166, 233, 322**. The final 89-position level is not the total number of generated codes. Use cumulative counts for trajectory slicing and work accounting, while keeping them distinct from measured latency. Do not assume the config is unchanged; record the exact upstream commit and inspect it.

Relevant predecessors include Adaptive Computation Time (Graves, 2016), CALM (NeurIPS 2022), and adaptive stopping for diffusion language models (e.g., SchED, 2026). **The general concept of adaptive computation is established.** A research contribution would have to come from the NCM hierarchy's particular behavior, rigorously compared policies, or a result about when additional levels help versus hurt.

## 3. Scope

### In scope: MVP / research version

Phase 1 is a standalone research deliverable. The online MVP is conditional on the Phase 1 decision gate; a documented negative result can complete Phase 1 without requiring online stopping work. Section 12 defines acceptance for each milestone separately.

- Reproduce the official hard-Sudoku baseline using the released checkpoint.
- Extract the complete 12-level generation trajectory for each example.
- Decode and validate outputs after each level, using the upstream tokenizer and Sudoku format.
- Measure generator time, reconstruction/decoding time, validator time, and end-to-end runtime.
- Quantify how frequently correct intermediate outputs appear, disappear, or never appear.
- Compare full-depth, fixed-depth, and verified early stopping.
- Evaluate one or more training-free stopping signals; train a lightweight policy only if there is measurable headroom.
- Produce versioned datasets, figures, tests, and an experiment report.

### Later phases

- Learn a stopping policy based on **expected benefit of further refinement**, not merely code-level confidence.
- Evaluate on WMT14 De-En and XSum where no exact cheap checker exists.
- Combine stopping decisions with Concept Firewall's failure-risk signals.
- Build an optional interactive visualization of per-level trajectories and policy decisions.

### Explicit non-goals

- Training or modifying the base NCM generator for v1.
- Altering the number of available hierarchy levels beyond the pretrained maximum.
- Building an LLM chatbot, browser product, or mobile application.
- Claiming that Sudoku correctness is equivalent to AI safety.
- Reporting skipped levels as equivalent to real speedup.
- Using inspected official test examples to select or fit any policy and then claim untouched official test performance.

## 4. Research questions and hypotheses

**RQ1: Early-exit opportunity.** How early do complete, valid outputs first occur? Do later levels ever corrupt a previously valid output?

**RQ2: Practical compute savings.** Does stopping at the first verified success improve latency or GPU cost **including monitoring overhead**, relative to full-depth generation?

**RQ3: Predictive stopping.** Can features available at level `k` predict whether additional refinement is valuable, outperforming simple fixed-level and confidence/stability heuristics?

**RQ4: Generality.** Do the results transfer from verifiable Sudoku to translation/summarization, where quality is continuous and sometimes non-monotonic?

**Hypothesis H1:** A nontrivial proportion of Sudoku trajectories contain a valid intermediate solution prior to level 12.

**Hypothesis H2:** For at least one task, a per-example policy will improve the held-out quality-versus-wall-clock frontier over the best fixed-level policy at the same compute budget.

**Hypothesis H3 (optional):** Internal state statistics contain incremental predictive value beyond level number, input difficulty, and partial decoded output alone.

All hypotheses are falsifiable; none is a promised result.

## 5. System architecture

```text
                    Original NCM release (frozen)
          +-------------------------------------------+
Puzzle -->| NCM generator: level 1 ... level K       |
          | Multiscale tokenizer and partial decoder  |
          +---------------------+---------------------+
                                |
                         LevelState stream
                                |
             +------------------+------------------+
             |                  |                  |
       Trajectory store   Sudoku validator   Feature extractor
             |                  |                  |
             +------------------+------------------+
                                |
                     Experiment evaluator
                                |
               +----------------+----------------+
               |                |                |
         Full-depth        Fixed-depth      Adaptive policy
            baseline         baselines        and/or verifier
               |                |                |
               +----------------+----------------+
                                |
                    Metrics, plots, report
```

### Operating modes by milestone

**A. Offline analysis mode.** Run the original NCM generator through all levels **unchanged**. Obtain codes from `net.generate(...)`, then reconstruct each generated prefix as a full-resolution cumulative latent using the pinned upstream quantizer's embedding, upsampling, and residual-transform operations. Capture an independent copy after every level and decode those copies post-hoc. Do not decode the shortened `z_levels` returned by `idx_to_zhats(...)`, or treat its aliased `z_hats` list as independent snapshots. Section 8.1 defines the adapter procedure and required checks. This mode measures partial-reconstruction quality and oracle opportunities without claiming computation was saved.

**B. True online stopping mode.** Once offline analyses are reliable, introduce a narrowly scoped, well-tested callback or `max_level`/stopping hook into the generation loop in `models/next_concept.py`. The hook must actually prevent later generator evaluations. Benchmark the modified full-depth path against the original and prove that disabling the stopping policy reproduces baseline outputs. Do not count offline truncation as a runtime improvement.

Offline mode is required for Phase 1. Online mode is required only for the conditional Phase 2 MVP after a go decision. Diagnostic profiling of the unchanged full-depth generator is permitted in Phase 1; it does not authorize a stopping hook or change the generation schedule.

### Interfaces (proposed; not existing upstream API)

```python
@dataclass
class LevelState:
    sample_id: str
    level: int
    code_ids: object                 # actual tensor stored optionally
    decoded_ids: list[int] | None
    decoded_text: str | None
    features: dict[str, float]
    generation_ms: float
    decode_ms: float

class StoppingPolicy(Protocol):
    def should_stop(self, state: LevelState) -> bool: ...

class SudokuVerifier(Protocol):
    def is_valid_solution(self, puzzle: object, output: object) -> bool: ...
```

Use a clean adapter around upstream. Prefer placing new code under `src/anytime_ncm/` rather than editing research code directly. A small isolated upstream patch is acceptable for the online callback, documented with the upstream commit and regression tests.

## 6. Repository structure

```text
anytime-ncm/
├── README.md
├── DESIGN.md                         # this document
├── pyproject.toml                    # project's additional dependencies and CLI
├── requirements.lock                 # generated from a validated environment
├── .gitignore
├── configs/
│   ├── sudoku_smoke.yaml
│   ├── sudoku_full.yaml
│   └── stopping_policies.yaml
├── third_party/
│   └── ncm/                          # pinned official Git submodule
├── src/anytime_ncm/
│   ├── upstream_adapter.py           # loading, sampling, hierarchy extraction
│   ├── trajectories.py              # structured run recording
│   ├── sudoku.py                    # parsing and correctness checks
│   ├── policies.py                  # full/fixed/validator/heuristic/learned
│   ├── features.py                  # per-level signals
│   ├── timing.py                    # correct GPU timings and overhead
│   ├── run_baseline.py
│   ├── collect.py
│   ├── benchmark.py
│   ├── train_policy.py
│   └── report.py
├── tests/
│   ├── test_sudoku_validator.py
│   ├── test_partial_decoder.py
│   ├── test_full_depth_equivalence.py
│   ├── test_policy_no_future_leakage.py
│   └── test_timing.py
├── data/                             # ignored: downloaded datasets
├── artifacts/                        # ignored: model checkpoints
├── results/                          # metadata, trajectories, plots
└── docs/
    ├── reproduction_log.md
    ├── experiment_protocol.md
    └── known_limitations.md
```

Ignore checkpoints, large datasets, secrets, environment directories, and raw latent tensors in Git. Keep small configs, code, synthetic fixtures, and results summaries versioned.

## 7. Setup: recommended Windows + NVIDIA / WSL2 pathway

**Requirement:** Python 3.10+, Git, sufficient storage, and preferably a recent NVIDIA CUDA-capable GPU. WSL2 Ubuntu is recommended on Windows for fewer research-repo compatibility surprises. If you have no supported GPU, use a Linux cloud instance with CUDA and record its hardware/software specifications. CPU-only use is not supported by the official `evaluate.py` entry point as written; a community CPU port is not a guaranteed fallback.

### 7.1 Verify environment

From WSL2 / Linux terminal:

```bash
nvidia-smi
python3 --version
git --version
```

If `nvidia-smi` fails, resolve drivers, WSL GPU passthrough, or choose a compatible hosted GPU **before** proceeding. Do not silently switch the scientific baseline to an unvalidated CPU fork.

### 7.2 Create a separate research repository

```bash
mkdir anytime-ncm
cd anytime-ncm
git init
git submodule add https://github.com/HazyResearch/ncm.git third_party/ncm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

On Windows without WSL2, activate the environment using PowerShell's `.venv\Scripts\Activate.ps1`; however, the official GPU evaluation may require other changes. The code examples below assume WSL2/Linux.

### 7.3 Install compatible CUDA PyTorch and dependencies

Select a **CUDA-enabled PyTorch wheel compatible with your NVIDIA driver** using the official selector at https://pytorch.org/get-started/locally/ . Do not hard-code an unverified CUDA wheel URL in this design. After installing it:

```bash
python -m pip install -r third_party/ncm/requirements.txt
python -m pip install pandas scipy scikit-learn matplotlib pyarrow pytest pyyaml
python - <<'PY'
import torch
print('torch:', torch.__version__)
print('cuda_available:', torch.cuda.is_available())
print('cuda_version:', torch.version.cuda)
if torch.cuda.is_available():
    print('gpu:', torch.cuda.get_device_name(0))
PY
```

Confirm CUDA is still available *after* dependency installation. If `pip` replaced the desired Torch build, reinstall the correct PyTorch build and lock the environment. Later, capture `pip freeze > requirements.lock`, Python version, CUDA driver/runtime, GPU model, and relevant environment variables. Note that the project may need additional packages discovered from upstream runtime errors; document each addition.

### 7.4 Download ONLY the hard-Sudoku checkpoint and dataset

The full model/dataset repositories contain many large task artifacts. Start with a narrow filtered download:

```bash
hf download hazyresearch/ncm-checkpoints \
  --include 'sudoku/hard/*' \
  --local-dir artifacts

hf download hazyresearch/ncm-datasets \
  --repo-type dataset \
  --include 'sudoku/hard/*' \
  --local-dir data
```

The `hf download --include` option is supported by the Hugging Face CLI. **Check the upstream Hub folder names with `hf download ... --dry-run` if the expected files do not appear**; the official README's generic complete-download commands are the fallback, but may download far more than needed.

Expected paths based on the released Hub layout (the config filename remains `sudoku-hard.yaml`):

```text
artifacts/sudoku/hard/tokenizer.pt
artifacts/sudoku/hard/generator.pt
data/sudoku/hard/puzzles.pickle
data/sudoku/hard/solutions.pickle
```

If the Hub layout differs, adapt paths after inspecting real files; do not fabricate checkpoint filenames. Record revision IDs or file hashes.

### 7.5 Reproduce the upstream baseline FIRST

From the research repository root:

Before running inference, freeze the partition manifest described in Section 8.5 and assign the first 32 smoke inputs to exploration. Official reproduction results are descriptive; do not use final-holdout outputs or aggregate scores to select a policy.

```bash
cd third_party/ncm
python evaluate.py \
  --config config/eval/sudoku-hard.yaml \
  --checkpoint-dir ../../artifacts/sudoku/hard \
  --data-dir ../../data/sudoku/hard \
  --gpus 0 \
  --n 32 \
  --out ../../results/upstream_smoke
cd ../..
```

This is a **32-input smoke test** only. The upstream command launches a GPU shard and then merges/scores its outputs. Check both the reported metrics and `results/upstream_smoke/shard_0.log`. For the full official baseline, remove `--n 32` and use a separate output folder.

**Checkpoint / hardware gate:** If loading fails with out-of-memory, incompatible CUDA, missing checkpoint paths, or tokenizer issues, resolve and record the blocker before writing new algorithms. Check if the official config's batch size is appropriate for your GPU, and use supported shard CLI options or a documented config override rather than altering evaluation semantics silently.

## 8. Implementation details and scientific controls

### 8.1 How to collect level-by-level outputs

The official `scripts/eval_shard.py` loads:

- `NextConceptTransformer` from `models.next_concept`;
- `VQVAETokenizer` from `tokenization.vqvae_tokenizer`;
- a checkpoint and task config;
- data from `puzzles.pickle` and `solutions.pickle`.

The official evaluator uses only the last entry of the second return value from `idx_to_zhats(g, return_zlevels=True)`, where the representation has full length. That final-output path cannot be extended to intermediate decoding by simply iterating over the same list:

- The second return value, `z_levels`, downsamples cumulative reconstructions to each level's length. With Sudoku's `compression_factor: 1`, the decoder preserves that length; early entries cannot produce complete 89-position board representations.
- The first return value, `z_hats`, appends the same accumulator tensor while updating it in place. At return, those entries alias the final accumulator. Cloning entries after the method returns does not recover the earlier states.

Implement prefix reconstruction in the adapter, leaving the generator unchanged. Mirror the pinned `models/quant.py` accumulation operations, but clone the full-resolution accumulator **inside the loop after each level**. The following illustrates that procedure; imports, loading, token selection, and persistence are omitted:

```python
# Illustrative adapter logic, not an existing upstream helper or runnable CLI.
# Match the pinned evaluator's eval mode and precision settings.
net.eval()
tk.vqvae.eval()
with torch.no_grad():
    generated_codes = net.generate(
        level0, context, temperature=temp, top_k=top_k, top_p=top_p,
        cfg_scale=cfg, cfg_null_eos=EOS,
    )
    vq = tk.vqvae.vq
    assert generated_codes.shape[1] == sum(vq.levels)
    z_hat = torch.zeros(
        generated_codes.shape[0], vq.levels[-1], vq.embed_dim,
        device=generated_codes.device,
    )
    partial_latents = []
    offset = 0
    for level_idx, length in enumerate(vq.levels):
        level_codes = generated_codes[:, offset:offset + length]
        contribution = vq.embeddings[level_idx](level_codes)
        if level_idx != len(vq.levels) - 1:
            contribution = vq._up_to_full(
                contribution, level_idx, vq.levels[-1]
            )
        contribution = vq._apply_quant_resi(contribution, level_idx)
        z_hat.add_(contribution)
        partial_latents.append(z_hat.clone())  # Snapshot before later updates.
        offset += length

    for k, latent in enumerate(partial_latents, start=1):
        assert latent.shape[1] == vq.levels[-1]  # 89 for this checkpoint.
        token_logits = tk.vqvae.decoder(latent)
        # Apply EXACT upstream pick_tokens and Sudoku decoding rules.
        # Then validate and save this level's output.
```

**Important:** `_up_to_full` and `_apply_quant_resi` are private upstream methods, so verify their signatures and behavior at the pinned commit and record that dependency. Preserve learned upsampling and residual transforms; replacing them with generic interpolation changes reconstruction semantics. Reuse upstream `pick_tokens`, the Sudoku pre-tokenizer, and reference handling. Do not assume the 89-token Sudoku representation is simply 81 ASCII digits.

Require both final-output parity with the official evaluator and intermediate-state regression tests: every latent must have full sequence length, snapshots must have independent storage, and changing only codes after level `k` must leave its snapshot unchanged. Compare an intermediate snapshot against an independently accumulated prefix fixture. Do not require snapshots to differ numerically on every real input, since a later contribution may legitimately leave an output unchanged. Final-level parity alone cannot detect incorrect early reconstructions or aliased snapshots.

In initial collection, generator runs all levels and `partial_latents` are decoded afterward. That correctly estimates *the opportunity* for early exit but cannot demonstrate latency savings from online halting.

### 8.2 Sudoku correctness contract

For each level, distinguish:

1. **Parseable:** The upstream token stream can be interpreted as a candidate board.
2. **Complete:** Every required cell has a legal assigned digit.
3. **Grid-valid:** Each row, column, and sub-grid contains each number once.
4. **Clue-consistent:** Every given cell matches the original puzzle.
5. **Reference agreement:** The candidate matches an official known solution, if appropriate.

Primary `is_valid_solution` requires (2), (3), and (4), not merely a nonzero count of correct cells. Keep official scoring separate so differences with original benchmark metrics are explicit. If the puzzle is not uniquely solvable, a distinct clue-consistent solution may still be correct; do not require exact reference equality as the sole criterion.

### 8.3 Features available to the stopping policy

Only use information available **at or before level k**:

- Level index and cumulative number of generated code positions.
- Code probability entropy / confidence (if exposed without changing sampling semantics).
- Changes in latent reconstructions across levels.
- Changes in decoded board/text across levels.
- Current validity flags for Sudoku, if policy explicitly permits a task-specific verifier.
- Timing estimates measured on the same hardware.

A task-general stopping policy may not use a perfect Sudoku validator. Keep task-specific verifier results as a distinct baseline, not as hidden training features for an ostensibly generic policy. Never use future levels, reference answers, or oracle exit labels as features at inference time.

### 8.4 Policies and comparison baselines

- **Full-depth:** Always generate all 12 levels (official behavior).
- **Fixed-k:** Always exit at a specified level `k`, evaluated for multiple `k` values.
- **Verified stop:** Stop at the first complete, valid Sudoku solution. This is a legitimate deployable policy for Sudoku, subject to verifier overhead.
- **Stability threshold:** Stop when consecutive partial outputs are sufficiently similar, with minimum-level and patience constraints.
- **Uncertainty threshold:** Stop based on confidence/entropy signals, calibrated on a development split.
- **Learned halting policy:** Logistic regression or small MLP, with thresholds tuned only on validation data.
- **Retrospective oracle:** Select the best exit knowing the whole future trajectory; **upper bound only**, never presented as deployable.

Calibrate comparisons at the same accuracy or compute budget and report the *best tuned fixed-depth baseline*, not a weak arbitrary level. Select fixed depths, heuristic thresholds, minimum levels, patience, inspection schedules, and learned-policy settings using development data only. Freeze the selected policies before final evaluation. A curve showing all fixed depths on exploratory data is descriptive and does not justify choosing the best depth on the final holdout.

### 8.5 Randomness and splitting

The released `sudoku-hard.yaml` specifies **temperature 0.0**, so changing a random seed need not produce alternative Sudoku continuations. Do not claim multi-seed diversity without explicitly enabling stochastic sampling and then documenting the changed distribution. Start by replicating the deterministic configuration. Analyze stochasticity as a separate, labeled extension.

The public artifacts are called an official **test** dataset. Holdout protection applies to every policy-selection decision, including training-free heuristics, fixed depths, and inspection schedules.

Before inspecting model outputs or per-level trajectories, freeze a manifest of disjoint exploration/training, development, and final-evaluation puzzle identities. Record partition sizes, construction method, seed, dataset revision, and manifest hash in `docs/experiment_protocol.md`. Assign the first 32 smoke examples to exploration; keep duplicate puzzle identities in one partition. Use exploration data for Phase 1 analysis and any controller fitting, development data for policy selection and the go/no-go decision, and the final holdout only after policies, metrics, and the statistical procedure are frozen.

Plan final evaluation separately for successive research phases. If Phase 3 is anticipated, reserve disjoint `phase2_final` and `phase3_final` partitions before initial output inspection; opening `phase2_final` must not expose `phase3_final` results. Freeze all Phase 3 policies and comparisons before evaluating them together on `phase3_final`. If no separate later-phase holdout was reserved and Phase 2 test results inform the learned-controller design, obtain a fresh holdout from the stated target distribution and evaluate the learned policy and all comparison baselines on it. Reuse of the exposed Phase 2 holdout may be reported as exploratory, with its limitations, but cannot support an untouched Phase 3 test claim. Record each holdout's access history.

Prefer newly generated, properly labeled Sudoku examples for exploration, training, and development so the official test set can remain the final evaluation set. If only the released data is available, partition it before inspection and describe final results as performance on a held-out subset of the released test data. Record possible overlap with base-model training data; controller partitioning alone does not establish absence of benchmark contamination.

Full official-set baseline reproduction is a separate descriptive result. Keep its holdout outputs and scores out of policy selection, and log any access. If official examples or aggregate results have already informed design choices, disclose that exposure and obtain a fresh final holdout before making an untouched-test claim. A later split cannot undo prior inspection.

### 8.6 Measuring compute and latency

Measure these separately:

- Per-level generation time in separate diagnostic profiling runs, using CUDA events or explicitly synchronized component timings.
- Cost of decoding a cumulative representation.
- Cost of extracting features and running the stopping policy.
- Sudoku verifier cost, including any host-device transfer.
- End-to-end per-example latency, peak GPU memory, and aggregate throughput at specified batch sizes.

Keep diagnostic profiling separate from headline latency benchmarks. In diagnostic runs, record event timings on the relevant CUDA stream and synchronize before reading them, or synchronize around isolated regions; document instrumentation overhead. Phase 1 may profile the unchanged full-depth generator with a profiler or non-mutating observation hooks, but must not add halting logic. Attribute reconstruction and other shared work explicitly rather than counting it twice.

For headline end-to-end runs, synchronize immediately before starting a host wall-clock timer and after the requested output is ready, then stop the timer. Do not insert diagnostic synchronization around every internal stage. Include input preparation, latent reconstruction, decoding, transfers, and all feature, verifier, and policy work actually used by that method. Retain synchronization required by the deployed algorithm itself. Exclude model loading, warmup, offline reference scoring, and result serialization from warm inference latency, and report those separately when relevant. Use identical timing boundaries for full-depth, fixed-depth, and adaptive methods.

Perform warmup iterations; record precision, `torch.compile` behavior, GPU model, batch size, and whether measurements are cold/warm. At least several timed runs should inform latency summaries and variation. Online adaptive batch execution is an additional engineering problem: early-completed samples must be masked or compacted. Begin with **batch size 1** for scientific clarity, then benchmark batched behavior separately.

**Do not equate 50% fewer hierarchy levels with 50% less latency.** Later levels generate more codes, and monitoring may dominate at small model sizes.

## 9. Experiment and evaluation plan

### Phase 0: Reproduction (required before anything else)

Deliverables: working environment, pinned versions, baseline metrics, log, and reproduction instructions.

Acceptance: official evaluation completes on a smoke subset and full baseline; differences from paper are explained, not silently hidden.

### Phase 1: Trajectory audit (first research contribution candidate)

For every exploration/development puzzle and hierarchy level, record validity, intermediate board, and decode cost. Obtain per-level generator-cost estimates from separate diagnostic profiling runs where reliable; store unavailable timings as null and report their coverage. Keep the final holdout sealed. Produce:

- Solve-rate-versus-level curve.
- Distribution of first-valid level.
- Frequency of valid-to-invalid later transitions.
- Fraction never solved.
- First-valid skipped levels and cumulative code work; where diagnostic timings exist, estimated net latency savings including repeated reconstruction, decoding, verification, and policy costs. These are offline estimates, **not measured online speedups**.
- Representative trajectories showing early success, late recovery, and never-solved cases.

**Predeclared decision gate:** Record the following design defaults in `docs/experiment_protocol.md` before trajectory inspection. They are research choices, not measured results: a minimum worthwhile **5% reduction in mean end-to-end latency**, **zero percentage points of empirical solve-rate loss** for verified stopping, and **zero false verifier accepts**. Report median and p95 latency separately. Changes to these thresholds require a dated protocol amendment before the affected evaluation; do not tune them against observed final-holdout outcomes.

On development data, estimate the cost of first-valid stopping by combining profiled generation work through the selected exit with all monitoring costs through that exit. For never-valid trajectories, charge full-depth work and every scheduled check. Compare against full-depth generation plus its final reconstruction and decode, using consistent timing boundaries. Report a paired 95% bootstrap interval for the estimated relative mean-latency reduction and state that separate component profiles cannot establish actual online speedup.

- **Go to Phase 2:** Estimated mean-latency reduction is at least 5%, its interval lower bound exceeds zero, and the quality/verifier checks pass. This justifies an online experiment only.
- **No-go under this protocol:** The interval upper bound is below 5%, or correctness/parity remains unresolved. Document limited opportunity or the unresolved validity issue, respectively; do not train a halting model.
- **Inconclusive:** All other cases, including missing cost estimates. Collect more exploration/development measurements within a predeclared sample and profiling budget, then report uncertainty if the gate remains unresolved. Do not substitute the final holdout for more development data.

A negative or inconclusive report completes Phase 1 when its required artifacts and limitations are documented. Translation or other checkpoints are possible follow-up studies, not automatic extensions of this work order.

### Phase 2: True online verified stopping

Add the minimal generation hook. Re-run the baseline with the hook disabled, ensure output equivalence, and measure actual stop-on-first-valid performance.

Acceptance: stopping truly avoids remaining generator work; valid solutions are never incorrectly accepted; the benchmark includes verifier and decoder overhead.

Freeze the verified policy and benchmark procedure before opening the Phase 2 final holdout (`phase2_final` if separate phase holdouts are reserved). Keep any Phase 3 holdout sealed. Report the measured result even if online overhead defeats the Phase 1 estimate. Claim the predeclared practical improvement only if actual mean latency falls by at least 5%, the paired 95% interval excludes zero reduction, empirical solve rate does not decrease, and there are no false verifier accepts. These sample results do not prove a population-wide zero-error guarantee. A valid negative online result still completes the Phase 2 experiment; controller training requires a separate justification of remaining headroom.

### Phase 3: Learned stopping, only if justified

Train simple interpretable models first. Compare their test-set quality and cost to full depth, fixed-k, verified Sudoku stop, and available uncertainty/stability baselines. Use appropriate calibration and confidence intervals. Avoid features that encode future truth.

Apply Section 8.5's phase-specific holdout rule: reserve or obtain an unexposed Phase 3 final set, freeze the learned policy and all comparison settings using exploration/training and development data, and evaluate all methods on that same final set. Phase 2 test results may motivate this follow-up study, but the exposed Phase 2 holdout must not be relabeled an untouched Phase 3 test set.

Acceptance: policy provides a clearly measured result, positive or negative, against strong baselines on held-out puzzle identities.

### Phase 4: Natural language generalization

Use WMT14 German-English or XSum with the released checkpoint. Evaluate quality at each level with appropriate reference-based metrics and targeted semantic checks (e.g., numbers and negation); acknowledge that BLEU/ROUGE are not full semantic correctness measures. Investigate when later levels improve or damage final quality.

Acceptance: report whether conclusions from Sudoku transfer; avoid conflating different task metrics.

### Phase 5: Optional visualization and Concept Firewall bridge

Only after research results exist, build a trajectory viewer: source input, each level's reconstruction, detected issues, estimated continuation value, chosen stop level, cost, and comparison with full-depth output. This viewer should be an inspectable research interface, not a substitute for experiments.

## 10. Metrics and statistical analysis

**Quality:** Sudoku complete-valid-clue-consistent solve rate (primary), upstream solved/cell/valid-grid metrics for comparability; WMT BLEU/chrF or suitable semantic analysis; XSum ROUGE plus targeted factual checks.

**Efficiency:** Median and p95 wall-clock latency; mean GPU time; per-example generator work; peak allocated GPU memory; throughput; stopping-policy overhead; decoding overhead.

**Tradeoff:** Quality against total measured latency or FLOPs for all exit methods. At matched quality, report relative latency reduction. At matched cost, report quality improvement.

**Reliability:** False early accepts (especially for heuristic/learned policies), calibration of predicted sufficiency, and subgroup performance where available.

**Statistics:** Paired per-input comparisons with bootstrap confidence intervals or other suitable methods; results across multiple data partitions if learning a controller; freeze the primary metric, policies, quality tolerance, and statistical procedure before inspecting the final holdout. For the decision gate, use relative reduction in mean end-to-end latency and paired 95% bootstrap intervals as specified in Section 9; preserve all repeated timings for each puzzle when resampling puzzle identities. Report quality differences and their uncertainty separately. Avoid selecting only successful example trajectories.

A simple research objective is:

\[
\min_{\pi}\;\mathbb{E}\left[L(y_{\tau}, y^*)+\lambda\,C_{\tau}\right]
\]

where `π` chooses exit level `τ` using only the current state, `L` measures task error, and `C` is *measured total inference cost*. The value-of-computation formulation is a later research extension, not a prerequisite for the MVP.

## 11. Storage and reproducibility

A compact JSONL trajectory record might look like:

```json
{
  "run_id": "smoke_001",
  "sample_id": "sudoku-hard:000123",
  "upstream_commit": "<actual commit SHA>",
  "checkpoint_revision": "<actual Hugging Face revision>",
  "config_sha256": "<actual hash>",
  "seed": 42,
  "sampling": {"temperature": 0.0, "top_k": 0, "top_p": 1.0},
  "levels": [
    {"k": 1, "complete": false, "valid": false, "gen_ms": null, "decode_ms": 0.0},
    {"k": 12, "complete": true, "valid": true, "gen_ms": null, "decode_ms": 0.0}
  ]
}
```

Values above are schema examples, **not measurements**. The offline collector may leave per-level generator timings null until reliable diagnostic profiling exists. Keep diagnostic timing records separate from headline benchmark records and identify the profiling run used for each offline cost estimate. Record dataset revision, partition name, manifest hash, and policy/protocol revision in the run metadata. Use Parquet for larger numerical feature matrices. Do not commit huge model activations by default.

Every published figure should trace back to a config, a dataset partition, a model/checkpoint revision, code commit, and a machine specification. Record exceptions, OOM restarts, and discarded runs.

## 12. Testing and acceptance criteria

Required automated tests by milestone:

1. Valid and invalid Sudoku fixtures, including incomplete grids, duplicate digits, and clue corruption.
2. Partial-decoder correctness: all cumulative snapshots have full sequence length and independent storage; an independently accumulated prefix fixture agrees; changing later codes cannot change earlier snapshots. Also require final-level parity with the original upstream evaluator on the same input.
3. Partition isolation: no duplicate puzzle identity crosses partitions; collection and tuning paths cannot read any sealed final holdout; Phase 2 evaluation cannot read a reserved Phase 3 holdout.
4. Timing sanity: no negative timings; warmup and device synchronization controls; diagnostic and headline runs are labeled separately.
5. Phase 2: full-depth no-stop parity, with the generation hook disabled versus the original generator.
6. Phase 2 and later policies: input isolation, so no future `k+1...K` values are accessible at level `k`.
7. Phase 2 and later policies: strict level boundaries and safe fallback; never halt before minimum level or request more than maximum.
8. Phase 2: offline versus online stop result equivalence for deterministic sampling, including never-valid cases, and proof that later generator evaluations are skipped.

**Phase 1 research deliverable is complete when** an independent developer can reproduce the smoke and full official baselines, produce an exploration/development per-level trajectory table and solve-rate plot, and reproduce the documented go/no-go/inconclusive assessment from commands, manifests, profiles, and limitations. Missing cost estimates must be labeled inconclusive, not presented as a measured negative speedup. Online generation edits and measurements are not required for this milestone.

**Conditional Phase 2 online MVP is complete when**, after a Phase 1 go decision, the Phase 2 tests pass and an independent developer can run the measured verified-stopping comparison against full depth and development-selected fixed-depth baselines on the frozen final holdout. Completion requires a reproducible experiment and honest positive or negative findings; a speedup claim additionally requires the Section 9 improvement criteria. A Phase 1 no-go or inconclusive outcome closes that research milestone without labeling the online MVP implemented.

## 13. Risks and mitigation

| Risk | Mitigation |
|---|---|
| No CUDA-capable GPU or insufficient VRAM | Preflight hardware; use a compatible Linux GPU host; benchmark resource requirements before scaling. |
| Partial decoded outputs are malformed | Use upstream decoder; explicitly count incomplete/unparseable outputs. |
| All useful outputs appear at the last level | Publish the finding; evaluate other checkpoints before training a controller. |
| Decoding on every level is too expensive | Measure this cost; test cheaper latent features or sparse checks. |
| GPU batch overhead hides savings | Separate batch-1 online latency from batch-throughput experiments. |
| Controller overfits task or puzzle | Hold out unique puzzles and use simple baselines; avoid test-label leakage. |
| Upstream repository changes | Pin a commit and record every patch in version control. |
| Overclaiming novelty | Compare to prior adaptive computation and diffusion exiting work; word findings as NCM-specific until established. |
| Unsafe checkpoint loading | Only load trusted upstream model files; some PyTorch loaders deserialize pickles and should not be used with arbitrary untrusted checkpoints. |

## 14. Immediate work order for Codex

**Do not implement the full roadmap in one pass. Complete these steps in order and stop after the first scientifically meaningful result.**

1. Read this document, upstream README, `evaluate.py`, `scripts/eval_shard.py`, `models/next_concept.py`, and `config/eval/sudoku-hard.yaml` at the *pinned commit*.
2. Report the actual Python/GPU/CUDA state and dependency issues. Do not fabricate successful installations or benchmark numbers.
3. Set up the repository with pinned upstream Git submodule and a clean Python environment.
4. Download the narrow Sudoku checkpoint/dataset, confirming actual Hub paths and hashes.
5. Freeze the partition manifest and protocol thresholds before output inspection, assigning the first 32 inputs to exploration. Run an official 32-example smoke baseline, then a documented full baseline when feasible; keep full-set reproduction outputs and scores separate from policy selection. Record an incomplete full baseline as a Phase 0 blocker rather than declaring Phase 1 complete.
6. Implement a reliable Sudoku parser and validator with unit tests.
7. Implement **offline post-hoc partial decoding** for all 12 levels using independent full-resolution cumulative snapshots as specified in Section 8.1; verify intermediate-prefix correctness, snapshot isolation, and final-level equivalence with upstream.
8. Run the trajectory audit on a modest representative exploration subset, then expand within exploration/development data. Profile the unchanged generator and monitoring costs separately where feasible.
9. Produce `results/phase1/summary.md` with graphs, actual numbers, limitations, and a **go/no-go/inconclusive recommendation** using Section 9's predeclared criteria. Stop after this report; a negative or inconclusive result is a valid Phase 1 outcome.
10. **Do not begin online generator edits or learned controller training in this work order.** A subsequent Phase 2 work order requires a Phase 1 go decision; later controller training requires evidence of remaining headroom.

### Expected Phase 1 deliverables

- `README.md` with tested setup and execution commands.
- `docs/reproduction_log.md` recording versions, hardware, and errors.
- `docs/experiment_protocol.md` with the frozen partition manifest/hash, thresholds, measurement procedure, and sample/profiling budget; partition manifests must be versioned alongside it.
- `src/anytime_ncm/` adapter, validator, trajectory collector.
- `tests/` covering correctness and baseline parity.
- `results/phase1/trajectories.parquet` or compact JSONL.
- `results/phase1/solve_rate_by_level.png`.
- Diagnostic cost profiles where available, with coverage and missing estimates explicitly documented.
- `results/phase1/summary.md` with measured findings and next-step decision.

## 15. References and source-of-truth links

1. Kumbong et al. (2026), *Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation*: https://arxiv.org/abs/2610.14162 (especially Section 3, Appendix C, Appendix F, Appendix I).
2. Official NCM repository and installation/evaluation commands: https://github.com/HazyResearch/ncm
3. Official generation script: https://github.com/HazyResearch/ncm/blob/main/scripts/eval_shard.py
4. Official hard-Sudoku configuration: https://github.com/HazyResearch/ncm/blob/main/config/eval/sudoku-hard.yaml
5. Official research blog: https://hazyresearch.stanford.edu/blog/2026-10-12-ncm
6. Model/dataset collection: https://huggingface.co/collections/hazyresearch/ncm
7. Hugging Face CLI download reference: https://huggingface.co/docs/huggingface_hub/package_reference/cli
8. PyTorch installation selector: https://pytorch.org/get-started/locally/
9. Graves (2016), *Adaptive Computation Time for Recurrent Neural Networks*: https://arxiv.org/abs/1603.08983
10. Google Research, *Confident Adaptive Language Modeling* (CALM): https://research.google/pubs/confident-adaptive-language-modeling/
11. SchED (2026), progress-aware early exiting for diffusion LMs: https://aclanthology.org/2026.findings-acl.1782/
12. PyTorch CUDA execution and timing guidance: https://pytorch.org/docs/stable/notes/cuda.html#asynchronous-execution

**Verification note:** Public repository structure, commands, NCM method names, Sudoku settings, and paper claims were checked against online sources on October 20, 2026. No local NCM inference run was executed while writing this design; instructions that depend on downloading weights, configuring CUDA, or benchmarking must be validated during implementation.
