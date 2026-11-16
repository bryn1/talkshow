"""M4 W3 (MC 12563) — INDIRECT CALLS, plan §2 (R1–R10).

One file per wave-leg-cluster (file hygiene): commit-1 = the CORE law —
a call through a FUNCTION-POINTER VALUE (bare `fp(x)`, the deref form
`(*fp)(x)`, a typedef'd target, NULL-check-then-call) — with the oracle
asm/reloc parity legs and run-pairs. Commit-2 = the addressing SHAPES
(table slot, struct member, array of fns); commit-3 = %r10 variadic;
commit-4 = the twins that STAY LOUD + §6 .set-alias.

Oracle captured at .tmp/m4-w3/out/indir.s (gcc 11.4, kernel recipe
-std=gnu89; -O0 -fno-pic for asm/reloc parity): the callee reaches a
SCRATCH register and the call is `call *%reg` — NEVER a call relocation;
the named call arm keeps R_X86_64_PLT32 name-0x4 (measured W2 fact).
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.environ.get("BLCC_REPO") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + args,
                          capture_output=True, text=True)


def link_run(tmp_path, tag, o):
    base = tmp_path / (tag + ".bin")
    r = subprocess.run(["ld", "-static", "-o", str(base), str(o)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    run = subprocess.run([str(base)], capture_output=True, text=True)
    return run.returncode


# ---- R1/R2: the CORE call-through-value law -------------------------------

VIA = ("typedef unsigned long size_t;\n"
       "static long add(long a, long b){ return a + b; }\n"
       "static long via(long (*f)(long, long)){ return f(4, 5); }\n"
       "int main(void){ return (int)via(add); }\n")


def _pair(tmp_path, tag, src, expect):
    """ORACLE-DECIDES (the shipped run_pair shape): full link both sides
    — gcc with its CRT, blcc with the §6 blob — run, SAME exit code."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc([str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode == expect, \
        "run-pair: gcc {} blcc {} expect {}".format(
            g.returncode, b.returncode, expect)


def test_call_through_fnptr_value(tmp_path):
    _pair(tmp_path, "iv0", VIA, 9)              # 4+5 == 9, both sides


def test_call_star_deref_form(tmp_path):
    # `(*fp)(x)` IS `fp(x)` (measured rc0; the §1 pointer arithmetic law)
    src = VIA.replace("return f(4, 5);", "return (*f)(4, 5);")
    _pair(tmp_path, "iv1", src, 9)


def test_typedef_fnptr_param_call(tmp_path):
    # THE corpus witness behind the 2 undeclared-`cmp` call first-blockers:
    # `typedef int (*cmp_t)(const void*, const void*); … c(a, b);`
    src = ("typedef unsigned long size_t;\n"
           "typedef int (*cmp_t)(const void *, const void *);\n"
           "static long a[2] = {7, 9};\n"
           "static int mycmp(const void *x, const void *y);"
           "static long sortish(cmp_t c){ return c(a, a + 1); }\n"
           "static int mycmp(const void *x, const void *y){ "
           "(void)x; (void)y; return 3; }\n"
           "int main(void){ return (int)sortish(mycmp); }\n")
    _pair(tmp_path, "iv2", src, 3)


def test_null_check_then_call(tmp_path):
    # the shipped truthy law on a fn-ptr + the call — no compiler check
    src = ("typedef unsigned long size_t;\n"
           "static long add(long a, long b){ return a + b; }\n"
           "static long nullish(long (*f)(long, long)){ "
           "if (f) return f(2, 5); return 0; }\n"
           "int main(void){ return (int)nullish(add); }\n")
    _pair(tmp_path, "iv3", src, 7)


def test_call_target_load_is_scratch_reg_indirect(tmp_path):
    # Oracle shape law (indir.s): the indirect call is `call *%reg` and
    # the .text carries NO relocation for it; the NAMED call in the same
    # TU keeps R_X86_64_PLT32 name-0x4 — the TWO addressing shapes stay
    # DIFFERENT in blcc too (this card's contract row). SAME flags both
    # sides (-O0 -fno-pic): -Os tail-calls the direct arm away and the
    # comparison would chase a shape gcc never emitted.
    src = ("typedef unsigned long size_t;\n"
           "long add(long, long);\n"
           "static long via(long (*f)(long, long)){ return f(4, 5); }\n"
           "int main(void){ return (int)(via(add) + add(1, 2)); }\n")
    s = tmp_path / "iv4.c"
    s.write_text(src)
    go = tmp_path / "iv4.gcc.o"
    gr = subprocess.run(["gcc", "-std=gnu89", "-O0", "-fno-pic", "-c",
                         str(s), "-o", str(go)],
                        capture_output=True, text=True)
    assert gr.returncode == 0, gr.stderr
    bo = tmp_path / "iv4.blcc.o"
    br = blcc(["-c", str(s), "-o", str(bo)])
    assert br.returncode == 0, br.stderr
    bt = blcc(["--emit-asm", "-c", str(s), "-o",
                str(tmp_path / "iv4.b")]).stdout
    assert re.search(r"call \*%r", bt), bt          # indirect: star form
    gt_r = subprocess.run(["readelf", "-r", str(go)],
                          capture_output=True, text=True).stdout
    bt_r = subprocess.run(["readelf", "-r", str(bo)],
                          capture_output=True, text=True).stdout

    def text_arms(out):
        blk = re.search(r"\.rela\.text.*?\n(.*?)(?:\n\n|\Z)", out, re.S)
        assert blk, out
        return re.findall(r"(R_X86_64_\S+)\s+\S+\s+(\S+ ?[+-] ?\S+)",
                          blk.group(1))
    g_arms, b_arms = text_arms(gt_r), text_arms(bt_r)
    # 1. the DIRECT call arm: PLT32 `add-4` on BOTH (W2-measured fact,
    #    now exercised through the kernel-recipe flags on a TU that also
    #    carries an indirect call) — and EXACTLY one each (multiset, not
    #    membership: an indirect call that degenerated into a direct one
    #    would add a second PLT32 arm here — the tooth plant named in the
    #    close-leg proves this leg goes RED on exactly that mutation).
    assert [a for a in g_arms if a[0] == "R_X86_64_PLT32"] == \
        [("R_X86_64_PLT32", "add - 4")], g_arms
    assert [a for a in b_arms if a[0] == "R_X86_64_PLT32"] == \
        [("R_X86_64_PLT32", "add - 4")], b_arms
    # 2. the INDIRECT call arm adds NOTHING on either side: the remaining
    #    text reloc is the fn-VALUE arm (`via(add)` — gcc answers
    #    R_X86_64_32, blcc the W2-pinned R_X86_64_32S on movq $sym —
    #    that name split is the W2 value law, not a W3 call fact).
    g_rest = [a for a in g_arms if a[0] != "R_X86_64_PLT32"]
    b_rest = [a for a in b_arms if a[0] != "R_X86_64_PLT32"]
    assert len(g_rest) == len(b_rest) == 1, (g_arms, b_arms)
    assert g_rest[0][1].startswith("add") and b_rest[0][1].startswith("add")


# ---- commit-2: the remaining TARGET-expression shapes + §6 alias ---------

def test_call_through_cast_target(tmp_path):
    # S14 form: `((int (*)(int))add)(1)` — the CAST of a fn value is the
    # target; the kernel idiom casts through void* (S18 form below).
    src = ("typedef unsigned long size_t;\n"
           "static long add(long a, long b){ return a + b; }\n"
           "int main(void){ return (int)((long (*)(long, long))add)(4, 5); }\n")
    _pair(tmp_path, "c2a", src, 9)


def test_call_through_voidptr_cast_target(tmp_path):
    # S18 form — the kernel's table-cast shape: the pointer VALUE rides
    # void*, the CALL casts it back to the fn-ptr type.
    src = ("typedef unsigned long size_t;\n"
           "static long add(long a, long b){ return a + b; }\n"
           "void *p;\n"
           "int main(void){ p = (void *)add; "
           "return (int)((long (*)(long, long))p)(4, 5); }\n")
    _pair(tmp_path, "c2b", src, 9)


def test_call_const_qualified_struct_slot(tmp_path):
    # S20/S21 form: the TARGET lives in a `static const struct` — the
    # const-qualified struct/member view is the parse-side gap commit-1
    # left NAMED (SMATRIX S20/S21 rc2 at that tree).
    src = ("typedef unsigned long size_t;\n"
           "struct op { long (*h)(long); long n; };\n"
           "static long f1(long x){ return x + 2; }\n"
           "static const struct op tbl[] = { { f1, 1 } };\n"
           "int main(void){ return (int)tbl[0].h(7); }\n")
    _pair(tmp_path, "c2c", src, 9)


def test_call_designated_const_struct_slot(tmp_path):
    src = ("typedef unsigned long size_t;\n"
           "struct op { long (*h)(long); long flags; };\n"
           "static long f1(long x){ return x * 3; }\n"
           "static const struct op one = { .h = f1, .flags = 3 };\n"
           "int main(void){ return (int)one.h(3); }\n")
    _pair(tmp_path, "c2d", src, 9)


def test_call_through_ternary(tmp_path):
    # S22 form: `(c ? f1 : f2)(x)` — the arms are FUNCTION VALUES; the
    # conditional decays each arm through the shipped fn-value law.
    src = ("typedef unsigned long size_t;\n"
           "static long f1(long x){ return x + 1; }\n"
           "static long f2(long x){ return x + 100; }\n"
           "static long pick(long c, long x){ return (c ? f1 : f2)(x); }\n"
           "int main(void){ return (int)(pick(1, 4) - pick(0, 4) + 100); }\n")
    _pair(tmp_path, "c2e", src, 1)   # 5 - 104 + 100 == 1


def test_call_through_set_alias(tmp_path):
    # §6 ALIAS law (W2 shipped `.set al, tgt` with the T-letter parity):
    # the W3 row — a CALL THROUGH THE ALIAS NAME works and RUNS (the
    # kernel's vdso form `sched_clock` → `native_sched_clock`).
    src = ("static long tgt(long x){ return x + 4; }\n"
           "static long al(long) __attribute__((alias(\"tgt\")));\n"
           "int main(void){ return (int)al(5); }\n")
    _pair(tmp_path, "c2f", src, 9)


def test_call_chain_paren_and_double_deref(tmp_path):
    # `((fp))(x)` and `(**fp)(x)` — the designator fold is GENERAL: every
    # deref whose type is a FuncType rides it (measured `**fp` folds, rc0).
    src = ("typedef unsigned long size_t;\n"
           "static long add(long a, long b){ return a + b; }\n"
           "static long via(long (*f)(long, long)){ "
           "return ((f))(4, 5) + (**(&f))(0, 0); }\n"
           "int main(void){ return (int)via(add); }\n")
    _pair(tmp_path, "c2g", src, 9)


# ---- commit-3: the %r10 VARIADIC indirect law (vr.s oracle) --------------

VA = "typedef __builtin_va_list va_list;\n"


def test_variadic_call_through_var(tmp_path):
    # §2 R-arm (kernel vdso-image-64 shape): a call through a VARIADIC
    # fn-ptr VALUE. The target must SURVIVE the arg staging — blcc
    # answers the oracle's law (measured vr.s: callee loaded BEFORE the
    # extras, `movl $0,%eax` = the shipped xorl, `call *%r10`).
    src = (VA +
           "static long vsum(long n, ...){ va_list a; long s = n; "
           "__builtin_va_start(a, n); "
           "s += __builtin_va_arg(a, long); s += __builtin_va_arg(a, long); "
           "__builtin_va_end(a); return s; }\n"
           "static long (*vp)(long, ...);\n"
           "int main(void){ vp = vsum; return (int)vp(1, 2, 3); }\n")
    _pair(tmp_path, "r10a", src, 6)


def test_variadic_call_overflow_through_slot(tmp_path):
    # The %r10 + PUSH-BLOCK interaction: >6 args on a variadic indirect
    # target — the push block moves %rsp, which is exactly WHY the target
    # rides %r10 and not a temp or %rax. Run-pair with 8 extras read
    # through the shipped §2.7 va_arg switch.
    src = (VA +
           "static long vsum(long n, ...){ va_list a; long s = n; long i; "
           "__builtin_va_start(a, n); "
           "for (i = 0; i < 8; i++) s += __builtin_va_arg(a, long); "
           "__builtin_va_end(a); return s; }\n"
           "static long (*slots[2])(long, ...);\n"
           "int main(void){ slots[1] = vsum; "
           "return (int)slots[1](1L, 2L, 3L, 4L, 5L, 6L, 7L, 8L, 9L); }\n")
    _pair(tmp_path, "r10b", src, 45)


def test_variadic_indirect_sequence_pin(tmp_path):
    # Shape pin — RE-PINNED at the M4 W3-fix (MC 12573). The old form
    # ("target into %r10 FIRST") pinned exactly the ordering gate class
    # C2 proved corruptible: a nested call inside the args rewrites %r10
    # (silent callee swap). The shipped law (measured gcc, gate oracle):
    # the target ADDRESS is materialized into a pool temp before the
    # args, and the %r10 RELOAD from that slot is the last move before
    # `call *%r10` — nothing can clobber the callee between them.
    src = (VA +
           "static long vp_dummy(long n, ...){ (void)n; return 0; }\n"
           "static long (*vp)(long, ...);\n"
           "long fire(void){ vp = vp_dummy; return vp(1, 2, 3); }\n")
    s = tmp_path / "r10c.c"
    s.write_text(src)
    br = blcc(["--emit-asm", "-c", str(s), "-o", str(tmp_path / "r10c.b")])
    assert br.returncode == 0, br.stderr
    body = br.stdout[br.stdout.index("fire:"):]
    ci = body.index("call *%r10")
    assert body.index("movq %rax, 8(%rsp)") < body.index("movq 16(%rsp), %rdi")
    m = re.search(r"movq \d+\(%rsp\), %r10", body)   # reload…
    assert m and m.start() < ci                       # …from the slot…
    assert body.rindex(", %rdi") < m.start()          # …after arg staging
    assert body.index("xorl %eax, %eax") < ci         # vector count 0


def test_nonvariadic_indirect_target_move_after_args(tmp_path):
    # The NON-variadic mirror of the TARGET LAW (M4 W3-fix): the target
    # is evaluated FIRST and its address parked in a pool temp (the old
    # "evaluated after the args" placement was gate class C1 — the
    # addressing clobbers staged %rcx/%rdx/%r8/%r9); the slot→%rax MOVE
    # stays the last emission before `call *%rax` (§2 R6's letter).
    src = ("typedef unsigned long size_t;\n"
           "static long add(long a, long b){ return a + b; }\n"
           "static long (*gfp)(long, long);\n"
           "long fire(long x){ gfp = add; return gfp(x, x); }\n")
    s = tmp_path / "r10d.c"
    s.write_text(src)
    br = blcc(["--emit-asm", "-c", str(s), "-o", str(tmp_path / "r10d.b")])
    assert br.returncode == 0, br.stderr
    body = br.stdout[br.stdout.index("fire:"):]
    ci = body.index("call *%rax")
    # address materialized BEFORE any arg staging:
    assert body.index("movq %rax, 8(%rsp)") < body.index("movq 16(%rsp), %rdi")
    # the slot→%rax move after the last arg move, immediately before call:
    assert body.rindex("movq 24(%rsp), %rsi") < body.rindex(
        "movq 8(%rsp), %rax") < ci


# ---- the twins that STAY LOUD ---------------------------------------------

def test_undeclared_ident_call_stays_loud(tmp_path):
    src = "int main(void){ return mystery(1); }\n"
    s = tmp_path / "lv0.c"
    s.write_text(src)
    br = blcc(["-c", str(s), "-o", str(tmp_path / "lv0.o")])
    assert br.returncode == 2
    assert "no declaration for callable" in br.stderr   # sentence survives


def test_object_call_is_loud_twin(tmp_path):
    # gcc rc1: `called object is not a function or function pointer`
    src = "int main(void){ long x = 3; return x(1); }\n"
    s = tmp_path / "lv1.c"
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / "lv1.gcc.o")])
    assert gr.returncode == 1, gr.stderr
    br = blcc(["-c", str(s), "-o", str(tmp_path / "lv1.o")])
    assert br.returncode == 2 and "function pointer" in br.stderr, br.stderr


def test_indirect_arity_is_loud(tmp_path):
    src = ("typedef unsigned long size_t;\n"
           "static long add(long a, long b){ return a + b; }\n"
           "static long via(long (*f)(long, long)){ return f(4); }\n"
           "int main(void){ return (int)via(add); }\n")
    s = tmp_path / "lv2.c"
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / "lv2.gcc.o")])
    assert gr.returncode == 1, gr.stderr
    br = blcc(["-c", str(s), "-o", str(tmp_path / "lv2.o")])
    assert br.returncode == 2, br.stderr


def test_more_than_six_named_stays_loud(tmp_path):
    # R9 (plan §2): >6 NAMED args on an indirect target KEEPS the shipped
    # §6-ABI sentence — the gcc twin ACCEPTS (rc0): NAMED LOUD-DIV row.
    src = ("typedef unsigned long size_t;\n"
           "static long g7(long a, long b, long c, long d, long e, long f,"
           " long g){ return a+b+c+d+e+f+g; }\n"
           "static long via(long (*h)(long,long,long,long,long,long,long))"
           "{ return h(1,2,3,4,5,6,7); }\n"
           "int main(void){ return (int)via(g7); }\n")
    s = tmp_path / "lv3.c"
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / "lv3.gcc.o")])
    assert gr.returncode == 0, gr.stderr           # gcc accepts (div row)
    br = blcc(["-c", str(s), "-o", str(tmp_path / "lv3.o")])
    assert br.returncode == 2
    assert "beyond the \u00a76 call ABI" in br.stderr    # sentence survives


def test_fnptr_call_wall_sentence_is_dead(tmp_path):
    # The W3 wall sentence must NOT appear on an accepted indirect call
    # (mirrors the W1 sentence-death pin).
    s = tmp_path / "dv0.c"
    s.write_text(VIA)
    br = blcc(["-c", str(s), "-o", str(tmp_path / "dv0.o")])
    assert br.returncode == 0, br.stderr
    assert "not in the subset" not in br.stderr
