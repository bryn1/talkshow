# LINES reason: one gate-divergence class = one leg cluster; the RED-at-tip
# witnesses, the RECURRENCE arity ladder and the law shape pins of the
# M4 W3-fix split across files would hide which gate row each leg closes.
"""M4 W3-fix (MC 12573) — the indirect-call TARGET LAW, gate classes C1/C2.

The W3 gate (MC 12404.2.53, verdict m4-w3-gate-verdict.md) caught two
SILENT-CORRUPTION classes the W3 suite's arity<=2 legs could never see:

  C1 — the non-variadic indirect target was evaluated AFTER the
       arg-register staging, and the addressing arithmetic clobbers
       %rcx/%rdx/%r8/%r9 = staged args 3..6 (`tbl[i].fn(1,2,3,4)`
       dispatched with arg4 = the base address; a div-bearing target
       kills arg3 already at arity 3, and CONST indices clobber too).
  C2 — the variadic `%r10` pre-load did not survive a NESTED CALL in
       the args (the callee's own variadic re-load rewrote %r10 — a
       silent CALLEE SWAP, G24 exit 7 = vB(1,530) exact arithmetic).

THE LAW shipped in blcc/expr_codegen._stage_call: the callee EXRESSION
is evaluated FIRST (nothing staged yet, clobbers are free), its address
materialized into a pool temp arg staging cannot reach; only the final
MOVE slot->reg rides the tail, after the REG_ARGS loads (plan §2 R6's
letter, gcc's observable law). The push-block arm re-materializes
%r10 through the same +16+8*extras shift law as the pushed args.

RECURRENCE LAW (named in LEDGER): the leg class 'indirect arity >=4
run-pair' — the arity ladder below (slot / member / div-target, 2..6,
rung 7 LOUD + variadic 9-arg through the push block). A computed-target
change may not ship without these legs green.

Every fixture below is PORTED FROM the gate battery (fixtures frozen at
.tmp/m4-w3-gate/out/), RED captured at 550998d (out/red-at-550998d in
.tmp/m4-w3fix/), GREEN at this fix. Expect values are the gcc 11.4
-Os oracle's exits RE-MEASURED this session (two gate-battery expect
arithmetic typos corrected: G24 19 not 21, G27 170 not 50). Gate class
C3 (the over-LOUD paren-arithmetic arrow base) rides the same file —
its legs RED-capture on the parser at 550998d (byte-identical at the
C1/C2 commit) and land with the parse-side fix in the C3 commit.
"""
import os
import re
import subprocess
import sys

REPO = os.environ.get("BLCC_REPO") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VA = "typedef __builtin_va_list va_list;\n"


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + args,
                          capture_output=True, text=True)


def _pair(tmp_path, tag, src, expect):
    """ORACLE-DECIDES (the shipped run_pair shape): full link both sides,
    run, SAME exit code — exactly the bar the gate found unmet."""
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


# ---- C1: the gate's divergent witnesses, ported verbatim -------------------

def test_c1_member_array_computed_target_4args(tmp_path):   # gate F03 49/17
    src = ("struct op { long (*fn)(long,long,long,long); long pad; };\n"
           "struct op tbl[4];\n"
           "long f(long a, long b, long c, long d){ return a+2*b+4*c+8*d; }\n"
           "int main(void){ int i = 2; tbl[i].fn = f;\n"
           "  return (int)tbl[i].fn(1,2,3,4); }\n")
    _pair(tmp_path, "wfix-f03", src, 49)


def test_c1_array_slot_const_index_4args(tmp_path):         # gate F15 110/106
    # CONSTANT indices clobber too: _emit_addr moves the table base into
    # %rcx regardless of index constancy — arity >=4 through ANY
    # Index-based target was wrong, not just computed ones.
    src = ("long f(long a, long b, long c, long d){ return 100+a+b+c+d; }\n"
           "long g(long a, long b, long c, long d){ return 200+a+b+c+d; }\n"
           "long (*tbl[3])(long,long,long,long);\n"
           "int main(void){ tbl[0]=g; tbl[2]=f; return (int)tbl[2](1,2,3,4); }\n")
    _pair(tmp_path, "wfix-f15", src, 110)


def test_c1_div_in_target_4args(tmp_path):                  # gate F17 26/11
    src = ("struct t { long (*fn)(long,long,long,long); long pad; };\n"
           "struct t tbl[10];\n"
           "long f(long a, long b, long c, long d){ return a+b+c+d; }\n"
           "int main(void){ int i = 6, j = 3; tbl[i/j].fn = f;\n"
           "  return (int)tbl[i/j].fn(5,6,7,8); }\n")
    _pair(tmp_path, "wfix-f17", src, 26)


def test_c1_char_index_target_6args(tmp_path):              # gate F18 91/75
    src = ("struct t { long (*fn)(long,long,long,long,long,long); };\n"
           "struct t tbl[8];\n"
           "long f(long a, long b, long c, long d, long e, long g)"
           "{ return a+2*b+3*c+4*d+5*e+6*g; }\n"
           "int main(void){ char c = 3; tbl[c].fn = f;\n"
           "  return (int)tbl[c].fn(1,2,3,4,5,6); }\n")
    _pair(tmp_path, "wfix-f18", src, 91)


def test_c1_table_computed_5args(tmp_path):                 # gate G04 62/46
    src = ("long f(long a, long b, long c, long d, long e)"
           "{ return a+b+c+d+e; }\n"
           "long (*tbl[4])(long,long,long,long,long);\n"
           "int main(void){ int i = 1; tbl[i] = f;\n"
           "  return (int)tbl[i](2,4,8,16,32); }\n")
    _pair(tmp_path, "wfix-g04", src, 62)


def test_c1_nested_args_plus_computed_target(tmp_path):     # gate G27 170/126
    # the COMPOUND hole: nested calls in the args AND a computed target
    src = ("long h(long x){ return x+1000; }\n"
           "long f(long a, long b, long c, long d)"
           "{ return (a%64)+(b%64)+(c%64)+(d%64); }\n"
           "long (*tbl[4])(long,long,long,long);\n"
           "int main(void){ int i=2; tbl[i]=f;\n"
           "  return (int)tbl[i](h(1),h(2),h(3),h(4)); }\n")
    _pair(tmp_path, "wfix-g27", src, 170)


def test_c1_div_target_3args(tmp_path):                     # gate G28 18/11
    # the div target kills arg3 (%rdx) already at arity 3
    src = ("struct t { long (*fn)(long,long,long); };\nstruct t tbl[10];\n"
           "long f(long a, long b, long c){ return a+b+c; }\n"
           "int main(void){ int i = 6, j = 3; tbl[i/j].fn = f;\n"
           "  return (int)tbl[i/j].fn(5,6,7); }\n")
    _pair(tmp_path, "wfix-g28", src, 18)


# ---- RECURRENCE LAW: the 'indirect arity >=4 run-pair' ladder --------------
# (the arity<=2 blindness that hid C1 from 66 shipped legs must not recur;
#  weighted sums make every arg position visible: term k = k*(k+1))

NAMES = "abcdef"


def _wsum(n):
    # term k: coefficient k on arg k (args are 1L,2L,…,kL) → sum of squares
    return sum(k * k for k in range(1, n + 1))


def _ladder_src(kind, n):
    types = ", ".join(["long"] * n)
    params = ", ".join("long " + NAMES[k] for k in range(n))
    body = " + ".join("{}*{}".format(k + 1, NAMES[k]) for k in range(n))
    args = ", ".join("{}L".format(k) for k in range(1, n + 1))
    fn = "long f({}){{ return {}; }}\n".format(params, body)
    if kind == "slot":
        return (fn + "long (*tbl[4])({});\n".format(types) +
                "int main(void){{ int i = 1; tbl[i] = f;\n"
                "  return (int)tbl[i]({}) % 256; }}\n".format(args))
    if kind == "member":
        return ("struct t {{ long (*fn)({}); long pad; }};\n"
                "struct t tbl[4];\n".format(types) + fn +
                "int main(void){{ int i = 1; tbl[i].fn = f;\n"
                "  return (int)tbl[i].fn({}) % 256; }}\n".format(args))
    assert kind == "div"
    return ("struct t {{ long (*fn)({}); }};\n"
            "struct t tbl[10];\n".format(types) + fn +
            "int main(void){{ int i = 6, j = 3; tbl[i/j].fn = f;\n"
            "  return (int)tbl[i/j].fn({}) % 256; }}\n".format(args))


def _ladder(tmp_path, kind):
    for n in range(2, 7):                      # fixed-arity register arm
        _pair(tmp_path, "wfix-lad-{}-{}".format(kind, n),
              _ladder_src(kind, n), _wsum(n))


def test_arity_ladder_slot_target_2_to_6(tmp_path):
    _ladder(tmp_path, "slot")


def test_arity_ladder_member_target_2_to_6(tmp_path):
    _ladder(tmp_path, "member")


def test_arity_ladder_div_target_2_to_6(tmp_path):
    _ladder(tmp_path, "div")


def test_arity_7_named_through_slot_SHIPS_FLIPPED(tmp_path):
    # M4 W-L FLIP (MC 12665, never deletion): rung 7 pinned the >6-arity
    # §6-ABI LOUD on the computed-slot indirect arm. W-L shipped real
    # stack passing (measured gcc -Os law) — the leg now pins the ACCEPT
    # and the VALUE through the same computed-slot target form.
    src = ("long g7(long a, long b, long c, long d, long e, long f,"
           " long g){ return a+b+c+d+e+f+g; }\n"
           "long (*tbl[2])(long,long,long,long,long,long,long);\n"
           "int main(void){ tbl[1] = g7; "
           "return (int)tbl[1](1,2,3,4,5,6,7); }\n")
    _pair(tmp_path, "wfix-lad-7", src, 28)


def test_variadic_9args_through_computed_slot_runs(tmp_path):
    # the push-block arm of the ladder: >6 args through a COMPUTED-index
    # slot — the target law's tail re-materializes %r10 after the pushes
    src = (VA +
           "long vsum(long n, ...){ va_list a; long s = n; long i;\n"
           "  __builtin_va_start(a, n);\n"
           "  for (i = 0; i < 8; i++) s += __builtin_va_arg(a, long);\n"
           "  __builtin_va_end(a); return s; }\n"
           "long (*slots[2])(long, ...);\n"
           "int main(void){ int i = 1; slots[i] = vsum;\n"
           "  return (int)slots[i](1L,2L,3L,4L,5L,6L,7L,8L,9L); }\n")
    _pair(tmp_path, "wfix-v9", src, 45)


# ---- C2: %r10 must survive a nested call inside the args -------------------

def test_c2_nested_variadic_indirect_callee_swap(tmp_path):  # gate G24 19/7
    # blcc=7 was EXACTLY vB(1, 530): the inner call's own r10 load swapped
    # the outer callee. (Gate battery's expect read 21 — arithmetic typo;
    # the oracle decides: (1 + 530) % 256 = 19.)
    src = (VA +
           "long vA(long n, ...){ va_list a; long s = n; __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long); __builtin_va_end(a); return s; }\n"
           "long vB(long n, ...){ va_list a; long s = n; __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long); __builtin_va_end(a); return s + 500; }\n"
           "long (*slots[2])(long, ...);\n"
           "int main(void){ slots[0] = vA; slots[1] = vB;\n"
           "  return (int)slots[0](1L, slots[1](10L, 20L), 2L) % 256; }\n")
    _pair(tmp_path, "wfix-g24", src, 19)


def test_c2_nested_variadic_indirect_via_var(tmp_path):      # G24 var twin
    src = (VA +
           "long vA(long n, ...){ va_list a; long s = n; __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long); __builtin_va_end(a); return s; }\n"
           "long vB(long n, ...){ va_list a; long s = n; __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long); __builtin_va_end(a); return s + 500; }\n"
           "long (*vp)(long, ...);\nlong (*vq)(long, ...);\n"
           "int main(void){ vp = vA; vq = vB;\n"
           "  return (int)vp(1L, vq(10L, 20L), 2L) % 256; }\n")
    _pair(tmp_path, "wfix-nv2", src, 19)


def test_c2_nested_variadic_inside_overflow_arg(tmp_path):
    # the nested INDIRECT variadic call sits in the PUSH-BLOCK arm (arg 7
    # of 9): pre-fix the outer %r10 pre-load died to the inner call's own
    # `movq %rax, %r10` — the outer dispatched vsingle (exit 3 = 1L+2L);
    # now the outer slot→%r10 reload happens AFTER the pushes.
    src = (VA +
           "long vsingle(long n, ...){ va_list a; long s = n; __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long); __builtin_va_end(a); return s; }\n"
           "long vsum(long n, ...){ va_list a; long s = n; long i; __builtin_va_start(a, n);\n"
           "  for (i = 0; i < 8; i++) s += __builtin_va_arg(a, long);\n"
           "  __builtin_va_end(a); return s; }\n"
           "long (*slots[2])(long, ...);\n"
           "int main(void){ slots[0] = vsum; slots[1] = vsingle;\n"
           "  return (int)slots[0](1L,2L,3L,4L,5L,6L,slots[1](50L,51L),8L,9L)\n"
           "    % 256; }\n")
    _pair(tmp_path, "wfix-nv1", src, 139)


def test_c2_variadic_slot_nested_call_arg(tmp_path):         # gate F12 106
    src = (VA +
           "long h(long x){ return x+100; }\n"
           "long vsum(long n, ...){ va_list a; long s = n;\n"
           "  __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long); s += __builtin_va_arg(a, long);\n"
           "  __builtin_va_end(a); return s; }\n"
           "long (*slots[2])(long, ...);\n"
           "int main(void){ slots[1] = vsum;\n"
           "  return (int)slots[1](1L, h(2), 3L); }\n")
    _pair(tmp_path, "wfix-f12", src, 106)


def test_c2_variadic_var_nested_2nd_arg(tmp_path):           # gate F13 10
    src = (VA +
           "long h(long x){ return x+7; }\n"
           "long vsum(long n, ...){ va_list a; long s = n;\n"
           "  __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long);\n"
           "  __builtin_va_end(a); return s; }\n"
           "long (*vp)(long, ...);\n"
           "int main(void){ vp = vsum; return (int)vp(1L, h(2)); }\n")
    _pair(tmp_path, "wfix-f13", src, 10)


def test_c2_variadic_overflow_nested_trivial_arg(tmp_path):  # gate F19 45
    # the builder's reproduced class stays green (nested call inside the
    # push-block args when the nested body never touches %r10)
    src = (VA +
           "long h(long x){ return x; }\n"
           "long vsum(long n, ...){ va_list a; long s = n; long i;\n"
           "  __builtin_va_start(a, n);\n"
           "  for (i = 0; i < 8; i++) s += __builtin_va_arg(a, long);\n"
           "  __builtin_va_end(a); return s; }\n"
           "long (*slots[2])(long, ...);\n"
           "int main(void){ slots[1] = vsum;\n"
           "  return (int)slots[1](1L,2L,h(3),4L,5L,6L,7L,8L,9L); }\n")
    _pair(tmp_path, "wfix-f19", src, 45)


def test_c2_nested_widemul_arg_r10(tmp_path):                # gate G25 7
    src = (VA +
           "long h(long x){ char a = (char)x; char b = 3; return (long)(a * b); }\n"
           "long vsum(long n, ...){ va_list a; long s = n; __builtin_va_start(a, n);\n"
           "  s += __builtin_va_arg(a, long); __builtin_va_end(a); return s; }\n"
           "long (*slots[2])(long, ...);\n"
           "int main(void){ slots[1] = vsum;\n"
           "  return (int)slots[1](1L, h(2)); }\n")
    _pair(tmp_path, "wfix-g25", src, 7)


# ---- C3: the arrow-call on a PARENTHESIZED ARITHMETIC base (gate C3) -------
# blcc was over-LOUD: `called object is not a 'function'` (rc2) where gcc is
# rc0 both sides. Root cause: the PARSE-side light typer (parser.expr_type)
# had no pointer-arithmetic arm, so `(p+2)->fn` never reached the callable
# view — the engine types the same node fine. Fix: ONE Binary arm mirroring
# the engine's ptr +/- int = ptr law (a both-pointer difference stays the
# §8 twin). Corpus volume 0 (all `)->ident(` witnesses are paren-IDENT
# bases — the G06d fairness leg below); the arity>=4 leg (F06) additionally
# proves the C1 TARGET LAW holds for these bases once accepted.

def test_c3_arrow_paren_arith_base(tmp_path):                # gate G06a 42
    src = ("struct op { long (*fn)(long,long); long pad; };\nstruct op arr[3];\n"
           "long f(long a, long b){ return a+b; }\n"
           "int main(void){ struct op *p = arr; long r; (p+2)->fn = f;\n"
           "  r = (p+2)->fn(40,2); return (int)r; }\n")
    _pair(tmp_path, "wfix-g06a", src, 42)


def test_c3_arrow_paren_arith_base_plus_readback(tmp_path):  # gate G06b 42
    src = ("struct op { long (*fn)(long,long); long pad; };\nstruct op arr[3];\n"
           "long f(long a, long b){ return a+b; }\n"
           "int main(void){ struct op *p = arr; long r; (p+2)->fn = f;\n"
           "  r = (p+2)->fn(40,2); return (int)(r + (p+1)->pad); }\n")
    _pair(tmp_path, "wfix-g06b", src, 42)


def test_c3_arrow_paren_arith_base_4args(tmp_path):          # gate F06 142
    # the COMPOUND row: C3 acceptance + arity 4 through an arithmetic
    # arrow base — pre-C1-fix this would have paired GREEN on exit code…
    # no: it would have diverged (rcx clobber) — both laws ride this leg.
    src = ("struct op { long (*fn)(long,long,long,long); long pad; };\n"
           "struct op arr[3];\n"
           "long f(long a, long b, long c, long d){ return a+3*b+9*c+27*d; }\n"
           "int main(void){ int i = 1; struct op *p = arr; (p+2)->fn = f;\n"
           "  return (int)(p+2)->fn(1,2,3,4); }\n")
    _pair(tmp_path, "wfix-f06", src, 142)


def test_c3_paren_ident_base_fairness(tmp_path):             # gate G06d 42
    # `(p)->fn(...)` (paren-IDENT base) already paired green pre-fix —
    # the acceptance fix must not disturb it (the corpus's 13-file
    # `skb)->output(...)` family rides exactly this arm).
    src = ("struct op { long (*fn)(long,long); long pad; };\nstruct op arr[3];\n"
           "long f(long a, long b){ return a+b; }\n"
           "int main(void){ struct op *p = arr+2; p->fn = f;\n"
           "  return (int)((p)->fn(40,2)); }\n")
    _pair(tmp_path, "wfix-g06d", src, 42)


def test_c3_noncallable_paren_base_stays_loud(tmp_path):
    # the §8 gcc-rc1 twin survives the acceptance: `(a-b)(1)` on LONGS is
    # not a call target (both-pointer difference is never a pointer).
    src = "int main(void){ long a = 3, b = 1; return (int)(a-b)(1); }\n"
    s = tmp_path / "wfix-c3neg.c"
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / "wfix-c3neg.gcc.o")])
    assert gr.returncode == 1, gr.stderr             # gcc rc1 too
    br = blcc(["-c", str(s), "-o", str(tmp_path / "wfix-c3neg.o")])
    assert br.returncode == 2 and "function pointer" in br.stderr, br.stderr


# ---- shape pins of the shipped law ------------------------------------------

def _main_body(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    br = blcc(["--emit-asm", "-c", str(s), "-o", str(tmp_path / tag)])
    assert br.returncode == 0, br.stderr
    return br.stdout[br.stdout.index("main:"):]


def test_indirect_target_address_materialized_before_arg_staging(tmp_path):
    # C1's witness (gate: `movq 32(%rsp), %rcx` arg4 staged, THEN
    # `movq 8(%rsp), %rcx` target addressing, THEN call): after the first
    # REG_ARGS load the ONLY %rcx destination left is arg4's own staging
    # move, and the slot->%rax move is the LAST emission before the call.
    body = _main_body(tmp_path, "wfix-pin1", _ladder_src("member", 4))
    lines = [ln.strip() for ln in body.splitlines()[1:]]
    ci = lines.index("call *%rax")
    si = next(k for k, ln in enumerate(lines) if ln == "movq 16(%rsp), %rdi")
    assert si < ci, body
    rcx_writes = [ln for ln in lines[si:ci] if ln.endswith(", %rcx")]
    assert rcx_writes == ["movq 40(%rsp), %rcx"], rcx_writes
    assert lines[ci - 1] == "movq 8(%rsp), %rax", lines[ci - 5:ci + 1]


def test_variadic_indirect_r10_reloaded_after_the_push_block(tmp_path):
    # C2's tail (measured gcc law: the callee ADDRESS rides a stack slot
    # and %r10 is re-materialized at the call): the %r10 load must come
    # from the (shifted) slot, AFTER the last pushq and before the call.
    src = (VA +
           "long vsum(long n, ...){ va_list a; long s = n; long i;\n"
           "  __builtin_va_start(a, n);\n"
           "  for (i = 0; i < 8; i++) s += __builtin_va_arg(a, long);\n"
           "  __builtin_va_end(a); return s; }\n"
           "long (*slots[2])(long, ...);\n"
           "int main(void){ slots[1] = vsum;\n"
           "  return (int)slots[1](1L,2L,3L,4L,5L,6L,7L,8L,9L); }\n")
    body = _main_body(tmp_path, "wfix-pin2", src)
    ci = body.index("call *%r10")
    m = re.search(r"movq (\d+)\(%rsp\), %r10", body)
    assert m, body                       # reload FROM A SLOT, not %rax…
    assert body.rindex("pushq ") < m.start() < ci   # …after the pushes…
    assert body.index("xorl %eax, %eax") < ci        # …vector count 0


# ---- W4 re-gate carry (MC 12581; verdict m4-w3-regate-verdict.md F-A) -----
# The C3 parse-side expr_type fix had a behavior delta the shipped row
# claimed away: the sizeof/__builtin_choose_expr consumer of the typed-None
# gap was a FALSE-LOUD at 550998d (rc2, §2.6 sentence, capture
# .tmp/m4-w4/out/red-choose-at-550998d.txt) and is a PAIR from a11608a.
# The improvement landed legless; the legs below pin it (oracle decides).

def test_w4regate_choose_expr_sizeof_ptr_arith_pair(tmp_path):
    # sizeof(p + 2) must FOLD (else the choose control dies §2.6 rc2 — the
    # 550998d class) and fold RIGHT (the FALSE arm would answer n-38, not
    # n+40, changing the exit code; the bare sizeof(p+2) rides the same
    # fold). Expect 42: gcc -std=gnu89 -Os and blcc, SAME exit, measured.
    src = ("struct s { long a; };\n"
           "long f(struct s *p, long n) {\n"
           "  return __builtin_choose_expr(sizeof(p + 2) == 8, n + 40, n - 38);\n"
           "}\n"
           "long g(struct s *p) { return sizeof(p + 2); }\n"
           "int main(void){ struct s v; return (int)(f(&v, 2) + g(&v) - 8); }\n")
    _pair(tmp_path, "w4regate-choose", src, 42)


def test_w4regate_sizeof_alignof_binary_consumers_pair(tmp_path):
    # The three OTHER expr_type consumers over Binary operands, measured:
    # sizeof(p-p) = the LONG difference (8, not a pointer), sizeof(p+2) = 8,
    # __alignof__(p+2) = 8. gcc 24, blcc 24 — the parse gate and the engine
    # now agree on every consumer of the pointer view.
    src = ("struct s { long a; int b; };\n"
           "int main(void){ struct s v; struct s *p = &v;\n"
           "  long d = sizeof(p - p);\n"
           "  long w = sizeof(p + 2);\n"
           "  long al = __alignof__(p + 2);\n"
           "  return (int)(d + w + al); }\n")
    _pair(tmp_path, "w4regate-cons", src, 24)
