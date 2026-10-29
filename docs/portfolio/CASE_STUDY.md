# Anytime NCM — testing when coarse answers are worth returning

**Question.** Can a frozen coarse-to-fine generator stop at a different depth for each input and save real time while preserving output quality?

**Approach.** Build full-resolution prefix reconstruction, verify intermediate and final parity, expose an online stopping callback and compare against full depth and fixed-depth controls. Separate current-state features from offline references and future outputs. Audit Sudoku with exact constraints and translation with corpus metrics. Freeze experiments, data roles, budgets and policies before outcome access; preserve failures and inconclusive gates.

**Result.** The final frozen translation rule stopped early on 315 of 1,188 development-evaluation inputs and saved **5.08% actual mean ready-output time** (127.872 ms versus 134.710 ms full). Its **0.665 corpus BLEU loss exceeded the 0.5 tolerance**, so the combined research target failed. The paired timing interval [3.38%, 6.86%] is conditional on the recorded sessions and component assumptions; no independent quality assurance follows.

**What made the engineering difficult.** Correct cumulative-prefix reconstruction required the released learned transformations, not simple truncation or interpolation. Offline early outputs save no generator work. Observations, reconstruction, decoding, transfers and decisions all consume time. Per-input reference-informed opportunities are not deployable online policies, and repeated timing runs do not add quality samples.

**Limitations retained.** The smaller final timing diagnostic compared only controller/full; the full original matrix was not completed after a preserved reporting failure. Fixed-depth frontier and statistical confirmation remain unestablished. Original missing terminal resource/state receipts remain unavailable. Reserved outcomes stay sealed. These findings apply to the tested checkpoints, rules, populations and schedules.

**Useful deliverables.** Prefix adapters, exact/heuristic validation with clear boundaries, causal stopping hooks, source-locked evidence, a portable historical viewer, dependency-free aggregate inspection, clean-install distributions and reproducible saved-evidence audits.

**Engineering validation is separate from scientific effectiveness.** Passing reconstruction/software/install tests does not turn a quality-failing controller into a successful research result. A bounded negative result with inspectable evidence is the project contribution.

[Repository](https://github.com/yoonalexander/Anytime-NCM) · [Research snapshot](https://github.com/yoonalexander/Anytime-NCM/releases/tag/research-v0.1.0) · [Final outcome](../PROJECT_OUTCOME.md) · [Asset guide](ASSETS.md) · [Website copy](WEBSITE_COPY.md).
