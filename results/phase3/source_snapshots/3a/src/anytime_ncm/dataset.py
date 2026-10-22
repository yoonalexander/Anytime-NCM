"""Frozen partition selection and non-executing, selective token-row access."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

MANIFEST_SHA256 = "ed7a6b3c102fe4713a3f80f8f02b53afe37a44b53da80964936467617799bdb7"
PROTOCOL_SHA256 = "557cf1377fe49b6c8515f506856ff0a395f8aaabe32adc79c25a8f2d9a3929ef"
ALLOWED_PARTITIONS = {"exploration": 1000, "development": 400}


def sha256(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def puzzle_identity(tokens) -> str:
    return hashlib.sha256(json.dumps(list(tokens), separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Example:
    index: int
    partition: str
    identity: str
    puzzle: tuple[int, ...]
    reference: tuple[int, ...]


def select_entries(manifest: dict, counts: dict[str, int]) -> tuple[dict, ...]:
    if not counts or set(counts) - ALLOWED_PARTITIONS.keys():
        raise ValueError("Collection permits only exploration and development.")
    seen_indices, seen_identities = set(), set()
    selected = []
    for name, entries in manifest["partitions"].items():
        for entry in entries:
            index, identity = entry["index"], entry["puzzle_sha256"]
            if index in seen_indices or identity in seen_identities:
                raise ValueError("Manifest indices and puzzle identities must be disjoint.")
            seen_indices.add(index)
            seen_identities.add(identity)
        if name not in counts:
            continue
        count = counts[name]
        if type(count) is not int or not 1 <= count <= ALLOWED_PARTITIONS[name] or count > len(entries):
            raise ValueError("Requested partition count is outside the frozen budget.")
        selected.extend(dict(entry, partition=name) for entry in sorted(entries, key=lambda e: e["index"])[:count])
    if set(counts) - manifest["partitions"].keys():
        raise ValueError("Requested partition is missing.")
    return tuple(sorted(selected, key=lambda e: e["index"]))


class _TokenRows:
    """Read only the pinned protocol-4 list-of-integer-lists grammar.

    No pickle execution, memo dereferences, globals, or object constructors.
    Unselected integer operands are skipped without decoding/materializing them.
    File bytes and structural opcodes are traversed, including sealed rows.
    """

    def __init__(self, data: bytes):
        self.data = memoryview(data)
        self.position = 0

    def op(self) -> int:
        while True:
            if self.position >= len(self.data):
                raise ValueError("Truncated token pickle.")
            value = self.data[self.position]
            self.position += 1
            if value != 0x95:  # FRAME; payload length is metadata, not token data.
                return value
            self.position += 8
            if self.position > len(self.data):
                raise ValueError("Truncated pickle frame.")

    def expect(self, value: int) -> None:
        if self.op() != value:
            raise ValueError("Unsupported token pickle structure.")

    def token(self) -> int:
        if self.position >= len(self.data):
            raise ValueError("Truncated integer operand.")
        value = int(self.data[self.position])
        self.position += 1
        return value

    def select(self, indices: set[int], row_length: int, expected_count: int) -> dict[int, tuple[int, ...]]:
        if self.data[:2].tobytes() != b"\x80\x04":
            raise ValueError("Only the pinned protocol-4 token-list format is supported.")
        self.position = 2
        self.expect(ord("]"))       # root EMPTY_LIST
        self.expect(0x94)           # MEMOIZE
        result, count = {}, 0
        while True:
            opcode = self.op()
            if opcode == ord("."):  # STOP
                break
            if opcode != ord("("):
                raise ValueError("Expected a root list batch.")
            while True:
                opcode = self.op()
                if opcode == ord("e"):  # root batch APPENDS
                    break
                if opcode != ord("]") or count >= expected_count:
                    raise ValueError("Unexpected token row.")
                self.expect(0x94)
                self.expect(ord("("))
                values = [] if count in indices else None
                length = 0
                while True:
                    opcode = self.op()
                    if opcode == ord("e"):
                        break
                    if opcode != ord("K"):  # BININT1 only, no executable pickle opcodes.
                        raise ValueError("Unsupported token operand.")
                    if values is not None:
                        values.append(self.token())
                    else:
                        self.position += 1  # never read the unselected operand
                    length += 1
                    if length > row_length or self.position > len(self.data):
                        raise ValueError("Malformed token row.")
                if length != row_length:
                    raise ValueError("Unexpected token row length.")
                if values is not None:
                    if any(value > 11 for value in values):
                        raise ValueError("Unknown selected Sudoku token ID.")
                    result[count] = tuple(values)
                count += 1
        if count != expected_count or self.position != len(self.data) or set(result) != indices:
            raise ValueError("Token dataset count, selection, or trailing bytes are invalid.")
        return result


def load_examples(repository: Path, counts: dict[str, int]) -> tuple[tuple[Example, ...], dict]:
    repository = Path(repository)
    manifest_path = repository / "docs/partitions/sudoku-hard.json"
    protocol_path = repository / "docs/experiment_protocol.md"
    if sha256(manifest_path) != MANIFEST_SHA256 or sha256(protocol_path) != PROTOCOL_SHA256:
        raise ValueError("Frozen manifest or protocol changed.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = select_entries(manifest, counts)  # reject sealed selection before opening datasets
    artifacts = json.loads((repository / "results/setup/artifacts.json").read_text(encoding="utf-8"))
    for record in artifacts:
        if sha256(repository / record["path"]) != record["sha256"]:
            raise ValueError(f"Pinned artifact mismatch: {record['path']}")
    indices = {entry["index"] for entry in entries}
    rows = []
    for filename, length in (("puzzles.pickle", 91), ("solutions.pickle", 89)):
        raw = (repository / "data/sudoku/hard" / filename).read_bytes()
        rows.append(_TokenRows(raw).select(indices, length, manifest["sample_count"]))
    examples = []
    for entry in entries:
        index = entry["index"]
        puzzle, reference = rows[0][index], rows[1][index]
        if puzzle_identity(puzzle) != entry["puzzle_sha256"]:
            raise ValueError("Selected puzzle identity disagrees with manifest.")
        examples.append(Example(index, entry["partition"], entry["puzzle_sha256"], puzzle, reference))
    return tuple(examples), {"artifacts": artifacts, "manifest_sha256": MANIFEST_SHA256,
                             "protocol_sha256": PROTOCOL_SHA256,
                             "selected_rows_per_file": len(examples),
                             "sealed_rows_materialized": 0}
