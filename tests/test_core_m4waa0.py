# LINES reason: one wave (M4 W-AA MC 12780): the light Call-arm law, its
# seam-consumer width rows and the one-home text gate are ONE contract; the
# run-pair rows are the measured law table and stay beside their gate.
"""M4 W-AA law battery (MC 12404.2.126 / job 12780): the light `expr_type`
Call arm — the §8 crowd's door, ONE home, and the seam consumers it feeds.

THE LAW. `skb_dst(skb)->output(net, sk, skb)` (include/net/dst.h:450 — the
dev-byte walk's sentence) is a call through a MEMBER OF A CALL RESULT. The
parse-side gate types the callee with the light mirror `Parser.expr_type`,
which had NO `ast.Call` arm, so the base answered None and the §8 gcc-rc1
twin LOUDed while the codegen engine (`TypeMap._ty`'s Call arm →
`_ind_call_ty`) typed the SAME program all along — the two-homes defect
(the W-AA sims, card 12778, measured the crowd: 15 Call-result streams of
the 17 §8 first-walls; the other 2 are StmtExpr callees, a DIFFERENT
missing arm that STAYS walled — this wave claims 15, never 17).

ONE HOME (the sims' §6 law, binding): the answer "what does a call return"
lives in exactly ONE text — `blcc.types.call_target_ret`, the pure body
lifted out of `TypeMap._ind_call_ty`. The engine arm and this mirror's arm
both DELEGATE to it; a second call-law text is what the one-home guard
test below turns RED. The named-function answer rides the shipped light
symbol shape `("fn", ret)` (the engine's `sigs[name][1]` twin) — ca01/ca02
have no fn-ptr to ride; ca21 has no symbol to ride; BOTH must answer.

THE SEAM (sims §2 S2): `expr_type` is not only the §8 gate — sizeof (§1
row 19), the W-Z CH37T `__auto_type` materializer, `_switch_label_width`
and `volatile_final` all read it. The width rows below (pl1/pl4 shapes)
pin that the arm answers the TARGET's return, not the fn-ptr — through the
live consumers, exit code as the type answer.
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4waa0_%s_%d_%s" % (os.environ.get("M4WAA_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# name -> (source, expect) — expect: exit code (run-pair, the kernel-REC
# program law) | "refuse" (BOTH sides LOUD — the §8 safe direction) |
# ("loud", FRAGMENT) (blcc LOUD while gcc answers — the INTENTIONAL
# divergence posture, pinned so a disarm can never ride silently).
ROWS = {
    # --- THE DOOR, verbatim (init_do_mounts.c.i 78538 <- dst.h:450) ---
    "a01-verbatim-dst450": ("""
struct dst_entry { int (*output)(void *net, void *sk, void *skb); };
struct sk_buff { int len; };
static struct dst_entry g;
static inline struct dst_entry __attribute__((__gnu_inline__))
__attribute__((__unused__)) __attribute__((no_instrument_function))
skb_dst_check(struct sk_buff *skb) { struct dst_entry r; r.output = 0;
	return r; }
static inline struct dst_entry *skb_dst(struct sk_buff *skb)
{ return &g; }
static int ip_output(void *n, void *s, void *k) { return 450; }
int answer(void)
{
	struct sk_buff s;
	g.output = ip_output;
	(void)skb_dst_check(&s);
	return skb_dst(&s)->output(0, 0, &s);
}
""" + MAIN, 194),
    # the DIRECT door the builder/gate hands pinned (k25): a static inline
    # returning the struct ptr (plant P2's row: the ("fn", ret) home).
    "a02-direct-inline-member": ("""
struct ops { int (*go)(int); };
struct ops g_ops;
static inline struct ops *get_ops(int k) { (void)k; return &g_ops; }
static int go_impl(int x) { return x + 2; }
int answer(void)
{
	g_ops.go = go_impl;
	return get_ops(1)->go(200);
}
""" + MAIN, 202),
    # value struct BY VALUE from a CALL, member fn-ptr (MEMORY class).
    "a04-value-struct-from-call": ("""
struct box { int (*fn)(int); };
static int imp(int x) { return x + 11; }
static struct box make_box(void)
{
	struct box b;
	b.fn = imp;
	return b;
}
int answer(void)
{
	return make_box().fn(204);
}
""" + MAIN, 215),
    # decayed-array rows: element callee, member-of-element, and the
    # element reached THROUGH a call base (ca05).
    "a05-array-element-callee": ("""
struct slot { int (*fn)(int); };
static int fa(int x){ return x + 1; }
static int fb(int x){ return x + 2; }
static struct slot tbl[2] = { { fa }, { fb } };
static struct slot *get_tbl(void) { return tbl; }
int t[2];
int answer(void)
{
	int (*p)(int);
	t[0] = 200;
	p = fa;
	return p(t[0]) + tbl[1].fn(0) + get_tbl()[0].fn(0);
}
""" + MAIN, 204),
    # union member callee THROUGH a call (post-W-Y §2.8 law).
    "a07-union-through-call": ("""
union chooser { int (*fn)(int); long raw; };
static union chooser g;
static int imp(int x) { return x + 7; }
static union chooser *get_u(void) { return &g; }
int answer(void)
{
	g.fn = imp;
	return get_u()->fn(207);
}
""" + MAIN, 214),
    # the designator shapes: `(*pp)` / `(**&pp)` — the light arms build
    # the PtrType view; `call_target_ret` decodes the ride.
    "a08-ptr-to-ptr-to-fn": ("""
static int imp(int x) { return x + 8; }
int answer(void)
{
	int (*p)(int) = imp;
	int (**pp)(int) = &p;
	return (*pp)(100) + (**&pp)(100);
}
""" + MAIN, 216),
    # VARIADIC member call (DoD interaction row; the gate must not size
    # the arg list through the mirror).
    "a09-variadic-member-call": ("""
struct fmts { int (*sum)(int, ...); };
static struct fmts g;
static int sum2(int n, ...)
{
	__builtin_va_list ap;
	int i, s = 0;
	__builtin_va_start(ap, n);
	for (i = 0; i < n; i++) s += __builtin_va_arg(ap, int);
	__builtin_va_end(ap);
	return s;
}
int answer(void)
{
	g.sum = sum2;
	return g.sum(3, 60, 70, 77);
}
""" + MAIN, 207),
    # attributed callee KEEPS (the attribute stack between decl and call).
    "a10-attributed-callee": ("""
struct dst_entry { int (*output)(int); };
struct dst_entry g;
static inline struct dst_entry *__attribute__((__gnu_inline__))
__attribute__((__unused__)) skb_dst_a(struct dst_entry *d) { return d; }
static int out_impl(int x) { return x + 10; }
int answer(void)
{
	g.output = out_impl;
	return skb_dst_a(&g)->output(200);
}
""" + MAIN, 210),
    # sizeof(call) rides the return type (the §1 row-19 mirror consumer).
    "a12-sizeof-call-result": ("""
struct two { int a; int b; };
static struct two mk(void)
{
	struct two t;
	t.a = 1; t.b = 2;
	return t;
}
int answer(void)
{
	return (int)sizeof(mk()) == 8 ? 212 : 213;
}
""" + MAIN, 212),
    # call-result feeding ARITHMETIC (width = type answer).
    "a13-arith-through-call": ("""
struct h { int (*get)(void); long (*big)(void); };
struct h g;
static int get_i(void) { return 20; }
static long get_l(void) { return 3L; }
int answer(void)
{
	g.get = get_i; g.big = get_l;
	return (int)(g.get() * 10) + (int)(g.big() * 1)
		+ (int)sizeof(g.get());
}
""" + MAIN, 207),
    # the CALL-RESULT QUALIFIER CHAIN: pointee quals ride, the value is
    # never qualified (plant P5's law, ca14).
    "a14-call-result-qualifiers": ("""
static const int tbl[3] = { 5, 7, 11 };
static const int *get_tbl(void) { return tbl; }
static volatile int v;
static volatile int *get_v(void) { return &v; }
int answer(void)
{
	const int *p = get_tbl();
	int s = p[1];
	*(get_v()) = 3;
	return s + v;
}
""" + MAIN, 10),
    # fn-ptr VAR vs direct call through ONE home (ca15).
    "a15-fnptr-var-vs-direct": ("""
struct d { int (*fn)(long); };
struct d g;
static long imp(long x) { return x + 15; }
int answer(void)
{
	long (*p)(long) = imp;
	long a;
	g.fn = imp;
	a = p(100L) + g.fn(100L);
	return (int)(a / 100) == 2 ? 215 : 216;
}
""" + MAIN, 215),
    # NEGATIVES — the §8 safe direction must stay BOTH-REFUSE.
    "a16-negative-noncallable": ("""
long x;
int answer(void)
{
	x = 1;
	return x(1);
}
""" + MAIN, "refuse"),
    "a17-negative-member-nonstruct": ("""
long *gl(void) { return 0; }
int answer(void)
{
	return gl()->m(1);
}
""" + MAIN, "refuse"),
    # __typeof__/__auto_type FROM a call — the W-H lazy TypeOf consumer.
    "a18-typeof-from-call": ("""
struct big { int a[4]; };
static struct big mk(void)
{
	struct big b;
	b.a[0] = 18;
	return b;
}
static int n4(void) { return 404; }
int answer(void)
{
	__auto_type v = n4();
	__auto_type p = mk();
	return v + p.a[0];
}
""" + MAIN, 166),
    # variadic callee that is a MEMBER OF A CALL RESULT (hash.h family).
    "a19-variadic-of-call-result": ("""
struct fmts { int (*v)(int, ...); };
static struct fmts g;
static int vsum(int n, ...)
{
	__builtin_va_list ap; int i, s = 0;
	__builtin_va_start(ap, n);
	for (i = 0; i < n; i++) s += __builtin_va_arg(ap, int);
	__builtin_va_end(ap);
	return s;
}
static struct fmts *get_fmts(void) { return &g; }
int answer(void)
{
	g.v = vsum;
	return get_fmts()->v(2, 100, 108);
}
""" + MAIN, 208),
    # NAMED-DIVERGE (sims ca20, pinned AS-IS): the ternary-of-values
    # callee through a call base — the light ptr-key (S1 seam) collapses
    # PtrType(StructType) to void*, so the member never resolves and the
    # §8 twin answers where gcc answers 220. The row pins the divergence;
    # widening `_light_ptr_key` is NOT this wave.
    "a20-cond-callee-diverge": ("""
struct ops { int (*fn)(int); };
static struct ops A, B;
static int fa(int x) { return x + 20; }
static int fb(int x) { return x + 21; }
static struct ops *get_a(void) { A.fn = fa; return &A; }
static struct ops *get_b(void) { B.fn = fb; return &B; }
int answer(void)
{
	return (1 ? get_a() : get_b())->fn(200);
}
""" + MAIN, ("loud", "called object is not a 'function'")),
    # THE DECAYED home (plant P3's row): a member of the result of a call
    # made through a fn-ptr VAR — no ("fn", ret) symbol to ride.
    "a21-decayed-home-var": ("""
struct ops { int (*go)(int); };
static struct ops g_ops;
static struct ops *(*fp)(void);
static struct ops *impl(void) { return &g_ops; }
static int go_impl(int x) { return x + 21; }
int answer(void)
{
	g_ops.go = go_impl;
	fp = impl;
	return fp()->go(200);
}
""" + MAIN, 221),
    # THE QUALIFIED TARGET (plant P5's row): `struct ops * const f(void)`
    # — the top qual eats, the pointee quals ride.
    "a22-qualified-target": ("""
struct ops { int (*go)(int); };
static struct ops g_ops;
static int go_impl(int x) { return x + 22; }
static struct ops * const get_ops(void) { return &g_ops; }
int answer(void)
{
	g_ops.go = go_impl;
	return get_ops()->go(200);
}
""" + MAIN, 222),
    # --- DoD interaction rows ---
    # call-through-member INSIDE the splice, POST-RENAME: the inliner
    # mints fresh binding names per param (W-W SPICE-SCOPE law); the
    # spliced body's callee is a member of a CALL RESULT, and the second
    # site carries a caller object named like the param (the capture
    # class the rename exists for). gcc 201+6 = 207.
    "a23-splice-post-rename": ("""
struct ops { int (*go)(int); };
static struct ops G;
static struct ops *pick(struct ops *o, int k) { (void)k; return o; }
static int imp(int x) { return x + 1; }
static inline int use(struct ops *o, int k) { return pick(o, k)->go(k); }
int answer(void)
{
	struct ops *p = &G;
	int k = 5;
	G.go = imp;
	return use(p, 200) + use(p, k);
}
""" + MAIN, 207),
    # decayed-array ARGUMENT into a call-through-member of a call result.
    "a25-decayed-array-arg": ("""
struct agg { int (*sum)(const int *, int); };
static struct agg g;
static struct agg *get_agg(void) { return &g; }
static int sum(const int *v, int n)
{
	int i, s = 0;
	for (i = 0; i < n; i++) s += v[i];
	return s;
}
int answer(void)
{
	int arr[3];
	arr[0] = 5; arr[1] = 7; arr[2] = 11;
	g.sum = sum;
	return get_agg()->sum(arr, 3);
}
""" + MAIN, 23),
    # the WIDTH seam (sims §2 S2, plant P3/P4 read THROUGH the consumer):
    # a short-returning fn-ptr reached through a call, sized through the
    # CH37T __auto_type materializer — the arm answers the TARGET's
    # return (2), not the fn-ptr (8).
    "a26-width-through-call": ("""
struct h { short (*get)(void); };
static short get_s(void) { return 7; }
struct h g = { get_s };
static struct h *get_h(void) { return &g; }
int answer(void)
{
	__auto_type v = get_h()->get();
	g.get = get_s;
	v = g.get();
	return (int)sizeof(v) == 2 ? 231 : 232;
}
""" + MAIN, 231),
    # the §2.14 door STAYS LOUD through the new arm: a STRUCT returned by
    # a VARIADIC call is the shipped LOUD-DIV twin — the Call arm must
    # not silently size it (the plant "variadic answers int" bypasses
    # this refusal and goes RED at the teeth leg).
    "a28-variadic-struct-loud": ("""
struct two { short x; short y; };
static struct two vs(int n, ...)
{
	struct two t;
	__builtin_va_list a;
	__builtin_va_start(a, n);
	t.x = n; t.y = (short)__builtin_va_arg(a, int);
	__builtin_va_end(a);
	return t;
}
int answer(void)
{
	struct two (*p)(int, ...) = vs;
	__auto_type v = p(2, 50);
	return (int)sizeof(v) == 2 ? 250 : 251;
}
""" + MAIN, ("loud", "variadic call")),
    # a VARIADIC target through a fn-ptr VAR, sized through the __auto_type
    # consumer: the law answers the TARGET's return (short), not a
    # guessed int — the plant "variadic answers int" moves this row (the
    # §2.14 struct door louds whatever the arm answers, so the width row,
    # not the struct row, is the one that catches a variadic mis-size).
    "a31-variadic-width": ("""
static short fs(int n, ...)
{
	__builtin_va_list a;
	int r;
	__builtin_va_start(a, n);
	r = n + __builtin_va_arg(a, int);
	__builtin_va_end(a);
	return (short)r;
}
int answer(void)
{
	short (*p)(int, ...) = fs;
	__auto_type v = p(2, 60);
	return (int)sizeof(v) == 2 ? 236 : 237;
}
""" + MAIN, 236),
    # the TOP-QUALIFIED fn-ptr VAR reached as a callee: the value decays
    # and the const on the POINTER does not stop the call (plant
    # "qualifier chain not eaten" re-walls this row).
    "a30-top-qualified-fnptr-var": ("""
struct ops { int (*go)(int); };
static struct ops g;
static struct ops *impl(void);
static struct ops *(* const cv)(void) = impl;
static struct ops *impl(void) { return &g; }
static int go_impl(int x) { return x + 24; }
int answer(void)
{
	g.go = go_impl;
	return cv()->go(200);
}
""" + MAIN, 224),
    # the QUALIFIED-MEMBER callee: the callee's own type carries a
    # top-level qual (`int (* const go)(int)`); the ONE home eats it
    # (plant "qualifier chain not eaten" re-walls this row).
    "a29-qualified-member-callee": ("""
struct ops { int (* const go)(int); };
static int imp(int x) { return x + 23; }
static struct ops g = { .go = imp };
static struct ops *get_t(void) { return &g; }
int answer(void)
{
	return get_t()->go(200);
}
""" + MAIN, 223),
}


def _setup():
    os.makedirs(TMP, exist_ok=True)


_setup()


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe]
        env = None
    else:
        exe = os.path.join(TMP, tag + ".blcc")
        cmd = ["python3", "-m", "blcc", c, "-o", exe]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    return r, exe


@pytest.mark.parametrize("name", sorted(ROWS))
def test_call_arm_law_run_pairs(name):
    src, expect = ROWS[name]
    if expect == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0, "gcc twin must refuse"
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, "blcc must keep the §8 refusal"
        assert "§8" in rb.stderr or "called object" in rb.stderr, \
            "%s: the refusal must be the §8 twin:\n%s" % (
                name, rb.stderr[:300])
        return
    if isinstance(expect, tuple):
        frag = expect[1]
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, \
            "%s: the shipped divergence posture must stay LOUD (a silent " \
            "answer here is the disarm):\n%s" % (name, rb.stdout[:200])
        assert frag in rb.stderr, \
            "%s: wrong refusal, wanted %r:\n%s" % (
                name, frag, rb.stderr[:300])
        return
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "blcc rc=%d:\n%s" % (rb.returncode, rb.stderr)
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


# ------------------------------------------------------------------ ONE HOME
# The sims' §6 law as a TEXT gate: "what does a call return" is answered
# by ONE text (`call_target_ret` in blcc/types.py); the engine arm and the
# light mirror arm both DELEGATE. A restated decay law in the mirror arm —
# exactly the sim-stub shape the P2/P3 plants encode — is a SECOND home:
# two texts drift (the sims measured which row each home misses), and this
# gate turns that RED deterministically, not by taste.
LAW_TEXT = re.compile(r"(?:tgt|ty|base|v)\w*\.inner\.ret")


def _blcc_sources():
    d = os.path.join(REPO, "blcc")
    return {f: open(os.path.join(d, f)).read()
            for f in sorted(os.listdir(d)) if f.endswith(".py")}


def test_call_law_has_exactly_one_home():
    src = _blcc_sources()
    homes = [f for f, txt in src.items() if LAW_TEXT.search(txt)]
    assert homes == ["types.py"], \
        "the call-return law text lives in %s — ONE home only " \
        "(MC 12780): delegate to call_target_ret, never restate" % homes
    types_src = src["types.py"]
    assert types_src.count("def call_target_ret(") == 1
    body = types_src.split("def call_target_ret(", 1)[1]
    body = body.split("\nwalk_fields", 1)[0]
    assert LAW_TEXT.search(body), \
        "the one home must CONTAIN the law text (an empty shell moving " \
        "the law elsewhere is still a second home)"


def test_light_call_arm_delegates_not_restates():
    arm = open(os.path.join(REPO, "blcc", "parser.py")).read()
    arm = arm.split("if isinstance(node, ast.Call):", 1)
    assert len(arm) > 1, "the light mirror lost its Call arm"
    arm = arm[1].split("if isinstance(node, ast.Unary)", 1)[0]
    assert "call_target_ret(" in arm, \
        "the mirror's Call arm must DELEGATE to call_target_ret"
    assert "ast.FuncType" not in arm and ".ret" not in arm, \
        "the mirror's Call arm restates the call law — second home " \
        "(MC 12780 one-home law)"
