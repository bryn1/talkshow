"""M39/M40/M52 — the va trio (callee side §2.7) and the variadic CALLER
ABI (§2.14), MC 12460. Run legs pair against gcc 11.4; the caller ABI is
pinned by greps against blcc's OWN asm (the §2.14 measured sequence:
subq $16 → REG_ARGS named+extras → reverse 8-byte pushes → xorl %eax,%eax
→ call → addq). §2.14 NEG legs: float/double extra and struct/union
(non-scalar) extra are LOUD — blcc has float storage only (§1 row 14),
and a struct extra breaks the 8-byte-slot model (both measured by the DA
at −Os and −mno-sse).
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itva")


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))


def blcc_asm(src, tag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path, "--emit-asm",
                        "-o", p + ".bin"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert r.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, r.stderr)
    with open(p + ".bin.s", encoding="utf-8") as fh:
        return fh.read()


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


def _loud(src, tag, frag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path,
                        "-o", p + ".out"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert r.returncode == 2, \
        "{}: expected LOUD (exit 2), got {} stderr={!r}".format(
            tag, r.returncode, r.stderr)
    assert frag in r.stderr, "{}: stderr must name {!r}: {}".format(
        tag, frag, r.stderr)
    assert not os.path.exists(p + ".out"), "rejected input emitted a binary"


VA_HDR = "typedef __builtin_va_list va_list;\n"


# ---- M39: callee side (§2.7) ------------------------------------------------

def test_va_basic_sum_run_pair():
    # va_start/va_arg/va_end, GP kinds int/long long/char* (§2.7 v1 census).
    both_run(VA_HDR + """
long sum3(int n, ...) {
    va_list ap;
    long s = 0;
    int i;
    __builtin_va_start(ap, n);
    for (i = 0; i < n; i++) {
        s += __builtin_va_arg(ap, long);
    }
    __builtin_va_end(ap);
    return s;
}
int main(void) {
    if (sum3(0) != 0) return 1;
    if (sum3(1, 5L) != 5) return 2;
    if (sum3(4, 1L, 2L, 3L, 4L) != 10) return 3;
    if (sum3(5, 1L, 2L, 3L, 4L, 5L) != 15) return 4;
    return 0;
}
""", "va-sum")


def test_va_overflow_run_pair():
    # 10 extras: the 4+ past the 6th argument ride the OVERFLOW AREA —
    # va_arg must switch bases (reg_save_area → overflow_arg_area) with
    # gp_offset still counting (§2.7; 13-args re-confirmed §2.14).
    both_run(VA_HDR + """
long sumall(int n, ...) {
    va_list ap;
    long s = 0;
    int i;
    __builtin_va_start(ap, n);
    for (i = 0; i < n; i++) s += __builtin_va_arg(ap, long);
    __builtin_va_end(ap);
    return s;
}
int main(void) {
    if (sumall(9, 1L, 2L, 3L, 4L, 5L, 6L, 7L, 8L, 9L) != 45)
        return 1;
    if (sumall(12, 1L, 2L, 3L, 4L, 5L, 6L, 7L, 8L, 9L, 10L, 11L, 12L)
        != 78) return 2;
    return 0;
}
""", "va-ovf")


def test_va_kinds_run_pair():
    # Mixed GP kinds per the §2.7 census: int, char*, long long — each
    # extra read AS its own type (the only well-defined pairing).
    both_run(VA_HDR + """
long kinds(int tag, ...) {
    va_list ap;
    long r = 0;
    int i;
    char *s;
    __builtin_va_start(ap, tag);
    i = __builtin_va_arg(ap, int);
    s = __builtin_va_arg(ap, char *);
    r = __builtin_va_arg(ap, long long);
    __builtin_va_end(ap);
    if (r == 500) return i + (long)(unsigned char)s[0] + 5;
    return i + (long)(unsigned char)s[0];
}
int main(void) {
    if (kinds(1, 7, "hi", 500LL) != 7 + 104 + 5) return 1;
    return 0;
}
""", "va-kinds")


def test_va_list_by_reference_run_pair():
    # §2.7: `va_list` params pass by reference — the vprintk/vscnprintf
    # hand-off: variadic outer collects into ap, helper(va_list) continues
    # the SAME cursor (lib/vsprintf.c:2581/2750 shape).
    both_run(VA_HDR + """
long take2(va_list ap) {
    long a = __builtin_va_arg(ap, long);
    long b = __builtin_va_arg(ap, long);
    return a * 10 + b;
}
long outer(int n, ...) {
    va_list ap;
    long r;
    __builtin_va_start(ap, n);
    r = take2(ap);
    __builtin_va_end(ap);
    return r;
}
int main(void) {
    if (outer(2, 3L, 4L) != 34) return 1;   /* take2 continues the SAME  */
    return 0;                               /* cursor: 3*10+4            */
}
""", "va-ref")


def test_va_copy_run_pair():
    # §2.7 `va_copy` = struct copy: the copy keeps an INDEPENDENT cursor
    # (kernel: 4 files / 4 sites, D′).
    both_run(VA_HDR + """
long use4(va_list cp) {
    long s = 0;
    int i;
    for (i = 0; i < 4; i++) s += __builtin_va_arg(cp, long);
    return s;
}
long outer(int n, ...) {
    va_list ap, cp;
    long r;
    __builtin_va_start(ap, n);
    __builtin_va_copy(cp, ap);
    r = use4(cp);
    r += __builtin_va_arg(ap, long);      /* original cursor untouched   */
    __builtin_va_end(cp);
    __builtin_va_end(ap);
    return r;
}
int main(void) {
    if (outer(5, 1L, 2L, 3L, 4L, 5L) != 15) return 1;  /* copy 1+2+3+4,  */
    return 0;                                          /* orig then 5    */
}
""", "va-copy")


def test_va_arg_float_loud():
    # §2.7: float/double TYPE ARGS are LOUD ("all va_arg type args are GP
    # in this tree" — the census has zero FP args to support).
    _loud(VA_HDR + "long f(int n, ...){ va_list ap; long r;"
          " __builtin_va_start(ap, n); r = __builtin_va_arg(ap, double);"
          " __builtin_va_end(ap); return r; }\n"
          "int main(void){ return 0; }\n", "va-arg-flt", "float")


def test_va_arg_struct_loud():
    # §2.7 all-GP: a struct/class type arg needs the multi-slot class
    # model — LOUD, never silent.
    _loud(VA_HDR + "struct S{long a; long b;};\n"
          "long f(int n, ...){ va_list ap; va_list cp;"
          " __builtin_va_start(ap, n); (void)__builtin_va_arg(ap, struct S);"
          " __builtin_va_end(ap); return 0; }\n"
          "int main(void){ return 0; }\n", "va-arg-st", "struct")


# ---- M52: caller ABI (§2.14 measured) ----------------------------------------

def test_caller_abi_stack_leg_asm_greps():
    asm = blcc_asm(VA_HDR + "int f9(int a, ...){ return a; }\n"
                   "int main(void){ return f9(1,2,3,4,5,6,7,8); }\n",
                   "call9")
    body = asm.split("\nmain:\n", 1)[1]
    # §2.14 measured sequence: subq $16 (alignment) BEFORE the pushes;
    # extras 7+ pushed in REVERSE source order (emission sees strictly
    # descending stack offsets — the last arg lands lowest, so the
    # callee's overflow_arg_area reads args forward from rbp+16);
    # `%al = 0` before EVERY variadic call; one addq restores align+slots.
    assert "subq $16, %rsp" in body, "§2.14 16-byte align: " + body
    pushes = [int(x) for x in re.findall(r"pushq (\d+)\(%rsp\)", body)]
    assert len(pushes) == 2 and pushes == sorted(pushes, reverse=True), \
        "§2.14 reverse 8-byte pushes of extras 7+ (got {})".format(pushes)
    assert "xorl %eax, %eax" in body, \
        "§2.14 %al = 0 before call (GP-only posture): " + body
    assert "addq $32, %rsp" in body, \
        "§2.14 alignment restore = 16 align + 2 stack args (32)"


def test_caller_abi_all_regs_asm_greps():
    # 3-arg call3 (§2.14): named + extras ALL ride GP regs — no stack, no
    # alignment sub, but STILL `%al = 0` (§2.14 pins xorl in the sequence).
    asm = blcc_asm(VA_HDR + "int f3(int a, ...){ return a; }\n"
                   "int main(void){ return f3(1,2,3); }\n", "call3")
    body = asm.split("\nmain:\n", 1)[1]
    # (main's own prologue — pushq %rbp / frame sub — always exists; the
    # §2.14 ALIGNED `subq $16` + arg pushes are what must be absent.)
    strays = re.findall(r"pushq (?!%rbp\b)\S+", body)
    assert not strays and "subq $16" not in body, \
        "call3 must not touch the stack: " + body
    assert "xorl %eax, %eax" in body, \
        "call3 still zeroes %al: " + body


def test_caller_too_few_loud():
    _loud(VA_HDR + "int f2(int a, int b, ...){ return a; }\n"
          "int main(void){ return f2(1); }\n", "va-few", "argument")


def test_caller_float_extra_loud():
    # §2.14 (v3 DA-m2-c2-4 + v4 flag-pin): float/double variadic EXTRA is
    # LOUD — rests on no-float-value-materialization (§1 row 14), true
    # under BOTH flag sets (the -mno-sse re-probe kept xorl but the extra
    # still rides flds/fstpl/pushq — no GP-only representation).
    _loud(VA_HDR + "int f1(int a, ...){ return a; }\n"
          "int main(void){ double d = 1.5; return f1(1, d); }\n",
          "va-flt-extra", "float")


def test_caller_struct_extra_loud():
    # §2.14 (DA-m2-c2-4 measured): a struct extra SPLITS across GP regs
    # (gcc movabsq / two-reg split) — breaks the one-slot model ⇒ LOUD.
    _loud(VA_HDR + "struct S{long a; long b;};\n"
          "int f1(int a, ...){ return a; }\n"
          "int main(void){ struct S s; return f1(1, s); }\n",
          "va-st-extra", "struct")


def test_fixed_arity_mismatch_stays_loud():
    _loud(VA_HDR + "int g3(int a, int b, int c){ return a; }\n"
          "int main(void){ return g3(1,2); }\n", "fix-arity", "takes")


def test_fixed_gt6_stays_loud():
    # §2.14: "want > 6 for FIXED-arity decls KEEPS its current LOUD"
    # (M48 residual: not measured in the tiny universe).
    _loud(VA_HDR + "int g7(int a,int b,int c,int d,int e,int f,int g)"
          "{ return a; }\nint main(void){ return g7(1,2,3,4,5,6,7); }\n",
          "fix7", "beyond the §6 call ABI")
