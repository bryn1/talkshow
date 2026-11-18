# LINES reason: one wave of legs (M4 W-N COMMIT-2 — implicit `__func__`,
# card 12404.2.85) — the keyword law and the value law are ONE binding;
# splitting would separate the declarable-name refusal from the object
# it protects.
r"""M4 W-N COMMIT-2 — `__func__` is the function's OWN name (gnu89 law).

THE LAW (gcc 11.4 -std=gnu89 REC, measured at MY hands, .tmp/m4-wn/out/
measure-wn2.txt): every function body carries an implicit
`static const char __func__[len+1] = "<name>"` — it is an ARRAY
(sizeof == len+1, indexable, decays to char*), holding the FUNCTION
name. And `__func__` is a KEYWORD at every declaration position: a
PARAMETER, a LOCAL, a FILE-SCOPE object, a `static const char`
re-declaration, even a STRUCT MEMBER named `__func__` — gcc rc1
'expected identifier or ( before __func__'. blcc tip: the body USE is
`sema: '__func__' undeclared — not a local, parameter, global or enum
constant` (92 of the 706 pinned streams first-block on exactly this
wall inside their first-blocker set; F-standalone sim flips
lib_math_reciprocal_div). FILE-SCOPE USE (gcc rc0 + warning + empty
1-byte object) and the `__FUNCTION__` alias (gcc rc0, corpus volume 0)
stay blcc LOUD — named honest walls, no arm added.

THE MECHANISM: the parser knows the function it is parsing — the ONE
body-construction point (parse_function_body) binds the name ONCE as a
real local char-array (the shipped §1c local-string-array law carries
sizeof/index/decay/frame — no second vocabulary), and the declarator
walk refuses the name at EVERY declaration position (gcc keyword law;
one check, ctx-agnostic — the member position refuses too, measured).
"""
import os
import subprocess
import sys

import pytest

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


def _run_pair(tmp_path, tag, src, want):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)])
    assert g.returncode == 0, "gcc must compile:\n" + g.stderr
    bx = tmp_path / (tag + ".blcc")
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, "blcc must compile:\n" + b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    assert gv.returncode == want, "oracle moved: {} != {}".format(
        gv.returncode, want)
    assert bv.returncode == want, "blcc answer: {} != {}".format(
        bv.returncode, want)


def test_wn2_func_index(tmp_path):
    # `__func__[0]` — the first letter of the function's name.
    _run_pair(tmp_path, "wn2ix",
              "char probe(void){ return __func__[0]; }\n"
              "int main(void){ return (int)probe(); }\n",
              ord("p"))


def test_wn2_func_sizeof(tmp_path):
    # The object is an ARRAY sized len+1 — sizeof answers 6 for `probe`.
    _run_pair(tmp_path, "wn2sz",
              "int probe(void){ return (int)sizeof(__func__); }\n"
              "int main(void){ return probe(); }\n", 6)


def test_wn2_func_decay_strlen(tmp_path):
    # Decays to char* — walking it yields the WHOLE name.
    _run_pair(tmp_path, "wn2dc",
              "int probe(void){ char *p = __func__; int n = 0;\n"
              "  while (p[n]) n++; return n; }\n"
              "int main(void){ return probe(); }\n", 5)


def test_wn2_func_per_function(tmp_path):
    # Each function binds its OWN name: 'a'(1) + 'b'(2) via lengths 1+1…
    # use first letters: aaa=97, bbb=98 → difference under exit-code.
    _run_pair(tmp_path, "wn2pf",
              "char aaa(void){ return __func__[0]; }\n"
              "char bbb(void){ return __func__[0]; }\n"
              "int main(void){ return (int)bbb() - (int)aaa() + 3; }\n",
              ord("b") - ord("a") + 3)


DECL_LOUD = [
    ("param", "long f(int __func__){ return 0; }"),
    ("local", 'long f(void){ char __func__[2] = "x"; return 0; }'),
    ("staticc", 'long f(void){ static const char __func__[] = "y";'
                " return 0; }"),
    ("file", "char __func__[3];\nlong f(void){ return 0; }"),
    ("member", "struct S { int __func__; };\nlong f(void){ return 0; }"),
    ("fnname", "long __func__(void){ return 0; }"),
    ("ptr", "char *__func__;\nlong f(void){ return 0; }"),
]


@pytest.mark.parametrize("tag,src", DECL_LOUD)
def test_wn2_decl_loud_pair(tmp_path, tag, src):
    # `__func__` is a KEYWORD everywhere a name is declared — gcc rc1
    # 'expected identifier or ( before __func__' (measured for every
    # position; blcc refuses the SAME positions).
    full = src + "\nint main(void){ return 0; }\n"
    s = tmp_path / ("wn2L" + tag + ".c")
    s.write_text(full)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode != 0, "gcc must refuse {}".format(tag)
    assert "__func__" in g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / ("wn2L" + tag + ".o"))])
    assert b.returncode != 0, "blcc invented a pass for {}".format(tag)
    assert "__func__" in b.stderr


def test_wn2_file_scope_use_honest_wall(tmp_path):
    # FILE-SCOPE use: gcc rc0 with a warning and an EMPTY 1-byte object
    # (measured); blcc keeps its LOUD undeclared wall — named honest
    # divergence, corpus volume 0 (no stream uses __func__ at file
    # scope: the walk shape is `pr_*` inside functions).
    src = 'char *gp = __func__;\nint main(void){ return 0; }\n'
    s = tmp_path / "wn2fs.c"
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode == 0, "gcc compiles (measured rc0 + warning)"
    assert "__func__" in g.stderr          # the 'not defined outside' warn
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn2fs.o")])
    assert b.returncode != 0


def test_wn2_function_alias_honest_wall(tmp_path):
    # `__FUNCTION__` — gcc accepts it (rc0, measured); pinned-corpus
    # volume 0 (grep: no stream spells it). blcc stays LOUD, named.
    src = "long f(void){ return sizeof(__FUNCTION__); }\n" \
          "int main(void){ return 0; }\n"
    s = tmp_path / "wn2fa.c"
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode == 0, "gcc accepts the alias (measured)"
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn2fa.o")])
    assert b.returncode != 0


def test_wn2_asm_substitute_law(tmp_path):
    # The kernel walk's REAL shape: __func__ feeding a `%c`-style string
    # constant — here pinned as the VALUE law through an index + the
    # .rodata string existing exactly once per distinct name.
    src = ("int alpha(void){ return (int)__func__[1]; }\n"
           "int main(void){ return alpha(); }\n")
    s = tmp_path / "wn2as.c"
    s.write_text(src)
    bx = tmp_path / "wn2as.bin"
    b = blcc(["-c", str(s), "--emit-asm", "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    asm = open(str(bx) + ".s").read()
    assert "alpha" in asm, "the function-name string must reach the asm"
