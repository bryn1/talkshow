# LINES reason: one wave (M4 W-AB COMMIT-1 MC 12783): the §5-conditional
# struct-arm law is ONE contract; the 27-row sims battery is the measured
# law table and stays beside its door (rows verbatim from card 12781).
"""M4 W-AB battery (MC 12404.2.129 / job 12783): §5 STRUCT VALUE in the
conditional `?:` — the arm the 13-stream crowd and the do_mounts walk hit.

THE DOOR (tip `expr_codegen.py:_ex_cond`): when the conditional's result
type is a StructType the tip LOUDed "'struct assignment' is not in the
subset (§5) — the conditional arm would copy a struct". The walk's 3rd
sentence (init_do_mounts.c.i 80619 ← include/net/sock.h:2026) and 12
streams stand behind exactly this arm.

THE LAW (sims card 12781, §3 — value-as-address, the ONE home): the
result is materialized in ONE frame temp by the SHIPPED `_slot` law;
BOTH arms are emitted as ADDRESSES through the shipped `_emit_addr`
family (the same door the W-H struct assign, the W-M struct-call temp
and the W-U statement-expression source already ride); the SELECTED arm
runs ONCE (control flow, not a fold); the copy is the SHIPPED
`_copy_block` size law (chunked GPR ≤16, rep movsb beyond, zero
libcalls — W-H MC 12645), whose ONLY emission in this file is
`_copy_block` itself (the text gate below — a second copy home is the
plant it turns RED); the VALUE is the temp's ADDRESS (object IS the
value — the W-H i128-pair law); `_emit_addr` gains Cond as a value-as-
address family member for the TARGET position `(c ? a : b) = s`.
The GNU `a ?: b` struct form and an arm `_emit_addr` cannot address
keep their shipped walls — never a faked hidden return.

The 27 rows are the sims' battery VERBATIM (row names, sources and
expectations = law-matrix.md at my hands): 18 run-pair PAIR rows, 9
BOTH-REFUSE negatives. sa12 pins the DOCUMENTED REDUNDANCY row: the
copy law never reads the volatile marker (`_decay`/`_untype` drop it;
sims §1 — "documented-redundancy row pinned").
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wab1_%s_%d_%s" % (os.environ.get("M4WAB_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# name -> (source, expect): exit code (run-pair) | "refuse" (BOTH sides
# LOUD — the safe direction stays BOTH-REFUSE).
ROWS = {
    "sa01-whole-assign": ("""
struct S { int a; int b; };
int answer(void)
{
	struct S s, t;
	s.a = 1; s.b = 94;
	t.a = 0; t.b = 0;
	t = s;
	return t.a * 100 + t.b;
}
""" + MAIN, 194),
    "sa02-union-assign": ("""
union U { int i; char c; };
int answer(void)
{
	union U u, v;
	u.i = 194;
	v.c = 1;
	v = u;
	return v.i;
}
""" + MAIN, 194),
    "sa03-const-rhs": ("""
struct S { int a; int b; };
int answer(void)
{
	const struct S cs = { 1, 94 };
	struct S s;
	s.a = 0; s.b = 0;
	s = cs;
	return s.a * 100 + s.b;
}
""" + MAIN, 194),
    "sa04-const-lhs-neg": ("""
struct S { int a; };
int answer(void)
{
	const struct S cs = { 1 };
	struct S s;
	s.a = 7;
	cs = s;
	return cs.a;
}
""" + MAIN, "refuse"),
    "sa05-self-assign": ("""
struct S { int a; int b; };
int answer(void)
{
	struct S s;
	s.a = 1; s.b = 94;
	s = s;
	return s.a * 100 + s.b;
}
""" + MAIN, 194),
    "sa06-ptr-target": ("""
struct S { int a; int b; };
int answer(void)
{
	struct S s, o;
	struct S *p = &o;
	s.a = 1; s.b = 94;
	o.a = 0; o.b = 0;
	*p = s;
	return p->a * 100 + p->b;
}
""" + MAIN, 194),
    "sa07-nested-member": ("""
struct In { int x; int y; };
struct Out { int z; struct In in; };
int answer(void)
{
	struct In in2; struct Out o1;
	in2.x = 1; in2.y = 94;
	o1.z = 7; o1.in.x = 0; o1.in.y = 0;
	o1.in = in2;
	return o1.in.x * 100 + o1.in.y;
}
""" + MAIN, 194),
    "sa08-array-member-copy": ("""
struct T { int a; int arr[3]; };
int answer(void)
{
	struct T t1, t2;
	t1.a = 0; t1.arr[0] = 0; t1.arr[1] = 0; t1.arr[2] = 0;
	t2.a = 7; t2.arr[0] = 1; t2.arr[1] = 2; t2.arr[2] = 94;
	t1 = t2;
	return t1.a * 20 + t1.arr[2];
}
""" + MAIN, 234),
    "sa09-array-member-assign-neg": ("""
struct T { int arr[3]; };
int answer(void)
{
	struct T t1, t2;
	t1.arr[0] = 1;
	t2.arr[0] = 0;
	t2.arr = t1.arr;
	return t2.arr[0];
}
""" + MAIN, "refuse"),
    "sa10-bitfield-struct-assign": ("""
struct B { unsigned a : 3; unsigned b : 13; unsigned c : 16; };
int answer(void)
{
	struct B b1, b2;
	b1.a = 3; b1.b = 5; b1.c = 7;
	b2.a = 0; b2.b = 0; b2.c = 0;
	b2 = b1;
	return b2.a * 60 + b2.b * 11 + b2.c;
}
""" + MAIN, 242),
    "sa11-packed-struct-assign": ("""
struct __attribute__((packed)) P { char c; int i; long l; };
int answer(void)
{
	struct P p1, p2;
	p1.c = 1; p1.i = 1; p1.l = 94;
	p2.c = 0; p2.i = 0; p2.l = 0;
	p2 = p1;
	return (int)(p2.c * 100 + (p2.i % 10) * 10 + (p2.l % 10));
}
""" + MAIN, 114),   # sims matrix measured value (probe comment 194 stale)
    "sa12-volatile-assign": ("""
struct V { int a; int b; };
int answer(void)
{
	volatile struct V v;
	struct V s;
	v.a = 0; v.b = 0;
	s.a = 7; s.b = 9;
	v = s;
	s.a = 0; s.b = 0;
	s = v;
	return s.a * 20 + s.b;
}
""" + MAIN, 149),
    "sa13-assign-value-chain": ("""
struct S { int a; int b; };
int answer(void)
{
	struct S s, a, a2;
	s.a = 2; s.b = 3;
	a.a = 0; a.b = 0; a2.a = 0; a2.b = 0;
	a2 = a = s;
	return a2.a * 100 + a2.b * 10 + a.a;
}
""" + MAIN, 232),
    "sa14-member-of-assign-value": ("""
struct S { int a; int b; };
int answer(void)
{
	struct S s, a;
	s.a = 1; s.b = 94;
	a.a = 0; a.b = 0;
	return (a = s).a * 100 + ((a = s).b % 10);
}
""" + MAIN, 104),   # sims matrix measured value (probe comment 194 stale)
    "sa15-union-member-struct": ("""
struct W { int a; union { int i; long l; } u; };
int answer(void)
{
	struct W w1, w2;
	w1.a = 1; w1.u.l = 0; w1.u.i = 94;
	w2.a = 0; w2.u.l = 0;
	w2 = w1;
	return w2.a * 100 + (w2.u.i % 100);
}
""" + MAIN, 194),
    "sa16-cond-member-arms": ("""
struct K { int v; };
struct A { struct K uid; };
static struct K make_kuid(int ns, int v) { struct K k; k.v = v; (void)ns; return k; }
int answer(void)
{
	struct A opts; struct A cur; struct K r;
	opts.uid.v = 7; cur.uid.v = 9;
	r = 1 ? opts.uid : make_kuid(0, 3);
	return r.v;
}
""" + MAIN, 7),
    "sa17-cond-compound-literal-arms": ("""
typedef struct { unsigned long pgprot; } pgprot_t;
int answer(void)
{
	pgprot_t prot;
	pgprot_t r;
	prot.pgprot = 7;
	r = 1 ? ((pgprot_t) { ((((unsigned long)(0ULL)))) } )
	    : ((pgprot_t) { ((((unsigned long)prot.pgprot))) } );
	return (int)(r.pgprot + 7);
}
""" + MAIN, 7),
    "sa18-walk-door-verbatim": ("""
typedef unsigned int uid_t;
typedef struct { uid_t v; } kuid_t;
struct user_namespace { int nr; };
struct sock { kuid_t sk_uid; };
struct net { struct user_namespace *user_ns; };
static struct sock sk_real;
static inline kuid_t make_kuid(struct user_namespace *ns, int val)
{
	kuid_t uid;
	uid.v = ((uid_t)val);
	(void)ns;
	return uid;
}
static inline kuid_t sock_net_uid(const struct net *net, const struct sock *sk)
{
	return sk ? sk->sk_uid : make_kuid(net->user_ns, 0);
}
int answer(void)
{
	struct net n;
	sk_real.sk_uid.v = 194;
	return sock_net_uid(&n, &sk_real).v;
}
""" + MAIN, 194),
    "sa19-struct-compound-assign-neg": ("""
struct S { int a; };
int answer(void)
{
	struct S s, t;
	s.a = 1; t.a = 2;
	s += t;
	return s.a;
}
""" + MAIN, "refuse"),
    "sa20-struct-inc-neg": ("""
struct S { int a; };
int answer(void)
{
	struct S s;
	s.a = 1;
	++s;
	return s.a;
}
""" + MAIN, "refuse"),
    "sa21-same-shape-diff-tag-neg": ("""
struct A { int x; int y; };
struct B { int x; int y; };
int answer(void)
{
	struct A a; struct B b;
	a.x = 1; a.y = 2; b.x = 3; b.y = 4;
	a = b;
	return a.x;
}
""" + MAIN, "refuse"),
    "sa22-union-vs-struct-neg": ("""
struct U { int x; };
union U2 { int x; };
int answer(void)
{
	struct U s; union U2 u;
	s.x = 1; u.x = 2;
	s = u;
	return s.x;
}
""" + MAIN, "refuse"),
    "sa23-anon-identity-neg": ("""
int answer(void)
{
	struct { int x; } a;
	struct { int x; } b;
	a.x = 1; b.x = 2;
	a = b;
	return a.x;
}
""" + MAIN, "refuse"),
    "sa24-empty-struct-assign": ("""
struct E { };
int answer(void)
{
	struct E e1, e2;
	int a = 7;
	e1 = e2;
	return a;
}
""" + MAIN, 7),
    "sa25-cond-different-arm-types-neg": ("""
struct A { int x; };
struct B { int x; };
int answer(void)
{
	struct A a; struct B b; struct A r;
	a.x = 1; b.x = 2;
	r = 1 ? a : b;
	return r.x;
}
""" + MAIN, "refuse"),
    "sa26-cond-struct-ptr-arms": ("""
struct S { int a; };
int answer(void)
{
	struct S s, t, *p;
	s.a = 7; t.a = 9;
	p = 1 ? &s : &t;
	return p->a;
}
""" + MAIN, 7),
    "sa27-const-scalar-neg": ("""
int answer(void)
{
	const int c = 7;
	int x = 9;
	c = x;
	return c;
}
""" + MAIN, "refuse"),
    # TEETH rows (not sims rows): the plants must bite. A 1-byte tail
    # truncation or a union size-1 restatement is INVISIBLE unless the
    # value's SIGNIFICANT byte sits high — these two put it at bit 56
    # (struct) and bit 48 (union), measured pairs at ship bytes 8/11.
    "sa28-cond-high-byte-struct": ("""
struct L { int a; long v; };
int answer(void)
{
	struct L x, y, r;
	x.a = 2; x.v = ((long)1 << 56) | 5;
	y.a = 9; y.v = 0;
	r = 1 ? x : y;
	return (int)((r.v >> 56) & 0xff) + (int)(r.v & 0xff) + (int)r.a;
}
""" + MAIN, 8),
    "sa29-cond-high-byte-union": ("""
union U { int i; long l; };
struct W { int a; union U u; };
int answer(void)
{
	struct W w1, w2, r;
	w1.a = 1; w1.u.l = ((long)3 << 48) | 7;
	w2.a = 8; w2.u.l = 0;
	r = 1 ? w1 : w2;
	return (int)((r.u.l >> 48) & 0xff) + (int)(r.u.i & 0xff) + (int)r.a;
}
""" + MAIN, 11),
    "sa30-union-valued-cond-arm": ("""
union U { int i; long l; };
int answer(void)
{
	union U u1, u2, r;
	u1.l = ((long)3 << 48) | 7;
	u2.l = 0;
	r = 1 ? u1 : u2;
	return (int)((r.l >> 48) & 0xff) + (int)(r.i & 0xff);
}
""" + MAIN, 10),
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
def test_struct_value_law_run_pairs(name):
    src, expect = ROWS[name]
    if expect == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0, "gcc twin must refuse:\n" + rg.stderr
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, "blcc must keep the refusal:\n" \
            + rb.stderr[:300]
        return
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "blcc rc=%d:\n%s" % (rb.returncode,
                                                    rb.stderr)
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


# --------------------------------------------------- ONE HOME (text gate)
# The struct COPY byte law has exactly ONE emission home in the expression
# layer: `_copy_block` (the shipped W-H size law). The conditional arm
# CALLS it; a restated chunk/rep sequence anywhere else in expr_codegen.py
# is the second home (the sims' copy-law plant) and this gate turns it
# RED deterministically.
_REP = re.compile(r'_e\("rep movsb"\)')


def test_block_copy_law_has_one_emission_home():
    src = open(os.path.join(REPO, "blcc", "expr_codegen.py")).read()
    assert len(_REP.findall(src)) == 1, \
        "the `rep movsb` emission must live ONLY in _copy_block " \
        "(MC 12783 one-home law); a second block-copy home drifts"
    body = src.split("def _copy_block", 1)[1].split("def ", 1)[0]
    assert _REP.search(body), "the one home must CONTAIN the emission"


def test_cond_arm_rides_the_shared_law_not_a_restatement():
    """The struct arm of `_ex_cond` must DELEGATE: `_slot` for the temp,
    `_emit_addr` for the arms, `_copy_block` for the bytes — never its
    own movq-chunk/rep sequence."""
    src = open(os.path.join(REPO, "blcc", "expr_codegen.py")).read()
    arm = src.split("def _ex_cond", 1)
    assert len(arm) > 1, "_ex_cond lost"
    arm = arm[1].split("\n    def ", 1)[0]
    # EMISSION forms only — prose in comments is not a second home:
    code = "\n".join(ln for ln in arm.splitlines()
                     if not ln.strip().startswith("#"))
    assert "self._copy_block(" in code, "the struct arm must ride _copy_block"
    assert "self._emit_addr(" in code, "the arms ride the value-as-address family"
    assert "self._slot(" in code, "the temp is the shipped _slot law"
    assert '_e("rep movsb")' not in code and "_copy_pairs(" not in code \
        and "_chunks(" not in code, \
        "the struct arm restates the copy law — second home (MC 12783)"
