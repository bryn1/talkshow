# LINES reason: one wave-arm (M4 W-AF COMMIT-TF, MC 12404.2.144 /
# job 12831): the {TF} = T1+T2+E call-target arms are ONE re-booked law
# (card-12825 §3 REVERSAL); every row here is that law's measured face —
# the move-set, the named stub refusals, the blast controls, the
# interaction seam and the one-home census. Sources VERBATIM from the
# card-12825 battery (.tmp/m4-waf-sims/law/src/, "the 34 rows stand").
r"""M4 W-AF COMMIT-TF — {TF} = T1 (StmtExpr arm) + T2 (typeof(EXPR)
materialization) + E (the `&` one-pointer law). THE RE-BOOKED TRAMP2
(card-12825 §3, VERDICT: REVERSAL): the 537-era parked arms are
EXPIRED-IN-SHAPE — the parse gate they feed is only the OUTER of TWO
stacked homes; the corpus wall opens only when all three arms ride, and
it RE-WALLS one class deeper (`cannot load a 512-byte value (§4)` at
arch_x86_events_core.c.i:51607:175 — the future card, NOT taken here).
CENSUS-GRADE CLAIM (card 12825 §8.1 + this card's close): accepts 584 ->
584, lost=[] gained=[] BOTH directions, EXACTLY ONE stream's first wall
moves. SILENT-DIVERGENCE MUST BE IMPOSSIBLE: the safe direction of the
typeof arm is answering None, NEVER a guessed type (the sims' p2 plant
documents the downstream judge that enforces it — a later fix must not
quietly remove that judge).

Postures below are MEASURED at this card's hands (battery files
.tmp/m4-waf-build/out/law-tip.txt / law-tfx.txt; exit IS the answer —
both sides link with the oracle's crt, the exit codes must MATCH).
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
BLCC_DIR = os.path.join(REPO, "blcc")
TMP = "/dev/shm/m4waf1_%s_%d_%s" % (os.environ.get("M4WAF_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# name: (source VERBATIM from the sims battery, expected, class)
#   "pair"  — both sides compile rc0 and the exits MATCH `expected`
#   "refuse" — gcc rc0 exit `expected`; blcc must refuse rc2 (NAMED
#              stub limit — never silent, never a wrong exit)
#   "ae05"  — pinned SILENT-DIVERGE: gcc exit 3, blcc exit 7 (KEEP-
#              PINNED ruling, card 12825 §4; the fix is its own card)
ROWS = {
    # ---- the move-set: tip BLCC-WALL -> {TF} PAIR (exits 11/13/14/33)
    "tf-af04-stmtexpr-filescope-fnptr": ("""
static int cb(void) { return 11; }
static int (*gp)(void) = cb;
int answer(void) { return ({ gp; })(); }
""", 11, "pair"),
    "tf-af05-paren-wrapped-stmtexpr": ("""
static int cb(void) { return 13; }
static int (*gp)(void) = cb;
int answer(void) { return (({ gp; }))(); }
""", 13, "pair"),
    "tf-af06-nested-stmtexpr-chain": ("""
static int cb(void) { return 14; }
static int (*gp)(void) = cb;
int answer(void) { return ({ ({ gp; }); })(); }
""", 14, "pair"),
    "tf-af26-asm-tramp-group-verbatim": ("""
struct ops { int (*fp)(void); };
static struct ops T;
extern typeof(*T.fp) tramp;
asm(".text\\n\\t.globl tramp\\ntramp:\\n\\tmov $33, %eax\\n\\tret\\n");
int answer(void)
{
\treturn ({ static void *u = (void *)&T; (void)u; (&tramp); })();
}
""", 33, "pair"),
    # ---- asm-trampoline OPERAND rows (unchanged by the wave, must
    #      STAY pair — the address-slot legs of the same corpus site)
    "tf-af22-types-compatible-p-typeof": ("""
struct ops { int (*fp)(void); };
static struct ops T;
extern typeof(*T.fp) tramp;
int tramp(void) { return 37; }
int answer(void)
{
\tint ok = __builtin_types_compatible_p(typeof(*T.fp), typeof(tramp));
\treturn ok ? 37 : 8;
}
""", 37, "pair"),
    "tf-af23-tramp-address-in-arg": ("""
struct static_call_key { void *func; int type; };
struct ops { int (*fp)(void); };
static struct ops T;
extern typeof(*T.fp) tramp;
int tramp(void) { return 43; }
static struct static_call_key K = { ((void *)0), 1 };
static void upd(struct static_call_key *k, void *tr, void *fn)
{
\tk->func = tr; (void)fn;
}
int answer(void)
{
\treturn ({ upd(&K, (void *)&tramp, (void *)0); 43; });
}
""", 43, "pair"),
    # ---- NAMED stub refusals (the honest limits, priced NOT silent):
    #      the mirror has no group-locals home (af03), types only "var"
    #      idents so `&f` of an ordinary function answers None (af25,
    #      af02 spelled without the group), and the DIRECT call of an
    #      asm-defined typeof symbol stays walled (af27 — at {TF} the
    #      refusal MOVES HOME, it does not soften).
    "tf-af03-group-local-fnptr-refuses": ("""
static int cb(void) { return 7; }
int answer(void) { return ({ int (*q)(void) = cb; q; })(); }
""", 7, "refuse"),
    "tf-af25-amp-plain-function-refuses": ("""
int f(void) { return 3; }
int answer(void) { return (&f)(); }
""", 3, "refuse"),
    "tf-af02-typeof-amp-call-nogroup": ("""
struct ops { int (*fp)(void); };
static struct ops T;
extern typeof(*T.fp) tramp;
int tramp(void) { return 33; }
int answer(void) { return (&tramp)(); }
""", 33, "refuse"),
    "tf-af27-asm-tramp-direct-refuses": ("""
struct ops { int (*fp)(void); };
static struct ops T;
extern typeof(*T.fp) tramp;
asm(".text\\n\\t.globl tramp\\ntramp:\\n\\tmov $33, %eax\\n\\tret\\n");
int answer(void) { return tramp(); }
""", 33, "refuse"),
    # ---- {E} blast controls: the DATA-side `&function` spellings are
    #      UNMOVED by the one-pointer law (card 12825 §3: call-target
    #      surface only — af31–af34 were PAIR at tip and stay PAIR).
    "tf-af31-global-init-amp-fn": ("""
int f(void) { return 4; }
static int (*p)(void) = &f;
int answer(void) { return p() + 1; }
""", 5, "pair"),
    "tf-af32-auto-init-amp-fn": ("""
int f(void) { return 4; }
int answer(void) { int (*p)(void) = &f; return p() + 1; }
""", 5, "pair"),
    "tf-af33-assign-amp-fn": ("""
int f(void) { return 4; }
static int (*p)(void);
int answer(void) { p = &f; return p() + 1; }
""", 5, "pair"),
    "tf-af34-global-init-no-amp": ("""
int f(void) { return 4; }
static int (*p)(void) = f;
int answer(void) { return p() + 1; }
""", 5, "pair"),
    # ---- the ae05 family, pinned AS-IS (KEEP-PINNED ruling — 0 sites
    #      in 73/73 sampled accepts; the data.py:422 fix is its OWN
    #      future card; this row is the exit-encoded false-green, held
    #      in the open, NEVER silently).
    "tf-af30-ae05-union-last-wins-pinned": ("""
union U { int a; long b; };
union U u = { 3, 7 };
int answer(void) { return (int)u.b; }
""", 3, "ae05"),
}


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe]
        env = None
    else:
        o = os.path.join(TMP, tag + ".blcc.o")
        exe = os.path.join(TMP, tag + ".blcc")
        b = subprocess.run([os.environ.get("PYTHON", "python3"), "-m",
                            "blcc", "-c", c, "-o", o], capture_output=True,
                           text=True, cwd=REPO,
                           env=dict(os.environ, PYTHONPATH=REPO))
        if b.returncode != 0:
            return b, None
        cmd = ["gcc", "-no-pie", "-o", exe, o]
        env = None
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return r, exe


def _asm(src, tag):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    s = os.path.join(TMP, tag + ".s")
    r = subprocess.run(["python3", "-m", "blcc", "--emit-asm", c, "-o", s],
                       capture_output=True, text=True, cwd=REPO,
                       env=dict(os.environ, PYTHONPATH=REPO))
    assert r.returncode == 0, r.stderr[:300]
    return open(s + ".s").read()


@pytest.fixture(autouse=True, scope="module")
def _tmp():
    os.makedirs(TMP, exist_ok=True)
    yield


@pytest.mark.parametrize("name", sorted(ROWS))
def test_tf_battery(name):
    src, expect, cls = ROWS[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "%s: gcc answered %d, expected %d" % (
        name, gx, expect)
    rb, bexe = _build(src, name, "blcc")
    if cls == "refuse":
        assert rb.returncode == 2, \
            "%s: NAMED stub refusal went soft (rc=%d):\n%s" % (
                name, rb.returncode, (rb.stdout + rb.stderr)[:300])
        return
    assert rb.returncode == 0, "%s: blcc rc=%d:\n%s" % (
        name, rb.returncode, (rb.stdout + rb.stderr)[:300])
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    if cls == "ae05":
        assert bx != gx, \
            "the af30/ae05 posture CHANGED (%d==%d) — the LAST-WINS arm " \
            "moved without its own card: reopen the KEEP-PINNED ruling " \
            "(card 12825 §4), this pin holds the CURRENT posture" % (
                bx, gx)
        assert bx == 7, "blcc-side drifted from the pinned 7: got %d" % bx
        return
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


# ---- interaction: the typeof-call INSIDE a splice, POST-RENAME ---------

SPLICE = """
struct ops { int (*fp)(void); };
static struct ops T;
extern typeof(*T.fp) tramp2;
asm(".text\\n\\t.globl tramp2\\ntramp2:\\n\\tmov $9, %eax\\n\\tret\\n");
static inline int pick(int q)
{
\t__asm__ volatile("" : "+r"(q));
\treturn ({ (&tramp2); })() + q;
}
int answer(void){ return pick(1) + pick(2); }
"""


def test_tf_splice_typeof_postrename_pair():
    # RED at tip (the un-typeable group callee answers the scoped §8
    # refusal), PAIR at {TF}: BOTH renamed clones answer the SAME value
    # (9+1 + 9+2 = 21) — the sims' wd301 precedent reading for the
    # W-P inline door.
    src = SPLICE
    rg, gexe = _build(src, "waf1spg", "gcc")
    assert rg.returncode == 0, rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    assert gx == 21, "gcc answered %d, expected 21" % gx
    rb, bexe = _build(src, "waf1spb", "blcc")
    assert rb.returncode == 0, rb.stderr[:300]
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert bx == gx, "clone divergence blcc %d vs gcc %d" % (bx, gx)


def test_tf_splice_pin_no_callee_copy():
    # THE SPINE: the value alone would pass if the inline door fell back
    # to the CALL law. No `pick:` leaf may survive in the emitted asm
    # (W-P splice law rides the clone path unchanged).
    asm = _asm(SPLICE, "waf1spin")
    assert "\npick:" not in asm and not asm.startswith("pick:"), \
        "the splice fell back to the CALL law: a `pick:` leaf survived"


# ---- one-home census: the §8 sentence's homes, tagged set exact --------

_SENT = re.compile(r"is not a 'function' or a 'function")
_TAG = "pointer' (§8 — gcc rc1 twin)"
_BLCC_ONLY = "§8 — blcc-only"


def test_tf_eight_homes_are_six_and_the_twin_tag_rides_two():
    # RENAMED at M4 W-AG COMMIT-0 (was test_tf_eight_homes_are_five_…;
    # the leg count is unchanged, the NAME was the claim):
    # W-AF measured the §8 sentence at FIVE homes: expr_parser.py 3
    # (blcc-only un-typeable arm + twin + named-ident twin),
    # expr_codegen.py 1, types.py 1 (the sims-named _ind_call_ty twin).
    # The oracle tag ("gcc rc1 twin") rode ONLY the two MEASURED typed
    # arms in expr_parser.py — the W-AF scoping (gate F-2).
    # M4 W-AG COMMIT-0 (gate F-2-SCOPE, card 12832): the NAME arm gained
    # its OWN scoped blcc-only face (six homes now: 4 parser + 1 codegen
    # + 1 types) — the tag may only reach it through `_twin_measured`,
    # the MEASURED scalar/struct/union/array class. A NEW home, or a NEW
    # tagged site, still goes this RED: adding a refusal home without a
    # measured twin is exactly the false-oracle F-2 named. The RUNTIME
    # catcher for tag-smuggling (postures, not strings) is
    # tests/test_core_m4wag0.py — the gate named this census's limit:
    # "the catcher pins STRINGS, not postures".
    # (Counts run over quotes/whitespace-normalized text: the shipped
    # sentences are multi-literal concatenations, a raw substring scan
    # splits them at every `" +` seam.)
    def norm(t):
        return re.sub(r"[\"'\s]+", "", t)
    homes = 0
    tagged = []
    scoped = []
    for f in sorted(os.listdir(BLCC_DIR)):
        if not f.endswith(".py"):
            continue
        src = norm(open(os.path.join(BLCC_DIR, f)).read())
        n = src.count(norm("is not a 'function' or a 'function"))
        homes += n
        if n:
            tagged.append((f, src.count(norm(_TAG))))
            scoped.append((f, src.count(norm(_BLCC_ONLY))))
    assert homes == 6, "the §8 sentence moved homes: %d emission sites " \
        "(expected 6: 4 parser + 1 codegen + 1 types — W-AG COMMIT-0 " \
        "gave the name arm its scoped face)" % homes
    assert tagged == [("expr_codegen.py", 0), ("expr_parser.py", 2),
                      ("types.py", 0)], \
        "the oracle tag drifted off its measured arms: %r" % tagged
    assert dict(scoped) == {"expr_codegen.py": 1, "expr_parser.py": 2,
                            "types.py": 1}, \
        "the scoped blcc-only sentence must ride every unmeasured " \
        "arm: %r" % scoped


# ---- kernel tier: the surviving §8 stream never wears the tag ----------

from test_core_m4w1 import STREAMS                       # noqa: E402
from test_core_m4w25b import _clean_i                    # noqa: E402


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_tf_kernel_events_core_wall_moved_off_eight(tmp_path):
    # THE census claim pinned: this stream's first wall moved to the
    # §4 big-value-load sentence (the future card's wall — its sentence
    # appears HERE for the first time; the 512-byte-load law itself is
    # FORBIDDEN territory for this wave and must NOT be closed).
    clean = _clean_i(os.path.join(STREAMS, "arch_x86_events_core.c.i"),
                     tmp_path, "waf1ec")
    r = subprocess.run(["python3", "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "waf1ec.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO))
    first = next(ln for ln in (r.stdout + r.stderr).splitlines()
                 if ln.strip())
    assert "cannot load a 512-byte value (§4)" in first, \
        "events/core first wall must be the newly-visible §4 512-byte " \
        "load sentence, got:\n" + first


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_tf_kernel_events_core_keeps_wall_never_lands(tmp_path):
    # The stream must NOT land: the §4 512-byte-load wall (its own
    # future card) stands. A silent rc0 here means the FORBIDDEN family
    # moved — NAME IT, do not ship it.
    clean = _clean_i(os.path.join(STREAMS, "arch_x86_events_core.c.i"),
                     tmp_path, "waf1nl")
    r = subprocess.run(["python3", "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "waf1nl.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO))
    assert r.returncode != 0, \
        "events/core LANDED — the §4 512-byte-load law (future card) " \
        "moved inside W-AF: STOP, this wave's DoD is walls-moved, not " \
        "this accept"
