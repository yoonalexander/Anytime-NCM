"""Freeze input-identity partitions before inference; never read solutions."""

import hashlib
import json
from pathlib import Path
import pickle
import random

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sources = json.loads((ROOT / "configs/setup_sources.json").read_text())
    puzzle_path = ROOT / "data/sudoku/hard/puzzles.pickle"
    # Only the explicitly pinned, trusted upstream dataset is deserialized.
    puzzles = pickle.loads(puzzle_path.read_bytes())
    if len(puzzles) != 2000:
        raise ValueError("Expected the 2000-input official reproduction set.")
    groups: dict[str, list[int]] = {}
    for index, puzzle in enumerate(puzzles):
        canonical = json.dumps([int(token) for token in puzzle], separators=(",", ":"))
        identity = hashlib.sha256(canonical.encode()).hexdigest()
        groups.setdefault(identity, []).append(index)
    exploration = sorted(key for key, indices in groups.items() if min(indices) < 32)
    remaining = sorted(set(groups) - set(exploration))
    random.Random(20261020).shuffle(remaining)
    # Allocate by unique puzzle identity, with every duplicate kept in one split.
    unique_count = len(groups)
    targets = {"exploration": unique_count // 2, "development": unique_count // 5,
               "phase2_final": unique_count * 15 // 100}
    if len(exploration) > targets["exploration"]:
        raise ValueError("Smoke group exceeds the exploration allocation.")
    needed = targets["exploration"] - len(exploration)
    identities = {"exploration": exploration + remaining[:needed]}
    cursor = needed
    for name in ("development", "phase2_final"):
        identities[name] = remaining[cursor:cursor + targets[name]]
        cursor += targets[name]
    identities["phase3_final"] = remaining[cursor:]
    partitions = {
        name: sorted(
            ({"index": index, "puzzle_sha256": key} for key in keys for index in groups[key]),
            key=lambda entry: entry["index"],
        ) for name, keys in identities.items()
    }
    all_indices = [entry["index"] for rows in partitions.values() for entry in rows]
    assert sorted(all_indices) == list(range(len(puzzles)))
    assert set(range(32)) <= {entry["index"] for entry in partitions["exploration"]}
    assert sum(map(len, identities.values())) == len(set().union(*map(set, identities.values())))
    record = {
        "schema_version": 1, "seed": 20261020,
        "dataset_repo": sources["dataset_repo"],
        "dataset_revision": sources["dataset_revision"],
        "puzzles_file_sha256": hashlib.sha256(puzzle_path.read_bytes()).hexdigest(),
        "identity_rule": "sha256 of compact JSON integer input-token list; solutions never read",
        "unique_puzzle_count": unique_count, "sample_count": len(puzzles),
        "partitions": partitions,
    }
    output = ROOT / "docs/partitions/sudoku-hard.json"
    serialized = json.dumps(record, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.read_text() != serialized:
        raise RuntimeError("Refusing to overwrite a different frozen partition manifest.")
    output.write_text(serialized)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    (output.parent / "sudoku-hard.sha256").write_text(f"{digest}  sudoku-hard.json\n")
    print(json.dumps({"manifest_sha256": digest, "counts": {name: len(rows) for name, rows in partitions.items()}}))


if __name__ == "__main__":
    main()
