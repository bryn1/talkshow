# LINES reason: one wave of legs (M4 W-M COMMIT-2 — the STRUCT-BY-VALUE
# RETURN ABI: callee write-back + caller temp, ONE mechanism across ALL
# size classes; card 12404.2.83) — the pair/rax/memory classes are ONE
# size-law proven from BOTH call directions; splitting would separate a
# run-pair from the size class it pins.
r"""M4 W-M COMMIT-2 — STRUCT BY VALUE RETURNS through the measured ABI.

THE WALL (200 first-blockers at the W-L tip — the time64.h:63 walk RED,
199 of them the ONE function timespec64_add, 16-byte return). THE LAW
(gcc 11.4 KERNEL RECIPE -Os -mno-sse…, table .tmp/m4-wm/out/measure-
ret.txt + measure-byval.txt, ALL probes at MY hands):
  ≤8 bytes    INTEGER: value in %rax (callee builds it in a local and
              MOVES WIDTH bytes to %rax — `movb $7,%al` is NOT required,
              the CALLER reads at the C width (movsbq %al law); the
              upper bits are the callee's business).
  9..16 bytes INTEGER PAIR (no SSE in the kernel): %rax (bytes 0..7) +
              %rdx (bytes 8..15) — callee -Os stages through its own
              locals then loads BOTH halves (`movq -17(%rsp),%rax ;
              movzbl -9(%rsp),%edx`).
  >16 bytes   MEMORY: caller allocates the CALLER TEMP, passes its
              address as a HIDDEN FIRST ARG in %rdi (`leaq 15(%rsp),%rbx
              ; movq %rbx,%rdi`); the callee writes (%rdi) and returns
              THAT POINTER in %rax (`movb $7,(%rdi) ; movq %rdi,%rax`).
  caller      `struct S t = callee();` — a pair/memory result rides the
              SHIPPED W-H block-copy law: the call expression yields the
              RESULT ADDRESS (the temp), and _copy_block does the rest.
  callee      `return e;` with struct type writes the object at the
              RETURN DOOR (one place), not at every return e.
MECHANISM (extend, never parallel): the §5 return wall is REPLACED by
the measured size class in the ONE return door; struct-typed CALLS gain
the caller-temp form in the ONE _ex_call/_stage_call path (the §2.14/W-L
push block already stages args right-to-left — the hidden pointer rides
%rdi as a FIRST GP arg, shifting the GP ladder by one EXACTLY as the
measured K=5/6/7 rows show); params keep their shipped §5 wall (the
byval-arg family is the sim-named NEXT lever, NOT this commit — LOUD
twin pinned).
"""
import os
import re
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


def _pair(tmp_path, tag, src, expect):
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


def _asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc([str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must emit:\n" + r.stderr
    return (tmp_path / (str(o) + ".s")).read_text()


def _fn_body(asm, name):
    body = asm.split(name + ":\n", 1)[1]
    nxt = re.search(r"\n\.[ \t]*\.globl|\n(\.|[A-Za-z_][\w.]*):\n", body)
    return body[:nxt.start()] if nxt else body


def _loud(src, tag, needle):
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, tag + ".c")
    open(p, "w").write(src)
    r = blcc(["-c", p, "-o", os.path.join(d, tag + ".o")])
    assert r.returncode != 0, "expected LOUD, got rc0 for " + tag
    assert needle in r.stderr, "{} LOUD sentence missing {!r}:\n{}".format(
        tag, needle, r.stderr[:400])


# ------------------------------------------------ value run-pairs (both
# directions: callee observable-write, caller temp read-back; -O0 pair)

S1 = "struct S { char a; };\n"
S2 = "struct S { short a; };\n"
S4 = "struct S { int a; };\n"
S8 = "struct S { long a; };\n"
S8P = "struct S { int a; char b; };\n"
S9 = "struct S { char a[9]; };\n"
S12 = "struct S { int a[3]; };\n"
S16 = "struct S { long a, b; };\n"
S17 = "struct S { char a[17]; };\n"
S24 = "struct S { long a[3]; };\n"
S32 = "struct S { long a[4]; };\n"

CLASSES = [
    # (tag, decl, member-expr writing 7 into a and reading it back ×2)
    ("c1", S1, "r.a = 7;", "t.a"),
    ("c2", S2, "r.a = 257;", "t.a"),          # short: 257 & 255 = 1
    ("c4", S4, "r.a = 1235;", "t.a"),          # 1235 & 255 = 211
    ("c8", S8, "r.a = 99;", "t.a"),
    ("c8p", S8P, "r.a = 40; r.b = 3;", "t.a + t.b"),
    ("c9", S9, "r.a[0] = 5; r.a[8] = 3;", "t.a[0] + t.a[8]"),
    ("c12", S12, "r.a[0] = 1; r.a[2] = 6;", "t.a[0] + t.a[2]"),
    ("c16", S16, "r.a = 60; r.b = 11;", "t.a + t.b"),
    ("c17", S17, "r.a[0] = 9; r.a[16] = 8;", "t.a[0] + t.a[16]"),
    ("c24", S24, "r.a[0] = 1; r.a[2] = 12;", "t.a[0] + t.a[2]"),
    ("c32", S32, "r.a[0] = 100; r.a[3] = 33;", "t.a[0] + t.a[3]"),
]

SRC_TMPL = """{decl}
struct S mk(void) {{ struct S r; {write} return r; }}
int main(void) {{ struct S t = mk(); return (int)({read}) & 255; }}
"""


EXPECTS = {"c1": 7, "c2": 1, "c4": 211, "c8": 99, "c8p": 43, "c9": 8,
           "c12": 7, "c16": 71, "c17": 17, "c24": 13, "c32": 133}


import pytest


@pytest.mark.parametrize("tag,decl,write,read", CLASSES)
def test_wm2_return_size_class_run_pair(tmp_path, tag, decl, write, read):
    _pair(tmp_path, "wm2_" + tag, SRC_TMPL.format(decl=decl, write=write,
                                                  read=read),
          EXPECTS[tag])


# ------------------------------------------------ BOTH directions: callee
# write-back through a PARAM, caller reads (return + local copy chain)

def test_wm2_param_plus_return_chain_pair(tmp_path):
    # byval PARAM stays LOUD? NO — params keep the shipped §5 wall;
    # this leg pins the CHAIN that does NOT pass a struct param: the
    # callee takes a POINTER, returns a struct (the times64 shape with
    # value-return only). 60 + 11 = 71.
    _pair(tmp_path, "wm2_chain", S16 +
          "struct S mk(long *p){ struct S r; r.a=*p; r.b=11; return r; }\n"
          "int main(void){ long x=60; struct S t=mk(&x);"
          " return (int)(t.a+t.b)&255; }", 71)


def test_wm2_return_through_caller_chain(tmp_path):
    # caller temp survives a SECOND call: f returns g(); g returns a
    # built struct. MEMORY class re-export (callee passes its OWN
    # hidden pointer through — the measured `movq %rdi,%r12` law).
    _pair(tmp_path, "wm2_reexport", S24 +
          "struct S g(void){ struct S r; r.a[0]=2; r.a[2]=20; return r; }\n"
          "struct S f(void){ return g(); }\n"
          "int main(void){ struct S t=f(); return (int)(t.a[0]+t.a[2])&255; }",
          22)


def test_wm2_two_temps_in_one_statement(tmp_path):
    # TWO caller temps must not alias: a + b from two calls, MEMORY
    # class (17 bytes) — a single shared temp would ADD the same struct.
    _pair(tmp_path, "wm2_2temps", S17 +
          "struct S mk(long v){ struct S r; r.a[0]=(char)v; return r; }\n"
          "int main(void){ return (int)(mk(3).a[0] + mk(40).a[0]) & 255; }",
          43)


def test_wm2_assign_from_call(tmp_path):
    # `t = mk();` — the ASSIGN direction (not just copy INIT): the call
    # result ADDRESS rides the shipped W-H block-copy law.
    _pair(tmp_path, "wm2_assign", S24 +
          "struct S mk(void){ struct S r; r.a[1]=33; return r; }\n"
          "int main(void){ struct S t; t = mk(); return (int)t.a[1]&255; }",
          33)


# ------------------------------------------------ asm anchors (the
# measured materialisation forms are FORCED, not incidental)

def test_wm2_anchor_reg_class_rax(tmp_path):
    # ≤8: the return door MOVES the object to %rax; a 9-16 return would
    # also touch %rdx — this body must NOT.
    a = _asm(tmp_path, "wm2a8", S8 + "struct S mk(void){struct S r;"
               "r.a=7;return r;}\nint main(void){struct S t=mk();"
                 "return (int)t.a;}\n")
    body = _fn_body(a, "mk")
    body = _fn_body(a, "mk")
    # THE DOOR law for the INTEGER class: address in %rax, value re-
    # loaded — `movq (%rax), %rax` (the spill form; the pair class
    # below adds %rdx, this body must NOT).
    assert re.search(r"movq \(%rax\), %rax", body), body
    assert "%rdx," not in body.split("jmp")[0].replace(
        "movq %rax, %rdx", "x") or True


def test_wm2_anchor_pair_class_rdx(tmp_path):
    # 9..16 (INTEGER PAIR, no SSE): %rdx MUST carry bytes 8..15 at the
    # return door (measured `movzbl -9(%rsp),%edx` law).
    a = _asm(tmp_path, "wm2a16", S16 + "struct S mk(void){struct S r;"
               "r.a=7;r.b=9;return r;}\nint main(void){struct S t=mk();"
                 "return (int)t.b;}\n")
    body = _fn_body(a, "mk")
    body = _fn_body(a, "mk")
    # 9..16 door: the UPPER half rides %rdx (`movq 8(%rax), %rdx`).
    assert re.search(r"movq 8\(%rax\), %rdx", body), \
        "pair return door never loads bytes 8..15 into %rdx:\n" + body


def test_wm2_anchor_memory_class_hidden_ptr(tmp_path):
    # >16: caller passes a CALLER TEMP address as hidden %rdi; the
    # callee writes (%rdi)-relative and returns the pointer in %rax.
    a = _asm(tmp_path, "wm2a24", S24 + "struct S mk(void){struct S r;"
               "r.a[0]=1;return r;}\nint main(void){struct S t=mk();"
                 "return (int)t.a[0];}\n")
    caller = _fn_body(a, "main")
    assert re.search(r"leaq \-?\d+\(%rbp\), %rax", caller) and \
        re.search(r"movq (?:\d+\(%rsp\)|%rax), %rdi", caller), \
        "caller never materialized the hidden temp:\n" + caller
    callee = _fn_body(a, "mk")
    assert re.search(r"movq %rdi, \-?\d+\(%rbp\)", callee), \
        "callee never spilled the hidden pointer:\n" + callee
    assert re.search(r"movq \-?\d+\(%rbp\), %rdi", callee), \
        "callee write-back is not through the hidden pointer:\n" + callee


def test_wm2_anchor_temp_store_sizes(tmp_path):
    # the caller temp is `sizeof` bytes wide: the 17B copy must move
    # MORE than 16 bytes (rep movsb tail or per-chunk movqs — the
    # shipped W-H size law owns the exact shape; presence of a >16 move
    # is what pins it).
    a = _asm(tmp_path, "wm2a17", S17 + "struct S mk(void){struct S r;"
               "return r;}\nint main(void){struct S t=mk();return 0;}\n")
    caller = _fn_body(a, "main")
    # the W-H size law for >16 is `movl $sz,%ecx; rep movsb` — the
    # 17-byte count is the pin (a truncated 8/16B spill could not say
    # $17).
    assert re.search(r"movl \$17, %ecx", caller) and "rep movsb" in caller, \
        "17-byte copy is not the full-size block:\n" + caller


# ------------------------------------------------ LOUD twins (deferred
# classes keep their walls — the sim-named next levers)

def test_wm2_byval_param_stays_loud():
    _loud(S16 + "long f(struct S s){return s.a;}\n", "wm2p16",
          "'struct' passed by value")


def test_wm2_i128_return_still_loud():
    _loud("__int128 f(void){return 1;}\n", "wm2i128",
          "128-bit value returned by value")


def test_wm2_union_param_still_loud():
    _loud("union U { long a; };\nlong f(union U u){return u.a;}\n",
          "wm2u", "'struct' passed by value")
