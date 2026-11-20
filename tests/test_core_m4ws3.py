# LINES reason: one wave (M4 W-S COMMIT-3, percpu-addressing law pins,
# card 12404.2.95): every leg is one row of the %gs/this_cpu law table.
r"""M4 W-S COMMIT-3 (MC 12716) — the percpu addressing law table,
MEASURED FIRST (own instrument .tmp/m4-ws/ws_laws.py, gcc 11.4 -Os) and
PINNED. Corpus fact named own-hands: `__seg_gs` / `__seg_fs` /
`this_base` appear in 0 of the 706 pinned streams (percpu.h's kernel
spelling goes through precpu_offset asm templates with an EXPLICIT `%gs`
prefix, not the C address-space keyword) — so the keyword itself stays
a NAMED LOUD parse wall (zero volume, never silent; the diverge row
below pins it), and what the corpus actually rides — the percpu SE +
typeof + `%gs`-asm idiom — must PAIR here, sizes b/w/l/q.

The p05 idiom dereferences at %gs base 0 in user space: BOTH compilers'
binaries segfault (measured -11 == -11) — the run-pair of the FAULT is
the observable law for user-space execution; the kernel-mode semantics
are what the cpufeature/precpu.h sites rely on and ride the same asm
operand machinery this table keeps honest.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]

GS_ASM = ("typedef unsigned char u8; typedef unsigned short u16;"
          " typedef unsigned int u32; typedef unsigned long ul;"
          " typedef unsigned long addr_t;\n"
          "static inline __attribute__((__always_inline__))"
          " u8 rdgs8(ul a){ u8 v; u8 *ptr=(u8*)({ ul p;"
          " __asm__(\"\" : \"=r\"(p) : \"0\"((void *)a));"
          " (typeof((void *)a))(p + (0)); });"
          " asm volatile(\"movb %%gs:%1,%0\" : \"=r\"(v) : \"m\"(*ptr));"
          " return v; }\n")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _pair(tag, src):
    c = "/dev/shm/ws3_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/ws3_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "law row must be valid C: " + g.stderr
    gex = _run("/dev/shm/ws3_%s.g" % tag)
    o = "/dev/shm/ws3_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "percpu law must COMPILE: " + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o", "/dev/shm/ws3_%s.b"
                           % tag], capture_output=True).returncode == 0
    assert _run("/dev/shm/ws3_%s.b" % tag) == gex, "%s: value pair" % tag


def test_ws3_percpu_read_idiom_pair():
    # THE percpu.h read shape: SE + typeof + `movb %%gs:%1,%0` — the
    # deref at base 0 FAULTS identically (measured -11 == -11).
    _pair("rd", GS_ASM + "u8 sink; int main(){ sink = rdgs8(0);"
          " return (int)sink; }")


def test_ws3_percpu_write_sizes_pair():
    # Sizes b/w/l/q of the %gs write idiom (precpu.h's `movb/movw/movl/
    # movq %%gs:` family): compile-pair the four widths, one function
    # each (posture law — the widths select the STORE operand size).
    src = (GS_ASM +
           "static inline __attribute__((__always_inline__))"
           " void wr8(u8 v, ul a){ u8 *p=(u8*)({ ul x;"
           " __asm__(\"\" : \"=r\"(x) : \"0\"((void *)a));"
           " (typeof((void *)a))(x + (0)); });"
           " asm volatile(\"movb %1,%%gs:%0\" : \"+m\"(*p) : \"qi\"(v)); }"
           "static inline __attribute__((__always_inline__))"
           " void wr16(u16 v, ul a){ u16 *p=(u16*)({ ul x;"
           " __asm__(\"\" : \"=r\"(x) : \"0\"((void *)a));"
           " (typeof((void *)a))(x + (0)); });"
           " asm volatile(\"movw %1,%%gs:%0\" : \"+m\"(*p) : \"ri\"(v)); }"
           "static inline __attribute__((__always_inline__))"
           " void wr32(u32 v, ul a){ u32 *p=(u32*)({ ul x;"
           " __asm__(\"\" : \"=r\"(x) : \"0\"((void *)a));"
           " (typeof((void *)a))(x + (0)); });"
           " asm volatile(\"movl %1,%%gs:%0\" : \"+m\"(*p) : \"r\"(v)); }"
           "static inline __attribute__((__always_inline__))"
           " void wr64(ul v, ul a){ ul *p=(ul*)({ ul x;"
           " __asm__(\"\" : \"=r\"(x) : \"0\"((void *)a));"
           " (typeof((void *)a))(x + (0)); });"
           " asm volatile(\"movq %1,%%gs:%0\" : \"+m\"(*p) : \"r\"(v)); }"
           "int main(){ if (0) { wr8(1,0); wr16(2,0); wr32(3,0);"
           " wr64(4,0); } return 0; }")
    _pair("wr", src)


def test_ws3_percpu_idiom_splices_and_heres_coexist():
    # INTERACTION: percpu SE-asm idiom + the COMMIT-2 `__here` scoped
    # label in ONE spliced body (the precpu.h + _THIS_IP_ family that
    # the 191-crowd streams actually carry).
    _pair("mix", GS_ASM +
          "static inline __attribute__((__always_inline__))"
          " ul ip(void){ return ({ __label__ __here; __here:"
          " (unsigned long)&&__here; }); }\n"
          "int main(){ u8 v = rdgs8(0); ul a = ip(); (void)v;"
          " return (int)((a & 1) | 8); }")


def test_ws3_seg_gs_keyword_named_loud_zero_volume():
    # NAMED wall (own-hands census): `__seg_gs` appears in 0/706 pinned
    # streams — the keyword stays a LOUD parse wall (gcc accepts it,
    # blcc refuses; zero volume, never silent). If a future stream
    # carries it, THIS leg is the first responder — extend at the
    # parser's qualifier seam with a NEW measured law table, not here.
    c = "/dev/shm/ws3_seg.c"
    open(c, "w").write("typedef unsigned char u8;\nu8 __seg_gs *gp;\n"
          "int main(){ return (int)(gp == 0); }\n")
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/ws3_seg.g"],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc accepts (keyword law)"
    b = blcc(["-c", c, "-o", "/dev/shm/ws3_seg.o"])
    assert b.returncode != 0, "keyword must stay a NAMED LOUD wall"
    assert "expected" in b.stderr, "wall must stand LOUD: " + b.stderr[:150]
