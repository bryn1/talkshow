# LINES reason: one wave of legs (M4 W-N COMMIT-3 — top-level asm,
# card 12404.2.85) — the grammar and the emission law are ONE feature;
# splitting separates a parse acceptance from the text it owes.
r"""M4 W-N COMMIT-3 — file-scope `asm("…")` blocks: VERBATIM at emission.

THE LAW (gcc 11.4 gnu89 REC, measured at MY hands, .tmp/m4-wn/out/
measure-wn3.txt): a top-level `asm( "lit" "lit" );` — ONE merged string
argument (juxtaposition is the LEXER's law) — emits its text VERBATIM,
wrapped in `#APP` / `#NO_APP`, at its source position between function
blocks; `%%` passes through unprocessed (file scope has no operand
scanner); OPERANDS (`:`) and `volatile` are gcc rc1 ('expected ) before
:' / the volatile wall). blcc tip dies `parse: expected a top-level
declaration, found 'asm'` — the sim A-arm proved this flips
kernel_sys_ni (the compat_sys_* `.weak`/`.set` alias family, one block
per compat syscall — dozens in a single stream).

THE MECHANISM: the TU loop grows ONE arm for the shape; codegen emits
the collected blocks at the ONE assembly point after the function
blocks. The NAMED placement divergence: blcc lays out functions-first-
then-data, so the blocks land between them (gcc interleaves at source
position); the TEXT — the #APP-wrapped bytes — is byte-parity law, and
alias/directive blocks are section-order-independent, so the VALUE is
the same.
"""
import os
import re
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


def _blcc_asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc(["-c", str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must compile:\n" + r.stderr
    return (tmp_path / (str(o) + ".s")).read_text()


def _gcc_asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".gcc.s")
    r = gcc(REC + ["-S", str(s), "-o", str(o)])
    assert r.returncode == 0, "gcc must compile:\n" + r.stderr
    return o.read_text()


def _app_blocks(text):
    out, cur = [], None
    for ln in text.splitlines():
        if ln.strip() == "#APP":
            cur = []
        elif ln.strip() == "#NO_APP":
            out.append(cur)
            cur = None
        elif cur is not None:
            cur.append(ln)
    return out


ALIAS = ('asm( ".weak " "compat_sys_foo" "\\n\\t" ".set  " '
         '"compat_sys_foo" "," "sys_ni_syscall");\n'
         'asm( ".weak " "compat_sys_bar" "\\n\\t" ".set  " '
         '"compat_sys_bar" "," "sys_ni_syscall");\n'
         "int sys_ni_syscall(void){ return 7; }\n"
         "int main(void){ return sys_ni_syscall(); }\n")


def test_wn3_alias_blocks_text_parity(tmp_path):
    # The #APP-wrapped body bytes are EQUAL between gcc and blcc, and
    # declaration ORDER is kept.
    ga = _gcc_asm(tmp_path, "wn3al", ALIAS)
    ba = _blcc_asm(tmp_path, "wn3al", ALIAS)
    gb, bb = _app_blocks(ga), _app_blocks(ba)
    # NAMED block-boundary divergence: gcc MERGES adjacent file-scope
    # asm statements into ONE #APP pair; blcc wraps one pair per
    # statement (measured both). The BODY LINES — the bytes the
    # assembler eats — are equal in declaration order.
    gl = [l for b in gb for l in b]
    bl = [l for b in bb for l in b]
    assert len(gl) == 4 and len(bl) == 4, \
        "one body line pair per directive: G{} B{}".format(gl, bl)
    assert gl == bl, "block body/order diverged:\nG{!r}\nB{!r}".format(
        gl, bl)
    for blk in bb:
        assert any(".weak compat_sys_foo" in l for l in blk) \
            or any(".weak compat_sys_bar" in l for l in blk)


def test_wn3_alias_blocks_run_pair(tmp_path):
    # The weak SET actually lands in the link: calling the ALIASED name
    # (declared extern) answers the target's value.
    src = ('asm( ".weak " "alias_ni" "\\n\\t" ".set  " "alias_ni" "," '
           '"sys_ni_syscall");\n'
           "int sys_ni_syscall(void){ return 7; }\n"
           "extern int alias_ni(void);\n"
           "int main(void){ return alias_ni(); }\n")
    s = tmp_path / "wn3rp.c"
    s.write_text(src)
    gx = tmp_path / "wn3rp.gcc"
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)])
    assert g.returncode == 0, g.stderr
    bx = tmp_path / "wn3rp.blcc"
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, "blcc must link:\n" + b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    assert gv.returncode == 7, "oracle moved: {}".format(gv.returncode)
    assert bv.returncode == 7, "blcc answer: {}".format(bv.returncode)


def test_wn3_percent_passthrough(tmp_path):
    # File scope has NO operand scanner: `%%` bytes pass VERBATIM on
    # BOTH compilers (measured gcc -S prints `movq $1,%%rax`; as then
    # refuses it identically — gcc -c and blcc -c answer the SAME rc,
    # the pair below). The emitted .s carries the verbatim bytes.
    src = ('asm("movq $1,%%rax; ret");\n'
           "int main(void){ return 0; }\n")
    s = tmp_path / "wn3pc.c"
    s.write_text(src)
    o = tmp_path / "wn3pc.bin"
    bg = gcc(REC + ["-S", str(s), "-o", str(tmp_path / "wn3pc.gcc.s")])
    assert bg.returncode == 0, bg.stderr
    bb_ = blcc(["-c", str(s), "--emit-asm", "-o", str(o)])
    assert bb_.returncode != 0          # as refuses %% on BOTH sides
    ga = (tmp_path / "wn3pc.gcc.s").read_text()
    ba = (tmp_path / (str(o) + ".s")).read_text()
    gb = [l for b in _app_blocks(ga) for l in b]
    bb = [l for b in _app_blocks(ba) for l in b]
    assert any("movq $1,%%rax" in l for l in gb), "gcc verbatim moved"
    assert any("movq $1,%%rax" in l for l in bb), \
        "%% must pass through VERBATIM at file scope"
    g = gcc(REC + ["-c", str(s), "-o", str(tmp_path / "wn3pcp.o")])
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn3pcp.b.o")])
    assert (g.returncode != 0) == (b.returncode != 0), \
        "as-verdict pair: gcc rc={} blcc rc={}".format(
            g.returncode, b.returncode)


def test_wn3_multiline_one_block(tmp_path):
    # A literal carrying `\\n\\t` emits MULTIPLE body lines inside ONE
    # #APP pair (measured gcc form; block count pinned at 1).
    src = ('asm(".text\\n\\t.long 7");\nint main(void){ return 0; }\n')
    ga = _gcc_asm(tmp_path, "wn3ml", src)
    ba = _blcc_asm(tmp_path, "wn3ml", src)
    assert len(_app_blocks(ga)) == len(_app_blocks(ba)) == 1
    assert _app_blocks(ga) == _app_blocks(ba)


LOUD_PAIR = [
    ("operands", 'asm("mov %0, %%rax" : "=r"(x));\n'
                 "int x;\nint main(void){ return 0; }\n"),
    ("volatile", 'asm volatile("nop");\nint main(void){ return 0; }\n'),
    ("exprarg", 'asm("%d", 1);\nint main(void){ return 0; }\n'),
]


@pytest.mark.parametrize("tag,src", LOUD_PAIR)
def test_wn3_file_scope_loud_pair(tmp_path, tag, src):
    # OPERANDS and VOLATILE are gcc rc1 at file scope (measured); the
    # non-literal argument too. blcc refuses the SAME shapes.
    s = tmp_path / ("wn3" + tag + ".c")
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode != 0, "gcc must refuse {} (measured)".format(tag)
    b = blcc(["-c", str(s), "-o", str(tmp_path / ("wn3" + tag + ".o"))])
    assert b.returncode != 0, "blcc invented a pass for {}".format(tag)


def test_wn3_statement_asm_unaffected(tmp_path):
    # In-function asm — including `asm volatile` — keeps its grammar
    # (the file-scope arm must not bleed into the statement parser).
    src = ('int main(void){ int x = 2; asm volatile("addl $1, %0" : "+r"(x));'
           " return x; }\n")
    _run = _gcc_asm(tmp_path, "wn3st", src)   # gcc rc0
    assert "addl $1" in _run
    bx = tmp_path / "wn3st.bin"
    b = blcc([str(tmp_path / "wn3st.c"), "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    assert subprocess.run([str(bx)], capture_output=True,
                          text=True).returncode == 3


def test_wn3_blocks_are_not_c(tmp_path):
    # The block text is the ASSEMBLER's jurisdiction: C-shaped garbage
    # inside stays LOUD at `as`, never re-parsed by blcc — blcc passes
    # the same bytes gcc would (the gcc rc pair on a BAD directive:
    # `as` fails both sides identically).
    src = 'asm(".not_a_directive_xyz @{{[}});\nint main(void){return 0;}\n'
    s = tmp_path / "wn3bad.c"
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    grc = g.returncode
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn3bad.o")])
    # Whatever `as` decides, blcc and gcc answer the SAME rc (byte-
    # identical text in the #APP block ⇒ the assembler agrees).
    assert (b.returncode != 0) == (grc != 0), \
        "gcc rc={} vs blcc rc={}".format(grc, b.returncode)
