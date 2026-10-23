# Concept Firewall bridge v1: recorded forecasts

The Phase 5 bridge consumes the actual local Concept Firewall implementation, not a hypothetical safety service. Producer: corrected collection 20261021T015216719695Z-collection and probes 20261021T015457393177Z-probes.

## Actual producer interface

Concept Firewall's src/concept_firewall/schema.py defines immutable LevelState (run_id, puzzle_id, trajectory_id, one-based level, codes_prefix, predicted_board, optional pooled_latent). Its probes.py LinearProbe.predict_failure_probability(state, puzzle) uses representations.extract_features on that exact state. The target is eventual final Sudoku invalidity. Version-1 JSON probe files and per-level test_predictions JSON already exist. No network API or general language-risk interface exists in the inspected implementation.

This bridge reads those saved forecasts. It does not call the probe, import CF modules, execute checkpoint/pickle objects, copy pooled activations, fit a model, or modify either project's inference. CF source/manifest/prediction/observation hashes are retained in firewall_bridge.json; probabilities are attached only for observed matching states.

## Matching contract

1. Both runs must identify the same upstream revision and generator/tokenizer SHA256 hashes.
2. Anytime identities hash the 91-token puzzle list; CF identities hash the canonical 81 clue digits. Parse the actual puzzle, canonicalize it and hash the ASCII digits. Never join by row number or assume the identity hashes coincide.
3. Require CF feature version sudoku-full-prefix-v2, equal canonical identity, one-based level, every cumulative code group and exact decoded board. Collection batch sizes differ; checkpoint equality alone is insufficient.
4. Consume only the existing CF internal-test forecasts intersecting Anytime's audited hard-Sudoku exploration/development identities. Keep only input_decoded and input_decoded_latent, the producer's predeclared primary comparison families. Probabilities must be finite in [0,1]; duplicate/missing forecast states and incompatible checkpoint metadata fail validation. Individual observed-state mismatches are counted and withheld.
5. Outcomes are separate: the prediction file's failure array is stripped before JSON decoding; it never enters the bridge or viewer. Other CF state bodies are skipped by puzzle ID before decoding. No NCM final-subset puzzle/reference rows are materialized.
6. Missing risk is null/unavailable, never zero. Easy Sudoku and WMT have no compatible forecasts. Level 12 is post-generation diagnosis, not a useful early warning.

Export schema: schema_version, producer_run, target, families, external_sources (relative CF path → SHA256), forecasts (Anytime identity → one-based level → family → probability), coverage/rejection counts and limitations. The viewer uses these read-only observations alongside the original policy. A risk score never changes an exit or an acceptance label.

## Interpretation and validation

CF's recorded primary level-6 comparison is negative: latent addition AUROC increment -0.0078, paired 95% interval [-0.0368,+0.0193]. The original report also disclaims intervention, conditional recovery, speedup and safety effectiveness. The viewer preserves that result; it does not re-evaluate or select probes.

Bridge validation establishes schema correctness, checkpoint/identity/prefix/output correspondence, forecast copying and unavailable-state handling. It makes no new predictive or joint policy benefit claim. These are overlapping public test data with distinct internal partitions; they are not fresh confirmation. Displayed probabilities are producer-calibrated estimates with no population guarantee. Sufficiency probabilities from Anytime Phase 3 estimate current correctness; they are a different target from CF eventual failure. Neither is a fitted continuation-value estimate.

## Reproduction

The committed portable HTML opens without either checkout's ML environment. Building requires the pinned local datasets and original recorded artifacts; CF is needed only to recreate/externally recheck forecasts:

~~~powershell
python scripts/view_trajectories.py build --firewall-root ..\Concept-Firewall
python scripts/view_trajectories.py verify --firewall-root ..\Concept-Firewall
python scripts/view_trajectories.py serve
~~~

Open http://127.0.0.1:8765/ or directly open results/phase5/viewer.html. The optional server binds loopback and serves only that single artifact. Building without --firewall-root yields explicit unavailable forecasts; it does not fabricate scores. Verification without that argument checks the retained export and viewer/source digests, without requiring CF to be installed.
