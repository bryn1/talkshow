# LINES reason: one wave (M4 W-T COMMIT-0, g05/g07 LOUD twin, card
# 12404.2.99): every leg is an arm of the ONE scoped-label use law;
# splitting would separate a LOUD row from its quiet twin.
r"""M4 W-T COMMIT-0 (MC 12736) — the g05/g07 quieter-than-gcc class
gets its LOUD twin AT THE ONE CLASSIFYING PLACE: blcc/codegen.py
`_label_ref` (the single resolution site for `goto` AND `&&label`).

THE gcc 11.4 -Os LAW (W-S gate MC 12721 LEG3 note 1 + own rows wt0a-
wt0f below, .tmp/m4-wt/out/laws-gcc.txt): a name DECLARED `__label__`
inside a `({...})` group is SCOPED TO THE GROUP — a `goto`/`&&` use of
that name FROM INSIDE the group resolves ONLY to a definition inside
the group; a definition that exists at root or at an outer group does
NOT count ("label 'h' used but not defined", gcc rc1). Today blcc
ACCEPTED these quietly (quieter-than-gcc — the gate probed the pre-W-S
tree 84d30ec: rc0 there too, PRE-EXISTING, not a wave regression).
The twin REPLACES: the silent `jmp` to the out-of-group definition.
CORPUS VOLUME 0 (pinned leg below): `goto __here` = 0 over the 706
pinned streams — the kernel uses ONLY the declare+define+&& shape, so
the LOUD twin cannot lose a single accepted stream.

Quiet twins that MUST STAY PAIR (measured rc0 BOTH, wt0d/wt0e/wt0f):
a group WITHOUT its own declaration jumping outward; a declaration
whose definition IS inside the group; a deeper group referencing a
name declared+defined at an outer group (the outermost use law is
unchanged — outward jumps are legal, §2.4d jump-INTO law untouched).
"""
import os
import re
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


def _loud(tag, src):
    """gcc must refuse AND blcc must refuse, with the scoped-label
    wall named (never a generic message)."""
    c = "/dev/shm/wt0_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode != 0, "gcc must reject the law row: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode != 0, "%s: scoped-label use must be LOUD: " % tag \
        + b.stderr
    assert "used but not defined" in b.stderr, \
        "%s: LOUD twin must name the same law: " % tag + b.stderr


def _pair(tag, src):
    c = "/dev/shm/wt0_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/wt0_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "quiet twin must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wt0_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wt0_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "quiet twin must COMPILE: " + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wt0_%s.b" % tag],
                          capture_output=True).returncode == 0
    assert subprocess.run(["/dev/shm/wt0_%s.b" % tag],
                          env={"PATH": "/usr/bin:/bin"}).returncode == gex


def test_wt0_g07_goto_decl_group_def_root_loud():
    # THE g07 row (gate label_laws3 g07): group DECLARES h, the only
    # definition is at ROOT. gcc: "label 'h' used but not defined".
    _loud("g07", "int main(){ ({ __label__ h; goto h; });"
          " h: return 4; }")


def test_wt0_g05_nested_decl_group_def_outer_loud():
    # THE g05 row: inner group DECLARES L, the definition lives in the
    # OUTER group. gcc LOUD (the shadowed name is never defined in the
    # group that declares it).
    _loud("g05", "int main(){int r=0; ({ __label__ L;"
          " ({ __label__ L; goto L; r=5; }); goto L; r=9; L: ; });"
          " return r;}")


def test_wt0_andref_decl_group_def_root_loud():
    # the &&-address twin (wt0c): same law, same one place.
    _loud("wt0c", "int main(){unsigned long a;"
          " ({ __label__ h; a=(unsigned long)&&h; });"
          " h: return (int)(a&7); }")


def test_wt0_root_decl_shadowed_by_group_loud():
    # wt0b: root ALSO declares h — the group declaration still scopes
    # the name to the group (gcc LOUD).
    _loud("wt0b", "int main(){__label__ h; int r=0;"
          " ({ __label__ h; goto h; r=5; }); h: r=7; return r;}")


def test_wt0_goto_out_without_decl_pair():
    # wt0d (gcc rc0): NO declaration in the group — the outward `goto`
    # is a plain outward jump, legal (§2.4d untouched).
    _pair("wt0d", "int main(){int r=0; ({ goto h; r=5; });"
          " h: r=7; return r;}")


def test_wt0_decl_defined_in_group_pair():
    # wt0e (gcc rc0 RUN 0): declare AND define inside the group.
    _pair("wt0e", "int main(){int r=0;"
          " ({ __label__ h; goto h; r=5; h: ; }); return r;}")


def test_wt0_deep_use_of_outer_decl_def_pair():
    # wt0f (gcc rc0): the deeper group carries NO declaration; the use
    # walks outward to the declared+defined name. Quiet stays quiet.
    _pair("wt0f", "int main(){int r=0; ({ __label__ L;"
          " ({ goto L; r=5; }); L: ; }); return r;}")


def test_wt0_volume_zero_goto_here():
    # The LOUD twin costs ZERO corpus streams: `goto __here` appears
    # in NONE of the 706 pinned streams (own-hands re-measure of the
    # gate's number). The kernel's ONLY scoped-label shape is the
    # declare+define+&& _THIS_IP_ idiom, which stays pair-quiet.
    if not os.path.isdir(PINNED):
        pytest.skip("pinned corpus not linked (builder posture)")
    n = 0
    for f in os.listdir(PINNED):
        if not f.endswith(".i"):
            continue
        with open(os.path.join(PINNED, f), errors="replace") as fh:
            n += len(re.findall(r"\bgoto\s+__here\b", fh.read()))
    assert n == 0, "volume-0 pin broken: %d corpus `goto __here` sites" % n
