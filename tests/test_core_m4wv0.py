# LINES reason: one commit (M4 W-V COMMIT-0, card 12747): the
# never-completed-extern-array sizeof law ships with its two doors, its
# completing-definition half and its volume pin — one law, one file.
r"""M4 W-V COMMIT-0 (MC 12747) — 'sizeof' on an extern INCOMPLETE array
whose size NO definition in this TU completes is LOUD, at BOTH doors.

THE gcc 11.4 -Os REC LAW (sims law rows e01/e13; own hands at the wave
REC, .tmp/m4-wv/shapes): gcc refuses LOUD
  "invalid application of 'sizeof' to incomplete type 'char[]'"
while tip dc6d94a answered rc0 with `mov $0x8` (disassembly verified) —
silent SIZE LAUNDERING: a program that reads `sizeof a` of a symbol whose
extent only the LINKER knows cannot be answered by a pointer size. The
corpus volume of the shape is 0 (pinned below), so this is a risk-seam
closure, not an accept move: it lands BEFORE the extern-reference lever
ships (loud-before-arming, W-V doctrine).

The law's OTHER half stays quiet: a COMPLETING definition in the TU
answers the completed size (measured: `extern int t[]; n = sizeof t;
int t[5];` folds 20; the e18 fn-scope spelling answers 16 via the later
`char y[16]`), and a PARAMETER's array type decays — `sizeof(param)`
keeps answering 8 exactly as C requires. The flexible-array-member arm
already LOUDed its own class and is untouched.
"""
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-mmx", "-mno-sse2",
       "-mno-80387", "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"}
NEEDLE = "sizeof' of extern incomplete array"


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/wv0_%s.c" % tag
    open(c, "w").write(src)
    return c


def _loud(tag, src):
    """blcc must refuse LOUD naming the class; returns gcc's rc (1)."""
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 1, "gcc must LOUD the shape: " + g.stderr
    assert "invalid application of" in g.stderr, g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 2, "%s must be LOUD (RED-first: tip answers " \
        "QUIET-8): %s" % (tag, b.stderr)
    assert NEEDLE in b.stderr, "%s: LOUD must name the class: " % tag \
        + b.stderr
    return g.returncode


# ---- RED-first witnesses (QUIET-8 at dc6d94a; LOUD at COMMIT-0) --------

def test_wv0_e01_never_completed_sizeof_loud():
    # sims row e01: the pure class — extern array, never completed.
    _loud("e01", "extern char a[];\n"
                 "unsigned long f(void){ return sizeof a; }\n"
                 "int main(void){ return 7; }\n")


def test_wv0_e13_sibling_function_sizeof_loud():
    # sims row e13: the arithmetic is legal, the sizeof is NOT — gcc
    # stops at the sizeof line and never at the `z + 1`.
    _loud("e13", "extern char z[];\n"
                  "char *f(void){ return z + 1; }\n"
                  "unsigned long g(void){ return sizeof z; }\n")


def test_wv0_fold_door_sizeof_loud():
    # THE corpus spelling: `int n = sizeof z;` in a GLOBAL initializer
    # rides the fold door (types.py `_fold_const`), not codegen. Measured
    # QUIET-8 at tip (the .data word held 8); COMMIT-0 refuses it — at
    # THIS door the shipped §4 fold wall answers (the law LOUDs inside
    # the fold, the initializer path surfaces its own honest sentence
    # naming the construct 'sizeof expression'). rc0 → rc2 is the
    # laundering closing; the sentence differs per door, the REFUSAL
    # does not.
    c = _w("fold", "extern char zz[];\n"
                   "int n = sizeof zz;\n"
                   "int main(void){ return 0; }\n")
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 1, "gcc must LOUD the shape: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 2, "fold door must REFUSE (RED-first: tip " \
        "answers QUIET-8): " + b.stderr
    assert ("sizeof' of extern incomplete array" in b.stderr
            or "must be an integer/char constant or address-of"
            in b.stderr), b.stderr


# ---- the law's quiet half + posture pins (green before AND after) ------

def test_wv0_completed_definition_folds_its_size(tmp_path):
    # e06 shape: the definition completes the object — the fold answers
    # 20 (measured at tip AND here), never a laundered 8. gcc rc1 at
    # the POINT OF USE (a NAMED-DIVERGE: blcc answers the true size;
    # volume 0). Value leg: main returns 3 iff n == 20.
    c = _w("e06", "extern int t[];\nint n = sizeof t;\nint t[5];\n"
                   "int main(void){ return n == 20 ? 3 : n == 8 ? 1 : 2; }\n")
    b = blcc(["-c", c, "-o", "/dev/shm/wv0_e06.o"])
    assert b.returncode == 0, b.stderr
    assert subprocess.run(["gcc", "-no-pie", "/dev/shm/wv0_e06.o", "-o",
                           "/dev/shm/wv0_e06"],
                          capture_output=True).returncode == 0
    assert subprocess.run(["/dev/shm/wv0_e06"],
                          env={"PATH": "/usr/bin:/bin"}).returncode == 3


def test_wv0_param_decay_still_answers_8():
    # The C decay law at the SAME arm: `sizeof(param)` of an array
    # parameter is the POINTER size (8) — the never-completed law must
    # not eat it (fn.locals resolves the name, not the file-scope entry).
    c = _w("par", "unsigned long h(int a[]){ return sizeof a; }\n"
                   "int main(void){ return h(0) == 8 ? 0 : 5; }\n")
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                                        "/dev/shm/wv0_par.g"],
                       capture_output=True, text=True)
    assert g.returncode == 0, g.stderr
    assert subprocess.run(["/dev/shm/wv0_par.g"],
                          env={"PATH": "/usr/bin:/bin"}).returncode == 0
    b = blcc(["-c", c, "-o", "/dev/shm/wv0_par.o"])
    assert b.returncode == 0, b.stderr
    assert subprocess.run(["gcc", "-no-pie", "/dev/shm/wv0_par.o", "-o",
                           "/dev/shm/wv0_par.b"],
                          capture_output=True).returncode == 0
    assert subprocess.run(["/dev/shm/wv0_par.b"],
                          env={"PATH": "/usr/bin:/bin"}).returncode == 0


def test_wv0_pointer_arithmetic_untouched():
    # sims rows e04/e12: `z[3]` and `z + 1` on the incomplete array are
    # gcc-LEGAL — the sizeof law must leave the arithmetic door alone.
    c = _w("e12", "extern char z[];\nchar *f(void){ return z + 1; }\n")
    b = blcc(["-c", c, "-o", "/dev/shm/wv0_e12.o"])
    assert b.returncode == 0, "arith legal both sides: " + b.stderr


# ---- volume pin (own census; the corpus cannot carry the shape) --------

def test_wv0_corpus_volume_zero():
    # Pinned: no stream ever spells `sizeof` on an extern-incomplete
    # array name — the LOUD is risk-seam closure at volume 0, so it
    # moves no accept. The names the corpus declares as `extern char
    # NAME[]` (init/rodata/opd/once family) may not appear under a
    # sizeof; checked TEXT-EXACT on the raw pinned streams.
    if not os.path.isdir(STREAMS):
        import pytest
        pytest.skip("corpus streams absent (worktree posture)")
    names = ["__init_begin", "__init_end", "__start_rodata", "__end_rodata",
             "__start_ro_after_init", "__end_ro_after_init", "__start_opd",
             "__end_opd", "__start_once", "__end_once"]
    pat = re.compile(r"sizeof\s*\(?\s*(" + "|".join(names) + r")\b")
    hits, decl, sha = [], 0, hashlib.sha256()
    for f in sorted(x for x in os.listdir(STREAMS) if x.endswith(".i")):
        with open(os.path.join(STREAMS, f), "r", errors="replace") as fh:
            txt = fh.read()
        sha.update(f.encode())
        sha.update(txt.encode("utf-8", "replace"))
        decl += len(re.findall(r"extern\s+char\s+" + names[0], txt))
        for m in pat.finditer(txt):
            hits.append((f, m.group(0)))
    # n=706 sha 22655bf48c05bd7a — the blessed corpus this law was measured on
    assert sha.hexdigest().startswith("22655bf48c05bd7a"), \
        "corpus drift: " + sha.hexdigest()[:16]
    assert decl > 400, "the idiom's own presence must be measurable"
    assert not hits, "sizeof-on-incomplete corpus volume must be 0: " \
        + str(hits[:3])
