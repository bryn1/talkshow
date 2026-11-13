"""M35/M51 `_Generic` (§1 row 6e, §2.6 MEASURED selection table) +
`__builtin_types_compatible_p` (§2.12 IDENTITY FOLD, 24-leg table subset)
— MC 12460. gcc 11.4 -std=gnu89 is the oracle for every leg; error legs
mirror the gcc sentences. fnptr-key/decl is M4 (function pointers DEFER):
its leg pins blcc stays LOUD, never silent-accepts.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itgen")


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))


def both_run(src, tag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b], cwd=ROOT, capture_output=True, text=True,
                        timeout=60)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build: " + rg.stderr
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


def _loud(src, tag, frag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path,
                        "-o", p + ".out"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert r.returncode == 2, \
        "{}: expected LOUD (exit 2), got {} stderr={!r}".format(
            tag, r.returncode, r.stderr)
    assert frag in r.stderr, "{}: stderr must name {!r}: {}".format(
        tag, frag, r.stderr)
    assert not os.path.exists(p + ".out"), "rejected input emitted a binary"


# ---- M35/M51: selection table legs (§2.6d, every `measured` value) ---------

def test_scalar_keys_run_pair():
    both_run("int main(void){ int v = _Generic(1, int: 11, long: 22, "
             "default: 33); if (v != 11) return 1; "
             "v = _Generic(1L, int: 11, long: 22, default: 33); "
             "if (v != 22) return 2; "
             "v = _Generic(1LL, long: 1, default: 7); if (v != 7) "
             "return 3;                      /* default used: LL != long  */"
             " v = _Generic(1L, long: 1, default: 0); if (v != 1) return 4;"
             "                       /* compatible assoc beats default    */"
             " return 0; }\n", "g-scalar")


def test_struct_key_run_pair():
    both_run("struct S{int a;};\nint main(void){ struct S s; int v = "
             "_Generic(s, struct S: 1, default: 0); if (v != 1) return 1; "
             "return 0; }\n", "g-structkey")


def test_typedef_struct_deref_key_run_pair():
    # __seqprop (seqlock.h:302) shape: `_Generic(*(s), seq_t_: …)` with s
    # a pointer — the deref control + typedef-struct key, measured 11.
    both_run("typedef struct { int c; } seq_t_;\n"
             "int probe(seq_t_ *s){ return _Generic(*s, seq_t_: 11, "
             "default: 22); }\n"
             "int main(void){ seq_t_ x; if (probe(&x) != 11) return 1; "
             "return 0; }\n", "g-seqprop")


def test_call_arms_selected_only_run_pair():
    # arms that are CALLS; the untaken arm must NOT run (99-side-effect
    # never fires) and must not be analyzed (§2.6d measured 11).
    both_run("typedef struct { int c; } seq_t_;\n"
             "int ran_nosel;\nint call_sel(void){ return 11; }\n"
             "int call_nosel(void){ ran_nosel = 99; return 22; }\n"
             "int main(void){ seq_t_ s; int v = _Generic(s, seq_t_: "
             "call_sel(), default: call_nosel()); if (v != 11) return 1; "
             "if (ran_nosel != 0) return 2; return 0; }\n", "g-callarm")


def test_array_key_never_matches_run_pair():
    # §2.6d: array control is ADJUSTED (array→pointer) before selection —
    # an `int[4]:` key never matches; the default arm runs (measured 8).
    both_run("int main(void){ int a4[4]; int v = _Generic(a4, int[4]: 7, "
             "default: 8); if (v != 8) return 1; return 0; }\n", "g-arrkey")


def test_qualified_key_never_matches_run_pair():
    # §2.6d: a `const int:` key matches NEITHER the const control (44)
    # nor the plain control (44) — key qualifiers ARE significant here.
    both_run("int main(void){ int i; const int ci = 1; int v = "
             "_Generic(ci, const int: 33, default: 44); if (v != 44) "
             "return 1; v = _Generic(i, const int: 33, default: 44); "
             "if (v != 44) return 2; return 0; }\n", "g-qualkey")


def test_const_control_plain_key_matches_run_pair():
    # control loses qualifiers on lvalue conversion; plain `int:` wins (33)
    both_run("int main(void){ const int ci = 1; int v = _Generic(ci, "
             "int: 33, default: 44); if (v != 33) return 1; return 0; }\n",
             "g-conctl")


def test_generic_dead_arm_not_analyzed_run_pair():
    # gcc 11.4 session-probe: `default: undeclared_fn()` COMPILES (arm
    # unanalyzed, gnu89 implicit-decl is a warning class); the lenient
    # window is the same one choose_expr uses.
    both_run("int main(void){ int v = _Generic(1, int: 1, default: "
             "undeclared_fn()); if (v != 1) return 1; return 0; }\n",
             "g-deadarm")


def test_dup_assoc_loud():
    # gcc sentence: `'_Generic' specifies two compatible types` (probe).
    _loud("struct S{int a;};\nint main(void){ struct S s; return _Generic"
          "(s, struct S: 1, struct S: 2); }\n", "g-dup",
          "two compatible types")


def test_no_match_no_default_loud():
    # §2.6d gcc sentence: `not compatible with any association`.
    _loud("int main(void){ float f; return _Generic(0.0f, int: 1); }\n",
          "g-nomatch", "not compatible with any association")


def test_fnptr_key_stays_loud_m4():
    # §1 row 16: function pointers are M4. The key type `int(*)(void)`
    # (and the control's decl) must keep a LOUD wall — never silent.
    _loud("int g(void){return 0;}\nint main(void){ int (*fp)(void); "
          "return _Generic(fp, int(*)(void): 5, default: 6); }\n",
          "g-fnptr", "function pointer")


# ---- §2.12 types_compatible_p identity fold -------------------------------

def test_types_compatible_identity_run_pair():
    both_run(r"""
typedef long off_t;
struct A { int x; };
struct B { int x; };
int main(void) {
    if (__builtin_types_compatible_p(int, int) != 1) return 1;
    if (__builtin_types_compatible_p(int, signed int) != 1) return 2;
    if (__builtin_types_compatible_p(off_t, long) != 1) return 3;
    if (__builtin_types_compatible_p(int *, int *) != 1) return 4;
    if (__builtin_types_compatible_p(int, const int) != 1) return 5;   /* measured 1: TOP-LEVEL quals IGNORED */
    if (__builtin_types_compatible_p(int[4], int[4]) != 1) return 6;
    if (__builtin_types_compatible_p(struct A, struct A) != 1) return 7;
    if (__builtin_types_compatible_p(void, void) != 1) return 8;
    if (__builtin_types_compatible_p(long long, long long) != 1) return 9;
    if (__builtin_types_compatible_p(char, unsigned char) != 0) return 10;
    if (__builtin_types_compatible_p(char, signed char) != 0) return 11;  /* char is its OWN type (measured 0) */
    if (__builtin_types_compatible_p(int, unsigned int) != 0) return 12;
    if (__builtin_types_compatible_p(int, long) != 0) return 13;
    if (__builtin_types_compatible_p(int *, const int *) != 0) return 14; /* pointee qual NOT top-level */
    if (__builtin_types_compatible_p(int *, void *) != 0) return 15;
    if (__builtin_types_compatible_p(int[4], int *) != 0) return 16;
    if (__builtin_types_compatible_p(int[4], int[5]) != 0) return 17;
    if (__builtin_types_compatible_p(struct A, struct B) != 0) return 18; /* nominal by TAG */
    if (__builtin_types_compatible_p(void, int) != 0) return 19;
    if (__builtin_types_compatible_p(long long, unsigned long long) != 0) return 20;
    return 0;
}
""", "tcompat")


def test_same_type_shape_run_pair():
    # compiler_types.h:250 __same_type — typeof-args through the fold.
    both_run("int main(void){ int a; long b; if (__builtin_types_"
             "compatible_p(__typeof__(a), int) != 1) return 1; if "
             "(__builtin_types_compatible_p(__typeof__(b), int) != 0) "
             "return 2; return 0; }\n", "tsame")
