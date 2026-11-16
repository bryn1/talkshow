# LINES reason: one wave of legs (M4 W3 COMMIT-0 — the implicit-builtin
# RE-DECLARATION law, plan-m4 v4 §7 AMENDMENT-4, MC 12563) — the accept
# arms, the LOUD twins and the winner law are ONE measured evidence set.
r"""M4 W3 COMMIT-0 — builtin RE-DECLARATION law (kernel strlen/strcmp family).

MEASURED GCC 11.4 gnu89 LAW (this card, .tmp/m4-w3/out/probe*.py + t*.c):
  ACCEPT rc0: a file-scope FUNCTION prototype that re-declares an implicit
  builtin with the SAME NAMED arity — `size_t strlen(const char *s);`
  (string_64.h:62, ×179 first-blockers), `int strcmp(const char *, const
  char *);` (boot.h:338 / linux/string.h, ×21), the `extern` spelling
  (boot/string.h ×10), a compatible repeat (param NAMES differ → same),
  the old-style empty-paren `size_t strlen();`, the DEFINITION form
  (lib/string.c shape rc0; `.data`-law: nm answers `T strlen` == gcc).
  A scalar/qualifier ARG-TYPE or RETURN-TYPE difference is rc0 + a
  -Wbuiltin-declaration-mismatch WARNING — blcc has no warning channel:
  rc0 with the USER prototype deciding (the winner row).
  THE WINNER: the user prototype wins the CALL TYPE — measured -O0 -fno-pic
  `extern int strlen(const char*); long g(){return strlen(s);}` carries the
  int→long sign-extend (cltq); `long strlen` does NOT. A re-declared
  builtin therefore TYPES from the user's prototype, never the builtin
  table (the §2.17 "a user declaration wins" law generalized).
  LOUD (gcc rc1 twins): ARITY mismatch (`int strlen(const char *, int);`
  error "conflicting types for built-in function"); a NON-FUNCTION symbol
  of a builtin name (typedef/var) keeps the shipped §6 sentence; static
  re-decl (static-after-extern rc1; static-FIRST rc0-warn corpus volume 0
  — LOUD stays, NAMED row); a use of a void-returning re-decl rc1 (the
  SHIPPED void-value law answers, no new arm).
  GENERAL fn-vs-fn re-declaration (every name, builtin or not): gcc rc1
  "conflicting types" for a concrete parameter-list or return clash;
  compatible spellings merge rc0 (param names ignored, array-of-T param
  == pointer-to-T (measured rc0), TOP-LEVEL param quals ignored, the
  empty-paren list is a PARAM wildcard but the RETURN still must match
  (`void f(); long f(int);` rc1 measured)). A non-builtin name collision
  stays a LOUD twin leg — the accept law is NEVER blanket-permissive.
  BLOB row (blcc-side, §6): the link-mode RUNTIME_ASM blob OWNS the builtin
  names; a user DEFINITION + link mode = rc2 LOUD NAMING the builtin
  (gcc rc0 — LOUD-DIV, kernel universe is `-c`-only, volume 0). The
  sealed test_redeclare_builtin_is_loud stays GREEN through this guard
  (same rc2, same literal name).
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


def compile_rc(tmp_path, tag, src, tool):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ("bgcc.o" if tool is gcc else "blcc.o"))
    r = tool(["-c", str(s), "-o", str(o)])
    return r, o


T = "typedef unsigned long size_t;\n"


# ---- ACCEPT arms (kernel corpus shapes, verbatim spellings) --------------

def test_strlen_proto_redecl_accepted(tmp_path):
    src = (T + "size_t strlen(const char *s);\n"
           "size_t g(const char *s) { return strlen(s); }\n")
    gr, _ = compile_rc(tmp_path, "sl0", src, gcc)
    br, _ = compile_rc(tmp_path, "sl0", src, blcc)
    assert gr.returncode == 0, gr.stderr          # oracle accepts
    assert br.returncode == 0, br.stderr           # law: accept too


def test_strcmp_pair_verbatim_accepted(tmp_path):
    # the two real spellings, in ONE TU (string_64.h + linux/string.h):
    src = (T + "int strcmp(const char *cs, const char *ct);\n"
           "extern int strcmp(const char *, const char *);\n"
           "int g(const char *a, const char *b){ return strcmp(a, b); }\n")
    gr, _ = compile_rc(tmp_path, "cp0", src, gcc)
    br, _ = compile_rc(tmp_path, "cp0", src, blcc)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


def test_extern_strlen_spelling_accepted(tmp_path):
    # boot/string.h:21 form (×10 in-corpus): the `extern` spelling
    src = (T + "extern size_t strlen(const char *s);\n"
           "size_t g(const char *s){ return strlen(s); }\n")
    gr, _ = compile_rc(tmp_path, "ex0", src, gcc)
    br, _ = compile_rc(tmp_path, "ex0", src, blcc)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


def test_empty_paren_builtin_redecl_accepted(tmp_path):
    # measured rc0: the old-style empty list re-declares (NO parameter
    # information — distinct from `(void)`, which says ZERO; the W1
    # call-arity law for an old-style declaration is the SHIPPED pre-W3
    # posture, untouched here — the leg tests the re-declaration wall).
    src = T + "size_t strlen();\nsize_t strlen(const char *s);\n"
    gr, _ = compile_rc(tmp_path, "ep0", src, gcc)
    br, _ = compile_rc(tmp_path, "ep0", src, blcc)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


def test_undeclared_builtin_call_unchanged(tmp_path):
    # fairness leg: the §6 blob posture WITHOUT any declaration survives
    src = T + "size_t g(const char *s){ return strlen(s); }\n"
    gr, _ = compile_rc(tmp_path, "fc0", src, gcc)
    br, bo = compile_rc(tmp_path, "fc0", src, blcc)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr
    out = subprocess.run(["nm", "-u", str(bo)], capture_output=True, text=True)
    assert "strlen" in out.stdout                  # U strlen, blob-side


# ---- THE WINNER law (measured): user prototype wins the call type --------

def _plain_int_sign_ext(tmp_path, fname):
    # The SHIPPED value-conversion law (measured tip): blcc carries `int`
    # in a FULL 64-bit register (no narrow reintern) — `int i; long y=i;`
    # compiles to a plain movq, NO sign-extend, on the pre-W3 tip too.
    # So the winner evidence is the int→long ASSIGNMENT context, where
    # the user prototype must be the SOURCE of the conversion (without the
    # winner flip the builtin table says `long` and no int is involved).
    s = tmp_path / (fname + ".c")
    s.write_text("extern int foo(void);\nlong g(void){ long y = foo(); "
                 "return y != 0; }\n")
    r = blcc(["--emit-asm", "-c", str(s), "-o", str(tmp_path / (fname + ".b"))])
    return r.stdout


def test_winner_user_arity_beats_builtin_table(tmp_path):
    # THE winner evidence in blcc's full-register law (measured: blcc
    # interns `int` in %rax with NO re-narrowing — the sign-extend twin
    # is a gcc-only shape): a re-declared builtin ARIETIES from the USER
    # prototype. The §6 table (strlen 1, strcmp 2) would answer LOUD at
    # every shape below; gcc rc0 answers clean (declaration + call).
    for tag, src in [
        ("s2", T + "extern int strlen(const char *, int);\n"
               "size_t f(const char *s){ return strlen(s, 1); }\n"),
        ("c1", T + "extern long strcmp(const char *);\n"
               "size_t f(const char *s){ return strcmp(s); }\n"),
    ]:
        gr, _ = compile_rc(tmp_path, "wn" + tag, src, gcc)
        br, _ = compile_rc(tmp_path, "wn" + tag, src, blcc)
        assert gr.returncode == 0, (tag, gr.stderr)
        assert br.returncode == 0, (tag, "user prototype must win:\n"
                                         + br.stderr)


def test_void_ret_use_is_a_silent_div_row(tmp_path):
    # MEASURED row, NOT a new arm: a `void`-returning re-decl whose value
    # is used is gcc rc1 ("void value not ignored"); blcc's SHIPPED law
    # has no void-value gate on -c at all (`extern int f(void); long
    # g(void){ (void)f(); return f(); }` answers rc0 at tip too) — a
    # pre-W3 SILENT-DIV class with kernel corpus volume 0 (the kernel
    # never calls a void fn for its value: it could not compile). This
    # row NAMED it; commit-0 does not silently fix or newly LOUDen it.
    src = (T + "extern void strlen(const char *);\n"
           "long f(const char *s){ return strlen(s); }\n")
    gr, _ = compile_rc(tmp_path, "vr0", src, gcc)
    br, _ = compile_rc(tmp_path, "vr0", src, blcc)
    assert gr.returncode == 1, gr.stderr
    assert br.returncode == 0, br.stderr    # SILENT-DIV row (volume 0)


def test_declared_strlen_value_is_data_ref(tmp_path):
    # R8/§6: a declared builtin used as a VALUE rides the W2 fn-value law
    # (movq $strlen, R_X86_64_32S), never a new undefined name.
    src = (T + "size_t strlen(const char *s);\n"
           "size_t (*fp)(const char *) = strlen;\n")
    s = tmp_path / "vd0.c"
    s.write_text(src)
    go = tmp_path / "vd0.gcc.o"
    gr = gcc(["-fno-pic", "-c", str(s), "-o", str(go)])
    assert gr.returncode == 0, gr.stderr
    bo = tmp_path / "vd0.blcc.o"
    br = blcc(["-c", str(s), "-o", str(bo)])
    assert br.returncode == 0, br.stderr
    for o in (go, bo):
        txt = subprocess.run(["readelf", "-r", str(o)],
                             capture_output=True, text=True).stdout
        assert re.search(r"R_X86_64_64\s+\S+\s+strlen \+ 0", txt), \
            "{}: the .data initializer must carry R_X86_64_64 strlen " \
            "(measured: identical both sides under the kernel recipe)".format(o)
        uu = subprocess.run(["nm", str(o)],
                            capture_output=True, text=True).stdout
        assert " D fp" in uu and " U strlen" in uu


# ---- LOUD twins (gcc rc1) -------------------------------------------------

def test_builtin_arity_clash_is_warning_only(tmp_path):
    # MEASURED (probe5): the DECL-ALONE arms of a builtin re-declaration
    # are rc0 + warning EVEN when the arity or the return kind clashes —
    # the rc1s arrive at the USE SITE. blcc accepts the declarations; the
    # shipped call-arity / void-value law answers the use sites LOUD.
    decl = (T + "extern int strlen(const char *, int);\n")
    gr, _ = compile_rc(tmp_path, "am0", decl, gcc)
    br, _ = compile_rc(tmp_path, "am0", decl, blcc)
    assert gr.returncode == 0 and br.returncode == 0, (gr.stderr, br.stderr)
    for tag, src in [
        ("few", T + "extern int strlen(const char *, int);\n"
               "size_t f(const char *s){ return strlen(s); }\n"),
    ]:
        gr, _ = compile_rc(tmp_path, "am" + tag, src, gcc)
        br, _ = compile_rc(tmp_path, "am" + tag, src, blcc)
        assert gr.returncode == 1, tag + ": oracle use-site must error"
        assert br.returncode == 2, tag + ": use-site LOUD:\n" + br.stderr


def test_static_after_nonstatic_loud(tmp_path):
    # MEASURED: static-FIRST of a builtin is rc0-warn (volume 0 in the
    # corpus, measured grep — zero `static ... strlen(` decls in 706
    # streams), but STATIC AFTER a non-static declaration is a hard gcc
    # rc1 for EVERY name, builtin or not. blcc LOUDs on the rc1 arm.
    src = (T + "size_t strlen(const char *s);\n"
           "static size_t strlen(const char *);\n")
    gr, _ = compile_rc(tmp_path, "st0", src, gcc)
    br, _ = compile_rc(tmp_path, "st0", src, blcc)
    assert gr.returncode == 1, gr.stderr
    assert br.returncode == 2
    assert "strlen" in br.stderr
    gen = "extern void zap(void);\nstatic void zap(void);\n"
    gr, _ = compile_rc(tmp_path, "st1", gen, gcc)
    br, _ = compile_rc(tmp_path, "st1", gen, blcc)
    assert gr.returncode == 1, gr.stderr
    assert br.returncode == 2 and "zap" in br.stderr, br.stderr


def test_typedef_of_builtin_name_stays_loud(tmp_path):
    # MEASURED: gcc accepts a TYPEDEF of a builtin name rc0 (typedefs are
    # not function re-declarations; USE as a callable is rc1
    # "called object type … is not a function"). blcc keeps the shipped
    # §6 sentence for the typedef spelling — a NAMED LOUD-DIV arm, corpus
    # volume 0 (measured grep: no `typedef … strlen/strcmp` in 706
    # streams). The law is stricter HERE and that is the shipped posture.
    src = T + "typedef int strlen;\n"
    gr, _ = compile_rc(tmp_path, "td0", src, gcc)
    br, _ = compile_rc(tmp_path, "td0", src, blcc)
    assert gr.returncode == 0, gr.stderr    # the measured oracle
    assert br.returncode == 2 and "strlen" in br.stderr, br.stderr
    use = T + "typedef int strlen;\nstrlen q;\nint m(void){ return strlen(q); }\n"
    gr, _ = compile_rc(tmp_path, "td1", use, gcc)
    assert gr.returncode == 1, gr.stderr    # use-site: oracle rc1


# ---- general fn-vs-fn re-declaration law (non-builtin twin leg) ----------

def test_nonbuiltin_conflict_stays_loud(tmp_path):
    # THE not-blanket-permissive twin: a NON-builtin name collision is a
    # gcc rc1 "conflicting types" error — blcc LOUDs too (measured tip:
    # blcc rc0 SILENT — this leg is the planted RED this commit closes).
    for tag, src in [
        ("ret", "int foo(const char *);\nlong foo(const char *);\n"),
        ("par", "void bar(const char *);\nvoid bar(char *);\n"),
        ("emp", "void qux();\nlong qux(int a);\n"),     # ret clash rc1
        ("vpr", "void zap(void);\nvoid zap(int);\n"),   # concrete clash
    ]:
        gr, _ = compile_rc(tmp_path, "nb" + tag, src, gcc)
        br, _ = compile_rc(tmp_path, "nb" + tag, src, blcc)
        assert gr.returncode == 1, "oracle must error on " + tag
        assert br.returncode == 2, \
            "non-builtin name collision must stay LOUD (" + tag + "): " \
            + repr(src)


def test_compatible_redecl_merges(tmp_path):
    # param names differ; array-of-T param == pointer-to-T (measured rc0)
    for tag, src in [
        ("nm", "int foo(const char *a);\nint foo(const char *b);\n"),
        ("ar", "void f(int a[]);\nvoid f(int *a);\n"),
        ("emp", "int g();\nint g(int a);\n"),
        ("def", "size_t ff(const char *s);\nsize_t ff(const char *s)"
                " { return 0; }\n".replace("size_t", "long")),
    ]:
        gr, _ = compile_rc(tmp_path, "ok" + tag, src, gcc)
        br, _ = compile_rc(tmp_path, "ok" + tag, src, blcc)
        assert gr.returncode == 0, gr.stderr
        assert br.returncode == 0, (tag, br.stderr)


# ---- the DEFINITION arm: -c accepts (T parity), link LOUD-names the blob -

STRLEN_DEF = (T + "size_t strlen(const char *s)\n{\n    size_t n = 0;\n"
              "    while (s[n]) n++;\n    return n;\n}\n"
              "size_t g(const char *s){ return strlen(s); }\n")


def test_def_arm_c_t_parity(tmp_path):
    s = tmp_path / "df0.c"
    s.write_text(STRLEN_DEF)
    go = tmp_path / "df0.gcc.o"
    gr = gcc(["-fno-pic", "-c", str(s), "-o", str(go)])
    assert gr.returncode == 0, gr.stderr
    bo = tmp_path / "df0.blcc.o"
    br = blcc(["-c", str(s), "-o", str(bo)])
    assert br.returncode == 0, br.stderr           # -c: blob absent, def wins
    gn = subprocess.run(["nm", "--defined-only", str(go)],
                        capture_output=True, text=True).stdout
    bn = subprocess.run(["nm", "--defined-only", str(bo)],
                        capture_output=True, text=True).stdout
    assert re.search(r"\bT strlen\b", gn) and re.search(r"\bT strlen\b", bn), \
            "T strlen both sides:\n" + gn + "\n--\n" + bn


def test_def_arm_link_blob_loud(tmp_path):
    # link mode: the §6 blob OWNS strlen → rc2 LOUD NAMING the builtin.
    # (gcc rc0 — NAMED LOUD-DIV; kernel universe is -c-only, volume 0.
    # The sealed test_redeclare_builtin_is_loud rides THIS same posture.)
    s = tmp_path / "df1.c"
    s.write_text(STRLEN_DEF + "int main(void){ return (int)strlen(\"ab\"); }\n")
    gx = tmp_path / "df1.gcc"
    gr = gcc([str(s), "-o", str(gx)])
    assert gr.returncode == 0, gr.stderr           # oracle links fine
    bx = tmp_path / "df1.blcc"
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 2, br.stderr
    assert "strlen" in br.stderr
    assert not bx.exists(), "a diagnostic leaves NOTHING at -o"


# ---- corpus legs: the 200-family first-blockers fall ----------------------

def _clean_i(path, tmp_path, tag):
    """m3 corpus idiom: elide linemarkers, erase literal suffixes."""
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


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", [
    "arch_x86_boot_a20.c.i",                  # strcmp first (boot.h:338)
    "arch_x86_boot_compressed_pgtable_64.c.i",  # strlen first (string_64.h)
    "arch_x86_entry_vdso_vdso-image-64.c.i",  # strlen witness
    "arch_x86_boot_string.c.i",               # boot tier, strlen family
])
def test_corpus_builtin_redecl_wall_is_dead(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "corpw3")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "corpw3.o")])
    assert "cannot re-declare the implicit builtin" not in r.stderr, \
        "{} still hits the builtin re-decl wall:\n{}".format(
            stream, r.stderr[:600])
