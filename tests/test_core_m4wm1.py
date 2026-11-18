# LINES reason: one wave of legs (M4 W-M COMMIT-1 — the 'i'/'g'
# constraint FOLD FAMILY, card 12404.2.83) — fold-vs-lea-vs-reg is ONE
# measured size table; splitting the table across files would separate
# a shape from its gcc-measured neighbour.
r"""M4 W-M COMMIT-1 — the 'i' FOLD FAMILY, gcc-measured (kernel recipe).

THE LAW (gcc 11.4 -Os kernel recipe, table .tmp/m4-wm/out/
measure-ifold.txt + probes/if_*.s, ALL at MY hands): every
COMPILE-TIME constant shape folds to `$imm` — including the static
symbol forms `(long)&gs[8] + 3 → $gs+11`, `(long)&gx[9] → $gx+72`
(array ELEMENT addresses fold at `sym + k*esz`), and the SAME-symbol
difference `(long)&garr[8] - (long)&garr[0] → $64`. A difference
ACROSS two symbols is gcc's OWN LOUD (`impossible constraint in
'asm'`, rc1) — blcc's existing wall is the honest twin, pinned.
The non-constant operand (`'i'` on a parameter) stays LOUD: the
kernel's `alternative_msr_write` class (83+ first-blockers in the
RPAF census) is gcc's INLINE+discard fold — blcc has no inliner,
the LOUD is named, NOT silently wrong (the verdict row).
THE MECHANISM: the ONE closure in `asmsub._asm_sym` grows its arms —
array-element addresses (Index on a global, `k*esz` at the element's
own _size) and the same-symbol difference — no parallel folder.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]


def _gcc_imm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    x = tmp_path / (tag + ".gcc.s")
    r = gcc(REC + ["-S", str(s), "-o", str(x)])
    if r.returncode:
        return None, r.stderr
    a = x.read_text()
    body = a.split("\nf:", 1)[1] if "\nf:" in a else a
    m = re.search(r"movl?\s+(-?\$\S+), %eax", body)
    return (m.group(1) if m else None), None


def _blcc(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".o")
    r = blcc(["-c", str(s), "-o", str(o)])
    return r


def _blcc_imm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc([str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must fold:\n" + r.stderr
    a = (tmp_path / (str(o) + ".s")).read_text()
    body = a.split("\nf:", 1)[1] if "\nf:" in a else a
    m = re.search(r"movl?\s+(-?\$\S+), %eax", body)
    return m.group(1) if m else None


BODY = 'long f(void){{ long r; asm("movl %1, %%eax" : "=a"(r) : "i"({})); return r; }}\n'

# (tag, expr, expected $-form at gcc AND blcc — the fold law agrees to
# the byte on every constant shape)
FOLDS = [
    ("aoff", "(long)&gs[8] + 3", "$gs+11"),
    ("saddr", "(long)&gs[9]", "$gs+9"),
    ("cint", "c", "$5"),
    ("cexpr", "(1<<4) + 3*2 - 1", "$21"),
    ("szof", "sizeof(struct T)", "$16"),
    ("enum", "EB - EA", "$33"),
    ("neg", "-17", "$-17"),
    ("cast", "(long)123", "$123"),
    ("chlit", "'A'", "$65"),
    ("bnot", "~(1<<3)", "$-9"),
    ("hex", "0x7fffffff", "$2147483647"),
    ("dshift", "1024 / 4 + 2048 >> 2", "$576"),
    ("ssub", "(long)&gs[8] - (long)&gs[0]", "$8"),
    ("faddr", "(long)f2", "$f2"),
]
PRE = ("char gs[16]; const int c = 5; struct T { long a, b; };\n"
       "enum E { EA = 7, EB = 40 };\nlong f2(void); char gs3;\n"
       "int main(void){ return 0; }\n")


import pytest


@pytest.mark.parametrize("tag,expr,want", FOLDS)
def test_wm1_i_fold_table(tmp_path, tag, expr, want):
    src = PRE + BODY.format(expr) + "long f2(void){ return 2; }\n"
    gi, gerr = _gcc_imm(tmp_path, "wm1" + tag, src)
    assert gi == want, "oracle law moved: {}\n{}".format(gi, gerr)
    bi = _blcc_imm(tmp_path, "wm1" + tag, src)
    assert bi == want, "fold: blcc {} vs gcc {} (want {})".format(
        bi, gi, want)


def test_wm1_sym_gap_stays_loud(tmp_path):
    # gcc's OWN LOUD (measured rc1 "impossible constraint"): the
    # difference ACROSS symbols is not foldable — blcc's wall is the
    # honest twin, pinned so a future folder cannot silently invent
    # a link-time difference.
    src = "char g1[8]; char g2[8];\n" + BODY.format(
        "(long)&g1[4] - (long)&g2[0]")
    s = tmp_path / "wm1gap.c"
    s.write_text(src)
    r = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert r.returncode != 0 and "impossible constraint" in r.stderr
    b = _blcc(tmp_path, "wm1gap", src)
    assert b.returncode != 0 and "not a compile-time constant" in b.stderr


def test_wm1_param_operand_loud_twin(tmp_path):
    # The RPAF census class (83+ first-blockers): `"i" (feature)` on a
    # PARAMETER. gcc -Os answers rc0 ONLY through the inliner folding
    # the constant argument per call site; blcc has no inliner and the
    # honest answer is LOUD (never silently wrong). Named LOUD-DIV
    # twin — the verdict's census-correction row.
    src = ('long f(long feature){ long r; asm("movl %1, %%eax"\n'
           '   : "=a"(r) : "i"(feature)); return r; }\n')
    b = _blcc(tmp_path, "wm1feat", src)
    assert b.returncode != 0 and "not a compile-time constant" in b.stderr


def test_wm1_g_class_prefers_imm(tmp_path):
    # 'g' general: a constant rides $imm (the shipped arm, pinned from
    # the gcc side: gcc emits $ for constants under 'g' too).
    src = PRE + 'long f(void){{ long r; asm("movl %1, %%eax" : "=a"(r)' \
        ' : "g"((1<<5) + 1)); return r; }}\n'
    gi, gerr = _gcc_imm(tmp_path, "wm1g", src)
    assert gi == "$33", "gcc g-class: {} {}".format(gi, gerr)
    bi = _blcc_imm(tmp_path, "wm1g", src)
    assert bi == "$33", "g-class imm: {}".format(bi)


def test_wm1_reg_class_stays_reg(tmp_path):
    # the "lea-vs-reg" leg of the table: an 'r' operand of a NON-
    # constant is a register at gcc AND blcc — no fold, no lea.
    # the asm references ONLY the register operand — gcc does not
    # materialise unreferenced operands, and blcc substitutes the
    # referenced %n only (the same law); $42-fold is pinned in the
    # table leg.
    src = ('long f(int x){ long r; asm("movl %1, %%eax"\n'
           '   : "=a"(r) : "r"(x)); return r; }\n'
           'int main(void){ return 0; }\n')
    s = tmp_path / "wm1r.c"
    s.write_text(src)
    x = tmp_path / "wm1r.gcc.s"
    g = gcc(REC + ["-S", str(s), "-o", str(x)])
    assert g.returncode == 0
    ga = x.read_text()
    b = blcc([str(s), "--emit-asm", "-o", str(tmp_path / "wm1r.bin")])
    assert b.returncode == 0, b.stderr
    ba = (tmp_path / "wm1r.bin.s").read_text()
    # gcc's answer: the register name. blcc's answer: its shipped
    # L3 memory-fold (the slot rides the movl directly — value-equal
    # spelling, M3 law). BOTH must NEVER show an immediate for a
    # non-constant 'r' operand — that is this leg's invariant.
    assert "movl %edi, %eax" in ga or "movl %edi,%eax" in ga, ga
    fb = ba.split("f:", 1)[1].split("ret")[0]
    assert not re.search(r"movl? \$\d+, %e(ax|cx|di)", fb), \
        "a non-constant 'r' operand materialised as an imm:\n" + ba


def test_wm1_fold_run_pair(tmp_path):
    # the fold is VALUE-visible: the immediate rides the run-pair.
    src = ('long g1[10];\nlong f(void){ long r;\n'
           ' asm("movl %1, %%eax" : "=a"(r) : "i"((long)&g1[3] + 2));\n'
           ' return (r ^ ((long)&g1[3] + 2)) ? 1 : 7; }\n'
           'int main(void){ return (int)f(); }\n')
    s = tmp_path / "wm1run.c"
    s.write_text(src)
    gx = tmp_path / "wm1run.gcc"
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)])
    assert g.returncode == 0, g.stderr
    bx = tmp_path / "wm1run.blcc"
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    assert gv.returncode == bv.returncode == 7, \
        "run-pair: gcc {} blcc {}".format(gv.returncode, bv.returncode)
