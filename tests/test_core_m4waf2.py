# LINES reason: one law (M4 W-AF COMMIT-Y, MC 12404.2.144 / job 12831):
# an attribute list between the qual words and the type SPECIFIER is
# LEGAL C — every row here is one measured face of that parse law and
# its priced blast radius. Sources VERBATIM from the card-12825 battery
# (".tmp/m4-waf-sims/law/src/", "the 34 rows stand").
r"""M4 W-AF COMMIT-Y — THE ATTR-BEFORE-SPECIFIER PARSE LAW ({Y}).

THE WALLS (live real-make table, card 12825 §6):
arch/x86/kernel/cpu/common.c:1047:59 and idt.c:57:59 —
`static const __attribute__((__section__(".init.rodata"))) struct …`
falls to `parse: expected a type, found 'struct'`; corpus volume
EXACTLY 2 (cpu_common + idt). THE FIX reuses the shipped skip mechanism
(`_at_attr`/`_skip_gnu_attrs` — the pair the declarator-star law rides)
behind a new attribute-FIRST gate in `_base_type_core`, re-entering the
specifier head so the tag/typeof/enum branch gets its look (sims probe
p5). THE SCALAR CONTROL (af29) pairs at tip and must keep pairing —
the sims p4 plant (skip ONE TOKEN instead of the LIST) flips its exit
2→14; that is the over-reach witness pinned at the wave's teeth gate.

WHAT {Y} OPENS AND WHAT IT DOES NOT (DoD FORBIDDEN list): the two
streams RE-WALL at the W-F packed-bitfield family (cpu/common →
45216:8, idt → 56743:2) — W-F is the NEXT wave (3-base→5-after-{Y}
priced), NOT closed here; the kernel-tier legs below pin the re-wall
sentences AND that neither stream lands. io_apic 52201:20 stays
character-identical (P3a: the attr law does NOT reach the packed
initializer). attr × typeof: the typeof spelling after quals+attr stops
being a parse refusal — the post-parse posture is the NAMED mirror
limit (typeof-of-FUNC-ident, af25/af27 family): refusal rc2, NEVER
silent; the tag-body typeof (attr × {Y} × {T2}) run-pairs (16).
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4waf2_%s_%d_%s" % (os.environ.get("M4WAF_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

ROWS = {
    # THE wall itself, VERBATIM af28 (exits 2 both sides at {Y}).
    "y-af28-attr-before-struct": ("""
struct D { int a; };
static const __attribute__((__section__(".init.rodata"))) struct D tab[]
\t= { {1} };
int answer(void) { return tab[0].a + 1; }
""", 2, "pair"),
    # af29, the SCALAR CONTROL that pairs at tip already — the row that
    # keeps the fix from over-reaching (sims p4: skip-one-token plants
    # flip THIS row's exit; over-reach has a witness).
    "y-af29-attr-before-scalar-control": ("""
static const __attribute__((__section__(".init.rodata"))) int scal = 7;
int answer(void) { return scal; }
""", 7, "pair"),
    # attr × {Y} × typeof: a typeof member type inside an attributed
    # tag declaration — the two W-AF laws MEET here; RED at tip (the
    # attr parse wall), PAIR at {Y} (measured 16: 5 + 4 + 7).
    "y-attr-times-typeof-in-tag-body": ("""
static int v = 7;
static const __attribute__((__aligned__(8))) struct H2 { typeof(v) a; int b; }
    th2[] = { { 3, 4 }, { 5, 6 } };
int answer(void){ return th2[1].a + th2[0].b + v; }
""", 16, "pair"),
}


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe]
    else:
        o = os.path.join(TMP, tag + ".blcc.o")
        exe = os.path.join(TMP, tag + ".blcc")
        b = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                           capture_output=True, text=True, cwd=REPO,
                           env=dict(os.environ, PYTHONPATH=REPO))
        if b.returncode != 0:
            return b, None
        cmd = ["gcc", "-no-pie", "-o", exe, o]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r, exe


@pytest.fixture(autouse=True, scope="module")
def _tmp():
    os.makedirs(TMP, exist_ok=True)
    yield


@pytest.mark.parametrize("name", sorted(ROWS))
def test_y_run_pairs(name):
    src, expect, _cls = ROWS[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "%s: gcc answered %d, expected %d" % (
        name, gx, expect)
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "%s: blcc rc=%d:\n%s" % (
        name, rb.returncode, (rb.stdout + rb.stderr)[:300])
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


def test_y_attr_x_typeof_of_function_stays_named_refusal():
    # attr (Y law) × typeof(FUNC-ident) (the mirror's NAMED None — it
    # types "var" symbols only, af25/af27 family): the parse refusal of
    # tip is DEAD at {Y}; what remains is a downstream sema refusal,
    # rc2, NEVER silent. The gcc side pairs (rc0, exit 9). If this ever
    # lands rc0 with a wrong value, or the parse family resurrects, RED.
    src = """
static int nine(void){ return 9; }
static const __attribute__((__aligned__(8))) typeof(nine) *tbl = nine;
int answer(void){ return tbl(); }
"""
    c = os.path.join(TMP, "y2.c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    rg, gexe = _build(src, "y2g", "gcc")
    assert rg.returncode == 0, rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    assert gx == 9, gx
    rb = subprocess.run(["python3", "-m", "blcc", "-c", c,
                         "-o", os.path.join(TMP, "y2b.o")],
                        capture_output=True, text=True, cwd=REPO,
                        env=dict(os.environ, PYTHONPATH=REPO))
    assert rb.returncode != 0, \
        "the typeof-of-function-ident limit landed silently — it is a " \
        "NAMED limit (af25/af27 mirror family), not this wave's law"
    assert "expected a type" not in rb.stderr, \
        "the attr-before-specifier parse family is STILL ALIVE:\n" \
        + rb.stderr[:300]


# ---- kernel tier: the two corpus streams re-wall at W-F, NOT land ------

from test_core_m4w1 import STREAMS                       # noqa: E402
from test_core_m4w25b import _clean_i                    # noqa: E402

STREAM_ROWS = {
    "arch_x86_kernel_cpu_common.c.i": "45216:8",
    "arch_x86_kernel_idt.c.i": "56743:2",
}


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", sorted(STREAM_ROWS))
def test_y_streams_rewrite_at_wf_never_land(stream, tmp_path):
    # THE Y wave-move receipts (census-priced): the attr parse wall is
    # DEAD, the next wall is the W-F packed-bitfield family at the
    # sims-predicted line:col (W-F = NEXT wave, NOT closed here; the
    # io_apic row at 52201:20 must stay character-identical per P3a —
    # that stream is UNMOVED in the ship census).
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "waf2")
    r = subprocess.run(["python3", "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "waf2.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO))
    first = next(ln for ln in (r.stdout + r.stderr).splitlines()
                 if ln.strip())
    assert "packed bitfield member initializer" in first, \
        "%s must re-wall at W-F, got:\n%s" % (stream, first)
    assert STREAM_ROWS[stream] in first, \
        "%s re-wall line:col drifted from %s:\n%s" % (
            stream, STREAM_ROWS[stream], first)
    assert "expected a type" not in first, "attr family still alive"
