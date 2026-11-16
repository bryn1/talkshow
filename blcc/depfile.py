"""M4 W4 — THE depfile writer (plan-m4.md v4 §4.3/§4.4, MC 12581).

ONE writer for the ONE `-Wp,-MMD,` channel (plan §4.4 law: "blcc preproc
grows the ONE -Wp,-MMD, writer in W4, reusing the same resolver, never a
second one"). The prerequisite EVENTS come from the M1 include resolver
(Preprocessor.deps — the same _include() that reads the file records the
event); this module only parses the -Wp spelling and RENDERS gcc's
measured .d shape. The driver calls write() right after
preprocess_file() returns.

MEASURED LAWS (gcc 11.4 this session; kernel witness = the REAL kbuild
argv on kernel/exit.c through a 5.10 O= objtree, 729 lines, captures
.tmp/m4-w4/out/witness-* + out/ lab probes):

  * WHEN: the .d is written when PREPROCESSING ENDS — gcc writes it even
    when the compile later fails (probe: .d exists at rc 1 after a
    post-pp error), and a pp-phase failure writes NOTHING. -E honors it
    too (fe.d measured). So the write sits between pp and lex: on any
    later diagnostic the .d STAYS (kbuild law: fixdep only runs after a
    successful recipe, §4.3) while the -o object is unlinked (§3.5 law).
  * SHAPE: `TARGET: dep...` with gcc's column wrap: a dep rides the
    CURRENT line iff the line stays <= 73 columns (`_WRAP_MAX`);
    otherwise ` \\` + newline ends the line and the dep rides fresh.
    Every dep is space-prefixed; the LAST dep is bare (no trailing
    space); the file ends '\\n'. The kernel witness wrapped one dep per
    line because every absolute path overflowed the budget; short paths
    PACK on one line (bisected byte-exact probes, wrap/).
  * TARGET: -MT/`-MQ spellings ACCUMULATE, space-joined before the colon
    (`a b.o real2.o:` — spaces NOT escaped in the target); both ride RAW,
    unescaped. With neither: basename of the SOURCE stem + '.o' — the -o
    operand is NOT used (measured: `-c sub/abc.c -o zz.o` -> `abc.o:`;
    same law under -E with or without -o). kbuild always spells
    -Wp,-MT,<basename> (basename_flags), so real traffic never hits the
    default; bare -MD/-MT/-MF driver forms are out of W4's scope — the
    wrapper REJECT-LOUDs them (kbuild 5.10 spells none of them).
  * PREREQS: include-EVENT order (DFS open order): the main source FIRST
    (fixdep's source_ law depends on it), then -include operands in argv
    order, then every resolved #include AT RESOLUTION, repeats included.
    No second walk, no re-sort, no dedup sweep at render time.
   * WHICH EVENTS — the libcpp OBJECT law, ported from gcc-11
     libcpp/files.c (source read) AND measured on gcc-11.4 (M4 W4-fix,
     MC 12586): _cpp_find_file keeps ONE _cpp_file per (fname STRING,
     start_dir) with cache SHARING at the (quote-equal-bracket) chain
     head; _cpp_stack_file emits file->path EXACTLY ONCE, at the
     object's FIRST OPEN. blcc object keys: 'D' = quoted, keyed by the
     INCLUDER'S DIR RAW PREFIX (make_cpp_dir hashes the string:
     "" != "./" != "d1/" — the same quoted NAME resolving to
     DIFFERENT files from two includer dirs emits BOTH, gate F-1);
     'C' = the ONE shared chain key (angle lookups AND the chain-head
     cache every quoted walk passes — a name first found THROUGH the
     chain rides once even when later re-included angle-wise); 'P' =
     -include (gcc's shared "./" cmdline dir); 'A' = absolute operand,
     never shares. A fresh own-dir find registers ONLY its start key
     (no chain sharing); a fresh chain find registers start+chain; a
     chain-head hit re-registers the start. Guards and file emptiness
     play NO role (measured: guarded "hd.h" + <hd.h> = 2 lines;
     <empty.h> twice = 1). Paths ride RAW spellings (PREREQS below);
     leading "./" components drop. The 729-line kernel/exit.c witness
     replays dep-for-dep IN ORDER (build/replay-exit.d vs
     out/witness-exit-MMD.d) — msr-index/kconfig/compiler_types/
     taskstats duplicate pairs are distinct NAMES; types.h's 100+
     same-name angle includers ride once on the chain key. No second
     walk, no re-sort, no render-time sweep.
  * MMD vs MD: MMD omits SYSTEM events, MD keeps them (measured:
    -isystem-dir headers and /usr/include/* vanish under -MMD, return
    under -MD). SYSTEM == the event resolved through an -isystem dir;
    blcc has no default system dirs, so a `<>`-include found via -I is
    USER and stays (measured). -include resolves system when the file is
    FOUND via an -isystem dir (measured: -include sysh.h -isystem sys ->
    absent from MMD).
  * ESCAPE (prereqs only): ' ' -> '\\ ', '#' -> '\\#' (measured
    `sp ace/has#space.h` -> `sp\\ ace/has\\#space.h`); ':' NOT escaped.
    fixdep treats a backslash as whitespace, so a spaced path is broken
    for KBUILD itself — mirrored, not hidden.
  * -MF redirects the depfile path (t3 not written, t4 held the deps).
    -MD/-MMD/-MF without a file operand, and ANY other -Wp subflag, is
    REJECT-LOUD rc 2 naming the token (the W0 never-silent posture;
    kbuild spells only -Wp,-MMD,<file>, comma-free by $(comma)-subst).
"""
from __future__ import annotations

import os
from typing import List, Optional

FORWARD = ("-MD", "-MMD", "-MF", "-MT", "-MQ")


def is_forwardable(token: str) -> bool:
    """The wrapper's gate for the FIVE depfile subflags — exactly one
    comma, a known flag, a non-empty operand (a comma INSIDE the name
    would make it 3+ parts: gcc's own comma split would mis-pair it too,
    so it is not forwardable and stays REJECT-LOUD)."""
    if not token.startswith("-Wp,"):
        return False
    parts = token[4:].split(",")
    return len(parts) == 2 and parts[0] in FORWARD and parts[1] != ""


class Deps:
    """Parsed -Wp state (LAST -MD/-MMD/-MF wins; -MT/-MQ accumulate)."""

    def __init__(self) -> None:
        self.mode: Optional[str] = None      # "MD" | "MMD" | None
        self.file: Optional[str] = None      # path from -MD/-MMD
        self.mf: Optional[str] = None        # -MF redirect
        self.targets: List[str] = []         # -MT/-MQ spellings, raw

    def active(self) -> bool:
        return self.mode is not None

    def wants_system(self) -> bool:
        return self.mode == "MD"

    def depfile_path(self) -> Optional[str]:
        return self.mf if self.mf is not None else self.file


def parse_wp(argv: List[str]) -> Deps:
    """Parse every -Wp, token (argv is exec-level, never whitespace-split;
    plan §3.2 L1). ValueError names the offending token — the caller turns
    it into the §8 rc 2. Comma split is EXACT: one operand per subflag."""
    d = Deps()
    for a in argv:
        if not a.startswith("-Wp,"):
            continue
        parts = a[4:].split(",")
        flag = parts[0]
        if len(parts) != 2 or flag not in FORWARD or not parts[1]:
            raise ValueError(a)
        if flag == "-MF":
            d.mf = parts[1]
        elif flag in ("-MT", "-MQ"):
            d.targets.append(parts[1])
        elif flag in ("-MD", "-MMD"):
            d.mode = flag[1:]
            d.file = parts[1]
    return d


def _esc(dep: str) -> str:
    return dep.replace(" ", "\\ ").replace("#", "\\#")


# Measured wrap column (gcc 11.4, wrap/ bisect this session): a dep is
# appended to the CURRENT line iff the resulting line would stay <= 73
# columns — a candidate that would make it 74+ rides a fresh line after
# ' \\\n '. A single dep longer than the budget still rides its own full
# line (witness line lengths reach 95); the TARGET: line follows the same
# law (short paths PACK: `q.o: q.c short.h` one line; the boundary 73/74
# bisected on byte-exact probes, wraps at 74).
_WRAP_MAX = 73


def default_target(src: str) -> str:
    """The measured no--MT target: the source's BASENAME with the suffix
    swapped for '.o' — never the -o operand (`sub/abc.c -o zz.o` ->
    `abc.o:`, probe dd1/dd2)."""
    base = os.path.basename(src)
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return stem + ".o"


def render(targets: List[str], src: str, deps: List[str]) -> str:
    """The exact byte shape measured from gcc (see module docstring)."""
    target = " ".join(targets) if targets else default_target(src)
    out = [target + ":"]
    pos = len(out[0])
    for dep in deps:
        e = _esc(dep)
        if pos + 1 + len(e) > _WRAP_MAX:
            out.append(" \\\n")
            pos = 0
        out.append(" " + e)
        pos += 1 + len(e)
    out.append("\n")
    return "".join(out)


def write(path: str, targets: List[str], o_operand: str,
          deps: List[str]) -> None:
    """Write the depfile IN ONE fopen('w') pass like gcc: the file ends up
    complete or the caller's diagnostic fires; kbuild/fixdep read it only
    after the recipe exits 0 (§4.3)."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(targets, o_operand, deps))
