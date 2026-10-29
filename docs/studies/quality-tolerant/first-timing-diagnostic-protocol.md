# Phase09T: first actual controller-versus-full timing diagnostic

Prospective October29,2026. [Numeric lock](first-timing-diagnostic-lock.json), [source lock](first-timing-diagnostic-source-lock.json), [quality evaluation and preserved failure](development-evaluation-results.md). The selected cheap19/8-only ridge controller is unchanged from pushed993180f. It fails allocated1188-input BLEU point tolerance(.664892>.5). Phase09completed native cache but failed terminal environment serialization; full reservation remains charged. Phase09Rverified1193saved traces/reported original corpus points without inference. No actual controller timing occurred. This diagnostic characterizes actual speed of the already quality-failing rule; it cannot rescue that failure or establish useful matched-quality speedup.

## Justification and preserved incompletion

The original1188x12methodsx2repeatsx2sessions timing matrix remains incomplete. Full failure charge leaves1808.461CPU seconds. Prior phase05actual4968requests used477.788combinedCPU seconds; original57144timingrequests cannot reasonably fit the remaining allowance. No refund or budget reset is allowed. The phase09Rprotocol declared a possible first controller/nativefull timing diagnostic BEFORE its quality scores were computed. The fixed comparator is the original pushed11, not an outcome-selected replacement.

Retain ALL1188inputs/60components and actual causal policy, but compare only controller/nativefull in2separate processes with1timed repeat per input/method/session and5warmups/method/session.4772real requests total(4752timed+20warmups),0synthetic NN attempts. This smaller diagnostic is a separately bounded alternative, not completion of the original matrix. Fixed1-10timings and within-session repeat variability remain unmeasured; none is statistically excluded. Existing12corpus quality POINTscores are retained, not recomputed. No new policy, fit, threshold, data extension, outcome population or confirmation follows. Negative quality status is fixed regardless of timing outcome.

## Access, runtime and measurements

Use phase09already-released evaluation entries/private source cache and phase09Rhashes/current8vectors/expected exits. Workers each materialize1188sources;0references/trajectories/newSGMLpayloads/tokenizertraining/targets. All confirmation/E3/E4/unallocated bodies remain sealed. Same strict adapter and validated joint_request callback: at8decode current prefix, compute19cheapfeatures and predict once, stop8or directly11; no10observation or extra logits/literal cues. Cached expected depth is used only for work validation, never passed to the controller. Full11uses native stock generation.

Reuse original model_context for pinned float32/eval/CPU4/TF32settings, all96-prefix identity checks and initial/final state fingerprints. Normalize ONLY its torch-version string through the now tested native_environment helper, then durably save environment/start/state-before receipt BEFORE any request. Save all starts/completions/errors; terminal receipt normalization must work on both paths. Two workers must have distinctPIDs and identical unchanged state hashes. No replacement receipt for the original missing cache state/resource fields.

Deterministic paired order(seed20261029+session), year/index identities carried throughout. Warmups from first16inputs. Time complete ready-output wall before tokenization/context/generation/reconstruction/decoding/transfers/currentfeatures/scalarprediction through final CUDA synchronization; loading/seeds/validation/hashes/logging outside. [PyTorch2.10](https://docs.pytorch.org/docs/2.10/generated/torch.cuda.synchronize.html) synchronization behavior remains the source. Record separate CUDA stream span, actual depths/visits, per-forward counts, every observed output/current generated8prefix,19cheapfeature parity and8unusedzeros, GPU peaks. Current-feature tolerance unchanged rtol1e-5/atol1e-6. No new reference score or quality inference.

## Paired summaries and fixed decision

Require complete2x1188x2timing cells. Report actual mean/median/p95/both session means and ratio1-controller/full. Average the two observed session values per input, resample all60whole components20,000times with shared indices/seed20261029, sum input totals then ratio. Retain original conservative nominal tail.05/22 and Monte Carlo family11/rank-error.001even though ONLY ONEcontrast is observed; do not fabricate10contrasts. [Field-Welsh2007](https://academic.oup.com/jrsssb/article-abstract/69/3/369/7109361) model-dependent bootstrap limitations still apply. Intervals are conditional nominal, require suitable independent/exchangeable components, and do not cover hardware/session population or all temporal dependence. One repeat removes within-session repeat information.

Separately record whether actual mean saving>=5%, both sessionspositive and retained paired lowerbound>0. Final controller status remains negative_quality_point_screen because frozen BLEUfails. Timing success would establish only measured speed of a quality-failing development rule. Original contract remains unestablished; Q0notpassed, potentially feasible fixeddepth comparisons lack support, original fullmatrix incomplete. After this diagnostic, perform existing-evidence confirmation-readiness audit and final closeout. NOmore models/fits/data rescue, whatever timing says.

## Tests, caps and stopping

Freeze/push before3pure synthetic cases or models: exact complete paired2386requests/session, year/index routing and work caps; unequal component input weights/null/5%boundary/invalidcases using FIXEDarrays (noMonteCarlo); normalize full worker initial/failure receipt before requests. Original phase09fiveNNtests and phase09RactualTorchVersiontests remain preserved; no needless repeat of model work. This diagnostic changes scheduling/reporting, reuses the same validated runtime and reports no new whole-suite result.

Perworker<=2386requests/26246generatorlevels/3579decodes/0encoders;1193cheap/decision calls,0addedlogit/cuecalls. Total<=4772requests/52492levels/7158decodes;7148prefixcalls incl2376prechecks;2checkpointloads. Exactly20kpaired timing draws once.0newcorpus/reference score, target, fit, family, download or paid dollar.

Wall2400sec; realmodelorchestration2000sec; testwall90sec/hard20CPUsec. Each worker hard450CPUsec plus per-request/completion checks; parent own100sec; combined execution<=1020CPUsec plus50reporting/verification credit. RSSparent2GiB/worker16GiB, GPU<=8GiBANDphysicaldevice, publicartifacts32MiB. Reservation1070CPUsec leaves738.461for final closeout even if full charged; no prior charges reduced.0retries. Resource/state/parity/work/environment/access/test failure stops and preserves partial evidence/fullreservation, no restart. Watch/poll SAMElivehandle through observation timeouts.

Archive sources/plans/receipts and verify saved records without new inference/scoring/resampling. Commit/push completed results/main equality. Original failures, fullcharges and missing receipts remain explicit.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_first_timing_diagnostic.py','run','--commit','PUSHED_LOCK_COMMIT')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_first_timing_diagnostic.py','verify')
~~~
