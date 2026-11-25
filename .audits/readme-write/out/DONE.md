# DONE.md — MC 12828 (12826.1) blcc README from artifacts — run-dir matrix

Reading used: brief said "main branch"; repo has NO main — kernel is origin/HEAD and the forward
line; work landed on kernel (flagged to owner). Stale contract row found en route: re-pin landed as
MC 12826.2 (reviewed, dc8d632, ARCHITECTURE v5.3); its docstring survivor as MC 12826.3 (verified,
2439678). LEDGER close row 499db62. Board: 12828 VERIFIED (knut), 12829 reviewed, 12830 VERIFIED.

R1 | README covers what/requirements/install+quickstart/CLI/supported-C/preprocessor/tests/architecture/scope | PASS | 9 H2 sections; full cat in evidence-readme-talkshow.txt; DA c3 row 1 live
R2 | README accurate to artifacts (ARCHITECTURE v5.1+ rows, driver.py, pp_predefines.py, tests, live help) | PASS | DA cycles r1 FIX (caught false blanket cc-phase claim) then SHIP 0.9; c3 SHIP 0.90 — 16 std spellings + c90/gnu90 aliases match driver tables, -c rows honest, exit codes live-verified
R3 | Does NOT claim the Linux kernel compiles with blcc | PASS | Scope bullet states OUT of scope; DA r1 DoD-3 clean, c3 row 5
R4 | Every command printed in README runs verbatim and prints what is shown | PASS | hello and fib and -E and wrapper re-run by DA r1/r2/c3 + orchestrator this session — outputs match
R5 | grep -c ^## in 4..9 and grep -c blcc single digit (mechanical probes) | PASS | measured 9 and 8 by orchestrator, DA r1, c3 — all agree
R6 | wc -l README.md at least 80 | PASS | 180 at HEAD 499db62, freshly measured c3
R7 | -c claims honest: rc 0 ELF relocatable; without -o rc 2; unshipped cc-flags rc 2 naming flag | PASS | live runs (orchestrator + DA r2/c3); test_core_m4w0.py 5 passed
R8 | Contract agrees: v5.3 SUPERSEDED -c row + scoped cc-phase law + grep-to-zero | PASS | git show dc8d632 reviewed; instrument re-run: zero un-annotated hits; c3 row 6
R9 | Committed and pushed to bryn1/talkshow kernel | PASS | efc60ba..499db62 chain, ls-remote tip matches local HEAD, tree clean
R10 | DA gate for THIS run dir | PASS | DA-verdict-c3.md — JUDGED ed1ae4b6face24c3a3d84204df3f8e698199a0531bcbd394347ed63d12ab43c1, CONFIDENCE 0.90, VERDICT SHIP
R11 | README L24 contract citation "(v5.1, 153 lines)" vs live file (154 lines, newest row v5.3, title still v5.1) | N/A | P3 recorded, DA c3 finding F1 — echoes the contract's own stale title line; fixing it moves the deliverable under the sealed JUDGED pin; hygiene follow-up noted in the final report, not a DoD row

CLEANUP: scratch binaries (.o, hello, fib) under out/.tmp and /tmp removed by the children and the orchestrator; the run dir keeps only evidence .txt/.md + the .tmp/judged pin map (gate scratch)
