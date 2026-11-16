"""M4 W-B COMMIT-0 (MC 12596) — the `.//dir` SPELLING law + the REPO law.

(a) THE SPELLING LAW (gate m4-w4-fixgate LEG2 rep, .tmp/m4-w4-fixgate/
    leg2/rep/): the F-2 drop-pairs loop in `_spell` (preproc.py) strips a
    leading `./` pair at a time, so `.//inc/n.h` lost only its FIRST two
    chars and printed `/inc/n.h` where gcc prints `inc/n.h`. The gcc-11.4
    measured law (rep rows tu2/tu3/tu4/tu5, g2.d–g4.d beside b2.d–b4.d):
    a LEADING `.` component eats its `.` AND every slash that follows it
    (`././/dd/a.h` -> `dd/a.h`; `-I.//inc` -> `inc/n.h`); non-dot leading
    spellings — `/abs/…`, `../…`, plain `dd/…` — stay RAW exactly as the
    F-2 law already holds them. Object IDENTITY is unchanged (the two
    spellings `.//dd/a.h` and `dd/a.h` are still TWO objects — g3.d emits
    FOUR prereq words, both files twice); only the SPELLING collapses.

(b) THE REPO LAW: test files must derive REPO from __file__ (the repo
    idiom) — a hardcoded shared-tree path is a FALSE-GREEN channel: a
    sealed-leg run of an OLD tree would exec the SHARED tree's blcc and
    grade code it never checked out. Files named by the brief:
    tests/test_depfile_m4fix.py, tests/test_core_m4w3fix.py,
    tests/test_core_m4w3_ind.py (+ the same defect found by grep in
    tests/test_depfile_m4.py — the fix is not done until every caller
    has it).

RED at 4e956b3: the three spelling legs + the repo-law leg — capture
.tmp/m4-wb/out/red-commit0.txt.
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)


def _blcc(args, cwd):
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          cwd=cwd, capture_output=True, text=True, env=env)


def _gcc(args, cwd):
    return subprocess.run(["gcc"] + args, cwd=cwd,
                          capture_output=True, text=True)


def _read(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _pair(tmp_path, tag, src, flags):
    gd, bd = "%s.g.d" % tag, "%s.b.d" % tag
    g = _gcc(["-Wp,-MMD," + gd] + flags + ["-c", src, "-o", "o_g.o"],
             tmp_path)
    b = _blcc(["-Wp,-MMD," + bd] + flags + ["-c", src, "-o", "o_b.o"],
              tmp_path)
    gt, bt = _read(os.path.join(tmp_path, gd)), _read(os.path.join(tmp_path, bd))
    if gt is not None:
        gt = gt.split(":", 1)[1]
    if bt is not None:
        bt = bt.split(":", 1)[1]
    return gt, bt, g.returncode, b.returncode


def _tree(d):
    w = lambda p, t: open(os.path.join(d, p), "w").write(t)
    for sub in ("dd", "inc"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    w("dd/a.h", '#include "s.h"\n')
    w("dd/s.h", "#define DS 1\n")
    w("inc/n.h", "#define ND 1\n")
    w("n.h", "#define NROOT 1\n")
    w("tu_slsl.c", '#include ".//dd/a.h"\nint e;\n')       # rep tu2
    w("tu_dslsl.c", '#include "././/dd/a.h"\nint e;\n')    # rep tu3
    w("tu_two.c", '#include ".//dd/a.h"\n#include "dd/a.h"\nint e;\n')  # rep tu4
    w("tu_angle.c", "#include <n.h>\nint e;\n")
    return d


@pytest.fixture
def tree(tmp_path):
    return _tree(str(tmp_path))


# ---------------------------------------------------------------- (a) spelling

def test_dir_slsl_angle_spells_without_dot(tree):
    # rep D10: -I.//inc -> gcc spells the prereq `inc/n.h` (blcc tip:
    # `/inc/n.h`). -I. after it so the FILE still resolves (rep order).
    gt, bt, grc, brc = _pair(tree, "d10", "tu_angle.c", ["-I.//inc", "-I."])
    assert grc == 0 and brc == 0, (gt, bt)
    assert bt == gt
    assert " inc/n.h" in (" " + bt), \
        "gcc spells `-I.//inc` prereq as inc/n.h — dot + slashes EATEN"
    assert "/inc/n.h" not in bt, "no leading-slash spelling (rep b2 class)"


def test_quoted_dot_slsl_spell_pair(tree):
    # rep tu3/g2/b2: `././/dd/a.h` must spell `dd/a.h` both sides.
    gt, bt, grc, brc = _pair(tree, "g2", "tu_dslsl.c", [])
    assert grc == 0 and brc == 0, (gt, bt)
    assert bt == gt
    words = bt.replace("\\\n", "").split()
    assert words[1:] == ["dd/a.h", "dd/s.h"], words


def test_two_spellings_same_file_two_objects_both_spelled(tree):
    # rep tu4/g3/b3: `.//dd/a.h` AND `dd/a.h` are TWO objects (four prereq
    # words — the F-1 identity law) and BOTH spell `dd/a.h … dd/s.h`.
    gt, bt, grc, brc = _pair(tree, "g3", "tu_two.c", [])
    assert grc == 0 and brc == 0, (gt, bt)
    assert bt == gt
    words = bt.replace("\\\n", "").split()
    assert words[1:] == ["dd/a.h", "dd/s.h", "dd/a.h", "dd/s.h"], words


# ------------------------------------------------------------------ (b) REPO law

_HARDCODED = re.compile(r'^REPO\s*=\s*"/home', re.M)


def test_no_test_file_hardcodes_repo_path():
    # A hardcoded shared-tree REPO is the false-green channel: a run of a
    # sealed checkout grades the SHARED tree's code. Every test file
    # derives REPO from __file__ (the repo idiom) or from BLCC_REPO.
    offenders = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.startswith("test_") or not fn.endswith(".py"):
            continue
        with open(os.path.join(HERE, fn), "r", encoding="utf-8") as f:
            if _HARDCODED.search(f.read()):
                offenders.append(fn)
    assert not offenders, \
        "REPO hardcoded in: " + ", ".join(offenders)
