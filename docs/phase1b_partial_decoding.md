# Phase 1B: upstream adapter and full-resolution partial decoding

**Completed:** October 20, 2026 (America/Toronto).
**Next milestone:** Phase 1C, offline trajectory collection and storage.

The adapter runs the released generator through all 12 levels before reconstructing or decoding prefixes. It implements offline inspection; it does not stop generation or measure an adaptive speedup.

## API and reconstruction contract

[upstream_adapter.py](../src/anytime_ncm/upstream_adapter.py) provides:

- `load_sudoku_adapter(repository, device="cuda")`: load the local tokenizer and generator with the official config, strict checkpoint state loading, float32 parameters, and eval mode. It requires the pinned, unchanged upstream checkout and official hard-Sudoku configuration. It performs no downloads.
- `adapter.generate_codes(context)`: accept a nonempty `torch.long` tensor of shape `[batch, 91]`, delegate once to unchanged upstream `generate`, and return all 322 codes. Sampling remains temperature 0, top-k 0, top-p 1, guidance 0, and the default eager/no-KV-cache path.
- `reconstruct_prefixes(adapter.vq, codes)`: validate complete code sequences and per-level codebook bounds, then return 12 independent float32 tensors of shape `[batch, 89, 256]`.
- `adapter.decode_latent(latent)`: return selected token IDs and decoded texts from a full-resolution latent.
- `adapter.decode_prefixes(codes)`: return one `DecodedPrefix` per level with one-based level number, that level's code length, cumulative code count, token IDs, and texts. Token IDs have shape `[batch, 89]`; decoded text may be shorter when special tokens are removed.

Example after preparing the official 91-token context tensor:

```python
from pathlib import Path
from anytime_ncm.upstream_adapter import load_sudoku_adapter

adapter = load_sudoku_adapter(Path.cwd())
codes = adapter.generate_codes(context)
prefixes = adapter.decode_prefixes(codes)
final_texts = prefixes[-1].texts
```

The reconstruction mirrors the pinned quantizer's float32 accumulator and operation order. Each level uses its own embedding, the learned/full-resolution upsampling path when required, and the residual transform. The accumulator is cloned inside the loop immediately after that level's addition. The adapter does not decode shortened `z_levels` or clone upstream's aliased accumulator list after return.

Private upstream dependencies are `MultiscaleResidualVectorQuantizer._up_to_full` and `._apply_quant_resi` at commit `c70274273f489abc73832b2b98584a8483b6b203`. An upstream upgrade requires a deliberate compatibility review and fresh prefix/parity verification.

The actual `pick_tokens` and `dec` definitions are extracted with Python AST from pinned `scripts/eval_shard.py`, then compiled with the official Sudoku globals. This avoids importing its top-level argument parsing, checkpoint loading, and dataset execution. Sudoku has no frequency or adjacency penalty; selection is upstream argmax, followed by upstream EOS/PAD filtering and Sudoku special-token decoding. Other tasks and sampling extensions are outside this adapter's contract.

Upstream import namespaces are checked to reject a conflicting `models`, `tokenization`, or `utils` package. Read-only Git checks use a command-scoped safe-directory exception for the known checkout and Windows-compatible CRLF normalization; no global Git configuration or upstream file is changed. The config digest is checked after newline normalization.

## Verification

Full implemented test suite:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1b_tests.xml')
```

Observed result: **88 passed in 4.57 seconds**, including the existing 59 Sudoku tests, 26 adapter/prefix tests, and 3 parity-input isolation tests. [JUnit report](../results/phase1/phase1b_tests.xml).

Synthetic prefix tests use the actual upstream quantizer with nonidentity learned weights. An independent fixture computes embeddings, transposed convolution/cascade, linear interpolation, optional learned refinement, residual convolution, and prefix sums without calling the adapter or its private reconstruction helpers. Tests cover full sequence length, exact intermediate values, final upstream latent equality, independent storage, future-code isolation, legitimate equal adjacent snapshots, malformed code sequences, exact generator delegation, decoder semantics, and eval-mode enforcement. The standalone parity script's synthetic tests reject missing exploration membership and changed puzzle identities.

Real-checkpoint CUDA verification:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/verify_phase1b.py', '--output', 'results/phase1/phase1b_verified')
```

The recorded directory is already populated. For a repeat, choose a fresh directory beneath `results/`; the script refuses to overwrite nonempty evidence.

On WSL2 / Python 3.12.3 / Torch 2.10.0+cu128 / RTX 5060:

- All 12 latent snapshots had shape `[32, 89, 256]` and independent storage.
- All 12 decoded token batches had shape `[32, 89]`.
- Changing every code after each depth 1–11 left all earlier snapshots unchanged.
- The final latent was bitwise equal to unchanged upstream reconstruction.
- All **32/32 final decoded texts exactly matched** a fresh official evaluator invocation.
- Generated input codes were unchanged by reconstruction and decoding.
- The official smoke comparator reproduced **24/32 solved (75.00%), 97.26% cell accuracy, and 75.00% valid grids**.

Both official and adapter generation used the same first 32 inputs, batch-size setting 128 (one effective batch of 32), float32 without autocast or compilation, greedy sampling, four CPU threads, and GPU 0. This establishes parity for this matched smoke run, not every possible batch size or platform. No new full-set evaluation ran.

Machine-readable [GPU evidence](../results/phase1/phase1b_verified/verification.json) records source/config/artifact/protocol/manifest hashes and execution settings. [Completion record](../results/phase1/phase1b_validation.json) joins the test and parity evidence. [Official score log](../results/phase1/phase1b_verified/official/evaluate.log) retains the unchanged scorer output.

## Access, failed attempts, and boundaries

Only the predetermined first 32 exploration puzzle identities were selected, after checking the frozen manifest and artifact hashes. The input pickle is necessarily deserialized in full; only indices 0–31 were passed to either generation path. The unchanged official evaluator internally loads the reference pickle before slicing to the 32 inputs. Its resulting prediction/reference pickle is exploration-only and remains ignored. The comparison inspected its hypotheses and index list; reference fields were not inspected. No holdout predictions or references were examined.

The first preflight failed on WSL Git ownership before inference; retrying exposed an empty-directory handling bug, also before inference. A subsequent attempt completed the official smoke evaluator but rejected the adapter load because WSL Git treated the Windows CRLF checkout as dirty. The failed [verification record](../results/phase1/phase1b/verification.json) and official logs are retained. After scoped Git and directory-handling fixes, the complete fresh run above and final test suite passed. No failed result was relabeled successful.

No intermediate board-quality statistics, trajectory dataset, early-exit opportunity estimate, latency profile, halting hook, controller training, or Phase 1C collector was added. The original full-set baseline, frozen protocol/partitions, environment lock, and upstream source remain unchanged. The paper-number discrepancy remains open.
