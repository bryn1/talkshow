# LINES reason: one wave of legs (M4 W-L COMMIT-1 — the REAL >6-argument
# call-ABI: caller spill block + callee read-back; card 12404.2.81) — the
# spill block and the read-back are ONE law proven from BOTH directions;
# splitting would separate the run-pair from the asm anchors that make a
# wrong slot offset visible.
r"""M4 W-L COMMIT-1 — REAL >6-ARGUMENT CALL-ABI (stack passing).

THE WALL (the ladder's #1, 335 first-blockers, ALL naming the one 7-param
static-inline print_hex_dump_debug; gate MC 12664 F-7: a wall-flip alone
ICEs 90/90 — `_stage_call` had no 7th slot). THE LAW (measured at MY OWN
hands, table + methodology in tests/test_core_m4wl0.py, gcc -Os kernel
recipe, two-TU probes):
  caller  args 1..6 ride rdi,rsi,rdx,rcx,r8,r9; args 7+ go into 8-byte
          stack slots, pushed RIGHT-TO-LEFT (first stack arg LOWEST, at
          the return address); the call site keeps rsp ≡ 0 (mod 16) AT the
          call instruction — an ODD K costs 8 bytes of pad, an EVEN K
          rides the §2.14 shipped `subq $16` unchanged; ONE addq restores.
  callee  arg(7+i) lands at 16(%rbp)+8i — 16(%rbp), 24(%rbp), 32(%rbp)…;
          blcc spills it into its own slot through the SAME prologue loop
          the register params ride (only the SOURCE differs).
  red zone  nothing lives below %rsp (the kernel builds -mno-red-zone);
          the spill block reserves with a REAL subq BEFORE the pushes.
MECHANISM (extend, never parallel): the shipped §2.14 variadic push block
IN `_stage_call` IS the block — its gate becomes `len(slots) > 6` (fixed
AND variadic), its fixed `subq $16` becomes pad = 16 (even K, byte-identical
to the shipped sequence the M2 §2.14 pins hold) / 8 (odd K — the alignment
LAW the old block broke at odd K: subq $16 + an odd number of pushes left
rsp ≡ 8 AT the call, invisible to the GP-only kernel callees, WRONG to any
SSE one). The callee gains the read-back SOURCE in the ONE prologue spill
loop; the `>6 params`/`>6 args` §6 walls die; the marker
test_core_m2_va.py::test_fixed_gt6_stays_loud FLIPS (never deleted).
A VARIADIC CALLEE with >6 NAMED params STAYS LOUD (kernel va_start is the
`&last + sizeof(last)` adjacency law — the named>6 form needs the incoming
area to BE the params; volume 0; named LOUD-DIV twin below).
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
    # cut at the NEXT function label (a line that starts col 0 and ends
    # with ":") so anchors assert on ONE function's instructions.
    nxt = re.search(r"\n\.[ \t]*\.globl|\n(\.|[A-Za-z_][\w.]*):\n",
                    body)
    return body[:nxt.start()] if nxt else body


# ------------------------------------------------- THE run-pairs (values)

def test_wl1_seven_scalars_pair(tmp_path):
    # K=1: 1 stack slot + pad. 1+2+3+4+5+6+7 = 28.
    _pair(tmp_path, "wl1_s7",
          "long g7(long a,long b,long c,long d,long e,long f,long g)"
          "{return a+b+c+d+e+f+g;}\n"
          "int main(void){return (int)g7(1,2,3,4,5,6,7);}\n", 28)


def test_wl1_eight_scalars_pair(tmp_path):
    # K=2: the §2.14 shape — two pushes, no extra pad. 1+8 = 9 (a+h).
    _pair(tmp_path, "wl1_s8",
          "long g8(long a,long b,long c,long d,long e,long f,long g,long h)"
          "{return a+h;}\n"
          "int main(void){return (int)g8(1,2,3,4,5,6,7,8);}\n", 9)


def test_wl1_nine_scalars_pair(tmp_path):
    # K=3 (odd): 3 arg pushes + 8B pad. Negative 7th rides the slot.
    _pair(tmp_path, "wl1_s9",
          "long g9(long a,long b,long c,long d,long e,long f,long g,"
          "long h,long i){return a+i+g;}\n"
          "int main(void){return (int)g9(10,2,3,4,5,6,-7,8,9);}\n", 12)


def test_wl1_ten_scalars_pair(tmp_path):
    # K=4: read-back offsets 16,24,32,40(%rbp) all exercised. 70+80+90+100
    # mod 251 = 340-251 = 89.
    _pair(tmp_path, "wl1_s10",
          "long p10(long a,long b,long c,long d,long e,long f,long g,"
          "long h,long i,long j){return g+h+i+j;}\n"
          "int main(void){return (int)p10(1,2,3,4,5,6,70,80,90,100)%251;}\n",
          89)


def test_wl1_address_taken_stack_param_pair(tmp_path):
    # &p7 — the address of a stack param (blcc's spill-slot law answers the
    # COPY's address; value observables identical — the run-pair proves it).
    _pair(tmp_path, "wl1_addr7",
          "long pa(long a,long b,long c,long d,long e,long f,long g)"
          "{long *p=&g; return *p + a;}\n"
          "int main(void){return (int)pa(1,2,3,4,5,6,100);}\n", 101 % 256)


def test_wl1_width_mix_stack_slot_pair(tmp_path):
    # Sub-8 args into stack slots ride FULL 8-byte extended slots
    # (char -2 sign-extends, short 300 lands whole): measured m06.
    _pair(tmp_path, "wl1_width",
          "int m7(int a,char b,long c,int d,char e,short f,int g)"
          "{return a+g+f+b;}\n"
          "int main(void){int r=m7(1,(char)-2,3,4,(char)-3,(short)300,10);"
          " return (r+1000)%256;}\n", (1 + 10 + 300 - 2 + 1000) % 256)


def test_wl1_callee_writes_param_pair(tmp_path):
    # A stack param is still PASS-BY-VALUE: the callee overwrites p7 and
    # p8; the caller's own variables are untouched.
    _pair(tmp_path, "wl1_byval",
          "long wb(long a,long b,long c,long d,long e,long f,long g,"
          "long h){g=g*2;h=h+1;return g+h;}\n"
          "int main(void){long x=5,y=6;long r=wb(1,2,3,4,5,6,x,y);\n"
          "  if (x!=5||y!=6) return 1; return (int)(r==17?7:0);}\n", 7)


def test_wl1_nested_call_in_stack_arg_pair(tmp_path):
    # The 7th arg is a CALL (m11/m13: the inner call completes BEFORE the
    # outer push block stages; side-effect visible through a global).
    _pair(tmp_path, "wl1_nest",
          "long side;\nlong bump(long v){side+=v;return side;}\n"
          "long g7(long a,long b,long c,long d,long e,long f,long g)"
          "{return a+g;}\n"
          "int main(void){long r=g7(10,2,3,4,5,6,bump(32));\n"
          "  if (side!=32) return 1; return (int)(r==42?6:0);}\n", 6)


def test_wl1_indirect_seven_pair(tmp_path):
    # The indirect arm rides the SAME block (fn-ptr to a 7-param fn).
    _pair(tmp_path, "wl1_ind",
          "long g7(long a,long b,long c,long d,long e,long f,long g)"
          "{return a+b+g;}\n"
          "int main(void){long (*fp)(long,long,long,long,long,long,long)"
          "=g7; return (int)fp(1,2,3,4,5,6,7);}\n", 10)


def test_wl1_caller_with_own_stack_args_pair(tmp_path):
    # A >6-arg function CALLING another >6 function: the callee reads its
    # incoming slots while its own frame (locals + temps) is live — the
    # 16(%rbp) law is INDEPENDENT of the caller's frame size.
    _pair(tmp_path, "wl1_nested77",
          "long add2(long x,long y){return x+y;}\n"
          "long g7(long a,long b,long c,long d,long e,long f,long g)"
          "{return add2(a,g);}\n"
          "long h7(long a,long b,long c,long d,long e,long f,long g)"
          "{return g7(a,b,c,d,e,f,g)+add2(b,f);}\n"
          "int main(void){return (int)h7(1,2,3,4,5,6,20);}\n", 21 + 8)


def test_wl1_loop_stability_pair(tmp_path):
    # TEN calls through the spill block: temps must unwind exactly (an
    # _unt leak grows the frame and corrupts LATER calls).
    _pair(tmp_path, "wl1_loop",
          "long g7(long a,long b,long c,long d,long e,long f,long g)"
          "{return a+b+c+d+e+f+g;}\n"
          "int main(void){long t=0;int i;for(i=0;i<10;i++) t+=g7(i,1,2,3,4,5,6);\n"
          "  return (int)(t%251);}\n", (45 + 10 * 21) % 251)


def test_wl1_call_in_condition_pair(tmp_path):
    # A >6 call in an IF condition: the staging block sits INSIDE the
    # control flow — rsp restore on every branch.
    _pair(tmp_path, "wl1_cond",
          "long g7(long a,long b,long c,long d,long e,long f,long g)"
          "{return a+b+c+d+e+f+g;}\n"
          "int main(void){long x=0;if(g7(1,1,1,1,1,1,1)==7)x=3;\n"
          "  else x=9; if(g7(2,2,2,2,2,2,2)!=13)x+=4; return (int)x;}\n",
          3 + 4)


def test_wl1_static_callee_pair(tmp_path):
    # static linkage + a global-memory operand through the 7th slot.
    _pair(tmp_path, "wl1_static",
          "long w;\nstatic void put7(long a,long b,long c,long d,long e,"
          "long f,long g){w=a+g;}\n"
          "int main(void){put7(1,2,3,4,5,6,41);return (int)(w==42?8:0);}\n",
          8)


def test_wl1_hex_dump_debug_verbatim(tmp_path):
    # F-7 VERBATIM (printk.h:604 non-DEBUG body, 7 params, EMPTY body —
    # the 335-first-blocker function). With the wall flipped but no stack
    # passing this ICEd (IndexError, no 7th staging slot): it must now
    # COMPILE and the call site must run pair-clean.
    _pair(tmp_path, "wl1_hexdump",
          "typedef unsigned long size_t;\n"
          "static inline void print_hex_dump_debug(const char *prefix_str,"
          " int prefix_type, int rowsize, int groupsize,\n"
          "\t\t\t\tconst void *buf, size_t len, _Bool ascii)\n{\n}\n"
          "char buf[32];\nint main(void){print_hex_dump_debug(\"p:\",0,16,4,"
          "buf,32,0);return 21;}\n", 21)


# ------------------------------------------- deterministic asm anchors

def test_wl1_caller_spill_offsets_anchor(tmp_path):
    # K=1: pad 8 + ONE push + addq $16; pushes read the staged slots from
    # INSIDE the frame ABOVE the pad (off-by-8 here = the tooth plant).
    asm = _asm(tmp_path, "wl1_a1",
               "long g7(long a,long b,long c,long d,long e,long f,long g)"
               "{return a+g;}\n"
               "long m(long x){return g7(x,2,3,4,5,6,x);}\n"
               "int main(void){return (int)m(1);}\n")
    body = _fn_body(asm, "m")
    i_sub = body.index("subq $8, %rsp")
    i_push = re.search(r"pushq \d+\(%rsp\)", body).start()
    i_call = body.index("call g7")
    assert i_sub < i_push < i_call, "subq BEFORE pushes BEFORE call: " + body
    assert "addq $16, %rsp" in body, "one addq restores pad+slot: " + body
    pushes = re.findall(r"pushq (\d+)\(%rsp\)", body)
    assert len(pushes) == 1 and int(pushes[0]) % 8 == 0, body
    # the pushed slot is the 7th arg's staged temp T7: 8*7 above the frame
    # base, shifted by the 8-byte pad => 8*(0+6+1) + 8 = 64.
    assert pushes[0] == "64", "spill slot offset for arg 7 (K=1): " + body


def test_wl1_even_k_keeps_shipped_sequence_anchor(tmp_path):
    # K=2 rides the §2.14 SHIPPED sequence UNCHANGED (subq $16, two
    # descending pushes, addq $32) — the M2 pin law byte-preserved.
    asm = _asm(tmp_path, "wl1_a2",
               "long g8(long a,long b,long c,long d,long e,long f,long g,"
               "long h){return a+h;}\n"
               "long m(long x){return g8(x,2,3,4,5,6,7,x);}\n"
               "int main(void){return (int)m(1);}\n")
    body = _fn_body(asm, "m")
    assert "subq $16, %rsp" in body, body
    pushes = [int(x) for x in re.findall(r"pushq (\d+)\(%rsp\)", body)]
    # Shifted-read law (m4wk1 §2.14 pin form): after `subq $16` the FIRST
    # push reads arg 8 (temp slot 8) at 8*8+16 = 80; after that push the
    # SAME-adjacent slot for arg 7 (temp 7) is 8*7+16+8 = 80 again — the
    # offsets are EQUAL, the addresses descend by 8. Emission order is
    # arg 8 then arg 7 (arg 7 ends LOWEST, at the return address).
    assert len(pushes) == 2 and pushes[0] == pushes[1] == 80, \
        "shifted 80/80 read of the adjacent slot pair: " + body
    assert "addq $32, %rsp" in body, body


def test_wl1_callee_readback_offsets_anchor(tmp_path):
    # args 7..9 spill from 16,24,32(%rbp) through the ONE prologue loop.
    asm = _asm(tmp_path, "wl1_a3",
               "long p9(long a,long b,long c,long d,long e,long f,long g,"
               "long h,long i){return g+h+i;}\n"
               "int main(void){return (int)p9(1,2,3,4,5,6,7,8,9);}\n")
    body = _fn_body(asm, "p9")
    for off in ("16", "24", "32"):
        assert "movq {}(%rbp), ".format(off) in body, \
            "read-back of arg @{}(%rbp): ".format(off) + body


def test_wl1_alignment_invariant_leg(tmp_path):
    # THE red-zone/alignment law over EVERY call site of a mixed file:
    # bytes adjusted at each call (pad subq + pushes) are 16-multiples,
    # so rsp ≡ 0 (mod 16) AT the call; and nothing is ever addressed
    # below %rsp (no negative (%rsp) reference anywhere).
    asm = _asm(tmp_path, "wl1_a4",
               "long g7(long a,long b,long c,long d,long e,long f,long g)"
               "{return a+g;}\n"
               "long g9(long a,long b,long c,long d,long e,long f,long g,"
               "long h,long i){return a+i;}\n"
               "long a(long x){return g7(x,1,2,3,4,5,x)+g9(x,1,2,3,4,5,6,"
               "7,x);}\n"
               "int main(void){return (int)a(4);}\n")
    assert not re.search(r"-\d+\(%rsp\)", asm), \
        "nothing may live below %rsp (kernel -mno-red-zone): " + asm
    body = asm.split("a(long x)", 1) and _fn_body(asm, "a")
    # Walking displacement law: track bytes off the frame base at every
    # `call`; (D + 8) % 16 == 0 means rsp is 16-aligned AT the call
    # (the call itself pushes 8). Covers the prologue, both blocks, and
    # the epilogue in ONE scan — no block-splitting assumptions.
    d = 0
    for m in re.finditer(
            r"subq \$(\d+), %rsp|addq \$(\d+), %rsp|pushq [^\n]+|popq "
            r"[^\n]+|(call [\w.]+)", body):
        tok = m.group(0)
        if tok.startswith("subq"):
            d += int(m.group(1))
        elif tok.startswith("addq"):
            d -= int(m.group(2))
        elif tok.startswith("pushq"):
            d += 8
        elif tok.startswith("popq"):
            d -= 8
        else:
            assert (d + 8) % 16 == 0, \
                "call site misaligned by {}B in a(): {}".format(d, body)


# --------------------------------- LOUD twins that MUST survive the flip

def test_wl1_struct_by_value_all_classes_build(tmp_path):
    # M4 W-M COMMIT-4 (MC 12670) moved the ≤16 boundary; M4 W-X
    # COMMIT-X (MC 12756) shipped the MEMORY class (>16) — the whole
    # 7×3 matrix now BUILDS (sizes 1..16 ride the pair law UNCHANGED,
    # size 24 rides the ascending incoming words; the 7-arg spellings
    # cover the stack-pair/no-split paths through the W-L push block
    # for BOTH classes). The former size-24 LOUD arm was W-M's named
    # KEEP, retired BY NAME at COMMIT-X; its values are run-paired in
    # tests/test_core_m4wx1.py (the battery), posture here is rc0.
    for size, decl in ((1, "struct S{char a;}"), (2, "struct S{char a,b;}"),
                       (4, "struct S{int a;}"), (8, "struct S{long a;}"),
                       (12, "struct S{int a,b,c;}"),
                       (16, "struct S{long a,b;}"),
                       (24, "struct S{long a,b,c;}")):
        for tag, src in (
            ("s6", decl + ";\nlong f6(struct S p,long b,long c,long d,"
             "long e,long f){return p.a;}\n"
             "int main(void){struct S p;return (int)f6(p,1,2,3,4,5);}\n"),
            ("s7mid", decl + ";\nlong f7(long a,long b,long c,long d,"
             "long e,long f,struct S g){return g.a;}\n"
             "int main(void){struct S p;return (int)f7(1,2,3,4,5,6,p);}\n"),
            ("s7first", decl + ";\nlong f7(struct S p,long b,long c,long d,"
             "long e,long f,long g){return p.a;}\n"
             "int main(void){struct S p;return (int)f7(p,1,2,3,4,5,"
             "6);}\n")):
            s = tmp_path / ("wl1_sv_%d_%s.c" % (size, tag))
            s.write_text(src)
            b = blcc(["-c", str(s), "-o", str(tmp_path / "wl1_sv.o")])
            assert b.returncode == 0, "%s %s must build (W-X MEMORY \
class, MC 12756):\n%s" % (size, tag, b.stderr)


def test_wl1_variadic_named_gt6_stays_loud(tmp_path):
    # The kernel's va_start is `&last + sizeof(last)` — with >6 NAMED
    # params the adjacency law needs the INCOMING area to BE the params.
    # Volume 0; gcc rc0 — a NAMED LOUD-DIV twin, not a silent accept.
    s = tmp_path / "wl1_va7.c"
    s.write_text("int v7(int a,long b,long c,long d,long e,long f,long g,"
                 " ...){return a;}\nint main(void){return v7(1,2,3,4,5,6,7,"
                 "8);}\n")
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wl1_va7.g.o")])
    assert g.returncode == 0, "gcc accepts (named divergence):\n" + g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wl1_va7.b.o")])
    assert b.returncode != 0, "variadic named>6 stays LOUD (volume 0)"
