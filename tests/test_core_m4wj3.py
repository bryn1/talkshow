# LINES reason: one wave of legs (M4 W-J COMMIT-3 — top-level
# `_Static_assert`, 327 first-blockers, card 12404.2.77) — accept arms,
# fail arms and the corpus witnesses are the three faces of ONE law.
r"""M4 W-J COMMIT-3 — file-scope (and block-scope) `_Static_assert`.

THE WALL (gate LEG 8): **327** streams whose first blocker (once FT +
dyn-offset walls die — measured at THIS tree after COMMIT-1/2) is
parse: "expected a top-level declaration, found '_Static_assert'" — my
cleaned-stream scan names them: arch_x86_boot_compressed_pgtable_64,
entry_common, entry_syscall_64, entry_vdso_vma, entry_vsyscall_vsyscall_64,
events_amd_core … (the mask says the cohort is 327). The dominant shape
(461 sites in init_main.c.i alone) is the kparam/struct-size law:
`_Static_assert(__builtin_offsetof(struct filename, iname) % sizeof(long)
== 0, "offsetof(struct filename, iname) % sizeof(long) == 0");`

MEASURED LAW (gcc 11.4 gnu89 -Os, my probes sa_*, out-gcc.txt):
  ACCEPT rc0: true/false-foldable conditions via the SHIPPED constant
    machinery (fold_truthy: IntLit/CharLit/enum-Ident/sizeof/alignof/
    cast/cond/BINARY incl. % and ==); string message; C23 ONE-ARG form
    rc0 EVEN IN gnu89 (sa_k); BLOCK scope rc0 (sa_l). Corpus samples:
    offsetof%sizeof(long)==0 (461), string-size <= 64-word (60),
    enum-count <= 32 (11), sizeof(struct)==N, 16 == ('0' - ' ') (kstrlib).
  REJECT pairs, both LOUD, sentences mirrored:
    condition 0        → rc1 "static assertion failed: \"MSG\"" (sa_a)
    condition 0, bare  → rc1 "static assertion failed" (sa_f)
    non-constant cond  → rc1 "expression in static assertion is not
                         constant" — SAME sentence with OR without the
                         message arg (sa_j/sa_s: the pin pair)
    message not a str  → rc1 "expected string literal before …" (sa_t)
    1/0 condition      → rc1 (divide-by-zero class); blcc's fold returns
                         None → "not constant" sentence — SAME VERDICT.
  gcc ALSO keeps _Static_assert inside functions fine (block-scope pair
  below); C23 `static_assert(1)` macro form is pp-level, out of scope.

MECHANISM (extend, no parallel rail): `_Static_assert` joins KEYWORDS
(the §5 "kept as keywords so diagnostics can name them exactly" family)
and _DECL_START_KW (the shipped declaration-opener law); parse_decl gets
ONE arm → _parse_static_assert — token shape, parse_expression for the
condition, the shipped fold_truthy for the verdict (fold None = the LOUD
"not constant" arm), _sema for the fail sentences. NO new expression
machinery: every corpus condition rides the SAME fold that sizeof/enum/
offsetof already use (461-body = the COMMIT-2 fold + % + ==, all shipped
folds). Block scope: parse_block_item already routes starts_decl →
parse_decl(at_file=False); the label-preceded unbraced form gets the
parse_statement arm (gcc gnu89 accepts label+decl — measured, wj1_und).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


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


def _ok(tmp_path, tag, src):
    g = _gcc_rc(tmp_path, tag, src)
    assert g.returncode == 0, "gcc twin must rc0:\n" + src + g.stderr
    r = _compile(tmp_path, tag, src)
    assert r.returncode == 0, "blcc must ACCEPT (measured gcc rc0):\n" \
        + src + "\n" + r.stderr
    return r


def _loud(tmp_path, tag, src, needle=None, gcc_needle=None):
    g = _gcc_rc(tmp_path, tag, src)
    assert g.returncode == 1, "gcc twin must rc1:\n" + g.stderr
    if gcc_needle is not None:
        assert gcc_needle in g.stderr, "gcc sentence moved?\n" + g.stderr
    r = _compile(tmp_path, tag, src)
    assert r.returncode != 0, "must LOUD:\n" + src + g.stderr
    if needle is not None:
        diag = r.stderr.replace(str(tmp_path), "")
        assert needle in diag, r.stderr
    return r


# ------------------------------------------------- the ACCEPT face (rc0)

def test_wj3_basic_pairs(tmp_path):
    _ok(tmp_path, "sa_true", '_Static_assert(1, "yes");\nint v = 1;\n')
    _ok(tmp_path, "sa_sizeof",
        'struct S { int a[3]; };\n_Static_assert(sizeof(struct S) == 12,'
        ' "sz");\n')
    # __alignof__ folded through the SHIPPED alignof mirror; pinned on
    # `long long` (both compilers 8, no long-double layout bet):
    _ok(tmp_path, "sa_alignof",
        '_Static_assert(__alignof__(long long) == 8, "al");\n')
    _ok(tmp_path, "sa_charlit",
        "_Static_assert(16 == ('0' - ' '), \"ks\");\n")  # kstrlib verbatim
    _ok(tmp_path, "sa_c23_one_arg", '_Static_assert(2 + 2 == 4);\n')
    _ok(tmp_path, "sa_block",
        'int f(void){ _Static_assert(1 + 1 == 2, "b"); return 2; }\n')


def test_wj3_corpus_shapes_pairs(tmp_path):
    # VERBATIM corpus conditions (my grep counts): the 461-site kparam
    # shape rides the COMMIT-2 fold + % + ==; the 60-site string-size
    # law; the 11-site enum law; the printf_spec sizeof law. All gcc rc0.
    _ok(tmp_path, "sa_corp1",
        "struct filename { const char *name; int iname; };\n"
        '_Static_assert(__builtin_offsetof(struct filename, iname) %'
        " sizeof(long) == 0,\n"
        '  "offsetof(struct filename, iname) % sizeof(long) == 0");\n')
    _ok(tmp_path, "sa_corp2",
        '#define MAX_PARAM_PREFIX_LEN (64 - sizeof(unsigned long))\n'
        '_Static_assert(sizeof("softdep_update") - 1 <='
        ' MAX_PARAM_PREFIX_LEN,\n'
        '  "softdep_update too long for sysctl");\n')
    _ok(tmp_path, "sa_corp3",
        "enum { NETIF_MSG_HW = 0, NETIF_MSG_WOL, NETIF_MSG_CLASS_COUNT };\n"
        "_Static_assert(NETIF_MSG_CLASS_COUNT <= 32);\n")  # 11-site enum
    _ok(tmp_path, "sa_corp4",
        "struct printf_spec { short type; int size; };\n"
        '_Static_assert(sizeof(struct printf_spec) == 8,'
        ' "printf_spec wrong size");\n')


def test_wj3_label_preceded_accept(tmp_path):
    # gnu89 accepts a declaration after a label (wj1_und measured rc0),
    # so the unbraced SA after `case` is rc0 both sides.
    g = _gcc_rc(tmp_path, "sa_lbl",
                'int f(int x){ switch (x) { case 1: _Static_assert(1,'
                ' "c");\n  case 2: return 2; } return 9; }\n')
    assert g.returncode == 0, g.stderr
    r = _compile(tmp_path, "sa_lbl",
                 'int f(int x){ switch (x) { case 1: _Static_assert(1,'
                 ' "c");\n  case 2: return 2; } return 9; }\n')
    assert r.returncode == 0, r.stderr


# ------------------------------------------------- the REJECT face (rc1)

def test_wj3_fail_named_pair(tmp_path):
    _loud(tmp_path, "sa_fail_msg",
          '_Static_assert(1 == 2, "boom went the clock");\n',
          needle='static assertion failed: "boom went the clock"',
          gcc_needle='static assertion failed: "boom went the clock"')


def test_wj3_fail_bare_pair(tmp_path):
    _loud(tmp_path, "sa_fail_bare",
          '_Static_assert(0);\n',
          needle="static assertion failed",
          gcc_needle="static assertion failed")


def test_wj3_fail_in_block_pair(tmp_path):
    _loud(tmp_path, "sa_fail_block",
          'int f(void){ _Static_assert(3 > 4, "nope"); return 1; }\n',
          needle='static assertion failed: "nope"',
          gcc_needle='static assertion failed: "nope"')


def test_wj3_not_constant_sentence_pair(tmp_path):
    # sa_j/sa_s: the SAME gcc sentence WITH and WITHOUT the message arg —
    # the blcc twin mirrors it both ways (the pin pair).
    _loud(tmp_path, "sa_nc_msg",
          "extern int v;\n_Static_assert(v == 2, \"runtime\");\n",
          needle="expression in static assertion is not constant",
          gcc_needle="expression in static assertion is not constant")
    _loud(tmp_path, "sa_nc_bare",
          "extern int v;\n_Static_assert(v == 2);\n",
          needle="expression in static assertion is not constant",
          gcc_needle="expression in static assertion is not constant")


def test_wj3_message_not_string_pair(tmp_path):
    _loud(tmp_path, "sa_msg_num",
          "_Static_assert(1, 42);\n",
          needle="expected string literal",
          gcc_needle="expected string literal")


def test_wj3_div_zero_same_verdict(tmp_path):
    # sa_q: `1/0 == 3` — gcc rc1 (divide-by-zero family); blcc's shipped
    # fold returns None for /0 → the "not constant" sentence. SAME
    # VERDICT, different sentence, pinned honest.
    r = _loud(tmp_path, "sa_div0", "_Static_assert(1/0 == 3, \"z\");\n")
    assert "not constant" in r.stderr, r.stderr


# ------------------------------------------------ corpus witnesses (kernel)

_SA_STREAMS = [
    "arch_x86_boot_compressed_pgtable_64.c.i", "arch_x86_entry_common.c.i",
    "arch_x86_entry_syscall_64.c.i", "arch_x86_entry_vdso_vma.c.i",
    "arch_x86_entry_vsyscall_vsyscall_64.c.i", "arch_x86_events_amd_core.c.i",
]


def _clean_i(path, tmp_path, tag):
    # the shipped m4w25b idiom VERBATIM: drop linemarker/directive lines,
    # fold integer suffixes (the sweep law the W waves run on).
    import re
    clean = tmp_path / (tag + ".clean")
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


import pytest

@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
@pytest.mark.parametrize("stream", _SA_STREAMS)
def test_wj3_sa_wall_dead_in_streams(stream, tmp_path):
    # THE corpus law: the top-level SA wall sentence must be GONE from
    # the 327-cohort face — these six streams answer
    # "expected a top-level declaration, found '_Static_assert'" as
    # their FIRST blocker at the COMMIT-2 tree (my scan, named in the
    # module docstring). After the arm they move PAST it. Whatever wall
    # comes next is a later wave's first blocker — honestly expected.
    src = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wj3c")
    r = blcc(["-c", str(src), "-o", str(tmp_path / "o.o")])
    diag = r.stderr.replace(str(tmp_path), "")
    assert "found '_Static_assert'" not in diag, \
        "top-level SA wall ALIVE in " + stream + ":\n" + diag[:600]
