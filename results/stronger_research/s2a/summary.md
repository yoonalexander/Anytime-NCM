# S2A: saved-data diagnosis and branch closure

Completed October 24, 2026 under the committed prospective protocol. One deterministic pass; 192 reused inputs /2,112 states /1,920 adjacent transitions; no model calls, target encodings, fits, new final outcomes or additional assignment search.

## What the evidence distinguishes

| Saved split | Early visible text equals its own final output | Early 64-ID equality | Deteriorating adjacent sentence-chrF transitions | Word recall at levels 1 /10 /11 |
| --- | ---: | ---: | ---: | --- |
| exploration (n=128) | 17/128 | 2/128 | 295/1280 | 0.101 / 0.443 / 0.483 |
| development (n=64) | 13/64 | 1/64 | 147/640 | 0.118 / 0.503 / 0.547 |

The 13/64 development early visible matches and 17/128 exploration matches show that some unchanged final translations already appear before the last level. Matching final output is retrospective and does not establish correctness versus the reference, a causal recognizer or economic stopping. Raw-ID equality is rarer: text rendering/EOS filtering can conceal token differences. No additional oracle assignment was constructed from these matches.

Reference-word recall generally emerges across refinement but is a lexical diagnostic, not content completeness. Development has 147/640 deteriorating sentence-chrF transitions even while corpus quality tends to improve. Mean sentence changes cannot replace the corpus score or certify harmful semantic revisions. These transition counts independently reproduce the prior audit.

## Persistent cue differences

| Split | Numeric reference coverage | Persistent missing numeric cue | Negation reference coverage | Persistent missing required negation cue | Final negation mismatch |
| --- | ---: | ---: | ---: | ---: | ---: |
| exploration | 31 | 9 | 17 | 3 | 5 |
| development | 13 | 6 | 9 | 0 | 2 |

Persistence means a reference digit token or required literal negation cue is missing from every saved prefix, including final. It is not evidence of a factual error: paraphrases, written numbers, token formatting and reference/source differences remain alternatives. The denominator is coverage above, not all cases independent of the cue.

## Evidence-ranked explanations

| Explanation | Support | Counterevidence / confound | Falsifiable next check |
| --- | --- | --- | --- |
| Stopping-policy weakness | Both selected WMT schedules necessarily reach level 11; saved early visible final-text matches exist | Oracle equality needs future output; no causal signal tested here predicts these cases; small selected-policy family | With justified opportunity/quality data, preregister a causal signal and compare its errors/cost with locked baselines |
| Representation/decoder dependence on late residual levels | Hard/easy Sudoku early exact validity absent; 32 target encodings need final level despite exact final round trips | WMT has early visible matches; different tasks/decoders; target-vs-generated Sudoku path/batch confounded | A specifically justified target-encoded WMT comparison could localize a remaining representation question but cannot itself establish a cause |
| Generator code errors | WMT word/cue discrepancies persist; generated Sudoku final differs from target round trip | No target-encoded WMT control; reference similarity and generation/decoder effects are mixed | Compare matched target and generated prefixes under a separately frozen pilot only if it changes a decision |
| Decoder/rendering sensitivity | Visible text can equal final despite different 64-ID outputs; adjacent revisions can reduce chrF | No perturbation experiment; EOS/filtering alone can explain some visible/raw difference | A controlled decoder/code perturbation study with pinned control and parity could test sensitivity; not performed |
| Measurement/protocol constraints | S1 uses uncalibrated costs, reused development, small cue coverage and truncated coordinate search; quality bounds miss margins | These limits do not prove zero actual headroom or that larger searches would help | Bounded prospective latency profiling and an eligible independent evaluation plan would address distinct missing evidence |

This supports failure localization rather than a causal mechanism. A claim that frozen WMT outputs never become useful early is too strong; a claim that the existing stopping rules recover a practical benefit is also unsupported. No single model intervention is selected from this evidence.

## Completed decisions

**S2B deferred:** a new target-encoded WMT pilot would localize representation/generation but would not resolve the current action-blocking issues: unsupported early-exit cost assumptions, failed quality bounds and lack of fresh confirmation. No specific controlled decoder/training intervention follows uniquely from these diagnostics. Repeating or extending encoding solely for a positive result is unjustified. This reasoned no-new-data decision completes S2A.

**S3 blocked:** S1 did not support practical headroom under the frozen gate; no controller fits or online comparison. **S4 deferred:** no specifically supported intervention and accepted model-work protocol; the original checkpoint remains unchanged. These are unexecuted branches, not failed experiments and not completed successful capabilities.

**S5 can proceed:** synthesize the finite opportunity-versus-recognition evidence with explicit search, uncertainty and timing limits; package an honest local manuscript candidate.

## Priced, unexecuted next-measurement proposal

If revisiting this line, first consider actual forced-exit timing on the first 16 already-exposed exploration identities, depths {1,4,7,10,11}, terminal-only and every-level-observation schedules, three repeats in each of two independent process blocks. Budget 960 timed +40 warmup requests =1,000 generator requests, 6,600 sample-level generator evaluations, 3,800 decoder forwards, zero full target encodings/fits/new-final access; matched saved-prefix parity checked inside those requests with no extra model calls. Cap two cumulative wall hours, 256 MiB new artifacts, existing local hardware and $0; no retries or replacement examples. This is a priced proposal only, outside consumed S1 and executed S2A, and requires a separate diagnostic protocol before execution. It would estimate schedule costs, not validate a causal policy or supply fresh confirmation. A suitable new group-aware quality-evaluation population would remain a separate unresolved requirement.

## Artifacts and accounting

See exploration.json /development.json for all per-identity diagnostics and level/transition summaries; execution.json records protocol/source/input digests, elapsed time, RSS and zero model-work counters. Only S1-selected exploration examples are reused; no new examples were selected. Synthetic aggregation tests passed. Historical empirical files and upstream checkpoint/source are unchanged.
