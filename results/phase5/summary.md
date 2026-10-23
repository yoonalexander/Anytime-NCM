# Phase 5: recorded-trajectory viewer and Concept Firewall bridge

**Complete — October 23, 2026.** Phase 4 was complete, with a practical-speedup no-go rather than an implementation blocker. The user explicitly requested Phase 5. This phase adds an inspection interface and saved-evidence interoperability, with zero model calls, fits, retuning or final-input materialization.

[Open the portable viewer](viewer.html) · [Completion receipt](completion.json) · [Build provenance](build.json) · [Declared scope](../../docs/phase5_scope.md) · [CF integration contract](../../docs/phase5_firewall_contract.md)

## Coverage and faithful display

| Saved study | Audited inputs | Recorded levels | Online timing shown |
| --- | ---: | ---: | --- |
| Hard Sudoku, Phase 1 | 1,400 | 16,800 | Unavailable per input; separate labeled development cohort estimates |
| Easy Sudoku, R3 / Phase 3 | 1,400 | 16,800 | 100 development inputs × 7 methods × 3 retained repeats |
| WMT14, Phase 4 | 192 | 2,112 | 64 development inputs × 4 methods × 3 retained repeats |
| Total | 2,992 | 35,712 | 2,868 existing online development requests |

Choose a study, partition, input and available stopping method. Search by dataset index or identity. Inspect any saved level with the level rail or keyboard-accessible slider. The viewer displays source, current reconstruction/issues, full-depth comparison, chosen exit, inspected levels, actual policy trace, all recorded timing repeats and run provenance.

Blue Sudoku cells changed from the previous recorded level; amber cells violate a supplied clue. Offline reference errors are distinct from current observations. WMT number/negation cues are literal heuristics, not semantic/factual truth labels. The source text is the released original; the actual 96-token-ID model prefix is inspectable.

Offline policy replay has no measured request latency. A measured cost is the selected method's total ready-output request, including its monitoring work, averaged over that input's three repeats. Separate cohort component-sum estimates never stand in for a selected input's measurement. No per-prefix measured timing is invented.

Continuation value remains **unavailable**: no continuation-value estimator was fitted. Existing Phase 3 sufficiency probabilities concern current correctness; CF probabilities concern eventual invalidity. Neither is substituted for continuation value.

## Saved-evidence Concept Firewall bridge

The actual local CF version-1 LevelState / LinearProbe interface and corrected saved run were inspected. Its producer predicts eventual hard-Sudoku final failure, not AI safety or language correctness.

The bridge checks upstream/checkpoint hashes, explicitly converts Anytime's 91-token-list identity to CF's canonical 81-clue-digit identity, then requires exact one-based level, all cumulative code groups and decoded-board equality. Batch settings differ (CF 8, original hard audit 128); identical weights alone would not justify attaching a score.

Of **3,468 candidate states on 289 overlapping audited puzzles, all 3,468 match exactly; zero mismatches are attached**. Only the producer's existing internal-test input_decoded and input_decoded_latent forecasts are retained. Unmatched states, easy Sudoku and WMT remain unavailable; level 12 is post-generation diagnosis. Failure outcome arrays are stripped before prediction JSON decoding and never enter the display or policy.

[Retained forecasts, coverage and external digests](firewall_bridge.json). The CF checkout was read only and is not imported by the viewer. No new probe predictions were generated. The forecast never changes an exit, acceptance decision or original result.

CF's original primary level-6 latent AUROC increment remains **−0.0078**, paired 95% interval **[−0.0368,+0.0193]**. This integration establishes display correspondence; it claims no new predictive, joint-policy, latency, recovery or safety benefit. The latent-family score remains the original CF forecast; bitwise latent-tensor or numeric probe-prediction parity across the two collection batch settings was not checked or claimed. These overlapping released data and consumed test subsets are not fresh confirmation.

## Verification

**433 tests pass**, including **29 new viewer regressions**, with no failures, errors or skips. [JUnit](tests.xml). Tests cover explicit identity conversion, mismatched/future-prefix boundaries, probability validity/coverage, label exclusion, repeated-timing fidelity, code/output correspondence, unavailable targets and safe HTML/script embedding.

The saved-data verifier checks source/artifact SHA256 values, all 2,992 original source/reference rows, all 35,712 reconstructions and diagnostics, every chosen exit, the original policy traces and all 2,868 measured timing records. With the CF argument, it reconstructs every exact join from the unchanged external files and compares the retained export. Fresh-process checks confirm no torch, NumPy, Transformers or sacreBLEU imports in the viewer module.

Phase 4's independent saved-data verifier still passes with its frozen sources and negative result unchanged. The prior current compatibility review is archived under results/phase1/reviews/2026-10-23-phase4c before refreshing it against the 433-test suite. Earlier empirical/completion artifacts remain unchanged.

[Browser checks](browser_checks.json) cover study/partition/sample/method selection, button/keyboard level control, three-repeat learned-policy timing, a real matched CF score, WMT rendering/cost, empty-search recovery and mobile geometry without horizontal overflow. No console errors/warnings were observed. The final served artifact exposes recorded configuration/hardware in provenance.

Direct file-URL navigation is blocked by the browser tool and was not automated. The self-contained HTML was verified over loopback; it embeds its data, scripts and styles, has no external assets/fetches, and can be retained as a portable artifact. The optional loopback server exposes only that single HTML, with other paths returning 404.

![WMT viewer](screenshots/wmt-desktop.png)

## Open and reproduce

Viewing or serving the committed artifact needs no weights, datasets, ML packages or internet:

~~~powershell
python scripts/view_trajectories.py serve
~~~

Open http://127.0.0.1:8765/. Stop the optional server with Ctrl+C. An alternate port can be selected with --port. The HTML is also the portable artifact.

Building/verification use standard-library Python (3.11+ recommended), original saved results and pinned local data; the CF checkout is needed only for recreating/external rechecking forecasts:

~~~powershell
python scripts/view_trajectories.py verify
python scripts/view_trajectories.py build --firewall-root ..\Concept-Firewall
python scripts/view_trajectories.py verify --firewall-root ..\Concept-Firewall
.\scripts\wsl_python.ps1 -PythonArguments @('-m','pytest','-q','-p','no:cacheprovider')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase4.py','verify')
~~~

Building without the optional CF argument produces explicit unavailable forecasts. It does not replace missing values with zero. Rebuilding is a saved-data transformation, not permission to rerun inference.

## Project stopping point

Phase 5's scoped deliverables are complete. The research studies still have no demonstrated practical adaptive-speedup advantage in their tested settings; Phase 0's hard-baseline paper-number discrepancy remains unresolved. A retrospective viewer does not resolve those scientific limitations. Further experiments, new hypotheses or live interventions require a new scope and suitable evidence.
