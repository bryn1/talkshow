r"""Regressions for the M1-c4 fix cycle (MC 12438). Every expectation was
measured against the live oracle (gcc 11.4 -E) THIS session before being
pinned — never from blcc.

T1 (P0-SILENT) mm/interval_tree.c, 72-token divergence. gcc emits
`static inline <gnu_inline/unused/no_instrument>` ONCE per function generated
by INTERVAL_TREE_DEFINE; blcc emitted the attribute tail a SECOND time
(rc 0 — silent). Root cause: the argument PRESCAN runs through
Expander._expand, whose return strips the per-token blue-paint extras
(F-3/MC 12436 machinery). The kernel's `#define inline inline __gnu_inline
__inline_maybe_unused notrace` (compiler_types.h:144) is SELF-REFERENTIAL:
prescanning the `static inline` argument produces a fresh `inline` token that
is hidden against {inline} — and losing that hiding re-subjects it to the
inline macro at the substitution site, so its whole tail expands AGAIN after
the prescan copy. Only macro-ARGUMENT text is affected: top-level
`static inline` was already correct (all other corpus inlines green).

T2 (37 files) macro-operand #include — C11 6.10.3: gcc expands the
include-directive operand BEFORE parsing the filename. Measured this session
(gcc 11.4, every row re-run):
  #define M "q.h"        + #include M      -> rc 0, q.h included
  #define M <q.h>        + #include M      -> rc 0, q.h included
  #define INC(x) <x.h>   + #include INC(q) -> rc 0, q.h included
  #define A B / #define B "q.h"            -> rc 0 (full expansion chain)
  define_trace.h shapes (both spellings)   -> rc 0:
      __stringify(TRACE_INCLUDE_PATH/system.h) -> "inc/kmem.h"
      <trace/events/system.h>                  -> <trace/events/kmem.h>
  comment inside the directive or body     -> rc 0 (comments are ONE space)
  #define A "q.h" 42 / raw "... 42"        -> rc 0 + warning
      "extra tokens at end of #include directive"
  #define M 42           + #include M      -> rc 1,
      error: #include expects "FILENAME" or <FILENAME>          (LOUD)
  #include NOT_A_MACRO                     -> rc 1, same error  (LOUD)
  variadic operand yielding an unresolvable name
      #define INC(p, ...) <p/__VA_ARGS__.h> + #include INC(trace, q.h)
                                          -> rc 1 fatal no-such-file  (LOUD)
blcc must expand the operand with the SHIPPED expander (never a second
rescan mechanism), parse the produced "q.h"/<q.h>, and NEVER fall back to a
silent default when the expansion is garbage: the error is loud on both sides.
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


# ------------------------------------------- T1: self-ref macro in ARGUMENT --


INLINE_DEFS = ("#define inline inline __gnu_inline __inline_maybe_unused "
               "notrace\n"
               "#define __gnu_inline __attribute__((__gnu_inline__))\n"
               "#define __inline_maybe_unused __attribute__((__unused__))\n"
               "#define notrace __attribute__((__no_instrument_function__))\n")


def test_selfref_inline_arg_attrs_not_duplicated(tmp_path):
    """Minimized interval_tree.c driver (<20 lines, VERBATIM the measured
    repro): `static inline` passes through a multi-line function-like macro
    whose body uses the plain parameter TWICE. gcc emits the attribute tail
    once per use; shipped blcc emitted it TWICE per use (rc 0 — SILENT)."""
    src = INLINE_DEFS + (
        "#define GEN(TYPE, PFX, STATIC)                  \\\n"
        "static void PFX ## _search(TYPE *n);            \\\n"
        "STATIC void PFX ## _insert(TYPE *n);            \\\n"
        "STATIC void PFX ## _remove(TYPE *n);\n"
        "struct S;\n"
        "GEN(struct S,\n"
        "    foo,\n"
        "    static inline)\n"
        "static inline int q(void);\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    # gcc-measured count: 3 uses of `inline` (2 splices + top-level),
    # each with exactly ONE gnu_inline attribute set.
    assert toks.count("__gnu_inline__") == 3, toks.count("__gnu_inline__")


def test_selfref_inline_arg_used_once(tmp_path):
    """Single-use variant: one splice, one tail. Guards the count pin above
    from a fix that suppresses the tail entirely."""
    src = INLINE_DEFS + (
        "#define GEN(TYPE, PFX, STATIC)                  \\\n"
        "STATIC void PFX ## _insert(TYPE *n);\n"
        "struct S;\n"
        "GEN(struct S,\n"
        "    foo,\n"
        "    static inline)\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    assert toks.count("__gnu_inline__") == 1
    assert "static" in toks and "inline" in toks


# ------------------------------------------- T2: macro-operand #include --


def test_include_object_string_operand(tmp_path):
    """#define M "q.h" + #include M: oracle rc 0, operand expands to the
    quoted name."""
    write(tmp_path, "q.h", "int q_marker;\n")
    out, _ = diff_snippet(tmp_path, '#define M "q.h"\n#include M\n')
    assert "q_marker" in norm(out)


def test_include_object_angle_operand(tmp_path):
    """#define M <q.h> + #include M: oracle rc 0 (angle search: -I dirs
    only, never the includer's dir — same rule as the raw form)."""
    write(tmp_path, "q.h", "int q_marker;\n")
    out, _ = diff_snippet(tmp_path, "#define M <q.h>\n#include M\n",
                          extra=["-I", str(tmp_path)])
    assert "q_marker" in norm(out)


def test_include_function_angle_operand(tmp_path):
    """#define INC(x) <x.h> + #include INC(q): parameter feeds the angle
    name; oracle rc 0."""
    write(tmp_path, "q.h", "int q_marker;\n")
    out, _ = diff_snippet(
        tmp_path, "#define INC(x) <x.h>\n#include INC(q)\n",
        extra=["-I", str(tmp_path)])
    assert "q_marker" in norm(out)


def test_include_expansion_chain(tmp_path):
    """A -> B -> "q.h": expansion runs to completion, not one step."""
    write(tmp_path, "q.h", "int q_marker;\n")
    src = '#define A B\n#define B "q.h"\n#include A\n'
    out, _ = diff_snippet(tmp_path, src)
    assert "q_marker" in norm(out)


def test_include_trace_shape_stringify(tmp_path):
    """The define_trace.h TRACE_INCLUDE_PATH spelling — EVERY kernel TU that
    #defines CREATE_TRACE_POINTS reaches
    `#include TRACE_INCLUDE(TRACE_INCLUDE_FILE)` through this chain:
    parameter substitution, then __stringify yields the quoted name.
    Oracle rc 0 (measured this session)."""
    write(tmp_path, "inc/kmem.h", "int kmem_marker;\n")
    src = ('#define __stringify_1(x...) #x\n'
           '#define __stringify(x...) __stringify_1(x)\n'
           '#define TRACE_INCLUDE_PATH inc\n'
           '#define TRACE_INCLUDE_FILE kmem\n'
           '#define __TRACE_INCLUDE(system) '
           '__stringify(TRACE_INCLUDE_PATH/system.h)\n'
           '#define TRACE_INCLUDE(system) __TRACE_INCLUDE(system)\n'
           '#include TRACE_INCLUDE(TRACE_INCLUDE_FILE)\n')
    out, _ = diff_snippet(tmp_path, src)
    assert "kmem_marker" in norm(out)


def test_include_trace_shape_angle(tmp_path):
    """The define_trace.h DEFAULT spelling: the angle operand is assembled
    across the parameter splice (`<trace/events/system.h>`, system=kmem2).
    Oracle rc 0 (measured this session)."""
    write(tmp_path, "trace/events/kmem2.h", "int kmem2_marker;\n")
    src = ('#define __TRACE_INCLUDE(system) <trace/events/system.h>\n'
           '#define TRACE_INCLUDE(system) __TRACE_INCLUDE(system)\n'
           '#define TRACE_INCLUDE_FILE kmem2\n'
           '#include TRACE_INCLUDE(TRACE_INCLUDE_FILE)\n')
    out, _ = diff_snippet(tmp_path, src, extra=["-I", str(tmp_path)])
    assert "kmem2_marker" in norm(out)


def test_include_comment_in_directive(tmp_path):
    """Comments are one space BEFORE filename parsing (R21 pass 1 + oracle):
    inside the directive and inside the macro body."""
    write(tmp_path, "q.h", "int q_marker;\n")
    src = '#define M /* comment */ "q.h" /* trailing */\n#include /*c*/ M\n'
    out, _ = diff_snippet(tmp_path, src)
    assert "q_marker" in norm(out)


def test_include_operand_garbage_loud(tmp_path):
    """Expansion yields `42`: oracle rc 1,
    error: #include expects "FILENAME" or <FILENAME>. blcc must die LOUD —
    never include a default, never skip silently."""
    path = write(tmp_path, "m.c", "#define M 42\n#include M\n")
    g = gcc_run([path] + PINS)
    b = blcc_run([path] + PINS)
    assert g.returncode == 1 and "expects" in g.stderr
    assert b.returncode != 0 and "expects \"FILENAME\" or <FILENAME>" \
        in b.stderr


def test_include_undefined_macro_loud(tmp_path):
    """Operand is a bare UNDEFINED name: still the same oracle error rc 1 —
    an unexpanded identifier is garbage, not a filename."""
    path = write(tmp_path, "m.c", "#include NOT_A_MACRO\n")
    g = gcc_run([path] + PINS)
    b = blcc_run([path] + PINS)
    assert g.returncode == 1 and "expects" in g.stderr
    assert b.returncode != 0 and "expects \"FILENAME\" or <FILENAME>" \
        in b.stderr


def test_include_operand_variadic_loud(tmp_path):
    """Variadic operand producing an unresolvable name (measured oracle rc 1,
    fatal no-such-file): loud, with the name it tried."""
    path = write(tmp_path, "m.c",
                 "#define INC(p, ...) <p/__VA_ARGS__.h>\n"
                 "#include INC(trace, q.h)\n")
    g = gcc_run([path] + PINS)
    b = blcc_run([path] + PINS)
    assert g.returncode == 1 and "No such file" in g.stderr
    assert b.returncode != 0 and "q" in b.stderr   # tried SOMETHING with q


def test_include_extra_tokens_warn_not_die(tmp_path):
    """Trailing tokens AFTER the filename: oracle rc 0 with warning
    "extra tokens at end of #include directive" — loudness parity means
    WARN and keep going (rc 0), the file is still included."""
    write(tmp_path, "q.h", "int q_marker;\n")
    path = write(tmp_path, "m.c", '#define A "q.h" 42\n#include A\n')
    g = gcc_run([path] + PINS)
    b = blcc_run([path] + PINS)
    assert g.returncode == 0 and "extra tokens" in g.stderr
    assert b.returncode == 0
    assert norm(b.stdout) == norm(g.stdout)
    assert "q_marker" in norm(b.stdout)
