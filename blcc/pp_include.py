"""blcc/pp_include.py — THE include-search law, one home (MC 12775
clean-code split of preproc.py, methods MOVED VERBATIM — zero behavior
change). IncludeMixin rides blcc.preproc.Preprocessor (the same mixin
idiom as blcc/memfold.py): operand parsing, the measured search order and
-include ordering (R17/G1-G11), the reopen-exactly-once cycle law (R20),
and the depfile OBJECT law (one object per (fname, start_dir), chain-head
sharing, emit-once-at-first-open). Needs only the Preprocessor state:
opts/stack/deps/_dep_objs/expander/_text/_warn/_read/_process.
"""
from __future__ import annotations

import os
from typing import List, Tuple

from blcc.lexer import DiagError
from blcc.pp_text import _spell

_MAX_INCLUDE_DEPTH = 200         # mirrors gcc's default -fmax-include-depth       # mirrors gcc's default -fmax-include-depth


class IncludeMixin:
    def _include_line(self, label, ln, toks, base_dir) -> None:
        operand = self._text(toks).strip()
        if operand[:1] not in ('"', "<"):
            # C11 6.10.3 / gcc (MC 12438, the 37-file class): the operand is
            # macro-EXPANDED before the filename is parsed — every kernel TU
            # that #defines CREATE_TRACE_POINTS reaches define_trace.h's
            # `#include TRACE_INCLUDE(TRACE_INCLUDE_FILE)` through this
            # path. The SHIPPED expander does the rescan (one mechanism,
            # F-3's); an operand that expands to garbage stays LOUD here —
            # _include's parser never defaults to silence.
            toks = self.expander.expand(toks, label, ln)
            operand = self._text(toks).strip()
        self._include(label, ln, operand, base_dir=base_dir)

    def _include(self, path: str, ln: int, operand: str,
                 base_dir=".", preinclude: bool = False) -> None:
        if not operand:
            raise DiagError("pp", path, ln, 1,
                            '#include expects "FILENAME" or <FILENAME>',
                            "#include")
        if operand[0] == "<":
            end = operand.find(">")
            if end < 0:
                raise DiagError("pp", path, ln, 1, "malformed #include",
                                "#include " + operand)
            target = operand[1:end]
            angle = True
            tail = operand[end + 1:]
        elif operand[0] == '"':
            end = operand.find('"', 1)
            if end < 0:
                raise DiagError("pp", path, ln, 1,
                                "malformed #include: expected \"quoted.h\"",
                                "#include " + operand)
            target = operand[1:end]
            angle = False
            tail = operand[end + 1:]
        else:
            # gcc 11.4 (measured): error, rc 1. Loud, never silent.
            raise DiagError("pp", path, ln, 1,
                            '#include expects "FILENAME" or <FILENAME>',
                            "#include " + operand)
        if tail.strip():
            # oracle rc 0 + warning "extra tokens at end of #include
            # directive" — the file is STILL included (MC 12438 pin).
            self._warn(path, ln, 1, "extra tokens at end of #include "
                                    "directive")
        if not target:
            raise DiagError("pp", path, ln, 1, "empty #include path",
                            "#include " + operand)
        # M4 W4-fix (MC 12586) — the SPELLING law is gcc's
        # append_file_to_dir (libcpp/files.c, read + measured this
        # session): dir + '/' (ONLY when the dir lacks a trailing
        # separator) + the raw name, NEVER normalized; the .d drops a
        # LEADING "./" component only (measured: -I. -> n.h,
        # -I./inc -> inc/n.h, -include ./n.h -> n.h), while `../`,
        # `//` and mid-path `./` ride RAW (F-2: gcc spells
        # inc/sub/../n.h and inc/sub//z.h; the W4 normpath collapse
        # was the 37/705 universe divergence). System law unchanged:
        # only an -isystem-directory match is a SYSTEM event (the
        # measured MMD/MD boundary; -I-found `<>` includes are USER).
        # -include (R17) keeps its measured order (verdict-c1 Leg 4,
        # rows G1-G11): the operand AS-GIVEN first (gcc: the shared
        # "./" cmdline dir — a relative name answers to the CWD), then
        # every -I dir in order, then every -isystem dir. The includer
        # (main file's) directory is NEVER searched for -include: that
        # is the quoted-#include rule, not this one.
        def _join(dirp: str) -> str:
            if not dirp or dirp.endswith("/"):
                return dirp + target
            return dirp + "/" + target

        def _chain() -> List[Tuple[str, bool]]:
            out = [(_join(d), False) for d in self.opts.includes_dir]
            out += [(_join(d), True) for d in self.opts.isystem]
            return out

        if os.path.isabs(target):
            # libcpp: an absolute operand searches NO chain
            # (no_search_path) — its object key is the name alone.
            cand, key_start = [(target, False)], None
            key_chain = ("A", target)
        elif preinclude:
            cand, key_start = [(target, False)] + _chain(), ("P", target)
            key_chain = ("C", target)
        elif angle:
            cand, key_start = _chain(), ("C", target)
            key_chain = None
        else:
            cand, key_start = [(_join(base_dir), False)] + _chain(), \
                ("D", base_dir, target)
            key_chain = ("C", target)
        hit = next((cd for cd in cand if os.path.isfile(cd[0])), None)
        full = hit[0] if hit else None
        shown = "#include %s" % operand
        if full is None:
            raise DiagError("pp", path, ln, 1, "no such file or directory",
                            shown)
        resolved = os.path.abspath(full)
        # gcc RE-OPENS a file that is already on the active stack: its
        # include guard (already defined) skips the body, so a guarded
        # re-entrant chain (uapi/linux/timex.h <-> linux/time.h — the
        # 676-file corpus wall, verdict-c2 F-1) is NORMAL and terminates.
        # A SECOND entry for the same file while one is still active can
        # only come from a body that re-executes — a true cycle — and
        # stays loud (the oracle dies too: its depth-200 cap). This is the
        # rule the oracle + the M20 diamond + the unguarded a<->b fixture
        # jointly force (MC 12436); the diamond re-read never sees the
        # file on the stack at all.
        if self.stack.count(resolved) >= 2:
            raise DiagError("pp", path, ln, 1,
                            "include cycle detected for '%s'" % full, shown)
        if len(self.stack) >= _MAX_INCLUDE_DEPTH:
            raise DiagError("pp", path, ln, 1,
                            "#include nested depth %d exceeds maximum of %d "
                            "(use -fmax-include-depth=DEPTH to increase the "
                            "maximum)" % (_MAX_INCLUDE_DEPTH,
                                          _MAX_INCLUDE_DEPTH), shown)
        # THE depfile OBJECT law, ported from gcc-11 libcpp/files.c
        # (_cpp_find_file + _cpp_stack_file, source read AND gcc 11.4
        # measured this session — gate F-1): ONE object per (fname
        # string, start_dir), with cache SHARING at the (quote≡bracket)
        # search-chain head, and the .d emits file->path EXACTLY ONCE
        # per object, at its FIRST OPEN. start_dir is hashed as a
        # STRING (make_cpp_dir): the quoted include's includer-dir raw
        # prefix — "" != "./" != "d1/", so the same NAME resolving to
        # DIFFERENT files from two includer dirs is TWO objects (the
        # W4 (name,kind) key over-collapsed exactly that). The chain is
        # ONE shared key ("C"); -include rides the shared "./" cmdline
        # key ("P"); an absolute operand never shares ("A"). A miss at
        # the start dir that finds THROUGH THE CHAIN registers the
        # chain key too (a later angle lookup then SHARES, no re-emit
        # — the TA/TB probes); a find AT the start dir registers only
        # the start key (I1: no chain sharing for own-dir hits); a
        # start-key re-open never re-emits, guarded or not (measured:
        # guarded "hd.h" + <hd.h> = 2 lines; <empty.h> twice = 1). This
        # is the 729-line kernel/exit.c witness law (test_depfile_m4.py
        # golden replay): the msr-index/kconfig/compiler_types/
        # taskstats duplicate pairs are different NAMES; types.h's
        # 100+ same-name angle includers ride once on the chain key.
        if key_start is None or key_chain is None:
            obj_key = key_chain if key_start is None else key_start
            emit = obj_key not in self._dep_objs
            self._dep_objs.add(obj_key)
        elif key_start in self._dep_objs:
            emit = False                          # cache hit at start
        elif hit is cand[0]:
            emit = True                           # fresh AT the start
            self._dep_objs.add(key_start)
        elif key_chain in self._dep_objs:
            emit = False                          # shared via chain head
            self._dep_objs.add(key_start)         # gcc caches start too
        else:
            emit = True                           # fresh via the chain
            self._dep_objs.add(key_start)
            self._dep_objs.add(key_chain)
        if emit:
            self.deps.append((_spell(full), hit[1]))
        self._process(full, self._read(full))
