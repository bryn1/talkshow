# M4 W-AM COMMIT-1 battery — {F} THE FRONTIER: the addressable-cast law
# at the ONE address site `_asm_addr_emit` (MC 12404.2.159 / card 12885;
# design truth .tmp/evidence/m4-wal-sims.md §1, the 31-row run-encoded law
# battery VERBATIM, postures the sims {F} column re-measured own hands at
# trees/f: law-tip-wl.txt / law-f-wl.txt).
#
# THE LAW: in a memory-constraint slot a NON-addressable expression (a
# cast of any width, a constant-foldable rvalue) is answered by gcc with
# the operand's MATERIALIZED converted VALUE — the temp's memory, never
# the source object's address (p2: the object leaks live bytes beside the
# cast window — wl12 77-vs-52 SILENT). The door rides the SHIPPED L3
# materialize idiom (_slot + park, _asm_eval_in's law); addressable
# operands keep riding `_emit_addr` UNTOUCHED. The (cast) = VALUE family
# is BOTH-REFUSE at this gcc — 14 rows prove blcc is FAITHFUL there
# (premise truth: the brief's "gcc accepts" was the sims' first premise
# correction); a lever opening it would be LOOSE by the oracle. wl06
# `&(int)x` stays BOTH-REFUSE: the value-as-address family in
# expr_codegen._emit_addr is NOT this fix's home (the HOME plant proves
# the door cannot be smuggled there).
#
# RED FIRST at tip c586d25 (own hands, logs/m4wam1-red-tip.log): EXACTLY
# 7 failed / rest pass — the five MOVED rows (wl11/12/13/14/26) + the
# frontier-x-splice-RENAME interaction (x1) + the one-home door leg (the
# door does not exist yet at tip — the leg IS its own birth-certificate
# tooth). GREEN at tip by design: the
# 14 BOTH-REFUSE premise rows (blcc already faithful), the controls
# (wl08/19/21/27/28/29/30/31), the bit-preserving-cast control x4, the
# NAMED pins (wl22 SILENT-8 until COMMIT-2 retargets it BY NAME;
# wl24/wl25 LOOSE output face — gcc-rc1 side, input-scoped door neither
# fixes nor widens).
#
# SUPERSEDED (COMMIT-2, MC 12404.2.159): the wl22 row's NAMED_SILENT pin
# is RETARGETED BY NAME below — at the {W22} bytes the silent face LANDS
# (the drop hands the operand to the COMMIT-1 door and the placement law
# restores the parked value), so the leg now pins PAIR-7 and goes RED
# for ANY re-opening of the source-answer (teeth INVERTED, never
# dropped; the saturating twin wl23 was PAIR before and stays PAIR — the
# PAIR is what proves the fix answers the CONVERSION, not
# "zero-everything"). RED-first at the COMMIT-1 bytes: this leg fails
# there (8 vs the pinned 7), logs/m4wam2-red-c1b.log.
#
# Probes embedded from the sims generators (wal_gen_law.py), blank-line-
# compacted (law-neutral whitespace only — every exit code re-anchored by
# THIS suite: each PAIR row re-runs BOTH sides and pins gcc off the sims
# number, so a compacted probe that drifted changes a pin and goes RED);
# the x-rows are this card's own interaction probes (gcc ground measured
# own hands at the tip bytes before any fix existed).
import os
import subprocess
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
STREAMS = "/home/claudecode/Blaha/.tmp/m4-plan/streams"
TMP = "/dev/shm/m4wam1_%s_%d_%s" % (os.environ.get("M4WAM_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

# name -> (source, kind, gcc-exit, pin)
ROWS = {
    "wl01_lval_cast_same": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { x = 1; (int)x = 5; return x; }
""",
        "BOTH-REFUSE", None, None),
    "wl02_lval_cast_signflip": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { x = 1; (unsigned)x = 7; return x; }
""",
        "BOTH-REFUSE", None, None),
    "wl03_lval_cast_widen": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { x = 1; (long)x = 9; return x == 9 ? 4 : 3; }
""",
        "BOTH-REFUSE", None, None),
    "wl04_lval_cast_narrow": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
long x;
int answer(void) { x = 1; (int)x = 300; return x == 300 ? 5 : (x == 44 ? 6 : 7); }
""",
        "BOTH-REFUSE", None, None),
    "wl05_lval_cast_u16": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { x = 1; (u16)x = 65537; return x; }
""",
        "BOTH-REFUSE", None, None),
    "wl06_addr_of_cast": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { int *p; x = 2; p = &(int)x; *p = 8; return x; }
""",
        "BOTH-REFUSE", None, None),
    "wl07_cast_compound": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { x = 4; (int)x += 3; return x; }
""",
        "BOTH-REFUSE", None, None),
    "wl08_cast_incdec": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { x = 4; (int)x++; return x; }
""",
        "PAIR", 5, None),
    "wl09_cast_of_rvalue": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) { x = 2; (int)(x + x) = 9; return x; }
""",
        "BOTH-REFUSE", None, None),
    "wl10_cast_ptr_width": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
char a[4]; char *p;
int answer(void) { p = a; (ul)p = 0; return p == 0 ? 1 : 2; }
""",
        "BOTH-REFUSE", None, None),
    "wl11_asm_rm_cast_u16": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct pt_regs { ul bx; u16 ss; };
int answer(void) {
    struct pt_regs r; struct pt_regs *regs = &r;
    u32 ar = 0;
    regs->ss = 0x34;
    __asm__ __volatile__ ("movzwl %[s], %[a]\\n\\t"
        : [a] "=r" (ar)
        : [s] "rm" ((u16)regs->ss));
    return (int)(ar & 0xff);
}
""",
        "PAIR_MOVED", 52, None),
    "wl12_asm_rm_cast_widen": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct pt_regs { ul bx; u16 ss; u16 hi; };
int answer(void) {
    struct pt_regs r; struct pt_regs *regs = &r;
    u32 ar = 0;
    regs->ss = 0x34; regs->hi = 0xBE;   /* LIVE bytes beside the window */
    __asm__ __volatile__ ("movl %[s], %k[a]\\n\\t"
        : [a] "=r" (ar)
        : [s] "rm" ((u32)regs->ss));
    return (ar & 0xffffu) == 0x34u ? ((ar >> 16) == 0 ? 52 : 77) : 91;
}
""",
        "PAIR_MOVED", 52, None),
    "wl13_asm_rm_neg_const": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int answer(void) {
    u32 r = 8;
    __asm__ ("bsrl %1,%0\\n\\t"
             "cmovzl %2,%0"
             : "=&r" (r) : "rm" (8u), "rm" (-1));
    return (int)r;
}
""",
        "PAIR_MOVED", 3, None),
    "wl14_asm_rm_plus_const": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int answer(void) {
    u32 v = 0;
    __asm__ volatile ("movl %[x], %[d]" : [d] "=r" (v) : [x] "rm" ((5 * 8 + 3)));
    return (int)(v & 0xff) - 40;
}
""",
        "PAIR_MOVED", 3, None),
    "wl15_struct_cast_target": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct S { int a; };
struct S s, t;
int answer(void) { s.a = 1; t.a = 2; (struct S)s = t; return s.a; }
""",
        "BOTH-REFUSE", None, None),
    "wl16_cast_target_const": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
const int c = 3;
int answer(void) { (int)c = 9; return c; }
""",
        "BOTH-REFUSE", None, None),
    "wl17_satur_fill": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
long x;
int answer(void) { x = 0x10034; (u16)x = 0xABCD; return (int)(x & 0xffff) == 0xABCD ? 11 : (int)((x >> 16) & 0xff); }
""",
        "BOTH-REFUSE", None, None),
    "wl18_satur_fit": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
long x;
int answer(void) { x = 0x34; (u16)x = 0x21; return (int)(x & 0xffff) == 0x21 ? 11 : 12; }
""",
        "BOTH-REFUSE", None, None),
    "wl19_cast_rvalue_control": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct pt_regs { ul bx; u16 ss; };
struct pt_regs r;
int answer(void) { r.ss = 0x12; return (int)((u16)r.ss) + 1; }
""",
        "PAIR", 19, None),
    "wl20_cast_index_target": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int a[3];
int answer(void) { a[1] = 1; (u16)a[1] = 300; return a[1]; }
""",
        "BOTH-REFUSE", None, None),
    "wl21_deref_cast_control": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x; char *p;
int answer(void) { x = 1; p = (char *)&x; *(int *)p = 6; return x; }
""",
        "PAIR", 6, None),
    "wl22_satur_trunc_fill": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct S { ul pad; u32 v; };
int answer(void) {
    struct S s; u32 d = 0;
    s.pad = 0; s.v = 0x11223344u;
    __asm__ volatile ("movw %[x], %w[d]" : [d] "=r" (d) : [x] "rm" ((u16)s.v));
    return (d & 0xffffu) == 0x3344u ? ((d >> 16) == 0 ? 7 : 8) : 9;
}
""",
        "PAIR", 7, None),
    "wl23_satur_trunc_fit": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct S { ul pad; u32 v; };
int answer(void) {
    struct S s; u32 d = 0;
    s.pad = 0x99; s.v = 0x21u;
    __asm__ volatile ("movw %[x], %w[d]" : [d] "=r" (d) : [x] "rm" ((u16)s.v));
    return (d & 0xffffu) == 0x21u ? 7 : 9;
}
""",
        "PAIR", 7, None),
    "wl24_cast_output_m": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
ul x;
int answer(void) {
    u32 d; x = 5;
    __asm__ volatile ("movl $7, %0" : "=m" ((u32)x));
    d = x;
    return (int)(d & 0xff) ? 10 : 11;
}
""",
        "NAMED_LOOSE", None, 10),
    "wl25_cast_readwrite_m": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
ul x;
int answer(void) {
    x = 5;
    __asm__ volatile ("incl %0" : "+m" ((u32)x));
    return (int)(x & 0xff);
}
""",
        "NAMED_LOOSE", None, 6),
    "wl26_cast_arith_m": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
int x;
int answer(void) {
    u32 d = 0;
    x = 3;
    __asm__ volatile ("movl %[x], %k[d]" : [d] "=r" (d) : [x] "rm" ((u32)(x + 1)));
    return (int)d;
}
""",
        "PAIR_MOVED", 4, None),
    "wl27_plain_local_m": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
u32 v;
int answer(void) {
    u32 d = 0;
    __asm__ volatile ("movl %[x], %[d]" : [d] "=r" (d) : [x] "rm" (v) : "memory");
    return (int)d;
}
""",
        "PAIR", 0, None),
    "wl28_cast_p_operand": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
char a[8]; char *p;
int answer(void) {
    p = a; a[0] = 12;
    ul d = 0;
    __asm__ volatile ("movb (%0), %b1" : "=r" (d) : "0" ((ul)p));
    return a[0];
}
""",
        "PAIR", 12, None),
    "wl29_two_cast_inputs": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct S { ul a; u16 b; u16 c; };
int answer(void) {
    struct S s; u32 d = 0, e = 0;
    s.a = 0; s.b = 0x21; s.c = 0x42;
    __asm__ volatile ("movzwl %[x], %[d]\\n\\tmovzwl %[y], %[e]"
        : [d] "=r" (d), [e] "=r" (e)
        : [x] "rm" ((u16)s.b), [y] "rm" ((u16)s.c));
    return (int)((d & 0xff) + ((e & 0xff) >> 1));
}
""",
        "PAIR", 66, None),
    "wl30_readwrite_cast_local": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct S { ul pad; u32 v; };
int answer(void) {
    struct S s;
    s.pad = 0; s.v = 5;
    __asm__ volatile ("incl %0" : "+m" ((u32)s.v));
    return (int)(s.v & 0xff);
}
""",
        "PAIR", 6, None),
    "wl31_output_cast_local_m": (
        """typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long ul;
typedef long sl;
struct S { ul pad; u32 v; };
int answer(void) {
    struct S s;
    s.pad = 0; s.v = 5;
    __asm__ volatile ("movl $7, %0" : "=m" ((u32)s.v));
    return (int)(s.v & 0xff);
}
""",
        "PAIR", 7, None),
    "x1_frontier_spliced_rename": (
        """typedef unsigned short u16; typedef unsigned int u32; typedef unsigned long ul;
struct R { u16 ss; };
static inline int fetch(struct R *regs) {
    u32 ar = 0;
    __asm__ __volatile__ ("movzwl %[s], %[a]\\n\\t"
        : [a] "=r" (ar) : [s] "rm" ((u16)regs->ss));
    return (int)(ar & 0xff);
}
int answer(void) {
    struct R regs;               /* SAME name as the callee param: the
                                    post-RENAME capture the W-W law mints
                                    past — the door rides the CLONE */
    regs.ss = 0x54;
    return fetch(&regs) + 1;
}
""",
        "PAIR_MOVED", 85, None),
    "x4_noop_cast_keeps_addr": (
        """typedef unsigned int u32;
int answer(void) {
    u32 x = 41; u32 d = 0;
    __asm__ volatile ("movl %[x], %k[d]" : [d] "=r" (d) : [x] "rm" ((u32)x));
    return (int)d;
}
""",
        "PAIR", 41, None),
}


def _law_main(d):
    key = os.path.join(d, "law_main_%d.o" % os.getpid())
    if not os.path.exists(key):
        src = os.path.join(d, "law_main_%d.c" % os.getpid())
        with open(src, "w") as fh:
            fh.write("int answer(void);\nint main(void){ return answer(); }\n")
        subprocess.run(["gcc", "-c", src, "-o", key], check=True,
                       capture_output=True)
    return key


def _side(name, src, which):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "%s_%s_%d.c" % (name, which, os.getpid()))
    with open(c, "w") as fh:
        fh.write(src)                       # law_main supplies main() —
    #   the sims posture-runner shape: the exit IS the answer
    o = c[:-2] + ".o"
    exe = c[:-2] + "." + which
    if which == "gcc":
        r = subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
                           capture_output=True, text=True)
    else:
        r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                           capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
        if r.returncode != 0:
            return r.returncode, (r.stdout + r.stderr)
    link = subprocess.run(["gcc", "-no-pie", o, _law_main(TMP), "-o", exe],
                          capture_output=True, text=True)
    if link.returncode != 0:
        return 99, link.stderr
    return 0, subprocess.run([exe], capture_output=True,
                             timeout=60).returncode


import pytest


@pytest.mark.parametrize("name", sorted(ROWS))
def test_wam_frontier_law(name):
    src, kind, gexit, pin = ROWS[name]
    grc, g = _side(name, src, "gcc")
    if kind == "BOTH-REFUSE":
        assert grc != 0, ("%s: gcc STARTED ACCEPTING (rc0 exit=%s) — the "
                          "both-refuse premise of sims §1 died at a new "
                          "gcc; re-measure the family before believing "
                          "blcc faithful" % (name, g))
        brc, b = _side(name, src, "blcc")
        assert brc != 0, ("%s: blcc OPENED the assignment/& face (exit=%s) "
                          "— the (cast)=VALUE family is BOTH-REFUSE (the "
                          "14-row premise); opening it is LOOSE by the "
                          "oracle, not a fix" % (name, b))
        return
    brc, b = _side(name, src, "blcc")
    if kind == "NAMED_LOOSE":
        # wl24/wl25: the OUTPUT face — gcc REFUSES (rc1), blcc accepts
        # (pre-existing LOOSE, sims §1: "neither fixes nor widens").
        assert grc != 0, ("%s: gcc stopped refusing the cast-output face "
                          "— the NAMED LOOSE reading is stale" % name)
        assert brc == 0 and b == pin, (
            "%s: the NAMED LOOSE posture moved (rc=%d exit=%s, pinned %d)"
            % (name, brc, b, pin))
        return
    assert grc == 0 and g == gexit, (
        "%s: gcc moved off the sims-measured %s (now rc=%d %r) — the "
        "ground truth of card 12879 §1 changed; re-measure before "
        "believing this row" % (name, gexit, grc, g))
    assert brc == 0, ("%s: rc=%d — the frontier door died back into a "
                      "wall:\n%s" % (name, brc, str(b)[:300]))
    assert b == g, ("%s: SILENT — blcc %d vs gcc %d (p2's class: the "
                    "source-object answer leaks the live bytes beside the "
                    "cast window)" % (name, b, g))


def test_wam_assign_face_stays_faithful():
    # The premise truth (sims §1 correction): blcc's refusal of the
    # (cast)=VALUE family is the shipped PARSE-side non-l-value law —
    # gcc's own twin sentence is 'lvalue required as left operand of
    # assignment'. The frontier door must NOT move this sentence.
    p = os.path.join(REPO, "blcc")
    hits = []
    for f in os.listdir(p):
        if f.endswith(".py"):
            t = open(os.path.join(p, f)).read()
            if "non-l-value" in t:
                hits.append(f)
    assert hits, "the shipped non-l-value refusal sentence vanished — the " \
        "assignment face opened silently (14 BOTH-REFUSE rows forbid it)"
    src, kind, gexit, pin = ROWS["wl01_lval_cast_same"]
    brc, b = _side("wl01_sentence", src, "blcc")
    assert brc != 0 and "non-l-value" in str(b), (
        "wl01 moved off the faithful refusal sentence: " + str(b)[:200])


def test_wam_door_home_is_one_site():
    # ONE hunk, ONE home: the materialize law (door + matable test) lives
    # in asmgen.py ONLY. expr_codegen._emit_addr's value-as-address
    # family must not grow a cast-stripping arm (wl06 pins: a member
    # there is LOOSE by the oracle). The HOME plant (fix smuggled into
    # _emit_addr) lands on this leg RED.
    ag = open(os.path.join(REPO, "blcc", "asmgen.py")).read()
    ec = open(os.path.join(REPO, "blcc", "expr_codegen.py")).read()
    assert ag.count("def _asm_matable") == 1, "the matable law is not ONE home"
    body = ec[ec.index("def _emit_addr"):]
    nxt = body.find("\n    def ", 1)
    body = body[:nxt + 1] if nxt != -1 else body
    import re as _re
    # The shipped body may BUILD a Cast (the CompoundLit value path) but
    # must never STRIP one: an unwrap arm is the smuggled door.
    assert _re.search(r"isinstance\([^)]*,\s*ast\.Cast\)", body) is None, (
        "_emit_addr grew a Cast-STRIPPING arm — the door was SMUGGLED "
        "into the value-as-address family; wl06 (&(int)x) pins that home "
        "LOOSE by the gcc oracle")


GAINED_2 = ["arch_x86_kernel_signal.c.i", "arch_x86_mm_extable.c.i"]


def _clean_i(path, tmp_path, tag):
    out = tmp_path / ("%s.c.i" % tag)
    with open(path, errors="replace") as fh:
        txt = "".join(ln for ln in fh if not ln.startswith("# "))
    out.write_text(txt)
    return out


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", GAINED_2)
def test_wam_frontier_lands_the_gained_2(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wam1")
    o = tmp_path / "wam1.o"
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(o)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == 0, (
        "%s must LAND at the frontier door — first wall:\n%s"
        % (stream, next((ln for ln in (r.stdout + r.stderr).splitlines()
                         if ln.strip()), "(no output)")))
    assert o.exists() and o.stat().st_size > 0, "empty object"


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_wam_vdso32_rewalls_at_m3_support(tmp_path):
    # THE RE-WALL, NAMED NOT CHASED (brief): opening vdso32's cast face
    # lands the stream on its NEXT wall — the M3-support sentence for the
    # 'A' constraint (the stream is gcc-DEAD behind the frontier at these
    # bytes, sims §2: the combo buys nothing at the corpus face). The
    # assembler width-suffix / constraint-support lever is the NEXT card.
    clean = _clean_i(os.path.join(
        STREAMS, "arch_x86_entry_vdso_vdso32_vclock_gettime.c.i"),
        tmp_path, "wamv")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "wamv.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    first = next((ln for ln in (r.stdout + r.stderr).splitlines()
                  if ln.strip()), "(no output)")
    assert r.returncode != 0, ("vdso32 must NOT accept — its stream is "
                               "gcc-DEAD behind the frontier at these bytes")
    assert "are not in the M3 SUPPORT set" in first, \
        "vdso32 moved off the M3-support sentence: " + first[:250]
    assert "not an addressable l-value" not in first, \
        "the frontier wall is still standing at vdso32: " + first[:250]
