# LINES reason: one wave (M4 W-T COMMIT-1, compound-literal nested-brace
# normalization at the ONE `_norm_init` home, card 12404.2.99): every
# leg is an arm of the ONE normalization law table — splitting would
# separate a depth from its law.
r"""M4 W-T COMMIT-1 (MC 12736) — compound literals as expressions /
assignments: the nested-brace normalization joins the ONE `_norm_init`
home (blcc/parser.py). Two laws, one function:

(1) POSITIONAL recursion — a brace level with NO designators still
    NORMALIZES its nested aggregate members (gnu89 `spinlock_t {
    { .rlock = { .raw_lock = { }, } } }` — the positional outer hides
    a DESIGNATED inner; today the raw Desig node reaches the _expr
    emitter and LOUDs `cannot emit expression, found 'construct'` —
    the walk stopper at include/linux/xarray.h:377:79 in init/main.o,
    the 322-stream first-wall top class). THE LOUD REFUSAL THIS
    COMMIT REPLACES: exactly that 'construct' wall (and its §4 twin
    `struct initializer must be a brace list of member constants`
    at file scope).
(2) THE CL UNWRAP MOVES INSIDE `_norm_init` — the decl-position law
    "an aggregate initialized from a compound literal is byte-identical
    to writing the brace list" (parser.py §1 row 11) now applies at
    EVERY depth. At TIP this SILENTLY MIS-COMPUTES
    (`struct N n = (struct N){ (struct M){4} };` answers 82 vs gcc 6 —
    the gate's t06 miscompute, now measured at tip bytes own hands).
    This law REPLACES the silent member-CL address-store.

gcc 11.4 -Os law table: .tmp/m4-wt/out/laws-cl-simcl.txt (19 rows, 15
RUN-PAIRS at the sim bytes; k06 struct-ternary is a PRE-EXISTING §5
struct-VALUE diverge — `plain_cond_struct` walls at tip too, NAMED);
file-scope posture pins g_scalar (pair-LOUD) + g_cl_nested (named
quieter row, tip-precedent, unmoved).
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
PINNED = "/home/claudecode/Blaha/.tmp/m4-plan/streams"
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _pair(tag, src):
    c = "/dev/shm/wt1_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/wt1_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "law row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wt1_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wt1_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must COMPILE: " % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wt1_%s.b" % tag],
                          capture_output=True).returncode == 0, "link"
    rex = subprocess.run(["/dev/shm/wt1_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert rex == gex, "%s: value pair gcc=%d blcc=%d" % (tag, gex, rex)


XA = ("struct arch_spinlock { }; "
      "struct raw_spinlock { struct arch_spinlock raw_lock; }; "
      "typedef struct { struct { struct raw_spinlock rlock; }; } spinlock_t; "
      "struct xarray { spinlock_t xa_lock; int march; }; ")


def test_wt1_xarray_verbatim_assign():
    # THE walk stopper, VERBATIM init/main.o shape (xarray.h:377:79):
    # `*(&xa->xa_lock) = (spinlock_t){ { .rlock = { .raw_lock = { }, } } }`.
    # RED-at-tip: `cannot emit expression, found 'construct'`.
    _pair("xarray", XA + "void f(struct xarray *xa){ *(&xa->xa_lock) ="
          " (spinlock_t){ { .rlock = { .raw_lock = { }, } } }; }"
          " int main(void){ struct xarray x; x.march=2; f(&x);"
          " return x.march; }")           # 2


def test_wt1_positional_outer_designated_inner():
    # THE law: positional OUTER brace, DESIGNATED inner (k08) — today
    # the inner Desig reaches the _expr emitter (construct wall).
    _pair("k08", "struct R{int q;};struct T{struct R r;int t;};"
          "int main(void){struct T v={ { .q=3 }, 1 };return v.r.q+v.t+1;}")


def test_wt1_nested_cl_in_cl_value():
    # THE gate's t06 class AT TIP BYTES: compiles SILENTLY WRONG at tip
    # (gcc 6, blcc 82). The unwrap-at-every-depth law fixes the value.
    _pair("k07", "struct M{int x;};struct N{struct M m;};"
          "int main(){struct N n=(struct N){ (struct M){4} };"
          "return n.m.x+2;}")             # 6


def test_wt1_global_nested_desig_fold():
    # file-scope fold of the SAME shape (RED-at-tip: `struct
    # initializer must be a brace list of member constants (§4)`).
    _pair("gnest", "struct R{int q;};struct T{struct R r;int t;};"
          "struct T v={ { .q=3 }, 1 };int main(void){return v.r.q+v.t+1;}")


def test_wt1_lifetime_two_cl_distinct_slots():
    # LIFETIME: two CL objects in ONE expression are DISTINCT (an alias
    # answers 50, distinct 41 — the gate's mis-lifetime guard row k02).
    _pair("k02", "int main(void){int*a=(int[]){1},*b=(int[]){2};"
          "*a+=9;*b+=*a;return *a+*b+19;}")


def test_wt1_lifetime_loop_fresh_per_iteration():
    # LIFETIME: a fresh CL object each iteration (fresh 9, stale 12).
    _pair("k03b", "int main(){int s=0,i;for(i=0;i<3;i++){int*p=(int[]){0};"
          "s+=*p;*p=1;}return s+9;}")


def test_wt1_lifetime_arg_temp_death():
    # LIFETIME: CL as function ARG must not clobber a live CL object.
    _pair("k04", "struct V{int v;};int g(struct V x){return x.v;}\n"
          "int main(void){struct V k=(struct V){.v=40};"
          "return g((struct V){.v=2})+k.v-36;}")


def test_wt1_cl_lvalue_write_read():
    _pair("k12", "int main(void){int*x=(int[]){1,2,3};x[1]=9;"
          "return x[1]+x[2]+5;}")         # 17


def test_wt1_cl_in_logical_chain():
    _pair("k05", "int main(void){int r=0;"
          " r = ((int[]){1}[0] || ((int[]){9}[0]=5))"
          " && ((int[]){2}[0]==2); return r+((int[]){3}[0])+2;}")


def test_wt1_chained_designator():
    _pair("k15", "struct In{int z;};struct Out{struct In i;};"
          "int main(void){return ((struct Out){ .i.z=11 }).i.z+51;}")


def test_wt1_posture_pins():
    # named posture rows (NOT regressions): g_scalar file-scope CL twin
    # pair MOVED at M4 W-AC (MC 12404.2.133, commit c5d365a): the shipped
    # brace-scalar collapse law reaches the file-scope `(int){5}` scalar
    # too - re-pinned AS MEASURED at my hands: blcc rc0 exit 5, gcc
    # -no-pie REC rc0 exit 5 (was the pre-existing LOUDER-than-gcc row
    # gcc rc0 blcc rc2; the law made blcc AGREE with gcc, value-correct).
    # g_cl_nested quieter-than-gcc row (tip-precedent rc0-vs-rc1, the
    # file-scope CL fold already shipped it) — PINNED as measured.
    c = "/dev/shm/wt1_gp.c"
    open(c, "w").write("int x = (int){5};\nint main(void){return x;}")
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 0, "g_scalar W-AC-moved posture drifted back: " \
        + b.stderr
    blcc([c, "-o", "/dev/shm/wt1_gp.bin"])
    assert subprocess.run(["/dev/shm/wt1_gp.bin"], capture_output=True,
                          timeout=60).returncode == 5, \
        "g_scalar value moved (measured gcc rc0 exit 5)"
    open(c, "w").write("struct M{int x;};struct N{struct M m;};"
                       "struct N g=(struct N){ (struct M){4} };"
                       "int main(void){return g.m.x;}")
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 0, "g_cl_nested tip-precedent posture moved"


def test_wt1_stream_construct_wall_moved():
    """VERBATIM stream pin: init_main.c.i (the walk's init/main.o TU).
    RED-FIRST at tip: the first wall is `sema: cannot emit expression,
    found 'construct'` — THE xarray.h:377:79 stopper. COMMIT-1 eats it;
    the queue law says the wall LANDS BEHIND (named in the verdict)."""
    if not os.path.isdir(PINNED):
        pytest.skip("pinned corpus not linked (builder posture)")
    import re as _re
    lm = _re.compile(r"^#\s+\d+\s+\"")
    clean = "/dev/shm/wt1_init_main_clean.c"
    with open(PINNED + "/init_main.c.i", errors="replace") as fh, \
            open(clean, "w") as oh:
        for ln in fh:
            if not lm.match(ln):
                oh.write(ln)
    r = blcc(["-c", clean, "-o", "/dev/shm/wt1_init_main.o"])
    first = next(ln for ln in r.stderr.splitlines() if ln.strip()) \
        if r.stderr else ""
    if r.returncode == 0:
        return                          # full-TU accept (close posture)
    assert ("cannot emit expression" not in first
            or "found 'construct'" not in first), \
        "the 'construct' wall must be EATEN by COMMIT-1 (RED-FIRST " \
        "pin): " + first[:200]
