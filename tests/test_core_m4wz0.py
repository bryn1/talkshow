"""M4 W-Z COMMIT-0 pins (MC 12404.2.121 / job 12774): the case label rides
the SHIPPED width law to the control's promoted type.

WHY THIS FILE EXISTS. W-Z's design-sims (card 12768, row cl16) measured a
PRE-EXISTING SILENT at tip 070dacc: gcc converts every case label to the
switch control's PROMOTED type — `case 0x100000000L:` under an `int` control
warns ("overflow in conversion") and TRUNCATES to 0, whereupon the case
MATCHES 0. blcc's parse-side fold answered the UNBOUNDED Python integer, so
the same label matched nothing and the switch rode its default arm with
rc0 on both sides — a silent wrong answer, the y27 disease in the switch's
own family (W-O's door). Volume 0 in the pinned corpus, repaired FIRST
(repair-first doctrine) before the wave's levers. The wrap is
`TypeMap._wrapw` — WHG-B's shipped width law, imported, never copied — and
these legs are its RUN-PAIRS: gcc builds, blcc builds, the binaries' exit
codes are the encoded answer (sims lineage: the exit code IS the memory
answer). RED-first: every row here answered the DEFAULT arm at 070dacc
(see .tmp/m4-wz-build/logs/cl16-redfirst.txt); the dup-after-wrap row went
RED for the opposite reason (no conversion, no collision, no refusal).
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wz0_%s_%d_%s" % (os.environ.get("M4WZ_TAG", "x"),
                                   os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

# (source, expected) — expected = the exit code BOTH binaries must answer
# (measured gcc posture, truncated-label matching its wrapped value), or the
# string "refuse" when gcc itself refuses (rc!=0) and blcc must refuse too.
ROWS = {
    # cl16 VERBATIM: over-wide label, int control — truncates to 0, MATCHES.
    "w0-int-trunc-matches": ("""
int main(void) { volatile int x = 0;
                 switch (x) { case 0x100000000L: return 161;
                              default: return 160; } }
""", 161),
    "w1-ulong-label-int": ("""
int main(void) { volatile int x = 0;
                 switch (x) { case 0x100000000UL: return 171;
                              default: return 170; } }
""", 171),
    # two spellings, ONE wrapped value — gcc's duplicate check keys on the
    # CONVERTED value, so this is a refusal, not a pair.
    "w2-dup-after-wrap": ("""
int main(void) { volatile int x = 1;
                 switch (x) { case 1: return 1;
                              case 0x100000001L: return 2;
                              default: return 3; } }
""", "refuse"),
    "w3-uint-control-wrap": ("""
int main(void) { volatile unsigned int x = 1;
                 switch (x) { case 0x100000001U: return 181;
                              default: return 180; } }
""", 181),
    "w4-neg-label-uint-control": ("""
int main(void) { volatile unsigned int x = 0xFFFFFFFFU;
                 switch (x) { case -1: return 191;
                              default: return 190; } }
""", 191),
    # signed control already wraps: 0xFFFFFFFFU as a LABEL against int −1 is
    # the same VALUE — refusal, measured.
    "w5-dup-signed-wrap": ("""
int main(void) { volatile int x = -1;
                 switch (x) { case -1: return 1;
                              case 0xFFFFFFFFU: return 2;
                              default: return 3; } }
""", "refuse"),
    # the identity leg: a 64-bit control keeps its wide labels WIDE — the
    # fix must not truncate what gcc keeps.
    "w6-long-control-identity": ("""
int main(void) { volatile long x = 0x100000000L;
                 switch (x) { case 0x100000000L: return 151;
                              default: return 150; } }
""", 151),
    # char control PROMOTES to int (§2.2) — the label converts to int, not
    # to char: 0x100000000L → 0 matches; 300 stays 300 and never matches.
    "w7-char-control-promotes": ("""
int main(void) { volatile char x = 0;
                 switch (x) { case 0x100000000L: return 141;
                              default: return 140; } }
""", 141),
    "w8-char-narrow-label": ("""
int main(void) { volatile char x = 5;
                 switch (x) { case 300: return 131;
                              default: return 130; } }
""", 130),
    # the gnu89 range arm converts BOTH bounds (case A ... B): the wrapped
    # window 0x100000000L ... 0x100000002L becomes 0 ... 2 and takes 1.
    "w9-range-bounds-convert": ("""
int main(void) { volatile int x = 1;
                 switch (x) { case 0x100000000L ... 0x100000002L:
                                  return 121;
                              default: return 120; } }
""", 121),
    # enum control (int-rank): today's labels ride unchanged; identity pair.
    "w10-enum-control-identity": ("""
enum e { E0 = 0, E7 = 7 };
int main(void) { volatile enum e x = E7;
                 switch (x) { case 7: return 111; default: return 110; } }
""", 111),
}


def _setup():
    os.makedirs(TMP, exist_ok=True)
    return TMP


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc"] + GCC_REC + [c, "-o", exe]
        env = None
    else:
        exe = os.path.join(TMP, tag + ".blcc")
        cmd = ["python3", "-m", "blcc", c, "-o", exe]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    return r, exe


@pytest.mark.parametrize("name", sorted(ROWS))
def test_case_label_width_law_run_pairs(name):
    src, expect = ROWS[name]
    _setup()
    if expect == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0, "gcc oracle must refuse:\n" + rg.stdout
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, \
            "%s: blcc SILENTLY ACCEPTED a shape gcc refuses — %s" % (
                name, rb.stdout[:200])
        assert "duplicate case" in rb.stderr, rb.stderr
        return
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "blcc rc=%d:\n%s" % (rb.returncode, rb.stderr)
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d — the label "  \
        "did not convert to the promoted control type" % (name, bx, gx)


def test_conversion_lands_before_the_duplicate_check():
    # the dup check keys on the CONVERTED value (gcc's law): w2 above pairs
    # the refusal; this names the blcc-side sentence for the wrapped pair.
    src = ROWS["w2-dup-after-wrap"][0]
    _setup()
    rb, _ = _build(src, "w2-sentence", "blcc")
    assert rb.returncode == 2 and "duplicate case" in rb.stderr, rb.stderr
