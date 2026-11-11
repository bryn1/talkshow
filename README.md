# blcc

A C compiler written in pure stdlib Python 3 that accepts a documented C subset and emits
x86-64 AT&T assembly, assembled/linked with system `as`/`ld` into static, freestanding ELF
executables that run on Linux x86-64 — no libc, programs reach the kernel via raw syscalls.

"Compiles linux" means: compiles C *for* Linux; the produced binaries run on Linux.
Compiling the Linux kernel source is out of scope (see docs/ARCHITECTURE.md §1).

## Use

    python3 -m blcc samples/hello.c -o .tmp/hello && .tmp/hello
    bin/blcc samples/fib.c -o .tmp/fib --emit-asm -v

## Docs / tests

- Contract: docs/ARCHITECTURE.md (the one source of truth).
- Tests: `python3 -m pytest tests/ -q` (pytest is a host test runner, not a product dep).
