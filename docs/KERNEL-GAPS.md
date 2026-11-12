# blcc M0b gap sweep — Linux 5.10 kernel corpus (MC 12426 VERIFIED, docs home: this file; raw data: /home/claudecode/Blaha/.tmp/m0b/raw/)

Run 2026-11-12 13:38–13:57 UTC on VM350. blcc: `/home/claudecode/Blaha/c-compiler`,
branch `kernel`, HEAD `d55d7f3` (READ-ONLY honored — see §7). Corpus: pristine
`/home/claudecode/Blaha/kernel-lab/linux-5.10` (5.10.274, never modified).
Tool: `/home/claudecode/Blaha/.tmp/m0b/gap_probe.py` (stdlib python, 10 workers,
30 s per-subprocess timeout, resumable — raw jsonl IS the state file).
gcc 11.4.0 is the preprocessing oracle.

**Corpus: 712 .c files** (brief estimated ~600; actual `find` over kernel/ mm/
init/ block/ ipc/ crypto/, recursive) — kernel 357, crypto 150, mm 115, block 70,
ipc 11, init 9. Full corpus kept (no reduction); sweep wall-time: pp+parse+aux
146 s, sfx probe 231 s (≈ 7 min total, 10 workers).

## 1. Method (four passes per file; two pinned, two exploratory)

| pass | input | question it answers |
|---|---|---|
| pp | raw `.c` through blcc's own pipeline | what blcc's shipped front-end hits FIRST on untouched kernel source |
| parse | `gcc -E` output, `# N "file"` markers stripped | what blcc's front-end hits FIRST once a GCC-grade preprocessor has done its job |
| aux | parse + ALL remaining `#` directive lines stripped (only `#pragma pack` survives gcc -E) | isolates lex/parse/sema-level C constructs from pp residue |
| sfx | aux + integer-literal suffixes (`1UL/1U/1L/1LLU/0x1LU`…) textually erased | NEXT construct layer behind the lex-suffix wall — the true M2 ranking |

aux and sfx are **exploratory depth probes**: their rows are in
`raw/aux.jsonl`/`raw/sfx.jsonl` and in the §3 ranking below, but OUT of the
pinned histogram.tsv and its sum-check (the DoD pins pp+parse there).

gcc recipe (deviation, NOT silent — the brief's flag list cannot preprocess
5.10.274 at all): real in-tree build flags lifted from `init/.main.o.cmd` of the
M0a-built tree: `-nostdinc -isystem $(gcc -print-file-name=include) -D__KERNEL__
-std=gnu89 -I arch/x86/include -I arch/x86/include/generated -I include
-I arch/x86/include/uapi -I arch/x86/include/generated/uapi -I include/uapi
-I include/generated/uapi -include include/linux/kconfig.h -include
include/generated/autoconf.h -I <seed>`. The brief's list lacks the
`generated{,/uapi}` dirs (`<asm/types.h>` resolves there) and gcc's own
`stdarg.h/stddef.h` dir — with it, `gcc -E` exits 0 on 691/712 files. Seed
(per HARNESS.md recipe): `seed/asm/{early_ioremap,export,mcs_spinlock}.h` →
`<asm-generic/...>` shims from the generic-y lists in
`arch/x86/include/{,uapi/}asm/Kbuild` (3 entries; the uapi Kbuild has none).
The tree's real (tinyconfig) `include/generated/autoconf.h` is used — it exists
from the M0a build and wins over the recipe's empty seed file via `-I include`
ordering. Consequence, stated plainly: code under disabled CONFIG_ symbols is
preprocessed away, so per-file construct counts are a LOWER BOUND on the
full-config kernel.

pp-pass deviation: branch `kernel` at d55d7f3 has **no `-E`/`-D` flags** (probed
at startup: `blcc: unknown flag '-E'`, rc 2 — recorded in meta.json), so the pp
pass runs the shipped §2 CLI `python3 -m blcc <file> -o <scratch>`. First
diagnostic is identical in kind: every kernel .c dies at pp before anything
else can happen.

## 2. Ranked constructs — the pinned histogram (`.tmp/evidence/m0b-histogram.tsv`, full 31 rows)

`construct = <pass>|<§8 phase>: <message, literals elided> found '<token>'`

| pass | count | construct (normalized) | example |
|---|---|---|---|
| pp | 708 | pp: `#include <...>` not in subset | block/badblocks.c:10 |
| pp | 1 each | pp: `#if` unsupported directive (mm/percpu-km.c:29) · lex `1nd` (crypto/jitterentropy.c:114) · sema `unsigned` (mm/percpu-vm.c:13) · parseable (kernel/trace/trace_kprobe_selftest.c) | |
| parse | 679 | lex: malformed number literal — suffix family `UL` 611, `U` 32, `L` 16, `0xffU` 11, `ULL` 6, `0xCAFEBull` 2, `0xaeUL` 1 | block/badblocks.c:732 |
| parse | 21 | gcc -E oracle fail (15 × headers absent under the tinyconfig oracle — 8 generated `*.asn1.h`, `asm/dasd.h`, 2 × neon, 2 × bpf-preload (`bpf/bpf_helpers.h`, `argp.h`), 2 × `./trace`-event headers; 6 × macro-arg mismatch under the tinyconfig oracle, e.g. `acct_process`) | block/partitions/ibm.c |
| parse | 8 | pp: unsupported directive found `#pragma` (residual `#pragma pack` in gcc -E output) | crypto/asymmetric_keys/asym_tpm.c |
| parse | 3 | sema: `unsigned` not in subset | crypto/jitterentropy.c |
| parse | 1 | parseable: blcc ran the WHOLE 2.7 MB front-end to sema (no main) — kernel/trace/trace_kprobe_selftest.c | |
| parse | 0 | compiles (blcc exit 0): none — no kernel TU has `main`; §8 sema stops them first | |

## 3. Depth-2 ranking (sfx probe) — the real M2 sequence

With the lex suffix wall textually erased, 690 files immediately surface their
NEXT first blocker:

| count | first blocker behind the suffix wall | example |
|---|---|---|
| 560 | `unsigned` / `__signed__` types (sema reject 241 + parse "expected a type" 319) | block/badblocks.c:18, block/bfq-cgroup.c:41 |
| 110 | `__builtin_va_list` as a type (va_list typedef from gcc stddef) | block/blk-mq-cpumap.c:19 |
| 21 | gcc-E oracle fail (same 21 files as parse pass) | |
| 8 | unknown escape sequences in string literals (`\e`,`\r`,`\'`, octal `\<n>`) | kernel/debug/kdb/kdb_io.c |
| 6 | `extern` linkage (§4 file-scope static only) | block/partitions/atari.c:7 |
| 2 | `inline` (kernel `#define inline` leaves the keyword in the stream) | kernel/user-return-notifier.c:11 |
| 1+1+1 | `union` (ipc/syscall.c) · enum-init not integer-const (kdb_keyboard.c) · `gfp_t` type-parse | |
| 1 | parseable to sema (the selftest file again) | |
| 1 | `LLU` suffix residue (probe regex gap, still the suffix family) | block/blk-iocost.c |

Family rollup (sfx, 712 total): unsigned-family 560 · va_list 110 · gcc-oracle
21 · escapes 8 · extern 6 · inline 2 · suffix-residue 1 · union 1 · enum-init 1 ·
gfp_t 1 · parseable 1.

## 4. Per-directory parse-pass stats

| dir | n | §8 diag | gcc-E-fail | parseable | compiles | timeout |
|---|---|---|---|---|---|---|
| kernel | 357 | 346 | 10 | 1 | 0 | 0 |
| crypto | 150 | 140 | 10 | 0 | 0 | 0 |
| mm | 115 | 115 | 0 | 0 | 0 | 0 |
| block | 70 | 69 | 1 | 0 | 0 | 0 |
| ipc | 11 | 11 | 0 | 0 | 0 | 0 |
| init | 9 | 9 | 0 | 0 | 0 | 0 |
| ALL | 712 | 690 | 21 | 1 | 0 | 0 |

Zero timeouts, zero as/ld (exit 3), zero usage-noise records in every pass.

## 5. Performance datapoint (blcc wall-time, this corpus)

| pass | mean | median | max | 712-file total |
|---|---|---|---|---|
| pp (dies at first `#include <>`) | 0.09 s | 0.09 s | 0.14 s | 65 s |
| parse (dies at lex, avg ~1 MB .i) | 0.85 s | 0.89 s | 1.66 s | 606 s |
| aux (≈ parse) | 0.85 s | 0.89 s | 1.81 s | 605 s |
| sfx (deepest parse reached — 30–40× more front-end work) | 2.62 s | 2.73 s | 5.29 s | 1868 s |
| gcc -E oracle (reference) | 0.15 s | 0.16 s | — | — |

Extrapolation for ~2500 kernel TUs (INFERRED, current early-exit depths are a
floor, not a full compile): front-end alone ≈ 2500×2.6 s ≈ 1.8 h single-core,
~11 min at 10 workers; codegen is not yet measured on anything deep. Python
startup is ~0.07 s/file of it. gcc does the same preprocessing ~6× faster.
blcc on a 2.7 MB preprocessed TU completes a full pass in <2 s — the pipeline
speed is not the M2/M3 risk; construct coverage is.

## 6. pp-pass vs parse-pass — what the preprocessor milestone ALONE unblocks

* pp-pass: 708/712 (99.4 %) die at the first angle-include; 100 % of files are
  dead at pp tier (only 1 file reaches sema — the 16-line selftest).
* parse-pass = the world after M1 gives blcc a gcc-grade pp: blockers move
  wholesale to lex (679) and the gcc-oracle set (21). **Newly parseable
  TUs from pp work alone: 0.**
* sfx: behind lex+unsigned, still no file compiles — depth 3 (`va_list`) is
  waiting too.

So M1 (full preprocessor) is a strict PREREQUISITE (nothing is even lexable
without it) but unlocks ZERO TUs by itself; it changes which wall is first, not
the end-to-end outcome.

## 7. M2/M3 sequencing implied by the ranking

1. **Lex integer-suffix family first — it is the gate for 95 % of the corpus.**
   One lexer rule (`[0-9a-fx]+` + `[uU][lL]{0,2}` / `[lL][uU][lL]?` / `[lL]{1,2}`,
   pinned interning per §4) moves the first blocker off 679 files. Cheapest
   construct on the board, largest unblock. Do it inside M2 before anything
   else; §5's "unsigned types" note must be amended — the LITERAL suffix is not
   the same wall as the TYPE keyword.
2. **Unsigned types (`unsigned`/`__signed__`) — 560 files at depth 2.** This is
   the single biggest true language gap. It pairs naturally with the suffix
   work (same §5 line) and needs types.py/codegen interning rows (§4 already
   has `movzbq`/`movzwl` hooks and unsigned char contexts — extend, don't
   rebuild).
3. **va_list / `__builtin_va_list` type — 110 files at depth 2.** Smallest
   honest slice: accept `__builtin_va_list` as a typedef-able opaque type + a
   `va_list`/`va_start`/`va_end` builtin posture (variadic CALLS are deeper;
   typedef acceptance alone unblocks the first blocker in these 110).
4. Only then the long tail per depth-3 probes you must re-run after M2 lands
   (this corpus shows them masked, never reached): escapes (8), `extern`
   linkage (6), `inline` keyword (2), `union` (1 here — pp-pass sees none),
   bitfields/function-pointers/goto/asm (0 seen at this depth under tinyconfig
   — their absence here is a CONFIG artifact, NOT evidence they are small).
5. **M1 pp stays the hard prerequisite and stays scheduled before M2** — but
   the ranking says: do NOT budget M1 as the milestone that makes kernel files
   "work"; budget M2 (suffix+unsigned+va) as the first milestone that flips
   real TUs from dead to alive. The 21 gcc-oracle files (8 asn1-generated
   headers, bpf preload, neon, plus 6 tinyconfig macro-arg quirks) need
   generated-header support in the harness, not blcc
   work — track them as harness debt (add asn1 table generation to the M0a
   harness, MC 12422 line).
6. Performance: no blcc performance milestone is warranted by this corpus
   (<2 s/TU front-end); revisit after codegen depth exists.

## 8. Raw data & self-check

* Raw per-file lines: `/home/claudecode/Blaha/.tmp/m0b/raw/{pp,parse,aux,sfx}.jsonl`
  — one JSON line per file per pass `{file,pass,status,construct,dfile,dline,raw,blcc_s[,gcc_s]}`
  (712 lines each; also the resume state — re-running `gap_probe.py run` skips
  completed (file,pass) pairs; VERIFIED: re-run found todo=0 after completion).
* `meta.json` = run provenance (blcc head, -E probe rc 2, flags, workers, seed count).
* **Self-check (DoD leg):** histogram sum per pass = pp 712, parse 712 = files
  swept per pass ✓ (VERIFIED via awk column-sum on the shipped TSV). TOP row
  (pp angle-include) 708 + 4 singletons = 712 ✓; parse: 611+32+16+11+8+6+6+3+2
  (=695) + 15 header-fail + 1 `0x<n>aeUL` + 1 parseable (=17 ones) = 712 ✓.
  aux/sfx sums also 712 each in stats.json.
* c-compiler READ-ONLY VERIFIED at end: no writes by this run (blcc got `-o`
  paths only inside `.tmp/m0b/scratch`; `PYTHONDONTWRITEBYTECODE=1`; scratch .i
  files deleted after use; `git status --porcelain` shows ONLY foreign
  concurrent-child files `scripts/gen_has_attribute_table.py`,
  `tests/test_pp_differential_m1.py` — not touched per brief).
* Known limits: first-blocker-per-file ranking is text-order biased (a file
  with 50 constructs counts once); tinyconfig autoconf strips CONFIG-gated code
  (counts are lower bounds); the sfx probe erases suffixes inside string
  literals too (classification-only probe, never a corpus edit); 21 files lack
  a working oracle under tinyconfig and their parse/aux/sfx rows are
  oracle-fail, not blcc, datapoints.

VERIFY_EXIT=0
# VERDICT: DONE
