# LINES reason: one law (M4 W-AG COMMIT-0, MC 12404.2.147 / job 12835):
# the W-AF gate F-2-SCOPE tag law — the "(§8 — gcc rc1 twin)" oracle tag
# rides ONLY the MEASURED twin class; every leg pins one face of that law.
r"""M4 W-AG COMMIT-0 — THE TWIN TAG RIDES THE MEASURED CLASS ONLY
(W-AF gate F-2-SCOPE, P1 — .tmp/evidence/m4-waf-gate-verdict.md).

THE REFUTED CLAIM (quote of the gate verdict): "the arm's own comment —
'reaching THIS arm means the name is declared AND typed AND non-callable
(scalar/struct/union/array)' — is FALSE for the shapes that actually reach
it", and "kernel_events_core.c.i:82407:918 still answers, at base AND
ship, with the twin tag" while the WHOLE clean stream compiles at gcc
rc0/0-diag/109,992 B. EIGHT of the gate's 17 invented gcc-rc0 shapes wore
the tag at ship (s2, s6, s7, s8, s12, s13, s14, s15 — all lifted VERBATIM
below from .tmp/m4-waf-gate/shapes/). The TAG LAW (AMENDMENT-49): an
oracle tag may only be worn by an arm whose CLASS was MEASURED against
gcc. The measured rc1-twin class is the CONCRETE non-callable one —
scalar/struct/union/array (`long x; x(1);`, `struct{int n;} w; w();`).
A typeof-declared FUNCTION POINTER is not that class: its refusal may
stay LOUD but rides UNtagged — untagged-loud is a legal posture;
false-twin-tag is the defect.

TEETH (wave gate): smuggling the twin tag back onto ANY function-pointer
shape turns leg 1 RED (a posture catcher, not a string census — the W-AF
gate named the text-census limit: "the catcher pins STRINGS, not
postures"); stripping it off a measured twin turns leg 2 RED.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

from test_core_m4w1 import STREAMS               # noqa: E402  (SHIPPED)
from test_core_m4w25b import _clean_i            # noqa: E402  (SHIPPED)

REC_GCC = ["gcc", "-std=gnu89", "-Os", "-mno-sse", "-mno-sse2",
           "-mno-80387", "-fno-stack-protector", "-fno-pic"]

_TAG = "gcc rc1 twin"

# ---- the eight gate-invented LEGAL (gcc rc0) shapes that wore the tag ---
# VERBATIM from .tmp/m4-waf-gate/shapes/ (card 12832, gate DoD-3 battery).
SHAPES = {
    "s2_typeof_ptr_call": (
        "int f(int x){return x;}\n"
        "typeof(f) *__p = &f;\n"
        "int g(void){ return __p(7); }\n"),
    "s6_typeof_member_call": (
        "int f(int x){return x;}\n"
        "struct holder { typeof(&f) fp; } v = { &f };\n"
        "int g(void){ return v.fp(7); }\n"),
    "s7_typeof_ptr_array": (
        "int f(int x){return x;}\n"
        "typeof(f) *tbl[2] = { &f, &f };\n"
        "int g(void){ return tbl[1](7); }\n"),
    "s8_typeof_assign_call": (
        "int f(int x){return x;}\n"
        "int g(void){ typeof(f) *__p; __p = &f; return __p(7); }\n"),
    "s12_typeof_member_ptr": (
        "int f(int x){return x;}\n"
        "struct s { typeof(f) *fp; } v = { &f };\n"
        "int g(void){ return v.fp(7); }\n"),
    "s13_extern_target": (
        "extern int ext(int);\n"
        "typeof(ext) *__p = &ext;\n"
        "int g(void){ return __p(7); }\n"),
    "s14_ptr_to_ptr_via_local": (
        "int f(int x){return x;}\n"
        "typeof(f) *__p = &f;\n"
        "int g(void){ typeof(f) **pp = &__p; return (*pp)(7); }\n"),
    "s15_corpus_readonce_deref_call": (
        "typedef void (*perf_overflow_handler_t)(int *, int *, int *);\n"
        "struct perf_event { perf_overflow_handler_t overflow_handler; };\n"
        "int fire_g(struct perf_event *event, void *data, int *regs) {\n"
        " (void)({ do { if (!(sizeof(event->overflow_handler) == sizeof"
        "(long))) { } } while (0); (*(const volatile typeof( _Generic("
        "(event->overflow_handler), default: (event->overflow_handler)))"
        " *)&(event->overflow_handler)); })(0, data, regs);\n"
        " return 0;\n}\n"),
}
# (s15 is the corpus READ_ONCE callee CLASS — the kernel typedefs and the
# _Generic arm list need a full kernel prelude to compile standalone, so
# the shape is lifted with the same Deref(Cast(typeof(_Generic…))) call
# spine and a scalar _Generic arm; the corpus row itself is measured by
# the kernel-tier leg below, VERBATIM.)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          capture_output=True, text=True,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _write(tmp_path, tag, src):
    p = tmp_path / (tag + ".c")
    p.write_text(src)
    return p


# ---- leg 1: a legal (gcc rc0) shape NEVER wears the tag ------------------

@pytest.mark.parametrize("name", sorted(SHAPES))
def test_f2sc_legal_shape_never_wears_the_twin_tag(name, tmp_path):
    src = SHAPES[name]
    gp = _write(tmp_path, name + "g", src)
    gr = subprocess.run(REC_GCC + ["-c", str(gp),
                                   "-o", str(tmp_path / (name + "g.o"))],
                        capture_output=True, text=True)
    assert gr.returncode == 0, \
        "battery precondition: %s must be a gcc-LEGAL (rc0) shape, the " \
        "gate measured rc0 for all eight:\n%s" % (name, gr.stderr)
    bp = _write(tmp_path, name + "b", src)
    br = blcc(["-c", str(bp), "-o", str(tmp_path / (name + "b.o"))])
    assert _TAG not in br.stderr, \
        ("%s is gcc rc0 (LEGAL C) yet blcc's refusal wore the oracle tag "
         "again — F-2-SCOPE P1 (gate 12832): %s" % (name, br.stderr))
    # The refusal itself may stay LOUD (over-loud until the dispatch law
    # ships) or move to ACCEPT (the {512B} TYPE law of THIS wave types the
    # typeof-spelled pointer) — the TAG BAN is the permanent law here.


# ---- leg 2: the measured class KEEPS the tag (no over-retraction) --------

MEASURED_TWINS = {
    # the class W-AF measured at gcc 11.4 rc1 (test_core_m4waf0 pins the
    # scalar + struct faces; these are the remaining faces of the SAME
    # class — array, union, enum-as-int):
    "twin_array": ("int main(void){ long a[2]; return a(1); }\n"),
    "twin_union": ("union u{int n;};\nint main(void){ union u w; "
                   "return w(1); }\n"),
    "twin_enum": ("enum e{A};\nint main(void){ enum e v; return v(1); }\n"),
}


@pytest.mark.parametrize("name", sorted(MEASURED_TWINS))
def test_f2sc_measured_twin_keeps_the_tag(name, tmp_path):
    src = MEASURED_TWINS[name]
    gp = _write(tmp_path, name + "g", src)
    gr = subprocess.run(REC_GCC + ["-c", str(gp),
                                   "-o", str(tmp_path / (name + "g.o"))],
                        capture_output=True, text=True)
    assert gr.returncode == 1, \
        "the twin must STAND for %s — gcc rc1 measured, gate 12832: %s" \
        % (name, gr.stderr)
    bp = _write(tmp_path, name + "b", src)
    br = blcc(["-c", str(bp), "-o", str(tmp_path / (name + "b.o"))])
    assert br.returncode == 2 and _TAG in br.stderr, \
        ("the measured rc1-twin class lost its tag — over-retraction: %s"
         % br.stderr)


# ---- leg 3 (kernel tier): the corpus row comes OFF the tag, wall STAYS --

@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_f2sc_corpus_row_untagged_wall_stands(tmp_path):
    # The DECISIVE row of the gate verdict: kernel_events_core.c.i
    # :82407:918 answered WITH the twin tag at base AND ship while the
    # whole clean stream compiles at gcc rc0/0-diag/109,992 B. After
    # COMMIT-0: the stream still REFUSES (the callee is a
    # `typeof(_Generic(…))` — the EXPR form stays lazy, sims P3c keeps
    # the wall) but the first wall wears NO oracle tag.
    stream = os.path.join(STREAMS, "kernel_events_core.c.i")
    clean = _clean_i(stream, tmp_path, "wag0kc")
    gr = subprocess.run(REC_GCC + ["-c", str(clean),
                                   "-o", str(tmp_path / "wag0k.o")],
                        capture_output=True, text=True)
    assert gr.returncode == 0, \
        "the corpus precondition (gate GATE-KEC-GCC-RC=0) broke: %s" \
        % gr.stderr[-400:]
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "wag0k.b.o")])
    assert r.returncode != 0, \
        "kernel_events_core LANDED — the _Generic-operand §8 wall is not " \
        "this card's law (sims P3c named it UNCLAIMED): do not ship it"
    first = next(ln for ln in (r.stdout + r.stderr).splitlines()
                 if ln.strip())
    assert _TAG not in first, \
        "the corpus §8 row still wears the twin tag (F-2-SCOPE): " + first
