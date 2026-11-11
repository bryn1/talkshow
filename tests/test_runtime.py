"""§6/§9: runtime blob symbols, AT&T purity, syscall numbers, and a live
assemble+link+run through the shipped blob (no skips: as/ld are §10 deps)."""
import os
import re
import subprocess

from blcc.runtime import BUILTINS, RUNTIME_ASM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp")


def test_blob_defines_start_and_the_six_builtins():
    for sym in ("_start", "_sys_write", "_sys_exit", "_sys_open",
                "_sys_read", "strlen", "strcmp"):
        assert "\n{}:".format(sym) in RUNTIME_ASM + "\n", sym


def test_builtin_symbol_table_matches_six_pin():
    assert BUILTINS["_sys_write"] == (3, "long")
    assert BUILTINS["_sys_exit"] == (1, "void")
    assert BUILTINS["_sys_open"] == (2, "long")
    assert BUILTINS["_sys_read"] == (3, "long")
    assert BUILTINS["strlen"] == (1, "long")
    assert BUILTINS["strcmp"] == (2, "long")
    assert set(BUILTINS) == {"_sys_write", "_sys_exit", "_sys_open",
                             "_sys_read", "strlen", "strcmp"}


def test_blob_is_pure_att_never_intel():
    assert ".intel_syntax" not in RUNTIME_ASM
    # Intel's tell is a bare register token; AT&T prefixes every register
    # with % (symbol operands like "call main" are legal in both, registers
    # are the discriminator). Comment-free lines only.
    code = "\n".join(ln.split("#")[0] for ln in RUNTIME_ASM.splitlines())
    regs = (r"\b(?:r(?:[0-9]|1[0-5]|ax|bx|cx|dx|si|di|sp|bp)[dwbx]?"
            r"|e(?:ax|bx|cx|dx|si|di|sp|bp)|[abcde]X|[abcdSsDdIiPp][LlXx]"
            r"|ah|ch|dh|bh)\b")
    for m in re.finditer(regs, code):
        assert m.start() > 0 and code[m.start() - 1] == "%", \
            "Intel-style bare register: {!r}".format(code[max(0, m.start()-20):m.end()])
    for num in ("$1,", "$2,", "$60,"):     # write / open / exit numbers
        assert num in RUNTIME_ASM


def test_blob_links_and_exits_with_main_low_byte():
    stub = RUNTIME_ASM + """    .text
main:
    pushq %rbp
    movq %rsp, %rbp
    movq $257, %rax             # _start must exit with rax & 0xff = 1
    popq %rbp
    ret
"""
    os.makedirs(TMP, exist_ok=True)
    base = os.path.join(TMP, "rt_probe.{}".format(os.getpid()))
    open(base + ".s", "w").write(stub)
    r = subprocess.run(["as", "--64", "-o", base + ".o", base + ".s"],
                       capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    r = subprocess.run(["ld", "-static", "-o", base, base + ".o"],
                       capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    assert subprocess.call([base]) == 1          # exit code = 257 & 0xff
    for suffix in ("", ".s", ".o"):
        os.remove(base + suffix)
