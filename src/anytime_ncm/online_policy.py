"""Phase 2 immutable causal policy inputs and pure offline simulation."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Observation:
    level: int
    cumulative_codes: int
    decoded_ids: tuple[int, ...]

def policy_spec(kind, *, levels=None, min_level=1, patience=1, depth=12):
    if kind not in ("full", "fixed", "verified", "stability"):
        raise ValueError("Unknown online policy.")
    if type(min_level) is not int or not 1 <= min_level <= 12 or type(patience) is not int or patience < 1:
        raise ValueError("Invalid minimum/patience.")
    levels = list(range(min_level, 13)) if kind == "stability" else list(range(1, 13) if levels is None else levels)
    if kind in ("verified", "stability") and (not levels or levels != sorted(set(levels)) or levels[-1] != 12
            or any(type(x) is not int or not 1 <= x <= 12 for x in levels)):
        raise ValueError("Inspection schedule must be sorted, unique and include final fallback.")
    if kind=="verified" and levels[0]<min_level:
        raise ValueError("Inspection occurs before the policy minimum.")
    if type(depth) is not int or not 1 <= depth <= 12:
        raise ValueError("Invalid fixed depth.")
    return {"kind": kind, "levels": levels if kind in ("verified", "stability") else [],
            "min_level": min_level, "patience": patience, "depth": depth}

def stable_decision(observation, previous, unchanged, patience):
    ids = observation.decoded_ids
    if len(ids) != 89 or any(type(x) is not int or not 0 <= x <= 11 for x in ids):
        raise ValueError("Expected current legal Sudoku IDs.")
    count = unchanged + 1 if previous is not None and previous == ids else 0
    return count >= patience, ids, count

def simulated_exit(spec, states):
    if len(states) != 12:
        raise ValueError("Need the complete saved trajectory.")
    kind = spec["kind"]
    if kind == "full": return 12
    if kind == "fixed": return spec["depth"]
    previous, unchanged = None, 0
    for level, state in enumerate(states, 1):
        if level not in spec["levels"]: continue
        if kind == "verified":
            stop = state["correctness"]["is_valid_solution"]
        else:
            frame = Observation(level, state["cumulative_codes"], tuple(state["decoded_ids"]))
            stop, previous, unchanged = stable_decision(frame, previous, unchanged, spec["patience"])
        if stop: return level
    return 12
