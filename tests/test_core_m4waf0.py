# LINES reason: one law (M4 W-AF COMMIT-0, MC 12404.2.144 / job 12831):
# the W-AE gate F-2 twin-tag retraction — the §8 sentence's oracle tag
# rides ONLY the measured rc1-twin class; every leg here pins one face of
# that single scoping law.
r"""M4 W-AF COMMIT-0 — THE §8 ORACLE-TAG RETRACTION (W-AE gate F-2, P1).

THE REFUTED CLAIM (quote of the verdict, .tmp/evidence/
m4-wae-gate-verdict.md F-2): "The §8 wall sentence in blcc/expr_parser.py
:498/520 and blcc/expr_codegen.py:1006 carries the tag (§8 — gcc rc1
twin). For the shape that is NOW the walk's first RED that tag is FALSE:
static_call(x)() preprocesses to extern typeof(*x86_pmu.disable_all)
__SCT__…; and ({ …; (&__SCT__…); })() — an object of FUNCTION type
called through its address — and gcc 11.4 at the REC program compiles it
rc0." W-AF OWN-HANDS RECEIPT (ship card): whole clean
arch_x86_events_core.c.i under the REC flags (gcc 11.4.0,
-std=gnu89 -Os -mno-sse -mno-sse2 -mno-80387 -fno-stack-protector
-fno-pic) → rc0, a 54,488-byte object, ZERO diagnostics
(.tmp/m4-waf-build/gcc-stream-rc0.txt).

THE SCOPED LAW this file pins (the verdict's fix clause: "scope the
sentence … so a blcc-only refusal can no longer wear an oracle tag;
NOT to ship static_call dispatch as a side-project"):
  1. a target the light mirror CANNOT type (the walk shape: a `({…;
     (&sym);})` group callee) refuses rc2 WITHOUT the twin tag;
  2. the typed non-callable class (`long x; x(1);`, `struct{int n;}
     w; w();` — measured gcc rc1 twins) KEEPS the tag;
  3. the codegen §8 arm carries NO oracle claim at all (a mirror-vs-
     codegen view mismatch is per-shape UNMEASURED against gcc).
The REFUSAL itself stands until the {TF} mirror arms of this same wave
land (rows af04/af05/af06/af26 of the card-12825 battery move at {TF});
legs here are written to stay green BOTH ways, so the retraction
outlives the wall it names. TEETH (wave gate): re-wearing the tag on
the un-typeable arm turns legs 1 and 4 RED.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

from blcc import parser as parser_mod            # noqa: E402  (path probe)
import blcc.expr_codegen as codegen_mod          # noqa: E402
from test_core_m4w1 import STREAMS               # noqa: E402  (SHIPPED)
from test_core_m4w25b import _clean_i            # noqa: E402  (SHIPPED)

REC_GCC = ["gcc", "-std=gnu89", "-Os", "-mno-sse", "-mno-sse2",
           "-mno-80387", "-fno-stack-protector", "-fno-pic"]

# af26 VERBATIM from the card-12825 battery (the corpus posture: the
# trampoline symbol declared `extern typeof(*fp)`, defined ONLY by ASM,
# called through a ({…;(&sym);}) group) — .tmp/m4-waf-sims/law/src/
# af26_trampoline_asm_defined_verbatim.c, copied unchanged.
AF26 = (
    "struct ops { int (*fp)(void); };\n"
    "static struct ops T;\n"
    "extern typeof(*T.fp) tramp;\n"
    'asm(".text\\n\\t.globl tramp\\ntramp:\\n\\tmov $33, %eax\\n\\tret\\n");\n'
    "int answer(void)\n"
    "{\n"
    "\treturn ({ static void *u = (void *)&T; (void)u; (&tramp); })();\n"
    "}\n")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          capture_output=True, text=True,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _blcc_rc_of(src, tmp_path, tag):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    r = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])
    return r


# ---- leg 1: the walk shape refuses, but wears NO oracle tag -------------

def test_f2_walk_shape_never_wears_the_twin_tag(tmp_path):
    gr = subprocess.run(REC_GCC + ["-c", str(_write(tmp_path, "waf0g", AF26)),
                                   "-o", str(tmp_path / "waf0g.gcc.o")],
                        capture_output=True, text=True)
    assert gr.returncode == 0, \
        "F-2's receipt is that gcc compiles the walk shape rc0:\n" + gr.stderr
    br = _blcc_rc_of(AF26, tmp_path, "waf0b")
    assert "gcc rc1 twin" not in br.stderr, \
        "a blcc-only refusal wore the oracle tag again (W-AE gate F-2):\n" \
        + br.stderr
    if br.returncode != 0:      # over-loud until {TF} ships: scoped here
        assert br.returncode == 2 and "§8" in br.stderr, br.stderr
        assert "blcc-only" in br.stderr, \
            "the un-typeable §8 arm must answer the scoped blcc-only " \
            "sentence:\n" + br.stderr
    # (once {TF} lands this leg keeps its teeth the other way: the tag
    # ban above is permanent, the rc2 branch simply stops firing)


def _write(tmp_path, tag, src):
    p = tmp_path / (tag + ".c")
    p.write_text(src)
    return p


# ---- leg 2: the measured twin class KEEPS its tag (no over-retraction) --

def test_f2_typed_noncallable_keeps_the_measured_twin(tmp_path):
    src = "int main(void){ long x = 3; return x(1); }\n"
    s = _write(tmp_path, "waf0t", src)
    gr = subprocess.run(REC_GCC + ["-c", str(s),
                                   "-o", str(tmp_path / "waf0t.gcc.o")],
                        capture_output=True, text=True)
    assert gr.returncode == 1, "gcc rc1 is the measured twin:\n" + gr.stderr
    br = _blcc_rc_of(src, tmp_path, "waf0t")
    assert br.returncode == 2, br.stderr
    assert "gcc rc1 twin" in br.stderr, \
        "the typed non-callable class lost its MEASURED tag — " \
        "over-retraction (gate F-2 names this twin):\n" + br.stderr


def test_f2_struct_object_twin(tmp_path):
    src = ("struct{int notcallable;} w;\n"
           "int main(void){ return w(); }\n")
    s = _write(tmp_path, "waf0s", src)
    gr = subprocess.run(REC_GCC + ["-c", str(s),
                                   "-o", str(tmp_path / "waf0s.gcc.o")],
                        capture_output=True, text=True)
    assert gr.returncode == 1, "t3 twin, gcc rc1 (gate F-2):\n" + gr.stderr
    br = _blcc_rc_of(src, tmp_path, "waf0s")
    assert br.returncode == 2 and "gcc rc1 twin" in br.stderr, \
        "the struct-object twin must keep the measured tag:\n" + br.stderr


# ---- leg 3: the codegen §8 arm carries no oracle claim at all -----------

def test_f2_codegen_home_carries_no_oracle_tag():
    src = open(os.path.join(os.path.dirname(parser_mod.__file__),
                            "expr_codegen.py")).read()
    assert "§8 — blcc-only: parse-mirror and codegen" in src, \
        "the scoped codegen sentence is gone — what replaced it?"
    assert "\"pointer' (§8 — gcc rc1 twin)\"" not in src, \
        "expr_codegen.py wears a §8 oracle claim again (F-2): the " \
        "mirror/codegen mismatch class is UNMEASURED against gcc"


# ---- leg 4 (kernel tier): the stream itself never wears the tag ---------

@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_f2_events_core_wall_wore_no_oracle_tag(tmp_path):
    # THE stream of the refutation: at base bytes its first wall wears
    # the (false) tag; at W-AF ship bytes the §8 sentence moved to the
    # §4 `cannot load a 512-byte value` FUTURE wall — and M4 W-AG
    # (MC 12404.2.147 / job 12835) IS that future card: the {512B} TYPE
    # law lands the stream rc0 (test_core_m4wag1.py pins the LAND with
    # the object-bytes leg). The PERMANENT law this leg keeps: no §8
    # refusal may wear the retracted tag — pinned at the runtime face by
    # tests/test_core_m4wag0.py (untagged corpus refusal).
    clean = _clean_i(os.path.join(STREAMS, "arch_x86_events_core.c.i"),
                     tmp_path, "waf0c")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "waf0c.o")])
    assert r.returncode == 0, \
        ("events/core REFUSED — the W-AG TYPE law (card 12835) that "
         "landed it moved back:\n" + next((ln for ln in
         (r.stdout + r.stderr).splitlines() if ln.strip()), ""))
