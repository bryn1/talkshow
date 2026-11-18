# LINES reason: one wave of legs (M4 W-N COMMIT-0 — the 'i'-FOLD TYPE
# LAW, card 12404.2.85) — the four gate edges F-1..F-4 are ONE root
# (the fold arms read SHAPE, not C TYPE); splitting the table across
# files would separate a shape from its type-law neighbour.
r"""M4 W-N COMMIT-0 — the 'i' FOLD reads C TYPE, not shape (gcc-measured).

THE LAW (gcc 11.4 -std=gnu89 kernel recipe; tables .tmp/m4-wn/out/
measure-wn2.txt + measure-wn3.txt, ALL probes at MY hands this card):
the W-M fold family answered every ADDRESS-SHAPE question by SYNTAX.
gcc answers by TYPE:
  F-1  BARE pointer difference `&gs[4]-&gs[0]` is the ELEMENT count
       ($4 at int, esz 4), NOT the byte span ($16); the (long)-CAST
       form keeps the byte answer ($16) — both spellings pinned.
       The compound `&gs[4]-&gs[0]-1` → $3 (the tip CRASHES: int
       object is not subscriptable — same root).
  F-2  A BARE element rvalue `gs[3]` under "i" is NOT a constant:
       gcc is LOUD (rc1 "probably does not match constraints"); the
       tip folder invented the pass $gs+12 from the shape alone.
       The address spelling `&gs[3]` folds ($gs+12) — the arm is an
       ADDRESS arm, and the address form is part of its law.
  F-3  `&c` of a const int global is the ADDRESS ($c), never the
       VALUE ($5): the value arm must not fire through the '&'.
       The bare `c` keeps the VALUE fold ($5, W-M). Statics ride the
       same law (`sc` → $7, `&sc` → $sc).
  F-4  `&gs[3]+1` (and `1+&gs[3]`, `&gs[3]+1L`) adds ONE ELEMENT
       ($gs+16 at esz 4); the cast forms scale by THEIR OWN pointee:
       `(long)&gs[3]+1 → $gs+13`, `(char*)&gs[3]+1 → $gs+13`,
       `(void*)&g+4 → $g+4` (GNU void* esz 1), `gs+3 → $gs+12`.
  +    A NON-CONST scalar global `gi` under "i" is gcc LOUD — the tip
       answered `$gi` (the address) silently: the same folder-
       invents-a-pass class as F-2, closed by the SAME type gate.
       A TRUNCATING `(int)` cast of an address is gcc LOUD too.
MECHANISM: ONE type check per recursion at the fold ENTRY
(`asmsub._asm_sym` + `_asm_ctype`): the C type decides which arms are
open — address-context (pointer type or the '&' spelling) opens the
Index/symbol arms, integer type opens the VALUE arm, pointer-typed
sides SCALE by their element size, same-symbol pointer differences
divide by it. No second folder; the shape arms stay.
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

PRE = ("int g; int gs[8]; long gl[8]; char gc[8];\n"
       "struct S { char x[16]; }; struct S gsp[4];\n"
       "const int c = 5; int gi = 7; static const int sc = 7;\n"
       "extern long ea[4]; int mm[2][3];\n"
       "long f(void);\nint main(void){ return 0; }\n")
BODY = 'long f(void){{ long r; asm("movl %1, %%eax" : "=a"(r) : "i"({})); return r; }}\n'  # noqa: E501


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


def _blcc_imm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc(["-c", str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must fold:\n" + r.stderr
    a = (tmp_path / (str(o) + ".s")).read_text()
    body = a.split("\nf:", 1)[1] if "\nf:" in a else a
    m = re.search(r"movl?\s+(-?\$\S+), %eax", body)
    return m.group(1) if m else None


# (tag, expr, expected $-form at gcc AND blcc — the TYPE law agrees)
FOLD_TYPE_TABLE = [
    # F-1: pointer difference = ELEMENTS (esz family); cast = BYTES
    ("f1-int", "&gs[4]-&gs[0]", "$4"),
    ("f1-long", "&gl[4]-&gl[0]", "$4"),
    ("f1-char", "&gc[5]-&gc[1]", "$4"),
    ("f1-struct", "&gsp[3]-&gsp[0]", "$3"),
    ("f1-neg", "&gs[0]-&gs[4]", "$-4"),
    ("f1-zero", "&gs[2]-&gs[2]", "$0"),
    ("f1-comp", "&gs[4]-&gs[0]-1", "$3"),
    ("f1-cast", "(long)&gs[4]-(long)&gs[0]", "$16"),
    ("f1-cast-long", "(long)&gl[8]-(long)&gl[0]", "$64"),
    ("f1-cast-comp", "(long)&gs[8]+3-1", "$gs+34"),
    # F-3: VALUE arm only at the bare spelling; '&' answers the ADDRESS
    ("f3-addr", "&c", "$c"),
    ("f3-val", "c", "$5"),
    ("f3-static-val", "sc", "$7"),
    ("f3-static-addr", "&sc", "$sc"),
    ("f3-addr-gi", "&gi", "$gi"),
    # F-4: pointer + int scales by element size; casts scale by THEIRS
    ("f4-plus", "&gs[3]+1", "$gs+16"),
    ("f4-rev", "1+&gs[3]", "$gs+16"),
    ("f4-longadd", "&gs[3]+1L", "$gs+16"),
    ("f4-castadd", "(long)&gs[3]+1", "$gs+13"),
    ("f4-charadd", "(char*)&gs[3]+1", "$gs+13"),
    ("f4-voidadd", "(void*)&g+4", "$g+4"),
    ("f4-decayadd", "gs+3", "$gs+12"),
    ("f4-minus", "&gs[3]-1", "$gs+8"),
    # address arms unchanged (W-M forms ride the type gate now)
    ("x-addr", "&gs[3]", "$gs+12"),
    ("x-negidx", "&gs[-2]", "$gs-8"),
    ("x-extern", "&ea[2]", "$ea+16"),
    ("x-castplus", "(long)&gs[8]+3", "$gs+35"),
    ("x-enum", "(1<<4) + 3*2 - 1", "$21"),
    # truncating-cast PAIRS: the ONE placement gcc folds the narrow
    # cast in (measured $16); every other narrow spelling is LOUD.
    ("ic-pair", "(int)&gs[4]-(int)&gs[0]", "$16"),
]

import pytest


@pytest.mark.parametrize("tag,expr,want", FOLD_TYPE_TABLE)
def test_wn0_fold_type_table(tmp_path, tag, expr, want):
    src = PRE + BODY.format(expr)
    gi, gerr = _gcc_imm(tmp_path, "wn0" + tag, src)
    assert gi == want, "oracle law moved: {}\n{}".format(gi, gerr)
    bi = _blcc_imm(tmp_path, "wn0" + tag, src)
    assert bi == want, "type-fold: blcc {} vs gcc {} (want {})".format(
        bi, gi, want)


# ---- PAIR-LOUD rows: gcc rc1 AND blcc rc2 — the folder may not
# invent a pass the oracle refuses (the wave's silent class). ----

LOUD_TABLE = [
    ("f2-bare", "gs[3]"),                    # element VALUE, no '&'
    ("gi-plain", "gi"),                      # non-const scalar VALUE
    ("ic-cast", "(int)&g"),                  # truncating address cast
]


@pytest.mark.parametrize("tag,expr", LOUD_TABLE)
def test_wn0_loud_pair(tmp_path, tag, expr):
    src = PRE + BODY.format(expr)
    s = tmp_path / ("wn0L" + tag + ".c")
    s.write_text(src)
    r = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert r.returncode != 0, "gcc must refuse {} (measured)".format(expr)
    b = blcc(["-c", str(s), "-o", str(tmp_path / ("wn0L" + tag + ".o"))])
    assert b.returncode != 0, \
        "blcc invented a pass for {}: {}".format(expr, b.stdout)
    assert "not a compile-time constant" in b.stderr


def test_wn0_f1_run_pair(tmp_path):
    # F-1 is VALUE-visible: the ELEMENT count rides the run-pair.
    src = ('int g1[10];\nlong f(void){ long r;\n'
           ' asm("movl %1, %%eax" : "=a"(r) : "i"(&g1[5] - &g1[1]));\n'
           ' return (r == 4) ? 4 : (int)r; }\n'
           'int main(void){ return (int)f(); }\n')
    s = tmp_path / "wn0run.c"
    s.write_text(src)
    gx = tmp_path / "wn0run.gcc"
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)])
    assert g.returncode == 0, g.stderr
    bx = tmp_path / "wn0run.blcc"
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    assert gv.returncode == 4, "gcc answer moved: {}".format(gv.returncode)
    assert bv.returncode == gv.returncode, \
        "run-pair: gcc {} blcc {} — the fold answered the BYTE span".format(
            gv.returncode, bv.returncode)


def test_wn0_f4_run_pair(tmp_path):
    # F-4 is VALUE-visible: one ELEMENT, not one byte.
    src = ('int g1[10];\nlong f(void){ long r;\n'
           ' asm("movl %1, %%eax" : "=a"(r) : "i"(&g1[2] + 1));\n'
           ' return (r == ((long)&g1[3])) ? 3 : 1; }\n'
           'int main(void){ return (int)f(); }\n')
    s = tmp_path / "wn0run4.c"
    s.write_text(src)
    gx = tmp_path / "wn0run4.gcc"
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)])
    assert g.returncode == 0, g.stderr
    bx = tmp_path / "wn0run4.blcc"
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    assert gv.returncode == 3, "gcc answer moved: {}".format(gv.returncode)
    assert bv.returncode == 3, \
        "run-pair: gcc {} blcc {} — +1 must add ONE element".format(
            gv.returncode, bv.returncode)


def test_wn0_cross_symbol_still_loud(tmp_path):
    # The W-M twin stays: a difference ACROSS objects is gcc's own
    # LOUD and blcc's honest wall — the type gate must not invent a
    # link-time difference either.
    src = ("char g1[8]; char g2[8];\n" + BODY.format("&g1[4]-&g2[0]"))
    s = tmp_path / "wn0gap.c"
    s.write_text(src)
    r = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert r.returncode != 0 and "impossible constraint" in r.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn0gap.o")])
    assert b.returncode != 0 and "not a compile-time constant" in b.stderr


def test_wn0_mem_form_ptr_index_ice_dead(tmp_path):
    # The ICE the type walk EXPOSES: "p"(&gs[3]) / "m"(gs[3]) hit
    # `_asm_elem_ty`'s PtrType arm — `ty.pointee` does not exist
    # (the attribute is `.inner`): internal compiler error at tip.
    src = ('int gs[8];\nlong f(void){ long r;\n'
           ' asm("movq %1, %%rax" : "=a"(r) : "p"(&gs[3])); return r; }\n'
           'int main(void){ return 0; }\n')
    s = tmp_path / "wn0ice.c"
    s.write_text(src)
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn0ice.o")])
    assert b.returncode == 0, "materialization ICE still live: " + b.stderr
