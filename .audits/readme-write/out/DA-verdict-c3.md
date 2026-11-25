# DA verdict c3 — run-dir gate re-verification, README run (bryn1/talkshow, branch kernel)

Adversarial re-verification of the final state against the DoD, every check RUN live in this
session at HEAD 499db6269377178b9616cad6099435eede8140bc. Findings first; the gate lines are the
last three lines. Current numbers are re-measured here (README 180 lines; 172 was round 1 — not
copied from any prior verdict).

## Findings per DoD row (command → observed)

### Row 1 — README coverage + mechanical greps: PASS
- `wc -l README.md` → **180** (≥ 80).
- `grep -c "^## " README.md` → **9** (∈ 4..9).
- `grep -c "blcc" README.md` → **8** (single digit, 1..9).
- Sections read in full: What it is / Requirements / Install and quickstart / CLI / Supported C /
  Preprocessor (M1) / Tests / Architecture / Scope and limits — every DoD-named topic covered.

### Row 2 — printed quickstart runs verbatim: PASS
- From /home/claudecode/talkshow-src:
  `python3 -m blcc samples/hello.c -o .audits/readme-write/out/.tmp/hello && .audits/readme-write/out/.tmp/hello`
  → stdout `Hello, Linux from blcc`, rc 0.
- Bonus refutation attempts, all green: `bin/blcc samples/fib.c -o …/fib --emit-asm -v` printed the
  `as --64` / `ld -static` invocations exactly as README §Requirements pins, the binary printed
  `fib(20)=6765` (README's claimed output), `<output>.s` was written beside the output as §CLI
  claims, and the run's scratch under repo `.tmp/` was removed on success. `ls samples/*.c | wc -l`
  → **12**, names matching the README list. `python3 -m pytest tests/ -q --collect-only` →
  **2411 tests collected** — matches the README's claim exactly.

### Row 3 — the `-c` honesty fix: PASS
- `python3 -m blcc samples/hello.c -o .audits/readme-write/out/.tmp/x.o -c` → rc **0**;
  `file` → `ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), not stripped`.
- `python3 -m blcc samples/hello.c -c` (no `-o`) → rc **2**, stderr `blcc: -c needs -o <output>`.
- `-Wall` → rc **2**, stderr `blcc: unknown flag '-Wall'` (names the flag).
- README §CLI carries a `-c` row (line 77: requires `-o`, loud exit 2, backed by driver +
  tests/test_core_m4w0.py); §Preprocessor (lines 137–147) presents the inventory as a DATED
  measurement record: "at the M1-c7 measurement every cc-phase flag exited 2 naming the flag …
  Kernel-integration work has since SHIPPED `-c` … so the inventory's classification is a
  measurement record, not a frozen promise; the still-unshipped flags (`-Wall`, `-O2`, …) exit 2
  naming the flag."

### Row 4 — `-std` list == live driver table: PASS
- `blcc/pp_predefines.py` `STDC_VERSIONS`: 16 accepted spellings (c89 gnu89 c94 gnu94 c99 gnu99
  c11 gnu11 c17 gnu17 c2x gnu2x iso9899:1990 iso9899:199409 iso9899:1999 iso9899:2011; plus the
  `""` default entry, not a user spelling). `blcc/driver.py:41` `_STD_ALIAS = {"c90": "c89",
  "gnu90": "gnu89"}`.
- README §CLI line 76 lists exactly those 16 + `c90`/`gnu90` — agreement, no extras.
- Spot-runs: `-std=gnu17` → rc **0** (binary ran, `Hello, Linux from blcc`); `-std=c90` alias →
  rc **0**; `-std=c23` → rc **2**, stderr `blcc: unsupported -std 'c23'`.

### Row 5 — no false kernel claim: PASS
- README lines 9–11: "Compiling the Linux kernel source is GCC-scale work and is explicitly out
  of scope"; §Scope lines 175–177: "Compiling the Linux kernel source is OUT of scope and never
  claimed — what is built and tested against the kernel is the *preprocessing* pipeline."

### Row 6 — contract agreement: PASS (with one cosmetic finding, below)
- `grep -n SUPERSEDED docs/ARCHITECTURE.md` → lines 11, 23, 42. Line 42 is the `-c` inventory row
  marked "**SUPERSEDED 2026-11-25 (M4 W0, eb24bba, MC 12531, v5.3)**" with the LOUD-div measurement
  KEPT as the dated record; line 23 carries the scoped cc-phase law ("a STILL-UNSHIPPED cc-phase
  flag is never silently pretended-supported … the ONE shipped exception since M4 W0 is `-c`").
- Current contract version row is **v5.3** ("§2 `-c` re-pin (MC 12829, 2026-11-25)"), and README +
  contract agree in substance on every pinned behavior (CLI `-c`, the dated inventory, still-unshipped
  flags exit 2, kernel source out of scope) — re-checked live in rows 3/5.
- **F1 (P3, cosmetic, non-blocking):** README line 24 cites the contract as "(v5.1, 153 lines)";
  live measurement: `wc -l docs/ARCHITECTURE.md` → **154**, and the newest version row is v5.3
  (the file's own H1 title still reads "v5.1 … — repo git history is the version store", so the
  README echoes the title, but the length pin is stale by one line and the version label trails
  the newest row). Record honestly: differs from the earlier-round figure; no DoD row fails on it.

### Row 7 — retired-claim grep: PASS
- `grep -c "m64 -c" tests/test_regress_m1c7.py` → **0**.

### Row 8 — repo state: PASS
- `git rev-parse HEAD` → **499db6269377178b9616cad6099435eede8140bc** (the required 499db62);
  branch `kernel`; `git status --porcelain` → empty (clean, verified AFTER scratch cleanup);
  `git ls-remote git@github.com:bryn1/talkshow.git refs/heads/kernel` → same sha. Remote tip == local.

## Other observations (non-blocking, recorded for the record)
- F2 (P4): `blcc/pp_predefines.py` line 56 carries `iso9899:2011` twice in the dict literal
  (duplicate key, last-wins, harmless) — code hygiene only, outside this run's DoD.
- Repo `.tmp/` holds scratch debris from earlier cycles (pre-existing, git-ignored, git status
  clean proves it is ignored/untracked-excluded); README's "removed on success" claim held for every
  successful compile run performed this session (my binaries left no trace in repo `.tmp/`).
- Scratch hygiene: my scratch binaries were removed before hashing; `.audits/readme-write/out/.tmp/`
  contains only the hasher's own `.tmp/judged/<sha>.{json,args.json}` provenance records, which the
  hasher itself defines as skip-tree scratch (dod_judged_hash.py: RUN_DIRS at lines 49/120/150,
  "scratch, not hashed") — deliberately left in place.

## Hash
Run as the last step before this file, after scratch cleanup, exactly the given command:
`python3 /usr/local/bin/gate/dod_judged_hash.py /home/claudecode/talkshow-src/.audits/readme-write/out`
→ the printed line copied verbatim below. The digest equals the manifest key already present in
`.tmp/judged/` from the earlier pin — the deliverable state has not moved since.

VERDICT: all 8 DoD rows re-verified live this session, every claimed behavior reproduced, the one
discrepancy found (F1, a stale cosmetic parenthetical) does not fail any DoD row. SHIP.

# JUDGED: ed1ae4b6face24c3a3d84204df3f8e698199a0531bcbd394347ed63d12ab43c1
# CONFIDENCE: 0.90
# VERDICT: SHIP
