"""blcc/parse_fold.py — THE parse-side constant-fold kernel, one home
(MC 12775 clean-code split of parser.py; methods MOVED VERBATIM — zero
behavior change). ParseFoldMixin rides blcc.parser.Parser. fold_truthy is
the arithmetic/sizeof/comparison kernel the kernel's __inttype/__typefits
controls need; None = NOT foldable here and the caller LOUDs (never
silently chooses). The bswap arm rides the ONE types.bswap_const home
(MC 12774 AM31 law). The WIDTH/WRAP answer-surface is deliberately NOT
here: the parse kernel keeps its refuse-posture — the sealed door law is
pinned by test_parse_time_fold_door_is_a_different_door (D2/L-1, LEDGER
continuation row tracks the consolidation candidate).
"""
from __future__ import annotations

from typing import Optional

from blcc import ast


class ParseFoldMixin:
    def _fold_const(self, n, at) -> int:
        # the fold-side constant law IS fold_truthy; None = the caller's
        # LOUD (a non-constant size can never have been compatible).
        v = self.fold_truthy(n)
        if v is None:
            self._sema(at, "array size in a type-identity comparison is "
                       "not an integer constant (§4)")
        return v

    def fold_truthy(self, node: ast.Node) -> Optional[int]:
        """The arithmetic/sizeof/comparison kernel needed by the kernel's
        `__inttype`/`__typefits` controls (`sizeof(x) <= sizeof(type)` and
        nested arithmetic on literals/enums). Returns None when the control
        is NOT foldable here — the caller LOUDs, never silently chooses."""
        if isinstance(node, ast.IntLit):
            return node.value
        if isinstance(node, ast.CharLit):
            return node.value - 256 if node.value > 127 else node.value
        if isinstance(node, ast.Ident):
            sym = self.lookup(node.name)
            if sym is not None and sym[0] == "enum":
                return sym[1]
            return None
        if isinstance(node, ast.Unary) and node.op in ("-", "+", "!", "~"):
            v = self.fold_truthy(node.operand)
            if v is None:
                return None
            if node.op == "-":
                return -v
            if node.op == "~":
                v = self.fold_truthy(node.operand)
                if v is None:
                    return None
                v = ~v & 0xFFFFFFFFFFFFFFFF
                return ((v + 2 ** 63) % 2 ** 64) - 2 ** 63
            if node.op == "!":
                return 0 if v else 1
            return v
        if isinstance(node, ast.Cast):
            return self.fold_truthy(node.operand)
        if isinstance(node, ast.Cond):
            # §1c (MC 12486): constant `?:` folds — TEST first, then ONLY
            # the chosen arm (C11 6.6: the dead arm need not be constant).
            v = self.fold_truthy(node.test)
            if v is None:
                return None
            if node.gnu:
                return v if v != 0 else self.fold_truthy(node.arm2)
            return self.fold_truthy(node.arm1 if v != 0 else node.arm2)
        if isinstance(node, ast.Sizeof):
            if node.typ is not None:
                return self._csize(node.typ)
            if isinstance(node.arg, ast.StrLit):
                # M4 W-J (MC 12655): sizeof("abcd") == 5 — the corpus's
                # 22-stream SA string-size law (`sizeof("softdep_update")
                # - 1 <= (64 - sizeof(unsigned long))`). StrLit.value is
                # DECODED (§4: bytes are rodata's concern); sizeof sees
                # the char[N] type WITHOUT decay — N = bytes + NUL.
                return len(node.arg.value.encode("utf-8")) + 1
            ty = self.expr_type(node.arg)
            return self._csize(ty) if ty is not None else None
        if isinstance(node, ast.Alignof):
            # M4 W2.5 (MC 12557): the alignof mirror of the SAME layout
            # law — `_calign` is the shipped §2.13/offsetof mirror.
            if node.typ is not None:
                return self._calign(node.typ)
            ty = self.expr_type(node.arg)
            return self._calign(ty) if ty is not None else None
        if (isinstance(node, ast.Call)
                and isinstance(node.callee, ast.Ident)
                and node.callee.name == "__builtin_types_compatible_p"):
            # M4 W-L (MC 12665): BUILD_BUG_ON_ZERO feeds the bitfield
            # width from the §2.12 identity law — the SAME
            # `_types_compatible` text codegen folds (CompatLawMixin),
            # now answering at PARSE. A TYPE that cannot materialize
            # folds NOT-compatible (0): the safe direction, pinned by
            # the truth-table leg.
            if len(node.args) != 2:
                return None
            return 1 if self._types_compatible(node.args[0],
                                               node.args[1]) else 0
        if (isinstance(node, ast.Call)
                and isinstance(node.callee, ast.Ident)
                and node.callee.name in ("__builtin_bswap16",
                                         "__builtin_bswap32",
                                         "__builtin_bswap64")
                and len(node.args) == 1):
            # M4 W-Z COMMIT-CL (MC 12774): the byte-swap of a constant IS
            # a constant expression — the post-pp kernel feeds case labels
            # the htons-of-constant expansion `case (( __be16)(__u16)
            # __builtin_bswap16((__u16)((0x0800))):` (the WALK wall
            # netdevice.h:4798, the 11-stream corpus crowd, all one
            # byte-identical construct). The swap rides types.bswap_const
            # — the SAME home the codegen door uses (one law, two doors;
            # AM31). None (LOUD) for a non-constant operand — cl14
            # measured gcc refusing at exactly that shape too.
            from blcc.types import bswap_const
            v = self.fold_truthy(node.args[0])
            if v is None:
                return None
            return bswap_const(node.callee.name, v)
        if isinstance(node, ast.Binary):
            op = node.op
            if op in ("&&", "||"):                      # short-circuit
                a = self.fold_truthy(node.left)
                if a is None:
                    return None
                if op == "&&" and a == 0:
                    return 0
                if op == "||" and a != 0:
                    return 1
                return self.fold_truthy(node.right)
            a = self.fold_truthy(node.left)
            b = self.fold_truthy(node.right)
            if a is None or b is None:
                return None
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/" and b != 0:
                q = abs(a) // abs(b)
                return -q if (a < 0) != (b < 0) else q
            if op == "%" and b != 0:
                q = abs(a) // abs(b)
                if (a < 0) != (b < 0):
                    q = -q
                return a - b * q
            if op in ("<<", ">>"):
                if b < 0 or b > 63 or a is None:
                    return None
                v = (a << b) & 0xFFFFFFFFFFFFFFFF if op == "<<" \
                    else a >> b
                return ((v + 2 ** 63) % 2 ** 64) - 2 ** 63
            if op in ("|", "&", "^"):
                if a is None or b is None:
                    return None
                v = (a | b) if op == "|" else \
                    ((a & b) if op == "&" else (a ^ b))
                return ((v + 2 ** 63) % 2 ** 64) - 2 ** 63
            if op == "<":
                return 1 if a < b else 0
            if op == "<=":
                return 1 if a <= b else 0
            if op == ">":
                return 1 if a > b else 0
            if op == ">=":
                return 1 if a >= b else 0
            if op == "==":
                return 1 if a == b else 0
            if op == "!=":
                return 1 if a != b else 0
            return None
        return None
