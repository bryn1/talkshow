# M4 W-AM COMMIT-2 battery — {W22} the SILENT FACE of the frontier
# family: a MODE-changing cast on an object base was answered at the
# SOURCE (MC 12404.2.159 / card 12885; sims 12879 §1 "a fix that stops at
# the address site leaves the silent half of its own family open"; the
# silent rows are ACCEPTED-WITH-WRONG-BITS — census-blind by construction,
# which is exactly why this battery exists and why the close carries a
# byte-level blast screen, not just counts).
#
# THE LAW (this commit, measured own hands): `_asm_static` strips casts to
# find the base — when a pure-INPUT 'm'/'rm' operand's cast CHANGES MODE
# (size change, or either side float-side), the source MEM is NOT the
# answer gcc prints: gcc force-mem's the converted value. The drop-site
# (ONE predicate, `_asm_value_conv`) hands the operand to the COMMIT-1
# door — REUSE: one materialize law, one home, no second engine. The
# PLACEMENT law completes it: the value door answers the VALUE, so after
# the aslot transport the parked value is restored in %rax — a PARTIAL
# -width template write (movw → %ax) otherwise lifts dead transport bytes
# into the write-back (wl22 SILENT 8-vs-7 was exactly that lift).
# BIT-PRESERVING casts (same width, integer-side ↔ pointer-side) KEEP
# riding the static address text (x4 is that control; gcc prints the
# address there too) — zero collateral by construction.
#
# RED-FIRST at the COMMIT-1 bytes (logs/m4wam2-red-c1.log): EXACTLY 4
# failed — x2 (SILENT at the {F} bytes: the door's OWN address-transport
# residue lifts into the write-back too — this row proves the placement
# law is PART of the fix, not garnish), x3 (co-existence, W22 face FIRST),
# x5 (the widening face: the object leaks 0x1122 beside the truncation),
# and the one-home leg for `_asm_value_conv` (birth certificate). Plus
# the RETARGETED leg in test_core_m4wam1 (wl22 BY NAME: the NAMED SILENT
# pin flips to the LANDS law here — SUPERSEDED paragraph rides its
# header). GREEN at these bytes: m4wam2 5 passed. The saturating PAIR
# lawlet lives in test_core_m4wam1 (wl23 stays PAIR — the pair pins that
# the fix answers the CONVERSION, not "zero everything").
#
# NAMED UNCHANGED faces (brief law — neither fixed nor widened): the
# OUTPUT face wl24/wl25 LOOSE (gcc-rc1 side, input-scoped door); the
# multi-output partial-width color-dirt residual (a template writing %w
# into TWO wider outputs can still see residue in a color the door never
# touched — gcc's own -O0 answer is allocation-luck there; the sims
# oracle rows this commit must turn are all single-output; NAMED, no
# card claimed).
import os
import subprocess
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wam2_%s_%d_%s" % (os.environ.get("M4WAM_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

ROWS = {
    # W22 x splice-post-RENAME (own probe; postures measured own hands:
    # tip WALL — the pointer-based object had no address answer either;
    # {F} bytes SILENT 8 — the door transports its own residue; ship 7).
    "x2_w22_spliced_rename": ("""typedef unsigned short u16; typedef unsigned int u32; typedef unsigned long ul;
struct S { ul pad; u32 v; };
static inline u32 lowhalf(struct S *s) {   /* param name s: caller-capture */
    u32 d = 0;
    __asm__ volatile ("movw %[x], %w[d]" : [d] "=r" (d) : [x] "rm" ((u16)s->v));
    return d;
}
int answer(void) {
    struct S s; s.pad = 0; s.v = 0x11223344u;
    return (lowhalf(&s) == 0x3344u) ? 7 : 8;
}
""", 7),
    # W22 x F co-existence, W22-face FIRST (the order that DISCRIMINATES:
    # with the F-first order the frontier statement's own movzwl cleans
    # the color and tip answers 7 by accident — named in PROGRESS).
    "x3_coexist_pair": ("""typedef unsigned short u16; typedef unsigned int u32; typedef unsigned long ul;
struct R { ul bx; u16 ss; };
struct S { ul pad; u32 v; };
int answer(void) {
    struct R r; struct S s; u32 ar = 0, d = 0;
    r.bx = 0; r.ss = 0x34; s.pad = 0x99; s.v = 0x11223344u;
    __asm__ volatile ("movw %[y], %w[dd]" : [dd] "=r" (d)
                      : [y] "rm" ((u16)s.v));          /* W22 face first */
    __asm__ volatile ("movzwl %[s], %[a]" : [a] "=r" (ar)
                      : [s] "rm" ((u16)r.ss));         /* frontier face  */
    return (ar == 0x34u && d == 0x3344u) ? 7 : 8;
}
""", 7),
    # bit-preserving control: (u32)x keeps the static address answer —
    # gcc prints the source MEM there too. Green at tip AND ship.
    "x4_noop_cast_keeps_addr": ("""typedef unsigned int u32;
int answer(void) {
    u32 x = 41; u32 d = 0;
    __asm__ volatile ("movl %[x], %k[d]" : [d] "=r" (d) : [x] "rm" ((u32)x));
    return (int)d;
}
""", 41),
    # the drop is MODE-scoped the other way too: a double cast int→u16→u32
    # on an object base lands on the door and answers the CONVERTED value;
    # the source answer leaks the live HIGH half (measured own hands: tip
    # SILENT 8 — d carries 0x11220021 where the conversion says 0x21).
    "x5_widen_object_base_lands": ("""typedef unsigned short u16; typedef unsigned int u32; typedef unsigned long ul;
struct S { ul pad; u32 v; };
int answer(void) {
    struct S s; u32 d = 0;
    s.pad = 0; s.v = 0x11220021u;
    __asm__ volatile ("movl %[x], %k[d]" : [d] "=r" (d) : [x] "rm" ((u32)(u16)s.v));
    return (d == 0x21u) ? 7 : 8;
}
""", 7),
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
        fh.write(src)
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
def test_wam_silent_face_law(name):
    src, gexit = ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gexit, (
        "%s: gcc moved off the ground measured own hands at the tip "
        "bytes (now rc=%d %r) — re-measure before believing this row"
        % (name, grc, g))
    brc, b = _side(name, src, "blcc")
    assert brc == 0, ("%s: rc=%d — the silent-face drop/door route died "
                      "back into a wall:\n%s" % (name, brc, str(b)[:300]))
    assert b == g, ("%s: SILENT — blcc %d vs gcc %d. THE census cannot "
                    "see this class (accepted either way): this row IS "
                    "the screen" % (name, b, g))


def test_wam_value_conv_one_home():
    # ONE drop-site, ONE predicate, ONE placement restorer — the silent
    # face must not grow a second mechanism beside the door.
    ag = open(os.path.join(REPO, "blcc", "asmgen.py")).read()
    assert ag.count("def _asm_value_conv") == 1, "the mode-test is not one"
    assert ag.count("def _asm_int_side") == 1, "the side-test is not one"
    assert ag.count('if o.vslot is not None and o.reg != "rax":') == 1, (
        "the placement value-restoration is not ONE site — a second "
        "park-place is the second mechanism this law forbids")
    ec = open(os.path.join(REPO, "blcc", "expr_codegen.py")).read()
    assert "def _asm_value_conv" not in ec, (
        "the mode-test was smuggled into the value-as-address family — "
        "wl06 pins that home LOOSE by the gcc oracle")
