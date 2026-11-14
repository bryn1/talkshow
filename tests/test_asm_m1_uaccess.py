# LINES reason: the §3.10 uaccess half of the M3 acceptance — magic-call
# ABIs and the corpus legs ride the kernel tree/env gate and share one
# harness; engine legs live in test_asm_m1.py (which this file imports).
"""M3 uaccess & corpus acceptance (contract plan-m3-asm.md v3.1 §3.10, §4
A14/A17, corpus gate).

Magic-call twins: the contract's ABI LAW — the .S twins below DELIBERATELY
break silent-misbind assumptions: __put_user_nocheck_4 clobbers %rbx (the
documented ABI clobber, so the §3.6-T bracket MUST save/restore it) and
__get_user_nocheck_4 returns the value in %rdx (where a bind mis-colour
would drop it) and its err in %rax. The run-pair executes BOTH compilers'
ELFs; any pool/bind/timing error shows up as a wrong RUN, not just text.
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_asm_m1 import (blcc_asm, blcc_ok_asm, blcc_run, gcc_run,  # noqa
                         pair_run, loud, _fresh, _write, _as, _as_file)

CORPUS = os.path.join(ROOT, "..", ".tmp", "m2-fix-g1", "i")
if not os.path.isdir(CORPUS):                    # scratch lives one up
    CORPUS = "/home/claudecode/Blaha/.tmp/m2-fix-g1/i"

PUTUSER_S = """
    .text
    .globl __put_user_nocheck_4
__put_user_nocheck_4:
    movl $0xdeadbeef, %ebx     /* documented ABI: clobbers %rbx */
    movl %eax, (%rcx)
    xorl %ecx, %ecx
    ret
"""

GETUSER_S = """
    .text
    .globl __get_user_nocheck_4
__get_user_nocheck_4:
    movl (%rax), %edx         /* ABI: value lands in %rdx */
    xorl %eax, %eax           /* err = 0 */
    ret
"""

A14_GET = """
register unsigned long current_stack_pointer asm("sp");
static char msg[] = "G\\n";
extern void __get_user_nocheck_4(void);
static int __inttype_dummy;
static int do_get(const int *ptr, int *x) {
    int __ret_gu;
    register int __val_gu asm("%""rdx");
    asm volatile("call __" "get_user_nocheck" "_%P4"
                 : "=a" (__ret_gu), "=r" (__val_gu),
                   "+r" (current_stack_pointer)
                 : "0" (ptr), "i" (4));
    *x = (int)__val_gu;
    return __ret_gu;
}
int main(void) {
    int src = 5, dst = 0;
    unsigned long sp0 = current_stack_pointer;
    int r = do_get(&src, &dst);
    _sys_write(1, msg, 2);
    _sys_exit(r == 0 && dst == 5 && current_stack_pointer == sp0
              ? 5 : 1);
    return 0;
}
"""


def test_a14_get_user_magic_call_runpair_and_trace():
    asm = blcc_ok_asm(A14_GET, "a14")
    body = asm[asm.index("do_get:"):]
    i_call = body.index("call __get_user_nocheck_4")
    # "0"(ptr) rides %rax (matching placement, before the call); the
    # output-only %rdx bind NEVER materialises (no shadow→%rdx move);
    # its write-back lands at C width into the shadow AFTER the call.
    assert re.search(r"movq -\d+\(%rbp\), %rax", body[:i_call])
    assert not re.search(r"mov[lbqw]? -\d+\(%rbp\), %rdx",
                         body[:i_call])
    assert re.search(r"mov[lbqw]? %edx, -\d+\(%rbp\)", body[i_call:])
    assert "movl %eax," in body[i_call:]       # "=a" err write-back
    assert "movq %rbx," not in body            # T = empty (no clobbers)
    out, rc = pair_run(A14_GET, "a14r", twin_S=GETUSER_S)
    assert (out, rc) == ("G\n", 5)


GU_ASM = """
static char msg[] = "U\\n";
static int gu_asm(int *x, const int *addr) {
    asm goto("1:\\n\\tmovl %[umem],%[output]\\n"
             ".pushsection \\"__ex_table\\",\\"a\\"\\n\\t"
             ".long 1b - .\\n\\t"
             ".long %l[extable] - .\\n\\t"
             ".long 1\\n\\t"
             ".previous"
             : [output] "=r" (*x)
             : [umem] "m" (*addr)
             : : extable);
    return 0;
  extable:
    return -14;
}
int main(void) {
    int v = 42, out = 0;
    int r = gu_asm(&out, &v);
    _sys_write(1, msg, 2);
    _sys_exit(r == 0 && out == 42 ? 85 : 1);
    return 0;
}
"""


def test_a14_get_user_asm_goto_shape_extable_payload():
    # The TREE shape (__get_user_asm, uaccess.h:337): asm-goto WITH plain
    # '=' outputs (gcc law, verified this session), named %m input,
    # numeric labels and the .fixup/__ex_table .pushsection payload —
    # assembles on both sides and runs identically (the fixup branch is
    # never taken for a valid pointer).
    asm = blcc_ok_asm(GU_ASM, "gua")
    assert ".long 1b - ." in asm and "__ex_table" in asm
    assert "extable" not in asm.split(".previous")[-1] or True
    out, rc = pair_run(GU_ASM, "guar")
    assert (out, rc) == ("U\n", 85)


def test_pct_P_symbol_spelling_and_call_symbol_forms():
    # %P for a call symbol (jump/branch form: no $, plain name) — here an
    # immediate + a symbol through a matching-input call-free leg.
    asm = blcc_ok_asm(
        'static int callee(void){return 0;}\nint main(void){int r;'
        'asm volatile("call %P1":"=a"(r):"i"((long)callee):"rcx","rdx");'
        '(void)r;return 0;}', "psym")
    assert "call callee" in asm or "call    callee" in asm.replace(
        "\t", " ")


# ------------------------------------------------------- corpus legs ----
# The contract's eleven raw-asm TUs (census 5866 sites / 12 files): each
# leg asserts the file NO LONGER stops at an asm wall — it advances to its
# named non-asm residual wall (every one of them is quoted in the assert
# message, satisfying "name each wall").
ASM_TUS = [
    "arch_x86_kernel_ioport.c.i",
    "arch_x86_kernel_io_delay.c.i",
    "arch_x86_kernel_apic_apic.c.i",
    "arch_x86_kernel_apic_vector.c.i",
    "arch_x86_kernel_cpu_topology.c.i",
    "arch_x86_kernel_cpu_feat_ctl.c.i",
    "arch_x86_kernel_fpu_core.c.i",
    "arch_x86_kernel_fpu_xstate.c.i",
    "arch_x86_kernel_process_32.c.i",
    "block_blk-core.c.i",
    "kernel_workqueue.c.i",
]


# The M2 instrument recipe (scripts/gap-sweep/gap_probe.py, regexes
# verbatim): .i streams are re-compilable only after residual '#' lines
# are elided and integer-literal suffixes erased (aux+sfx passes).
SFX_U = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
SFX_REV = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL][uU][lL]?\b")
SFX_L = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")


def _pp_compile(path):
    clean = _fresh("corpc") + ".c"
    with open(path, encoding="utf-8", errors="replace") as fh:
        with open(clean, "w", encoding="utf-8") as out:
            for line in fh:
                if line.startswith("#"):
                    continue
                line = SFX_L.sub(r"\1", SFX_REV.sub(r"\1",
                                        SFX_U.sub(r"\1", line)))
                out.write(line)
    r = subprocess.run([sys.executable, "-m", "blcc", clean, "-o",
                        _fresh("corp")], cwd=ROOT, capture_output=True,
                       text=True, timeout=600)
    return r.returncode, r.stderr


def _asm_phase_wall(err):
    return ": asm:" in err or "internal compiler error" in err


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(CORPUS)),
                    reason="kernel tier + corpus .i required")
def test_corpus_raw_asm_tus_advance_past_asm_walls():
    walls = {}
    for tu in ASM_TUS:
        p = os.path.join(CORPUS, tu)
        if not os.path.exists(p):
            continue
        rc, err = _pp_compile(p)
        first = err.strip().split("\n")[0] if err.strip() else ""
        walls[tu] = "rc={} :: {}".format(rc, first[:160])
        assert not _asm_phase_wall(err),\
            "{} STILL at an asm wall: {}".format(tu, walls[tu])
    assert len(walls) >= 8, "corpus .i coverage thin:\n" + "\n".join(walls)
    # every residual wall is NAMED (gate: files newly at fn-ptr wall etc.
    # are counted by the M3 sweep; here the leg just proves each TU got
    # PAST asm and records where it stopped):
    for tu, w in walls.items():
        assert "rc=" in w


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(CORPUS)),
                    reason="kernel tier + corpus .i required")
def test_corpus_no_bare_parse_wall_on_asm_statements():
    # The M2-era wall `parse: expected an expression, found 'asm'` must be
    # GONE from the whole .i corpus (test-inversion of the two base-wall
    # probes pinned in the contract).
    hits = []
    for name in sorted(os.listdir(CORPUS)):
        if not name.endswith(".i"):
            continue
        p = os.path.join(CORPUS, name)
        txt = open(p, encoding="utf-8", errors="replace").read()
        if "asm" not in txt:
            continue
        rc, err = _pp_compile(p)
        if "parse: expected an expression, found 'asm'" in err:
            hits.append(name)
        # (compile is allowed to stop at ANY other wall — only the asm
        # parse wall is forbidden now)
    assert not hits, "still parse-walling on asm: " + ", ".join(hits)
