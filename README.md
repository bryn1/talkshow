# blcc

A C compiler written in pure stdlib Python 3 that accepts a documented C
subset and emits x86-64 AT&T assembly, assembled and linked with the system
`as` and `ld` into static, freestanding ELF executables that run on Linux
x86-64. There is no libc: programs reach the kernel through raw syscalls, and
the compiler ships its own `_start`.

blcc is a compiler *for* Linux — the binaries it produces run on Linux.
Compiling the Linux kernel source is GCC-scale work and is explicitly out of
scope; the preprocessing pipeline, however, is designed and tested against
the linux-5.10 kernel build: a GCC-differential test suite with a dedicated
KERNEL_510 tier, 2411 tests in total (see Tests below).

## What it is

- Accepts the documented C subset (contract §4), emits x86-64 AT&T assembly,
  and drives system `as` + `ld` into a static, non-PIE freestanding ELF.
- Freestanding: no libc, no libc headers, no dynamic linking. Implicit
  builtins (`_sys_write`, `_sys_open`, `_sys_read`, `_sys_exit`, `strlen`,
  `strcmp`) reach the kernel via raw syscalls; `_start` is compiler-shipped.
- Every unsupported or invalid input is a loud diagnostic — the cardinal
  failure (silently wrong code) is designed out.
- `docs/ARCHITECTURE.md` (v5.1, 153 lines) is the authoritative contract:
  scope, CLI, C subset, runtime, diagnostics, and the test inventory.

## Requirements

- Python 3, stdlib only — zero pip dependencies (the tree has no
  `requirements.txt`; every module imports stdlib and siblings only).
  The host reference is Ubuntu 22.04 with Python 3.10 (a 3.10 syntax ceiling
  is contract law).
- System GNU `as` and `ld` on `PATH` — invoked exactly as
  `as --64 -o <tmp>.o <file>.s` then `ld -static -o <output> <tmp>.o`.
- A Linux x86-64 host. Windows/macOS targets and other ISAs are out of scope.
- For running the test suite only: `pytest` (a host test runner, never
  imported by the compiler itself — not a product dependency).

## Install and quickstart

No package to install — clone the repository (`https://github.com/bryn1/talkshow`)
and run the compiler from the repo root as a Python module, or use the thin
exec wrapper under `bin/` (it forwards every argument and works from any
directory).

Compile and run a sample. This is real, verified output on Linux x86-64:

    $ python3 -m blcc samples/hello.c -o /tmp/hello && /tmp/hello
    Hello, Linux from blcc

The `samples/` directory ships 12 small programs (hello, arith, loop, fib,
array, strings, struct, grid, hostname, argv, switch, globmix). Each one's
exact stdout bytes and exit code are pinned in the contract (§7) and asserted
end-to-end by the test suite. Quoted `#include "..."` resolves includer-dir
first, so samples find their own `print.h` helper (`pstr`/`pint`/`pchar`).

## CLI

Two forms (this is the actual usage text the compiler prints):

    python3 -m blcc <input.c> [-o <output>] [--emit-asm] [-v]
    python3 -m blcc -E <input.c> [-D name[=tokens]] [-U name]
           [-I dir] [-isystem dir] [-nostdinc] [-include file] [-std=X]

| Flag | Effect (contract §2) |
|---|---|
| `-o FILE` | output binary path — REQUIRED for compilation (omitting it is a loud exit 2; gcc's implicit `<stem>.o` posture is deliberately not copied) |
| `--emit-asm` | keep and print the emitted asm; also writes `<output>.s` beside the binary (still assembles and links) |
| `-v` | echo each external `as` / `ld` command before running it |
| `-E` | preprocess only: stream to stdout, or to the `-o` FILE (gcc's measured `-E -o` sink); no `main` required |
| `-D name[=tokens]` | define a macro, applied after builtins; bare `-Dname` is exactly `-Dname=1`; function-like spellings (`-D SQ(x)=((x)*(x))`) are valid |
| `-U name` | undefine a macro (a builtin pop warns, gcc-style) |
| `-I dir` / `-isystem dir` | include search dirs; `#include <...>` resolves through these ONLY — there are no default system directories |
| `-nostdinc` | accepted (there are no default system dirs to drop anyway) |
| `-include file` | force-include before the main file (resolves CWD, then -I, then -isystem) |
| `-std=X` | selects the predefined-macro profile; the accepted spellings are `c89` `c90` `gnu89` `gnu90` `c94` `gnu94` `c99` `gnu99` `c11` `gnu11` `c17` `gnu17` `c2x` `gnu2x` `iso9899:1990` `iso9899:199409` `iso9899:1999` `iso9899:2011` (`c90`/`gnu90` alias `c89`/`gnu89`; the set is the driver's validation table); an unknown spelling exits 2 |
| `-c` | compile to the `-o` file as an object (no link) — M4 kernel-integration mode; requires `-o` (without it, a loud exit 2). Backed by the driver and `tests/test_core_m4w0.py`; the printed usage text above does not list it |

Exit codes: `0` success; `2` compile or preprocessor error (a
`file:line:col: <phase>: <message>` diagnostic on stderr); `3` assembler or
linker failure (the tool's stderr passed through). Scratch files live under
the repo `.tmp/` and are removed on success.

Concrete, verified examples — preprocess a sample, or compile with the
wrapper while keeping the asm and echoing the toolchain calls:

    $ python3 -m blcc -E samples/loop.c | head
    $ bin/blcc samples/fib.c -o /tmp/fib --emit-asm -v
    $ /tmp/fib
    fib(20)=6765

## Supported C

A readable summary of contract §4 (the contract owns the exact pins):

- **Types:** `char` `short` `int` `long` `void` (1/2/4/8 bytes, pointers 8),
  structs, fixed-size arrays of any rank, `typedef`, `enum` constants. All
  values live in 64-bit slots with pinned per-width re-interning rules.
- **Initializers:** brace lists at every level, char arrays from string
  literals, zero-filled tails; globals land in `.data`/`.bss`.
- **Functions:** prototypes, definitions, calls, recursion, and
  `main(int argc, char **argv)`; file-scope `static`.
- **Control:** `if`/`else`, `while`, `do…while`, `for`, `switch`/`case`/
  `default`, `break`, `continue`, `return`, nested blocks.
- **Operators:** arithmetic (division truncates toward zero, pinned), bitwise
  including shifts, comparisons, short-circuit `&&`/`||`, compound
  assignment, `++`/`--`, `sizeof` (type / identifier / parenthesized
  expression forms), casts, address-of and dereference.
- **Strings:** literals become `.rodata` byte arrays typed `char *`; the
  escape set is pinned (including `\x` taking EXACTLY two hex digits, with no
  maximal-munch consumption: `"\x80ab"` is three characters).
- **Not in the subset** (contract §5 — every one is a loud, naming
  diagnostic): `float`/`double`, `goto` and labels, unions, bitfields,
  function pointers, variadic functions, struct assignment/comparison, and
  multi-file linking beyond `#include` inlining (exactly one translation
  unit reaches `as`).

## Preprocessor (M1)

GCC-grade preprocessing, built to the oracle's measured behavior rather than
to assumptions:

- The full directive set — `#include` (quoted and angled, with macro-expanded
  operands), `#define`/`#undef` (object- and function-like, GNU variadics),
  `#if`/`#ifdef`/`#ifndef`/`#elif`/`#else`/`#endif`, `#error`, `#warning`,
  `#line`, `#pragma` pass-through (emitted in `-E` mode only) — plus `#`
  stringify, `##` paste, and blue-paint recursion hiding.
- Predefined macros are GENERATED DATA captured from gcc 11.4 per `-std`
  profile (regenerable via `scripts/gen_predefines_table.py`), not a
  hand-picked table.
- Behavior is pinned by a GCC-differential suite (`tests/test_pp_differential_m1.py`):
  snippet-tier rows diff the compiler's `-E` stream against `gcc -E` token
  streams, and
  kernel-tier rows diff the linux-5.10 P1–P5 headers with the real Kbuild
  flag set. Kernel-tier rows skip unless `KERNEL_510` points at a
  linux-5.10 tree.
- Kernel-build option inventory: every option spelling the real linux-5.10
  tinyconfig reference build emits (2806 distinct spellings measured across
  its 777 command records) is classified against gcc — preprocessing-surface
  spellings are measured-equal, and at the M1-c7 measurement every cc-phase
  flag exited 2 naming the flag (never a silent pretend-support). Kernel-
  integration work has since SHIPPED `-c` — compile to the `-o` operand as an
  object file, stopping before the link (per the driver and
  `tests/test_core_m4w0.py`) — so the inventory's classification is a
  measurement record, not a frozen promise; the still-unshipped flags
  (`-Wall`, `-O2`, …) exit 2 naming the flag. See the inventory table in
  contract §2.

## Tests

    python3 -m pytest tests/ -q

The suite is 2411 collected tests: lexer/preprocessor/parser/codegen/driver
unit files, end-to-end runs of every §7 sample asserting exact stdout and
exit codes, negative suites asserting the loud-diagnostic contract,
regression files per fix cycle, and the GCC-differential suite described
above (its kernel-tier legs activate when the `KERNEL_510` environment
variable names a linux-5.10 tree; unset, they skip). Deterministic: no
network, samples write only under `.tmp/`, no third-party deps.

## Architecture

`docs/ARCHITECTURE.md` is the authoritative contract. Every module listed
there implements exactly what it says.

## Scope and limits

- Static, non-PIE freestanding ELF for Linux x86-64 only — no PIE or dynamic
  linking, no Windows/macOS targets, no other ISAs, no precompiled output
  other than ELF.
- Freestanding: no libc and no bundled system headers. `#include <...>`
  resolves through `-I`/`-isystem` ONLY; a missing header is a loud
  preprocessor diagnostic.
- One translation unit reaches the assembler; multi-file linking is out.
- Compiling the Linux kernel source is OUT of scope and never claimed —
  what is built and tested against the kernel is the *preprocessing*
  pipeline (KERNEL_510 differential tier, 2411 tests).
- Anything outside the §4 subset fails LOUD (exit 2, construct named);
  guessing codegen for input the contract rejects is the one failure mode
  the design forbids.
