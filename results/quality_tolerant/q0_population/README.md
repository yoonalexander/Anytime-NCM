# Q0 population and reference-coverage audit

October25,2026. **Complete; actual coverage and document overlap established. Q1 remains statistically blocked and unstarted.**

[Methods/results](../../../docs/studies/quality-tolerant/q0-population-methods-and-feasibility.md), [protocol](../../../docs/studies/quality-tolerant/q0-population-protocol.md), [numeric lock](../../../docs/studies/quality-tolerant/q0-population-lock.json), [source lock](../../../docs/studies/quality-tolerant/q0-population-source-lock.json), [decision](decision.json).

Consumed S1/E2:92 numeric-covered groups among448. E3:30/128. E4:191/1024. Closed unallocated:90/571. E4 clears183 zero-adverse NI coverage, but remains below required power/precision; illustrative iid p=.005 NI power is38.389%. Source alignment is exact on all3,003 rows. The corpus has164 official document labels;988 E4 inputs share documents with704 known consumed groups. Only36 E4 inputs, including12 numeric-covered references, are in disjoint documents. These counts did not change any population.

[Aggregate coverage/planning/document overlap](population-coverage.json), [source-only document map](document-map.json), [source provenance](document-provenance.json), [append-only machine-only reference-access receipt](coverage-access-release.json), [execution](execution.json), [87 tests](focused-tests.xml), [source archive](execution-sources.zip), [work ledger](ledger.jsonl).

Lock `22d57ab7b23d197b1a4c7f9a7d5a9df6b96a756f` was pushed before tests/data access. Reference-derived aggregate exposure is now disclosed for E3/E4/unallocated roles; model outputs remain sealed. No raw reference text/per-input cue flags, model output, quality scoring, fitting or Q1 work. Original protocols/manifests/receipts are unchanged. Official raw archive stays ignored under data/wmt14/q0_population/.

Verify saved receipts, hashes and counters without another reference read or download:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_q0_population.py','verify')
~~~

The runner refuses another run after started.json. No new data allocation or reservation release follows this audit.
