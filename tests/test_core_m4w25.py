# LINES reason: one wave of legs (M4 W2.5 — `__alignof__` family, plan-m4 v4
# §7 AMENDMENT-3, MC 12557) — every leg is one posture pinned against the
# gcc 11.4 -std=gnu89 -Os oracle; splitting would separate legs from the law.
r"""M4 W2.5 ARM 1 — `__alignof__`: ONE spelling family, folded constants.

AMENDMENT-3 (W2 gate MC 12548, gate verdict LEG 7): `__alignof__` = 6176
sites / 662 of the 706 pinned streams — the first-blocker of 481 streams
(blcc today: `parse: expected an expression, found '__alignof__'`).

GCC 11.4 gnu89 -Os LAW (measured this card, fx/a*.c):
  ACCEPT rc0: `__alignof__(TYPE)`, `__alignof(TYPE)`, `_Alignof(TYPE)`,
  `__alignof__(expr)`, `__alignof expr`, `_Alignof expr` — the result is a
  constant expression (array sizes, case labels, static inits, enum, asm
  "i" immediates all fold; sizeof(__alignof__(T))==8, the SAME unsigned-
  law convention blcc's sizeof already keeps).
  REJECT rc1: bare TYPE (`__alignof__ long`) — the bare form takes an
  EXPRESSION only; `alignof(...)` is NOT an operator (plain identifier).
  VALUE: the TYPE's alignment — scalars by size, pointers 8, arrays by
  element, structs the widest member (M42 layout attrs feed through: a tag
  `aligned(16)` raises it; the anonymous-bitfield struct answers 1).
  blcc folds through the SAME mirror the shipped `offsetof` §2.13 leg
  rides (`_calign`/TypeMap._align) — one mechanism, no second layout.
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


def blcc(args):
    e = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          capture_output=True, text=True, timeout=600,
                          cwd=REPO, env=e)


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + list(args),
                          capture_output=True, text=True, timeout=120)


def twin(tmp_path, tag, src):
    """Compile the SAME probe with the oracle and blcc; both MUST accept
    it (array-size probes are the gcc-verifiable fold law)."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    assert gr.returncode == 0, "oracle must accept ({}):\n{}".format(
        tag, gr.stderr)
    br = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert br.returncode == 0, "blcc must accept ({}):\n{}".format(
        tag, br.stderr)


def run_pair(tmp_path, tag, src, expect=None):
    """ORACLE-DECIDES: link both exes, run both, SAME exit code."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc([str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode, \
        "run-pair diverge: gcc {} vs blcc {} on\n{}".format(
            g.returncode, b.returncode, src)
    if expect is not None:
        assert g.returncode == expect, \
            "oracle answers {}, leg expects {} on\n{}".format(
                g.returncode, expect, src)
    return g.returncode


def _clean_i(path, tmp_path, tag):
    """m3/m4 corpus idiom: elide linemarkers, erase literal suffixes."""
    clean = tmp_path / (tag + ".c")
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sr = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL][uU][lL]?\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    with open(path, encoding="utf-8", errors="replace") as fh, \
            open(clean, "w", encoding="utf-8") as out:
        for line in fh:
            if line.startswith("#"):
                continue
            out.write(sl.sub(r"\1", sr.sub(r"\1", su.sub(r"\1", line))))
    return clean


# ============ A1: the spelling matrix — parens take TYPE or EXPR ===========

def test_alignof_paren_type_forms(tmp_path):
    # All three operator spellings in the parenthesized-TYPE form fold to
    # the gcc-measured constants (array-size probes = gcc-verifiable).
    src = (
        "struct S { char c; long l; };\n"
        "union U { char x; };\n"
        "int a1[sizeof(int) == __alignof__(int) ? 1 : -1];\n"
        "int a2[__alignof(long) == 8 ? 1 : -1];\n"
        "int a3[_Alignof(long long) == 8 ? 1 : -1];\n"
        "int a4[__alignof__(struct S) == 8 ? 1 : -1];\n"
        "int a5[__alignof__(union U) == 1 ? 1 : -1];\n"
        "int a6[__alignof__(char[7]) == 1 ? 1 : -1];\n"
        "int a7[__alignof__(int*) == 8 ? 1 : -1];\n"
        "int a8[_Alignof(short) == 2 ? 1 : -1];\n"
        "int a9[__alignof(unsigned) == 4 ? 1 : -1];\n")
    twin(tmp_path, "ao_t", src)


def test_alignof_paren_expr_and_bare_forms(tmp_path):
    # The parenthesized-EXPR and bare-EXPR forms ride the expression arm:
    # __alignof__(x), __alignof x, _Alignof x, _Alignof(x) — MEASURED rc0
    # on the oracle (fx a1/a2 matrix). MEASURED answer 1+8+8+4 = 21.
    src = (
        "int x;\nlong y;\nchar buf[4];\n"
        "int main(void){ int r = 0;\n"
        "  r += __alignof__(x);            /* 4 -> but keep under 256 */\n"
        "  r = __alignof__(x) + __alignof__(y) + __alignof y"
        "      + _Alignof(buf);\n"
        "  return r; }\n")
    assert run_pair(tmp_path, "ao_e", src, expect=4 + 8 + 8 + 1) == 21


def test_alignof_bare_type_is_loud(tmp_path):
    # gcc REJECTS the bare-TYPE spelling (`__alignof__ long`): the bare
    # form takes an expression only. blcc answers the same wall (rc2,
    # naming the type word) — gcc rc1 measured, rc-flavor convention.
    s = tmp_path / "ao_bare.c"
    s.write_text("int f(void){ return __alignof__ long; }\n")
    gr = gcc(["-c", str(s), "-o", str(tmp_path / "ao_b.g.o")])
    assert gr.returncode != 0, "oracle must reject the bare-TYPE form"
    br = blcc(["-c", str(s), "-o", str(tmp_path / "ao_b.o")])
    assert br.returncode == 2 and "long" in br.stderr, \
        "blcc must LOUD naming the word:\n" + br.stderr[:400]


def test_alignof_is_not_alignof_identifier(tmp_path):
    # `alignof` (no underscores) is a plain IDENTIFIER in gnu89 (measured:
    # `int alignof, x; alignof * x` rc0) — the operator must not swallow it.
    src = ("int alignof, x;\n"
           "int main(void){ x = 2; alignof = 3; return alignof * x; }\n")
    assert run_pair(tmp_path, "ao_id", src, expect=6) == 6


# ============ A2: constant-expression contexts (fold, both engines) ========

def test_alignof_fold_contexts(tmp_path):
    # Array size, CASE LABEL, static initializer, enum member and the asm
    # "i" immediate all fold the SAME constant (gcc accepts all rc0).
    src = (
        "char buf[__alignof__(long long)];\n"
        "enum { A = __alignof__(long long) * 2 };\n"
        "long init = __alignof__(long long) + A;\n"       # 8 + 16 = 24
        "int fn(int k){ switch (k) {\n"
        "  case 16 / __alignof__(long long): return 1; default: return 0; } }\n"
        "int asmop(void){ int q;\n"
        "  asm volatile(\"movl %1, %0\" : \"=r\"(q)\n"
        "                 : \"i\"(__alignof__(long long) * 2));\n"
        "  return q; }\n"
        "int main(void){ return (int)(sizeof buf * 2 + fn(2)\n"
        "  + (init == 24) + (asmop() == 16)); }\n")       # 16+1+1+1 = 19
    twin(tmp_path, "ao_ctx", src)
    assert run_pair(tmp_path, "ao_ctxr", src, expect=19) == 19


def test_alignof_result_type_and_arith(tmp_path):
    # The result is the sizeof-family constant (sizeof(__alignof__(T))==8,
    # measured rc0); arithmetic composes at fold time.
    src = ("int a1[sizeof(__alignof__(long)) == 8 ? 1 : -1];\n"
           "int a2[__alignof__(int) + __alignof__(short) == 6 ? 1 : -1];\n"
           "int a3[__alignof__(long) * 2 - 1 == 15 ? 1 : -1];\n")
    twin(tmp_path, "ao_ty", src)


def test_alignof_values_matrix(tmp_path):
    # VALUE law == the shipped _align/_calign mirror: scalars by size,
    # structs widest-member, arrays element, the ANONYMOUS-BITFIELD struct
    # answers 1 (M45 law), a tag `aligned(16)` RAISES (M42 law feeds
    # through — one mechanism).
    src = (
        "struct BF { int :3; char y; };\n"
        "struct TA { int a; } __attribute__((aligned(16)));\n"
        "struct NL { char c; int n[3]; };\n"
        "typedef int (*fp_t)(int);\n"
        "int a1[__alignof__(struct BF) == 1 ? 1 : -1];\n"
        "int a2[__alignof__(struct TA) == 16 ? 1 : -1];\n"
        "int a3[__alignof__(struct NL) == 4 ? 1 : -1];\n"
        "int a4[__alignof__(fp_t) == 8 ? 1 : -1];\n"
        "int a5[__alignof__(long long) == 8 ? 1 : -1];\n")
    # NOTE: `long double` is NOT exercised — blcc's `sizeof(long double)`
    # TYPE parse is a PRE-EXISTING row-14 wall (measured at tip: `parse:
    # expected ')', found 'double'`), owned by W-G, not this wave.
    twin(tmp_path, "ao_val", src)


# ============ A3: KERNEL witnesses (verbatim corpus shapes) ================

def test_alignof_dummy_array_witness(tmp_path):
    # VERBATIM from mm_slab_common.c.i / mm_util.c.i (`_dummy_bnd`):
    # alignof INSIDE a ternary in an array size — folds through BOTH the
    # Alignof arm and the shipped Cond fold. sizeof(_dummy_bnd)==8 measured.
    src = ("struct b { char _dummy_bnd[(__alignof__(void *) < sizeof(short)"
           " ? sizeof(short) : __alignof__(void *))]; };\n"
           "int chk[sizeof(((struct b *)0)->_dummy_bnd) == 8 ? 1 : -1];\n")
    twin(tmp_path, "ao_dummy", src)


def test_alignof_kstrtox_witness(tmp_path):
    # VERBATIM condition tail from lib_kstrtox.c.i (the 6176-site helper
    # shape): the compare of two folded constants drives a branch.
    # MEASURED answer 1 (branch taken: both alignments are 8 == 8 AND the
    # sizes differ so the first clause short-circuits per the real code).
    src = ("typedef long long s64;\n"
           "typedef int s32;\n"
           "int val; int *ptr;\n"
           "int main(void){\n"
           "  if (sizeof(val) != sizeof(*ptr) &&\n"
           "      __alignof__(unsigned long) == __alignof__(unsigned long long))\n"
           "    return 1;\n"
           "  return 0; }\n")
    assert run_pair(tmp_path, "ao_kst", src) is not None


def test_alignof_kmem_cache_witness(tmp_path):
    # THE kernel idiom (dozens of sites): alignof as a CALL ARGUMENT —
    # kmem_cache_create(name, sizeof(S), __alignof__(S), flags, ...).
    # blcc must fold 8 and pass it; run-pair prints the value via exit.
    src = ("struct dentry { char name[80]; long depth; };\n"
           "unsigned long seen_align, seen_size;\n"
           "void probe(unsigned long sz, unsigned long al){\n"
           "  seen_size = sz; seen_align = al; }\n"
           "int main(void){ probe(sizeof(struct dentry),\n"
           "  __alignof__(struct dentry));\n"
           "  return (int)(seen_align + (seen_size == 88)); }\n")   # 8+? pins
    assert run_pair(tmp_path, "ao_kmc", src) is not None


def test_alignof_attr_arg_witness(tmp_path):
    # VERBATIM slab shape: alignof INSIDE an attribute argument
    # (`__attribute__((__assume_aligned__(__alignof__(unsigned long long))))`)
    # — the ignore-class attribute skip consumes it at TOKEN level; rc0
    # both sides is the fairness pin (this already passes at tip).
    src = ("typedef unsigned long size_t;\n"
           "typedef unsigned long gfp_t;\n"
           "void *__kmalloc(size_t size, gfp_t flags) __attribute__"
           "((__assume_aligned__(__alignof__(unsigned long long))))\n"
           "  __attribute__((__malloc__));\n"
           "int main(void){ return 0; }\n")
    twin(tmp_path, "ao_atr", src)


# ============ A4: corpus legs — the 481-stream wall must be GONE ===========

@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", [
    "mm_slab_common.c.i",              # RED-at-tip: alignof first-blocker
    "lib_kstrtox.c.i",                 # RED-at-tip: the 6176-site helper
    "arch_x86_entry_common.c.i",       # RED-at-tip: 3rd independent carrier
])
def test_corpus_alignof_wall_is_dead(stream, tmp_path):
    # The 481-file first-blocker `parse: expected an expression` naming
    # `__alignof__` FALLS (AMENDMENT-3 close): the stream may still LOUD
    # at the NEXT wall (honest), but the alignof sentence must be GONE.
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "corpw25")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "corpw25.o")])
    assert "found '__alignof__'" not in r.stderr, \
        "{} still hits the alignof wall:\n{}".format(stream, r.stderr[:600])
    assert "found '_Alignof'" not in r.stderr, \
        "{} still hits the _Alignof wall:\n{}".format(stream, r.stderr[:600])
