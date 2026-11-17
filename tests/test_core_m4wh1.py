"""M4 W-H COMMIT-1 (MC 12645) — __auto_type DECLARATION SPECIFIER.

THE MEASURED LAW (gcc 11.4 -std=gnu89, probes .tmp/m4-wh/probes/
at_probe.py + at_probe2.py — every leg below cites its measurement):

  `__auto_type ID = init;` declares ID with the type of `init` after
  VALUE CONVERSION (lvalue conversion): arrays DECAY to pointers,
  functions decay to function pointers, TOP-LEVEL qualifiers DROP,
  pointed-to qualifiers KEEP. That is where it DIVERGES from
  `__typeof__(init) ID = (init);` — typeof does NOT evaluate-convert:
  `__typeof__(ca) v` is the ARRAY int[4] (measured: sizeof(v)==16 arm
  rc 1 when the law says pointer), `__typeof__(ci) v; v = 7;` is rc 1
  (const kept) while the auto form is rc 0. blcc's mechanism: the SAME
  TypeOf node the §2.6 row rides, flagged `auto`, materialized through
  the ONE _untype with the value-conversion law on top.

  REJECT twins (all measured rc 1 on gcc): MISSING init; a second
  declarator (`= 1, b = 2`); a pointer/array declarator (`*v =`);
  `void` init (`variable or field declared void`); bit-field init
  (typeof of a bit-field). `auto_type` WITHOUT the underscores is not
  a keyword at all (did-you-mean twin). ACCEPT arms (all rc 0): file
  scope, `static`, statement expressions, ternary/comma/cast/compound-
  literal/string sources, `&v` of the auto variable.

  NAMED DIVERGENCE (SILENT-DIV pin, W-G precedent, self-flagged): the
  pointee-qualifier KEEP is a TYPE law blcc's one store law never
  enforced for ANY const path — `const int *p; *p = 7;` is tip-accepted
  TODAY (measured at e2d9c27: blcc rc 0 exit 7, gcc rc 1). The leg
  DIVERGENCE-PINS blcc's current shape; it is NOT approval — retirement
  rides the const-store class dying, never this wave.
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


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _pair(tmp_path, tag, src, e):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    g = subprocess.run(["gcc", "-std=gnu89", str(s), "-o",
                        str(tmp_path / (tag + ".g"))],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc: " + g.stderr
    b = blcc([str(s), "-o", str(tmp_path / (tag + ".b"))])
    assert b.returncode == 0, "blcc: " + b.stderr
    gv = subprocess.run([str(tmp_path / (tag + ".g"))],
                        capture_output=True).returncode
    bv = subprocess.run([str(tmp_path / (tag + ".b"))],
                        capture_output=True).returncode
    assert gv == e, "gcc gave {} expected {}".format(gv, e)
    assert bv == e, "blcc gave {} expected {}".format(bv, e)


def _loud(tmp_path, tag, src, needle=None):
    r = _compile(tmp_path, tag, src)
    assert r.returncode != 0, "must LOUD (measured gcc rc1 twin):\n" + src
    if needle is not None:
        assert needle in r.stderr, r.stderr
    return r


# ------------------------------------------------------ acceptance arms

def test_wh1_scalar_law_run_pair(tmp_path):
    # sizeof(v) is the init's type: 5L -> long 8, 1 -> int 4, 1UL -> 8,
    # (unsigned char)gi -> 1 (probe arms scalar-*/literal-*/cast-src).
    _pair(tmp_path, "wh1_sc",
          "long g(void){ __auto_type a = 5L; __auto_type b = 1;"
          " __auto_type c = 1UL; __auto_type d = (unsigned char)b;"
          " return (long)sizeof(a) * 1000 + sizeof(b) * 100"
          " + sizeof(c) * 10 + sizeof(d); }\n"
          "int main(void){ return (int)g(); }",   # 8481 % 256 = 33
          8481 % 256)


def test_wh1_array_decays_run_pair(tmp_path):
    # `ca` (int[4]) -> int*: sizeof 8 and p[1] READS the element — the
    # measured DIFFERENCE vs __typeof__(ca), which keeps int[4]
    # (array-eq-typof rc 1). Decay law + the array-eq-typof negative.
    _pair(tmp_path, "wh1_arr",
          "int ca[4];\nlong g(void){ ca[1] = 4; __auto_type p = ca;"
          " return p[1] * 10 + (long)sizeof(p); }\n"
          "int main(void){ return (int)g(); }",   # 48
          48)


def test_wh1_fn_decay_loud_defer(tmp_path):
    # NAMED DEFER (measured gcc rc 0, blcc LOUD): the auto law DECAYS
    # `foo` to pointer-to-function (sizeof 8 — the engine answers it
    # through the materialized type), but CALLING the variable rides
    # the §8 call gate, whose LIGHT mirror never materialized a TypeOf
    # node — pre-existing for `__typeof__(foo) f` too (measured at
    # e2d9c27: same LOUD sentence; the typeof form itself is gcc rc 1,
    # a function-TYPED var being invalid). Kernel census: the 406-row
    # __auto_type crowd is the scalar max()/min()/FIELD_MODIFY class —
    # 0 fn-typed auto sites. Retirement rides the call gate learning
    # to materialize TypeOf (W3 §8 gate owns it), not a second gate.
    r = _compile(tmp_path, "wh1_fn",
                 "long foo(void){ return 6; }\n"
                 "long g(void){ __auto_type f = foo; return f() +"
                 " (long)sizeof(f); }\n"
                 "int main(void){ return (int)g(); }")
    assert r.returncode != 0, (
        "when the call gate materializes TypeOf, FLIP this leg to the "
        "run-pair expect 14 (6 + 8)")
    assert "not a 'function'" in r.stderr, r.stderr


def test_wh1_top_qual_drops_run_pair(tmp_path):
    # qual-drop-assign rc 0 vs the typeof twin rc 1 (qual-keep-typof):
    # top-level const DROPS — v = 9 must COMPILE and run.
    _pair(tmp_path, "wh1_q",
          "const int ci = 7;\n"
          "long g(void){ __auto_type v = ci; v = 9; return v; }\n"
          "int main(void){ return (int)g(); }", 9)


def test_wh1_pointee_qual_divergence(tmp_path):
    # SILENT-DIV PIN (NOT approval): gcc rc 1 (`*v = 7` through the
    # const-pointed auto var); blcc's ONE store law never enforced a
    # const write for ANY path (tip measured: `const int *p; *p = 7;`
    # rc 0, exit 7). The auto law KEEPS the pointee const in the TYPE
    # (the law table); the write-guard is the pre-existing class.
    r = _compile(tmp_path, "wh1_pq",
                 "const int ci; const int *pci;\n"
                 "long g(void){ __auto_type v = pci; *v = 7; return ci; }\n")
    assert r.returncode == 0, (
        "retire this leg together with the const-store class, not "
        "before:\n" + r.stderr)


def test_wh1_stmt_expr_run_pair(tmp_path):
    # The corpus SHAPE: `({...})` with auto locals (stmt-expr rc 0):
    _pair(tmp_path, "wh1_se",
          "long g(void){ return ({ __auto_type t = 2L; t * 3; }); }\n"
          "int main(void){ return (int)g(); }", 6)


def test_wh1_file_scope_run_pair(tmp_path):
    # file-scope rc 0 (probe file-scope/file-static): data-layer mirror
    # materializes the auto type exactly like the `static __typeof__`
    # row it already rides (data.py §2.6).
    _pair(tmp_path, "wh1_fs",
          "__auto_type gx = 5L;\n"
          "int main(void){ return (int)gx; }", 5)


def test_wh1_static_local_run_pair(tmp_path):
    # block-static rc 0 — the §1c static-local constant law applies to
    # the MATERIALIZED type (5L -> long, constant init required):
    _pair(tmp_path, "wh1_sl",
          "int main(void){ static __auto_type v = 7L; return (int)v; }", 7)


def test_wh1_kernel_class_run_pair(tmp_path):
    # The ktime/jiffies class END-TO-END: the auto var feeds typeof
    # casts and sizeof EXACTLY as __careful_cmp_once's signedness test
    # does (stream init_main.c.i:14433 pattern in miniature):
    _pair(tmp_path, "wh1_kc",
          "long g(long delta){ __auto_type x_56 = (0L);"
          " __auto_type y_57 = (delta);"
          " return (long)(sizeof(typeof(x_56)) * 10"
          " + (int)(((typeof(y_57))(-1)) < ((typeof(y_57))1))"
          " * ((x_56) > (y_57) ? 0 : 1)); }\n"
          "int main(void){ return (int)(g(3) * 10 + g(-5)); }",
          # g(3): 80 + 1*(0>3? no ->1) = 81 ; g(-5): 80 + 1*(0>-5? yes ->0)
          # = 80 -> 81*10 + 80 = 890 -> 890 % 256 = 122
          890 % 256)


def test_wh1_addr_of_run_pair(tmp_path):
    # and-of-auto rc 0: &v is a long* over the DECLARED object:
    _pair(tmp_path, "wh1_ad",
          "int main(void){ __auto_type v = 40L; long *p = &v;"
          " *p += 2; return (int)v; }", 42)


def test_wh1_tern_init_run_pair(tmp_path):
    # tern rc 0: the conditional's COMMON type (long) is the auto type:
    _pair(tmp_path, "wh1_tn",
          "int gi = 1;\nlong g(void){ __auto_type v = gi ? 10L : 2L;"
          " return (long)sizeof(v) + v; }\n"
          "int main(void){ return (int)g(); }", (8 + 10) % 256)


def test_wh1_strlit_run_pair(tmp_path):
    # strlit rc 0: char[3] decays to char*; the literal bytes are the
    # object (string-initializer law NOT entered — the literal lives):
    _pair(tmp_path, "wh1_st",
          "int main(void){ __auto_type s = \"ab\"; return s[1]; }",
          ord("b"))


def test_wh1_clit_array_run_pair(tmp_path):
    # arr-clit rc 0: (int[]){...} -> pointer to the literal object:
    _pair(tmp_path, "wh1_cl",
          "long g(void){ __auto_type p = (int[]){1,2,3};"
          " return p[2] * 10 + (long)sizeof(p); }\n"
          "int main(void){ return (int)g(); }", 38)


# ---------------------------------------------------------- reject arms

def test_wh1_two_declarators_loud(tmp_path):
    # two-decls rc 1 (gcc verbatim: '__auto_type' may only be used with
    # a single declarator):
    _loud(tmp_path, "wh1_2d",
          "int main(void){ __auto_type a1 = 1, b1 = 2L; return a1; }",
          "may only be used with a single declarator")


def test_wh1_missing_init_loud(tmp_path):
    # no-init rc 1 (gcc verbatim: '__auto_type' requires an initialized
    # data declaration) — the type comes from the initializer or nowhere:
    _loud(tmp_path, "wh1_ni", "int main(void){ __auto_type v; return 0; }",
          "requires an initialized data declaration")


def test_wh1_pointer_declarator_loud(tmp_path):
    # ptr-decl rc 1 (gcc verbatim: '__auto_type' requires a plain
    # identifier as declarator) — `*v =` is NOT pointer-to-inferred:
    _loud(tmp_path, "wh1_pd",
          "int *q; int main(void){ __auto_type *v = q; return 0; }",
          "requires a plain identifier as declarator")


def test_wh1_array_declarator_loud(tmp_path):
    # the array-form twin of the pointer arm (measured rc 1, SAME gcc
    # sentence as the pointer arm):
    _loud(tmp_path, "wh1_ad2",
          "int main(void){ __auto_type v[2] = 5; return 0; }",
          "requires a plain identifier as declarator")


def test_wh1_void_init_loud(tmp_path):
    # void-init rc 1 `variable or field declared void`:
    r = _loud(tmp_path, "wh1_vi",
              "void fv(void); int main(void){ __auto_type v = fv();"
              " return 0; }")
    assert "declared void" in r.stderr, r.stderr


def test_wh1_bitfield_init_loud(tmp_path):
    # bitfield rc 1 (gcc verbatim: '__auto_type' used with a bit-field
    # initializer): the member has no value-convertible type of its own
    # (typeof of a bit-field is the same refusal):
    _loud(tmp_path, "wh1_bf",
          "struct BF{ int x : 3, y : 29; } gb;\n"
          "int main(void){ __auto_type v = gb.x; return 0; }",
          "used with a bit-field initializer")


def test_wh1_block_extern_fn_decl(tmp_path):
    # The jiffies-class SECOND wall (measured at tip e2d9c27, PRE-
    # EXISTING false-LOUD): every __cmp/__careful_cmp_once signedness
    # check opens `do { extern void __compiletime_assert_NN(void)
    # __attribute__((__error__("..."))); ... } while (0)` — a
    # BLOCK-SCOPE FUNCTION DECLARATION, which tip answered `sema:
    # cannot emit statement` (statement dispatch had no FuncDecl arm;
    # the parser HAD already defined the name). gcc rc 0. With the
    # declaration emitting nothing (it declares, defines nothing) the
    # verbatim jiffies line and a same-shape run-pair both pass.
    r = _compile(tmp_path, "wh1_be",
                 "int main(void){ do { extern void ff(void);"
                 " if (0) ff(); } while (0); return 3; }")
    assert r.returncode == 0, (
        "block-scope extern fn decl must emit NOTHING (name already "
        "declared; gcc rc 0):\n" + r.stderr)
    _pair(tmp_path, "wh1_be2",
          "int ff(void){ return 4; }\n"
          "int g(void){ extern int ff(void); return ff(); }\n"
          "int main(void){ return g(); }", 4)


def test_wh1_bare_word_not_keyword(tmp_path):
    # auto-type-word rc 1: `auto_type` (no underscores) is an ordinary
    # identifier — `auto_type v = 5;` is NOT this specifier:
    _loud(tmp_path, "wh1_bw", "int main(void){ auto_type v = 5; return 0; }")
