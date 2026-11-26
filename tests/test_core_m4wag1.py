# M4 W-AG TYPE LAW — the `typeof(TYPE)` wrapper MATERIALIZES AT THE PARSER
# PRODUCTION (MC 12404.2.147 / job 12835, card 12835). One concern: the
# exit-encoded postures the one-home production hunk moves, and the blast
# controls it must leave UNTOUCHED.
r"""M4 W-AG COMMIT-TYPE — the TYPE-form `typeof(TYPE)` / `__typeof__(TYPE)`
wrapper resolves AT PRODUCTION (`parser._base_type_core`, the TYPE branch).

THE MEASURED PREMISE (sims card 12833 RE-PRICED at my hands; the brief's
"big-value-load gap" was a FALSE PREMISE): the corpus `cannot load a
512-byte value (§4)` / `cannot load a 2048-byte value (§4)` walls are the
UN-MATERIALIZED wrapper at a declaration — `__typeof__(u64 [64])
pmc_prev_left;` keeps a TypeOf node, the DECL never becomes an ARRAY TYPE,
`_decay`/the §4 load law MISS the array-ness, and the ident CONTENT-LOADS
the whole object (512 B / 2048 B) instead of DECAYING to its address. The
SILENT family is the real risk: the same spelling with a <=8-byte object
COMPILES AT rc0 AND SEGFAULTS (sims wgF06/ef14: gcc exit 3 vs blcc SIGSEGV)
— every small per-CPU collapse is a compiled lie. The §4 `_load` law
itself is CORRECT and untouched here; a "big-value copy materializer"
would have made the WRONG load legal — the sims decision row says FIX IT
AS THE TYPE LAW, and this wave ships exactly that.

ONE HOME: the production `return typ`. The EXPR spelling (`typeof(expr)`)
and `__auto_type` stay LAZY — W-H's measured difference table and the W-Z
auto materialization are UNMOVED (rows F08/F10 below pin both faces).

Battery idiom: the process EXIT CODE is the answer (gcc REC-flag twin vs
blcc, `-no-pie`, `answer()` through the shared MAIN harness — the shipped
W-AF/W-W law-battery idiom). A SILENT-WRONG row cannot hide: the leg runs
the blcc object and compares exits.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
TMP = "/dev/shm/m4wag1_%s_%d" % (os.environ.get("M4WAG_TAG", "x"), os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# ---- the family the law ships (PAIR at {512B}; RED at tip: >8B walls
# or the <=8B SEGFAULT class — sims wgF sources VERBATIM) ----------------

ROWS = {
    # the corpus spelling itself (events/core.c:1357 per_cpu store):
    "F01_per_cpu_store_verbatim": (
        "typedef unsigned long u64;\n"
        "static __attribute__((section(\".data\" \"\"))) "
        "__typeof__(u64 [64]) pmc_prev_left;\n"
        "int answer(void)\n"
        "{\n"
        "\tint idx = 3; u64 left = 42;\n"
        "\t(*({ (void)(0); ({ do { const void *__vpp_verify = (typeof("
        "(&(pmc_prev_left[idx])) + 0))((void *)0); (void)__vpp_verify; } "
        "while (0); (typeof(*(&(pmc_prev_left[idx]))) *)(&(pmc_prev_left"
        "[idx])); }); })) = left;\n"
        "\treturn (int)(pmc_prev_left[3] == 42 && pmc_prev_left[2] == 0 "
        "? 3 :\n\t\t     pmc_prev_left[3] == 0 ? 4 : 5);\n}\n", 3),
    "F02_per_cpu_read_verbatim": (
        "typedef unsigned long u64;\n"
        "static __typeof__(u64 [64]) pmc_prev_left = { [5] = 77 };\n"
        "int answer(void)\n{\n\tint idx = 5;\n"
        "\tu64 prev_left = (*({ (void)(0); ({ do { const void "
        "*__vpp_verify = (typeof((&(pmc_prev_left[idx])) + 0))((void *)0);"
        " (void)__vpp_verify; } while (0); (typeof(*(&(pmc_prev_left[idx]"
        "))) *)(&(pmc_prev_left[idx])); }); }));\n"
        "\treturn (int)(prev_left == 77 ? 3 : prev_left == 0 ? 4 : 5);\n"
        "}\n", 3),
    "F03_plain_sub_read_512": (
        "typedef unsigned long u64;\n"
        "static __typeof__(u64 [64]) pv3 = { [7] = 9 };\n"
        "int answer(void) { return (int)(pv3[7] == 9 && pv3[6] == 0 ? 3 :"
        " pv3[7] ? 4 : 5); }\n", 3),
    # THE SILENT FAMILY: <=8-byte same spelling — at tip this COMPILES and
    # SEGFAULTS (exit 139/-11 vs gcc 3). sims wgF06 VERBATIM.
    "F06_silent8_sub": (
        "typedef int i32;\n"
        "static __typeof__(i32 [2]) pv6 = { 7, 8 };\n"
        "int answer(void) { int d = pv6[1] - 8; return (d == 0 ? 3 : (d "
        "> 0 ? 4 : 2)); }\n", 3),
    "F09_2048_shape": (
        "typedef unsigned long u64;\n"
        "static __typeof__(u64 [256]) pv9;\n"
        "int answer(void) { pv9[200] = 5; return (int)(pv9[200] == 5 && "
        "pv9[199] == 0 ? 3 : 4); }\n", 3),
    "F13_typeof_param_pass": (
        "typedef int i32;\n"
        "static __typeof__(i32 [4]) pv13 = { 1, 2, 3, 4 };\n"
        "int answer(void) { int s = pv13[0] + pv13[3]; return (s == 5 ? 3"
        " : s == 0 ? 4 : 5); }\n", 3),
    # ---- BLAST CONTROLS: every one PAIRS at tip and must PAIR unchanged
    # at ship (sims: F04/F05/F07/F10/F11/F12 unmoved, zero collateral) ---
    "F04_typedef_control": (
        "typedef unsigned long u64;\ntypedef u64 arr64[64];\n"
        "static arr64 pv4 = { [7] = 9 };\n"
        "int answer(void) { return (int)(pv4[7] == 9 && pv4[6] == 0 ? 3 :"
        " pv4[7] ? 4 : 5); }\n", 3),
    "F05_plain_decl_control": (
        "typedef unsigned long u64;\nstatic u64 pv5[64] = { [7] = 9 };\n"
        "int answer(void) { return (int)(pv5[7] == 9 && pv5[6] == 0 ? 3 :"
        " pv5[7] ? 4 : 5); }\n", 3),
    "F07_typeof_scalar_control": (
        "typedef unsigned long u64;\nstatic __typeof__(u64) pv7 = 11;\n"
        "int answer(void) { return (int)(pv7 == 11 ? 3 : 4); }\n", 3),
    "F10_typeof_expr_decl": (
        "typedef unsigned long u64;\nstatic u64 init10 = 3;\n"
        "static __typeof__(init10) v10;\n"
        "int answer(void) { v10 = 4; return (int)(v10 == 4 && init10 == 3"
        " ? 3 : 4); }\n", 3),
    "F11_bigstruct_byvalue": (
        "struct big { char b[512]; };\n"
        "int answer(void) { struct big x; int i; for (i = 0; i < 512; i++"
        ") x.b[i] = (char)i;\n\treturn (int)(x.b[255] == (char)255 ? 3 : "
        "4); }\n", 3),
    "F12_memcpy512_shape": (
        "typedef unsigned long u64;\n"
        "static u64 src12[64]; static u64 dst12[64];\n"
        "int answer(void)\n{\n\tint i; unsigned char *s = (unsigned char "
        "*)src12, *d = (unsigned char *)dst12;\n"
        "\tsrc12[63] = 0x1122334455667788;\n"
        "\tfor (i = 0; i < 512; i++) d[i] = s[i];\n"
        "\treturn (int)(dst12[63] == 0x1122334455667788 ? 3 : 4);\n}\n",
        3),
    # ---- interactions the brief demands: wrapper × array-of / × const ---
    "I01_wrapper_of_scalar_ARRAY_of": (
        "typedef unsigned long u64;\n"
        "__typeof__(u64) arr1[4];\n"
        "int answer(void){ arr1[3] = 7; return (int)(arr1[3] == 7 && "
        "arr1[0] == 0 ? 3 : 4); }\n", 3),
    "I02_nested_wrapper_array": (
        "typedef int i32;\n"
        "static __typeof__(__typeof__(i32 [4])) nb2 = { 1, 2, 3, 4 };\n"
        "int answer(void){ return (int)(nb2[1] + nb2[2] == 5 ? 3 : 4); }\n"
        , 3),
}


def _build(src, tag, kind):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe]
    else:
        o = os.path.join(TMP, tag + ".blcc.o")
        exe = os.path.join(TMP, tag + ".blcc")
        b = subprocess.run([os.environ.get("PYTHON", "python3"), "-m",
                            "blcc", "-c", c, "-o", o], capture_output=True,
                           text=True, cwd=REPO,
                           env=dict(os.environ, PYTHONPATH=REPO))
        if b.returncode != 0:
            return b, None
        cmd = ["gcc", "-no-pie", "-o", exe, o]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r, exe


@pytest.mark.parametrize("name", sorted(ROWS))
def test_typelaw_battery_exit_is_the_answer(name):
    src, expect = ROWS[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "%s: gcc answered %d, expected %d" % (
        name, gx, expect)
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, (
        "%s: blcc refused rc=%d — the TYPE-form wall the {512B} law ships "
        "at this card:\n%s" % (name, rb.returncode,
                               (rb.stdout + rb.stderr)[:300]))
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert bx == gx, (
        "%s: SILENT/VALUE divergence blcc %d vs gcc %d — the <=8-byte "
        "same-spelling crash class must PAIR at ship (no silent accept "
        "without a gcc-measured row)" % (name, bx, gx))


# ---- wrapper × const: the TYPE form carries its qualifier through the
# materialization (gcc: `__typeof__(const int) x; x = 6;` is read-only,
# rc1). The EXPR-form over-lax face (wgF08) is a SEPARATE named law —
# sims card 12833 named it for its own future card and it stays EXACTLY
# as measured: pinned here, not smoothed.

def test_typelaw_wrapper_of_const_type_refuses(tmp_path):
    src = ("static const int c = 4;\n"
           "__typeof__(const int) x = 5;\n"
           "int answer(void){ x = 6; return (int)(x == 6 && c == 4 ? 3 : "
           "4); }\n")
    p = tmp_path / "wagconst.c"
    p.write_text(src + MAIN)
    gr = subprocess.run(["gcc", "-no-pie"] + GCC_REC +
                        [str(p), "-o", str(tmp_path / "gc")],
                        capture_output=True, text=True)
    assert gr.returncode == 1, \
        "gcc rc1 precondition (read-only through the wrapper): " + gr.stderr
    br = subprocess.run([sys.executable, "-m", "blcc", "-c", str(p),
                         "-o", str(tmp_path / "bo")],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO))
    assert br.returncode == 2, (
        "blcc %s the const carried by the MATERIALIZED TYPE form — gcc "
        "refuses rc1 (measured above): silent write past const is the "
        "FALSE-ACCEPT side\n%s" % ("accepted" if br.returncode == 0
                                   else "answered rc%d" % br.returncode,
                                   br.stderr[:300]))


def test_typelaw_expr_form_overlax_stays_pinned(tmp_path):
    # sims wgF08 OVER-LAX, kept VISIBLE (its own row, own law, own future
    # card — AM31): the const carried by the EXPR form is NOT applied by
    # tip and this commit does NOT move it (the {512B} hunk touches the
    # TYPE production ONLY). If this leg ever flips, the EXPR-form law
    # moved — that move has its own card, not this one.
    src = ("typedef int i32;\nstatic const i32 c8 = 4;\n"
           "static __typeof__(c8) v8 = 5;\n"
           "int answer(void)\n{\n\tv8 = 6;\n\treturn (int)(v8 == 6 && "
           "c8 == 4 ? 3 : 4);\n}\n")
    p = tmp_path / "wagexpr.c"
    p.write_text(src + MAIN)
    gr = subprocess.run(["gcc"] + GCC_REC +
                        ["-c", str(p), "-o", str(tmp_path / "ge")],
                        capture_output=True, text=True)
    assert gr.returncode == 1, "wgF08 gcc rc1 (read-only) precondition"
    br = subprocess.run([sys.executable, "-m", "blcc", "-c", str(p),
                         "-o", str(tmp_path / "be")],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO))
    assert br.returncode == 0, (
        "the NAMED over-lax EXPR-form posture CHANGED (rc=%d) — that law "
        "has its own future card; do not move it silently here:\n%s"
        % (br.returncode, br.stderr[:300]))


# ---- interaction: wrapper-declared local INSIDE a splice, POST-RENAME --
# (the W-P inline door; wd301 precedent, the m4waf1 SPLICE row extended
# with the wrapper-decl the clone must carry).

SPLICE = """
typedef int i32;
static inline int pick(int q)
{
\t__typeof__(i32 [4]) loc = { 0, 0, 0, 0 };
\t__asm__ volatile("" : "+r"(q));
\tloc[2] = q * 2;
\t__asm__ volatile("" : "+r"(loc[2]));
\treturn loc[2] + q;
}
int answer(void){ return pick(1) + pick(2) == 9 ? 3 : 4; }
"""


def _asm_of(src, tag):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    s = os.path.join(TMP, tag + ".s")
    r = subprocess.run([sys.executable, "-m", "blcc", "--emit-asm", c,
                        "-o", s], capture_output=True, text=True, cwd=REPO,
                       env=dict(os.environ, PYTHONPATH=REPO))
    assert r.returncode == 0, r.stderr[:300]
    return open(s + ".s").read()


def test_typelaw_splice_wrapper_postrename():
    rg, gexe = _build(SPLICE, "wagspg", "gcc")
    assert rg.returncode == 0, rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    assert gx == 3, "gcc answered %d, expected 3" % gx
    rb, bexe = _build(SPLICE, "wagspb", "blcc")
    assert rb.returncode == 0, rb.stderr[:300]
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert bx == gx, "clone divergence blcc %d vs gcc %d" % (bx, gx)
    asm = _asm_of(SPLICE, "wagsp pin")
    assert "\npick:" not in asm and not asm.startswith("pick:"), \
        "the splice fell back to the CALL law: a `pick:` leaf survived"


def test_typelaw_expr_form_array_face_stays_refused(tmp_path):
    # THE ONE-HOME WITNESS (measured at tip, at the sims stub AND at ship
    # bytes — IDENTICAL everywhere): the EXPR spelling over an ARRAY
    # operand stays LAZY — `__typeof__(a10) v` is gcc rc0 (exit 3) and
    # blcc refuses `cannot load a 32-byte value (§4)`: the OVER-LOUD face
    # of the same family as the corpus 512/2048 walls, NAMED UNCLAIMED by
    # the sims (P3c — the kernel_events_core.c.i §8 wall rides it). This
    # card ships the TYPE home ONLY; if a second materialization home is
    # ever smuggled in (the EXPR spelling resolving at production too),
    # this row flips to an accept and goes RED — the one-home plant
    # witness the wave gate runs.
    src = ("typedef unsigned long u64;\n"
           "static u64 a10x[4];\n"
           "__typeof__(a10x) v10a = { 1, 2, 3, 4 };\n"
           "int answer(void){ return (int)(v10a[2] == 3 && v10a[0] == 1 "
           "? 3 : 4); }\n")
    p = tmp_path / "wagxarr.c"
    p.write_text(src + MAIN)
    gr = subprocess.run(["gcc"] + GCC_REC + ["-c", str(p),
                                             "-o", str(tmp_path / "ge")],
                        capture_output=True, text=True)
    assert gr.returncode == 0, "gcc rc0 precondition: " + gr.stderr
    br = subprocess.run([sys.executable, "-m", "blcc", "-c", str(p),
                         "-o", str(tmp_path / "be")],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO))
    assert br.returncode == 2, (
        "the EXPR-form array face MOVED (rc=%d) — that is a SECOND "
        "materialization home; the TYPE law is ONE home and P3c named "
        "this face UNCLAIMED:\n%s" % (br.returncode, br.stderr[:300]))
    assert "cannot load a 32-byte value" in br.stderr, \
        "the refusal moved off its sentence (collateral): " + br.stderr[:300]


# ---- kernel tier: the corpus pair LANDS, the W-F walls do NOT move ------

from test_core_m4w1 import STREAMS               # noqa: E402  (SHIPPED)
from test_core_m4w25b import _clean_i            # noqa: E402  (SHIPPED)


def _blcc_stream(tmp_path, stream, tag):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, tag)
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / (tag + ".o"))],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO))
    return r, tmp_path / (tag + ".o")


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", ["arch_x86_events_core.c.i",
                                    "arch_x86_kernel_irq.c.i"])
def test_typelaw_corpus_pair_lands(stream, tmp_path):
    r, obj = _blcc_stream(tmp_path, stream, "wagland")
    assert r.returncode == 0, \
        "the {512B} pair must LAND at ship — first wall here:\n" + \
        next((ln for ln in (r.stdout + r.stderr).splitlines()
              if ln.strip()), "(no output)")
    assert obj.exists() and obj.stat().st_size > 0, "empty object"


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_typelaw_wf_walls_landed_at_wah(tmp_path):
    # RENAMED + TEETH-INVERTED at M4 W-AH (MC 12404.2.150), NEVER dropped:
    # this card's {512B} TYPE law left the three data-side W-F walls on
    # their sentences (that was TRUE at W-AG ship, the sims P3c receipt);
    # at W-AH the producer WINDOW law lands all three rc0 — the leg now
    # pins the LANDS. A stream back on a wall is the collateral catcher.
    for s in ("arch_x86_kernel_cpu_common.c.i", "arch_x86_kernel_head64"
              ".c.i", "arch_x86_kernel_idt.c.i"):
        r, _ = _blcc_stream(tmp_path, s, "wagctl")
        assert r.returncode == 0, \
            "%s moved BACK onto a wall (collateral!):\n%s" % (
                s, next((ln for ln in (r.stdout + r.stderr).splitlines()
                         if ln.strip()), "(no output)"))
