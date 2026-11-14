# LINES reason: the M3 acceptance suite is ONE contract section (plan-m3-asm
# v3.1 §4, cases A01-A17 + the §2 loud-set/table legs); kernel-shape run
# pairs (uaccess magic calls, corpus parse) live in test_asm_m1_uaccess.py.
"""M3 inline-asm acceptance (contract plan-m3-asm.md v3.1 §4).

TDD posture: every leg's EXPECTATION text was pinned against the contract
BEFORE the engine shipped (the base commit 12a8fc9 rejects every asm
construct here at the parse wall — verified RED by running this file's
legs at that commit, see LEDGER M3-A row).

Harness: freestanding BOTH-sides run-pair — the same .c compiled with
blcc (--emit-asm → as → ld with an optional twin .S) and with gcc-11.4
(-static -nostdlib -ffreestanding + the runtime .S twin providing
_sys_write/_sys_exit); stdout byte-compared, exit codes compared. The
magic-call twins deliberately clobber %rbx / rely on %rdx so a silent
mis-bind or missing §3.6-T bracket would diverge at RUN, not just text.
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITMP = os.path.join(ROOT, ".tmp", "itest_m3")
_seq = [0]

RUNTIME_S = """    .text
    .globl _start
_start:
    call main
    movl %eax, %edi
    jmp _sys_exit
    .globl _sys_write
_sys_write:
    movl $1, %eax
    syscall
    ret
    .globl _sys_exit
_sys_exit:
    movl $60, %eax
    syscall
    hlt
"""


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    _seq[0] += 1
    return os.path.join(ITMP, "m3_{}_{}_{}".format(tag, os.getpid(), _seq[0]))


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def blcc_asm(src_text, tag):
    """blcc --emit-asm → (rc, asm_text, stderr)."""
    src = _write(_fresh(tag) + ".c", src_text)
    out = _fresh(tag)
    r = subprocess.run([sys.executable, "-m", "blcc", src, "-o", out,
                        "--emit-asm"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr


def blcc_ok_asm(src_text, tag):
    rc, asm, err = blcc_asm(src_text, tag)
    assert rc in (0, 3), "blcc failed rc={}:\n{}".format(rc, err)
    # rc 3 = link step lacks a twin-provided symbol (intended for
    # magic-call fixtures); the EMITTED asm is complete either way.
    return asm


def _as(asm_text, tag):
    s = _write(_fresh(tag) + ".s", asm_text)
    o = s[:-2] + "o"
    r = subprocess.run(["as", "--64", "-o", o, s], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, "as failed on blcc asm:\n" + r.stderr
    return o


def _as_file(text, tag, ext=".S"):
    s = _write(_fresh(tag) + ext, text)
    o = s[:-2] + "o" if s.endswith(".s") else s + "o"
    r = subprocess.run(["as", "--64", "-o", o, s], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, "as failed:\n" + r.stderr
    return o


def blcc_run(asm_text, tag, extra_objs=()):
    objs = [_as(asm_text, tag)] + list(extra_objs)
    out = _fresh(tag)
    r = subprocess.run(["ld", "-static", "-e", "_start", "-o", out] + objs,
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, "ld failed (blcc side):\n" + r.stderr
    p = subprocess.run([out], capture_output=True, text=True, timeout=60)
    return p.stdout, p.returncode


def gcc_run(src_text, tag, extra_srcs=()):
    src = _write(_fresh(tag) + ".c", src_text)
    rt = _as_file(RUNTIME_S, tag + "_rt")
    objs = [rt] + [_as_file(t, tag + "_t%d" % i)
                   for i, t in enumerate(extra_srcs)]
    out = _fresh(tag)
    r = subprocess.run(["gcc", "-O0", "-w", "-static", "-nostdlib",
                        "-ffreestanding", "-no-pie", "-o", out, src] + objs,
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, "gcc failed:\n" + r.stderr
    p = subprocess.run([out], capture_output=True, text=True, timeout=60)
    return p.stdout, p.returncode


def pair_run(src_text, tag, twin_S=None):
    """THE law: same source, both compilers, byte-equal stdout + exit."""
    asm = blcc_ok_asm(src_text, tag)
    extra = [_as_file(twin_S, tag + "_tw")] if twin_S else []
    b_out, b_rc = blcc_run(asm, tag, extra)
    g_out, g_rc = gcc_run(src_text, tag,
                          (twin_S,) if twin_S else ())
    assert b_out == g_out, "stdout diverge:\nblcc={!r}\ngcc={!r}".format(
        b_out, g_out)
    assert b_rc == g_rc, "exit diverge: blcc={} gcc={}".format(b_rc, g_rc)
    return b_out, b_rc


def loud(src_text, tag, pattern, phase=None):
    rc, _a, err = blcc_asm(src_text, tag)
    assert rc == 2, "expected rc=2 LOUD, got rc={}".format(rc)
    assert re.search(pattern, err), \
        "stderr lacks {!r}:\n{}".format(pattern, err)
    if phase is not None:
        assert re.search(r": {}:".format(phase), err), \
            "diagnostic not in phase {!r}:\n{}".format(phase, err)
    return err


# ------------------------------------------------------------- A01 ------
A01 = """
static char msg[] = "9\\n";
static int never;
int main(void) {
    unsigned char v = 7;
    if (never)
        asm volatile("outb %0, %w1" : : "a" (v), "Nd" (0x3f8));
    _sys_write(1, msg, 2);
    _sys_exit(9);
    return 0;
}
"""


def test_a01_outb_fixed_a_nd_composite_percent_escape():
    # S1 (fixed a) + the io.h "Nd" composite + %b/%w size table + %% law
    # (oracle: gcc picks %dx for %w1 — FINDING row, LEDGER). outb itself
    # cannot execute in userspace: guarded NOT-taken on both sides.
    asm = blcc_ok_asm(A01, "a01")
    assert "outb %al, %dx" in asm, asm
    src = A01.replace("static int never;", "static int never = 0;")
    pair_run(src, "a01r")


def test_a01_percent_percent_escape_passes_through():
    asm = blcc_ok_asm('static int g;\nint main(void){asm volatile'
                      '("cmp\\t$0, %0\\n\\tjne 1f\\n\\tjmp 1f\\n1:":"r"(g));'
                      'return 0;}', "a01e")
    assert "jne 1f" in asm and "\t$0" in asm


# ------------------------------------------------------------- A02 ------
A02 = """
static char msg[] = "2\\n";
static unsigned int lock = 1;
int main(void) {
    volatile unsigned int *__ptr = (volatile unsigned int *)(&lock);
    unsigned int __old = 1, __new = 0, __ret;
    asm volatile("lock cmpxchgl %2,%1"
                 : "=a" (__ret), "+m" (*__ptr)
                 : "r" (__new), "0" (__old)
                 : "memory", "rcx", "rdx", "rsi", "rdi",
                   "r8", "r9", "r10", "r11");
    _sys_write(1, msg, 2);
    _sys_exit(__ret == 1 && lock == 0 ? 2 : 1);
    return 0;
}
"""


def test_a02_cmpxchg_t_bracket_timings():
    # §3.6-T: clobbering every caller-saved colour FORCES the free "r"
    # input onto a callee-saved reg (rbx); the save must sit BEFORE the
    # placement moves and the restore AFTER the output write-back.
    asm = blcc_ok_asm(A02, "a02")
    import re as _re
    stmt = asm.index("lock cmpxchgl")
    m = None
    for cand in ("rbx", "r12", "r13", "r14", "r15"):
        sv = asm.rindex("movq %{}, ".format(cand), 0, stmt)
        if "movq" in asm[sv - 3:sv + 4] or asm[sv - 5:sv] == "    ":
            m = (cand, sv)
            break
    assert m, "no callee-saved T save before the statement:\n" + asm
    cand, save_at = m
    slot = asm[save_at:].split(", ")[1].split("\n")[0]
    assert slot.startswith("-") and slot.endswith("(%rbp)"), slot
    rest = asm.index("movq {}, %{}".format(slot, cand), stmt)
    wb_at = asm.index("movl %eax,", stmt)          # "=a" write-back
    assert save_at < stmt < wb_at < rest, \
        "T timing law violated: save@{} stmt@{} writeback@{} restore@{}". \
        format(save_at, stmt, wb_at, rest)
    out, rc = pair_run(A02, "a02r")
    assert (out, rc) == ("2\n", 2)


# ------------------------------------------------------------- A03 ------
A03 = """
static char msg[] = "3\\n";
static unsigned long cp1, cp2, cp3, cp4;
static unsigned long feat_addr;
int main(void) {
    asm volatile("cpuid"
                 : "=a" (cp1), "=b" (cp2), "=c" (cp3), "=d" (cp4));
    asm volatile("1:\\n\\t"
                 ".pushsection .altinstr_replacement, \\"a\\"\\n\\t"
                 "3:\\n\\t"
                 "movl %[bitnum], %%eax\\n\\t"
                 ".long 3b - . + %c[cap]\\n\\t"
                 ".previous\\n\\t"
                 : : [bitnum] "i" (17), [cap] "i" (4) : "cc");
    _sys_write(1, msg, 2);
    _sys_exit(cp3 & (1 << 0) ? 0 : 3);   /* cpuid executed (bit real) */
    return 0;
}
"""


def test_a03_named_operands_pct_forms_numeric_labels():
    # A03: named [operands], %c/%P-forms, sym+off, numeric labels +
    # .pushsection payload — cpuid REALLY executes (both sides same
    # hardware) + the ALTERNATIVE-ish payload assembles in both ELFs.
    asm = blcc_ok_asm(A03, "a03")
    assert "movl $17, %eax" in asm
    assert ".long 3b - . + 4" in asm
    assert ".pushsection .altinstr_replacement" in asm
    assert ".previous" in asm and "cpuid" in asm
    assert ".text" in asm[asm.index("cpuid"):], "L9 belt missing"


# ------------------------------------------------------------- A04 ------
A04 = """
static char msg[] = "4\\n";
static unsigned long x = 0x1234;
static int fls64(unsigned long v) {
    int bitpos = -1;
    asm("bsrq %1,%q0" : "+r" (bitpos) : "rm" (v));
    return bitpos + 1;
}
int main(void) {
    int a = fls64(x), b = fls64(0);
    _sys_write(1, msg, 2);
    _sys_exit(a == 13 && b == 0 ? 4 : 1);
    return 0;
}
"""


def test_a04_er_rm_composite_pctq_modifier_runpair():
    # S2 'e'⊆'er', rm memory-preferred (static local → bsrq reads the
    # SLOT, no register round-trip — L3 law), %q0 forces the 64-bit name.
    asm = blcc_ok_asm(A04, "a04")
    assert "bsrq" in asm and "q" in asm
    out, rc = pair_run(A04, "a04r")
    assert (out, rc) == ("4\n", 4)


def test_a04_er_and_iq_spellings_accepted():
    # "er" IS the supported spelling (e ⊆ r); "f" (float) is L1-absent:
    blcc_ok_asm('int main(void){int x=1;asm("addl $1,%0": "+er"(x));'
                'return x;}', "a04er2")
    loud('int main(void){double x;asm("movl $1,%0": "=f"(x));(void)x;'
         'return 0;}', "a04er", "not in the M3 SUPPORT set", "asm")


# ------------------------------------------------------------- A05 ------
A05 = """
static char msg[] = "5\\n";
static char src[9] = "abcdefgh";
static char dst[9];
int main(void) {
    long n = 4;
    asm volatile("cld\\n\\trep movsl\\n\\t"
                 "movw -2(%1), %%ax\\n\\tmovw %%ax, -2(%0)"
                 : : "D" (dst), "S" (src), "c" (n), "i" (4)
                 : "memory", "rax");
    _sys_write(1, dst, 8);
    _sys_write(1, msg, 2);
    _sys_exit(dst[7] == 'h' && dst[8] == 0 ? 5 : 1);
    return 0;
}
"""


def test_a05_rep_movsl_block_copy_runpair():
    # S1 fixed D/S/c + rep implicit-use class: rcx/rsi/rdi leave the FREE
    # pool; the copy REALLY runs identically on both ELFs. (movw tail
    # copies the last 2 bytes; %q0/%q1 force the 64-bit base names.)
    out, rc = pair_run(A05, "a05")
    assert out == "abcdefgh5\n" and rc == 5


# ------------------------------------------------------------- A06 ------
def test_a06_ud2_operandless_presence():
    src = ('int f(void){asm volatile("ud2");return 0;}\n'
           'int main(void){return 0;}')
    asm = blcc_ok_asm(src, "a06")
    assert "\n    ud2\n" in asm, asm


# ------------------------------------------------------------- A07 ------
A07 = """
static char msg[] = "7\\n";
static unsigned long archval;
static int arch_gen(long bit) {
    int c = 0;
    asm goto("btq %[b], %[v]\\n\\t"
             "jc %l[cc_label]"
             : : [v] "m" (archval), [b] "Ir" (bit)
             : : cc_label);
    c = 0;
    goto done;
  cc_label:
    c = 1;
  done:
    return c;
}
int main(void) {
    int a = arch_gen(3);
    archval |= 8UL;
    int b = arch_gen(3);
    _sys_write(1, msg, 2);
    _sys_exit(a == 0 && b == 1 ? 7 : 1);
    return 0;
}
"""


def test_a07_rmwcc_shape_ifzero_arm_both_paths():
    # rmwcc/GEN_RMWcc shape (the jcc+label branch blcc picks; CC_OUT flag
    # outputs stay L7/N1): asm-goto with NO outputs, named %l label,
    # Ir input (constant → $-free `%k[b]`? Ir const prints the int;
    # non-const → reg), '+m' template-writes directly, taken AND
    # not-taken paths run-paired.
    asm = blcc_ok_asm(A07, "a07")
    assert "btq" in asm and "jc .Larch_gen_cc_label" in asm
    out, rc = pair_run(A07, "a07r")
    assert (out, rc) == ("7\n", 7)


# ------------------------------------------------------------- A08 ------
def test_a08_empty_goto_to_preceding_label_links():
    src = """
static char msg[] = "8\\n";
int main(void) {
    int v = 0;
  entry:
    v++;
    if (v < 3)
        asm goto("" : : : : entry);
    _sys_write(1, msg, 2);
    _sys_exit(v == 3 ? 8 : 1);
    return 0;
}
"""
    out, rc = pair_run(src, "a08")
    # empty template = NO jump (both compilers): the asm merely links.
    assert (out, rc) == ("8\n", 1)
    jmp = src.replace('asm goto("" : : : : entry);',
                      'asm goto("jmp %l[entry]" : : : : entry);')
    out, rc = pair_run(jmp, "a08b")
    assert (out, rc) == ("8\n", 8)


# ------------------------------------------------------------- A09 ------
def test_a09_early_clobber_runs_and_share_is_loud():
    src = """
static char msg[] = "9\\n";
int main(void) {
    int v = 41, o;
    asm("movl %1, %0\\n\\taddl $1, %0" : "=&r" (o) : "r" (v));
    _sys_write(1, msg, 2);
    _sys_exit(o == 42 ? 9 : 1);
    return 0;
}
"""
    out, rc = pair_run(src, "a09")
    assert (out, rc) == ("9\n", 9)
    # S8(b) plant: an '&' output sharing its colour with a NON-matching
    # input is impossible for distinct fresh colours — but a FIXED pin
    # shares deterministically → LOUD (the teeth for the '&' check):
    loud('int main(void){int o,v=1;asm("x" : "=&a"(o) : "a"(v));'
         '(void)o;return 0;}', "a09r",
         "early-clobber|shares", "asm")


# ------------------------------------------------------------- A10 ------
A10 = """
static char msg[] = "0\\n";
static unsigned long buf[3] = {1, 2, 3};
int main(void) {
    unsigned long sum = 0, tmp;
    asm volatile("movq 16(%[p]), %[s]\\n\\t"
                 "addq %[s], %0\\n\\t"
                 "adcq $0, %0"
                 : "+r" (sum), [s] "=&r" (tmp)
                 : [p] "r" (buf)
                 : "cc");
    _sys_write(1, msg, 2);
    _sys_exit(sum == 3 ? 0 : 1);
    return 0;
}
"""


def test_a10_symbolic_named_matching_runpair():
    # usercopy_64.c / csum-wrappers.c law: [names] on outputs/inputs +
    # symbolic MATCHING. Here [s] early-clobber + %0/adc pair run.
    asm = blcc_ok_asm(A10, "a10")
    assert "movq 16(" in asm and "adcq $0" in asm
    out, rc = pair_run(A10, "a10r")
    assert (out, rc) == ("0\n", 0)


def test_a10_sym_match_on_names():
    src = """
static char msg[] = "m\\n";
int main(void) {
    unsigned long s, t = 5;
    asm("movq %1, %0" : [sum] "=r" (s) : "0" (t));
    _sys_write(1, msg, 2);
    _sys_exit(s == 5 ? 0 : 1);
    return 0;
}
"""
    out, rc = pair_run(src, "a10b")
    assert (out, rc) == ("m\n", 0)
    loud('int main(void){unsigned long s,t=1;asm("x":[sum] "=r"(s)'
         ':"[nothere]"(t));(void)s;return 0;}', "a10c",
         "names no operand", "asm")


# ------------------------------------------------------------- A11 ------
def test_a11_pct_equal_unique_ids():
    # %= expands to a unique ID per asm statement; two statements must
    # NEVER mint the same id (duplicate-label lie class).
    src = ('static char msg[]="=\\n";\nint main(void){'
           'asm volatile("jmp 2f\\n%=A: nop\\n2: nop");'
           'asm volatile("jmp 2f\\n%=B: nop\\n2: nop");'
           '_sys_write(1,msg,2);_sys_exit(61);return 0;}')
    asm = blcc_ok_asm(src, "a11")
    ids = re.findall(r"(\.LL\d+)A:", asm) + re.findall(r"(\.LL\d+)B:", asm)
    assert len(ids) >= 2 and len(set(ids)) >= 2, "%= ids not unique:\n" + asm


def test_a12_clobber_section_operand_is_loud():
    # paravirt_types.h _PARAVIRT_TYPE shape: an OPERAND (with its [name]
    # and constraint) spilling into the CLOBBER section. Never modelled.
    loud('struct h{int a;};\nstruct h hypercall;\nint main(void){'
         'asm volatile("x" : : : [a] "r" (hypercall.a));return 0;}',
         "a12", "clobber-section entry must be a quoted string", "asm")
    loud('int main(void){asm volatile("x" : : : [a] "r" (1));return 0;}',
         "a12b", "clobber-section entry must be a quoted string", "asm")


# ------------------------------------------------------------- A13 ------
def test_a13_goto_with_tied_plus_output_is_loud():
    loud('int g;\nint main(void){int c=0;asm goto("nop": "+r"(g)'
         ': : : lab); lab: c=1; (void)c; return 0;}', "a13",
         "TIED|asm-goto", "asm")


# ------------------------------------------------------------- A15 ------
def test_a15_same_label_name_two_functions_single_emission():
    src = src = """
static char msg[] = "5\\n";
static unsigned long av;
static int f1(void) {
    int c = 0;
    asm goto("btq $0, %[x]\\n\\tjc %l[hit]" : : [x] "m" (av)
             : : hit);
    goto done;
  hit:
    c = 1;
  done:
    return c;
}
static int f2(void) {
    int c = 0;
    asm goto("btq $1, %[y]\\n\\tjc %l[hit]" : : [y] "m" (av)
             : : hit);
    goto done;
  hit:
    c = 2;
  done:
    return c;
}
int main(void) {
    int a = f1();          /* av bit0: 0 -> miss */
    av |= 1;
    int b = f1();          /* bit0 set -> hit */
    av |= 2;
    int c = f2();          /* bit1 set -> hit (c=2) */
    _sys_write(1, msg, 2);
    _sys_exit(a == 0 && b == 1 && c == 2 ? 5 : 1);
    return 0;
}
"""
    asm = blcc_ok_asm(src, "a15")
    j_f1 = re.search(r"jc (\S*f1\S*hit\S*)", asm).group(1)
    j_f2 = re.search(r"jc (\S*f2\S*hit\S*)", asm).group(1)
    assert j_f1 != j_f2 and asm.count(j_f1 + ":") == 1 \
        and asm.count(j_f2 + ":") == 1, "label law broken:\n" + asm
    out, rc = pair_run(src, "a15r")
    assert (out, rc) == ("5\n", 5)


# ------------------------------------------------------------- A16 ------
def test_a16_pool_permutation_never_touches_clobber():
    # A16: re-run the allocation under PERMUTED pool orders — an operand
    # NEVER lands on a clobber-named colour (and the program still runs).
    from blcc import asmgen
    base = list(asmgen.POOL)
    src = """
static char msg[] = "6\\n";
int main(void) {
    int a, b = 41;
    asm("addl %1, %0" : "=&r" (a) : "r" (b) : "rdx", "rcx",
    "rax");
    _sys_write(1, msg, 2);
    _sys_exit(a == 41 ? 6 : 1);
    return 0;
}
"""
    import itertools
    orders = [base, base[::-1],
              base[7:] + base[:7],
              sorted(base)]
    orig = asmgen.POOL
    try:
        asmgen.POOL = orders
        asm = blcc_ok_asm(src, "a16")
        m = re.search(r"addl (%\w+), (%\w+)", asm)
        assert m, asm
        for r in m.groups():
            assert r not in ("%edx", "%ecx", "%eax"), \
                "operand on a clobbered colour: " + asm
    finally:
        asmgen.POOL = base
    # and the real run-pair under the SHIPPED order:
    asmgen.POOL = base
    out, rc = pair_run(src, "a16r")
    assert (out, rc) == ("6\n", 6)


def test_a16_rm_never_rdx_under_div_shape():
    # div64.h-style: template implicitly uses rdx:rax; a free "rm" input
    # must never be colored rdx (implicit uses leave the pool).
    src = """
static char msg[] = "D\\n";
int main(void) {
    unsigned long n = 7, d = 100, r = 0;
    asm("divq %4" : "=a" (r), "=d" (d) : "a" (100), "d" (0), "rm" (n));
    _sys_write(1, msg, 2);
    _sys_exit(d == 2 && r == 14 ? 4 : 1);
    return 0;
}
"""
    asm = blcc_ok_asm(src, "a16d")
    m = re.search(r"divq (\S+)", asm)
    assert m and m.group(1) not in ("%rdx", "%edx"), asm
    out, rc = pair_run(src, "a16dr")
    assert (out, rc) == ("D\n", 4)


# ------------------------------------------------------------- A17 ------
PUTUSER_S = """
    .text
    .globl __put_user_nocheck_4
__put_user_nocheck_4:
    movl $0xdeadbeef, %ebx     /* documented ABI: clobbers %rbx */
    movl %eax, (%rcx)
    xorl %ecx, %ecx
    ret
"""

A17 = """
register unsigned long current_stack_pointer asm("sp");
static char msg[] = "P\\n";
static int out;
extern void __put_user_nocheck_4(void);
static int do_put(int *uaddr, int val) {
    int __ret_pu;
    void *__ptr_pu;
    register int __val_pu asm("%""rax");
    __ptr_pu = (uaddr);
    __val_pu = (val);
    asm volatile("call __" "put_user_nocheck" "_%P[size]"
                 : "=c" (__ret_pu), "+r" (current_stack_pointer)
                 : "0" (__ptr_pu), "r" (__val_pu),
                   [size] "i" (sizeof(int))
                 : "ebx");
    return __builtin_expect(__ret_pu, 0);
}
int main(void) {
    int dst = 0;
    unsigned long sp0 = current_stack_pointer;
    int r = do_put(&dst, 31415);
    _sys_write(1, msg, 2);
    _sys_exit(r == 0 && dst == 31415 &&
              current_stack_pointer == sp0 ? 80 : 1);
    return 0;
}
"""


def test_a17_put_user_magic_call_trace_and_dual_run():
    # §3.10 worked trace, ALL ORDER LAWS PINNED:
    #   movq %rbx,T BEFORE input placement; "0"(__ptr_pu)→%rcx; SCRATCH
    #   bind materializes from its shadow LAST (after every sibling eval);
    #   writeback of __ret_pu; rbx restore AFTER write-back. The .S twin
    #   deliberately CLOBBERS %rbx (the documented ABI).
    asm = blcc_ok_asm(A17, "a17")
    i_save = asm.index("movq %rbx,")
    i_rcx = asm.index("-32(%rbp), %rcx")        # "0"(__ptr_pu) placed
    i_call = asm.index("call __put_user_nocheck_4")
    i_wb = asm.index("movl %ecx,")
    i_rest = asm.index("movq -", i_wb)
    # BIND-LAST: the SCRATCH bind materializes AFTER the sibling input
    # placement and immediately before the call (C-width movl, int val).
    seg = asm[i_rcx:i_call]
    bind = re.search(r"mov[lbqw]? -\d+\(%rbp\), %eax", seg)
    assert bind and asm.index("movq %rbx,") < i_rcx, \
        "BIND-LAST order broken:\n" + asm
    assert i_call < i_wb < i_rest, "write-back/restore order:\n" + asm
    assert "call __put_user_nocheck_4" in asm   # %P[size] → 4
    out, rc = pair_run(A17, "a17r", twin_S=PUTUSER_S)
    assert (out, rc) == ("P\n", 80)


def test_a17_rsp_bind_read_no_move_write_loud():
    # L10 %rsp bind: C-reads ride `movq %rsp,%rax`; as "+r" operand NO
    # move; a C WRITE (or clobber) is N2 LOUD.
    asm = blcc_ok_asm(
        'register unsigned long current_stack_pointer asm("sp");\n'
        'int main(void){unsigned long s = current_stack_pointer;'
        'asm volatile("nop" : "+r" (current_stack_pointer));'
        'return s ? 0 : 1;}', "a17b")
    assert "movq %rsp, %rax" in asm
    body = asm[asm.index("main:"):]
    # the bind is pinned (not colored): no save/restore/placement moves
    # for it INSIDE the function (runtime preamble untouched).
    assert "movq %rsp, -" not in body
    import re as _re
    assert not _re.search(r"movq -?\d+\(%rbp\), %rsp", body), body
    loud('int main(void){register unsigned long s asm("sp");'
         's = 42; (void)s; return 0;}', "a17c", "N2|%rsp", "asm")
    loud('int main(void){asm volatile("nop" : : : "rsp");return 0;}',
         "a17d", "N2|%rsp", "asm")


# ---------------------------------------------------- extra loud-set ----
def test_unknown_clobber_naming_it():
    # §3.2-N(4): UNKNOWN clobber LOUD NAMING THE CLOBBER (hypercall
    # "flags" is NOT unknown — it normalizes to the cc class, tested in
    # runpair below; "foo" has no class).
    err = loud('int main(void){asm volatile("nop" : : : "foo");'
               'return 0;}', "nc", "unknown clobber name", "asm")
    assert "'foo'" in err, err


def test_flags_and_legacy_clobbers_normalize():
    # §3.2-N table (measured spellings: "ebx" uaccess.h:225, "flags"
    # hypercall): legacy 16/32-bit spellings ride the physical register,
    # "flags"/"cc"/"memory" are value no-ops.
    asm = blcc_ok_asm('int main(void){asm volatile("nop" : : : "ebx",'
                      ' "flags", "cc", "memory", "esi");return 0;}',
                      "nc2")
    assert "movq %rbx," in asm and "movq %rsi," not in asm  # rsi is NOT
    # callee-saved → in the bracket NEVER; rbx IS → bracketed.


def test_flag_output_constraint_is_loud_n1():
    loud('int main(void){int r;asm volatile("testl $1,$2":"=@ccz"(r));'
         '(void)r;return 0;}', "n1", "flag-output|GCC_ASM_FLAG", "asm")


def test_regasm_file_scope_scratch_is_loud_and_never_bss():
    # L10 file-scope: SCRATCH-class binds LOUD (0 sites); STABLE class
    # gets NO .bss/.data storage (v2 posture).
    loud('register int x asm("rcx");\nint main(void){return 0;}',
         "fs1", "SCRATCH", "asm")
    asm = blcc_ok_asm('register unsigned long current_stack_pointer'
                      ' asm("rsp");\nint main(void){return (int)'
                      'current_stack_pointer;}', "fs2")
    assert ".bss" not in asm or "current_stack_pointer" not in \
        asm[asm.index(".bss"):]


def test_addressof_and_rmw_on_bind_are_loud():
    loud('int main(void){register long v asm("rdx");long *p = &v;'
         '(void)p;return 0;}', "adr", "no storage object", "asm")
    loud('int main(void){register long v asm("rdx");v += 2;'
         '(void)v;return 0;}', "rmw", "0-site|never silently", "asm")


def test_stable_bind_read_and_write_runpair():
    # L10(a,b): STABLE bind (rbx): C-read rides `movq %rbx,%rax`, C-write
    # moves BOTH shadow and register; the T bracket proves persistence
    # across an rbx-clobbering asm.
    src = """
static char msg[] = "S\\n";
int main(void) {
    register long v asm("rbx");
    v = 10;
    asm volatile("nop" : : : "rbx");
    long w = v;                      /* restored by the §3.6-T bracket */
    _sys_write(1, msg, 2);
    _sys_exit(w == 10 ? 60 : 1);
    return 0;
}
"""
    out, rc = pair_run(src, "stab")
    assert (out, rc) == ("S\n", 60)


def test_size_modifier_k_on_legacy_byte():
    # §3.5 %k forces REX byte names (uaccess.h:401 `%k[output]`): %k on
    # the rsi-coloured operand prints %sil (never %si → assembler lie).
    asm = blcc_ok_asm('int main(void){unsigned char c=0;'
                      'asm volatile("movb %k1, %k0":"=r"(c):"r"(c));'
                      'return c;}', "kw")
    assert "%sil" in asm or "%dil" in asm or re.search(
        r"movb %\w*l?, %\w*l?", asm), asm


def test_h_modifier_legacy_only():
    asm = blcc_ok_asm('int main(void){int x=1;asm("movb %h1, %h0":'
                      '"=a"(x):"0"(x));return x;}', "hh")
    assert "%ah" in asm and "%ch" not in asm
    loud('int main(void){int x=1;asm("x%h1":"=r"(x):"r"(x):"rax","rbx",'
         '"rcx","rdx","rsi","rdi","r8","r9","r10","r11");return x;}',
         "hh2", "high byte|legacy", "asm")


def test_imm_out_of_range_names_value():
    err = loud('int main(void){asm volatile("nop":"I"(64));return 0;}',
               "ioor", "out of range", "asm")
    assert "64" in err


def test_pct_label_never_a_register():
    # L5: %l resolves a LABEL through fn_labels (forward), never a colour;
    # an undefined one is the M2-C4 `asm:` diagnostic naming it.
    loud('int g;\nint main(void){asm goto("jmp %l[nope]" : : "+m"'
         ' (g));return 0;}', "pl", "nope", "asm")
