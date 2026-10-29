# Phase04 fixed-model selection: below the spending gate

October29,2026. **The best richer-feature rule exits23/101consumed calibration inputs at level8, meets all original corpus POINT margins, and projects4.289%savings.** This improves on the earlier full-only selection, but misses this phase's prospectively locked5%estimated-saving gate. No87-input evaluation or new model request/fit occurred. Actual controller latency and quality generalization remain unresolved.

[Protocol](joint-controller-selection-protocol.md), [numeric lock](joint-controller-selection-lock.json), [source lock](joint-controller-selection-source-lock.json). Lock58d11d7d8514b4378dcb6e869078c08d1a28a0d1 pushed before tests/selection. [Candidate results](../../../results/quality_tolerant/campaign_20261029/joint_controller_selection/candidate-results.json), [frozen policy](../../../results/quality_tolerant/campaign_20261029/joint_controller_selection/policy.json), [decision](../../../results/quality_tolerant/campaign_20261029/joint_controller_selection/decision.json), [execution](../../../results/quality_tolerant/campaign_20261029/joint_controller_selection/execution.json), [review](../../../results/quality_tolerant/campaign_20261029/joint_controller_selection/completion-review.json).

## What selection established

All80adaptive candidates plus native full are retained: cheap/rich groups,8-only or8/10inspection,10shared thresholds, optional source/current number-set equality and negation-cue agreement. The source cues are heuristics, not reference-defined quality endpoints or learned protection. Reused101calibration references/trajectories are consumed development evidence. Four phase03models reused without refitting; campaign remains at4real fits/1family.

| Best point-passing candidate | Early exits | BLEU loss | chrF loss | Numeric F1 /negation loss | Estimated saving |
| --- | --- | --- | --- | --- | --- |
| Rich, inspect8, cue guard, score<=.6 | 23/101 | .484310 | .644696 | 0/0 | 4.288927% |
| Cheap, inspect8, cue guard, score<=.6 | 16/101 | .415496 | .489243 | 0/0 | 2.406871% |
| Full | 0/101 | 0 | 0 | 0/0 | 0% |

The selected rule's estimated mean133.624670ms uses the prior fixed11mean139.612550ms, the original2.145616ms/extra observation proxy, and.5ms/decision richer-feature allowance. Its terminal-only sensitivity mean131.467659ms would imply5.834%saving if extra observation/feature costs were0. That is an optimistic model sensitivity, not an actual upper bound. Prior timing-proxy errors and input composition mean the4.289%projection is not a measured controller result. Model-decision compute is0in this proxy and must be paid in any actual diagnostic.

All faster candidates fail at least one unchanged corpus point margin; none was silently dropped. The exact selected policy is saved and cannot be retuned on later timing or evaluation outcomes. All11fixed depths were scored; only11passes point margins and it is the named comparator. No adjusted quality exclusion is claimed for the other depths; an eventual evaluation must retain all11controls.

## Verification and decision

7focused synthetic cases passed before calibration access:81candidate bounds, unsupported-model skipping, threshold equality, cue vetoes, unused-future poisoning, actual inspection/history order, finite values, full fallback, work meters, observation/feature costs, ties and exact5%spending boundary.0toyfits/model requests/checkpoint loads.91corpus metric calls,8181policy-input replays,11151decisions,101reference/trajectory bodies,366prior compact feature records. No87evaluation, reservation, new source tokenization, encoding, fitting, GPU, bootstrap or paid work.

Wall25.998sec, execution CPU10.388sec charged plus300reporting/verification credit; artifacts64MiBcredit. Saved verifier passed; an independent completion check recomputed81candidate cost/point screens, verified all11fixed metrics against the earlier exact calibration results, checked7test cases and1132protected historical files. It did not reopen original trajectory/reference bodies or refit models. Cumulative accounting:1323model attempts,339.540model seconds,1519.786CPU seconds,4fits/1family,256MiBartifact credit,$0.

**Decision:** preserve `selection_did_not_establish_worthwhile_candidate`; the87-input evaluation remains closed. Q0 remains failed. A separate bounded calibration-only timing diagnostic of this exact rule is justified before spending the remaining family on new fits: the selected rule is near5%, the cost proxy is approximate, and actual cost is the campaign's unresolved endpoint. That alternative must receive a new prospective source/numeric lock and cannot convert this failed spend gate into a pass. No new thresholds, calibration reallocation or quality claim follows. If measured timing is insufficient, next consider only a justified family2/data-eligibility branch or bounded closeout.

Saved verification:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_joint_controller_selection.py','verify')
~~~
