# LINES reason: one wave of legs (M4 W-P COMMIT-1 — THE inline pass,
# card 12404.2.89): every leg is an arm of ONE splice/discard law; a
# split would separate the witness from its guards.
r"""M4 W-P COMMIT-1 — THE INLINE PASS (plan AMENDMENT-17; card
12404.2.89). AMENDMENT-16 ruled R1 param-substitution OUT (0/485
eligible, naive substitution VALUE-CORRUPT); the real function-body
splice is the lever for the walk death at arch/x86/include/asm/
nospec-branch.h:375:7 — `"i" (feature)` on the CALLEE param — and the
485-stream crowd (measured: ALL 485 first-blockers sit in the one
definition of `alternative_msr_write`; per-stream: 1 call site, const
`i`-feed, single-asm body, and `_static_cpu_has` (asm-goto, NOT in the
splice universe) waits behind it — CURRENCY = WALK ADVANCEMENT, the
accepts law (pin STAYS flipped per AM17) is untouched).

THE LAW: a file-scope `static inline` whose every call site is in
STATEMENT position and whose body is in the splice universe (no
goto/label/asm-goto/static local/register-asm, scalar params,
void/scalar return, not recursive/cyclic, not address-taken, not an
alias target) is spliced AT the site by the existing statement emitter:
params copy-in left-to-right with the §2.2 conversion (row i01:
`f(i++, i)` = 8 both sides); the standalone copy of a candidate that
HAS call sites and is fully spliced is DISCARDED. MEASURED-TRUTH
REPAIR (M4 W-Q MC 12712, gate MC 12708 F-1): a ZERO-call-site static
inline is NOT discarded — `_inl_analyze` skips site-less candidates and
the copy survives in all three spellings (nm pin
test_wp1_zero_site_keeps_copy; rows i03/i05/i08 measured GCC's -Os
posture only: no symbol survives in GCC's .s). A param
whose caller-arg folds to a constant answers the imm closure with the
LITERAL (`.word 245`), guarded: body writes/addresses the param →
slot-only → the S5/L4 refusal stands (named LOUD twin — row i15).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
TMP = "/dev/shm"


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


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _pair(tag, src, want=None):
    """Compile with BOTH (gcc REC = the oracle, blcc -c object linked by
    gcc -no-pie, house idiom); returns (grc, blcc_rc, gex, bex, btxt)."""
    c = "/dev/shm/wp1_%s.c" % tag
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "/dev/shm/wp1_%s.g" % tag])
    assert g.returncode == 0, "probe must be valid C: " + g.stderr
    gs = gcc(REC + ["-S", c, "-o", "/dev/shm/wp1_%s.g.s" % tag])
    gex = _run("/dev/shm/wp1_%s.g" % tag)
    o = "/dev/shm/wp1_%s.b.o" % tag
    b = blcc(["-c", c, "-o", o])
    bex = btxt = None
    if b.returncode == 0:
        assert gcc([o, "-no-pie", "-o", "/dev/shm/wp1_%s.b" % tag]
                   ).returncode == 0, "link must work"
        bex = _run("/dev/shm/wp1_%s.b" % tag)
        blcc(["-c", c, "--emit-asm", "-o", "/dev/shm/wp1_%s.bt" % tag])
        btxt = open("/dev/shm/wp1_%s.bt.s" % tag).read()
    if want is not None:
        assert (gex, bex) == (want, want), \
            "%s: value pair %s vs %s" % (tag, gex, bex)
    return g.returncode, b.returncode, gex, bex, btxt


# VERBATIM (own-hands slice) of the pinned-corpus witness region:
# .tmp/m4-wp/clean/arch_x86_kernel_i8259.c.i lines 9142-9161 — the
# post-pp `alternative_msr_write` definition (the nospec-branch.h:375
# stream, template merged by the pp exactly as the corpus carries it),
# `extern u64 x86_pred_cmd;` and the barrier whose call feeds the
# constant `( 7*32+21)`. Head/tail are the test's own typedefs/main.
NOSPEC = """
typedef long unsigned int u64;
typedef unsigned int u32;
static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) __attribute__((no_instrument_function)) __attribute__((__always_inline__))
void alternative_msr_write(unsigned int msr, u64 val, unsigned int feature)
{
 asm volatile("# ALT: oldnstr\\n" "661:\\n\\t" "" "\\n662:\\n" "# ALT: padding\\n" ".skip -(((" "665""1""f-""664""1""f" ")-(" "662b-661b" ")) > 0) * " "((" "665""1""f-""664""1""f" ")-(" "662b-661b" ")),0x90\\n" "663" ":\\n" ".pushsection .altinstructions,\\"a\\"\\n" " .long 661b - .\\n" " .long " "664""1""f - .\\n" " .word " "%c[feature]" "\\n" " .byte " "663""b-661b" "\\n" " .byte " "665""1""f-""664""1""f" "\\n" ".popsection\\n" ".pushsection .altinstr_replacement, \\"ax\\"\\n" "# ALT: replacement " "1" "\\n" "664""1" ":\\n\\t" "wrmsr" "\\n" "665""1" ":\\n" ".popsection\\n"
  : : "c" (msr),
      "a" ((u32)val),
      "d" ((u32)(val >> 32)),
      [feature] "i" (feature)
  : "memory");
}

extern u64 x86_pred_cmd;

static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) __attribute__((no_instrument_function)) void indirect_branch_prediction_barrier(void)
{
 alternative_msr_write(0x00000049, x86_pred_cmd, ( 7*32+21));
}
u64 x86_pred_cmd;
"""


def test_wp1_nospec_witness():
    """RED AT TIP (`'i' operand is not a compile-time constant`)."""
    g, b, gex, bex, btxt = _pair(
        "nospec", NOSPEC + "\nint main(void){ indirect_branch_prediction_"
        "barrier(); return 3; }\n", want=3)
    assert b == 0, b
    assert ".word 245" in btxt, "the %c[feature] fold lost its literal"
    assert not re.search(r"^alternative_msr_write:", btxt, re.M), \
        "fully-spliced callee kept a standalone copy"
    assert not re.search(r"^indirect_branch_prediction_barrier:", btxt,
                         re.M)


def test_wp1_discard_site_inside_uncalled_caller():
    """MEASURED BEHAVIOR (renamed M4 W-Q MC 12712 from the misleading
    `test_wp1_discard_zero_site`, gate MC 12708 F-1): the discarded
    callee `alternative_msr_write` HAS a call site — inside the
    uncalled barrier — is fully spliced there, and its standalone copy
    is gone (gcc keeps neither symbol: the parity row below). The
    ZERO-site barrier itself is NOT discarded (pin:
    test_wp1_zero_site_keeps_copy); the walk's init/main.o never
    needed a zero-site discard — its uncalled barrier copy compiles
    because the callee splices INSIDE that copy."""
    g, b, gex, bex, btxt = _pair(
        "zero", NOSPEC + "\nint main(void){ return 3; }\n", want=3)
    assert b == 0
    assert "alternative_msr_write" not in btxt
    assert re.search(r"^indirect_branch_prediction_barrier:", btxt,
                     re.M), \
        "measured truth: the ZERO-site caller keeps its copy"
    gtxt = open("/dev/shm/wp1_zero.g.s").read()
    assert "alternative_msr_write" not in gtxt     # parity row


def test_wp1_zero_site_keeps_copy():
    """MEASURED-TRUTH pin (M4 W-Q MC 12712, gate F-1 repair-forward):
    a ZERO-call-site static inline keeps its standalone copy in ALL
    THREE spellings — plain / `always_inline` / `gnu_inline` (nm at
    tip: t f_plain/f_alw/f_gnu, .tmp/m4-wq/out/c0-claim-red.txt) where
    gcc -Os keeps none. The 11319 extra copies the gate measured over
    the 46 accepts are THIS class — code-size story, routed to the
    F-8 family with the real zero-site discard (plan AMENDMENT-18);
    W-Q ships NO discard behavior. If a future wave lands the real
    discard, re-pin this leg to gcc parity HERE, not silently."""
    src = ("static inline int f_plain(int a){ return a + 1; }\n"
           "static inline __attribute__((__always_inline__)) int "
           "f_alw(int a)\n{ return a + 2; }\n"
           "static inline __attribute__((__gnu_inline__)) int f_gnu"
           "(int a)\n{ return a + 3; }\n"
           "int main(void){ return 3; }\n")
    g, b, _gex, _bex, btxt = _pair("zskeep", src, want=3)
    assert g == 0 and b == 0
    gtxt = open("/dev/shm/wp1_zskeep.g.s").read()
    for fn in ("f_plain", "f_alw", "f_gnu"):
        assert re.search("^%s:" % fn, btxt, re.M), \
            "zero-site copy vanished — real discard shipped? re-pin " \
            "this law to gcc parity in the same commit"
        assert not re.search("^%s:" % fn, gtxt, re.M), \
            "oracle moved at -Os — re-measure before touching the law"


def test_wp1_slot_param_load():
    """Inline substitutes NON-CONSTANT where gcc keeps the load: the
    `r`-constraint param rides the caller slot at -Os (both sides run
    the copy)."""
    src = ("int acc;\nstatic inline __attribute__((__always_inline__)) "
           "void f(int p){ asm volatile(\"movl %0, %%eax\\n\\tmovl "
           "%%eax, acc+0(%%rip)\" : : \"r\"(p) : \"memory\"); }\n"
           "int main(void){ int t = 41; acc = 0; f(t + 2); f(acc); "
           "return acc & 0xff; }\n")
    _pair("slot", src, want=43)


def test_wp1_write_mask_loud():
    """Slot-only guard (tooth class: 'inline drops asm `i` param
    binding'): a body that WRITES its param must not answer the imm
    fold with a stale literal — the S5/L4 refusal stands, LOUD."""
    src = NOSPEC.replace('"i" (feature)', '"i" (feature)/*w*/').replace(
        "\n asm volatile", "\n feature |= 8;\n asm volatile")
    g, b, _g, _b, _t = _pair("wmask", src + "\nint main(void){ "
                             "indirect_branch_prediction_barrier(); "
                             "return 3; }\n")
    assert g == 0
    assert b != 0, "slot-only param folded a literal — stale-value plant"


def test_wp1_recursion_twin():
    """Recursion guard (tooth class): the cyclic candidate keeps
    today's call+copy posture; the VALUE pairs (24)."""
    src = ("static inline __attribute__((__always_inline__)) int r(int n)"
           "{ return n <= 0 ? 1 : n * r(n - 1); }\n"
           "int main(void){ return r(4) & 0xff; }\n")
    _pair("rec", src, want=24)


def test_wp1_multi_site():
    """Two statement sites: both spliced, copy discarded, frame grows
    per site (row i10: gcc reuses slots — blcc grows; VALUE pairs)."""
    src = ("static inline __attribute__((__always_inline__)) void f(int v)"
           "{ extern int acc; acc += v + 1; }\n"
           "int acc;\n"
           "int main(void){ f(1); f(41); return acc & 0xff; }\n")
    g, b, gex, bex, btxt = _pair("multi", src, want=44)
    assert not re.search(r"^f:", btxt, re.M)


def test_wp1_multi_site_value():
    """W-R (MC 12714) FLIPPED PIN: value-position sites ARE spliced now
    — the same pass covers the value seam (the epilogue answers %rax),
    the copy is discarded. The VALUES of row i10 still pair (44 both);
    only the posture flipped (was: "value site must keep the copy" —
    W-P law, superseded by plan AMENDMENT-19; the ORDER-UNDEFINED twin
    of test_wp1_value_position_untouched STANDS unchanged)."""
    src = ("static inline int f(int v){ return v + 1; }\n"
           "int main(void){ return (f(1) + f(41)) & 0xff; }\n")
    g, b, gex, bex, btxt = _pair("msite", src, want=44)
    assert not re.search(r"^f:", btxt, re.M), "value site now splices"


def test_wp1_addr_taken_param():
    """&param inside a SPLICED body: the copy-in slot is the param's
    object (row i02 shape: 47 — caller's x untouched)."""
    src = ("int res;\nstatic inline __attribute__((__always_inline__)) "
           "void f(int p){ int *q = &p; *q += 3; res = p; }\n"
           "int main(void){ int x = 4; f(x); return res + x * 10 & 0xff; }\n")
    _pair("atp", src, want=47)


def test_wp1_name_collide():
    """Callee locals cannot collide with caller locals (i04: 107)."""
    src = ("static inline __attribute__((__always_inline__)) int f(int v)"
           "{ int t = v * 2; return t + 1; }\n"
           "int main(void){ int t = 100; f(3); return (6 + t) & 0xff; }\n")
    _pair("ncol", src, want=106)


def test_wp1_static_local_guard():
    """Static local ⇒ NOT expandable: today's call+copy stands, the
    shared-object value law pairs (i07: 4) and the copy survives."""
    src = ("static inline __attribute__((__always_inline__)) int f(int d)"
           "{ static int s = 0; s += d; return s; }\n"
           "int main(void){ int a; a = f(1); a = f(2); return a & 0xff; }\n")
    g, b, gex, bex, btxt = _pair("sloc", src, want=3)
    assert re.search(r"^f(\.|:)", btxt, re.M), "guard must keep the copy"


def test_wp1_addrtaken_fn():
    """The fn name used as a VALUE keeps symbol + call (fn-ptr law)."""
    src = ("static inline __attribute__((__always_inline__)) int f(int v)"
           "{ return v + 2; }\n"
           "int (*p)(int);\nint main(void){ p = f; return p(40) & 0xff; }\n")
    g, b, gex, bex, btxt = _pair("afn", src, want=42)
    assert re.search(r"^f:", btxt, re.M)


def test_wp1_alias_target_kept():
    """§6 alias: an alias target is never discarded (fairness — the
    `.set` needs its body; both compilers keep it)."""
    src = ("static inline __attribute__((__always_inline__)) int f(int v)"
           "{ return v + 2; }\n"
           "extern int g(int) __attribute__((alias(\"f\")));\n"
           "int main(void){ return g(3) & 0xff; }\n")
    g, b, gex, bex, btxt = _pair("al", src, want=5)
    assert re.search(r"^f:", btxt, re.M)


def test_wp1_i128_param_guard():
    """i128 params are NOT in the splice universe; the existing §6
    GPR-PAIR refusal stands UNCHANGED (tip law — the splice neither
    relaxes nor re-homes it; gcc answers, named LOUD-DIV)."""
    src = ("__int128 acc;\nstatic inline __attribute__((__always_inline"
           "__)) void f(__int128 v){ acc += v; }\n"
           "int main(void){ f(1); f(40); return (int)(acc & 0xff); }\n")
    g, b, gex, bex, _t = _pair("i128", src)
    assert g == 0 and gex == 41
    assert b != 0                              # the tip refusal stands


def test_wp1_switch_spliced_result():
    """W-P × W-O interaction: a spliced callee feeds the constant
    switch whose arm carries the W-M materialized `%P` and a cmpxchg
    — ONE call graph, run-value pair."""
    src = ("""
int lock; int want;
static inline __attribute__((__always_inline__)) int probe(int v)
{ return v & 3; }
static inline __attribute__((__always_inline__)) void tag(int m, unsigned f)
{ asm volatile(".pushsection .altinstructions,\\"a\\"\\n .word %c[ff]\\n"
  ".popsection\\n" : : "c"(m), [ff] "i"(f) : "memory"); }
int main(void)
{
  int old = 9;
  lock = 9; want = 7;
  tag(0x3b, ( 7*32+21 ));
  switch (probe(6)) {
  case 2:
    asm volatile("lock cmpxchgl %P1, %0" : "+m"(lock) : "r"(want),
                 "a"(old) : "memory");
    break;
  default:
    break;
  }
  return lock & 0xff;
}
""")
    _pair("inter", src, want=7)


def test_wp1_arg_twice_aliasing():
    """Row i01: param read twice + side-effecting arg — copy-in ONCE,
    left-to-right (8 both sides)."""
    src = ("static inline __attribute__((__always_inline__)) int f(int a,"
           " int b){ int r; r = a*b + a; a = a + b; return r + 0*a; }\n"
           "int main(void){ int i = 2; int x = f(i++, i); return x & "
           "0xff; }\n")
    _pair("tw", src, want=8)


def test_wp1_value_position_untouched():
    """Order/position law: a call used as a VALUE keeps the existing
    staging order — this leg pins blcc 21 (gcc -Os stages right-to-left
    and answers 12: the ORDER-UNDEFINED class, NAMED, unchanged by
    W-P — the same values stand at tip)."""
    src = ("int a;\nint g1(void){ a += 10; return a; }\n"
           "int g2(void){ a += 1; return a; }\n"
           "static inline __attribute__((__always_inline__)) int f(int x,"
           " int y){ return x + y; }\n"
           "int main(void){ int v = f(g1(), g2()); return v & 0xff; }\n")
    g, b, gex, bex, _t = _pair("ord", src)
    assert b == 0 and bex == 21, (bex,)      # blcc law: left-to-right
    assert gex == 12                          # gcc -Os: right-to-left


def test_wp1_cycle_stmt_sites():
    """Cycle guard TOOTH: two static inlines calling EACH OTHER in
    STATEMENT position are every-site-eligible; only the call-cycle
    guard keeps them the CALL law (compile never diverges, values 6)."""
    src = ("int acc;\nstatic inline void b(int n);\n"
           "static inline void a(int n){ if (n) b(n - 1); }\n"
           "static inline void b(int n){ acc += 1; a(n); }\n"
           "int main(void){ a(5); return acc & 0xff; }\n")
    _pair("cyc", src, want=5)


PINNED = "/home/claudecode/Blaha/.tmp/m4-plan/streams"


def test_wp1_corpus_wall_moved():
    """CORPUS SPOT (the close instrument's permanent pin): a pinned
    485-crowd stream (arch_x86_kernel_i8259.c.i) first-blocked at tip
    on the 'i'-param 'i'-closure wall; W-P moved it ONTO the block-scope
    struct wall; W-Q (MC 12712) moved it AGAIN onto the cpufeature.h
    'i' class (asm-goto `_static_cpu_has` — the W-R queue-behind wall,
    F-4 WALL-IS-A-QUEUE doctrine). Path-gated: the pinned corpus dir
    decides. F-2 HARDENING (M4 W-R COMMIT-0, gate MC 12713): the pin
    rides the SITE — clean-stream :10493:, the post-pp `_static_cpu_has`
    definition (cpufeature.h:187 in the walk) — because the class
    string alone is SHARED with the retired W-P nospec-branch.h:375
    wall and could not tell the two apart; the class string stays as
    the secondary check."""
    if not os.path.isdir(PINNED):
        import pytest
        pytest.skip("pinned corpus not linked (builder posture)")
    src = PINNED + "/arch_x86_kernel_i8259.c.i"
    clean = "/dev/shm/wp1_i8259_clean.c"
    import re as _re
    lm = _re.compile(r"^#\s+\d+\s+\"")
    with open(src, errors="replace") as fh, open(clean, "w") as oh:
        for ln in fh:
            if not lm.match(ln):
                oh.write(ln)
    r = blcc(["-c", clean, "-o", "/dev/shm/wp1_i8259.o"])
    assert r.returncode != 0            # still a honest RED…
    assert "struct declaration in block scope" not in r.stderr, \
        "the W-Q wall came back: " + r.stderr[:200]
    first = next(ln for ln in r.stderr.splitlines() if ln.strip())
    # W-R (MC 12714) FLIPPED SITE PIN with the wave (same precedent as
    # W-Q's "4 wall pins FLIPPED"): the asm-goto splice eats the
    # cpufeature copy-posture — the COMMIT-0 pins (":10493:" standing,
    # class "'i' operand") are asserted GONE — and the stream lands on
    # the NAMED behind-class, the `__here` label wall (the 193-stream
    # crowd; F-4 WALL-IS-A-QUEUE), clean-stream :11342:.
    # M4 W-S (MC 12716) FLIPPED THIS PIN AGAIN: COMMIT-2's scoped
    # `__label__` law eats the `__here` wall — the ":11342:" SITE and
    # the "used but not defined" CLASS are asserted GONE — and the
    # stream lands on the next behind-class, the expression-'construct'
    # wall at clean :22228:70 (a NEW top-class row of the W-S close
    # sweep, named there).
    # M4 W-T (MC 12736) FLIPPED THIS PIN A THIRD TIME: COMMIT-1 eats
    # the expression-'construct' wall — the ":22228:70" SITE and the
    # "'construct'" CLASS are asserted GONE (queue law, W-T combo
    # sweep numbers) — and the stream lands on the combo sweep's NEW
    # top-class behind-row, `not an addressable l-value` (the
    # ({...})-as-lvalue class) at clean :35846:10 — the 279-stream
    # blocker named as the next wave's lever.
    assert ":10493:" not in first and "constraint 'i' operand is not a " \
        "compile-time" not in first, "the cpufeature wall came back: " \
        + first[:300]
    assert ":11342:" not in first and "label '__here' used but not " \
        "defined" not in first, "the __label__ wall came back: " \
        + first[:300]
    assert "found 'construct'" not in first, \
        "the expression-construct wall (W-S behind-class) must be " \
        "EATEN by W-T COMMIT-1: " + first[:300]
    # M4 W-U (MC 12739) FLIPPED THIS PIN A FOURTH TIME, exactly as this
    # docstring predicted ("the 279-stream blocker named as the next
    # wave's lever"): COMMIT-1's copy-source law eats the
    # `({...})`-as-lvalue wall — the ":35846:10" SITE and the
    # "not an addressable l-value / statement expression" CLASS are
    # asserted GONE — and the stream lands on the extern-local
    # `zero_pfn` class at clean :36317:16, the row the W-U {A+B+D}
    # combo sweep (153 → 181, own hands) shows COMMIT-2 eating.
    assert ":35846:10" not in first \
        and "not an addressable l-value" not in first, \
        "the statement-expression l-value wall (W-U's own class) came " \
        "back: " + first[:300]
    assert ":36317:" in first and "'zero_pfn' undeclared" in first, \
        "wall must land on the named behind SITE+CLASS (clean " \
        ":36317:16 = the extern-local zero_pfn wall): " + first[:300]
