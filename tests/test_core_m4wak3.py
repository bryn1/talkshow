# M4 W-AK LEVER-C battery — the asmsub '+r'-on-packed-bitfield FIX at the
# pend loop (MC 12404.2.156 / card 12873; sims card 12849 §4, probes
# as01-as13 VERBATIM, postures out/as-{tip,c,c0}.txt).
#
# THE LAW: gcc's extract -> OPERATE -> MASKED write-back. The shipped
# W-X door already reads packed fields through the window; lever-C rides
# the SHIPPED masked-RMW door `_bf_store(value_ready=True, base_slot=..)`
# (`_bf_incdec`'s door) for the '+r' write-back — REUSE, one window law,
# one home. Postures (sims-measured, 14 rows): 13 PAIR + as03 NAMED
# SILENT (gcc 220 vs blcc 1 — gcc FORWARDS the un-truncated arithmetic
# result to a same-expression readback; blcc's MEMORY law is identical,
# witnessed by as03b forced-memory PAIR exit=1; the residual is gcc
# register-forwarding, NOT this door's law — card 12845's 220-row
# reading REFINED by the sims, own hands). as02 unpacked scope-witness
# PAIR unchanged: the gate stays PACKED-scoped (W-AI scope law holds;
# the W-AK refusal sentence stands for shapes with no layout answer).
# Width-suffix law (narrowing twins): %k0/%w0 operate on the operand's
# register WIDTH (as09-as13); the masked store still honours the FIELD —
# as11/12/13 are packed x narrowing CO-EXISTENCE rows.
#
# RED FIRST at commit-B bytes (W-AI loudify still standing): 12 failed /
# 3 passed — the 11 tip WALL rows (sims out/as-tip.txt: as03b volatile twin
# too; the sims §4 prose count 10 understates its own table by the volatile
# row — table wins) + the W-AK sentence leg (tip carries the OLD W-AI
# sentence). GREEN at tip already: as09/as10 unpacked narrow twins (never
# gated) and the as02 scope witness — logs/m4wak3-red-tipB.log.
import os
import subprocess
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wak3_%s_%d_%s" % (os.environ.get("M4WAK_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

PRE = ("typedef unsigned int u32; typedef unsigned char u8; "
       "typedef unsigned long ul;\n"
       "struct cx  { u32 a:4, b:30; } __attribute__((packed));\n"
       "struct w9  { u32 x:9;  } __attribute__((packed));\n"
       "struct nx  { u32 a:4, b:30; };\n"
       "volatile u32 v;\n")
NPRE = ("typedef unsigned int u32; typedef unsigned short u16;\n"
        "typedef unsigned long ul;\n\n")
# name -> (source, gcc-exit, posture)  — exits VERBATIM sims out/as-c.txt
AS_ROWS = {
    "as01_packed_pin_silent": (PRE + """
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
""", 50, "PAIR"),          # SCOPE WITNESS: unpacked never gated, was PAIR
    "as03_inc30_saturating": (PRE + """
int answer(void)
{
\tstruct cx s;
\ts.a = 4; s.b = 0x3FFFFFFFu;      /* span-filling: 30 bits all ones */
\t__asm__ volatile("inc %0" : "+r"(s.b));
\treturn (int)(s.b % 251u) + 1;
}
""", 220, "NAMED_DIVERGE"),        # blcc MEMORY answer 1; see below
    "as03b_inc30_memory_view": (
        "typedef unsigned int u32; typedef unsigned char u8;\n"
        "typedef unsigned long ul;\n\n"
        "struct cx  { u32 a:4, b:30; } __attribute__((packed));\n"
        + """
int answer(void)
{
    volatile struct cx s;
    s.a = 4; s.b = 0x3FFFFFFFu;      /* span-filling: 30 bits all ones */
    __asm__ volatile("inc %0" : "+r"(s.b));
    return (int)(s.b % 251u) + 1;    /* MEMORY view (forced reload) */
}
""", 1, "PAIR"),
    "as04_inc30_nonsaturating": (PRE + """
int answer(void)
{
\tstruct cx s;
\ts.a = 4; s.b = 0x1234567u;       /* non-filling mid value */
\t__asm__ volatile("inc %0" : "+r"(s.b));
\treturn (int)(s.b % 251u) + 1;
}
""", 195, "PAIR"),
    "as05_w9_inc_saturating": (PRE + """
int answer(void)
{
\tstruct w9 t;
\tt.x = 511u;                      /* span-filling: the 9-bit window */
\t__asm__ volatile("inc %0" : "+r"(t.x));
\treturn (int)(t.x & 511u) + 1;
}
""", 1, "PAIR"),
    "as06_w9_inc_nonsaturating": (PRE + """
int answer(void)
{
\tstruct w9 t;
\tt.x = 257u;                      /* non-filling mid value */
\t__asm__ volatile("inc %0" : "+r"(t.x));
\treturn (int)(t.x & 511u) + 1;
}
""", 3, "PAIR"),
    "as07_window_neighbours_packed": (PRE + """
int answer(void)
{
\tstruct cx s;
\ts.a = 9; s.b = 0x100u;
\t__asm__ volatile("inc %0" : "+r"(s.b));
\treturn (int)(s.a * 2 + (s.b & 1u));
}
""", 19, "PAIR"),
    "as08_window_neighbours_w9": (PRE + """
struct two { struct w9 p; u8 tail; } __attribute__((packed));
int answer(void)
{
\tstruct two z;
\tz.p.x = 300u; z.tail = 77u;
\t__asm__ volatile("inc %0" : "+r"(z.p.x));
\treturn (int)(z.p.x % 251u) + (int)(z.tail == 77u);
}
""", 51, "PAIR"),
    "as09_narrow_k0_width": (NPRE + """
struct S { unsigned int a; unsigned int b:30; unsigned int c; };
int answer(void)
{
    struct S s; s.a = 1; s.b = 3; s.c = 4;
    __asm__ __volatile__("inc %k0" : "+r"(s.b));
    return (int)s.b;
}
""", 4, "PAIR"),
    "as10_narrow_w0_width": (NPRE + """
struct S { unsigned int a; unsigned int b:30; unsigned int c; };
int answer(void)
{
    struct S s; s.a = 1; s.b = 3; s.c = 4;
    __asm__ __volatile__("inc %w0" : "+r"(s.b));
    return (int)s.b;
}
""", 4, "PAIR"),
    "as11_narrow_k0_packed": (
        "typedef unsigned int u32; typedef unsigned char u8;\n"
        "typedef unsigned long ul;\n\n"
        "struct P { unsigned int a; unsigned int b:30; unsigned int c; } "
        "__attribute__((packed));\n"
        + """
int answer(void)
{
    struct P s; s.a = 1; s.b = 3; s.c = 4;
    __asm__ __volatile__("inc %k0" : "+r"(s.b));
    return (int)s.b;
}
""", 4, "PAIR"),
    "as12_narrow_w0_packed": (
        "typedef unsigned int u32; typedef unsigned char u8;\n"
        "typedef unsigned long ul;\n\n"
        "struct P { unsigned int a; unsigned int b:30; unsigned int c; } "
        "__attribute__((packed));\n"
        + """
int answer(void)
{
    struct P s; s.a = 1; s.b = 3; s.c = 4;
    __asm__ __volatile__("inc %w0" : "+r"(s.b));
    return (int)s.b;
}
""", 4, "PAIR"),
    "as13_k0_saturating": (
        "typedef unsigned int u32; typedef unsigned char u8;\n"
        "typedef unsigned long ul;\n\n"
        "struct P { unsigned int a; unsigned int b:30; unsigned int c; } "
        "__attribute__((packed));\n"
        + """
int answer(void)
{
    struct P s; s.a = 1; s.b = 0x3FFFFFFDu; s.c = 4;
    __asm__ __volatile__("add %k0, %k0" : "+r"(s.b));
    return (int)((s.b >> 8) & 255u);
}
""", 255, "PAIR"),
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
        #   the sims posture-runner shape (the exit IS the answer)
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


@pytest.mark.parametrize("name", sorted(AS_ROWS))
def test_wak_asm_rw_packed_fix_law(name):
    src, gcc_exit, posture = AS_ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gcc_exit, (
        "%s: gcc moved off the sims-measured %d (now rc=%d %r) — the "
        "ground truth of card 12849 §4 changed; re-measure before "
        "believing this row" % (name, gcc_exit, grc, g))
    brc, b = _side(name, src, "blcc")
    if posture == "NAMED_DIVERGE":
        # as03: blcc LANDED (the wall is gone) and answers the MEMORY
        # law 1; gcc's 220 is REGISTER FORWARDING of the un-truncated
        # arithmetic result into a same-expression readback — a DIFFERENT
        # law, NOT this door's (sims §4 refinement; the memory twin as03b
        # PAIR exit=1 is the identity receipt: the memory both compilers
        # agree on is bit-identical). Pinned as a NAMED divergence: a
        # future change here must re-measure, never silently re-tune.
        assert brc == 0, ("%s: blcc must LAND at W-AK, still a wall "
                          "rc=%d:\n%s" % (name, brc, b[:300]))
        assert b == 1, ("%s: the NAMED divergence moved — gcc %d, blcc %r "
                        "(memory-law 1 was the sims §4 measurement; the "
                        "forwarding law has NO card yet)"
                        % (name, g, b))
        return
    assert brc == 0, ("%s: rc=%d — the fix died back into a wall (the "
                      "W-AI loudify for UN-MODELLED shapes must not "
                      "re-extend into the modelled class):\n%s"
                      % (name, brc, b[:300]))
    assert b == g, ("%s: SILENT — blcc %d vs gcc %d (sims §4.2 clobber "
                    "class: a raw-unit store would show here)"
                    % (name, b, g))


def test_wak_gate_sentence_still_named():
    # The W-AK refusal sentence for shapes the layout door cannot answer
    # keeps the W-AI sentence CORE (retired-claim hygiene: the dead "has
    # its OWN card" tail — the card LANDED — replaced by the honest
    # no-layout wording at the ONE site). The literal rides the source
    # SPLIT across the house 79-col wrap, so the pin matches the shipped
    # SOURCE chunks — contiguously — and the dead tail vanishes repo-wide.
    path = os.path.join(REPO, "blcc", "asmgen.py")
    with open(path) as fh:
        text = fh.read()
    for chunk in ("read-write '+' asm operand on a packed ",
                  "bitfield member is not modelled (W-AK: no ",
                  "layout answer"):
        assert chunk in text, ("the loudify moved off its W-AK sentence, "
                               "chunk missing: %r" % chunk)
    assert "has its OWN card" not in text and \
           "has its OWN card" not in open(
               os.path.join(REPO, "blcc", "expr_codegen.py")).read(), (
        "the retired claim 'the fix rides its own card' survived the "
        "card that ships the fix")
