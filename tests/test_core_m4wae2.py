# LINES reason: one wave's law battery (M4 W-AE COMMIT-1 MC 12819): the
# 16-row exit-encoded table IS the measured law and stays in one file.
r"""M4 W-AE battery (MC 12404.2.141 / job 12819): the sims law battery
(card 12816 §2) revived VERBATIM at my hands, exit-encoded: both sides
compile with the REC flags, link against law_main.c, and the RUN exit IS
the answer. Postures at base bytes (scored, RED-FIRST): 13 run-PAIR rows
unchanged by this wave; ae11 is THE divergence face (the init_task wall
distilled to 6 lines — BLCC-WALL at base, run-PAIR 171 under the width-0
slot law); ae07 is the excess-elements posture row (gcc WARN+accept exit
1, blcc LOUD rc2 — the W-AD excess-init stance STANDS by design, brief:
"ae07 excess-LOUD stance stands"); ae05 is the NAMED divergence row:
multi-designator union init — gcc law = exactly ONE named member (last
wins, C 6.7.9§17), blcc MERGES both slots (gcc 36 vs blcc 40). This row
pins the CURRENT merge behavior and must flip when the future ae05 card
fixes it — it is NOT fixed here.
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wae2_%s_%d_%s" % (os.environ.get("M4WAE_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# sims law/src rows VERBATIM (card 12816), answer == the run exit.
ROWS = {
    "ae01-cross-static-unit-cross": ("""
/* bitfield crossing a storage-unit boundary in STATIC-init context */
static struct S { unsigned a:28; unsigned b:8; } s = { .a = (1u<<28)-1, .b = 5 };
int answer(void){ return ((unsigned char*)&s)[4]*2 + (((unsigned char*)&s)[0]==0xFF); }
""", 11),
    "ae02-designated-resume-slot": ("""
/* designated resume position at the post-bitfield field: WHICH slot? */
static union C { struct S { unsigned a:1; unsigned b:1; int c; } s; unsigned w; }
  cv = { .s = { .a = 1, 7 } };
int answer(void){ return (cv.w&1) + 2*((cv.w>>1)&1) + 4*(cv.s.c==0); }
""", 7),
    "ae03-anon-pad-position": ("""
/* the fork shape: unnamed width-0 pad between two bitfields; POSITIONAL
   items consume it (gcc law) or skip it (blcc data-side count)? */
static union C { struct S { unsigned a:1; unsigned :0; unsigned b:1; } s;
                 unsigned w[2]; } cv = { .s = { 1, 2 } };
int answer(void){ return (cv.w[0]&1) + 8*(cv.w[1]&1); }
""", 1),
    "ae04-union-task-bias": ("""
/* union-wrapping task (task_union/thread_union stack bias, REAL shape mini) */
struct T { int x; unsigned f:1; long y; };
union U { struct T t; unsigned long stack[16]; } u = { .t = { .x = 3, .f = 1, .y = 5 } };
int answer(void){ return (sizeof(u)==128) + u.t.x*2 + (u.t.y==5)*8; }
""", 15),
    "ae06-zerofill-spans-unit-pad": ("""
/* zero-fill span vs slots: gap must cover the bitfield's UNIT + pad */
union V { struct S { char c; unsigned bf:3; long l; } s; char b[16]; };
union V v = { .s = { .l = 5 } };
int answer(void){ return v.s.c + v.s.l + 4*((unsigned char*)&v)[1]
              + 8*((unsigned char*)&v)[2] + 16*((unsigned char*)&v)[3]; }
""", 5),
    "ae08-array-of-bitfield-structs": ("""
/* array-of-struct-with-bitfields static init, designated element */
struct S { unsigned a:1; int v; } arr[2] = { [1] = { .a = 1, .v = 7 } };
int answer(void){ return ((((unsigned*)&arr[1])[0])&1) + 2*arr[1].v
              + 4*arr[0].v; }
""", 15),
    "ae09-init-task-chain-mini": ("""
/* the REAL init_task designated chain, VERBATIM rows (shape-preserved):
   .thread = { }, .tasks = { &(init_task.tasks), &(init_task.tasks) },
   .prio = (100 + (19 - -20 + 1)) - 20, .comm = "swapper" */
struct th { unsigned long sp; };
struct lst { struct lst *next, *prev; };
struct K { struct th thread; struct lst tasks; int prio; char comm[16];
           unsigned bf:1; } k = {
 .thread = { .sp = (unsigned long)&k.comm[0], },
 .tasks = { &(k.tasks), &(k.tasks) },
 .prio = (100 + (19 - -20 + 1)) - 20,
 .comm = "swapper",
};
int answer(void){ return (k.prio==120) + 2*(k.tasks.next==&k.tasks)
              + 4*(k.comm[0]=='s') + 8*(k.thread.sp==(unsigned long)k.comm); }
""", 15),
    "ae10-signed-bitfield-negative": ("""
/* signed bitfield negative static init: stored bits, overlay read */
union C { struct S { int x:3; } s; int w; } cv = { .s = { .x = -1 } };
int answer(void){ return (cv.w==7); }
""", 1),
    "ae11-count-wall-fork": ("""
/* THE divergence face: struct whose :0 pad forks the slot count;
   designated chain fills both sides of the fork (overlay readout) */
union C { struct T { unsigned f; unsigned a:1; unsigned :0; unsigned b:1;
                    int tail; } t; unsigned w[3]; } cv =
  { .t = { .f = 1, .a = 1, .b = 1, .tail = 42 } };
int answer(void){ return cv.t.f + 2*(cv.w[1]&1) + 4*cv.t.tail; }
""", 171),
    "ae12-positional-into-bits": ("""
/* all-positional run into bitfield slots */
union C { struct S { unsigned a:1, b:1; int c; } s; unsigned w; }
  cv = { .s = { 1, 1, 9 } };
int answer(void){ return (cv.w&1) + 2*((cv.w>>1)&1) + 4*(cv.s.c==9); }
""", 7),
    "ae13-union-bitfield-bias": ("""
/* union with a bitfield member: bias + partial-word set */
union U { unsigned a:12; int v; } u = { .a = 0xfff };
int answer(void){ return (u.v==0xfff) + 2*(u.v!=0xfff); }
""", 1),
    "ae14-wide-cross-FIXG1": ("""
/* {u32 a:31; u32 b:3}: b crosses to the next unit (W-F FIX-G1 twin) */
union C { struct S { unsigned a:31; unsigned b:3; } s; unsigned char b[8]; }
  cv = { .s = { .a = 1, .b = 7 } };
int answer(void){ return cv.b[4] + 16*(cv.b[0]&1) + 1; }
""", 24),
    "ae15-missing-tail-zerofill": ("""
/* missing-init tail: zeros must span the bitfield byte too */
union C { struct S { int a; unsigned f:2; int b; } s; unsigned w[3]; }
  cv = { .s = { .a = 3 } };
int answer(void){ return cv.s.a + 4*((cv.w[1]>>0)&3 == 0) + 8*(cv.s.b==0); }
""", 11),
    "ae16-resume-after-wide": ("""
/* designated resume at the field AFTER a 31-bit field: which slot? */
union C { struct S { unsigned a:31; unsigned b:2; int c; } s; unsigned w[3]; }
  cv = { .s = { .a = 1, 5 } };
int answer(void){ return ((cv.w[1]>>0)&3) + 4*(cv.s.c==0); }
""", 5),
}

# Posture row (design stance, brief: "ae07 excess-LOUD stance stands"):
# gcc WARNS and ACCEPTS (exit 1); blcc LOUDs the §4 sentence rc2.
WALL_POSTURE = {
    "ae07-resume-after-pad": """
/* designated RESUME past a width-0 pad: excess element position? */
union C { struct S { unsigned a:1; unsigned :0; unsigned b:1; } s;
          unsigned w[2]; } cv = { .s = { .b = 1, 5 } };
int answer(void){ return (cv.w[1]&1) + 2*(cv.w[0]&1); }
""",
}

# NAMED divergence row (card 12816 §2 ae05): multi-designator union init.
# gcc law = exactly ONE named member initialized (last wins); blcc MERGES
# both slots. Pinned AS-IS: this row pins the CURRENT behavior and goes
# RED when the future union-init card fixes it. NOT fixed in 12819.
NAMED_DIVERGENCE = {
    "ae05-nested-anon-slot-math": ("""
/* nested anon struct+union slot math (promotion descent) */
struct O { union { struct { int x; int y; }; int z; }; int w; } o =
  { .y = 2, .z = 4, .w = 8 };
int answer(void){ return o.x + 2*o.y + 4*o.w; }
""", 36, 40),          # (gcc exit, blcc exit) — the measured merge bias
}


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    m = os.path.join(TMP, tag + "_main.c")
    with open(m, "w") as fh:
        fh.write(MAIN)
    o = os.path.join(TMP, tag + (".gcc.o" if kind == "gcc" else ".blcc.o"))
    b = os.path.join(TMP, tag + (".gcc" if kind == "gcc" else ".blcc"))
    if kind == "gcc":
        cmd = ["gcc", "-no-pie"] + GCC_REC
        env = None
    else:
        cmd = ["python3", "-m", "blcc"]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd + ["-c", c, "-o", o], capture_output=True,
                       text=True, cwd=REPO, env=env, timeout=600)
    if r.returncode != 0:
        return r, None
    lm = os.path.join(TMP, tag + "_lawmain.o")
    r2 = subprocess.run(["gcc", "-no-pie"] + GCC_REC + ["-c", m, "-o", lm],
                        capture_output=True, text=True, timeout=600)
    assert r2.returncode == 0, r2.stderr
    rl = subprocess.run(["gcc", "-no-pie", o, lm, "-o", b],
                        capture_output=True, text=True, timeout=600)
    assert rl.returncode == 0, rl.stderr
    return r, b


@pytest.fixture(autouse=True, scope="module")
def _tmp():
    os.makedirs(TMP, exist_ok=True)
    yield


@pytest.mark.parametrize("name", sorted(ROWS))
def test_law_rows_run_pair(name):
    src, expect = ROWS[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, \
        "%s: blcc rc=%d:\n%s" % (name, rb.returncode, rb.stderr[:300])
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


@pytest.mark.parametrize("name", sorted(WALL_POSTURE))
def test_ae07_excess_loud_stance_stands(name):
    src = WALL_POSTURE[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc must WARN-and-accept:\n" + rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    assert gx == 1, "gcc exit twin moved: %d" % gx
    rb, _ = _build(src, name, "blcc")
    assert rb.returncode == 2, \
        "ae07 excess-LOUD stance FELL (blcc rc=%d) — the W-AD excess-init " \
        "family posture is unchanged by the slot-model law " \
        "(card 12816 §2 ae07)" % rb.returncode


@pytest.mark.parametrize("name", sorted(NAMED_DIVERGENCE))
def test_ae05_named_divergence_pinned(name):
    src, gexp, bexp = NAMED_DIVERGENCE[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, rb.stderr[:300]
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert (gx, bx) == (gexp, bexp), \
        "ae05 moved from the PINNED divergence (gcc %d expected %d, blcc %d " \
        "expected %d): the union LAST-WINS init law changed — that is the " \
        "future card's fix; update this pin there, never silently " \
        "(card 12816 §2)" % (gx, gexp, bx, bexp)
