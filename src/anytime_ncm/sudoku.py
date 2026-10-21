"""Sudoku parsing and correctness checks, independent of model inference.

Token IDs follow the pinned upstream SudokuTokenizer: 0 is blank, 1..9 are
digits, 10 is a row separator, and 11 is BOS. There are no PAD/EOS IDs.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Integral
from typing import TypeAlias


class SudokuParseError(ValueError):
    """An input cannot be represented as a nine-by-nine Sudoku board."""


@dataclass(frozen=True)
class SudokuBoard:
    """Immutable row-major cells; zero denotes a blank."""

    cells: tuple[int, ...]

    def __post_init__(self) -> None:
        try:
            cells = tuple(self.cells)
        except TypeError as exc:
            raise SudokuParseError("Board cells must be iterable.") from exc
        if len(cells) != 81:
            raise SudokuParseError("A board must contain exactly 81 cells.")
        if any(isinstance(cell, bool) or not isinstance(cell, Integral)
               or not 0 <= cell <= 9 for cell in cells):
            raise SudokuParseError("Cells must be integers from 0 through 9.")
        object.__setattr__(self, "cells", tuple(int(cell) for cell in cells))

    @property
    def complete(self) -> bool:
        return all(cell != 0 for cell in self.cells)

    def to_text(self) -> str:
        """Render the upstream 89-character board form, without BOS."""
        characters = "".join(str(cell) if cell else "_" for cell in self.cells)
        return "|".join(characters[start:start + 9] for start in range(0, 81, 9))


BoardInput: TypeAlias = SudokuBoard | str | Iterable[int]


def parse_board(value: BoardInput) -> SudokuBoard:
    """Parse a token stream or text into a board without repairing bad geometry.

    Accept 81 flat cells or nine rows of nine cells separated by eight pipes.
    Ignore whitespace in text, and remove BOS wherever upstream's
    skip_special_tokens=True would remove it. Text accepts <BOS> or the B
    shorthand understood by upstream encode. Both '_' and '0' denote blanks.
    Integer inputs must be flat token IDs; floats, booleans, unknown IDs and
    None are rejected. Tensor callers should explicitly pass .tolist().
    """
    if isinstance(value, SudokuBoard):
        return value
    if isinstance(value, str):
        text = "".join(value.replace("<BOS>", "B").split())
        text = text.replace("B", "")
        if any(character not in "0123456789_|" for character in text):
            raise SudokuParseError("Text contains an unknown Sudoku character.")
    else:
        try:
            iterator = iter(value)
        except TypeError as exc:
            raise SudokuParseError("Expected Sudoku text or a flat token iterable.") from exc
        characters = []
        for token in iterator:
            if isinstance(token, bool) or not isinstance(token, Integral):
                raise SudokuParseError("Token IDs must be integers, not booleans or floats.")
            token = int(token)
            if not 0 <= token <= 11:
                raise SudokuParseError("Unknown Sudoku token ID.")
            if token == 11:
                continue
            characters.append("|" if token == 10 else "_" if token == 0 else str(token))
        text = "".join(characters)
    if "|" in text:
        rows = text.split("|")
        if len(rows) != 9 or any(len(row) != 9 for row in rows):
            raise SudokuParseError("Expected nine rows of nine cells and eight separators.")
        text = "".join(rows)
    if len(text) != 81:
        raise SudokuParseError("A board must contain exactly 81 cells.")
    return SudokuBoard(tuple(0 if character in "_0" else int(character) for character in text))


def _units(board: SudokuBoard) -> tuple[tuple[int, ...], ...]:
    cells = board.cells
    rows = tuple(cells[start:start + 9] for start in range(0, 81, 9))
    columns = tuple(cells[column::9] for column in range(9))
    boxes = tuple(
        tuple(cells[(row + dr) * 9 + column + dc] for dr in range(3) for dc in range(3))
        for row in range(0, 9, 3) for column in range(0, 9, 3)
    )
    return rows + columns + boxes


def _grid_valid(board: SudokuBoard) -> bool:
    digits = frozenset(range(1, 10))
    return all(frozenset(unit) == digits for unit in _units(board))


def _clue_consistent(puzzle: SudokuBoard, candidate: SudokuBoard) -> bool:
    return all(given == 0 or given == actual
               for given, actual in zip(puzzle.cells, candidate.cells))


@dataclass(frozen=True)
class SudokuValidation:
    """Independent candidate flags; reference agreement is optional diagnostics."""

    board: SudokuBoard | None
    parseable: bool
    complete: bool
    grid_valid: bool
    clue_consistent: bool
    reference_agreement: bool | None
    parse_error: str | None = None

    @property
    def is_valid_solution(self) -> bool:
        return self.parseable and self.complete and self.grid_valid and self.clue_consistent


def validate_solution(
    puzzle: BoardInput,
    output: BoardInput,
    *,
    reference: BoardInput | None = None,
) -> SudokuValidation:
    """Validate a candidate; reference equality never controls acceptance.

    Malformed candidate outputs return explicit false flags and a parse error.
    Malformed or locally contradictory puzzle clues raise ValueError. An optional
    reference must itself be a complete, grid-valid, clue-consistent solution;
    invalid reference data raises ValueError instead of becoming a model error.
    Local clue consistency does not establish solvability or uniqueness.
    """
    parsed_puzzle = parse_board(puzzle)
    for unit in _units(parsed_puzzle):
        clues = [cell for cell in unit if cell != 0]
        if len(clues) != len(set(clues)):
            raise ValueError("Puzzle contains conflicting clues.")
    parsed_reference = None
    if reference is not None:
        parsed_reference = parse_board(reference)
        if not (_grid_valid(parsed_reference)
                and _clue_consistent(parsed_puzzle, parsed_reference)):
            raise ValueError("Reference must be a complete, valid solution of the puzzle.")
    try:
        candidate = parse_board(output)
    except SudokuParseError as exc:
        return SudokuValidation(
            board=None, parseable=False, complete=False, grid_valid=False,
            clue_consistent=False,
            reference_agreement=False if parsed_reference is not None else None,
            parse_error=str(exc),
        )
    return SudokuValidation(
        board=candidate, parseable=True, complete=candidate.complete,
        grid_valid=_grid_valid(candidate),
        clue_consistent=_clue_consistent(parsed_puzzle, candidate),
        reference_agreement=(candidate.cells == parsed_reference.cells
                             if parsed_reference is not None else None),
    )


def is_valid_solution(puzzle: BoardInput, output: BoardInput) -> bool:
    """Accept only a complete, valid grid preserving every puzzle clue."""
    return validate_solution(puzzle, output).is_valid_solution


@dataclass(frozen=True)
class OfficialSudokuMetrics:
    """Per-example values of the pinned official decoded-text scoring rules."""

    solved: bool
    cell_accuracy: float
    valid_grid: bool


def official_metrics(hypothesis: str, reference: str) -> OfficialSudokuMetrics:
    """Score already-decoded text exactly as upstream eval_merge.py does.

    This deliberately does not normalize whitespace/BOS/formatting or check
    puzzle clues. Cell accuracy compares only zipped characters after removing
    pipes, so truncated outputs can score 1.0 and an empty comparison is NaN.
    Average these per-example values for upstream-compatible aggregate metrics.
    """
    if not isinstance(hypothesis, str) or not isinstance(reference, str):
        raise TypeError("Official metrics require already-decoded strings.")
    cells = hypothesis.replace("|", "")
    reference_cells = reference.replace("|", "")
    matches = [left == right for left, right in zip(cells, reference_cells)]
    accuracy = sum(matches) / len(matches) if matches else float("nan")
    valid = False
    if len(cells) == 81 and cells.isdigit() and "0" not in cells:
        rows = [cells[start:start + 9] for start in range(0, 81, 9)]
        columns = ["".join(row[column] for row in rows) for column in range(9)]
        boxes = [
            "".join(rows[row][column] for row in range(br, br + 3)
                    for column in range(bc, bc + 3))
            for br in (0, 3, 6) for bc in (0, 3, 6)
        ]
        valid = all(sorted(unit) == list("123456789") for unit in rows + columns + boxes)
    return OfficialSudokuMetrics(hypothesis == reference, accuracy, valid)
