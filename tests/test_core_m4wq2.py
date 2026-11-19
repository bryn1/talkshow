# LINES reason: one wave of legs (M4 W-Q COMMIT-2 - the gate's corruption
# guards VERBATIM + the interaction TUs, card 12404.2.91): the guards and
# the interactions judge ONE mechanism (the W-Q tag identity); a split
# would separate each guard from its witness.
r"""M4 W-Q COMMIT-2 - GATE GUARDS + INTERACTIONS (card 12404.2.91).
The three corruption guards the W-P gate (MC 12708 leg 5) demanded
ride VERBATIM (b01_tag_reuse_outer_scope / b13_two_functions_same_tag
/ b15_guard_outer_alive - their probes are the gate's own texts, a
name-keyed layout table fails all three by MIS-SIZE; the minted-identity
law pairs them). THE INTERACTION TUs: a block-scope struct inside a
W-P SPLICE body (q14 family, called from a caller LOOP), a NON-constant
`"i"` operand naming a block-struct member (the S5/L4 refusal must
stand for members too - the imm map answers PARAMS, never a member),
and a cmpxchg-family constant-DISPATCHED switch whose arms carry
block-scope definitions (live AND dead arms, the W-O fold law).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
TMP = "/dev/shm"


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _pair(tag, src, want=None):
    c = "%s/wq2_%s.c" % (TMP, tag)
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "%s/wq2_%s.g" % (TMP, tag)])
    assert g.returncode == 0, "probe must be valid C: " + g.stderr
    gex = _run("%s/wq2_%s.g" % (TMP, tag))
    o = "%s/wq2_%s.b.o" % (TMP, tag)
    b = blcc(["-c", c, "-o", o])
    bex = btxt = None
    if b.returncode == 0:
        assert gcc([o, "-no-pie", "-o", "%s/wq2_%s.b" % (TMP, tag)]
                   ).returncode == 0, "link must work"
        bex = _run("%s/wq2_%s.b" % (TMP, tag))
        blcc(["-c", c, "--emit-asm", "-o", "%s/wq2_%s.bt" % (TMP, tag)])
        btxt = open("%s/wq2_%s.bt.s" % (TMP, tag)).read()
    if want is not None:
        assert (gex, bex) == (want, want), \
            "%s: value pair %s vs %s" % (tag, gex, bex)
    return g.returncode, b.returncode, gex, bex, btxt


# -- THE GATE GUARDS, VERBATIM (m4-wp-gate leg5_sims.py b01/b13/b15) ----

def test_wq2_b01_tag_reuse_outer_scope():
    """inner tag SHADOWS the file tag; the inner type is a DIFFERENT
    type (gate MC 12708 b01, verbatim)."""
    _pair("b01", r"""
struct S { int a; };
int main(void) { struct S o; struct Inner { int a2; };
    o.a = 5; { struct S { long b; }; struct S i; i.b = 7;
        if (sizeof(struct S) != 8) return 11; if (o.a != 5) return 12;
        if (sizeof(o) != 4) return 13; }
    if (sizeof(struct S) != 4) return 14; return 0; }""", want=0)


def test_wq2_b13_two_functions_same_tag():
    """same tag, different layout, two functions: gcc says two DIFFERENT
    types (gate b13, verbatim - the name-keyed table mis-sizes one)."""
    _pair("b13", r"""
struct G { int z; };
int fa(void) { struct S { int a; }; struct S x; x.a = 5; return x.a; }
int fb(void) { struct S { long a; long b; }; struct S y; y.a = 7; y.b = 1;
    return (int)(y.a + y.b + sizeof(struct S)); }
int main(void) { if (fa() != 5) return 11; if (fb() != 8 + 16) return 12;
    if (sizeof(struct G) != 4) return 13; return 0; }""", want=0)


def test_wq2_b15_guard_outer_alive():
    """GUARD ROW: an object of the OUTER tag is LIVE across an inner
    same-tag definition; the two layouts must coexist (gate b15,
    verbatim)."""
    _pair("b15", r"""
struct S { short a; short b; };
struct S G;
int main(void) { G.a = 3; G.b = 4;
    { struct S { long long q; }; struct S loc; loc.q = 9;
      if (sizeof(struct S) != 8) return 11;
      if (sizeof(G) != 4) return 12;
      if (G.a != 3 || G.b != 4) return 13; }
    if (sizeof(struct S) != 4) return 14;
    if (G.a + G.b != 7) return 15; return 0; }""", want=0)


# -- INTERACTION TUs -----------------------------------------------------

def test_wq2_splice_body_block_struct_and_switch():
    """W-P x W-Q: a static inline whose body carries a block-scope
    struct, a block enum and a constant-DISPATCHED switch, called from
    a caller LOOP - every site splices; each copy lays out its block
    declarations independently. mix(k): gt = 2*(3k+3) -> 12+18+24=54."""
    src = """
int gt;
static inline void mix(int k){
    struct Box { int a; int b; } bx;
    bx.a = k; bx.b = k * 2;
    enum { MAGIC = 3 };
    switch (sizeof(int)) {
    case 4: {
        struct Arm { int c; } ar; ar.c = MAGIC;
        asm volatile("movl %%eax, gt+0(%%rip)" : : "a"
                     (bx.a + bx.b + ar.c) : "memory");
        asm volatile("addl gt+0(%%rip), %%eax" : "=a" (gt) : : "memory");
        break; }
    case 8: gt += 100; break;
    }
}
int main(void){ int i, acc = 0; for (i = 1; i <= 3; i++){ gt = 0;
    mix(i); acc += gt; } asm volatile("" : : "r" (acc) : "memory");
    return acc % 100; }
"""
    _pair("spmix", src, want=54)


def test_wq2_block_forward_completion_no_leak():
    """A block-scope forward declaration COMPLETED in the same block
    (q08 family) must NOT make the NAME visible at file scope: the
    LATER file definition of the same name is a DIFFERENT type — gcc
    compiles this TU (file sizeof 8, block sizeof 4); a leak would
    LOUD the file definition as "already defined"."""
    _pair("noleak", """
int gb, gf;
void f(void){ struct N1 *p; struct N1 { int a; } v; v.a = 1;
    gb = (int)sizeof(v); p = &v; gb += p->a; }
struct N1 { long z; long y; long x; long w; };
int h(void){ struct N1 k; gf = (int)sizeof(k); return gf; }
int main(void){ f(); h(); if (gb != 5) return 11;
    if (gf != 32) return 12; return 0; }
""", want=0)


def test_wq2_i_operand_block_member_loud():
    """The imm map answers PARAMS only: a NON-constant `"i"` operand
    naming a BLOCK-STRUCT MEMBER keeps the S5/L4 refusal on BOTH trees
    (gcc rc1 "impossible constraint"), inside a spliced body too."""
    src = """
int acc;
static inline void bad(void){ struct Box { int v; } bx; bx.v = 3;
    asm volatile("movl %0, acc+0(%rip)" : : "i" (bx.v) : "memory"); }
int main(void){ bad(); return 3; }
"""
    c = "%s/wq2_ibad.c" % TMP
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "%s/wq2_ibad.g" % TMP])
    b = blcc(["-c", c, "-o", "%s/wq2_ibad.b.o" % TMP])
    assert g.returncode != 0 and b.returncode != 0


def test_wq2_cmpxchg_arm_block_struct_live_and_dead():
    """cmpxchg-family constant DISPATCH: the LIVE arm (case 8) carries
    a block-scope struct whose object feeds the asm; the DEAD arms carry
    block-scope definitions of the SAME name too (the W-O skip must not
    mis-wire layouts; a.l + a.h = 4 + 3 = 7)."""
    src = """
int gt;
static inline void cw(long *v){
    switch (sizeof(long)) {
    case 1: { struct W { char c; } a; a.c = 1; gt += a.c; break; }
    case 4: { struct W { int i; } a; a.i = 2; gt += a.i; break; }
    case 8: { struct W { long l; long h; } a; a.l = *v; a.h = 3;
              asm volatile("movl %%eax, gt+0(%%rip)"
                           : : "a" ((int)(a.l + a.h)) : "memory");
              break; }
    }
}
int main(void){ long x = 4; cw(&x); return gt % 100; }
"""
    _pair("cw8", src, want=7)
