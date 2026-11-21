# LINES reason: one wave (M4 W-U COMMIT-3, the splice-shadow resolution
# law, card 12404.2.102): the legs are the ONE law (a spliced local beats
# the caller's same-name static) seen from the arms that resolve it, plus
# the interaction TUs with this wave's own laws; splitting them would let
# one resolving arm change without the row that bounds it.
r"""M4 W-U COMMIT-3 (MC 12739) — the INLINER scope seam: a spliced local
shadows the caller's same-name `static` (blcc/inliner.py splices a callee
body into the caller; the callee's parameters and autos land in
`fn.locals`, the caller's function-scope `static` objects live in
`fn.statics`, and blcc's flat per-function maps resolved `fn.statics`
FIRST).

THE law, named (own hands at the wave REC, gcc 11.4): a name means what
the INNERMOST DECLARING scope says it means at the point of use. In the
spliced region the innermost declaration is the CALLEE's local, so the
LOCAL wins there; outside the call the caller's own `static` keeps its
meaning (the negative leg below pins both halves). In unspliced C the two
maps are DISJOINT by construction — the parser LOUDs "'x' collides with a
name declared in this scope" for a static local sharing a name with a
local or parameter — so this law is a NO-OP except where the splice made
one function hold both meanings. blcc ships it as ONE predicate
(`ExprEmitter._static_visible`) guarding every arm that resolves
`fn.statics`: `_ex_ident`, the `_ex_assign` fast store, `_emit_addr`'s
Ident arm (blcc/expr_codegen.py) and the asm operand fold + the asm memory
arm (blcc/asmsub.py) — five arms; the sixth statics-reading arm
(`AsmGenMixin._asm_addr_base`) already resolves locals-first and is
NAMED here rather than patched beside.

This REFRAMES the old premise honestly: the 28-stream 'cannot load a
5-byte value' class (and the LEDGER's earlier 'odd-size load' framing of
it) is NOT an odd-size load need — text-patching.h:114:2 was reading the
CALLER's `static union text_poke_insn insn` where the callee's local
`union text_poke_insn *insn` belonged. The row below is the acceptance
witness: gcc answers 255, tip LOUDs the mis-bound load.

SILENT MIS-COMPUTE witnesses (worse than the LOUD ones, so they are the
teeth): s3 (a caller static ARRAY vs a callee local array → blcc answered
247 where gcc answers 0) and s5 (a callee local `q` vs a caller static `q`
→ blcc answered 2 where gcc answers 0). Both are RUN-PAIR rows here.

Named residual limits (instrument, not posture): a spliced callee's OWN
`static` and a caller LOCAL of the same name resolve toward the local by
this law (the mirror image; corpus volume 0 — the 616 multi-`__label__`
-style scope-overlap census in .tmp/m4-wu/out/label-census.txt is the
instrument class that would show it, and no stream carries a callee
static colliding with a caller local), and the same-name-collision
guardrail in the parser still LOUDs in unspliced source.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _w(tag, src):
    c = "/dev/shm/wu3_%s.c" % tag
    open(c, "w").write(src)
    return c


def _pair(tag, src):
    c = _w(tag, src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/wu3_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wu3_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wu3_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must COMPILE (RED-first at C2 bytes): " \
        % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wu3_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wu3_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d — a SILENT mis-bound " \
        "name (the splice shadow) shows up as a wrong VALUE, not a " \
        "failure: %s" % (tag, bex, gex, src.splitlines()[0][:40])


HDR = ("typedef unsigned char u8; typedef int s32;\n"
       "union text_poke_insn { u8 text[5]; struct { u8 opcode; s32 disp; } "
       "__attribute__((packed)); };\n")


# ---- the acceptance witness (sealed law row 18, VERBATIM) --------------

def test_wu_l18_text_gen_insn_splice_shadow_pairs():
    # THE root-cause row: callee local `union text_poke_insn *insn` vs
    # caller `static union text_poke_insn insn`. At C2 bytes blcc LOUDs
    # `cannot load a 5-byte value (§4)` on the MIS-BOUND load; gcc answers
    # 255. This single row is what the 28-stream 5-byte class really was.
    _pair("l18", HDR + """
static inline __attribute__((__always_inline__))
void __text_gen_insn(void *buf, u8 opcode, long d, int size)
{
 union text_poke_insn *insn = buf;
 insn->opcode = opcode;
 if (size > 1) insn->disp = (long)d;
}
static inline __attribute__((__always_inline__))
void *text_gen_insn(u8 opcode, long d)
{
 static union text_poke_insn insn; /* per instance */
 __text_gen_insn(&insn, opcode, d, 5);
 return &insn.text;
}
int use(u8 op, long d);
int use(u8 op, long d){ union text_poke_insn *ip; ip = (union text_poke_insn *)text_gen_insn(op, d); return (int)ip->text[0] + (int)(ip->disp & 3); }
int main(void){ return use(2, 5) - 4; }
""")


# ---- own shadow shapes, run-encoded (>=4) ------------------------------

def test_wu_s1_pointer_local_shadows_caller_static():
    _pair("s1", """
struct U { unsigned char t[5]; long d; };
static inline __attribute__((__always_inline__)) void callee1(void *buf, long d)
{ struct U *u = buf; u->d = d + 1; }
static inline __attribute__((__always_inline__)) long outer1(long d)
{ static struct U u; callee1(&u, d); return u.d + 2; }
int main(void){ return (int)outer1(3) - 6; }
""")


def test_wu_s2_local_alias_of_the_shadowed_object():
    _pair("s2", """
struct U { unsigned char t[5]; long d; };
static inline __attribute__((__always_inline__)) void callee2(struct U *u, long d)
{ u->d = d * 2; }
static struct U g;
static inline __attribute__((__always_inline__)) long outer2(long d)
{ static struct U u; struct U *u2 = &u; callee2(u2, d); g.d = u.d; return g.d + 1; }
int main(void){ return (int)outer2(4) - 9; }
""")


def test_wu_s3_static_array_versus_local_array_is_a_run_pair():
    # SILENT MIS-COMPUTE witness: at C2 bytes this answered 247 (gcc 0).
    _pair("s3", """
static inline __attribute__((__always_inline__)) int callee3(void)
{ int a[3]; a[0] = 1; a[1] = 2; a[2] = 3; return a[0] + a[1] + a[2]; }
static inline __attribute__((__always_inline__)) int outer3(void)
{ static int a[3]; a[0] = 10; a[1] = 20; a[2] = 30; return callee3() + a[0]; }
int main(void){ return outer3() - 16; }
""")


def test_wu_s5_caller_static_survives_the_splice_too():
    # THE NEGATIVE HALF of the same law: inside the spliced call the
    # callee's local `q` wins (5), and AFTER the call the caller's own
    # `static q` still means the static (7, then +1). Answer 13. At C2
    # bytes blcc answered 2 — the static stole the local.
    _pair("s5", """
static inline __attribute__((__always_inline__)) int callee6(void){ int q = 5; return q; }
static inline __attribute__((__always_inline__)) int outer6(void){ static int q = 7; int r = callee6(); q += 1; return q + r; }
int main(void){ return outer6() - 13; }
""")


def test_wu_s4_callee_static_versus_caller_static_unchanged():
    # posture pin (measured identical at C2 bytes, 255 on both sides): two
    # OWN statics of the same name in the two functions keep their own
    # symbols; the new law must not fold them together.
    _pair("s4", """
static inline __attribute__((__always_inline__)) int callee4(int p)
{ static int q; q = p + 1; return q; }
static inline __attribute__((__always_inline__)) int outer4(int p)
{ static int q; q = 100; return callee4(p) + q; }
int main(void){ return outer4(4) - 106; }
""")


def test_wu_s6_unspliced_static_local_law_unchanged():
    # §1c posture pin: with NO splice involved, the function-scope static
    # still shadows the same-name global (%rip path) — the law this commit
    # adds is a NO-OP there, and the old sentence stays true.
    _pair("s6", """
int v = 40;
static inline int bump(void){ static int v = 1; v += 2; return v; }
int main(void){ return bump() + v - 43; }
""")


# ---- interactions with this wave's own laws ---------------------------

def test_wu_i1_law_a_inside_an_inlined_splice():
    # A × D: a transparent-group lvalue (`({ u->d; }) = …`) INSIDE the
    # spliced callee body, over the very local that the caller's static
    # used to steal. At C2 bytes this died on the mis-bound load.
    _pair("i1", """
struct U { unsigned char t[5]; long d; };
static inline __attribute__((__always_inline__)) void callee5(void *buf, long d)
{ struct U *u = buf; ({ u->d; }) = d + 1; }
static inline __attribute__((__always_inline__)) long outer5(long d)
{ static struct U u; callee5(&u, d); return u.d + 2; }
int main(void){ return (int)outer5(3) - 6; }
""")


def test_wu_i3_law_a_and_law_b_in_one_function():
    # A × B: the SAME function carries an extern-local binding a name the
    # TU never declares (COMMIT-2) and a group lvalue (COMMIT-1).
    # Compile-posture (the symbol is a link-time fact); at C2 bytes the
    # extern-local leg LOUDed before the group leg was even reached.
    c = _w("i3", "int main(void){ extern int lone_obj; int v = 1; "
                  "({ v; }) = 2; return v + (int)(long)&lone_obj * 0 - 2; }\n")
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + ["-c", c, "-o",
                                                     "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc compiles the interaction row: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 0, "both laws must hold in one function: " \
        + b.stderr


def test_wu_s7_inliner_label_freshness_still_holds():
    # cross-commit pin: the inliner mints FRESH label names per site
    # (`inl_<name>`) and my law touches only the object-name resolution;
    # a spliced `__label__` site must still compile and PAIR.
    _pair("s7", """
static inline __attribute__((__always_inline__)) int loopish(int n)
{ __label__ done; int r = 0; if (n > 2) { r = 7; goto done; } r = 1;
done: return r; }
int main(void){ return loopish(3) + loopish(1) - 8; }
""")
