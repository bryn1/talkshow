# M4 W-AI COMMIT-0 — asmsub '+r'-ON-PACKED-BITFIELD LOUDIFY (MC 12404.2.153
# / job 12846, card 12846). One concern: the named SILENT door of
# test_core_m4wah1 goes LOUD, PACKED-SCOPED ONLY, at the ONE operand home.
r"""M4 W-AI COMMIT-0 — the lead ruling on the sims decision pack (card 12845
§4): the read-write '+' `"+r"` asm operand on a PACKED bitfield member is a
SILENT divergence (gcc 50 vs blcc 0, pinned at W-AH) whose blast screen over
ALL 591 accepted streams flipped N=0 — the pre-registered rule selects
LOUDIFY-NOW, and the FIX (gcc's extract→op→masked write-back window law,
sims §4.2) rides its OWN card. This commit moves NO value: the corpus
carries zero shipped shapes; what ships is the refusal so no future stream
can land SILENT-WRONG on this face.

SCOPE LAW (sims §4.1/§4.3, the measured over-fire): the arm is
PACKED-SCOPED. as02 — the UNPACKED twin — answers CORRECT today (PAIR
50/50): a loudify that fires there would refuse correct code. The packed
key REUSES the shipped law `_bf_owner_packed` (types.py): bitfield member
whose OWNER (nesting included — the W-G anon-hoist face) is packed. That is
exactly the population the W-X window access law serves, so gate and law
share ONE home.

Rows as01–as08 are VERBATIM transplants of the sims `asmsub/src` probes
(exit IS the answer; gcc REC twin, -no-pie, run — the shipped battery
idiom). Measured postures (sims §4.2 + this card's screen): the 7 packed
rows go WALL rc2 with the named sentence; the unpacked twin stays PAIR
50/50 — that row is ALSO the scope witness (a loudify smuggled to unpacked
scope flips it RED: the LOUDIFY-SCOPE plant rides it).

SUPERSEDED (the WALL posture) at M4 W-AK (MC 12404.2.156): the fix
LANDED — the pend-loop masked write-back rides the SHIPPED packed RMW
door `_bf_store(value_ready=True, base_slot=..)` (`_bf_incdec`'s door),
one window law, one home. The 7 packed rows RETARGETED BY NAME to
RUN-PAIR (teeth inverted: a raw-unit store answers WRONG here and flips
them RED); as03 rides the sims-§4 NAMED divergence (gcc register-
forwarding 220 vs blcc memory-law 1 — the memory identity is as03b,
m4wak3). THE SCOPE LAW STANDS: the gate keeps refusing, with the W-AK
sentence, shapes with no layout answer (m4wak3 sentence pin); as02
unpacks through both postures.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
TMP = "/dev/shm/m4wai0_%s_%d" % (os.environ.get("M4WAI_TAG", "x"),
                                 os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

PRE = """typedef unsigned int u32; typedef unsigned char u8; typedef unsigned long ul;
struct cx  { u32 a:4, b:30; } __attribute__((packed));
struct w9  { u32 x:9;  } __attribute__((packed));
struct nx  { u32 a:4, b:30; };
volatile u32 v;
"""

# (row) -> (probe body VERBATIM from sims asmsub/src, gcc REC exit, posture)
AS_ROWS = {
    # the W-AH pin VERBATIM reproduced: gcc 50 vs blcc 0 SILENT at tip
    "as01_packed_pin_silent": ("""
\tstruct cx s;
\ts.a = 0; s.b = 0;
\ts.a = 4; s.b = v ? 0x1234567u : 0x7654321u;
\t__asm__ volatile("" : "+r"(s.a));
\t__asm__ volatile("" : "+r"(s.b));
\treturn (int)(s.a * 3 + (s.b & 255u) * 7 + ((s.b >> 22) & 255u) * 11);
""", 50, "PAIR"),
    # UNPACKED twin: blcc CORRECT (PAIR 50) — loudify must NOT fire here
    "as02_unpacked_pair": (PRE.replace(
        "struct cx  { u32 a:4, b:30; } __attribute__((packed));",
        "struct cx  { u32 a:4, b:30; };") + """
int answer(void)
{
\tstruct cx s;
\ts.a = 0; s.b = 0;
\ts.a = 4; s.b = v ? 0x1234567u : 0x7654321u;
\t__asm__ volatile("" : "+r"(s.a));
\t__asm__ volatile("" : "+r"(s.b));
\treturn (int)(s.a * 3 + (s.b & 255u) * 7 + ((s.b >> 22) & 255u) * 11);
}
""", 50, "PAIR"),
    # span-FILLING saturating twin (the AMENDMENT-52 law-let: pairs ship
    # together — the non-filling as04 alone hides a width error)
    "as03_inc30_saturating": ("""
\tstruct cx s;
\ts.a = 4; s.b = 0x3FFFFFFFu;      /* span-filling: 30 bits all ones */
\t__asm__ volatile("inc %0" : "+r"(s.b));
\treturn (int)(s.b % 251u) + 1;
""", 220, "NAMED"),
    "as04_inc30_nonsaturating": ("""
\tstruct cx s;
\ts.a = 4; s.b = 0x1234567u;       /* mid value: same law, other face */
\t__asm__ volatile("inc %0" : "+r"(s.b));
\treturn (int)(s.b % 251u) + 1;
""", 195, "PAIR"),
    "as05_w9_inc_saturating": ("""
\tstruct w9 t;
\tt.x = 511u;                      /* span-filling: the 9-bit window */
\t__asm__ volatile("inc %0" : "+r"(t.x));
\treturn (int)(t.x & 511u) + 1;
""", 1, "PAIR"),
    "as06_w9_inc_nonsaturating": ("""
\tstruct w9 t;
\tt.x = 257u;                      /* non-filling twin */
\t__asm__ volatile("inc %0" : "+r"(t.x));
\treturn (int)(t.x & 511u) + 1;
""", 3, "PAIR"),
    # NEIGHBOUR survival: gcc 19 vs blcc 2 at tip (blcc lost s.a)
    "as07_window_neighbours_packed": ("""
\tstruct cx s;
\ts.a = 9; s.b = 0x100u;
\t__asm__ volatile("inc %0" : "+r"(s.b));
\treturn (int)(s.a * 2 + (s.b & 1u));
""", 19, "PAIR"),
    # TAIL survival: gcc 51 vs blcc 50 at tip (blcc lost z.tail)
    "as08_window_neighbours_w9": ("""
struct two { struct w9 p; u8 tail; } __attribute__((packed));
int answer(void)
{
\tstruct two z;
\tz.p.x = 300u; z.tail = 77u;
\t__asm__ volatile("inc %0" : "+r"(z.p.x));
\treturn (int)(z.p.x % 251u) + (int)(z.tail == 77u);
}
""", 51, "PAIR"),
}


def _src(name):
    body = AS_ROWS[name][0]
    if body.startswith("typedef"):     # self-contained row (as02 twin form)
        return body
    if "int answer(void)" in body:     # whole-function row rides the PRE
        return PRE + body
    return PRE + "int answer(void)\n{\n" + body + "}\n"


def _write(name, src):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, name + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    return c


def _gcc(src, tag):
    c = _write(tag, src)
    exe = os.path.join(TMP, tag + ".gcc")
    r = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe],
                       capture_output=True, text=True)
    assert r.returncode == 0, "gcc twin must build:\n" + r.stderr
    return subprocess.run([exe], capture_output=True, timeout=60).returncode


def _blcc(src, tag):
    c = _write(tag, src)
    o = os.path.join(TMP, tag + ".blcc.o")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", o],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    return r, o


@pytest.mark.parametrize("name", sorted(AS_ROWS))
def test_wai_asm_rw_packed_bitfield_lands_at_wak(name):
    # RETARGETED BY NAME at M4 W-AK (MC 12404.2.156; teeth INVERTED,
    # never dropped — was `test_wai_asm_rw_packed_bitfield_loudify`, the
    # W-AI pin that the '+r'-on-packed-bitfield face REFUSES LOUD while
    # the fix rode its card. The card LANDED: the pend-loop masked
    # write-back answers AT THE SHIPPED RMW DOOR, so the rows RUN-PAIR.
    # as02 (the UNPACKED scope witness) rode PAIR through BOTH postures:
    # the gate scope law (PACKED-only) holds under the fix — that is the
    # row's whole purpose. as03 is the sims-§4 NAMED DIVERGENCE: gcc's
    # 220 is REGISTER FORWARDING of the un-truncated result to a
    # same-expression readback; blcc answers the MEMORY law 1, the
    # identical memory (as03b twin PAIR exit=1, m4wak3 battery).
    src, gcc_exit, posture = _src(name), AS_ROWS[name][1], AS_ROWS[name][2]
    gx = _gcc(src, name)
    assert gx == gcc_exit, (
        "%s: gcc moved off the sims-measured exit %d (now %d) — the "
        "fix-law ground truth of card 12845 §4.2 changed; re-measure "
        "before believing this row" % (name, gcc_exit, gx))
    r, o = _blcc(src, name)
    assert r.returncode == 0, (
        "%s: rc=%d — the FIX died back into a wall (the gate must "
        "refuse ONLY shapes with no layout answer; the modelled class "
        "answers now):\n%s" % (name, r.returncode,
                               (r.stdout + r.stderr)[:300]))
    b = subprocess.run(["gcc", "-no-pie", "-o", o + ".bin", o],
                       capture_output=True, text=True)
    assert b.returncode == 0, b.stderr
    bx = subprocess.run([o + ".bin"], capture_output=True,
                        timeout=60).returncode
    if posture == "NAMED":
        assert bx == 1, (
            "%s: the NAMED divergence moved — gcc %d, blcc %d (memory-law "
            "1 was the sims §4 measurement; register-forwarding has NO "
            "card — re-measure before touching this door)" % (name, gx, bx))
        return
    assert bx == gx, ("%s: SILENT — blcc %d vs gcc %d (sims §4.2 clobber "
                      "class: a raw-unit store would answer HERE)"
                      % (name, bx, gx))


from test_core_m4w1 import STREAMS                       # noqa: E402
from test_core_m4w25b import _clean_i                    # noqa: E402

# Blast controls (kernel tier): accepted streams that CARRY '+r' operands
# (563 of the 591 do) must stay rc0 — the loudify screen measured N=0 flips
# on all 591; these three ride the suite as the heavy controls, the closest
# shipped shapes to the refused face.
BLAST_CTRL = ["arch_x86_entry_common.c.i",
              "arch_x86_entry_syscall_64.c.i",
              "arch_x86_kernel_apic_io_apic.c.i"]


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", BLAST_CTRL)
def test_wai_blast_controls_stay_accepted(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "waictl")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "waictl.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == 0, (
        "%s (accepted, carries '+r' asm) was REFUSED by the loudify — "
        "the blast screen priced 0 flips; first wall:\n%s"
        % (stream, next((ln for ln in (r.stdout + r.stderr).splitlines()
                         if ln.strip()), "(no output)")))
