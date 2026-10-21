"""Synthetic correctness fixtures and parity with the pinned upstream scorer."""

import ast
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
import io
import math
from pathlib import Path
import warnings

import numpy as np
import pytest

from anytime_ncm.sudoku import (
    SudokuBoard, SudokuParseError, is_valid_solution, official_metrics,
    parse_board, validate_solution,
)


SOLUTION = (
    "534678912"
    "672195348"
    "198342567"
    "859761423"
    "426853791"
    "713924856"
    "961537284"
    "287419635"
    "345286179"
)
PUZZLE = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)
UPSTREAM = Path(__file__).resolve().parents[1] / "third_party/ncm"


@pytest.fixture
def solution():
    return parse_board(SOLUTION)


@pytest.fixture
def puzzle():
    return parse_board(PUZZLE)


@pytest.fixture
def tokenizer(monkeypatch):
    monkeypatch.syspath_prepend(str(UPSTREAM))
    from tokenization.sudoku_tokenizer import SudokuTokenizer
    return SudokuTokenizer()


def test_valid_solution_has_all_acceptance_flags(puzzle, solution):
    result = validate_solution(puzzle, solution, reference=solution)
    assert result.parseable and result.complete and result.grid_valid
    assert result.clue_consistent and result.reference_agreement
    assert result.is_valid_solution and is_valid_solution(puzzle, solution)
    assert result.parse_error is None


@pytest.mark.parametrize("render", [
    lambda board: board.to_text(),
    lambda board: board.to_text().replace("_", "0"),
    lambda board: " \n ".join(board.to_text()),
    lambda board: "<BOS>" + board.to_text() + "<BOS>",
    lambda board: "B" + board.to_text() + "B",
    lambda board: list(board.cells),
    lambda board: iter(board.cells),
    lambda board: board,
])
def test_parse_normalizes_supported_board_forms(puzzle, render):
    assert parse_board(render(puzzle)) == puzzle
    assert len(puzzle.to_text()) == 89
    assert puzzle.to_text().count("|") == 8


def test_real_upstream_tokenizer_prompt_and_decoded_output(puzzle, solution, tokenizer):
    tokens = [11] + tokenizer.encode(puzzle.to_text()) + [11]
    assert len(tokens) == 91
    assert parse_board(tokens) == puzzle
    output = [11] + tokenizer.encode(solution.to_text()) + [11]
    assert parse_board(tokenizer.decode(output, skip_special_tokens=True)) == solution
    assert is_valid_solution(tokens, output)


def test_bos_removal_matches_upstream_at_non_boundary_positions(solution, tokenizer):
    tokens = tokenizer.encode(solution.to_text())
    tokens.insert(5, 11)
    assert parse_board(tokens) == parse_board(tokenizer.decode(tokens, skip_special_tokens=True))


def test_numpy_integer_token_ids_are_supported(puzzle):
    assert parse_board(np.asarray(puzzle.cells, dtype=np.int64)) == puzzle


def test_blank_cells_remain_parseable_and_clue_consistent(puzzle, solution):
    result = validate_solution(puzzle, puzzle, reference=solution)
    assert result.parseable and result.clue_consistent
    assert not result.complete and not result.grid_valid
    assert result.reference_agreement is False
    assert not result.is_valid_solution


@pytest.mark.parametrize("bad", [
    "", SOLUTION[:-1], SOLUTION + "1", SOLUTION.replace("5", ".", 1),
    SOLUTION.replace("5", "\u0665", 1), "<bos>" + SOLUTION,
    "|".join([SOLUTION[:9]] * 8), "|" + SOLUTION,
    SOLUTION[:8] + "|" + SOLUTION[8:],
    [0] * 80, [0] * 82, [True] + [0] * 80,
    [1.0] + [0] * 80, ["1"] + [0] * 80,
    [12] + [0] * 80, [-1] + [0] * 80,
    [None] + [0] * 80, [[0] * 9] * 9, None, 123,
])
def test_malformed_candidate_is_never_accepted(puzzle, solution, bad):
    with pytest.raises(SudokuParseError):
        parse_board(bad)
    result = validate_solution(puzzle, bad, reference=solution)
    assert not result.parseable and result.board is None
    assert not result.complete and not result.grid_valid and not result.clue_consistent
    assert result.reference_agreement is False
    assert result.parse_error
    assert not is_valid_solution(puzzle, bad)


def test_misplaced_separators_are_not_silently_removed(puzzle, solution):
    malformed = "|" + solution.to_text()[1:]
    # Removing all pipes would still leave the wrong cell count here.
    assert not validate_solution(puzzle, malformed).parseable
    wrong_geometry = solution.to_text().replace("|", "", 1)
    wrong_geometry = wrong_geometry[:8] + "|" + wrong_geometry[8:]
    assert len(wrong_geometry) == 89
    assert wrong_geometry.replace("|", "") == SOLUTION
    assert not validate_solution(puzzle, wrong_geometry).parseable
    assert official_metrics(wrong_geometry, solution.to_text()).valid_grid


@pytest.mark.parametrize("swap", [(0, 9), (0, 1)])
def test_row_or_column_corruption_rejected_even_when_boxes_preserved(solution, swap):
    cells = list(solution.cells)
    left, right = swap
    cells[left], cells[right] = cells[right], cells[left]
    result = validate_solution("0" * 81, cells)
    assert result.parseable and result.complete and result.clue_consistent
    assert not result.grid_valid and not result.is_valid_solution


def test_latin_square_rejected_for_invalid_subgrids():
    latin = [(row + column) % 9 + 1 for row in range(9) for column in range(9)]
    digits = set(range(1, 10))
    assert all(set(latin[start:start + 9]) == digits for start in range(0, 81, 9))
    assert all(set(latin[column::9]) == digits for column in range(9))
    result = validate_solution("0" * 81, latin)
    assert result.complete and not result.grid_valid and not result.is_valid_solution


def test_valid_grid_can_corrupt_puzzle_clues(puzzle, solution):
    alternative = SOLUTION.translate(str.maketrans("12", "21"))
    result = validate_solution(puzzle, alternative, reference=solution)
    assert result.complete and result.grid_valid
    assert not result.clue_consistent and not result.is_valid_solution
    assert not result.reference_agreement
    assert official_metrics(alternative, SOLUTION).valid_grid


def test_distinct_solution_is_valid_for_a_nonunique_puzzle(solution):
    puzzle = SOLUTION[:9] + "0" * 72
    # Exchange two rows within one band, keeping the fixed first row intact.
    alternate = SOLUTION[:9] + SOLUTION[18:27] + SOLUTION[9:18] + SOLUTION[27:]
    assert alternate != SOLUTION
    result = validate_solution(puzzle, alternate, reference=solution)
    assert result.is_valid_solution and result.clue_consistent
    assert result.reference_agreement is False
    official = official_metrics(alternate, SOLUTION)
    assert not official.solved and official.valid_grid


def test_reference_agreement_is_cell_based_not_format_based(puzzle, solution):
    result = validate_solution(puzzle, SOLUTION, reference=solution.to_text())
    assert result.reference_agreement is True and result.is_valid_solution
    assert not official_metrics(SOLUTION, solution.to_text()).solved


def test_reference_is_optional(puzzle, solution):
    assert validate_solution(puzzle, solution).reference_agreement is None
    assert validate_solution(puzzle, "").reference_agreement is None


@pytest.mark.parametrize("bad_puzzle", ["", "11" + "0" * 79, "1" + "0" * 8 + "1" + "0" * 71])
def test_invalid_puzzle_is_a_caller_error(bad_puzzle, solution):
    with pytest.raises(ValueError):
        validate_solution(bad_puzzle, solution)


@pytest.mark.parametrize("bad_reference", ["", PUZZLE, "1" * 81, SOLUTION.translate(str.maketrans("12", "21"))])
def test_invalid_reference_is_a_caller_error(puzzle, solution, bad_reference):
    with pytest.raises(ValueError):
        validate_solution(puzzle, solution, reference=bad_reference)


def test_board_storage_is_immutable_and_validated(solution):
    source = list(solution.cells)
    board = SudokuBoard(source)
    source[0] = 0
    assert board == solution
    with pytest.raises(FrozenInstanceError):
        board.cells = (0,) * 81
    with pytest.raises(SudokuParseError):
        SudokuBoard((10,) + (0,) * 80)
    with pytest.raises(SudokuParseError):
        SudokuBoard((0,) * 80)


def test_official_cell_metric_preserves_truncation_and_empty_semantics():
    assert official_metrics(SOLUTION[:1], SOLUTION).cell_accuracy == 1.0
    assert not official_metrics(SOLUTION[:1], SOLUTION).valid_grid
    assert math.isnan(official_metrics("", SOLUTION).cell_accuracy)


def test_official_metric_requires_already_decoded_strings():
    with pytest.raises(TypeError):
        official_metrics([1] * 81, SOLUTION)


@pytest.mark.parametrize("hypothesis", [
    SOLUTION, "|".join(SOLUTION[start:start + 9] for start in range(0, 81, 9)),
    SOLUTION[:-1], SOLUTION[:1], "", PUZZLE.replace("0", "_"),
    SOLUTION.translate(str.maketrans("12", "21")), "1" * 81,
])
def test_metrics_match_actual_upstream_scoring_function(hypothesis):
    # Extract only the pure Sudoku scorer, avoiding eval_merge's CLI/file I/O.
    source = ast.parse((UPSTREAM / "scripts/eval_merge.py").read_text(encoding="utf-8"))
    exact = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == "exact")
    scorer = ast.Module(body=[exact], type_ignores=[])
    namespace = {"np": np, "hyps": [hypothesis], "refs": [SOLUTION]}
    exec(compile(scorer, "upstream Sudoku scorer", "exec"), namespace)
    output = io.StringIO()
    with warnings.catch_warnings(), redirect_stdout(output):
        warnings.simplefilter("ignore", RuntimeWarning)  # Upstream empty-mean behavior.
        namespace["exact"]()
    solved, count, cells, valid = output.getvalue().splitlines()[-1].split()
    result = official_metrics(hypothesis, SOLUTION)
    assert float(solved) == 100 * result.solved
    assert count == f"{int(result.solved)}/1"
    assert float(valid) == 100 * result.valid_grid
    expected_cell_percent = float(f"{100 * result.cell_accuracy:.2f}")
    assert (math.isnan(float(cells)) and math.isnan(expected_cell_percent)) or float(cells) == expected_cell_percent
