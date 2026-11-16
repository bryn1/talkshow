"""M4 W4-fix (MC 12586) — the libcpp OBJECT LAW + gcc-raw path spellings.

Gate verdict .tmp/evidence/m4-w4-gate-verdict.md:
  F-1 (P2): the W4 event identity (directive-name, origin-kind)
      over-collapsed — the SAME quoted NAME resolving to DIFFERENT FILES
      from different includer dirs must emit BOTH prereqs (gate LEG1 case
      6, gcc 11.4 beside it). blcc collapsed to one.
  F-2 (P3): the .d must carry gcc's RAW spellings — `../`, `//`, `./`
      segments survive (37/705 universe recipes; blcc normpath-collapsed).
  F-3 (P3): the m5 (-MD/-MMD last-wins) and m10 (is_forwardable part
      count) mutation survivors pinned as direct law legs.

THE LAW, ported from the gcc-11 libcpp source (files.c fetched + read,
incpath/add_path behavior MEASURED against gcc 11.4 this session):
_cpp_find_file keeps ONE OBJECT per (fname string, start_dir) with cache
SHARING at the (quote≡bracket) search-chain head; _cpp_stack_file emits
file->path exactly once, at the object's FIRST OPEN. start_dir for a
quoted include is the INCLUDER'S dir hashed as its RAW PATH PREFIX —
make_cpp_dir hashes the string, so "" != "./" != "d1/", and the same
name resolving from two includer dirs is TWO objects (F-1). A fresh
find via the chain registers BOTH the start key and the chain key, so a
later angle lookup of that name SHARES (no second emit); guards and
file emptiness play no role. Spellings are NEVER normalized:
append_file_to_dir joins dir+name raw (a '/' rides only when the dir
lacks a trailing separator) and the .d drops LEADING "./" components
only (measured: -I./inc -> inc/n.h; -I././inc -> inc/n.h; -Iinc -> mid
path dots kept: name "./x.h" -> inc/./x.h; name "sub//x.h" ->
inc/sub//x.h; -Iinc/sub/.. -> inc/sub/../n.h).

RED proof: legs 1, 2 (identity half), the TB leg and the collapse-shaped
F-2 rows are RED at 4eb643d — capture .tmp/m4-w4fix/out/red-at-4eb643d.txt.
"""
import os
import subprocess
import sys

import pytest

REPO = os.environ.get("BLCC_REPO") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _blcc(args, cwd):
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          cwd=cwd, capture_output=True, text=True, env=env)


def _gcc(args, cwd):
    return subprocess.run(["gcc"] + args, cwd=cwd,
                          capture_output=True, text=True)


def _read(path):
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else None


def _pair(tmp_path, tag, src, flags):
    """Same compile both compilers; returns (gdeps, bdeps, grc, brc) with
    the target word split off (each side writes its OWN .d name)."""
    gd, bd = "%s.g.d" % tag, "%s.b.d" % tag
    g = _gcc(["-Wp,-MMD," + gd] + flags + ["-c", src, "-o", "o_g.o"], tmp_path)
    b = _blcc(["-Wp,-MMD," + bd] + flags + ["-c", src, "-o", "o_b.o"], tmp_path)
    gt, bt = _read(os.path.join(tmp_path, gd)), _read(os.path.join(tmp_path, bd))
    if gt is not None:
        gt = gt.split(":", 1)[1]
    if bt is not None:
        bt = bt.split(":", 1)[1]
    return gt, bt, g.returncode, b.returncode


def _dep_words(d):
    """The prereq tokens of a .d body (wraps folded) — target excluded."""
    body = d.replace("\\\n", "")
    return body.split()


def _tree(d):
    w = lambda p, t: open(os.path.join(d, p), "w").write(t)
    for sub in ("d1", "d2", "j1", "j2", "inc", "inc/sub", "sys"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    # F-1 core: same quoted NAME, DIFFERENT files by includer dir
    w("d1/inc.h", '#include "s.h"\n')
    w("d2/inc.h", '#include "s.h"\n')
    w("d1/s.h", "#define S1 1\n")
    w("d2/s.h", "#define S2 2\n")
    w("tu_f1.c", '#include "d1/inc.h"\n#include "d2/inc.h"\nint e;\n')
    # chain-found name: NOT in j1/j2 -> both includers reach inc/js.h
    w("j1/inc.h", '#include "js.h"\n')
    w("j2/inc.h", '#include "js.h"\n')
    w("inc/js.h", "#define JS 1\n")
    w("tu_chain.c", '#include "j1/inc.h"\n#include "j2/inc.h"\nint e;\n')
    # same includer dir twice
    w("d1/a.h", '#include "s.h"\n')
    w("d1/b.h", '#include "s.h"\n')
    w("tu_same.c", '#include "d1/a.h"\n#include "d1/b.h"\nint e;\n')
    # angle AFTER a quoted chain find shares the object (chain-head cache)
    w("inc/t.h", "#define T1 1\n")
    w("tu_share.c", '#include "d1/x.h"\n#include <t.h>\nint e;\n')
    w("d1/x.h", '#include "t.h"\n')
    # raw-string includer-dir identity: root ("") vs "./"
    w("a.h", '#include "x.h"\n')
    w("b.h", '#include "x.h"\n')
    w("x.h", "#define XR 1\n")
    w("tu_tb.c", '#include "a.h"\n#include "./b.h"\nint e;\n')
    # F-2 spelling fixtures
    w("n.h", "#define NROOT 1\n")          # reachable via -I. / -I./
    w("inc/n.h", "#define NINC 1\n")       # reachable via -Iinc variants
    w("inc/x.h", "#define XINC 1\n")
    w("inc/z.h", "#define ZINC 1\n")     # chain-only: never root-reachable
    w("inc/sub/y.h", "#define Y 1\n")
    w("inc/sub/z.h", "#define ZSUB 1\n")  # the file "//" actually opens
    w("tu_dotd.c", '#include <n.h>\nint e;\n')
    w("tu_name1.c", '#include "./z.h"\nint e;\n')      # chain: inc/./z.h
    w("tu_name2.c", '#include "sub/../z.h"\nint e;\n')  # inc/sub/../z.h
    w("tu_name3.c", '#include "sub//z.h"\nint e;\n')    # inc/sub//z.h
    w("tu_inc0.c", 'int e;\n')
    return d


@pytest.fixture
def tree(tmp_path):
    return _tree(str(tmp_path))


# ---------------------------------------------------------------- F-1 identity

def test_f1_same_quoted_name_two_includer_dirs_emits_both(tree):
    # The gate's LEG1 case-6 shape, sealed (RED at 4eb643d: d2/s.h MISSING).
    gt, bt, grc, brc = _pair(tree, "f1", "tu_f1.c", [])
    assert grc == 0 and brc == 0
    assert bt is not None and bt == gt
    # NAMED assertions so the RED was F-1, not an incidental byte-diff:
    words = _dep_words(bt)
    assert "d1/s.h" in words and "d2/s.h" in words, \
        "F-1: same quoted NAME resolving to DIFFERENT files must emit BOTH"


def test_f1_quoted_found_via_chain_rides_once(tree):
    # Two DIFFERENT includer dirs, one CHAIN-found file: ONE prereq
    # (the chain-head cache shares the object — no regression on this
    # half of the law while the F-1 half is fixed).
    gt, bt, grc, brc = _pair(tree, "chain", "tu_chain.c", ["-Iinc"])
    assert grc == 0 and brc == 0
    assert bt == gt
    assert _dep_words(bt).count("inc/js.h") == 1


def test_f1_quoted_same_includer_dir_rides_once(tree):
    gt, bt, grc, brc = _pair(tree, "same", "tu_same.c", [])
    assert grc == 0 and brc == 0
    assert bt == gt
    assert _dep_words(bt).count("d1/s.h") == 1


def test_f1_angle_after_quoted_chain_find_shares(tree):
    # The chain-head CACHE law: a quoted name first found THROUGH THE
    # CHAIN makes a later angle lookup of the same NAME share the object
    # (one prereq), while a name found in its OWN dir stays its own
    # object (I3: quoted own-dir + angle chain = TWO).
    gt, bt, grc, brc = _pair(tree, "share", "tu_share.c", ["-Iinc"])
    assert grc == 0 and brc == 0
    assert bt == gt
    assert _dep_words(bt).count("inc/t.h") == 1


def test_f1_includer_dir_identity_is_the_raw_string(tree):
    # make_cpp_dir hashes the dir STRING: "" (includer "a.h") and "./"
    # (includer "./b.h") are DIFFERENT objects, so "x.h" rides TWICE —
    # gcc measured, byte-identical spellings both "x.h" after the
    # leading-"./" drop (RED at 4eb643d: blcc collapsed them to one).
    gt, bt, grc, brc = _pair(tree, "tb", "tu_tb.c", [])
    assert grc == 0 and brc == 0
    assert bt == gt
    assert _dep_words(bt).count("x.h") == 2


# ------------------------------------------------------------------ F-2 spelling

@pytest.mark.parametrize("tag,src,flags,want", [
    # dir spellings: the leading "./" drops, ".." and mid dots ride RAW
    ("s1", "tu_dotd.c", ["-I."], "n.h"),
    ("s2", "tu_dotd.c", ["-I./"], "n.h"),
    ("s3", "tu_dotd.c", ["-Iinc"], "inc/n.h"),
    ("s4", "tu_dotd.c", ["-I./inc"], "inc/n.h"),
    ("s5", "tu_dotd.c", ["-I././inc"], "inc/n.h"),
    ("s6", "tu_dotd.c", ["-Iinc/"], "inc/n.h"),
    ("s7", "tu_dotd.c", ["-Iinc/sub/.."], "inc/sub/../n.h"),
    # name spellings: "./" and ".." and "//" ride RAW (mid-path)
    ("n1", "tu_name1.c", ["-Iinc"], "inc/./z.h"),
    ("n2", "tu_name2.c", ["-Iinc"], "inc/sub/../z.h"),
    ("n3", "tu_name3.c", ["-Iinc"], "inc/sub//z.h"),
])
def test_f2_gcc_raw_spellings_no_collapse(tree, tag, src, flags, want):
    # RED at 4eb643d for s7/n1/n2/n3 (normpath collapsed them).
    gt, bt, grc, brc = _pair(tree, tag, src, flags)
    assert grc == 0 and brc == 0, "fixture must compile under gcc"
    assert bt == gt, "gcc-raw spelling byte law"
    assert want in _dep_words(bt), want


def test_f2_preinclude_operand_leading_dot_dropped(tree):
    # -include ./n.h — the "./" + operand join then the leading-drop:
    # the prereq is "n.h" (not "./n.h", not normpath-mangled).
    gt, bt, grc, brc = _pair(tree, "pi", "tu_inc0.c", ["-include", "./n.h"])
    assert grc == 0 and brc == 0
    assert bt == gt
    assert _dep_words(bt) == ["tu_inc0.c", "n.h"]


# ------------------------------------------------- F-3 mutation-survivor pins

def test_m5_md_mmd_last_wins_is_the_law():
    # m5 class: the 12-mutant mutation run SURVIVED a first-wins flip —
    # no leg exercised two depfile-mode flags in one argv. Pin it.
    from blcc import depfile
    d = depfile.parse_wp(["-Wp,-MD,a.d", "-Wp,-MMD,b.d"])
    assert d.mode == "MMD" and d.file == "b.d"     # LAST wins
    d = depfile.parse_wp(["-Wp,-MMD,b.d", "-Wp,-MD,a.d"])
    assert d.mode == "MD" and d.file == "a.d"      # LAST wins
    d = depfile.parse_wp(["-Wp,-MMD,x.d", "-Wp,-MF,y.d", "-Wp,-MMD,z.d"])
    assert d.mode == "MMD" and d.file == "z.d" and d.mf == "y.d"


def test_m10_is_forwardable_exactly_two_parts():
    # m10 class: len(parts) >= 2 survived (REJECT-LOUD still fired
    # DOWNSTREAM in parse_wp). Pin the WRAPPER GATE itself: an
    # un-forwardable token never reaches the parser through this law.
    from blcc import depfile
    assert depfile.is_forwardable("-Wp,-MMD,f.d")
    assert depfile.is_forwardable("-Wp,-MF,f.d")
    assert not depfile.is_forwardable("-Wp,-MMD,a.d,b")     # 3 parts
    assert not depfile.is_forwardable("-Wp,-MMD")           # 1 part
    assert not depfile.is_forwardable("-Wp,-MMD,")          # empty operand
    assert not depfile.is_forwardable("-Wp,-MD,x,-MT")      # 3 parts
    assert not depfile.is_forwardable("-Wp,-DFOO")          # unknown
    assert not depfile.is_forwardable("-DFOO")              # not -Wp
