# LINES reason: one wave of legs (M4 W-L COMMIT-2 — the BUILD_BUG_ON_ZERO
# fold: bitfield-width constant folding through __builtin_types_compatible_p
# + block-scope anon-struct materialization; card 12404.2.81) — the macro
# chain, its truth-table arms, and the walk-progress leg are ONE law seen
# from three sides; splitting them separates a fold from its own evidence.
r"""M4 W-L COMMIT-2 — the BUILD_BUG_ON_ZERO fold (walk progress).

THE WALL (walk blocker init/main.c:1263, verbatim):
    #define BUILD_BUG_ON_ZERO(e)  ((int)(sizeof(struct { int:(-!!(e)); })))
The width feeds parse_int_constant → fold_truthy, which has NO arm for
`__builtin_types_compatible_p` — the call folds at CODEGEN (the shipped
§2.12 law in types.py `_types_compatible`) but a bitfield width must fold
at PARSE, so every BUILD_BUG_ON_ZERO site LOUDs "bitfield width, found
'('". THE FIX is two faces of the ONE-law doctrine, never a new law:
  B) fold_truthy gains the Call arm riding the SAME `_types_compatible`
     text — the law moves into `CompatLawMixin` (types.py) so the codegen
     host (TypeMap) and the parse-fold host (Parser) run ONE text; each
     host supplies its already-shipped materializer (TypeMap._ty / the
     parser's expr_type mirror — the same peel _csize/_calign do).
  A) block-scope anon structs (sizeof(struct{...}) etc.) mint their tag
     and register it in struct_tags, but parse_translation_unit DROPPED
     the trailing `_pending` StructDecls — codegen's TypeMap never saw
     them ("undefined struct"). The fix drains the SAME `_drain_pending`
     at TU end; collect's first pass registers them wherever they land.
THE SIZE LAW (measured, gcc 11.4 -Os): `sizeof(struct { int:0; })` is the
GNU empty-struct answer 0 — BUILD_BUG_ON_ZERO(false) folds to 0, and
BUILD_BUG_ON_ZERO(true) asks for width -1, which BOTH compilers reject
(the compile error IS the static assert) — the twin legs pin that both
sides stay loud, never one-sided.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")

# VERBATIM include/linux/bug.h + kern.h spellings (5 lines).
BBQ = (
    "#define BUILD_BUG_ON_ZERO(e)\t\t((int)(sizeof(struct { int:(-!!(e)); })))\n"
    "#define __same_type(a, b)\t__builtin_types_compatible_p(typeof(a), "
    "typeof(b))\n"
    "#define __must_be_array(a)\tBUILD_BUG_ON_ZERO(__same_type((a), &(a)[0]))\n")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


def _pair(tmp_path, tag, src, expect):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc(["-O0", str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode == expect, \
        "run-pair: gcc {} blcc {} expect {}".format(
            g.returncode, b.returncode, expect)


def _loud_too(src, tmp_path, tag):
    # THE BUILD_IS_THE_ASSERT twin: the TRUE case asks for width -1; the
    # gcc law (measured) rejects negative bitfield width — blcc must NOT
    # accept where gcc refuses.
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    g = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    b = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert g.returncode != 0, "gcc must reject the TRUE case"
    assert b.returncode != 0, "blcc must reject the TRUE case:\n" + b.stderr


# ------------------------------------------------- the verbatim macro

def test_wl2_bbq_false_case_folds_pair(tmp_path):
    # BUILD_BUG_ON_ZERO(false) = 0 (measured gcc: a struct carrying only
    # a :0 anonymous padding field has size 0 — the GNU empty-struct
    # answer the kernel relies on). Used the way the kernel uses it: an
    # ARRAY SIZE, an enum term and an expression addend — never a NAMED
    # :0 field, which §1 row 12 already LOUDs (gcc error twin).
    # __must_be_array: real array => incompatible with &(a)[0]'s pointer
    # type => 0; an int* => compatible with &p[0]'s int* => 1 (width -1
    # => BOTH reject: that IS the assert, pinned by the true-case leg).
    _pair(tmp_path, "wl2_bbq",
          BBQ +
          "static int arr[8];\n"
          "static int probe[1 + BUILD_BUG_ON_ZERO(__must_be_array(arr))];\n"
          "int main(void){ int a2[3];\n"
          "  int x = 13 + BUILD_BUG_ON_ZERO(__must_be_array(a2))\n"
          "            + BUILD_BUG_ON_ZERO(__must_be_array(arr));\n"
          "  return (int)(sizeof(probe)/sizeof(probe[0])) + x\n"
          "         + (int)(sizeof(arr)/sizeof(arr[0])) - 1; }\n", 21)


def test_wl2_bbq_true_case_is_the_assert_both_sides(tmp_path):
    # BUILD_BUG_ON_ZERO(1) => width -1 => BOTH compilers reject (the
    # error IS the assert). NAMED fairness twin: this leg is GREEN at
    # tip too — the fold must answer 1 there, never silently 0.
    _loud_too(BBQ + "static int boom[BUILD_BUG_ON_ZERO(1)];\n"
              "int main(void){return 0;}\n", tmp_path, "wl2_true")


def test_wl2_compat_truth_table_fold(tmp_path):
    # The fold answers the shipped §2.12 law's truth table through width
    # folds (fold ⇒ width 0; the NEGATION of a false pair ⇒ width -1 is
    # rejected ONLY if the fold got it WRONG — pinning both directions).
    # Direct pins on the fold's TRUTH TABLE, each row expressed ONLY
    # through the fold: the row compiles iff the fold answers as gcc
    # measures (a wrong answer asks for width -1 => compile error).
    s = tmp_path / "wl2_sa.c"
    s.write_text(BBQ +
        "_Static_assert(BUILD_BUG_ON_ZERO(__builtin_types_compatible_p"
        "(int, long) != 0) == 0, \"tl0\");\n"
        "_Static_assert(BUILD_BUG_ON_ZERO(__builtin_types_compatible_p"
        "(int, int) != 1) == 0, \"tl1\");\n"
        "_Static_assert(BUILD_BUG_ON_ZERO(__builtin_types_compatible_p"
        "(int *, const int *) != 0) == 0, \"tl2\");\n"
        "_Static_assert(BUILD_BUG_ON_ZERO(__builtin_types_compatible_p"
        "(int, const int) != 1) == 0, \"tl3\");\n"
        "_Static_assert(BUILD_BUG_ON_ZERO(__builtin_types_compatible_p"
        "(typeof(1), typeof(1L)) != 0) == 0, \"tl4\");\n"
        "int main(void){return 5;}\n")
    g = gcc(["-c", str(s), "-o", str(tmp_path / "sa.g.o")])
    assert g.returncode == 0, "the table is gcc-measured:\n" + g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "sa.b.o")])
    assert b.returncode == 0, "the fold answers the table:\n" + b.stderr


def test_wl2_anon_struct_in_sizeof_materializes(tmp_path):
    # Gap A: block-scope anon structs in sizeof type-contexts — tag minted
    # and registered at parse, but the TU loop DROPPED the trailing
    # _pending StructDecls, so codegen answered "undefined struct".
    _pair(tmp_path, "wl2_anon",
          "int f(int x){ return (int)sizeof(struct{int a; long b;}) + x; }\n"
          "int main(void){ int arr[sizeof(struct{int a; long b;})"
          " / sizeof(struct{int a;})];\n"
          "  return (int)f(0) + (int)(sizeof(arr)/sizeof(arr[0]))\n"
          "    + (int)sizeof(struct{char c[5];}); }\n",
          16 + 16 / 4 + 5)


def test_wl2_anon_sizeof_in_width_and_param(tmp_path):
    # The same materialization reached through a bitfield width AND a
    # parameter-declarator sizeof (type contexts, not expression scope).
    _pair(tmp_path, "wl2_anon2",
          "struct H { unsigned int w : sizeof(struct{int a;}) * 8 - 1;\n"
          "  int k : sizeof(struct{int a;}) * 8 - 2; };\n"
          "int g(int v[sizeof(struct{long x;})]){ return 4; }\n"
          "int main(void){ struct H h; return (int)(sizeof(h) > 0 ? 2 : 9)\n"
          "  + g(0); }\n", 6)


def test_wl2_enum_width_adjacent_streams(tmp_path):
    # Adjacent streams that feed the SAME width grammar (build_bug.h
    # consumers in the walk's front row): enum values through the folded
    # kernel idiom `1UL << ...` and BUILD_BUG_ON_ZERO in an initializer —
    # these compile verbatim or the fold regressed.
    src = BBQ + (
        "typedef unsigned long size_t;\n"
        "struct timer_list { int x; };\n"
        "static struct timer_list tarr[2];\n"
        "enum { N = sizeof(tarr)/sizeof(tarr[0]) + BUILD_BUG_ON_ZERO("
        "__must_be_array(tarr)) };\n"
        "static char slab[64 + (int)BUILD_BUG_ON_ZERO(sizeof(long) != 8)];\n"
        "int main(void){ return (int)N + (int)sizeof(slab) - 45; }\n")
    _pair(tmp_path, "wl2_adj", src, 2 + 64 - 45)


# --------------------------------------------------------- walk progress

def _clean_i(path, tmp_path, tag):
    out = tmp_path / (tag + ".clean.i")
    with open(path, "r", errors="replace") as fh:
        out.write_text("".join(ln for ln in fh if not ln.startswith("# ")))
    return out


@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
def test_wl2_walk_past_main_1263(tmp_path):
    # The W-L walk leg: init/main.c's first blocker at :1263 was the
    # BUILD_BUG_ON_ZERO width LOUD. After this commit the walk moves
    # PAST it — the leg pins the width sentence is GONE from the stream
    # (the next blocker is reported by the CLOSE row, not pinned here so
    # the leg cannot go stale against future waves' gains).
    src = _clean_i(os.path.join(STREAMS, "init_main.c.i"), tmp_path, "wl2w")
    r = blcc(["-c", str(src), "-o", str(tmp_path / "o.o")])
    assert "bitfield width" not in r.stderr, \
        "the :1263 width wall is ALIVE in init_main.c:\n" + r.stderr[:400]
