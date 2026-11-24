# LINES reason: one wave (M4 W-AE COMMIT-1 MC 12819): the slot-model PAIRING
# law is ONE contract; the pin vectors are its measured truth and stay
# beside it (vectors from card 12816 §1a/§1c, re-measured at my hands).
r"""M4 W-AE pairing law (MC 12404.2.141 / job 12819) — AGREEMENT-PINNING.

THE WALL: the walk's standing first RED (init/init_task.c:69:3, data.py:580
`len(items) > len(slots)`) was a TWO-HOME disagreement about ONE member —
the anonymous `unsigned :0;` inside struct task_struct. The parser's
_init_slots gave it a positional slot (120); the data-side _struct_layout
and gcc 11.4 both skip it (119 members, DWARF sizeof 5824). DATA == gcc;
the PARSER table was the divergent home.

THE LAW this file pins (both directions — sims §6): for every struct/union
the front end completes, parser `_init_slots` and data `_struct_layout`
emit the SAME slot SEQUENCE — identical names and counts — and identical
BYTE offsets wherever both tables carry byte truth. Bit rows: DATA's bit
descriptor is the gcc truth (pinned against the card-12816 DWARF vectors);
the parser's residual bit-slot drift is NOT law but is PINNED here as
MEASURED (+4/slot through the unit run, +24 carried to the tail, rejoin at
`thread` = 1472 = gcc offsetof) so no third home can shift it silently.
A change to ONE home without the other turns this file RED — that is the
pairing plant's witness (plants at the wave's teeth gate).

Pin vectors (card 12816 §1a/§1c, re-measured own hands at ship): counts
P==D==119 == gcc DWARF members; idx30 sched_reset_on_fork (first shape
fork: P-off 564 == DATA unit, DATA == DWARF (564, lsb 0..2)); idx33
THE COUNT FORK (sched_remote_wakeup lands at DATA (568,0,1), parser drift
+8); rows 38..117 carry +24; idx118 `thread` rejoins P==D==1472; DATA
total 5824 == gcc sizeof. RED-FIRST: at base bytes task_struct counts 120
!= 119 — this file's task_struct test and the ae11 leg of
test_core_m4wae2.py both FAIL at base.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
sys.path.insert(0, REPO)

from blcc import ast                                # noqa: E402
from blcc.lexer import Lexer, SourceLine            # noqa: E402
from blcc.parser import Parser                      # noqa: E402
from blcc.codegen import Codegen                    # noqa: E402
import test_core_m4w1 as w1                         # noqa: E402

STREAMS = os.environ.get("BLCC_STREAMS") or w1.STREAMS
needs_streams = pytest.mark.skipif(
    not os.path.isdir(STREAMS), reason="corpus streams not present")

GCC_SIZEOF_TASK = 5824          # gcc 11.4 DWARF truth (card 12816 §1c)
GCC_THREAD_OFF = 1472           # gcc offsetof(task_struct, thread)
GCC_DWARF_MEMBERS = 119         # the :0 pad is NOT a DWARF member

# card 12816 §1a: the eight bit rows of task_struct (idx 30..37) — DATA's
# descriptors == gcc DWARF byte/bit EXACTLY; parser slot offsets and the
# measured drift vector.
BF_ROWS = {                       # idx: (data descriptor, p-off, drift)
    30: ((564, 0, 1), 564, 0), 31: ((564, 1, 1), 568, 4),
    32: ((564, 2, 1), 572, 8), 33: ((568, 0, 1), 576, 8),
    34: ((568, 1, 1), 580, 12), 35: ((568, 2, 1), 584, 16),
    36: ((568, 3, 1), 588, 20), 37: ((568, 4, 1), 592, 24),
}
TAIL_DRIFT = {i: 24 for i in range(38, 118)}   # +24 carried to the tail


def _tables(src, tag, union=False):
    """ONE front-end pass; BOTH slot tables read out of it (no subprocess —
    the law is about the two in-engine tables, not the emitted bytes)."""
    lines = [SourceLine("<pin>", i + 1, ln)
             for i, ln in enumerate(src.splitlines())]
    p = Parser(Lexer(lines).tokenize())
    tu = p.parse_translation_unit()
    P = p._init_slots(ast.StructType("<pin>", 1, 1, tag, union))
    _offs, total, D = Codegen(tu)._struct_layout(
        ast.StructType("<pin>", 1, 1, tag, union), None)
    return P, D, total


def _assert_pairing(P, D, drift=None, tag="?"):
    """THE LAW: identical slot sequence; byte-offset parity wherever the
    tables carry byte truth. drift = dict row -> expected P-D offset delta
    for the rows carrying MEASURED residual drift (default none)."""
    drift = drift or {}
    pn = [s[0] for s in P]
    dn = [s[0] for s in D]
    assert len(P) == len(D), \
        "%s: slot-count fork — parser %d vs data %d (the init_task wall " \
        "class, data.py:580)" % (tag, len(P), len(D))
    assert pn == dn, "%s: slot NAME sequence diverged: %s vs %s" % (
        tag, pn, dn)
    for i, (p, d) in enumerate(zip(P, D)):
        exp = drift.get(i, 0)
        assert p[2] - d[2] == exp, \
            "%s row %d (%s): offset parity broken — parser %d data %d, " \
            "expected drift %d, got %d" % (
                tag, i, d[0], p[2], d[2], exp, p[2] - d[2])
        if d[4] is None:
            assert p[3] == d[3], "%s row %d: byte-size fork %s" % (
                tag, i, d[0])


# ------------------------------------------------------------ REAL shape
@needs_streams
def test_slot_pairing_on_the_real_task_struct(tmp_path):
    """The REAL struct behind the wall, from the pinned corpus stream:
    counts, names, every pin vector of card 12816 §1a/§1c."""
    clean = w1._clean_i(os.path.join(STREAMS, "init_init_task.c.i"),
                       tmp_path, "wae-pin")
    src = open(clean, encoding="utf-8", errors="replace").read()
    P, D, total = _tables(src, "task_struct")
    assert len(D) == GCC_DWARF_MEMBERS == len(P), \
        "task_struct counts vs gcc DWARF: P=%d D=%d DWARF=%d" % (
            len(P), len(D), GCC_DWARF_MEMBERS)
    assert total == GCC_SIZEOF_TASK, \
        "DATA total %d != gcc sizeof %d (DATA IS gcc — card 12816 §1c)" % (
            total, GCC_SIZEOF_TASK)
    drift = dict(TAIL_DRIFT)
    for i, (_bf, _po, _dr) in BF_ROWS.items():
        drift[i] = _dr
    _assert_pairing(P, D, drift=drift, tag="task_struct")
    # idx30: first SHAPE fork — P byte-offset == DATA unit (564), DATA
    # == gcc DWARF; idx33: the COUNT-fork row exists in both tables and
    # is sched_remote_wakeup at DATA (568, lsb 0) — no :0 slot anywhere.
    for i, (bf, po, dr) in BF_ROWS.items():
        d = D[i]
        assert d[4] is not None and tuple(d[4][:3]) == bf, \
            "row %d: DATA descriptor %s != gcc DWARF %s" % (i, d[4][:3], bf)
        assert P[i][2] == po, \
            "row %d: parser slot offset %d != measured %d" % (i, P[i][2], po)
    assert D[33][0] == "sched_remote_wakeup" and P[33][0] == D[33][0]
    # rejoin: idx118 thread at BOTH == gcc offsetof 1472
    assert P[118][2] == D[118][2] == GCC_THREAD_OFF
    # the :0 pad appears in NEITHER table (the count fork is gone):
    anon_bit = [i for i, d in enumerate(D)
                if d[0] is None and d[4] is not None]
    assert anon_bit == []


@needs_streams
def test_slot_pairing_on_the_thread_union(tmp_path):
    """union arms AGREE at base already (sims §1c) — pin it so the wave
    cannot move a union arm by accident: 2 slots, offsets 0/0, 16384."""
    clean = w1._clean_i(os.path.join(STREAMS, "init_init_task.c.i"),
                       tmp_path, "wae-pin-u")
    src = open(clean, encoding="utf-8", errors="replace").read()
    P, D, total = _tables(src, "thread_union", union=True)
    assert [s[0] for s in P] == [s[0] for s in D] == ["task", "stack"]
    # (THIS config's 5.10 arm is `struct task_struct task` — not the
    #  PREVAIL-config `thread_info` name; offsets/sizes are the law.)
    assert [s[2] for s in P] == [s[2] for s in D] == [0, 0]
    assert P[1][3] == 16384, "gcc sizeof(thread_union)=16384 (card 12816)"
    assert total == 16384


# ------------------------------------------------------------ SHAPES
def _shape(src, tag, expect_pairs, union=False):
    P, D, _tot = _tables(src, tag, union=union)
    _assert_pairing(P, D, drift=expect_pairs, tag=tag)
    return D


def test_shape_ae03_pad_between_bits():
    D = _shape("struct S { unsigned a:1; unsigned :0; unsigned b:1; };",
               "S", {})
    assert [d[0] for d in D] == ["a", "b"]          # the pad is NO slot
    assert D[0][4][:3] == (0, 0, 1) and D[1][4][:3] == (4, 0, 1)


def test_shape_pad_at_head():
    D = _shape("struct H { unsigned :0; unsigned a:1; int z; };", "H", {})
    assert [d[0] for d in D] == ["a", "z"] and D[1][2] == 4


def test_shape_pad_at_tail_and_doubled():
    D = _shape("struct T { unsigned a:1; int z; unsigned :0; };", "T", {})
    assert [d[0] for d in D] == ["a", "z"]
    D = _shape("struct D2 { unsigned a:1; unsigned :0; unsigned :0;"
               " int z; };", "D2", {})
    assert [d[0] for d in D] == ["a", "z"] and D[1][2] == 4


def test_shape_wide_cross_keeps_FIXG1_descriptors():
    D = _shape("struct W { unsigned a:31; unsigned b:3; int z; };", "W", {})
    assert D[0][4][:3] == (0, 0, 31) and D[1][4][:3] == (4, 0, 3)
    assert D[2][2] == 8


def test_shape_pad_inside_anon_union_inner_and_outer():
    D = _shape("union AU { unsigned u:2; unsigned :0; unsigned v:1; };",
               "AU", {}, union=True)
    assert [d[0] for d in D] == ["u", "v"]          # :0 consumes NO slot
    assert D[1][4][:3] == (0, 0, 1)                 # union arm: bit 0
    _shape("struct U { unsigned a:1; unsigned :0;"
           " union { unsigned u:2; unsigned :0; unsigned v:1; } au;"
           " int z; };", "U", {})


def test_shape_bits_mixed_with_arrays():
    D = _shape("struct A { unsigned f:1; int arr[3]; unsigned g:2; };",
               "A", {})
    assert [d[0] for d in D] == ["f", "arr", "g"]
    assert D[1][2] == 4 and D[1][3] == 12 and D[2][4][:3] == (16, 0, 2)


def test_shape_packed_pad_counts_agree_offsets_measured_drift():
    # The parser slot table does NOT pack: a packed struct carries a
    # MEASURED residual offset (z: P 8 vs DATA 5). Names/counts — the
    # pairing LAW — hold; the offsets are pinned as measured.
    _shape("struct __attribute__((packed)) Pk { unsigned a:1;"
           " unsigned :0; unsigned b:1; int z; };", "Pk", {2: 3})


# ------------------------------------------------------- ONE LAW, 2 HOMES
def _enclosing_def(src, idx):
    head = src[:idx]
    ms = list(re.finditer(r"def (_[a-z0-9_]+|[a-z0-9_]+)\(", head))
    return ms[-1].group(1) if ms else None


def test_the_width0_law_lives_in_exactly_two_homes():
    """The width-0 no-slot decision lives in the parser's _init_slots
    (ONE arm) and the data-side _struct_layout (union arm + struct arm).
    A THIRD home — even behaviorally identical — is the second mechanism
    this gate turns RED on."""
    d = os.path.join(REPO, "blcc")
    srcs = {f: open(os.path.join(d, f)).read()
            for f in ("parser.py", "types.py")}
    hits = [(f, m.start()) for f, s in srcs.items()
            for m in re.finditer(r'getattr\(m, "width", None\) == 0', s)]
    assert len(hits) == 1 and hits[0][0] == "parser.py" \
        and _enclosing_def(srcs["parser.py"], hits[0][1]) == "_init_slots", \
        "parser-side width-0 skip must live ONCE inside _init_slots: %s" % (
            hits,)
    hits = [(m.start()) for m in re.finditer(r"if w == 0:", srcs["types.py"])]
    assert len(hits) == 2 and all(
        _enclosing_def(srcs["types.py"], i) == "_struct_layout" for i in
        hits), "data-side w==0 arms must be the two _struct_layout arms: %s" \
        % (hits,)
    others = [f for f in sorted(os.listdir(d))
              if f.endswith(".py") and f not in ("parser.py", "types.py")]
    strays = [(f, m.start()) for f in others
              for m in re.finditer(r'width", None\) == 0',
                                   open(os.path.join(d, f)).read())]
    assert not strays, "a third width-0 home appeared: %s" % (strays,)
