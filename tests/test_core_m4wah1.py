# M4 W-AH INTERACTIONS — the packed fold window against the three shipped
# mechanisms it can meet (MC 12404.2.150 / job 12839, card 12839). One
# concern: packed window x const-fold, x byte order (q7 class), x inline
# splice POST-RENAME.
r"""M4 W-AH COMMIT-INTERACTIONS — the {WFW} producer window (see
test_core_m4wah0.py for the law itself) measured where it MEETS the shipped
mechanisms, per the sims contract (card 12838 §2 probes + §6 q7 plant):

* const-fold: a CONSTANT-AGGREGATE local init folds to a static template
  (the DATA path — the fold is what put the local shapes in front of the
  producer in the first place); a VOLATILE-sourced value defeats the fold
  and rides the shipped LOCAL RMW path, which the sims probes measured
  byte-correct at the wfw arm (gcc 31 = pbf2 31 = wfw 31; post-INIT
  byte-view 239 = 239 = 239) — the {LW} local-window hunk has NO measured
  need and is NOT authored (NAMED no-op).
* byte order: the fold window is LITTLE-ENDIAN (W-F layout law). The sims
  q7 plant (window assembled/stored BIG-endian) flipped exactly the
  w>8 crossing rows to SILENT — the byte-view row below is that witness
  in the repo: bytes are the answer, a BE window cannot hide.
* splice POST-RENAME: the W-P inline door clones a `static inline` body
  and renames its locals; a packed cross-byte init inside the clone must
  answer identically in both clones (wd301 precedent, the W-AG SPLICE row
  carried over to the window law).
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
TMP = "/dev/shm/m4wah1_%s_%d" % (os.environ.get("M4WAH_TAG", "x"),
                                 os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

PRE = """typedef unsigned int u32; typedef unsigned char u8; typedef unsigned long ul;
struct cx  { u32 a:4, b:30; } __attribute__((packed));
struct w9  { u32 x:9;  } __attribute__((packed));
"""


def _pair(src, tag, expect_gcc=None):
    """Build+run under gcc REC and blcc; the EXIT IS the object answer."""
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    gexe = os.path.join(TMP, tag + ".gcc")
    rg = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [c, "-o", gexe],
                        capture_output=True, text=True)
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    if expect_gcc is not None:
        assert gx == expect_gcc, "gcc answered %d, expected %d" % (
            gx, expect_gcc)
    o = os.path.join(TMP, tag + ".blcc.o")
    bexe = os.path.join(TMP, tag + ".blcc")
    rb = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", o],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO))
    assert rb.returncode == 0, (
        "blcc refused the packed fold-window interaction rc=%d:\n%s"
        % (rb.returncode, (rb.stdout + rb.stderr)[:300]))
    r = subprocess.run(["gcc", "-no-pie", "-o", bexe, o],
                       capture_output=True, text=True)
    assert r.returncode == 0, "blcc object must link:\n" + r.stderr
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert bx == gx, "SILENT divergence blcc %d vs gcc %d" % (bx, gx)
    return gx


def test_wf_byte_view_cross_window_pair():
    # THE window witness, authored here (sims q2/q3/q7 classes): byte-view
    # read-back of the crossing object + the overrun sentinel. `b` is bits
    # 4..33 — the fold window MUST be ceil((4+30)/8)=5 bytes; a floor
    # window, a width-bytes window, a BE window or an extent-CLAMPED
    # window all change THESE BYTES, and the exit is the byte view.
    src = PRE + """
static struct cx s = { .a = 5, .b = 0x3FFFFFFFu };
static unsigned char gd = 0x5A;
int answer(void)
{
\tconst unsigned char *p = (const unsigned char *)&s;
\treturn (int)((p[0]*3 + p[1]*7 + p[2]*11 + p[3]*13 + p[4]*17
\t\t     + gd*19 + (s.b & 255u)*23 + ((s.b >> 26) & 15u)*29) % 251);
}
"""
    _pair(src, "wah1-byte")


def test_wf_local_const_init_in_reach_pair():
    # const local-init face WITHIN the shipped unit's reach: a constant
    # aggregate local init lands through `_init_bf_local` (frame RMW over
    # the declared unit); a value whose bits all fit the declared unit
    # pairs gcc. This is what the local INIT door ships at W-AH.
    src = PRE + """
int answer(void)
{
\tstruct cx s = { .a = 5, .b = 0xFFFFFFFu };
\treturn (int)((s.a*3 + (s.b & 255u)*7 + ((s.b >> 22) & 255u)*11) % 251);
}
"""
    _pair(src, "wah1-inreach")


def test_wf_local_static_fold_template_pair():
    # THE const-fold face, measured honest: a function-scope `static`
    # (NOT an auto local — the auto const aggregate rides frame stores,
    # own asm receipt .tmp/m4-wah-build/logs/fold-shape-receipt.txt)
    # folds to the static template: the DATA path, the producer hunk and
    # the {WFW} window carry a SATURATING crossing value — 30 bits all
    # ones, byte 4 = 0x03 live — exit-pair vs gcc.
    src = PRE + """
int answer(void)
{
\tstatic struct cx s = { .a = 5, .b = 0x3FFFFFFFu };
\treturn (int)((s.a*3 + (s.b & 255u)*7 + ((s.b >> 22) & 255u)*11) % 251);
}
"""
    _pair(src, "wah1-fold", expect_gcc=87)


def test_wf_local_const_saturating_lw_pinned(tmp_path):
    # THE {LW} DOOR, pinned SILENT VISIBLE (sims card 12838 NAMED no-op,
    # corpus volume 0 — an auto LOCAL bitfield INIT RMWs over the
    # DECLARED unit: a saturating crossing value (0x3FFFFFFF << 4 reaches
    # byte 4) loses its top bits — blcc 234 vs gcc 87, receipted own
    # hands at ship bytes, asm `movl -8(%rbp)` 4-byte unit RMW). The
    # brief FORBIDS the {LW} hunk this card (it moves ZERO corpus
    # streams — a dead law is not a law); pinned so the door CANNOT
    # change answer beside this wave unnoticed: a movement here is the
    # {LW} law's OWN card arriving.
    src = PRE + """
int answer(void)
{
\tstruct cx s = { .a = 5, .b = 0x3FFFFFFFu };
\treturn (int)((s.a*3 + (s.b & 255u)*7 + ((s.b >> 22) & 255u)*11) % 251);
}
"""
    p = tmp_path / "walw.c"
    p.write_text(src + MAIN)
    gexe = tmp_path / "walw.g"
    rg = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [str(p), "-o", str(gexe)],
                        capture_output=True, text=True)
    assert rg.returncode == 0, rg.stderr[:300]
    gx = subprocess.run([str(gexe)], capture_output=True, timeout=60).returncode
    assert gx == 87, "gcc moved off the measured 87 — re-measure the door"
    o = tmp_path / "walw.o"
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", str(p),
                        "-o", str(o)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO))
    assert b.returncode == 0
    r = subprocess.run(["gcc", "-no-pie", "-o", str(tmp_path / "walw.b"),
                        str(o)], capture_output=True, text=True)
    assert r.returncode == 0
    bx = subprocess.run([str(tmp_path / "walw.b")],
                        capture_output=True, timeout=60).returncode
    assert bx == 234, (
        "the NAMED {LW} door ANSWER CHANGED (%d, was the pinned silent "
        "234 vs gcc 87) — the local-window law is its OWN card; do not "
        "half-fix it beside this one" % bx)


def test_wf_volatile_defeats_fold_pair():
    # The sims' fold-defeating probe (local-window-probe.txt): a
    # VOLATILE-sourced value rides the shipped LOCAL RMW path (the {LW}
    # arm is NOT needed — this row measures that claim at ship bytes;
    # sims: gcc 31 = pbf2 31 = wfw 31, byte-view 239 = 239).
    src = PRE + """
volatile unsigned v;
int answer(void)
{
\tstruct w9 s;
\tv = 0x155;
\ts.x = 0; s.x = (u32)v;
\treturn (int)(s.x == 0x155 ? (int)(0x155 % 251) : 250);
}
"""
    _pair(src, "wah1-vol", expect_gcc=90)


def test_wf_splice_post_rename_pair():
    # splice POST-RENAME (W-P inline door, wd301 precedent — the W-AG
    # SPLICE leg carried to the window law): the packed crossing init
    # lives INSIDE the cloned body; both clones answer (distinct values
    # per clone — a rename collision WOULD show), the asm anchor keeps
    # the runtime operand per-clone, and the splice must not fall back
    # to a call. The anchor rides a PLAIN int on purpose: an '+r'
    # operand on a BITFIELD MEMBER is the NAMED asmsub door below.
    src = PRE + """
static inline int pick(int q)
{
\tstruct cx s = { .a = 4, .b = (u32)(q ? 0x1234567u : 0x7654321u) };
\t__asm__ volatile("" : "+r"(q));
\treturn (int)(s.a * 3 + (s.b & 255u) * 7 + ((s.b >> 22) & 255u) * 11
\t\t     + q);
}
int answer(void){ int r = pick(1) + pick(0); return r % 251; }
"""
    gx = _pair(src, "wah1-sp")
    assert gx != 0
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "wah1-sp-pin.c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    s = os.path.join(TMP, "wah1-sp-pin.s")
    r = subprocess.run([sys.executable, "-m", "blcc", "--emit-asm", c,
                        "-o", s], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO))
    assert r.returncode == 0, r.stderr[:300]
    asm = open(s + ".s").read()
    assert "\npick:" not in asm and not asm.startswith("pick:"), \
        "the splice fell back to the CALL law: a `pick:` leaf survived"


def test_wf_asm_rw_operand_on_bitfield_is_silent_pinned(tmp_path):
    # THE NAMED DOOR (pre-existing AT TIP, pinned UNMOVED — its own card,
    # NOT the producer window's home): a read-write '+r' asm operand on a
    # BITFIELD MEMBER stores the RAW operand value at the object's base
    # address (asm dump: `movl %eax, -8(%rbp)` over the packed 5-byte
    # object), clobbering the neighbours. Receipts (own hands, this card,
    # logs/splice-asm-dump.txt): packed gcc 50 vs blcc 0 AT TIP ALREADY
    # and at ship (UNMOVED); the non-packed twin answers 50/50 (PAIRS).
    # Pinned so a half-fix that changes the answer without the real law
    # flips this leg — the W-AG wgF08 pin idiom: SILENT, VISIBLE.
    src = PRE + """
volatile u32 v;
int answer(void)
{
\tstruct cx s;
\ts.a = 0; s.b = 0;
\ts.a = 4; s.b = v ? 0x1234567u : 0x7654321u;
\t__asm__ volatile("" : "+r"(s.a));
\t__asm__ volatile("" : "+r"(s.b));
\treturn (int)(s.a * 3 + (s.b & 255u) * 7 + ((s.b >> 22) & 255u) * 11);
}
"""
    p = tmp_path / "waasm.c"
    p.write_text(src + MAIN)
    gexe = tmp_path / "waasm.g"
    rg = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [str(p), "-o", str(gexe)],
                        capture_output=True, text=True)
    assert rg.returncode == 0, rg.stderr[:300]
    gx = subprocess.run([str(gexe)], capture_output=True, timeout=60).returncode
    assert gx == 50, "gcc moved off the measured 50 — re-measure the door"
    o = tmp_path / "waasm.o"
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", str(p),
                        "-o", str(o)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO))
    assert b.returncode == 0
    r = subprocess.run(["gcc", "-no-pie", "-o", str(tmp_path / "waasm.b"),
                        str(o)], capture_output=True, text=True)
    assert r.returncode == 0
    bx = subprocess.run([str(tmp_path / "waasm.b")],
                        capture_output=True, timeout=60).returncode
    assert bx == 0, (
        "the NAMED asmsub door ANSWER CHANGED (%d, was the pinned silent "
        "0 at tip and at W-AH ship) — the real law has its OWN card; do "
        "not half-fix it beside this one" % bx)
