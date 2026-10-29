# Campaign phase04: fixed joint-risk controller selection

Prospectively frozen October29,2026, after the [phase03 discrimination result](signal-discrimination-results.md), before new synthetic tests or this selection's calibration outcome reads. [Numeric lock](joint-controller-selection-lock.json), [source lock](joint-controller-selection-source-lock.json), [campaign authority](campaign-20261029-objective.md). This is family1continuation,0new fits/requests, not a third controller family or independent confirmation. Q0 and prior failed gates remain failed.

## Fixed access and candidate family

Only101old calibration trajectory/reference bodies are released using immutable controller-split.json. Read366previous phase03 compact feature records (361fit/calibration inputs plus5warmups), select101nonwarm calibration records for replay. Do not open the87evaluation bodies or E3/E4/unallocated outcomes. Previous calibration selection, sentence labels and diagnostic results are consumed development exposure; no held-out inferential claim follows. Existing source/checkpoint/document provenance remains unchanged.

Reuse the4fixed phase03binary joint-risk ridge models, with their training-only means/scales and penalty10, without refitting. Compare cheap19and selected_logit27feature groups. For each group use decision schedules[8]or[8,10], followed by11fallback; thresholds0,.1,.2,.3,.4,.5,.6,.7,.8,.9(shared at both levels); literal cue guard off/on. Exactly80adaptive candidates plus native-full fallback if all models exist. Skip model-dependent schedules if a required fit was unsupported; never fabricate an all-zero cue head. The richer8probe qualified; richer10did not, so including10is exploratory and all its failed candidates must be retained. Threshold scores are not calibrated probabilities.

At each scheduled observation, exit iff joint score<=threshold and, when enabled, current source-number-set equality and source/current negation-cue agreement both equal1. These causal guards are heuristic vetoes, not replacements for the reference-defined corpus endpoints or learned protection against unseen negation-change events. Feature history at10requires actual earlier8inspection; a10-only schedule would need different features/models and is not included. An8-only policy never inspects10. Full fallback has no early observations.

## Endpoints, comparisons and selection

For every candidate replay all101inputs using saved current/past features, then compute actual CORPUS BLEU/chrF, numeric-reference mean F1 on the unchanged defined-reference denominator, and negation mismatch on the selected text. Apply original full-relative POINT tolerances .5/1/.02/.02 using the existing implementation's1e-10numeric boundary allowance. These consumed point scores do not establish quality uncertainty bounds. No per-sentence proxy substitutes for a corpus score.

Retain corpus points for all11fixed depths. Lock the fastest point-passing fixed depth as the named development comparator; do not claim adjusted quality exclusion for any other fixed depth. Any later actual benchmark must include native full and all11fixed controls. No test-driven comparator replacement.

Cost model: prior actual fixed-depth mean plus(extra observations)*2.1456159247680517ms, the frozen original observation proxy, plus.5ms per decision for selected_logit or for any cue-guard candidate. The.5ms rounds up the previous selected bundle's approximately.43ms/decision synchronous component average; it is a development approximation, not a bound, isolated cue cost or validated online decision latency. Cheap unguarded candidates add0extra-feature surcharge. The scalar model-decision cost is unmeasured/0in this proxy; actual evaluation must pay it and every other online operation. Also report optimistic terminal-only means with zero extra observation/feature cost; these are sensitivity estimates, not proven speedup upper bounds.

Select the point-passing candidate with minimum estimated mean cost, tie by lexical name, including full fallback. Its separately locked evaluation branch is ready only if selected policy is adaptive AND estimated saving>=5%versus the prior fixed11mean. This heuristic gates spending; it is not proof of actual benefit. Otherwise preserve the negative selection result and prospectively review only a justified bounded family2/data alternative or closeout. Do not repeatedly adjust thresholds after inspecting results or auto-open87evaluation bodies. Even a passed selection gate requires policy/comparator push BEFORE separately locked actual evaluation.

All81candidate and11fixed comparisons are descriptive development selection. No p-values, bootstrap, multiplicity-adjusted quality inference or independent confirmation. No paired ready-output claim can be made without actual paired execution. Endpoint/multiplicity/dependence/coverage/power requirements for confirmation remain as in failed Q0 unless a defensible separately locked design actually resolves them.

## Numeric limits, stopping and delivery

Caps:101trajectory bodies,101reference strings,366saved feature records,8181policy-input replays,12120decision calls,91corpus metric calls,81candidate specs,11fixed points.0source string materializations,0new model requests/checkpoint loads/encoders/target encodings/fits/families/downloads/paid dollars/confirmation.7focused synthetic cases,0toy fits/model calls. CPU<=1200execution seconds +300reporting/verification credit; wall<=1800sec, tests<=120sec, parentRSS<=2GiB, artifacts<=64MiB. Shared campaign accounting remains binding. No retries; access/schema/source/resource failure stops this phase and charges conservative reservation with failed evidence preserved.

Archive source, test before released access, preserve all candidates and policy, source digests, ledgers and decisions under results/quality_tolerant/campaign_20261029/joint_controller_selection/. Update the roadmap/report without altering previous phases. Commit/push selection and verify live equality before any evaluation access.

After this protocol/implementation lock is pushed:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_joint_controller_selection.py','run','--commit','PUSHED_LOCK_COMMIT')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_joint_controller_selection.py','verify')
~~~

Saved verification must perform no inference/refitting. The once-only run cannot be repeated. Primary metric/ridge/ranking references are linked in [phase03protocol](signal-discrimination-protocol.md) and the unchanged [diagnostic report](controller-diagnostic-results.md); no new statistical guarantee is introduced here.
