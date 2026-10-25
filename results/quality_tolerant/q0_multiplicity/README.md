# Q0 multiplicity extension

October25,2026. **Method audit passed; overall feasibility remains statistically blocked. Q1 is not ready and was not started.**

[Methods and feasibility](../../../docs/studies/quality-tolerant/q0-multiplicity-methods-and-feasibility.md), [prospective protocol](../../../docs/studies/quality-tolerant/q0-multiplicity-protocol.md), [numeric lock](../../../docs/studies/quality-tolerant/q0-multiplicity-lock.json), [source lock](../../../docs/studies/quality-tolerant/q0-multiplicity-source-lock.json), [decision](decision.json).

The protected-exclusion intersection-union design reduces the necessary zero-adverse covered count385->183 and first80%-power count1038->436 at adverse p=.005. It preserves every quality tolerance and all potentially feasible fixed controls. The released consumed pool has at most240 numeric-covered groups; sealed E4 coverage/independence remains unknown. Original half-margin precision still matters (368 covered groups even at zero events).

Lock/source/tests were pushed at `9dad432739b081efe9b2e7ab2c311a624154084e` before execution. [64 tests](focused-tests.xml), [340,000 gate trials](gate-trials.json), [270,000 cue trials](cue-trials.json), [exact sample/power calculations](statistical-feasibility.json), [execution](execution.json), [source bytes](execution-sources.zip), [work ledger](ledger.jsonl). No new bootstrap, real-data/model work, paid compute or reservation access. All original Q0 artifacts remain unchanged.

Verify receipt/source/artifact/preservation hashes and saved case completeness, without rerunning simulations:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_q0_multiplicity.py','verify')
~~~

The one-shot runner refuses another run after started.json. Generic uniform-p cases validate error composition conditional on valid marginal tests; they do not certify corpus-bootstrap coverage or real translation quality/speedup. Negative-control false-acceptance rates and deliberate clustered-input failures are expected counterexamples, never alternative methods selected for a gate.
