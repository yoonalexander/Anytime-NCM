# Q0: statistical feasibility

Completed October 25, 2026: **statistically blocked; Q1 is not ready and was not started.**

- [Methods, results and Q1 limits](../../../docs/studies/quality-tolerant/q0-methods-and-feasibility.md)
- [Prospective protocol](../../../docs/studies/quality-tolerant/q0-protocol.md) and [numeric lock](../../../docs/studies/quality-tolerant/q0-lock.json)
- [Decision receipt](decision.json), [execution/source digests](execution.json), [byte-exact source archive](execution-sources.zip)
- [26-test receipt](focused-tests.xml), [137 deterministic result/CDF checks](independent-checks.json)
- [Analytical feasibility/power](statistical-feasibility.json), [96,000 trials](synthetic-trials.json), [synthetic corpus](synthetic-corpus.json), [synthetic timing](synthetic-timing.json), [pre-work ledger](ledger.jsonl)

385 covered independent examples are necessary under the 59-interval conservative cue method, versus at most 240 in the released consumed S1/E2 union. The prespecified p=.005 power alternative first reaches 80% at 1,038 covered groups. E4 has only 1,024 total groups, remains sealed and has unknown coverage. No empirical outcomes were rescored. The negative readiness decision is about this design; no universal impossibility result is claimed.

The protocol/source lock was pushed as `96dc9a0be7ec551b9ae7f7f8b07e5ac35631bfac` before any tests or simulations. One successful run consumed exactly 96,000 trials/140,000 bootstrap draws, 13.115 measured seconds and 128,802,816 bytes peak RSS; $0. No real-data body reads or model work. E3/E4/unallocated outcomes stay sealed.

Verify immutable execution sources/artifacts without re-running simulations:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_quality_tolerant_q0.py','verify')
~~~

The deterministic CDF/result checker is `scripts/verify_quality_tolerant_q0.py`; its initial receipt is exclusive and must not be overwritten. Its exact source digest is in independent-checks.json. Neither checker reruns trials. The runner refuses another execution once started.json exists. Whole-suite/model verifiers and Q1 searches are outside Q0.
