# Phase 1A: Sudoku parsing and correctness

**Completed:** October 20, 2026.
**Scope:** Sudoku parsing, independent solution validation, official metric compatibility, and focused tests.

## Public API

The implementation is in [sudoku.py](../src/anytime_ncm/sudoku.py) and uses only the Python standard library.

| API | Contract |
| --- | --- |
| `parse_board(value)` | Return an immutable, row-major `SudokuBoard`, or raise `SudokuParseError` |
| `validate_solution(puzzle, output, reference=None)` | Return separate candidate flags; the optional reference is diagnostic |
| `is_valid_solution(puzzle, output)` | Accept only a parseable, complete, grid-valid, clue-consistent candidate |
| `official_metrics(hypothesis, reference)` | Return per-example official decoded-text solved/cell/valid-grid values |

`reference` is a keyword-only argument to `validate_solution`. Reference answers and official scoring are evaluation diagnostics, not stopping-policy inputs.

## Parsing contract

- Accept flat integer token iterables, upstream-decoded text, or a `SudokuBoard`.
- Accept either 81 flat cells or nine rows of nine cells separated by eight correctly placed pipes.
- Token `0` is blank, `1..9` are digits, `10` is a row separator, and `11` is BOS.
- Text accepts blanks as `_` or `0`, whitespace, `<BOS>`, and upstream's `B` shorthand.
- Remove BOS wherever upstream's `skip_special_tokens=True` removes it, including the two boundary tokens of a 91-token puzzle prompt.
- Upstream has no integer PAD/EOS token IDs for Sudoku. Unknown IDs, None, floats, booleans, unknown characters, bad lengths, and bad separator geometry are rejected.
- NumPy integer arrays can be supplied directly. Tensor callers must explicitly convert to a flat integer list; the validator imports no Torch or model code.

The parser does not infer missing cells, repair separators, or discard arbitrary characters.

## Validation contract

Candidate flags are `parseable`, `complete`, `grid_valid`, `clue_consistent`, and optional `reference_agreement`.

A malformed candidate returns false acceptance flags and a parse error. An 81-cell board containing blanks can be parseable and clue-consistent while remaining incomplete and grid-invalid. A complete valid grid can still fail clue consistency.

Malformed or locally conflicting puzzle clues raise ValueError, because they are caller/input-data errors. If supplied, the reference must be a complete valid solution preserving the clues. Local clue checks do not solve a puzzle or establish uniqueness.

Reference agreement compares normalized cells. A different solution of a nonunique puzzle remains acceptable when complete, grid-valid, and clue-consistent.

## Official metric compatibility

Official metrics intentionally operate on already-decoded strings without parser normalization or clue checks. Exact text equality determines official solved status. Cell accuracy removes pipes and compares zipped characters; a matching truncated prefix can score 1.0, and an empty comparison produces NaN. Official valid-grid scoring removes pipes and checks row/column/box digits but does not inspect puzzle clues.

These rules are preserved for comparability and must not be used as the primary solution-acceptance rule. No existing baseline output was rescored as part of Phase 1A.

## Verification

Command, from the repository root in PowerShell:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests/test_sudoku_validator.py', '-q', '-p', 'no:cacheprovider')
```

Observed result: **59 passed in 0.64 seconds**, using the validated WSL Python 3.12 environment. Explicit argument forwarding prevents the Python `-p` option from colliding with the helper's PowerShell parameter name. The pytest cache is disabled for the Windows-mounted checkout.

[Test fixtures](../tests/test_sudoku_validator.py) cover supported text/token forms, the actual upstream tokenizer, malformed/incomplete outputs, row/column/box violations, clue corruption, invalid caller data, immutable storage, and a valid non-reference solution. Metric parity tests execute only the actual pinned upstream Sudoku scoring function extracted from its syntax tree, avoiding the evaluator's CLI and file I/O.

[Machine-readable completion evidence](../results/phase1/phase1a_validation.json) records the test result and source hashes. Fixtures are synthetic. The only dataset inspection was the token structure of the first exploration input; no holdout predictions/references were inspected and no model inference was run.

## Boundary

Phase 1A is complete. Phase 1B partial decoding, Phase 1C collection, Phase 1D profiling/reporting, generation changes, and learned policies remain pending. The frozen protocol, manifest, checkpoints, upstream checkout, and original baseline records are unchanged.
