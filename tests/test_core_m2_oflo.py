"""§1 row 16 (M53): __builtin_{add,sub,mul}_overflow — MC 12460 build c3.

Law measured against gcc 11.4.0 -std=gnu89 (.tmp/m2-scratch/c6/probes,
oflo3.c + ofshape.c): flag = the TRUE result is outside the RESULT type
(f == 0/1, never anything else); the stored value is the low bits of the
true result reinterpreted as the result type. gcc -O0 Case-B codegen is
a truncation-equality check (movslq/movl + cmpq/jne), plus a jno OF-leg
ONLY when operands AND result are signed (f1/f2 drop it; blcc mirrors
this exactly, extremes like LONG_MAX*2 alias to flag 0 in gcc AND blcc).
WIDTH legs (result width == operand width == result sign): one hardware
op at that width — addb/addw/addl/addq + seto, unsigned setc, imull/
imulq + seto for w>=4; char/short MUL rides the wide path (no imulb/w).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp", "itoflo")
_seq = [0]


def _paths(tag):
    os.makedirs(TMP, exist_ok=True)
    _seq[0] += 1
    base = os.path.join(TMP, "of_{}_{}_{}".format(tag, os.getpid(), _seq[0]))
    return base + ".c", base + ".blcc", base + ".gcc"


def both_run(src, tag):
    src_path, b_out, g_out = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                         "-o", b_out], cwd=ROOT, capture_output=True,
                        text=True, timeout=60)
    try:
        assert rb.returncode == 0, \
            "blcc compile failed ({}):\n{}".format(tag, rb.stderr)
        rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", src_path,
                             "-o", g_out], capture_output=True, text=True,
                            timeout=60)
        assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
            tag, rg.stderr)
        pb = subprocess.run([b_out], capture_output=True, timeout=30)
        pg = subprocess.run([g_out], capture_output=True, timeout=30)
        assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
            "run-pair mismatch ({}): blcc={} gcc={}".format(
                tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    finally:
        for p in (src_path, b_out, g_out):
            if os.path.exists(p):
                os.remove(p)


def blcc_loud(src, tag, family="sema", needle=None):
    src_path, b_out, _ = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                             "-o", b_out], cwd=ROOT, capture_output=True,
                            text=True, timeout=60)
        assert rb.returncode == 2, \
            "{} must LOUD, rc={}\n{}".format(tag, rb.returncode, rb.stderr)
        assert ": {}:".format(family) in rb.stderr, \
            "{} landed outside the {} family:\n{}".format(
                tag, family, rb.stderr)
        if needle is not None:
            assert needle in rb.stderr, \
                "{} must name {!r}:\n{}".format(tag, needle, rb.stderr)
    finally:
        for p in (src_path, b_out):
            if os.path.exists(p):
                os.remove(p)


def blcc_asm(src, tag):
    src_path, b_out, _ = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                         "-o", b_out, "--emit-asm"], cwd=ROOT,
                        capture_output=True, text=True, timeout=60)
    s_path = b_out + ".s"
    try:
        assert rb.returncode == 0, \
            "{} must compile:\n{}".format(tag, rb.stderr)
        return open(s_path, encoding="utf-8").read()
    finally:
        for p in (src_path, b_out, s_path):
            if os.path.exists(p):
                os.remove(p)


# ------------------------------------------------------------------ run-pairs

def test_oflo_width_add_sub_run_pair():
    # WIDTH legs: one hardware op at the result width, flag from OF/CF.
    # Every value leg is SEQUENCED (stored, then checked — the c2 probe
    # finding: same-arg-list reads showed stale re-interned values).
    both_run("""
#include-less-never
struct R { int pad; };
char c1; int f1;
int main(void) {
    int r; int f;
    { char a; a = 0; f = __builtin_add_overflow((char)60, (char)20, &a);
      r = a; if (f != 0) return 1; if (r != 80) return 2; }
    { char a; f = __builtin_add_overflow((char)-128, (char)-1, &a);
      r = a; if (f != 1) return 3; if (r != 127) return 4; }
    { short a; f = __builtin_add_overflow((short)32000, (short)1000, &a);
      r = a; if (f != 1) return 5; if (r != -32536) return 6; }
    { int a; f = __builtin_add_overflow(2147483647, 1, &a);
      r = a; if (f != 1) return 7; if (r != -2147483648) return 8; }
    { int a; f = __builtin_sub_overflow(-2147483648, 1, &a);
      r = a; if (f != 1) return 9; if (r != 2147483647) return 10; }
    { long a; f = __builtin_add_overflow(9223372036854775807L, 1L, &a);
      if (f != 1) return 11; if (a != -9223372036854775807L - 1) return 12; }
    { unsigned char a; f = __builtin_add_overflow(255u, 1u, &a);
      r = a; if (f != 1) return 13; if (r != 0) return 14; }
    { unsigned short a; f = __builtin_add_overflow(65535u, 1u, &a);
      r = a; if (f != 1) return 15; if (r != 0) return 16; }
    { unsigned int a; f = __builtin_add_overflow(4294967295u, 1u, &a);
      if (f != 1) return 17; if (a != 0u) return 18; }
    { unsigned long a; f = __builtin_add_overflow(
          18446744073709551615ul, 1ul, &a);
      if (f != 1) return 19; if (a != 0ul) return 20; }
    return 0;
}
""".replace("#include-less-never\n", ""), "w")


def test_oflo_mul_run_pair():
    both_run("""
int main(void) {
    int r; int f;
    { char a; f = __builtin_mul_overflow((char)60, (char)20, &a);
      r = a; if (f != 1) return 1; if (r != -80) return 2; }
    { unsigned char a; f = __builtin_mul_overflow(20u, 20u, &a);
      r = a; if (f != 1) return 3; if (r != 144) return 4; }
    { short a; f = __builtin_mul_overflow((short)300, (short)300, &a);
      r = a; if (f != 1) return 5; if (r != 24464) return 6; }
    { int a; f = __builtin_mul_overflow(100000, 100000, &a);
      r = a; if (f != 1) return 7; if (r != 1410065408) return 8; }
    { int a; f = __builtin_mul_overflow(10, 20, &a);
      r = a; if (f != 0) return 9; if (r != 200) return 10; }
    { unsigned int a; f = __builtin_mul_overflow(65536u, 65536u, &a);
      if (f != 1) return 11; if (a != 0u) return 12; }
    { int a; f = __builtin_mul_overflow(100000L, 100000L, &a);
      r = a; if (f != 1) return 13; if (r != 1410065408) return 14; }
    { int a; f = __builtin_mul_overflow(10L, 20L, &a);
      r = a; if (f != 0) return 15; if (r != 200) return 16; }
    return 0;
}
""", "mul")


def test_oflo_wide_narrow_run_pair():
    # Case B: operand width != result width, or sign mismatch — the true
    # value is range-checked (gcc f1..f6 mirror); int operands widened
    # into long NEVER flag (their true sum always fits — measured).
    both_run("""
int main(void) {
    int r; int f;
    { unsigned char a; f = __builtin_add_overflow(5, -1, &a);
      r = a; if (f != 0) return 1; if (r != 4) return 2; }
    { unsigned char a; f = __builtin_add_overflow(260, 0, &a);
      r = a; if (f != 1) return 3; if (r != 4) return 4; }
    { unsigned char a; f = __builtin_sub_overflow(-5, 0, &a);
      r = a; if (f != 1) return 5; if (r != 251) return 6; }
    { int a; f = __builtin_sub_overflow(0u, 1u, &a);
      r = a; if (f != 0) return 7; if (r != -1) return 8; }
    { int a; f = __builtin_add_overflow(4294967295u, 4294967295u, &a);
      r = a; if (f != 1) return 9; if (r != -2) return 10; }
    { int a; f = __builtin_add_overflow(100L, 200L, &a);
      r = a; if (f != 0) return 11; if (r != 300) return 12; }
    { int a; f = __builtin_add_overflow(2147483647L, 1L, &a);
      r = a; if (f != 1) return 13; if (r != -2147483648) return 14; }
    { int a; f = __builtin_add_overflow(9223372036854775807L, 1L, &a);
      r = a; if (f != 1) return 15; if (r != 0) return 16; }
    { long a; f = __builtin_add_overflow(2147483647, 2147483647, &a);
      if (f != 0) return 17; if (a != 4294967294L) return 18; }
    { unsigned int a; f = __builtin_add_overflow(
          4294967296ul, 0ul, &a);
      if (f != 1) return 19; if (a != 0u) return 20; }
    return 0;
}
""", "wide")


def test_oflo_side_effects_run_pair():
    # The three arguments evaluate EXACTLY once, left to right, and the
    # result pointer is a full expression (p->slot through an arrow).
    both_run("""
struct P { int slot; int pad; };
struct P p;
int i;
int g;
int bump(void) { g = g + 1; return 7; }
int main(void) {
    int f;
    i = 41;
    f = __builtin_add_overflow(i++, 1, &p.slot);
    if (f != 0 || i != 42 || p.slot != 42) return 1;
    f = __builtin_add_overflow(bump(), bump(), &p.pad);
    if (f != 0 || g != 2 || p.pad != 14) return 2;
    if (p.slot != 42) return 3;
    return 0;
}
""", "side")


# -------------------------------------------------------------------- LOUDs

def test_oflo_arity_is_loud():
    blcc_loud("""
int main(void) { int r; return __builtin_add_overflow(1, 2, &r) + __builtin_add_overflow(1, &r); }
""", "of-arity", needle="3 arguments")


def test_oflo_pointer_operand_is_loud():
    blcc_loud("""
int a; int *p;
int main(void) { int r; return __builtin_add_overflow(p, 1, &r); }
""", "of-operand", needle="scalar integer")


def test_oflo_result_not_pointer_is_loud():
    blcc_loud("""
int main(void) { int r = 0; return __builtin_add_overflow(1, 2, r); }
""", "of-resptr", needle="pointer")


def test_oflo_result_float_is_loud():
    blcc_loud("""
float f;
int main(void) { return __builtin_add_overflow(1, 2, &f); }
""", "of-float", needle="scalar integer")


# ------------------------------------------------------------------- asm pins

def test_oflo_asm_width_and_flag_shapes():
    # The WIDTH legs must ride the per-width hardware op (the mutation
    # plant spec names: a width-ignoring implementation breaks the addb
    # leg, a seto/setc swap breaks the unsigned leg).
    asm = blcc_asm("""
char cb; short sb; int ib; long lb; unsigned char cub; unsigned short sub_b;
int fc(char a, char b) { return __builtin_add_overflow(a, b, &cb); }
int fs(short a, short b) { return __builtin_add_overflow(a, b, &sb); }
int fi(int a, int b) { return __builtin_add_overflow(a, b, &ib); }
int fl(long a, long b) { return __builtin_add_overflow(a, b, &lb); }
int fuc(unsigned char a, unsigned char b) { return __builtin_add_overflow(a, b, &cub); }
int fus(unsigned short a, unsigned short b) { return __builtin_sub_overflow(a, b, &sub_b); }
int main(void) { return fc(1, 2) + fs(1, 2) + fi(1, 2) + fl(1, 2)
                 + fuc(1, 2) + fus(2, 1); }
""", "oflo-asm")
    assert "addb %cl, %al" in asm or "addb " in asm, "char addb leg missing"
    assert "addw " in asm, "short addw leg missing"
    assert "addl " in asm, "int addl leg missing"
    assert "addq " in asm, "long addq leg missing"
    assert "seto %sil" in asm or "seto " in asm, "signed seto leg missing"
    assert "setc " in asm, "unsigned setc leg missing"
    assert "subb " in asm or "subw " in asm, "sub width leg missing"
