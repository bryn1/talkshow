# LINES reason: one wave of legs (M4 W-J COMMIT-2 — `__builtin_offsetof`
# with a RUNTIME ARRAY INDEX, rbtree_latch.h:72 = 118 first-blockers, card
# 12404.2.77) — splitting would separate the fold's constant/dynamic split
# from the run-pairs that prove the arithmetic.
r"""M4 W-J COMMIT-2 — `__builtin_offsetof(TYPE, member[idx])` with a
NON-CONSTANT index.

THE WALL (gate LEG 8 R2, re-measured at MY hands): rbtree_latch.h:72:126,
118 streams, the `container_of(node, struct latch_tree_node, node[idx])`
shape — post-pp the macro body spells `__builtin_offsetof(struct
latch_tree_node, node[idx])` with `unsigned int idx` a RUNTIME value (my
grep of the pinned streams, verbatim: arch_x86_entry_common.c.i). gcc
11.4 gnu89 -Os rc0 — the builtin is a general expression when the index
is one. blcc tip: sema "__builtin_offsetof index is not a compile-time
constant (§2.13)" — the §2.13 fold LOUDs.

MEASURED LAW (my probes of_a..of_p, gcc 11.4 gnu89 -Os, rc + run; the
CONSTANT arm rides the shipped fold UNTOUCHED — asm parity leg pins it):
  CONSTANT split first: fold_truthy the index; foldable rides the shipped
    IntLit law exactly as before (of_c array-size fold stays rc0 and the
    CONSTANT asm shows NO multiplication — the fold is not downgraded).
  RUNTIME arm (index not foldable): the builtin becomes the expression
    `off + idx * esize` built from the SHIPPED machinery — off = the
    constant layout fold to the array member (the existing _offsetof_flat
    walk), esize = _csize (the shipped §2.13/sizeof mirror law, packed+
    bitfield shrink included — of_f runs pair-clean), the arithmetic rides
    ast.Binary through the shipped expression codegen ("fold through
    shipped machinery": NO new mechanism, NO libcall — asm legs).
  NESTED paths continue past the dyn step: `arr[i][j]`, `inner.u[i].tail`
    — further steps ride the SAME walk; two dyn steps accumulate
    (of_n: 64 and 32 measured).
  NOT an array → both LOUD (of_e: gcc rc1 "subscripted value is neither
    array nor pointer nor vector"; blcc "indexed member is not an array
    (§2.13)" — SAME VERDICT, different sentence, pinned).
  BITFIELD subscripted → both LOUD (of_g same gcc sentence; blcc's
    shipped "no member … a bitfield member … stays LOUD" — same verdict).
  Bitfield ELEMENTS inside the array size law: of_f `struct E { u16 p0:12,
    p1:4; }` packed — gcc esize 2 (measured f(1)==2 f(2)==4): the §2.13
    mirror _csize already shrinks the unit (W-F law) — pair-clean.
  UNSIGNED/CHAR index (of_j/of_k): int-rules, pair-clean run values.
  VLA-size use (of_m `int a[__builtin_offsetof(T, arr[i])]`): gcc rc0
    (gnu89 VLA), blcc LOUD rc2 — the VLA class is a shipped DEFER, LOUD-
    DIV named, corpus volume 0 (dyn-index sites in the 706 are ONLY
    inside container_of address arithmetic).
  RESULT TYPE divergence PINNED (pre-existing class, my measurement):
    gcc types the builtin `unsigned long` (sizeof == 8, of_d/of_p
    measured BOTH sides); blcc's shipped constant arm types it `int`
    (sizeof 4 — measured at tip) and the dyn arm rides the SAME int law
    (of_d pair below). Named, volume-law: every kernel use is
    `(char*)p - off` BYTE arithmetic — a negative or > 2^31 offset is UB
    territory; the container_of run-pair is the observable.
"""
import os
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


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _gcc_rc(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return gcc(["-Os", "-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])


def _loud(tmp_path, tag, src, needle=None, gcc_rc=None):
    g = _gcc_rc(tmp_path, tag, src)
    if gcc_rc is not None:
        assert g.returncode == gcc_rc, "gcc rc{} expected:\n{}".format(
            gcc_rc, g.stderr)
    r = _compile(tmp_path, tag, src)
    assert r.returncode != 0, "must LOUD:\n" + src + g.stderr
    if needle is not None:
        diag = r.stderr.replace(str(tmp_path), "")
        assert needle in diag, r.stderr
    return r


def _pair(tmp_path, tag, src, expect):
    """ORACLE-DECIDES shipped run_pair: full link both sides, run, SAME
    exit code, and BOTH equal the Python-precomputed expectation."""
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


RB = ("struct rb_node { unsigned long __rb_parent_color;\n"
      "                     struct rb_node *rb_right, *rb_left; };\n"
      "struct latch_tree_node { struct rb_node node[2]; void *priv; };\n")


# ------------------------------------------------- THE witness (118 wall)

def test_wj2_rbtree_latch_container_of_run_pair(tmp_path):
    # rbtree_latch.h:72 VERBATIM shape (the __lt_from_rb /
    # __rb_de_augment_form family): container_of over `node[idx]` with a
    # RUNTIME idx, back-derived pointer must recover the owner. idx=1 and
    # idx=0 both, from the SAME object.
    _pair(tmp_path, "wj2_latch",
          RB +
          "struct owner { int magic; struct latch_tree_node ltn; };\n"
          "#define container_of(ptr, type, member) \\\n"
          "  ((type *)((char *)(ptr) - __builtin_offsetof(type, member)))\n"
          "struct owner *back(struct rb_node *n, int idx) {\n"
          "  return container_of(n, struct owner, ltn.node[idx]); }\n"
          "int main(void){ struct owner o; o.magic = 77;\n"
          "  return (back(&o.ltn.node[1], 1)->magic == 77\n"
          "       && back(&o.ltn.node[0], 0)->magic == 77) ? 0 : 1; }\n", 0)


# ------------------------------------------------------- the arithmetic

def test_wj2_dyn_basic_and_scaled_run_pair(tmp_path):
    # of_a: esize scaling (f(i) == i * 16); of_b: a constant PREFIX rides
    # the fold (pad forces node@8 — gcc's layout law, measured at MY hands
    # — the self-fix story below) while the index term stays runtime.
    _pair(tmp_path, "wj2_a",
          "struct rb { long a, b; };\nstruct L { struct rb node[2]; };\n"
          "unsigned long f(int i){ return __builtin_offsetof(struct L,"
          " node[i]); }\n"
          "int main(void){ return (f(0) == 0 && f(1) == 16"
          " && f(2) == 32) ? 0 : 1; }\n", 0)
    _pair(tmp_path, "wj2_b",
          "struct rb { long a, b; };\n"
          "struct L { int pad; struct rb node[2]; };\n"
          "unsigned long f(int i){ return __builtin_offsetof(struct L,"
          " node[2 * i + 1]); }\n"
          "int main(void){ return (f(0) == 24 && f(1) == 56) ? 0 : 1; }\n",
          0)


def test_wj2_nested_and_double_dyn_run_pair(tmp_path):
    # of_h: constant path past .u then dyn index; of_n: TWO dyn steps
    # accumulate (row-major: (i*4 + j) * 16 measured against gcc).
    _pair(tmp_path, "wj2_h",
          "struct Inner { long t; long u[4]; };\n"
          "struct Outer { char c; struct Inner inner; };\n"
          "unsigned long f(int i){ return __builtin_offsetof(struct Outer,"
          " inner.u[i]); }\n"
          "int main(void){ return (f(0) == 16 && f(2) == 32) ? 0 : 1; }\n",
          0)
    _pair(tmp_path, "wj2_n",
          "struct E { long v[2]; };\nstruct A { struct E arr[3][4]; };\n"
          "unsigned long g(int i, int j){ return __builtin_offsetof("
          "struct A, arr[i][j]); }\n"
          "int main(void){ return (g(1, 0) == 64 && g(0, 2) == 32"
          " && g(2, 3) == 176) ? 0 : 1; }\n", 0)


def test_wj2_index_types_run_pair(tmp_path):
    # of_j/of_k: unsigned long and signed char indices — int-rules on
    # sane magnitudes, pair-clean (measured both binaries).
    _pair(tmp_path, "wj2_j",
          "struct E { long v[2]; };\nstruct A { struct E arr[4]; };\n"
          "unsigned long f(unsigned long i){ return __builtin_offsetof("
          "struct A, arr[i]); }\n"
          "int main(void){ return f(3) == 48 ? 0 : 1; }\n", 0)
    _pair(tmp_path, "wj2_k",
          "struct E { long v; };\nstruct A { struct E arr[4]; };\n"
          "unsigned long g(signed char i){ return __builtin_offsetof("
          "struct A, arr[i]); }\n"
          "int main(void){ return g(2) == 16 ? 0 : 1; }\n", 0)


def test_wj2_packed_bitfield_element_run_pair(tmp_path):
    # of_f: the element size law for a packed-bitfield element — the
    # §2.13 MIRROR _csize shrinks the unit to 2 (W-F law), so the runtime
    # term scales by 2, exactly gcc's measured f(1)==2 f(2)==4.
    _pair(tmp_path, "wj2_f",
          "struct __attribute__((__packed__)) E { unsigned short p0:12,"
          " p1:4; };\n"
          "struct T { struct E arr[3]; };\n"
          "unsigned long f(int i){ return __builtin_offsetof(struct T,"
          " arr[i]); }\n"
          "int main(void){ return (f(1) == 2 && f(2) == 4) ? 0 : 1; }\n", 0)


def test_wj2_runtime_division_of_dyn_run_pair(tmp_path):
    # of_l: the dyn result is a REAL expression — arithmetic rides on it
    # through the shipped codegen (division by 8 = shr, no libcall).
    _pair(tmp_path, "wj2_l",
          "struct E { long v; };\nstruct A { struct E arr[8]; };\n"
          "long f(int i){ return (long)__builtin_offsetof(struct A,"
          " arr[i]) / 8; }\n"
          "int main(void){ return f(5) == 5 ? 0 : 1; }\n", 0)


# --------------------------------------------- asm parity: shipped fold

def test_wj2_constant_arm_asm_unchanged(tmp_path):
    # asm-parity #1: the CONSTANT arm still FOLDS to a bare immediate —
    # the dyn arm must not downgrade it. Needle: the folded f(1)==16 shape
    # has no multiply/shift chain; the offset rides as a constant.
    s = tmp_path / "wj2_ca.c"
    s.write_text("struct rb { long a, b; };\nstruct L { struct rb"
                 " node[2]; };\nlong f(void){ return __builtin_offsetof("
                 "struct L, node[1]); }\n")
    r = blcc(["--emit-asm", "-c", str(s), "-o", str(tmp_path / "wj2_ca.o")])
    assert r.returncode == 0, r.stderr
    asm = r.stdout
    assert "imul" not in asm and "mulq" not in asm and "shl" not in asm, \
        "constant arm must stay FOLDED:\n" + asm
    assert "16" in asm, "folded immediate 16 must be visible:\n" + asm


def test_wj2_dyn_arm_asm_shipped_arith_no_libcall(tmp_path):
    # asm-parity #2: the RUNTIME arm is arithmetic through the shipped
    # expression machinery — NO call of any kind (no libcall, no helper).
    s = tmp_path / "wj2_da.c"
    s.write_text("struct rb { long a, b; };\nstruct L { struct rb"
                 " node[2]; };\nunsigned long f(int i){"
                 " return __builtin_offsetof(struct L, node[i]); }\n")
    r = blcc(["--emit-asm", "-c", str(s), "-o", str(tmp_path / "wj2_da.o")])
    assert r.returncode == 0, r.stderr
    # M4 W-K (MC 12663, gate F-6): a POSITIVE anchor, like the
    # constant-arm twin has — rc0 + no-call alone stayed GREEN under
    # the gate PLANT-B (dyn values wrong); the shipped arithmetic must
    # actually be visible: imulq of the index by the element size.
    assert "call" not in r.stdout, \
        "dyn arm must ride the shipped arithmetic (no libcall):\n" + \
        r.stdout
    assert "imulq" in r.stdout, \
        "positive anchor (gate F-6): the shipped multiply must be VISIBLE " \
        "(gate PLANT-B dropped the index term and this leg stayed GREEN " \
        "on rc/no-call alone); measured blcc -Os arm: imulq %rcx, %rax\n" \
        + r.stdout


# ------------------------------------------------ LOUD-consistency arms

def test_wj2_not_array_same_verdict(tmp_path):
    # of_e: index on a non-array member — gcc rc1 "subscripted value is
    # neither array nor pointer nor vector"; blcc LOUDs its §2.13
    # sentence. SAME VERDICT, different sentence, pinned.
    r = _loud(tmp_path, "wj2_e",
              "struct S { int x; };\nunsigned long f(int i){"
              " return __builtin_offsetof(struct S, x[i]); }\n",
              needle="indexed member is not an array", gcc_rc=1)
    assert "subscripted value" not in r.stderr  # blcc keeps its own law


def test_wj2_bitfield_subscripted_same_verdict(tmp_path):
    # of_g: subscript ON a bitfield — gcc rc1 (same sentence); blcc's
    # shipped "no member … bitfield … LOUD" answers (bitfields never land
    # in the layout table — the §2.13 posture).
    _loud(tmp_path, "wj2_g",
          "struct B { unsigned int bf:3; };\nunsigned long f(int i){"
          " return __builtin_offsetof(struct B, bf[i]); }\n",
          needle="bitfield", gcc_rc=1)


def test_wj2_unsizable_element_same_verdict(tmp_path):
    # RED at the pre-fix tree via the old §2.13 fold LOUD; after the arm
    # the dyn index rides the SAME walk as the constant one and answers the
    # shipped REAL-BLOCKER sentence. Array of UNDEFINED element — gcc LOUDs at the array
    # declaration ("array type has incomplete element type"); the shipped
    # §2.13 walk answers at the fold with its REAL-BLOCKER sentence
    # (measured at tip). SAME VERDICT, different sentence and position,
    # pinned honestly.
    _loud(tmp_path, "wj2_esz",
          "struct E;\nstruct T { struct E arr[2]; };\n"
          "unsigned long f(int i){ return __builtin_offsetof(struct T,"
          " arr[i]); }\n",
          needle="incomplete", gcc_rc=1)


def test_wj2_vla_dyn_loud_div_PIN(tmp_path):
    # of_m: dyn offsetof in a VLA size — gcc rc0 (gnu89 VLA), blcc LOUD
    # (the VLA class is a shipped DEFER, and the old §2.13 sentence is
    # REPLACED by the fold law). LOUD-DIV named, corpus volume 0 (the
    # 706's dyn-index sites are container_of address arithmetic only).
    g = _gcc_rc(tmp_path, "wj2_m",
                "struct E { long v; };\nstruct A { struct E arr[4]; };\n"
                "int g(int i){ int a[__builtin_offsetof(struct A,"
                " arr[i])]; return (int)sizeof(a) / 8; }\n")
    assert g.returncode == 0, "gcc gnu89 VLA twin:\n" + g.stderr
    r = _compile(tmp_path, "wj2_m",
                 "struct E { long v; };\nstruct A { struct E arr[4]; };\n"
                 "int g(int i){ int a[__builtin_offsetof(struct A,"
                 " arr[i])]; return (int)sizeof(a) / 8; }\n")
    assert r.returncode != 0, "blcc keeps the VLA/const wall (named)"


# ------------------------------------------------- the divergence pins

def test_wj2_result_type_divergence_PIN(tmp_path):
    # of_d/of_p (measured at MY hands, tip AND oracle): gcc types the
    # builtin unsigned long (sizeof 8) — blcc's SHIPPED constant arm types
    # it int (sizeof 4, tip-measured) and the dyn arm rides the same law.
    # Every kernel site is (char*)p - off BYTE arithmetic, so the value
    # observable is untouched (run-pairs above); named, retires with the
    # int-typing law, NOT silently patched under this wave.
    g = _gcc_rc(tmp_path, "wj2_t",
                "struct L { long a[2]; };\nint r(void){ return (int)"
                "sizeof(__builtin_offsetof(struct L, a[1])); }\n")
    assert g.returncode == 0
    r = _compile(tmp_path, "wj2_t",
                 "struct L { long a[2]; };\nint r(void){ return (int)"
                 "sizeof(__builtin_offsetof(struct L, a[1])); }\n"
                 "int main(void){ return r() == 4 ? 0 : 1; }\n")
    assert r.returncode == 0, "blcc's int-typing law pinned:\n" + r.stderr
