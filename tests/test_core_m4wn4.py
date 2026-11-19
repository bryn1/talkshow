# LINES reason: one wave of legs (M4 W-N COMMIT-4 — the interaction TU,
# card 12404.2.85): these legs exist ONLY to exercise the three W-N
# laws in ONE translation unit; splitting one TU across files would
# test three waves, not the interaction.
r"""M4 W-N COMMIT-4 — the interaction TU: %P + __func__ + file asm in ONE body.

The three commits each own their legs; THIS file pins that they ride
together in one translation unit without interference — the shape the
kernel walk actually hits (a percpu `%P` read beside a `pr_*` name use
beside file-scope alias blocks, the current.h:15 consumer family).
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


# ONE TU, THREE LAWS: a file-scope `.weak`/`.set` alias block (COMMIT-3
# shape, verbatim sys_ni idiom), a `%P` percpu-style address read
# (COMMIT-1 current.h:15 law through the switch expansion), and a
# `__func__` name use (COMMIT-2) — the exit code folds ALL THREE.
TRIPLE = """\
asm( ".weak " "zalias" "\\n\\t" ".set  " "zalias" "," "ztarget");
long per_cpu__zvar = 77;
int ztarget(void){ return 3; }
extern int zalias(void);
long zread(void){
  typeof(per_cpu__zvar) pfo_val__;
  asm("mov" "q " "" "%" "P[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "p" (&(per_cpu__zvar)));
  return (long)(unsigned long) pfo_val__;
}
int zmix(void){
  return (int)zread() + (int)__func__[0] + zalias();
}
int main(void){ return zmix() & 0xFF; }
"""


def _both(tmp_path, tag, src, extra=None):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)] + (extra or []))
    assert g.returncode == 0, "gcc must compile:\n" + g.stderr
    bx = tmp_path / (tag + ".blcc")
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, "blcc must compile:\n" + b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    return gv.returncode, bv.returncode


def test_wn4_triple_tu_run_pair(tmp_path):
    # 77 (percpu %P read) + 122 ('z' of __func__ "zmix") + 3 (the weak
    # alias call) = 202. One exit byte, three laws.
    g, b = _both(tmp_path, "wn4tri", TRIPLE)
    assert g == (77 + ord("z") + 3) & 0xFF, "oracle moved: {}".format(g)
    assert b == g, "blcc answer: {} != {}".format(b, g)


def test_wn4_func_string_via_P_address(tmp_path):
    # `%P` addressing the `__func__` ARRAY through "m"(*__func__): the
    # printed frame text is the string's OWN address — load the first
    # letter through it. COMMIT-1's text feeds COMMIT-2's object.
    src = ("int zf(void){ long v;\n"
           ' asm("movq %P1, %0" : "=r"(v) : "p"(&__func__[0]));\n'
           "  return (int)v & 0xFF; }\n"
           "int main(void){ return zf(); }\n")
    g, b = _both(tmp_path, "wn4fa", src)
    assert g == ord("z"), "oracle moved: {}".format(g)
    assert b == g, "blcc answer: {}".format(b)


def test_wn4_func_pointer_P_constant(tmp_path):
    # `%P` with `"p"(__func__)`: gcc accepts it — `__func__` is a
    # STATIC const object, its address is a CONSTANT (rc0 measured) —
    # blcc's injection is a fn-STATIC too (the gnu89 binding really is
    # static storage), so the COMMIT-1 constant-address guard passes
    # and the SYMBOL text prints. The load answers the first letter.
    src = ("int zf(void){ long v;\n"
           ' asm("movq %P1, %0" : "=r"(v) : "p"(__func__));\n'
           "  return (int)v & 0xFF; }\n"
           "int main(void){ return zf(); }\n")
    g, b = _both(tmp_path, "wn4fp", src)
    assert g == ord("z"), "oracle moved: {}".format(g)
    assert b == g, "blcc answer: {}".format(b)


def test_wn4_alias_block_and_fold_pipe(tmp_path):
    # COMMIT-3 blocks beside COMMIT-0's fold law: the `"i"` operand
    # `&gs[3]+1` folds to `gs+16` (ELEMENT scaling) and the plain
    # printer answers without `$`-ambiguity; the file-scope alias block
    # sits ABOVE and changes nothing. Exit code: gs[3]+1 arithmetic is
    # NOT evaluated — the address rides; the exit proves both TUs
    # compile+link with blocks + fold in one TU.
    src = ('asm( ".weak " "w2alias" "\\n\\t" ".set  " "w2alias" "," "gsym");\n'
           "int gs[8] = {1,2,3,4,5,6,7,8};\n"
           "long gsym(void){ return 0; }\n"
           "int main(void){ long r;\n"
           ' asm("movl %1, %%eax" : "=a"(r) : "i"(&gs[4]-&gs[0]));\n'
           " return (int)r & 0xFF; }\n")
    g, b = _both(tmp_path, "wn4af", src)
    assert g == 4, "oracle moved: {} (elements law)".format(g)
    assert b == 4, "blcc answer: {}".format(b)


def test_wn4_stream_shaped_walk_leg(tmp_path):
    # The pinned-stream SHAPE (current.h:15 inside the percpu switch)
    # already rides COMMIT-1; this leg re-pins it INSIDE a TU that also
    # declares a file-scope block — the walk-streams interleave all
    # three, so the walk lever must not regress when blocks join.
    src = ('asm(".weak w3a\\n\\t.set w3a,w3b");\n'
           "struct task_struct; extern struct task_struct *current_task;\n"
           "struct task_struct *w3get(void){\n"
           " return ({ typeof(current_task) r__; switch(sizeof(current_task))"
           " { case 8: r__ = ({ unsigned long v__; asm(\"mov\" \"q \" \"\""
           " \"%\" \"P[var]\" \", \" \"%[val]\" : [val] \"=\" \"r\" (v__)"
           " : [var] \"p\" (&(current_task))); (typeof(current_task))v__;"
           " }); break; default: break; } r__; });\n}\n"
           "int main(void){ return 0; }\n")
    s = tmp_path / "wn4w3.c"
    s.write_text(src)
    o = tmp_path / "wn4w3.bin"
    b = blcc(["-c", str(s), "--emit-asm", "-o", str(o)])
    assert b.returncode == 0, "walk shape must compile beside blocks:\n" \
        + b.stderr
    a = (tmp_path / (str(o) + ".s")).read_text()
    body = a.split("\nw3get:", 1)[1]
    m = re.search(r"movq (\S*current_task\S*), %rax", body)
    assert m and m.group(1) == "current_task(%rip)", \
        "the %P address text regressed: {!r}".format(m)
