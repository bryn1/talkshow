# M4 W-AS COMMIT-2 battery — INTERACTIONS + the SHUT-DOOR catchers
# (MC 12404.2.168 / card 12901; design truth .tmp/evidence/m4-war-sims.md
# §4-§5). COMMIT-1 shipped {R} (C 6.2.1p6 define-before-init, one hunk at the
# define() home); this file pins WHAT {R} TOUCHES BESIDE the frontier:
#
# (1) self-decl × SPLICE-POST-RENAME (the W-P/W-R inline door): a plain local
#     whose OWN initializer spells offsetof(typeof(*VAR), m), inside a static
#     inline whose PARAMETER NAME the caller's local captures. The hoist
#     happens at PARSE time, the clone rename happens LATER — the spliced
#     body must still answer the renamed slots (probe sp1: caller local
#     `timer` collides with the parameter `timer`; measured own hands:
#     gcc/blcc exit-paired, and the emitted asm carries NO out-of-line
#     `unbox:` leaf — the clone happened).
# (2) SATURATING PAIR at the interaction site (sims p_offzero lawlet): sp1
#     carries the FILLS spelling (the second offsetof answers work@16), sp2
#     the FITS spelling (timer@0). The pair pins the clone's fold VALUE.
# (3) THE KYBER PIN — RETARGETED BY VALUE (sims §5 parse-order side effect).
#     SUPERSEDED (M4 W-AS, card 12901): at tip a063dcc block_kyber-iosched
#     first-walled at :45646:421 with `__builtin_offsetof: 'timer' is a
#     member path into a non struct/union type (§2.13), found '('`. Under
#     {R} the hoisted initializer parse sizes `struct __call_single_data`
#     earlier and the W-K cycle guard fires FIRST: the wall moved BACKWARD to
#     :10765:36 `sema: circular layout dependency: 'struct
#     __call_single_data' is being sized while its 'aligned' attribute
#     argument sizes it (§2.13 cycle guard), found ''`. The stream is NOT
#     open (rc2 stands — own hands out/next-r.jsonl); the pin moves BY VALUE
#     with this SUPERSEDED paragraph (W-AM COMMIT-4 precedent), never dropped.
# (4) THE MAP-VIOLATION CATCHER: kernel_kthread.c.i / kernel_workqueue.c.i
#     next-walled at `sema: cannot load a 24-byte value (§4), found 'load'`
#     (:48190:4 / :44285:13, own hands). The §4-24B door is NEXT-CARD
#     territory (sims marked the combo UNMEASURED-on-second-hop — DO-NOT-
#     SHIP). If anyone smuggles the §4-24B load door into this family, these
#     streams compile and the catcher goes RED at that gate (the MAP-VIOLATION
#     plant's witness rows — the sims' restraint, legislated).
import os
import subprocess
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4was2_%s_%d_%s" % (os.environ.get("M4WAS_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
STREAMS = os.environ.get("BLCC_STREAMS") or os.path.join(
    REPO, "..", ".tmp", "m4-plan", "streams")

BOX = ("typedef struct { long handles; long pad; } timer_t;\n"
       "typedef struct { timer_t timer; long work; } box_t;\n"
       "static box_t g_box = { { 1, 2 }, 41 };\n")
UNBOX = """static inline long unbox(timer_t *timer)
{
    box_t *owner = (box_t *)((char *)timer -
        __builtin_offsetof(typeof(*owner), timer));
    return owner->work + __builtin_offsetof(typeof(*owner), work);
}
"""
MAIN = "int answer(void);\nint main(void){ return answer(); }\n"

# sp1: CALLER-CAPTURE (the caller's local `timer` collides with the inline's
# parameter `timer`) — post-RENAME splice × self-decl. 41 + 16 + 3 = 60, the
# FILLS spelling (the second offsetof answers work@16 INSIDE the clone).
SP1 = BOX + UNBOX + """int answer(void)
{
    box_t *timer = &g_box;
    return unbox(&timer->timer) + (timer != 0) * 3;
}
"""
# sp2: no-collision control + FITS spelling (only the timer@0 offset is
# folded; 41 + 1 = 42) — the saturating twin at the interaction site.
SP2 = BOX + """static inline long unbox(timer_t *timer)
{
    box_t *owner = (box_t *)((char *)timer -
        __builtin_offsetof(typeof(*owner), timer));
    return owner->work + 1;
}
int answer(void)
{
    box_t *t = &g_box;
    return unbox(&t->timer);
}
"""
SPLICE_ROWS = {"sp1_callercapture_selfdecl_clone": (SP1, 60),
               "sp2_nocollision_fits_twin": (SP2, 42)}


def _law_main(d):
    key = os.path.join(d, "law_main_%d.o" % os.getpid())
    if not os.path.exists(key):
        src = os.path.join(d, "law_main_%d.c" % os.getpid())
        with open(src, "w") as fh:
            fh.write(MAIN)
        subprocess.run(["gcc", "-c", src, "-o", key], check=True,
                       capture_output=True)
    return key


def _side(name, src, which):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "%s_%s_%d.c" % (name, which, os.getpid()))
    with open(c, "w") as fh:
        fh.write(src)
    o = c[:-2] + ".o"
    exe = c[:-2] + "." + which
    if which == "gcc":
        r = subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
                           capture_output=True, text=True)
    else:
        r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                           capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
        if r.returncode != 0:
            return r.returncode, (r.stdout + r.stderr)
    link = subprocess.run(["gcc", "-no-pie", o, _law_main(TMP), "-o", exe],
                          capture_output=True, text=True)
    if link.returncode != 0:
        return 99, link.stderr
    return 0, subprocess.run([exe], capture_output=True,
                             timeout=60).returncode


import pytest


@pytest.mark.parametrize("name", sorted(SPLICE_ROWS))
def test_was_splice_selfdecl_pairs_postrename(name):
    src, gexit = SPLICE_ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gexit, (name + ": gcc moved off the ground "
                                      "measured own hands (rc=" + str(grc) +
                                      " " + repr(g) + ") — re-measure")
    brc, b = _side(name, src, "blcc")
    assert brc == 0, (name + ": rc=" + str(brc) + " — the clone lost the "
                      "self-decl binding:\n" + str(b)[:300])
    assert b == g, (name + ": SILENT — blcc " + str(b) + " vs gcc " + str(g)
                    + " (the clone carries the wrong fold VALUE — the "
                    "saturating pair pins it)")


def test_was_clone_happened_no_outofline_leaf():
    # The W-P door proof (m4wag1 idiom): the asm carries NO `unbox:` leaf —
    # the body was SPLICED post-RENAME with the self-decl local intact.
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "was2asm.c")
    with open(c, "w") as fh:
        fh.write(SP1 + MAIN)
    s = os.path.join(TMP, "was2asm.s")
    r = subprocess.run(["python3", "-m", "blcc", "--emit-asm", c, "-o", s],
                       capture_output=True, text=True, cwd=REPO,
                       env=dict(os.environ, PYTHONPATH=REPO))
    assert r.returncode == 0, r.stderr[:300]
    asm = open(s + ".s").read()
    assert "\nunbox:" not in asm and not asm.startswith("unbox:"), \
        "the splice fell back to the CALL law: an `unbox:` leaf survived"


# ---- corpus pins (KERNEL tier): the retargeted kyber wall + shut doors ----

def _clean_compile(stream, tag):
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(TMP, tag + ".clean.i")
    keep = []
    with open(os.path.join(STREAMS, stream), "r", errors="replace") as fh:
        for ln in fh:
            if not ln.startswith("# "):
                keep.append(ln)
    with open(out, "w") as fh:
        fh.write("".join(keep))
    r = subprocess.run(
        ["python3", "-m", "blcc", "-c", out,
         "-o", os.path.join(TMP, tag + ".o")],
        capture_output=True, text=True, cwd=REPO,
        env=dict(os.environ, PYTHONPATH=REPO))
    return r


@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
def test_was_kyber_wall_retargeted_by_value():
    # SUPERSEDED paragraph in the file header: the tip member-path wall is
    # DEAD for this stream (moved BACKWARD to the circular guard). The wall
    # STANDS (rc2) — a MOVED wall is not an OPENED wall.
    r = _clean_compile("block_kyber-iosched.c.i", "was2kyber")
    diag = (r.stdout + r.stderr).replace(TMP, "")
    assert r.returncode != 0, "kyber ACCEPTED — the door is not {R}-sized:\n" \
        + diag[:300]
    assert "circular layout dependency" in diag, \
        "kyber's wall is NOT the circular guard — the retarget is stale:\n" \
        + diag[:300]
    assert "member path into a non struct/union type" not in diag, \
        "the SUPERSEDED member-path sentence answers kyber again:\n" \
        + diag[:300]


@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
@pytest.mark.parametrize("stream,line", [
    ("kernel_kthread.c.i", "48190"), ("kernel_workqueue.c.i", "44285")])
def test_was_s424b_door_stays_shut(stream, line):
    # THE MAP-VIOLATION CATCHER. §4-24B is NEXT-CARD territory (sims marked
    # the combo UNMEASURED-on-second-hop; W-AS ships {R} ONLY). The stream
    # must STILL wall, AT the §4-24B sentence, at the pinned position. A
    # smuggled §4-24B door turns this RED — that is the plant witness.
    r = _clean_compile(stream, "was2s424b")
    diag = (r.stdout + r.stderr).replace(TMP, "")
    assert r.returncode != 0, (stream + ": ACCEPTED — §4-24B was smuggled "
                               "into this wave (MAP VIOLATION):\n"
                               + diag[:400])
    assert "cannot load a 24-byte value (§4), found 'load'" in diag, \
        (stream + ": no longer walls AT the §4-24B sentence — retarget this "
         "row BY NAME (own card), never silently:\n" + diag[:300])
    assert ":%s:" % line in diag, (stream + ": §4-24B sentence moved off "
                                   ":" + line + ": — re-measure the row")
