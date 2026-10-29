# Phase08 final development comparison: policy ready for once-only evaluation

October29,2026. **A cheap-feature8-only ridge rule passes the original calibration corpus POINTmargins and projects5.325%savings.** It exits220/891calibration inputs at8, otherwise11, with no extra literal guard or logit summaries. This passes the predeclared spending gate for one separately locked1188-input development evaluation. Actual latency/generalization and the original independent-quality contract remain unproved.

[Protocol](development-controller-protocol.md), [numeric lock](development-controller-lock.json), [source lock](development-controller-source-lock.json), [prototype provenance](development-controller-provenance.json). Locka5b8e5c18b1bdcb29b0fe9ef3701262120d5c5c7was pushed before11synthetic cases,12real fits and241candidate corpus replays. [Models](../../../results/quality_tolerant/campaign_20261029/development_controller/models.json), [all candidates](../../../results/quality_tolerant/campaign_20261029/development_controller/candidate-results.json), [locked policy](../../../results/quality_tolerant/campaign_20261029/development_controller/policy.json), [decision](../../../results/quality_tolerant/campaign_20261029/development_controller/decision.json), [execution](../../../results/quality_tolerant/campaign_20261029/development_controller/execution.json), [review](../../../results/quality_tolerant/campaign_20261029/development_controller/completion-review.json).

## Selected rule and actual corpus calibration points

Fit used3408new development inputs only; calibration891,178/59document/alias components. All1188development-evaluation outcomes,7700proposed confirmation and historical87/E3/E4/unallocated outcomes stayed closed. Corpus points use226reference-covered numeric inputs, unchanged denominators and no sentence-score averaging.

| Best point-passing rule | Early exits | BLEU loss | chrF loss | Numeric F1 loss | Negation increase | Estimated saving |
| --- | --- | --- | --- | --- | --- | --- |
| Ridge cheap19,8-only,score<=.6,no guard | 220/891 | .446092 | .748715 | .009833 | .004489 | 5.325385% |
| Ridge cheap+literal cues24,8-only,score<=.6,no guard | 228/891 | .442620 | .757840 | .000983 | .004489 | 5.227649% |
| Ridge cue24,8-only,score<=.6,guard | 191/891 | .398471 | .671678 | 0 | 0 | 4.082838% |
| Tree full27,8-only,score<=.5,no guard | 180/891 | .477260 | .616660 | .006146 | .001122 | 3.742488% |

Selected estimated mean137.105205ms versus prior native-full144.817283ms. Cost proxy uses the prior fixed-depth profile,2.145616msper extra observation,0.5msper added-feature/guard decision and0unmeasured scalar-prediction cost. It is a selection estimate; actual evaluation must time all operations. No controller timing was run in this phase. No new rule was added after candidate results. Nativefull/fixed11is the locked fastest point-passing fixed comparator; all11fixed control points are retained without adjusted quality exclusion.

## Matched ablations and limitations

| Family/group | Level8adverse-ranking AUC | Level10AUC |
| --- | --- | --- |
| Ridge cheap19 | .729914 | .678551 |
| Ridge +logits22 | .740049 | .692293 |
| Ridge +literal cues24 | .738471 | .678678 |
| Ridge full27 | .746434 | .693521 |
| Tree cheap19 | .694910 | .640789 |
| Tree full27 | .689997 | .636930 |

Richer features add a modest ranking increment on these SAMEcalibration inputs; they are not selected by the frozen quality/cost criterion. The cheap rule's result cannot be attributed solely to sample-size growth because the source population also differs from earlier2014studies. Tree results apply to this fixed shallow greedy family, not every nonlinear estimator. All scores/reliability bins/clipped squared errors/fit-prevalence comparisons/constant features/component-deletion sensitivity are retained in [diagnostics](../../../results/quality_tolerant/campaign_20261029/development_controller/prediction-diagnostics.json). No calibrated probability, p-value, quality bound or optimum claim follows.

[Endpoint component support](../../../results/quality_tolerant/campaign_20261029/development_controller/endpoint-component-support.json) shows fit negation adverse34events/26components at8and11/9at10; calibration13/8and7/6. Numeric adverse fit253/107components at8and114/61at10; calibration85/36and35/21. This is materially more varying supervision than the original0negation-change labels, but remains sparse/dependent for risk assurance. No endpoint-specific head was created or described as protection. The joint target remains a sentence-loss proxy at normalized threshold4; actual selected calibration corpus tolerances remain.5/1/.02/.02.

## Work, checks and remaining branch

8ridge ablation fits extend family1;4depth<=3/minleaf32trees consume family2. Total campaign16real fits/2families; remaining numerical fit allowance does not authorize further models after this final comparison.3233tree threshold cells<7000,10692single-row predictions,214731candidate-input replays,296253logical decisions,251corpus metric calls.241candidate+11fixed comparisons are development selection with no inferential multiplicity claim. JSONnormalization uses the tested reporting repair. Original phase07serialization failure/partialJSON/full charge and missing parent final CPUreceipt remain preserved.

Header filtering decoded891calibration trace/reference bodies each after4304trace/4299reference headers; fit bodies were skipped for this corpus replay. Saved4304feature records/4299label rows supplied training only through declared current/past columns.0newsourcepayloads/tokenizations/checkpoints/NNcalls/targets/downloads/bootstrap. Private inputs are hash-bound/ignored; no corpus text/full logits/activations entered Git.

11focused synthetic cases passed before fitting: exact ablation columns, training-only ridge scaling, supported interactions, absent/rare classes and constant leaves, depth/minleaf/search budgets,241candidate bounds, threshold equality/guard/unused-feature isolation, invalid models, poisoned-private-body header filtering, sparse schedule/history and cost accounting.4toyclassical fits,0toyNNcalls. Saved verifier passed; independent review checked1253protected files, all241cost/point screens,891selected row decisions,12model structures/class counts and ridge fit-prevalence intercepts, plus11test cases without newfits/NNcalls/reference scoring. No historical full-suite rerun was claimed.

Actual wall127.649sec, CPU115.863sec charged+300reporting/verification credit, RSS347394048bytes, artifacts64MiBcredit,$0. Cumulative charges10607model attempts(10602known actual),5157.982model seconds,5723.091CPU seconds,16real fits/2families,544MiBartifact credit; all shared ceilings intact.

**Next:** push this policy/comparator and then prospectively freeze ONE1188-input development evaluation of THISrule, native full and all11fixed controls. Measure actual online skipped work, complete ready-output time and paired component uncertainty; compute unchanged corpus POINTquality. Do not retune or replace the policy after those outcomes. This is not Q4confirmation; the unchanged failed Q0independent-population/statistical gate still controls that branch. If evaluation fails or confirmation remains indefensible, close out honestly with preserved negative/inconclusive evidence.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_development_controller.py','verify')
~~~
