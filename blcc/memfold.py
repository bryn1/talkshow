"""blcc/memfold.py — §2.17 mem* SIZE-CLASS INLINE FOLD (MC 12460 cycle-2,
stage T+8b). MC 12404.2.21 forbids a second tokenization; THIS is the
belt-side of the mem* law: every mem* call site is lowered to an inline
size-class expansion with ZERO callees (blcc's machine class is GP + x86
string ops only). WHY the belt and not a DCE: blcc never inlines and has
no dead-code elimination — the only way to guarantee a boot/vdso image
links `-z defs` clean (nm parity, §2.17 corollary) is to never EMIT the
symbol reference in the first place.

FOLD LAW (§2.17, gcc 11.4 -Os measured):
  __builtin_{memcpy,memset,memcmp,memmove} -> ALWAYS fold.
  plain memcpy/memset/memcmp/memmove      -> fold UNLESS the TU carries a
      visible DEFINITION of that name (lib/string.c's memcpy stays a
      function — the CALL path, never the fold).
  Size classes (GP widths 8/4/2/1, no SSE, no callee):
    memcpy/memmove CONST <=16  straight-line GP pairs (mov8 class);
    memcpy         CONST >16/VAR  rep movsb;
    memmove        CONST >16/VAR  direction test: fwd rep movsb, bwd loop;
    memset         CONST <=16  immediate stores (movq $0 class on zero);
    memset         CONST >16/VAR  fill byte + rep stosb;
    memcmp         every size   early-exit byte loop; result = UNSIGNED
      byte difference (glibc AND the kernel's own lib/string.c measured —
      FINDING c2-F2 against the contract's "signed" wording; oracle wins).
  Result contract: memcpy/memmove/memset yield dst (the standard value the
  RUN pairs pin, even though gcc -Os often leaves it undefined); memcmp
  the byte difference as a signed int.
  A fold-visible size that is negative or > 2^31 is a §5 LOUD wall (the
  oracle's own `size exceeds the implementation limit` family).

Split from expr_codegen.py (already over the 600-line cap; §4.1's module
plan gains this line); a MIXIN of ExprEmitter, so every emit helper
(_e/_t/_unt/_label/_fold_const/_err/_emit_expr, fn.lines) is self's.
"""
from __future__ import annotations

from blcc import predef
from blcc.lexer import DiagError

_SIZE_STORE = {8: "movq", 4: "movl", 2: "movw", 1: "movb"}


def _chunks(n: int):
    """Width decomposition 8 -> 4 -> 2 -> 1 as (offset, width) pairs."""
    out, off = [], 0
    for w in (8, 4, 2, 1):
        while n - off >= w:
            out.append((off, w))
            off += w
    return out


class MemFoldMixin:

    def _is_mem_fold(self, name: str) -> bool:
        if name in predef.MEM_FOLDS:
            return True
        # plain spelling: fold IFF no visible DEFINITION of it in this TU
        return name in predef.MEM_PLAIN and name not in self.funcs

    def _mem_fold(self, n) -> None:
        name = n.callee.name
        # the op is decided on the PLAIN tail: "__builtin_memset" and
        # "memset" land in the SAME size classes (§2.17 fold law)
        plain = name[len("__builtin_"):] if name.startswith("__builtin_") \
            else name
        is_cmp = plain == "memcmp"
        is_set = plain == "memset"
        is_mv = plain == "memmove"
        if len(n.args) != 3:
            self._err(n, "'{}' takes exactly 3 arguments (§2.17)".format(
                name), name)
        a_d, a_m, a_n = n.args
        self._emit_expr(a_d)                    # left-to-right (§2.12)
        t_d = self._t()
        self._e("movq %rax, {}".format(t_d))
        self._emit_expr(a_m)
        t_m = self._t()
        self._e("movq %rax, {}".format(t_m))
        self._emit_expr(a_n)
        t_n = self._t()
        self._e("movq %rax, {}".format(t_n))
        try:
            cn = self._fold_const(a_n, n)
        except DiagError:
            cn = None
        if cn is not None and (cn < 0 or cn > 2 ** 31):
            self._err(n, "mem* size constant {} exceeds the implementation "
                        "limit (§2.17)".format(cn), name)
        cf = None
        if is_set and cn is not None:
            try:
                cf = self._fold_const(a_m, n)
            except DiagError:
                cf = None
        if is_cmp:
            self._fold_memcmp(t_d, t_m, t_n, cn)
        elif is_mv:
            self._fold_memmove(t_d, t_m, t_n, cn)
        elif is_set:
            self._fold_memset(t_d, t_m, t_n, cn, cf)
        else:
            self._fold_memcpy(t_d, t_m, t_n, cn)
        if not is_cmp:
            self._e("movq {}, %rax".format(t_d))   # the standard dst value
        self._unt(3)

    # -- GP straight-line copy (mov8 class) --------------------------------

    def _copy_pairs(self, cn: int, down: bool = False) -> None:
        # byte-exact for any overlap direction when ordered; `down` =
        # descending offsets (the memmove backward-safe straight class).
        for off, w in (sorted(_chunks(cn), reverse=True) if down
                       else _chunks(cn)):
            if w == 8:
                self._e("movq {}(%rsi), %rax".format(off))
                self._e("movq %rax, {}(%rdi)".format(off))
            elif w == 4:
                self._e("movl {}(%rsi), %edx".format(off))
                self._e("movl %edx, {}(%rdi)".format(off))
            elif w == 2:
                self._e("movzwl {}(%rsi), %edx".format(off))
                self._e("movw %dx, {}(%rdi)".format(off))
            else:
                self._e("movzbl {}(%rsi), %edx".format(off))
                self._e("movb %dl, {}(%rdi)".format(off))

    # -- size classes ------------------------------------------------------

    def _fold_memcpy(self, td, ts, tn, cn) -> None:
        self._e("movq {}, %rdi".format(td))
        self._e("movq {}, %rsi".format(ts))
        if cn is not None and cn <= 16:
            self._copy_pairs(cn)
            return
        self._e(("movl ${}, %ecx".format(cn)) if cn is not None else
                "movq {}, %rcx".format(tn))
        self._e("rep movsb")

    def _fold_memset(self, td, tf, tn, cn, cf) -> None:
        self._e("movq {}, %rdi".format(td))
        if cn is not None and cn <= 16 and cf is not None:
            b = cf & 0xFF                        # memset fills (char)c
            for off, w in _chunks(cn):
                if b == 0:
                    self._e("{} $0, {}(%rdi)".format(_SIZE_STORE[w], off))
                elif w == 8:
                    self._e("movabsq $0x{:x}, %rax".format(
                        b * 0x0101010101010101))
                    self._e("movq %rax, {}(%rdi)".format(off))
                elif w == 4:
                    v = b * 0x01010101
                    self._e("movl ${}, {}(%rdi)".format(
                        v if v < 2 ** 31 else v - 2 ** 32, off))
                elif w == 2:
                    v = b * 0x0101
                    self._e("movw ${}, {}(%rdi)".format(
                        v if v < 2 ** 15 else v - 2 ** 16, off))
                else:
                    self._e("movb ${}, {}(%rdi)".format(
                        b if b < 128 else b - 256, off))
            return
        if cf is not None:
            self._e("movabsq $0x{:x}, %rax".format(
                (cf & 0xFF) * 0x0101010101010101))
        else:
            self._e("movq {}, %rax".format(tf))  # only %al matters
        self._e(("movl ${}, %ecx".format(cn)) if cn is not None else
                "movq {}, %rcx".format(tn))
        self._e("rep stosb")

    def _fold_memcmp(self, td, ts, tn, cn) -> None:
        self._e("movq {}, %rdi".format(td))
        self._e("movq {}, %rsi".format(ts))
        self._e(("movl ${}, %ecx".format(cn)) if cn is not None else
                "movq {}, %rcx".format(tn))
        lab = self._label("mc")
        # early-exit byte loop; result = UNSIGNED byte difference (the
        # glibc AND lib/string.c value; FINDING c2-F2 — contract says
        # "signed", the oracle-measured answer is unsigned).
        self.fn.lines.append("{}l:".format(lab))
        self._e("testq %rcx, %rcx")
        self._e("je {}e".format(lab))
        self._e("movzbl (%rdi), %eax")
        self._e("movzbl (%rsi), %edx")
        self._e("cmpl %edx, %eax")
        self._e("jne {}n".format(lab))
        self._e("incq %rdi")
        self._e("incq %rsi")
        self._e("decq %rcx")
        self._e("jmp {}l".format(lab))
        self.fn.lines.append("{}n:".format(lab))
        self._e("subl %edx, %eax")
        self._e("movslq %eax, %rax")             # int result, sign-kept
        self._e("jmp {}d".format(lab))
        self.fn.lines.append("{}e:".format(lab))
        self._e("xorl %eax, %eax")
        self.fn.lines.append("{}d:".format(lab))

    def _fold_memmove(self, td, ts, tn, cn) -> None:
        self._e("movq {}, %rdi".format(td))
        self._e("movq {}, %rsi".format(ts))
        lab = self._label("mm")
        self._e("cmpq %rsi, %rdi")
        self._e("jb {}f".format(lab))            # dst below src: forward
        # ---- backward path (dst >= src: copy from the tail) ----
        if cn is not None and cn <= 16:
            self._copy_pairs(cn, down=True)
            self._e("jmp {}d".format(lab))
        else:
            self._e(("movl ${}, %ecx".format(cn)) if cn is not None else
                    "movq {}, %rcx".format(tn))
            self.fn.lines.append("{}b:".format(lab))
            self._e("testq %rcx, %rcx")
            # DONE jumps to the END label — NOT to `f`: the fwd block
            # RELOADS %rcx from the size slot and a rcx==0 fall-through
            # would run rep movsb with the FULL count over the already
            # backward-copied region (T+8b: TDD found, mv leg RED).
            self._e("je {}d".format(lab))
            self._e("decq %rcx")
            self._e("movzbl (%rsi,%rcx), %eax")
            self._e("movb %al, (%rdi,%rcx)")
            self._e("jmp {}b".format(lab))
        # ---- forward path ----
        self.fn.lines.append("{}f:".format(lab))
        if cn is not None and cn <= 16:
            self._copy_pairs(cn)
        else:
            self._e(("movl ${}, %ecx".format(cn)) if cn is not None else
                    "movq {}, %rcx".format(tn))
            self._e("rep movsb")
        self.fn.lines.append("{}d:".format(lab))
