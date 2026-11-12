r"""Regressions for the M1-c5 fix cycle (MC 12454, card 12404.2.15).
EVERY expectation below was measured against the live oracle (gcc 11.4 -E)
THIS session before being pinned — never from blcc. RED-first evidence:
/home/claudecode/Blaha/.tmp/evidence/m1-fix-c5-red.log (all these shapes
failing on b8a3efe pre-fix).

F-A (verdict-c3, P1 SILENT): object-like `##` paste was never executed.
`#define Q X##Y` + `int Q;` -> gcc `int XY;`, shipped blcc `int X##Y;`,
both rc 0. The object-like path spliced the body RAW into the rescan stream
instead of routing it through `_substitute`, so (a) no paste happened and
(b) the rescan prescan-expanded the ##-operands before any join could
(C11 6.10.3.4 keeps them RAW, joins them, THEN expands the result).
linux-5.10 uses object-like ## nowhere (whole-tree grep: 0 — both apparent
hits are "#####" inside string literals), so this class is corpus-invisible
by construction; the shipped suite had ZERO object-like ## rows.

Oracle matrix measured this card (gcc 11.4 -E, every rc re-read without a
pipe) — pinned by the rows below:
  quiet joins:  X##Y##Z -> XYZ;  5##b -> 5b;  0x##1 -> 0x1;  _##x -> _x;
                &##& -> &&;  +##+ -> ++;  -##> -> ->;  1.5##z -> 1.5z;
                X## ##Y -> XY (duplicated ## collapses against the SAME
                left operand); `in##t` prints `int` and gcc -c accepts it
                (the pasted token IS a keyword at parse time).
  RAW operands: `#define a a##b` + `#define b 7` -> `ab` (NOT `a##7`);
                `#define A X` + `#define Q A##B` -> `AB` (never `XY`);
                `__LINE__##_tag` -> `__LINE___tag`; both __LINE__ ->
                `__LINE____LINE__`; a function-like ##-adjacent operand
                that is an object-like paste macro stays RAW (`O##z`->`O1`).
  result rescan: `#define ab 5` + `#define a a##b` -> `5`;  a paste-built
                head calls a following function-like macro (`G(z) z##1` +
                `#define C G(a)` -> `a1`); `_Pragma` produced by paste IS
                processed (`_##Pragma` -> the pragma is emitted).
  LOUD (rc != 0, oracle): `##` at either end of a body (define-time,
                "'##' cannot appear at either end of a macro expansion");
                invalid join (expansion-time, "pasting '+' and '-' does
                not give a valid preprocessing token") — `%##-`, `+##-`,
                `##` between `,` and a PLAIN parameter;  while the GNU
                `, ## __VA_ARGS__` idiom with a NON-empty tail stays QUIET
                (rmwcc.h, 1309 sites in 5.10) — the matrix pair is pinned.
  Spacing (cpp space_needed): expansion-adjacent tokens never print glued:
                `CAT(pr,i)ntf` prints `pri ntf`, `<`+`<` prints `< <`,
                `/`+`*` prints `/ *` (gcc-measured); source whitespace and
                `1/2` stay untouched.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_pp_differential_m1 import norm, PINS     # noqa: E402  (SHIPPED)


def gcc_run(args):
    return subprocess.run(["gcc", "-E"] + args, capture_output=True,
                          text=True, timeout=120)


def blcc_run(args):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc", "-E"] + args,
                          capture_output=True, text=True, timeout=120,
                          env=env)


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)


def diff_snippet(tmp_path, src, extra=(), fname="t.c"):
    """Both sides on identical argv; both exit 0; token streams equal."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode == 0, "gcc failed: %s" % g.stderr
    assert b.returncode == 0, "blcc failed: %s" % b.stderr
    assert norm(b.stdout) == norm(g.stdout), \
        "token mismatch:\n blcc: %r\n gcc:  %r" % (norm(b.stdout)[:80],
                                                   norm(g.stdout)[:80])
    return b.stdout, b


def loud_pair(tmp_path, src, class_txt, fname="t.c"):
    """Oracle LOUD: both sides rc != 0, both name the same diagnostic
    class (rc 1 = gcc, rc 2 = blcc's pp-fatal; class = message text)."""
    path = write(tmp_path, fname, src)
    g = gcc_run([path] + PINS)
    b = blcc_run([path] + PINS)
    assert g.returncode != 0 and class_txt in g.stderr, \
        "oracle not loud: rc=%d %s" % (g.returncode, g.stderr[:200])
    assert b.returncode != 0 and class_txt in b.stderr, \
        "blcc not loud: rc=%d %s" % (b.returncode, b.stderr[:200])


# ---------------------------------------------- F-A: object-like ## paste --


def test_object_paste_minimal(tmp_path):
    """THE F-A repro (verdict-c3, v8): `#define Q X##Y` + `int Q;` ->
    `int XY;`. Pre-fix blcc printed `int X##Y;` at rc 0 (SILENT)."""
    _, b = diff_snippet(tmp_path, "#define Q X##Y\nint Q;\n")
    assert "XY" in norm(b.stdout)


def test_object_paste_self_head_and_tail(tmp_path):
    """v1/v2: `#define a a##b` + `int a;` -> `int ab;`;  `b##a` -> `ba`."""
    out, _ = diff_snippet(tmp_path, "#define a a##b\nint a;\n",
                          fname="h.c")
    assert norm(out)[-2:] == ["ab", ";"]
    out, _ = diff_snippet(tmp_path, "#define a b##a\nint a;\n",
                          fname="t.c")
    assert norm(out)[-2:] == ["ba", ";"]


def test_object_paste_pp_number_and_underscore(tmp_path):
    """v9/v11: `#define a 5##b` -> `int 5b;` (pp-number join);
    `#define W _##x` -> `_x w;`."""
    out, _ = diff_snippet(tmp_path, "#define a 5##b\nint a;\n",
                          fname="n.c")
    assert "5b" in norm(out)
    out, _ = diff_snippet(tmp_path, "#define W _##x\nW w;\n",
                          fname="u.c")
    assert norm(out)[:2] == ["_x", "w"]


def test_object_paste_operand_raw_not_prescanned(tmp_path):
    """v6 (C11 6.10.3.4 prescan order): with `#define b 7` defined, the
    ##-adjacent `b` stays RAW: `a##b` -> `ab`, never `a##7`/`a7`."""
    out, _ = diff_snippet(tmp_path, "#define a a##b\n#define b 7\nint a;\n")
    assert norm(out)[-2:] == ["ab", ";"]


def test_object_paste_operand_macro_never_expanded(tmp_path):
    """e3/e5: operands that are themselves defined macros stay RAW through
    the paste, and the RESULT is only expanded if it names a macro:
    `#define A X` `#define B Y` `#define XY 3` `#define Q A##B` -> `AB`
    (never `XY`, so the `XY` macro must NOT fire)."""
    out, _ = diff_snippet(tmp_path,
                          "#define A X\n#define B Y\n#define XY 3\n"
                          "#define Q A##B\nint x = Q;\n")
    assert "AB" in norm(out) and "3" not in norm(out)


def test_object_paste_result_is_rescanned(tmp_path):
    """v7: the pasted token is a FRESH token — `#define ab 5` +
    `#define a a##b` + `int x = a;` -> `int x = 5;`."""
    out, _ = diff_snippet(tmp_path,
                          "#define ab 5\n#define a a##b\nint x = a;\n")
    assert "5" in norm(out)


def test_object_paste_builtin_operand_raw(tmp_path):
    """v12/e10: `__LINE__##_tag` -> `__LINE___tag` and `__LINE__##__LINE__`
    -> `__LINE____LINE__`: built-in hook macros are ##-adjacent operands
    too and are used RAW (gcc prints the literal, not the line number)."""
    out, _ = diff_snippet(tmp_path, "#define V __LINE__##_tag\nV v;\n",
                          fname="l1.c")
    assert norm(out)[0] == "__LINE___tag"
    out, _ = diff_snippet(tmp_path,
                          "#define V __LINE__##__LINE__\nV v;\n",
                          fname="l2.c")
    assert norm(out)[0] == "__LINE____LINE__"


def test_object_paste_chain3(tmp_path):
    """e1: paste chains run left-to-right as one raw join:
    `#define Q X##Y##Z` -> `XYZ q;`."""
    out, _ = diff_snippet(tmp_path, "#define Q X##Y##Z\nQ q;\n")
    assert norm(out)[0] == "XYZ"


def test_object_paste_dup_paste_keeps_left(tmp_path):
    """e13: `#define Q X## ##Y` -> `XY q;` — the duplicated ## collapses
    against the SAME left operand (a collapse that drops the popped left
    prints `Y` and stays token-equal only by luck of a missing operand)."""
    out, _ = diff_snippet(tmp_path, "#define Q X## ##Y\nQ q;\n")
    assert norm(out)[0] == "XY"


def test_paste_keyword_rekeywords(tmp_path):
    """e4: `#define K in##t` + `K x = 1;` prints `int x = 1;` — and the
    pasted token IS a keyword for the parser (oracle -c rc 0 measured)."""
    out, _ = diff_snippet(tmp_path, "#define K in##t\nK x = 1;\n")
    assert norm(out)[:3] == ["int", "x", "="]
    path = write(tmp_path, "kw.c", "#define K in##t\nK x = 1;\n")
    c = subprocess.run(["gcc", "-c", path, "-o", os.devnull],
                       capture_output=True, text=True, timeout=120)
    assert c.returncode == 0, c.stderr


def test_paste_pragma_operand_processed(tmp_path):
    """e11: `#define P _##Pragma` + `P("unused")` -> gcc processes the
    paste-built `_Pragma` and emits `#pragma unused` (-E passes pragmas
    through; blcc does too, the result token is not blue-painted)."""
    out, _ = diff_snippet(tmp_path,
                          '#define P _##Pragma\nP("unused")\nint x;\n')
    assert "#pragma unused" in out or "pragma" in norm(out)


def test_paste_ws_edges(tmp_path):
    """e9: body edge whitespace is trimmed at #define and the paste eats
    the whitespace around `##`: `#define Q   X ## Y   ` -> `XY q;`."""
    out, _ = diff_snippet(tmp_path, "#define Q   X ## Y   \n Q q;\n")
    assert norm(out)[0] == "XY"


# ------------------------------------- interaction with the c4 rescan wall --


def test_fn_self_paste_controls(tmp_path):
    """v3/v4/v5 (function-like controls, were green pre-fix): a
    function-like body's own name pasted with a RAW arg — `f(x) x##a` +
    `f(y)` -> `ya`;  `f(x) f##x` -> `fy`."""
    for body, want in (("x##a", "ya"), ("f##x", "fy"), ("a##x", "ay")):
        out, _ = diff_snippet(tmp_path,
                              "#define f(x) %s\nint v = f(y);\n" % body,
                              fname="f.c")
        assert norm(out)[-2] == want


def test_fn_paste_raw_param_arg_not_prescanned(tmp_path):
    """e18 (C11 6.10.3.4 prescan order, function-like side): a ##-adjacent
    parameter's argument is used RAW — `#define y Z` + `f(x) x##a` + `f(y)`
    -> `ya`, never `Za` (oracle-measured both sides). The shipped code got
    this right from c2's raw-marking, but NOTHING pinned it: teeth fault
    2 (raw-marking flipped to plain) stays GREEN without this row."""
    out, _ = diff_snippet(tmp_path,
                          "#define y Z\n#define f(x) x##a\nint u = f(y);\n"
                          "#define g(x) a##x\nint v = g(y);\n")
    toks = norm(out)
    assert "ya" in toks and "ay" in toks and "Z" not in toks, toks


def test_fn_operand_object_paste_macro_raw(tmp_path):
    """e15 (raw-operand rule x c4 splice-rescan boundary): a function-like
    ##-adjacent operand that is an OBJECT-LIKE paste macro stays RAW:
    `#define O X##Y` + `#define F(z) O##z` + `F(1)` -> `O1`, never `XY1`."""
    out, _ = diff_snippet(tmp_path,
                          "#define O X##Y\n#define F(z) O##z\nint v = F(1);\n")
    assert norm(out)[-2] == "O1"


def test_paste_head_calls_next_macro(tmp_path):
    """e17: a paste-built head is a fresh token that must see the call
    behind it on the rescan: `#define G(z) z##1` + `#define C G(a)` +
    `int v = C;` -> `int v = a1;` (c4 F-3 machinery, now via the object
    route too)."""
    out, _ = diff_snippet(tmp_path,
                          "#define G(z) z##1\n#define C G(a)\nint v = C;\n")
    assert norm(out)[-2] == "a1"


def test_paste_result_tail_not_glued(tmp_path):
    """e14 (cpp space_needed at the splice boundary):
    `#define CALL CAT(pr,i)ntf` prints `pri ntf` — the paste result and
    the raw body tail are TWO tokens and must never print glued as
    `printf` (oracle-verified); the fix lives in the -E join."""
    out, _ = diff_snippet(tmp_path,
                          "#define CAT(a,b) a##b\n"
                          "#define CALL CAT(pr,i)ntf\nCALL;\n")
    toks = norm(out)
    assert toks == ["pri", "ntf", ";"], toks


def test_paste_operator_joins_and_spacing(tmp_path):
    """e16 + spacing probes: valid operator joins become ONE token
    (`&##&` -> `&&`, `+##+` -> `++`, `-##>` -> `->`), while expansion-
    adjacent punctuators that are NOT pasted print with cpp spacing
    (`<`+`<` -> `< <`, `/`+`*` -> `/ *`) and source `1/2` stays glued."""
    out, _ = diff_snippet(tmp_path,
                          "#define T(x,y) x##y\nint v = T(&,&);\n"
                          "int w = T(+,+);\nint u = T(-,>);\n")
    for tok in ("&&", "++", "->"):
        assert tok in norm(out), tok
    out, _ = diff_snippet(tmp_path,
                          "#define L <\n#define R L<L\n#define D /\n"
                          "#define Q D*x\nR s;\nint z = 1/2;\n")
    toks = norm(out)
    assert toks[:3] == ["<", "<", "<"], toks[:3]   # `< < <` not `<<<`
    assert toks[toks.index("z") + 2:toks.index("z") + 5] == \
        ["1", "/", "2"], toks


# ------------------------------------------------------- LOUD parity rows --


def test_paste_edge_of_body_loud(tmp_path):
    """e6/e7 (oracle rc != 0 at DEFINE time): `#define E ##b` and
    `#define E a##` die with "'##' cannot appear at either end of a macro
    expansion" — blcc warned at rc 0 pre-fix (SILENT class)."""
    loud_pair(tmp_path, "#define E ##b\nE;\n",
              "cannot appear at either end", "h.c")
    loud_pair(tmp_path, "#define E a##\nE;\n",
              "cannot appear at either end", "t.c")


def test_paste_invalid_join_loud(tmp_path):
    """e8 (oracle rc != 0 at expansion): `#define E +##-` + `E e;` —
    "pasting '+' and '-' does not give a valid preprocessing token" (gcc
    names the operands double-quoted; blcc single-quoted — class check)."""
    loud_pair(tmp_path, "#define E +##-\nE e;\n",
              "does not give a valid preprocessing token")


def test_paste_matrix_loud_and_quiet(tmp_path):
    """The matrix extremes stay pinned: `1##+` and `.##.` error (join is
    not one token) while `.##4` -> `.4`, `1.5##z` -> `1.5z` and `0x##1` ->
    `0x1` are quiet single pp-number/operators — a fix that erred on every
    non-identifier join would die on these quiet rows."""
    loud_pair(tmp_path, "#define T(x,y) x##y\nint v = T(1,+);\n",
              "does not give a valid preprocessing token", "a.c")
    loud_pair(tmp_path, "#define T(x,y) x##y\nint v = T(.,.);\n",
              "does not give a valid preprocessing token", "b.c")
    out, _ = diff_snippet(tmp_path,
                          "#define T(x,y) x##y\nint v = T(. ,4);\n"
                          "int w = T(1.5,z);\n#define Q 0x##1\nint x = Q;\n",
                          fname="q.c")
    toks = norm(out)
    assert "1.5z" in toks and "0x1" in toks, toks


def test_comma_paste_matrix(tmp_path):
    """The GNU comma pair, oracle-measured: the variadic idiom
    `__C(, ##__VA_ARGS__, ...)` is QUIET with a non-empty tail (rmwcc.h,
    1309 sites in 5.10) AND with an empty one (comma swallowed); the SAME
    `, ## plain-param` through a named parameter is an ERROR ("pasting
    ',' and '42'..."). blcc must reproduce BOTH sides of the pair."""
    out, _ = diff_snippet(tmp_path,
                          "#define C(...) __C(, ##__VA_ARGS__, 4,3)\n"
                          "int v = C(42);\n")
    toks = norm(out)
    i = toks.index("__C")
    assert toks[i:i + 5] == ["__C", "(", ",", "42", ","], toks[i:i + 5]
    out, _ = diff_snippet(tmp_path,
                          "#define C(...) __C(, ##__VA_ARGS__, 4,3)\n"
                          "int v = C();\n", fname="e.c")
    toks = norm(out)
    i = toks.index("__C")
    assert toks[i:i + 4] == ["__C", "(", ",", "4"], toks[i:i + 4]
    loud_pair(tmp_path, "#define C1(y) ,##y\nint v = C1(42);\n",
              "does not give a valid preprocessing token", "c.c")
