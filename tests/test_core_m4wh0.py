"""M4 W-H COMMIT-0 (MC 12645, card 12404.2.73) — PAIRED WAVE PINS.

AMENDMENT-7 pairing law: the jiffies.h:427 `__UNIQUE_ID` class (406
first-blockers; gate ROOT CAUSE = the absent GNU `__auto_type` DECLARATION
SPECIFIER, NOT the ##-paste — .tmp/evidence/m4-wg-gate-verdict.md LEG 7)
and the STRUCT-ASSIGNMENT family (path.h 76 + capability.h 12 first-
blockers, and the SECOND wall 392/406 of the __auto_type crowd lands on)
ship PAIRED — desugaring alone yields 0 accepts (measured), so the legs
below pin BOTH walls RED-at-tip and both commits flip them.

COMMIT-0 ships the walls as they MEASURE at tip (refusal pins, green at
tip like the W-F f2 pin): COMMIT-1 (auto_type) and COMMIT-2 (block copy)
FLIP them to acceptance — a flip, never a deletion. Controls pin what
must not move.

MEASURED LAW TABLES (gcc 11.4 -std=gnu89/-Os probes, .tmp/m4-wh/probes/):
  __auto_type LAW: type = the INITIALIZER'S type after value conversion —
    arrays DECAY to pointers (`ca` -> int*, sizeof 8), functions decay to
    fn-pointers, TOP-LEVEL qualifiers DROP (`__auto_type v = ci; v = 7;`
    rc 0 while `__typeof__(ci) v; v = 7;` rc 1), POINTED-TO qualifiers
    KEEP (`__auto_type v = pci; *v = 7;` rc 1); init REQUIRED (rc 1
    without), exactly ONE plain-identifier declarator (`*v =` / `a=1,b=2`
    rc 1), `void` init rc 1 (`variable or field declared void`), works at
    file scope, `static`, and in `({...})`. The bare word `auto_type`
    (no underscores) is NOT the keyword (rc 1 — did-you-mean twin).
  STRUCT-ASSIGNMENT LAW: same-tag aggregate assignment = BLOCK COPY of
    sizeof bytes; at -Os the emission is ALWAYS INLINE moves (movq <=8,
    9..16 chunked, >=15 rep movsb) and NEVER a libcall (measured to 100
    bytes). Different tags rc 1 `incompatible types when assigning`;
    struct->scalar and scalar->struct rc 1; ARRAY = array rc 1
    `assignment to expression with array type` (tip FALSE-ACCEPT — the
    fixg2b sibling audit named the family, the `=` arm never got it).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
FIXTURE = os.path.join(HERE, "fixtures", "m4wh", "jiffies427_verbatim.i")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _pair(tmp_path, tag, src, e):
    """Run-pair idiom: gcc AND blcc compile+run the same program; BOTH
    exit codes equal the PRE-COMPUTED Python witness."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    g = subprocess.run(["gcc", "-std=gnu89", str(s), "-o",
                        str(tmp_path / (tag + ".g"))],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc: " + g.stderr
    b = blcc([str(s), "-o", str(tmp_path / (tag + ".b"))])
    assert b.returncode == 0, "blcc: " + b.stderr
    gv = subprocess.run([str(tmp_path / (tag + ".g"))],
                        capture_output=True).returncode
    bv = subprocess.run([str(tmp_path / (tag + ".b"))],
                        capture_output=True).returncode
    assert gv == e, "gcc gave {} expected {}".format(gv, e)
    assert bv == e, "blcc gave {} expected {}".format(bv, e)


# ------------------------------------------------- wall 1: __auto_type

# The verbatim jiffies.h:427 expansion EXACTLY as the pinned corpus
# carries it (init_main.c.i line 14433, 808 bytes, fixture
# fixtures/m4wh/jiffies427_verbatim.i; gcc -std=gnu89 RC0 on the same
# file — measured this session). 406/706 streams' first-blocker.
def test_wh0_jiffies427_verbatim_accepted(tmp_path):
    # FLIPPED by COMMIT-1 (was test_wh0_jiffies427_verbatim_wall, the
    # RED-at-tip refusal pin `parse: expected ';', found
    # '__UNIQUE_ID_x_56'`). The whole 406-stream class in one file now
    # COMPILES: the two auto locals take (0L)/(delta)'s long, the
    # compiletime-assert and the `>` ternary ride existing legs.
    r = blcc(["-c", FIXTURE, "-o", str(tmp_path / "jf.o")])
    assert r.returncode == 0, r.stderr
    assert r.stderr.strip() == "", r.stderr


# The v5.10 macro chain VERBATIM (compiler.h ___PASTE/__PASTE/
# __UNIQUE_ID(__LINE__) + jiffies.h __cmp/__careful_cmp_once/max —
# .tmp/m4-wg-gate/triage/uniq.c). At tip the parse wall fires; after
# COMMIT-1 the SAME file must build AND run-pair with gcc (max law).
UNIQ_CHAIN = r"""
#define ___PASTE(a,b) a##b
#define __PASTE(a,b) ___PASTE(a,b)
#define __UNIQUE_ID(prefix) __PASTE(__PASTE(__UNIQUE_ID_, prefix), __LINE__)
#define __cmp_op_max >
#define __cmp(op, x, y) ((x) __cmp_op_##op (y) ? (x) : (y))
#define __careful_cmp_once(op, x, y, ux, uy) ({		\
	__auto_type ux = (x); __auto_type uy = (y);	\
	__cmp(op, ux, uy); })
#define __careful_cmp(op, x, y) \
	__careful_cmp_once(op, x, y, __UNIQUE_ID(x_), __UNIQUE_ID(y_))
#define max(x, y)	__careful_cmp(max, x, y)
long f(long delta) { return max(0L, delta); }
int main(void) { return (int)(f(-5) * 2 + f(7)); }   /* 0*2+7 = 7 */
"""


def test_wh0_uniq_macro_chain_run_pair(tmp_path):
    # FLIPPED by COMMIT-1 (was test_wh0_uniq_macro_chain_wall, the
    # RED-at-tip refusal pin): the VERBATIM v5.10 chain — paste +
    # __LINE__ unique names + __auto_type locals — now BUILDS and RUNS
    # the max() law pair-clean with gcc (f(-5)=0, f(7)=7 → 0*2+7 = 7).
    _pair(tmp_path, "wh0_chain", UNIQ_CHAIN, 7)


# ---------------------------------------- wall 2: struct-assignment

STRUCTS = ("struct S { int a, b; };\n"
           "struct S gs;\n")

def test_wh0_struct_assign_copy(tmp_path):
    # FLIPPED by COMMIT-2 (was test_wh0_struct_assign_wall, the
    # RED-at-tip refusal pin): same-tag whole-struct assignment is the
    # MEASURED BLOCK COPY (the §5 refusal was the wall the 88 header
    # first-blockers AND 392/406 of the auto_type crowd hit second —
    # both families now move; law table tests/test_core_m4wh2.py).
    r = _compile(tmp_path, "wh0_asg", STRUCTS +
                 "int f(void){ struct S w; w = gs; return w.b; }\n")
    assert r.returncode == 0, r.stderr
    assert r.stderr.strip() == "", r.stderr


def test_wh0_path_h_class(tmp_path):
    # FLIPPED by COMMIT-2 (was test_wh0_path_h_class_wall, the
    # RED-at-tip pin). The VERBATIM path.h:24 class (76 first-
    # blockers), stream text:
    #     path_put(path);  *path = (struct path) { };
    # — compound-literal RHS, empty braces (the RB_ROOT_CACHED witness
    # shape test_core_m2_clit flipped with this commit) — COMPILES.
    r = _compile(tmp_path, "wh0_path",
                 "struct vfsmount; struct dentry;\n"
                 "struct path { struct vfsmount *mnt; struct dentry *dentry; };\n"
                 "void path_put(struct path *path);\n"
                 "void path_put_init(struct path *path)\n"
                 "{\n"
                 " path_put(path);\n"
                 " *path = (struct path) { };\n"
                 "}\n")
    assert r.returncode == 0, r.stderr
    assert r.stderr.strip() == "", r.stderr


# ------------------------------------------------------ controls

def test_wh0_control_scalar_assign(tmp_path):
    _pair(tmp_path, "wh0_ctl1",
          "long g(void){ long v = 40; v += 2; return v; }\n"
          "int main(void){ return (int)g(); }", 42)


def test_wh0_control_member_by_member(tmp_path):
    # What the §5 sentence told you to write stays CORRECT both states:
    _pair(tmp_path, "wh0_ctl2", STRUCTS +
          "int f(void){ struct S w; gs.a = 11; gs.b = 22;"
          " w.a = gs.a; w.b = gs.b; return w.a + w.b; }\n"
          "int main(void){ return (int)(f() % 256); }", (11 + 22) % 256)


def test_wh0_control_typeof_rides(tmp_path):
    # __typeof__ is NOT this wave's mechanism and must not move:
    r = _compile(tmp_path, "wh0_ctl3",
                 "long g(void){ __typeof__(5L) v = 5L; return (long)sizeof(v); }\n")
    assert r.returncode == 0, r.stderr
