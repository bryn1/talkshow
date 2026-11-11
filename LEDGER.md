# blcc — LEDGER
Project: blcc, a C compiler (stdlib Python 3) emitting static freestanding x86-64 Linux ELF binaries.
Started: 2026-11-11 (MC 12406). Contract: docs/ARCHITECTURE.md (v3, repo git history is the version store).
STATUS: VERIFY — verdict loop OPEN: cycle-2 fix landed; §7 samples 12/12 byte-exact,
suite 227 green; awaiting the cycle-3 independent re-verify (test profile, MC 12409).
MC 12407 frontend (preproc, lexer, ast, parser + tests): DONE commit f7b515d
MC 12408 backend (runtime, types, data, expr_codegen, codegen, driver, 12 samples + e2e tests): DONE commit c9915a5
docs v3 (contract pinned to landed implementation; strings.c sample pinned to gcc ground truth): commits 5e0b399, 5a06dc7
MC 12409 test cycle 1 — independent adversarial e2e + negative suites: commit 6526a2d — VERDICT FAIL (F1 `&&` target always 0, F2 (int)-cast zero-extends, F3 .align after label, F4 global string init died at link).
MC 12405 fix cycle 1 — F1-F4 + LINES-reason headers, tests/test_regress_c2.py: commit 988dbb8 — TEST-verdict-c2 PASS (MC 12409), DA-verdict FIX (MC 12411: P0-1 member arrays, P1-1 \xHH bytes, P1-2 sizes/tracebacks, P2-1 int typing, P2-2 struct layout, P2-3 octal, P3-1..P3-4, P4-1).
MC 12409 test cycle 2 — re-verify probes (short-circuit counters, cast matrix, .data label proof, initializer matrices, L-suffix pin): commit 274b1aa.
MC 12405 fix cycle 2 (this commit) — DA cycle-2 list, surgical, tests/test_regress_c3.py (13 tests, RED-first): member arrays decay to address (global/ptr/local); \xHH >= 0x80 emitted as ONE byte (surrogate path, never UTF-8 re-encoded); array-size expressions constant-fold (enum/literals/+ - * /, param declarators) with loud §8 diagnostics for non-constant, and a driver belt turning ANY internal fault into an §8 exit-2 "internal compiler error" (never a traceback); int-typed results are int (sizeof table) and narrow through the 32-bit slot incl. compound/++/--/unary-minus (gcc-differential overflow rows); natural struct layout (alignof = max member align, size rounds to it); C octal \0ddd escapes; \u is a loud unknown escape; array initializers are brace-list/string only; parser builtin names DERIVE from runtime.BUILTINS (one table). LEDGER de-staled here.
