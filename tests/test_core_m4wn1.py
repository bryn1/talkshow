# LINES reason: one wave of legs (M4 W-N COMMIT-1 — the `%P` modifier
# at the ONE operand printer, card 12404.2.85) — the modifier law is
# ONE table; splitting it would separate a spelling from its guard
# neighbour (%c keeps its §3 L3 refusal at the SAME switch).
r"""M4 W-N COMMIT-1 — `%P` PRINTS THE ADDRESS, not a `$imm` (gcc-measured).

THE LAW (gcc 11.4 -std=gnu89 kernel recipe; tables .tmp/m4-wn/out/
measure-wn*.txt, ALL at MY hands): `%P` is the CONSTANT-MODIFIER that
prints its operand WITHOUT the `$` — and gcc's operand model answers by
FORM, the same law the §3 L3 guard already speaks:
  * `%P` on a MEMORY/address operand prints the address text itself
    (`g`, `12+gs` at gcc; blcc's pinned L3 spellings `g(%rip)`,
    `gs+12(%rip)`, the frame `-N(%rbp)`) — gcc rc0, blcc tip LOUD
    (the §3 L3 guard fired right for `%c` and too heavy for `%P`);
  * `%P` on a REGISTER prints the register (`movq %P1, %rax` with an
    "r" input: gcc `%rax`);
  * `%P` on an IMMEDIATE prints the raw value (`42`, `5`, `gs+16`) —
    the shipped M3 sym-call spelling, unchanged;
  * `%c` on memory stays gcc LOUD ('operand is not a condition code,
    invalid operand code c') — the guard is RIGHT there;
  * a doubled size modifier (`%Pq1`) is LOUD both sides.
THE MEASUREMENT THAT SIZES THE WAVE: 316 of the 706 pinned streams
first-block on exactly this — every `this_cpu_read_stable/percpu_*`
consumer passes `"p" (&(var))` under `%P` (arch/x86/include/asm/
current.h:15 is the kernel walk's first RED). THE MECHANISM: the ONE
substitution point `asmsub._asm_print` grows ONE arm — form-first,
never a parallel printer.
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


REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]


def _blcc_asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc(["-c", str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must compile:\n" + r.stderr
    return (tmp_path / (str(o) + ".s")).read_text()


# ---- THE WALK SHAPE: arch/x86/include/asm/current.h:15, VERBATIM from
# the post-pp stream (.tmp/m4-plan/streams/arch_x86_kernel_signal.c.i,
# line 2715 — the switch this_cpu_read_stable expands into). ----
CUR = """\
typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long u64;
struct task_struct;
extern __attribute__((section(".data" ""))) __typeof__(struct task_struct *) current_task;
struct task_struct *pscr(struct task_struct *out) {
 return ({ typeof(current_task) pscr_ret__; switch(sizeof(current_task)) { case 8: pscr_ret__ = ({ u64 pfo_val__; asm("mov" "q " "" "%" "P[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "p" (&(current_task))); (typeof(current_task))(unsigned long) pfo_val__; }); break; default: break; } pscr_ret__; });
}
int main(void){ return 0; }
"""


def test_wn1_current_h15_verbatim_stream(tmp_path):
    # BYTE-PARITY on the walk's first RED: the emitted substitution for
    # the verbatim current.h:15 asm statement — the `%P` on the "p"
    # (&(current_task)) MEMORY operand prints blcc's L3 address spelling
    # with NO `$` prefix, byte-identical to the plain-`%N` text of the
    # same operand and to the pinned stream line.
    a = _blcc_asm(tmp_path, "wn1cur", CUR)
    ab = a.split("\npscr:", 1)[1]
    m = re.search(r"movq? (\S*current_task\S*), %rax", ab)
    assert m, "no movq for the %P operand emitted:\n" + ab[:800]
    assert m.group(1) == "current_task(%rip)", \
        ("current.h:15 verbatim: %%P must print the ADDRESS text "
         "(blcc L3 form, the pinned M3 §3.5 spelling class), got %r"
         % m.group(1))
    assert "$" not in m.group(1)


def test_wn1_current_h15_run_pair(tmp_path):
    # The address is the VALUE law too: reading through the %P address
    # returns the same byte both compilers.
    src = ('long gv = 77;\nlong f(void){ long r;\n'
           ' asm("movq %P1, %0" : "=r"(r) : "p"(&gv)); return r; }\n'
           'int main(void){ return (int)f() & 0xFF; }\n')
    s = tmp_path / "wn1rp.c"
    s.write_text(src)
    gx = tmp_path / "wn1rp.gcc"
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)])
    assert g.returncode == 0, g.stderr
    bx = tmp_path / "wn1rp.blcc"
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    assert gv.returncode == 77, "oracle moved: {}".format(gv.returncode)
    assert bv.returncode == 77, "blcc answer: {}".format(bv.returncode)


PRE = ("int g; long gv = 77; int gs[8]; struct P { long a, b; } gp;\n"
       "const int c = 5;\nlong f(void);\nint main(void){ return 0; }\n")
TPL = 'long f(void){{ long r; long v = 3; asm("movq {}, %%r11" : "=a"(r) : {}); return r; }}\n'  # noqa: E501

# (tag, modifier, constraint-expr, gcc-answer-class, blcc-answer)
P_TABLE = [
    # global address via "p": gcc prints the symbol (absolute REC form);
    # blcc prints its L3 rip form — the ADDRESS text, no `$`.
    ("pg", "%P1", '"p"(&g)', None, "g(%rip)"),
    ("pelem", "%P1", '"p"(&gs[3])', None, "gs+12(%rip)"),
    ("pmember", "%P1", '"p"(&gp.b)', None, "gp+8(%rip)"),
    # frame slot under "m": gcc prints the FRAME text (`-8(%rsp)`
    # measured) — blcc answers its own frame form, no `$`:
    ("pframe", "%P1", '"m"(v)', None, None),       # layout-own: class-pinned
    # reg operand: the REGISTER prints (gcc `%rax`)
    ("preg", "%P1", '"r"(r)', None, None),         # class: a %reg, no $
    # immediates: the RAW value (no `$`) — already shipped, re-pinned
    ("pimm", "%P1", '"i"(42)', "42", "42"),
    ("pconst", "%P1", '"i"(c)', "5", "5"),
    ("psym", "%P1", '"i"((long)&gs[8]+3)', None, "gs+35"),
]


import pytest


@pytest.mark.parametrize("tag,mod,cexpr,gccwant,blccwant", P_TABLE)
def test_wn1_P_table(tmp_path, tag, mod, cexpr, gccwant, blccwant):
    src = PRE + TPL.format(mod, cexpr)
    s = tmp_path / ("wn1" + tag + ".c")
    s.write_text(src)
    x = tmp_path / ("wn1" + tag + ".gcc.s")
    g = gcc(REC + ["-S", str(s), "-o", str(x)])
    assert g.returncode == 0, "gcc must accept %%P: " + g.stderr
    ga = x.read_text()
    gb = ga.split("\nf:", 1)[1] if "\nf:" in ga else ga
    gm = re.search(r"movq (\S+), %r11", gb)
    assert gm, "no gcc movq:\n" + gb[:400]
    a = _blcc_asm(tmp_path, "wn1" + tag, src)
    ab = a.split("\nf:", 1)[1]
    m = re.search(r"movq (\S+), %r11", ab)
    assert m, "no blcc movq:\n" + a[:400]
    got = m.group(1)
    assert "$" not in got, "%%P prints the ADDRESS — no `$`: %r" % got
    if blccwant is not None:
        assert got == blccwant, "{}: blcc printed {}".format(tag, got)
    elif tag == "pframe":
        assert re.fullmatch(r"-?\d+\(%rbp\)", got), \
            "frame text expected, got %r" % got
        assert re.fullmatch(r"-?\d+\(%r(?:bp|sp)\)", gm.group(1)), \
            "gcc frame text expected, got %r" % gm.group(1)
    elif tag == "preg":
        assert got.startswith("%") and gm.group(1).startswith("%"), \
            "%P on a REG prints the register: blcc %r gcc %r" % (
                got, gm.group(1))


def test_wn1_P_equals_plain_N(tmp_path):
    # THE ONE LAW: %P on a MEMORY operand is what the plain %N already
    # prints — the address text, `$`-less. Byte-equal by construction.
    src = PRE + TPL.format("%1", '"p"(&gs[3])')
    pa = _blcc_asm(tmp_path, "wn1n0", src).split("\nf:", 1)[1]
    plain = re.search(r"movq (\S+), %r11", pa)
    srcP = PRE + TPL.format("%P1", '"p"(&gs[3])')
    pb = _blcc_asm(tmp_path, "wn1nP", srcP).split("\nf:", 1)[1]
    pform = re.search(r"movq (\S+), %r11", pb)
    assert plain and pform
    assert plain.group(1) == pform.group(1) == "gs+12(%rip)"


def test_wn1_c_on_memory_stays_loud(tmp_path):
    # %c on a MEMORY operand: gcc rc1 ('invalid operand code c'), blcc
    # LOUD — the §3 L3 guard is RIGHT for %c and this leg pins that the
    # %P fix did NOT widen it.
    src = PRE + TPL.format("%c1", '"m"(gv)')
    s = tmp_path / "wn1cm.c"
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode != 0 and "operand code" in g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn1cm.o")])
    assert b.returncode != 0


def test_wn1_P_offset_value_run_pair(tmp_path):
    # The address TEXT is the VALUE law: `movq %P1, %0` with "p"(&gs[3])
    # loads gs[3] — the OFFSET SIGN rides the exit code (the W-N gate
    # found the M3-A seed's flipped `-off`: gs-12 materialized silently).
    src = ("int gs[8] = {1, 2, 3, 4, 5, 6, 7, 8};\n"
           "int main(void){ long v;\n"
           ' asm("movq %P1, %0" : "=r"(v) : "p"(&gs[3]));\n'
           " return (int)v & 0xFF; }\n")
    s = tmp_path / "wn1sgn.c"
    s.write_text(src)
    gx = tmp_path / "wn1sgn.gcc"
    g = gcc(["-O0", "-no-pie", str(s), "-o", str(gx)])
    assert g.returncode == 0, g.stderr
    bx = tmp_path / "wn1sgn.blcc"
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    gv = subprocess.run([str(gx)], capture_output=True, text=True)
    bv = subprocess.run([str(bx)], capture_output=True, text=True)
    assert gv.returncode == 4, "oracle moved: {}".format(gv.returncode)
    assert bv.returncode == 4, "blcc loaded from %r" % bv.returncode


def test_wn1_P_on_p_local_loud(tmp_path):
    # `%P` on a `"p"` OPERAND that is a frame address ("p"(&v)): gcc
    # rc1 'invalid expression as operand' — a runtime address is not a
    # constant. blcc LOUDS (the printer checks the text, not the shape).
    src = PRE + TPL.format("%P1", '"p"(&v)')
    s = tmp_path / "wn1pl.c"
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode != 0 and "invalid expression" in g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn1pl.o")])
    assert b.returncode != 0, "%%P on a frame address must stay LOUD"


def test_wn1_P_on_m_computed_honest_wall(tmp_path):
    # NAMED honest wall: `%P` on a COMPUTED "m" (`gs[i]`): gcc emits the
    # computed text `gs(,%rdi,4)` (rc0); blcc's model materializes the
    # address into a register and REFUSES the text — LOUD, named (corpus
    # volume 0: the 316-stream wall is the `p`-symbol spelling).
    src = (PRE + TPL.format("%P1", '"m"(gs[i])')).replace(
        "long f(void)", "long f(long i)")
    s = tmp_path / "wn1mc.c"
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode == 0, "gcc emits computed text (measured)"
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn1mc.o")])
    assert b.returncode != 0


def test_wn1_Pq_doubled_loud(tmp_path):
    # `%Pq1` — gcc LOUD rc1; the §3.5 modifier table stays closed.
    src = PRE + TPL.format("%Pq1", '"r"(r)')
    s = tmp_path / "wn1pq.c"
    s.write_text(src)
    g = gcc(REC + ["-S", str(s), "-o", "/dev/null"])
    assert g.returncode != 0
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wn1pq.o")])
    assert b.returncode != 0
