"""M41 — extern / inline / union (contract §2.8), MC 12460.
Run legs pair against gcc 11.4 (gnu89 = the kernel's dialect). Symbol
shape is pinned with `nm` on blcc's OWN binary: gnu89 bare `inline` is an
EXTERNAL definition (T); `static inline` is local (t) — and blcc has NO
DCE (§2.8 v4/DA-m2-c3-2: it emits every parsed function; the gcc-−Os
"vanishes" fact is the ORACLE's, never a blcc emission rule);
`extern inline` emits NO symbol at all (gnu89 inline-only definition).
union = full decl + member access, every member at offset 0, size/align =
max member.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itlink")


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
    return None


def blcc_bin(src, tag):
    """Compile with blcc, return (path-to-binary, nm-symbol-lines)."""
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b], cwd=ROOT, capture_output=True, text=True,
                        timeout=60)
    os.remove(src_path)
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    nm = subprocess.run(["nm", out_b], capture_output=True, text=True,
                        timeout=30)
    assert nm.returncode == 0, nm.stderr
    return out_b, nm.stdout


# ---- extern (functions + variables) ------------------------------------------

def test_extern_fn_decl_then_def_run_pair():
    both_run("extern int twice(int a);\n"
             "int twice(int a) { return a * 2; }\n"
             "int main(void) { return twice(21); }\n", "ext-fn")


def test_extern_fn_asm_legs():
    p, syms = blcc_bin("int twice(int a){ return a * 2; }\n"
                       "int main(void){ return twice(21); }\n", "ext-fnm")
    # nm parity row §2.8: the definition is a GLOBAL text symbol.
    assert re.search(r"\bT twice\b", syms), "T twice missing: " + syms
    os.remove(p)


def test_extern_var_decl_run_pair():
    both_run("extern int g;\nint g = 41;\n"
             "int main(void) { return g + 1; }\n", "ext-var")


def test_extern_tentative_single_symbol():
    # `int g;` (tentative) + `extern int g;` re-decl = ONE object, not
    # two emissions (nm must show exactly one symbol named g).
    p, syms = blcc_bin("int g;\nextern int g;\n"
                       "int main(void){ g = 3; return g; }\n", "ext-tent")
    got = [ln for ln in syms.splitlines() if re.search(r"\bg\b$", ln)]
    assert len(got) == 1, "g must appear ONCE in nm: {!r}".format(syms)
    pb = subprocess.run([p], capture_output=True, timeout=30)
    assert pb.returncode == 3
    os.remove(p)


# ---- inline (gnu89 linkage trio) ---------------------------------------------

def test_gnu89_bare_inline_is_global():
    src = ("inline int f(void) { return 4; }\n"
           "int main(void) { return f() + 2; }\n")
    p, syms = blcc_bin(src, "inl-bare")
    assert re.search(r"\bT f\b", syms), \
        "gnu89 bare inline ⇒ GLOBAL T (§2.8 p10): " + syms
    os.remove(p)
    both_run(src, "inl-bare-run")


def test_static_inline_local_and_run_pair():
    src = ("static inline int h(void) { return 2; }\n"
           "int main(void) { return h() + 1; }\n")
    p, syms = blcc_bin(src, "inl-static")
    # blcc has NO DCE: `h` IS emitted — as a LOCAL symbol, never global.
    assert re.search(r"\bt h\b", syms), \
        "static inline ⇒ local t (§2.8): " + syms
    assert not re.search(r"\bT h\b", syms), syms
    os.remove(p)
    both_run(src, "inl-static-run")


def test_extern_inline_emits_no_symbol():
    # gnu89: `extern inline` is an inline-only definition — NO symbol.
    # (blcc still PARSES and COMPILES it; the emission is what must be
    # absent — §2.8 "no symbol, no static companion emitted".)
    p, syms = blcc_bin("extern inline int k(void) { return 1; }\n"
                       "int main(void) { return 0; }\n", "inl-ext")
    assert not re.search(r"\b[TtDdBbRrGg] k\b", syms), \
        "extern inline must emit NO symbol: " + syms
    pb = subprocess.run([p], capture_output=True, timeout=30)
    assert pb.returncode == 0
    os.remove(p)


# ---- union (§2.8: all members at offset 0; size/align = max) ----------------

UN = "union U { char c; int i; long l; };\n"


def test_union_member_aliasing_run_pair():
    # All members at offset 0: a long store is seen through int/char
    # (low bytes defined); the size = max member = 8.
    both_run(UN + """
long probe(void) {
    union U u;
    long r = 0;
    if (sizeof(union U) == 8) r += 100;
    u.l = 0x1122334455667788L;
    if ((u.c & 0xff) == 0x88) r += 1;
    if ((u.i & 0xffff) == 0x7788) r += 10;
    u.l = 5;
    if (u.i == 5) r += 1000;
    return r;
}
int main(void) { return (int)probe(); }
""", "un-alias")


def test_union_in_struct_run_pair():
    both_run(UN + """
struct S { union U u; int z; };
int main(void) {
    struct S s;
    s.u.l = 7;
    s.z = 1;
    if (s.u.i == 7 && sizeof(struct S) == 16) return 2;
    return 1;
}
""", "un-struct")


def test_union_array_stride_run_pair():
    both_run(UN + """
int main(void) {
    union U arr[2];
    arr[0].l = 1; arr[1].l = 9;
    if (arr[0].l == 1 && arr[1].i == 9 && (char*)arr == (char*)&arr[0])
        return 2;
    return 1;
}
""", "un-arr")


def test_union_sizeof_typedef_run_pair():
    both_run("typedef union { short a; long b; } U2;\n"
             "int main(void) { U2 x; x.b = 3; "
             "if (x.a == 3 && sizeof(U2) == 8) return 2; return 1; }\n",
             "un-td")


def test_union_decl_in_struct_inline_run_pair():
    both_run("""
struct S { union { int a; long b; } u; };
int main(void) { struct S s; s.u.b = 11; if (s.u.a == 11) return 2;
                 return 1; }
""", "un-inline")
