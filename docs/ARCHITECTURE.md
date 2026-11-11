# blcc — Architecture Contract (v2, 2026-11-11, MC 12406) — repo git history is the version store

Executable contract: code children implement EXACTLY this; the closing Architect verifies reality against it.
Project: /home/claudecode/Blaha/c-compiler/ (session plane). Host: Ubuntu 22.04 x86-64, Python 3.10.12 (no 3.11+ syntax).
Layout: one concern per file; target ~250 lines, soft cap 400 (a file over 400 carries a `# LINES:` reason line at its top), absolute cap 600.

## 1. Scope / non-scope
- blcc accepts the C subset in §4, emits x86-64 AT&T assembly, and drives system `as`+`ld` into a STATIC freestanding ELF that runs on this Linux host.
- "Compiles linux" = compiles C *for* Linux; the produced binaries run on Linux. Compiling the Linux KERNEL source is GCC-scale work and is explicitly OUT of scope — blcc never claims it.
- Freestanding: NO libc, no libc headers, no dynamic linking. Programs reach Linux via raw syscalls through §5 builtins; the compiler ships its own `_start`.
- Out: PIE/dynamic, Windows/macOS/other ISAs, `#include <...>` system headers, precompiled output other than ELF.
- Cardinal failure = silently wrong code: every unsupported/invalid input is a loud diagnostic (§8), never guessed codegen.

## 2. CLI contract (pinned)
- `python3 -m blcc <input.c> -o <output>`; `bin/blcc` = thin exec wrapper forwarding all args to that command.
- Flags: `--emit-asm` (keep + print emitted asm, still assembles/links); `-v` (echo each external as/ld command before running it). No other flags.
- Exit codes: 0 ok. 2 = compile error: stderr diagnostic per §8. 3 = assembler/linker failure: tool stderr passed through.
- Artifacts: scratch `.s` in `.tmp/` (removed on success); `--emit-asm` writes `<output>.s` beside `<output>` and keeps it.
- Assembled/linked exactly: `as --64 -o <tmp>.o <file>.s` then `ld -static -o <output> <tmp>.o`.

## 3. Modules (one concern per file)
Pipeline: driver → preprocessor → lexer → parser → codegen → as/ld; runtime.py feeds codegen.

| File | Concern |
|---|---|
| blcc/__init__.py | Package docstring ONLY — the single file this phase creates; no code ever lands here. |
| blcc/lexer.py | Tokenizer: ids, keywords, int/char/string literals (escapes `\n \t \\ \" \0 \xHH`), punctuation, comments; every token carries file/line/col. |
| blcc/preproc.py | Subset preprocessor: `#include "local.h"` (quoted, input-relative, cycle guard), object-like + function-like `#define`, `#ifdef/#ifndef/#else/#endif`, `#undef`. |
| blcc/ast.py | Node dataclasses only (frozen where practical) — no behavior beyond fields. |
| blcc/parser.py | Recursive-descent parser: declarations + statements → ast nodes; records every grammar diagnostic. |
| blcc/expr_parser.py | Expression parser: precedence-climbing + casts + unary, producing ast nodes. Split from parser.py up front: the expression grammar alone would push one file past 400 lines. |
| blcc/codegen.py | x86-64 AT&T emitter: stack frame per function, locals at fixed rbp offsets, temporaries on-stack; correctness over optimization. |
| blcc/driver.py | CLI parse, pipeline order, as/ld subprocess calls, diagnostics, exit codes 0/2/3. |
| blcc/runtime.py | Emits the runtime asm blob (frozen text constant) + builtin symbol table shared with codegen. No C runtime source: blcc cannot compile C. |

Rejected: JIT/bytecode middle-end, LLVM/lli, third-party parsers, a second runtime in C, per-function temp registers ( SSA-style regalloc) — all rejected for stdlib-only + correctness-first.

## 4. C subset (pinned)
- Types: `char` `short` `int` `long` `void`; sizes 1/2/4/8, all 8 for pointers; `_Bool` out. Structs; arrays (fixed size; `T a[]` only with init list or as parameter); `typedef`; `enum` constants (int-valued).
- Interning: char/short sign-extend to 64-bit on load/store, int zero-extends; codegen uses movsx/movsxd/movzx per width — pinned so two coders emit identical asm.
- Storage: globals (initializers = integer/char/address-of-global constants; 0 → `.bss`, non-zero → `.data`), locals. Only storage class keyword accepted: `static` at file scope (same as non-static there); `static` inside a function → diagnostic.
- Functions: prototypes, definitions, calls, recursion, `main(int argc, char **argv)` (other mains allowed as ordinary functions). No default argument promotions beyond the interning rule.
- Operators: `+ - * / %` (signed; x86 idq semantics pinned — `/` and `%` truncate toward zero; sample 2 exists to pin that), unary `-`; `& | ^ ~ << >>` (shift count from operand's own width); `!`; `== != < <= > >=`; `&& ||` (short-circuit); compound `+= -= *= /= %= &= |= ^= <<= >>=`; `++ --` prefix+postfix; `sizeof` types+expressions (compile-time); casts among the 4 int types and pointer↔pointer / pointer↔long; `&` `*`.
- Control: `if`/`else`, `while`, `do…while`, `for` (declaration or expression init; both empty allowed), `break`, `continue`, `return`, nested blocks.
- `switch`/`case`/`default` IS IN the subset (pinned — do not re-litigate): integer controlling expr, compile-time-constant labels, codegen emits a compare chain (jump table allowed as a refinement only when all case values are dense and contiguous), C fall-through semantics preserved, `break` exits the switch.
- Strings: literals → byte arrays in `.rodata`, type `char *`; same escape set as lexer.
- Sample helper: `samples/print.h` (preprocessor-included, ordinary C on top of §6 builtins): `void pstr(const char *)`, `void pint(long)` (signed decimal), `void pchar(int)`; plus `#define NL` → `"\n"`. Samples use it so the pinned stdout bytes stay readable.

## 5. NOT in the subset — loud diagnostic naming the construct, exit 2
float/double · goto/labels · unions · bitfields · function pointers (declarations, calls through them) · variadic functions · struct assignment or comparison (member-wise scalar assignment is in) · multi-file linking beyond `#include` inlining (exactly one translation unit to `as`) · `static`/`extern` linkage rules beyond file scope · `default` in switch outside a switch, arrays as struct members beyond fixed arrays, `for` init declarations beyond one simple declaration.
Any token the lexer cannot classify is itself a diagnostic naming the offending text.

## 6. Linux-freestanding runtime (pinned)
- Implicit builtins — always in scope, no declaration needed; a user redeclaring one is a diagnostic:
  `long _sys_write(long fd, const char *buf, long len);` `void _sys_exit(long code);`
  `long _sys_open(const char *path, long flags);` `long _sys_read(long fd, char *buf, long len);`
  `long strlen(const char *s);` `long strcmp(const char *a, const char *b);`
- Mapping (Linux x86-64): `syscall(number, arg1..3)` → rax=number, rdi=arg1, rsi=arg2, rdx=arg3, rcx/r11 clobbered; `instruction_syscall`. write=1, open=2, read=0, exit=60. `_sys_write`→1, `_sys_open`→2, `_sys_read`→0, `_sys_exit`→60 (never returns); `strlen`/`strcmp` are asm loops in the runtime blob (return byte count / 0-equal / sign of first difference).
- `_start`: extern "C"-style ABI — argc/argv/envp already on the stack at entry; `_start` loads argc→rdi, argv→rsi, calls `main`, then `_sys_exit(rax & 0xff)`. argv strings stay at their stack addresses; codegen references them only via pointers passed in registers/locals.
- Assembly ABI: System V — args rdi,rsi,rdx,rcx,r8,r9; return rax; callee-saved rbx,rsp,rbp,r12–r15 untouched by generated code; rsp 16-byte aligned at every `call`.
- Emitted module layout: single `.text`, `.section .rodata`, `.data`, `.bss`; entry `_start`; link: static, non-PIE, default base 0x400000.
- Runtime blob = frozen asm text constant in blcc/runtime.py (no runtime.c anywhere — blcc has no C compiler to compile it with).

## 7. samples/ (pinned names, exact expected stdout bytes, exit codes)
Source-style contract for all samples: they use ONLY §4+§6; the ONLY permitted `#include` is the quoted helper `samples/print.h` (§4). Exit codes come from an explicit `_sys_exit` in every sample.

| # | File | Expected stdout (exact bytes) | Exit |
|---|---|---|---|
| 1 | hello.c | `Hello, Linux from blcc\n` | 0 |
| 2 | arith.c | `(2+3)*4 - 6/3 + (7%5) - (-9/2) + 7 % -2` = 25 → `25\n` (gcc reference run: -9/2=-4, 7%-2=1, truncation toward zero) | 25 |
| 3 | loop.c | sum 1..10 → `55\n` | 55 |
| 4 | fib.c | `fib(20)=6765\n` | 0 |
| 5 | array.c | `int a[8]` filled `a[i]=i*i`, summed via pointer walk `*(p+i)` → `140\n` | 0 |
| 6 | strings.c | `char buf[16]`: copy `"blcc"` (via strlen+byte loop), write reversed → `ccbl\n` | 0 |
| 7 | struct.c | `struct point{int x;int y;}` global `{3,4}` + `struct point *p=&pt`; `p->y + pt.x` → `7\n` | 0 |
| 8 | grid.c | 5×5 `#` grid (nested for) → `#####\n` ×5 | 0 |
| 9 | hostname.c | `_sys_open("/etc/hostname",0)`, `_sys_read` (buf 128), `_sys_write(1,…)` verbatim bytes | 0 |
| 10 | argv.c | `pint(argc)` + NL; argv[1] if present → `pstr` + NL | argc |
| 11 | switch.c | loop 0..4, switch {0:`zero\n` 1:`one\n` 2:`two\n` default:`many\n`} → `zero\none\ntwo\nmany\nmany\n` | 0 |
| 12 | globmix.c | global `int g` (+1 twice in `bump()`), local 19 + g → `21\n` | 21 |

Pinned: exit codes ≥256 truncate per `exit(n & 0xff)` (all pinned codes are < 256 — this rule only guards samples). Tests run every sample twice: no args, and with one arg `hi`. argv.c then prints `argc=2\nhi\n` exit 2; the no-arg run prints `argc=1\n` exit 1 — that exact pair is the argv contract. hostname.c asserts stdout == first bytes of /etc/hostname up to 128 (content-derived assertion, not a literal).

## 8. Diagnostics contract
- Compile error: `file:line:col: <phase>: <message>, found '<token-or-construct>'` on stderr, exit 2. Phases: `lex` / `pp` / `parse` / `sema` / `asm`.
- Unsupported §5 constructs: message names the construct literally (e.g. `float`, `goto`, `union`, `function pointer`).
- Assembler/linker: tool stderr passed through verbatim, exit 3; scratch `.o`/`.s` kept on failure (into `.tmp/`).
- `main` missing → `sema` diagnostic exit 2. Nothing is ever emitted for input the contract rejects.

## 9. tests/ contract
- tests/test_*.py, pytest (installed on host; test-runner ONLY — never imported by blcc/ sources; `requirements.txt` stays absent — the tree has zero third-party deps).
- Unit: test_lexer.py (token kinds, line/col, escapes), test_preproc.py (defines, includes, conditionals, undef, cycle guard), test_parser.py + test_expr_parser.py (AST shapes incl. switch, sizeof), test_codegen.py (asm text patterns: frame setup, switch cmp-chain, movsx), test_runtime.py (blob symbols present), test_driver.py (exit codes, `--emit-asm` keeps `.s`, `-v` echoes).
- End-to-end: tests/test_samples.py — for each §7 sample: compile via `python3 -m blcc`, run the binary, assert EXACT stdout + exit per the table (argv/hostname per their pinned rules); no skips, no timeouts >10s, fully deterministic.
- Negative: float literal → exit 2 + `float`; goto → exit 2 + `goto`; missing `;` and unbalanced `}` → exit 2 naming file:line:col; unknown include → exit 2 + `pp`.
- Deterministic: samples write only under `.tmp/`; no network; no env reads beyond what argv/hostname pinned.

## 10. Data stores / ports / dependencies (closing Architect checks this table against reality)
- Data stores: NONE. Ports / services / daemons: NONE. Environment/config files: NONE.
- Runtime deps: `python3` (stdlib only, 3.10) + `/usr/bin/as` + `/usr/bin/ld` — nothing else, no pip installs.
- Dev deps: `pytest` (host-installed test runner). No vendored third-party code.

## 11. File hygiene (binding on every child)
- No literal unimplemented-work marker words — spelled "T-O-D-O" and "F-I-X-M-E" here so this file passes its own grep gate — anywhere in source or docs; the fleet gate fails on them. Unimplemented scope is a §5 diagnostic, never a marker comment.
- Python 3.10 syntax ceiling (no `match`, no 3.11 stdlib APIs); English identifiers; files ≤600 lines (400 soft, see header line rule); every module imports only stdlib + blcc siblings.
