# R1A: saved Sudoku prefix error diagnosis

**Declared:** October 22, 2026 (America/Toronto), before computing the new error taxonomy.
**Study:** R1A / sudoku_prefix_diagnosis.
**Empirical input snapshot:** `c1fce9311998e2d7ae9609c1e34b0c6949d6a256`.
**Scope:** A deterministic, descriptive analysis of existing exploration trajectories. No new inference, profiling, downloads, controller fitting, or final-holdout access. R1B is not included.

## Inputs and access

Use all 1,000 exploration identities in the unchanged frozen manifest, including the 32 original smoke identities. Load puzzle/reference rows through the existing selective reader with exactly `{"exploration": 1000}`. The source JSONL also contains 400 development records: traverse its lines in the original manifest-selected order and skip development lines before JSON deserialization. The file checksum covers all bytes, but development trajectories do not enter this analysis. Holdout rows remain unmaterialized.

Required source hashes:

| Input | SHA-256 |
| --- | --- |
| Original full trajectory JSONL | `2baf2948df953d7f379f9b359091c9a40d31fe9ecafe29f99305ff8bb3e0f5d9` |
| Collection metadata | `c873d0f584173cbdf17e0b19f787a41a512a8db2170e45a0a01fe4a6543df342` |
| Original analysis JSON | `f07902170491118523d2038339f635b260561a227b8658753e2a83fdc8236f67` |

Protocol and manifest hashes remain those in the original frozen study. Validate every selected record using the existing saved-record validator. Compare the independently recomputed exploration primary-valid counts, first-valid histogram, never-valid count, and valid-to-invalid transitions against the original analysis before interpreting new summaries. Any mismatch stops the analysis.

## Board metrics

The observation grain is one puzzle at one of 12 levels: 12,000 exploration states. For parseable boards, compare all 81 cells with the valid supplied reference. Report exact integer histograms plus count, sum, mean, median, p90, p95, min, max, and zero/positive counts for each metric. Quantiles use linear interpolation at (n−1)×q. Explicitly report undefined coverage; never replace an unparseable board with zero errors.

- Wrong-reference cells include blanks (0 differs from the nonzero reference).
- Split wrong cells and blanks into given-clue positions and originally empty positions. Clue violation means the candidate differs from a supplied clue, including a blank at that clue.
- Report wrong-filled cells separately from blanks. Given/empty are disjoint position sets; blanks are a subset of wrong-reference cells.
- For each of rows, columns, and boxes, count invalid units, units containing a blank, duplicate nonzero-digit units, duplicate excess, and missing digits.
- A unit is invalid unless its sorted values equal digits 1–9. Blanks therefore make a unit invalid and create missing digits, but do not create duplicate-digit counts.
- Duplicate excess is the number of filled values minus the number of distinct nonzero values. Missing digits is 9 minus the number of distinct nonzero digits.
- Sum invalid units and duplicate excess over all 27 units. Report the union of cells taking part in a repeated nonzero digit as a separate conflicting-cell count.
- Row, column, box, clue, blank, and reference-error categories can overlap. Their counts are not an additive decomposition of all mistakes. Duplicate excess summed across unit families can count the same offending cell more than once.

Pooled reference-error rates divide total wrong cells by total parseable cell opportunities (81 per board). Given-cell and empty-cell rates use their own summed position denominators; do not average percentages with unequal denominators. Unit distributions have 9 units per family and 27 overall.

## Adjacent-level changes

The observation grain is one puzzle at one of 11 boundaries: 11,000 transitions. Report:

- Changed cells.
- Corrected cells: wrong relative to reference before, correct afterward.
- Corrupted cells: correct before, wrong afterward.
- Wrong-to-different-wrong cells: wrong at both levels with different values.
- Stable-correct and stable-wrong cells, plus blanks filled and blanks created.
- The changed/corrected/corrupted/wrong-to-different-wrong counts separately at given and empty positions.

Check exactly that changed = corrected + corrupted + wrong-to-different-wrong, and wrong_after = wrong_before − corrected + corrupted. Blank fill/creation overlaps these categories. Transitions involving an unparseable endpoint have undefined cell metrics and explicit coverage. No transition is a model call or a timing observation.

## Groups and examples

Summarize every level and boundary for all exploration inputs, final-primary-success inputs, and final-primary-failure inputs. Membership uses the final independently checked primary verdict and is retrospective. These groups and all reference-based metrics are diagnostic labels, not permitted stopping inputs. Show levels 10–12 and boundaries 10→11 and 11→12 prominently; retain all levels/boundaries in machine-readable outputs.

Choose the lowest dataset index satisfying each category, independently (a puzzle may serve multiple categories):

1. Early primary success at any level 1–11.
2. Final primary success.
3. Final primary failure.
4. A reference-correct cell becoming wrong at any boundary.
5. A clue violation at level 11 followed by final primary success.
6. A complete, clue-consistent, grid-invalid output at level 12.

Save actual boards at levels 10–12 and the example's metrics. Mark absent categories explicitly; do not broaden category definitions after seeing results.

## Deliverables and verification

Write a fresh directory under `results/followup/`: analysis JSON, 12,000-row board-metric CSV, 11,000-row transition CSV, Markdown summary, standalone scientific PNG figures, and input/source/output hashes with access counters. Reject an existing output directory. A verification mode recomputes machine-readable results and validates all artifact/source hashes without inference.

Use focused fixtures with independently known error counts, blanks, duplicate overlap, clue corruption, every transition category, variable clue denominators, malformed outputs, exact quantiles, absent categories, and reader access rejection. Run the full implemented test suite. Visually inspect the scientific figures. Keep empirical Phase 1 artifacts and historical completion records unchanged. If the current repository/navigation audit must be refreshed, archive its prior record/JUnit bytes first, record the new date, and distinguish that compatibility check from R1A's exploration-only analysis.

## Interpretation and stopping

Findings are descriptive, not causal or held-out policy results. Retain hypotheses about tokenizer/decoder limitations and generated-code errors as hypotheses. Use the results to refine the already proposed 32-input R1B target-encoding diagnostic; do not execute it. Preserve the original hard-Sudoku no-go and zero online-latency measurements. End R1A after its report, verification, documentation update, commit, push, and remote-ref check.
