"""Freestanding Linux runtime per ARCHITECTURE.md §6.

Concerns: the frozen asm text constant (RUNTIME_ASM) and the builtin symbol
table (BUILTINS) shared with codegen. The blob is PURE AT&T syntax — the host
default for `as --64`; it never mixes Intel mnemonics and carries no
.intel_syntax directive (mixing caused 'too many memory references' in a
probe). Writable scratch would live in .data, but the blob needs none: the
§6 builtins are leaf syscalls and pure asm loops. No runtime.c exists
anywhere — blcc has no C compiler to compile one with (§6).

Mapping (Linux x86-64): syscall number in rax; args already in rdi/rsi/rdx
(System V matches the syscall register order); rcx/r11 clobbered by the
instruction itself. write=1, open=2, read=0, exit=60.
"""
from __future__ import annotations

# name -> (argc, return-kind). §6-pinned signatures, always in scope; this is
# the ONE builtin table — blcc/parser.py DERIVES its re-declaration guard
# (parser.BUILTINS) from these names (P3-4: one mechanism, one source).
BUILTINS = {
    "_sys_write": (3, "long"),   # long _sys_write(long fd, const char *buf, long len)
    "_sys_exit": (1, "void"),    # void _sys_exit(long code) — never returns
    "_sys_open": (2, "long"),    # long _sys_open(const char *path, long flags)
    "_sys_read": (3, "long"),    # long _sys_read(long fd, char *buf, long len)
    "strlen": (1, "long"),       # long strlen(const char *s)
    "strcmp": (2, "long"),       # long strcmp(const char *a, const char *b)
}

RUNTIME_ASM = """\
    .text
    .globl _start
# _start (§6): argc/argv/envp are already on the stack at entry; rsp is
# 16-byte aligned here, so the two calls below satisfy the ABI pin.
_start:
    movq (%rsp), %rdi           # argc
    leaq 8(%rsp), %rsi          # argv (strings stay at their stack addresses)
    call main
    movzbl %al, %edi            # exit code = main's rax & 0xff
    call _sys_exit              # never returns

# ---- §6 builtins: plain System-V leaves, args already in rdi/rsi/rdx ----

_sys_write:                     # syscall 1: write(fd, buf, len)
    movq $1, %rax
    syscall
    ret

_sys_open:                      # syscall 2: open(path, flags, mode=0)
    xorl %edx, %edx
    movq $2, %rax
    syscall
    ret

_sys_read:                      # syscall 0: read(fd, buf, len)
    xorl %eax, %eax
    syscall
    ret

_sys_exit:                      # syscall 60: exit(code); never returns
    movq $60, %rax
    syscall
1:  jmp 1b                      # unreachable safety net, loud-never trap

# strlen(s) -> rax = byte count before the NUL.
strlen:
    xorl %eax, %eax
1:  cmpb $0, (%rdi,%rax)
    je 2f
    incq %rax
    jmp 1b
2:  ret

# strcmp(a,b) -> 0 when equal, else the sign of the first byte difference.
strcmp:
1:  movzbl (%rdi), %eax
    movzbl (%rsi), %edx
    cmpl %edx, %eax
    jne 2f
    testl %eax, %eax
    je 3f
    incq %rdi
    incq %rsi
    jmp 1b
2:  subl %edx, %eax
    movslq %eax, %rax
    ret
3:  xorl %eax, %eax
    ret
"""
