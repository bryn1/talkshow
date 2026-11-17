# LINES reason: the declaration grammar and the §5 construct diagnostics it
# must enforce are one concern; splitting them would duplicate the scope logic.
"""Declarations + statements parser for blcc (ARCHITECTURE.md §3) + light sema.

Concerns: scopes/symbols, the declaration grammar (functions, variables,
structs, enums, typedefs), every §4 statement, and the §5 "loud diagnostic
naming the construct" rejections. Expression grammar lives in
expr_parser.py; type SIZING is codegen's (§4 table), never done here.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from blcc import ast, predef
from blcc.lexer import DiagError, Lexer, SourceLine, Token, TokenStream
from blcc.expr_parser import ExprParser
from blcc.asmstmt import AsmParseMixin
from blcc.runtime import BUILTINS as _RUNTIME_BUILTINS

# §6 implicit builtins: always callable, never re-declarable. The NAME set is
# DERIVED from blcc/runtime.py's BUILTINS — one table, no mirrored list (P3-4).
BUILTINS = frozenset(_RUNTIME_BUILTINS)

_TYPE_KW = ("char", "short", "int", "long", "void")
_QUAL_WORDS = {"const": "const", "volatile": "volatile",
               "__volatile__": "volatile", "restrict": "restrict",
               "__restrict": "restrict", "__restrict__": "restrict"}

_DECL_START_KW = _TYPE_KW + ("const", "struct", "enum", "static", "typedef",
                             "extern", "float", "double", "union", "unsigned",
                             # M4 W2 COMMIT-0 (MC 12545): `_Bool` opens a
                             # declaration like any other type keyword.
                             "_Bool",
                             # M4 W-B (MC 12596): so does `__int128`.
                             "__int128",
                             # M2: the extended specifier vocabulary (§4.1a)
                             "signed", "__signed__", "__signed", "register",
                             "inline", "__inline__", "__inline", "volatile",
                             "__volatile__", "restrict", "__restrict",
                             "__restrict__", "typeof", "__typeof__",
                             "__typeof", "__extension__",
                             # M4 W-H (MC 12645): opens a declaration —
                             # parse_decl intercepts it BEFORE any base
                             # type walk (it is NOT a base-type word).
                             "__auto_type")


class Parser(AsmParseMixin):
    _STMT_HANDLERS = {"if": "parse_if", "while": "parse_while",
                      "do": "parse_do_while", "for": "parse_for",
                      "switch": "parse_switch", "case": "parse_nested_label",
                      "default": "parse_nested_label",
                      "__label__": "parse_label_decl",
                      # M3 §3 L0: the asm statement family (the lexer
                      # already spells asm/__asm__ as keywords).
                      "asm": "parse_asm_statement",
                      "__asm__": "parse_asm_statement"}

    def __init__(self, toks: List[Token]):
        self.s = TokenStream(toks)
        self.scopes: List[Dict[str, tuple]] = [{}]
        # §2.7: `__builtin_va_list` is supplied by the COMPILER (the .i
        # stream only carries `typedef __builtin_va_list va_list;`).
        self.scopes[0]["__builtin_va_list"] = ("typedef",
                                               predef.VA_LIST_TY)
        # M4 W-B (MC 12596): gcc's x86-64 target predefines
        # `__int128_t`/`__uint128_t` as BUILTIN TYPEDEFS (measured: decl
        # rc 0, sizeof 16; `unsigned __int128_t` is a parse ERROR — the
        # typedef law, not keyword commutation). Kernel census: 0 sites
        # (the kernel spells the keywords), but the names are
        # compiler-supplied — same §2.7 mechanism as __builtin_va_list.
        self.scopes[0]["__int128_t"] = ("typedef", ast.BuiltinType(
            "<predefined>", 0, 0, "__int128"))
        self.scopes[0]["__uint128_t"] = ("typedef", ast.BuiltinType(
            "<predefined>", 0, 0, "unsigned __int128"))
        self.struct_tags: Dict[str, Tuple[ast.Member, ...]] = {
            predef.TAG: predef.VA_MEMBERS}
        self._anon_n = 0                  # unique minted-tag counter (T+7)
        # M4 W3 COMMIT-0 (MC 12563): the re-declaration ledger — name →
        # (return key, param key list or None for the old-style empty
        # list, variadic). ONE table, judged by _fn_redecl_law.
        self.fn_decls: Dict[str, Tuple] = {}
        self._pending: List[ast.Node] = []  # Struct/EnumDecls made by types
        self._bare_type_ok = False          # a tag/enum definition just read
        self.switch_depth = 0
        self.expr = ExprParser(self.s, self.is_typename, self.parse_type,
                               self.callable_known, self.expr_type,
                               self.parse_stmt_expr, self.fold_truthy,
                               self.resolve_offsetof,
                               parse_init=self.parse_initializer,
                               norm_init=self._norm_init,
                               objsize=self.resolve_objsize)

    # -- §2.4 GNU statement-expressions (M2-C5 leg 1) ------------------------

    def parse_stmt_expr(self, open_tok: Token) -> ast.Node:
        """`({ stmts… final; })` — the primary already consumed `(` AND
        verified `{` opens the braced group; it is consumed here."""
        self.s.expect_punct("{")
        self.scopes.append({})
        stmts: List[ast.Node] = []
        while not self.s.at_punct("}"):
            if self.s.peek().kind == "eof":
                self._parse_err(open_tok, "unterminated statement expression")
            stmts.extend(self.parse_block_item())
        self.scopes.pop()
        self.s.expect_punct("}")
        self.s.expect_punct(")")
        value = None
        if stmts:
            # The final statement may carry LABELS (`h: (unsigned long)&&h;`
            # — kernel.h `_THIS_IP_`): the expression is still the value;
            # the label chain is rebuilt around an empty statement so the
            # label's address points AT the value's position.
            chain: List[ast.Node] = []
            cur = stmts[-1]
            while isinstance(cur, ast.Label):
                chain.append(cur)
                cur = cur.stmt
            if isinstance(cur, ast.ExprStmt) and cur.expr is not None:
                value = cur.expr
                tail = ast.ExprStmt(cur.file, cur.line, cur.col, None)
                for lab in reversed(chain):
                    tail = ast.Label(lab.file, lab.line, lab.col, lab.name,
                                     tail)
                stmts = stmts[:-1] + [tail]
        return ast.StmtExpr(open_tok.file, open_tok.line, open_tok.col,
                            tuple(stmts), value)

    # -- §2.6 __builtin_choose_expr control folding (M2-C5 leg 4) ------------

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
            ty = self.expr_type(node.arg)
            return self._csize(ty) if ty is not None else None
        if isinstance(node, ast.Alignof):
            # M4 W2.5 (MC 12557): the alignof mirror of the SAME layout
            # law — `_calign` is the shipped §2.13/offsetof mirror.
            if node.typ is not None:
                return self._calign(node.typ)
            ty = self.expr_type(node.arg)
            return self._calign(ty) if ty is not None else None
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

    def _calign(self, ty) -> Optional[int]:
        """alignof mirror of TypeMap._align (scalars by size, arrays by
        element, structs by widest member) for the §2.13 fold."""
        from blcc.types import TYPE_SIZE
        if ty is None:
            return None
        while isinstance(ty, ast.Qualified):
            ty = ty.inner               # `const insn_attr_t tab[]` — the
            #                              §1 row 10 walk hit the missing
            #                              arm (pre-existing mirror gap)
        if isinstance(ty, ast.BuiltinType):
            return TYPE_SIZE.get(ty.name)
        if isinstance(ty, ast.PtrType):
            return 8
        if isinstance(ty, ast.ArrayType):
            return self._calign(ty.inner)
        if isinstance(ty, ast.TypeOf):
            inner = ty.typ if ty.typ is not None else (
                self.expr_type(ty.expr) if ty.expr is not None else None)
            return self._calign(inner)
        if isinstance(ty, ast.StructType):
            members = self.struct_tags.get(ty.tag)
            if members is None:
                return None
            packed = self._attr_packed(ty)
            a = 1
            for m in members:
                if getattr(m, "width", None) is not None:
                    # §1 row 12 (M45): a NAMED bitfield contributes its
                    # unit's alignment; ANONYMOUS ones contribute nothing
                    # (measured __alignof__ {int :3; char x;} == 1).
                    # W-F COMMIT-1 (MC 12621) REPLACES the packed DEFER:
                    # _malign_f(m, packed, u, ty) == max(1, raise), the
                    # measured packed contribution (families align 1;
                    # E6 aligned(4) -> 4; E7 tag aligned(8) -> 8) — the
                    # same answer TypeMap._align computes as `r if packed
                    # else max(u, r)`.
                    if m.width == 0 or m.name is None:
                        continue
                    u = TYPE_SIZE.get(m.type.name if isinstance(
                        m.type, ast.BuiltinType) else "", 0)
                    if not u:
                        return None
                    a = max(a, self._malign_f(m, packed, u, ty))
                    continue
                ma = self._calign(m.type)
                if ma is None:
                    return None
                a = max(a, self._malign_f(m, packed, ma, ty))
            ov = self._tag_aligned(ty, ty)
            return max(a, ov or 0)
        return None

    def _ff(self, reason) -> None:
        """Record the FIRST unsizable leaf seen by an offsetof walk
        (set-once: the depth-first walk reaches the real blocker before
        the outer arms report). M4 W-F COMMIT-0 (MC 12621, gate F2)."""
        if getattr(self, "_ff_why", None) is None:
            self._ff_why = reason

    def _why_unsizable(self, ty) -> str:
        """Name WHY a member type has no compile-time size, as deep as
        the fold mirror can see: incomplete tag / first unsizable member
        inside a defined tag / bitfield unit that is not a scalar.
        W-F gate F2: the §2.13 LOUD must name the REAL blocker, never
        mis-attribute it to the struct that happens to report first.
        (COMMIT-0 listed "packed+bitfield DEFER (§5)" as a reason;
        COMMIT-1's layout law REPLACED that refusal, so the reason is
        gone with it — a real unsizable packed struct now names its
        MEMBER.)"""
        from blcc.types import TYPE_SIZE
        if ty is None:
            return "type not known to the fold"
        while isinstance(ty, ast.Qualified):
            ty = ty.inner
        if isinstance(ty, ast.ArrayType):
            if ty.size is None:
                return "incomplete array of " + self._why_unsizable(ty.inner)
            if self.fold_truthy(ty.size) is None:
                return "array with a non-constant size of " \
                    + self._why_unsizable(ty.inner)
            return "array of " + self._why_unsizable(ty.inner)
        if isinstance(ty, ast.StructType):
            members = self.struct_tags.get(ty.tag)
            if members is None:
                return "'{}' is an incomplete type (no definition " \
                    "here)".format(ty.tag)
            # W-F COMMIT-1: the packed+bitfield §5 DEFER is DEAD — the
            # law (measured gcc 11.4) SIZES those shapes, so a packed
            # struct no longer gets a DEFER excuse here; if the fold
            # cannot size one NOW the reason is a MEMBER (never re-add a
            # packed+bitfield excuse — that was the mis-attribution
            # this wave exists to bury).
            for m in members:
                if getattr(m, "width", None) is not None:
                    if not TYPE_SIZE.get(m.type.name if isinstance(
                            m.type, ast.BuiltinType) else "", 0):
                        return "'{}' has a bitfield whose unit type is " \
                            "not a known scalar".format(ty.tag)
                    continue
                if self._csize(m.type) is None:
                    return "'{}' member '{}' unsizable: {}".format(
                        ty.tag, m.name or "(anonymous)",
                        self._why_unsizable(m.type))
            return "'{}' layout needs info the fold cannot " \
                "compute".format(ty.tag)
        if isinstance(ty, ast.FuncType):
            return "a function type has no size"
        if isinstance(ty, ast.BuiltinType) and not \
                TYPE_SIZE.get(ty.name, 1):
            return "'{}' has no size".format(ty.name)
        return "the fold cannot size this type"

    def _offsetof_flat(self, ty):
        """Flat [(name, byte-offset, type)] walk for the §2.13 fold:
        anonymous nested members are PROMOTED (T+7), and every union
        member sits at the union's base — §2.8, FINDING c2-F1: the T+6
        fold aligned union members like struct members, gcc 11.4 measures
        offsetof(union U, l) == 0 for EVERY member. Same layout family as
        _csize/_calign (the parse-time fold mirror of TypeMap)."""
        from blcc.types import TYPE_SIZE
        members = self.struct_tags.get(ty.tag)
        if members is None:
            self._ff("'{}' is an incomplete type (no definition "
                     "here)".format(ty.tag))
            return None
        out = []
        packed = self._attr_packed(ty)
        if ty.is_union:
            for m in members:
                if (self._csize(m.type) is None
                        or self._calign(m.type) is None):
                    self._ff("member '{}' of '{}' unsizable: {}".format(
                        m.name or "(anonymous)", ty.tag,
                        self._why_unsizable(m.type)))
                    return None
                if getattr(m, "width", None) is not None:
                    continue        # §1 row 12: a bitfield is a gcc ERROR
                    #                  for offsetof (loudly absent, §2.13)
                    #                  W-F: under packed it STILL never
                    #                  lands in the byte map — unions
                    #                  restart every member at bit 0 (§2.8),
                    #                  so the packed cursor never applies.
                if m.name is None:
                    inner = self._offsetof_flat(m.type)
                    if inner is None:
                        return None
                    out += inner
                else:
                    out.append((m.name, 0, m.type))
            return out
        # W-F COMMIT-1 (MC 12621): ONE bit cursor with no mid-walk byte
        # rounding. The old arm rounded to a byte after EVERY bitfield
        # (`o = (ob + 7) // 8`, next bitfield starting `ob = o * 8`) and
        # LOST the bit position — measured SILENT mis-fold at tip:
        # __builtin_offsetof({u16 x:9,y:7;char z;}, z) folded 3, gcc says
        # 2 (probes/misfold2.c; the S-matrix never paired a byte member
        # after a bitfield, so no leg could see it). The bug predates the
        # wave; the W-F law table found it; pinned by the fold-pair leg.
        bit = 0
        for m in members:
            w = getattr(m, "width", None)
            if w is not None:
                # §1 row 12 (M45): a bitfield NEVER lands in the flat byte
                # map — offsetof(bitfield) is a gcc ERROR and the §2.13
                # "no member" LOUD is its shipped mirror. The bits still
                # occupy the cursor for members that FOLLOW, under the
                # W-F law (gcc 11.4 measured, .tmp/m4-wf/probes/):
                # packed = BIT-CONTIGUOUS (the unit shrank — never
                # relocate to the next declared unit, never self-align),
                # unpacked = §1 row 12 unit moves, and an `aligned(N)`
                # member POSITIONS the cursor first in BOTH modes
                # (X1/X2/X4/Y1 — packed AND unpacked, named AND anon).
                u = TYPE_SIZE.get(m.type.name if isinstance(
                    m.type, ast.BuiltinType) else "", 0)
                if not u:
                    self._ff("'{}' has a bitfield whose unit type is not "
                             "a known scalar".format(ty.tag))
                    return None
                ub = u * 8
                if w == 0:
                    if bit % ub:
                        bit = (bit // ub + 1) * ub
                    continue
                r = self._mem_raise(m, ty)
                if r:
                    rb = r * 8
                    if bit % rb:
                        bit = (bit // rb + 1) * rb
                if not packed:
                    base = (bit // ub) * ub
                    if bit + w > base + ub:
                        bit = base + ub
                bit += w
                continue
            if isinstance(m.type, ast.ArrayType) and m.type.fam:
                # §1 row 13 (M46): offsetof(S, fam) is legal and equals
                # the header end aligned to the element (§1 row 13 fold
                # mirror; the FAM is last, so the cursor does not
                # advance). W-F: the element align rides _malign_f (the
                # TypeMap._malign mirror — packed LOWERS it to 1; the old
                # arm used the RAW align, a mirror drift the packed
                # DEFER used to mask).
                mal = self._calign(m.type)
                if mal is None:
                    self._ff("flexible array member '{}' of '{}' has an "
                             "unsizable element".format(m.name, ty.tag))
                    return None
                mal = self._malign_f(m, packed, mal, ty)
                o = (bit + 7) // 8
                o = (o + mal - 1) // mal * mal
                out.append((m.name, o, m.type))
                continue
            msz = self._csize(m.type)
            mal = self._calign(m.type)
            if msz is None or mal is None:
                self._ff("member '{}' of '{}' unsizable: {}".format(
                    m.name or "(anonymous)", ty.tag,
                    self._why_unsizable(m.type)))
                return None
            mal = self._malign_f(m, packed, mal, ty)
            o = (bit + 7) // 8
            o = (o + mal - 1) // mal * mal
            if m.name is None:
                inner = self._offsetof_flat(m.type)
                if inner is None:
                    return None
                out += [(n, o + io, t) for (n, io, t) in inner]
            else:
                out.append((m.name, o, m.type))
            bit = (o + msz) * 8
        return out

    def resolve_objsize(self, e) -> int:
        """§1 row 19: __builtin_object_size(p, n)'s compile-time answer.
        Walk the lvalue spine (casts, &, [], +CONST) to the naming object;
        its remaining size, else -1 (= SIZE_MAX, gcc's unidentified
        answer — measured on extern char ext[])."""
        off = 0
        while True:
            if isinstance(e, ast.Cast):
                e = e.operand
                continue
            if isinstance(e, ast.Unary) and e.op == "&":
                e = e.operand
                continue
            if isinstance(e, ast.Index):
                e = e.base
                continue
            if isinstance(e, ast.Binary) and e.op == "+":
                v = self.fold_truthy(e.right)
                if v is not None:
                    off += v
                    e = e.left
                    continue
                v = self.fold_truthy(e.left)
                if v is not None:
                    off += v
                    e = e.right
                    continue
                return -1
            break
        try:
            t = self.expr_type(e)
        except DiagError:
            return -1
        if t is None:
            return -1
        while isinstance(t, ast.Qualified):
            t = t.inner
        sz = self._csize(t)
        if sz is None:
            return -1
        return sz - off if sz > off else 0

    def resolve_offsetof(self, ty, chain, at):
        # §2.13 fold: walk the layout table for the member chain. A
        # MISSING member LOUDs — a bitfield member never lands in
        # struct_tags (its declaration is itself LOUD), mirroring gcc's
        # ERROR "attempt to take address of bit-field structure member":
        # never a silent number.
        # M4 W-F COMMIT-0 (MC 12621, W-B gate F2 P3): a None answer from
        # the walk USED to be reported as a flat "incomplete member
        # layout" — which MIS-ATTRIBUTED the blocker whenever the refusal
        # lived deeper than the outermost struct (the measured 613-stream
        # wall: the REAL refusal is the packed+bitfield §5 DEFER inside
        # `struct desc_struct`, reached via member 'tls_array' of
        # 'struct thread_struct' at processor.h:546; it took a resolver
        # WRAP to see it). The walk now records the FIRST unsizable leaf
        # — set-once, so the depth-first walk keeps the real blocker —
        # and the LOUD names it.
        self._ff_why = None
        cur = ty
        off = 0
        for step in chain:
            if isinstance(step, int):
                if not isinstance(cur, ast.ArrayType):
                    self._parse_err(at, "__builtin_offsetof: indexed "
                                        "member is not an array (§2.13)")
                esz = self._csize(cur.inner)
                if esz is None:
                    self._parse_err(at, "__builtin_offsetof: element "
                                        "size unknown (§2.13)")
                off += step * esz
                cur = cur.inner
                continue
            if not isinstance(cur, ast.StructType):
                self._parse_err(at, "__builtin_offsetof: '{}' is a member "
                                    "path into a non struct/union type "
                                    "(§2.13)".format(step))
            members = self.struct_tags.get(cur.tag)
            if members is None:
                self._parse_err(at, "undefined struct/union '{}' "
                                    "(§2.13)".format(cur.tag))
            flat = self._offsetof_flat(cur)
            if flat is None:
                why = getattr(self, "_ff_why", None)
                self._parse_err(at, "__builtin_offsetof: incomplete "
                                    "member layout (§2.13)" +
                                    (": REAL BLOCKER " + why
                                     if why else ""))
            found = None
            for n, o, t in flat:
                if n == step:
                    found = (o, t)
                    break
            if found is None:
                self._parse_err(at, "no member '{}' in '{}' (§2.13; a "
                                    "bitfield member is a gcc ERROR and "
                                    "stays LOUD)".format(step, cur.tag))
            off += found[0]
            cur = found[1]
        return off

    def _csize(self, ty) -> Optional[int]:
        """Compile-time size for fold_truthy's sizeof arms (mirrors the
        TypeMap layout rules on the subsets that reach here; None = can't
        say → caller LOUDs)."""
        from blcc.types import TYPE_SIZE
        if ty is None:
            return None
        while isinstance(ty, ast.Qualified):
            ty = ty.inner               # `const insn_attr_t tab[]` — the
            #                              §1 row 10 walk hit the missing
            #                              arm (pre-existing mirror gap)
        if isinstance(ty, ast.BuiltinType):
            return TYPE_SIZE.get(ty.name)
        if isinstance(ty, ast.PtrType):
            return 8
        if isinstance(ty, ast.TypeOf):
            inner = ty.typ if ty.typ is not None else (
                self.expr_type(ty.expr) if ty.expr is not None else None)
            return self._csize(inner)
        if isinstance(ty, ast.ArrayType):
            if ty.size is None:
                return None
            n = self.fold_truthy(ty.size)
            inner = self._csize(ty.inner)
            if n is None or inner is None:
                return None
            return n * inner
        if isinstance(ty, ast.StructType):
            members = self.struct_tags.get(ty.tag)
            if members is None:
                return None
            packed = self._attr_packed(ty)
            if ty.is_union:
                # §2.8 union: SIZE = max member (not the struct sum) —
                # FINDING c2-F1: the T+6 fold summed union members, which
                # desynced offsetof of members that FOLLOW a union.
                # M45: a bitfield member measures ceil(w/8) there.
                mss = []
                for m in members:
                    if getattr(m, "width", None) is not None:
                        # W-F: NO packed DEFER here either — a union
                        # member's extent is ceil(w/8) at bit 0 in BOTH
                        # modes (measured U4 packed == 4/1, A2u 4/4).
                        if m.width == 0:
                            continue        # padding consumes nothing
                        mss.append((m.width + 7) // 8)
                        continue
                    cs = self._csize(m.type)
                    if cs is None:
                        return None
                    mss.append(cs)
                if not mss:
                    return None
                align = 1
                for m in members:
                    w = getattr(m, "width", None)
                    if w is not None:
                        if w == 0 or m.name is None:
                            continue        # no alignment contribution (§12)
                        u = TYPE_SIZE.get(
                            m.type.name if isinstance(
                                m.type, ast.BuiltinType) else "", 0)
                        if not u:
                            return None
                        align = max(align, self._malign_f(m, packed, u, ty))
                        continue
                    ms = self._csize(m.type)
                    align = max(align, self._malign_f(m, packed,
                                                      min(ms, 8), ty))
                ov = self._tag_aligned(ty, ty)
                align = max(align, ov or 0)
                total = max(mss + [0])
                return (total + align - 1) // align * align
            off_bit = 0
            align = 1
            for m in members:
                w = getattr(m, "width", None)
                if w is not None:
                    # §1 row 12 (M45) fold mirror of TypeMap._struct_layout.
                    # W-F COMMIT-1 (MC 12621): the packed DEFER is GONE —
                    # packed cursor BIT-CONTIGUOUS (unit shrunk, no
                    # relocate, no self-align); `aligned(N)` POSITIONS
                    # the cursor first in both modes (X1/X2/X4/Y1; tip
                    # silently MIS-SIZED the unpacked raised shape X2:
                    # fold 4 vs gcc 8 — law-table find, pinned by leg).
                    u = TYPE_SIZE.get(m.type.name if isinstance(
                        m.type, ast.BuiltinType) else "", 0)
                    if not u:
                        return None
                    ub = u * 8
                    if w == 0:
                        if off_bit % ub:
                            off_bit = (off_bit // ub + 1) * ub
                        continue
                    r = self._mem_raise(m, ty)
                    if r:
                        rb = r * 8
                        if off_bit % rb:
                            off_bit = (off_bit // rb + 1) * rb
                    if not packed:
                        base = (off_bit // ub) * ub
                        if off_bit + w > base + ub:
                            off_bit = base + ub
                    if m.name is not None:
                        align = max(align, self._malign_f(m, packed, u, ty))
                    off_bit += w
                    continue
                if isinstance(m.type, ast.ArrayType) and m.type.fam:
                    # §1 row 13 (M46) fold mirror: zero size contribution,
                    # element align joins the struct's (FD align 8).
                    mal = self._calign(m.type)
                    if mal is None:
                        return None
                    align = max(align, self._malign_f(m, packed, mal, ty))
                    continue
                ms = self._csize(m.type)
                if ms is None:
                    return None
                mal = self._malign_f(m, packed, min(ms, 8), ty)
                align = max(align, mal)
                off = (off_bit + 7) // 8
                off = (off + mal - 1) // mal * mal if mal > 1 else off
                off_bit = (off + ms) * 8
            ov = self._tag_aligned(ty, ty)
            align = max(align, ov or 0)
            nbytes = (off_bit + 7) // 8
            return (nbytes + align - 1) // align * align
        return None

    # -- diagnostics helpers (§8 format) ------------------------------------

    def _sema(self, pos, message: str, found: Optional[str] = None):
        """pos: a Token or an ast.Node — anything carrying file:line:col."""
        if found is None:
            found = getattr(pos, "text", None) or str(getattr(pos, "value", ""))
        raise DiagError("sema", pos.file, pos.line, pos.col, message, found)

    def _parse_err(self, tok: Token, message: str):
        raise DiagError("parse", tok.file, tok.line, tok.col, message,
                        tok.text)

    # -- scopes / light sema hooks -------------------------------------------

    def lookup(self, name: str) -> Optional[tuple]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def define(self, name: str, sym: tuple, at: Token) -> None:
        # M4 W3 COMMIT-0 (MC 12563, plan §7 AMENDMENT-4): the §6 blanket
        # guard narrows to the NON-FUNCTION spellings. A builtin name
        # re-declared as a FUNCTION rides the MEASURED law in
        # _builtin_redecl_law (called by the is_fn branch of parse_decl);
        # a typedef/var/enum collision is NOT a re-declaration shape
        # (gcc rc1; the kernel corpus spells none) and keeps the §6
        # sentence verbatim — the law is never blanket-permissive.
        if name in BUILTINS and sym[0] != "fn":
            self._sema(at, "cannot re-declare the implicit builtin '{}' (§6)".format(name))
        self.scopes[-1][name] = sym

    # -- M4 W3 COMMIT-0: re-declaration law (MC 12563) ----------------------

    def _skey(self, ty) -> str:
        """Canonical COMPATIBILITY key for one type (gcc 11.4 re-decl law,
        all arms MEASURED this card): top-level qualifiers of a PARAM
        disappear; pointer TARGET qualifiers are load-bearing
        (`void bar(const char *)` vs `void bar(char *)` = gcc rc1); an
        array-of-T param and a pointer-to-T param are the SAME key
        (`void f(int a[])` + `void f(int *a)` = gcc rc0); typedef spellings
        were already resolved to the concrete node by parse_base_type;
        struct/union identity is the TAG; a `__typeof__` argument can
        never be name-compared — keyed opaque (universe volume 0)."""
        ty = self._unqual(ty)
        while isinstance(ty, ast.TypeOf):
            if ty.typ is None:
                return "?T"            # __typeof__(expr): opaque key,
            ty = self._unqual(ty.typ)  # resolution needs the fn — volume 0
        if isinstance(ty, ast.ArrayType):
            return "*" + self._ikey(ty.inner)
        if isinstance(ty, ast.PtrType):
            return "*" + self._ikey(ty.inner)
        return self._ikey(ty)

    def _ikey(self, ty) -> str:
        # NO _unqual here: below the parameter's top level the qualifier IS
        # the type (gcc rc1 on the const pair — measured).
        if isinstance(ty, ast.Qualified):
            return "q" + ty.qual + "|" + self._ikey(ty.inner)
        if isinstance(ty, ast.PtrType):
            return "*" + self._ikey(ty.inner)
        if isinstance(ty, ast.ArrayType):
            return "[" + self._ikey(ty.inner) + "]"
        if isinstance(ty, ast.FuncType):
            return ("fn" + self._skey(ty.ret) + "("
                    + ",".join(self._skey(p.type) for p in ty.params)
                    + ("..." if ty.variadic else "") + ")")
        if isinstance(ty, ast.StructType):
            return ("U" if ty.is_union else "S") + (ty.tag or "?")
        if isinstance(ty, ast.BuiltinType):
            return ty.name
        return "?" + type(ty).__name__

    def _fn_redecl_law(self, name, fty, is_static, pos) -> None:
        """MEASURED gcc 11.4 collision law for a FUNCTION re-declaration
        (this card, .tmp/m4-w3/out/probe5.py — DECL-ALONE vs USE-SITE arms
        separated; the first sweep's rc1s were USE-SITE errors, NAMED):
        (1) An implicit-builtin name (kernel strlen/strcmp family — the
        200 first-blockers) re-declared is rc0 + a warning ONLY: even an
        arity-clash or a `void` return is a warning at the declaration;
        the LOUD arrives at the USE SITE (`too few arguments`, `void value
        not ignored`) and blcc's shipped call-arity/void-value law
        answers it. The re-declared builtin therefore TYPES, ARIETIES and
        stages from the USER prototype — the §6 builtin table answers the
        UNDECLARED spelling only (the §2.17 "a user declaration wins" law,
        generalized). (2) STATIC after a non-static declaration of the
        same name is a hard gcc rc1 ("static declaration … follows
        non-static"); static-FIRST is rc0-warn. (3) General fn-vs-fn
        re-declaration (every name — the non-builtin collision stays a
        LOUD twin leg, the law is never blanket-permissive): concrete
        parameter lists and the return must be compatible; old-style `()`
        carries NO parameter information (measured rc0 `size_t strlen();`
        + concrete; rc1 on a return clash through it)."""
        prior = self.fn_decls.get(name)
        if prior is not None and is_static and not prior[3]:
            self._sema(pos, "static declaration of '{}' follows non-static "
                       "declaration (gcc rc1 twin)".format(name), name)
        key = None if fty.no_proto else tuple(self._skey(p.type)
                                              for p in fty.params)
        sig = (self._skey(fty.ret), key, fty.variadic, is_static)
        if prior is not None and not self._sig_compat(prior, sig):
            self._sema(pos, "conflicting types for '{}' — a previous "
                       "declaration of this name is not compatible "
                       "(measured gcc twin rc1)".format(name), name)
        if prior is None or prior[1] is None:
            self.fn_decls[name] = sig

    @staticmethod
    def _sig_compat(a, b) -> bool:
        # Old-style `()` carries NO parameter information (measured:
        # `size_t strlen();` + concrete list merge rc0; a return clash
        # through it is still rc1). The return and variadic arms always
        # compare.
        return (a[0] == b[0] and a[2] == b[2]
                and (a[1] is None or b[1] is None or a[1] == b[1]))

    def is_typename(self, name: str) -> bool:
        sym = self.lookup(name)
        return sym is not None and sym[0] == "typedef"

    def callable_known(self, name: str) -> bool:
        if name in BUILTINS:
            return True
        if name in predef.VA_FOLDS:
            # §2.7: the va intrinsics are FOLDS, not callables (row 19
            # "folds, not callables" posture) — no symbol, no sigs entry.
            return True
        if name in predef.INTRINSIC_FOLDS:
            return True
        if name in predef.MEM_FOLDS:
            # §2.17: same posture for the mem* builtins — the fold needs
            # no user declaration (gcc's builtin posture); plain names
            # still go through normal declaration rules.
            return True
        sym = self.lookup(name)
        return sym is not None and sym[0] == "fn"

    def expr_type(self, node: ast.Node) -> Optional[ast.Node]:
        """Light type-of-expression: only what §5 struct checks need."""
        if isinstance(node, ast.Ident):
            sym = self.lookup(node.name)
            return (self._unqual(sym[1]) if sym is not None
                    and sym[0] == "var" else None)
        if isinstance(node, ast.Cast):
            # M4 W3 commit-2: the value of a cast is its TYPE — the call
            # target `((fp_t)expr)(x)` types through the cast (S14/S18).
            return self._unqual(node.type)
        if isinstance(node, ast.Index):
            base = self.expr_type(node.base)
            if isinstance(base, ast.Qualified):
                base = self._unqual(base)   # `const struct op tbl[]` —
            # W3 commit-2 (S20/S21): the qualified ARRAY view decays too.
            if isinstance(base, (ast.ArrayType, ast.PtrType)):
                return self._unqual(base.inner)
            return None
        if isinstance(node, ast.Binary):
            # M4 W3-fix C3 (MC 12573, gate row G06a/G06b/F06): the
            # POINTER-ARITHMETIC base of an arrow-call — `(p+2)->fn(x)`
            # — types on this side too; the light mirror of the engine's
            # §4 law is ONE arm: ptr +/- int = the pointer, `int + ptr`
            # (gnu89 rc0) mirrors. A BOTH-pointer difference is the
            # LONG difference, never a pointer: stays None and answers
            # the §8 gcc-rc1 twin at the call gate (negative leg).
            left = self.expr_type(node.left)
            right = self.expr_type(node.right)
            if node.op in ("+", "-"):
                if isinstance(left, ast.PtrType) and not isinstance(
                        right, ast.PtrType):
                    return self._unqual(left)
                if node.op == "+" and isinstance(right, ast.PtrType) \
                        and not isinstance(left, ast.PtrType):
                    return self._unqual(right)
            return None
        if isinstance(node, ast.Select):
            base = self.expr_type(node.base)
            if isinstance(base, ast.Qualified):
                base = self._unqual(base)
            if node.arrow and isinstance(base, ast.PtrType):
                base = self._unqual(base.inner)
            if isinstance(base, ast.StructType):
                from blcc.types import walk_fields
                for name, mtype in walk_fields(
                        self.struct_tags.get(base.tag, ()),
                        self.struct_tags):
                    if name == node.field:
                        return mtype
            return None
        if isinstance(node, ast.Unary) and node.op == "*":
            base = self.expr_type(node.operand)
            if isinstance(base, ast.Qualified):
                base = self._unqual(base)
            if isinstance(base, (ast.PtrType, ast.ArrayType)):
                return self._unqual(base.inner)
        if isinstance(node, ast.Unary) and node.op == "&":
            # W3 commit-2 (S22 chain `**(&f)`): ADDRESS-OF builds the
            # pointer view — the mirror the deref arm decays back.
            inner = self.expr_type(node.operand)
            if inner is not None:
                return ast.PtrType(node.file, node.line, node.col, inner)
        return None

    # -- small token helpers --------------------------------------------------

    def _at(self, *words: str) -> bool:
        t = self.s.peek()
        return t.kind == "kw" and t.text in words

    def _accept(self, *words: str) -> Optional[Token]:
        if self._at(*words):
            return self.s.next()
        return None

    def starts_decl(self) -> bool:
        t = self.s.peek()
        if t.kind == "kw" and t.text in _DECL_START_KW:
            return True
        if self._at_attr() or self._at_extension():
            return True                    # §1 row 9: attr rides decls
        return t.kind == "id" and self.is_typename(t.text)

    # -- §1 row 9: gcc __attribute__ (parse + strip) --------------------------

    _ATTR_WORDS = ("__attribute__", "__attribute")
    _LAYOUT_ATTRS = ("packed", "aligned", "aligned_with")

    def _tag_attr_list(self, ty):
        return getattr(self, "struct_tag_attrs", {}).get(ty.tag, ())

    def _attr_packed(self, ty) -> bool:
        return any(nm == "packed" for nm, _a in self._tag_attr_list(ty))

    def _tag_aligned(self, ty, at):
        best = None
        for nm, arg in self._tag_attr_list(ty):
            if nm == "aligned":
                # M4 W2.5: bare `aligned` (arg None) = 16, measured gcc.
                v = 16 if arg is None else self.fold_truthy(arg)
                if v is None or v <= 0:
                    self._sema(at, "'aligned' attribute needs a positive "
                               "constant (§1 row 9)")
                best = v if best is None else max(best or 0, v)
        return best

    def _mem_raise(self, m, at):
        best = None
        for nm, arg in getattr(m, "attrs", ()):
            if nm == "aligned":
                v = 16 if arg is None else self.fold_truthy(arg)
                if v is None or v <= 0:
                    self._sema(at, "'aligned' attribute needs a positive "
                               "constant (§1 row 9)")
                best = v if best is None else max(best or 0, v)
        return best

    def _malign_f(self, m, packed, base, at):
        """§1 row 9 layout law: packed lowers the member to align 1;
        a member `aligned(N)` RAISES it (and the struct's align) — both
        gcc 11.4 run-pair pinned (l-packed/l-memb legs)."""
        a = 1 if packed else base
        v = self._mem_raise(m, at)
        return max(a, v) if v is not None else a

    def _at_extension(self) -> bool:
        tok = self.s.peek()
        return tok.kind == "kw" and tok.text == "__extension__"

    def _at_attr(self) -> bool:
        t = self.s.peek()
        # the lexer keeps `__attribute__` a KEYWORD (§4.1 vocabulary) and
        # the single-underscore spelling an identifier — accept both kinds.
        return t.text in self._ATTR_WORDS and t.kind in ("id", "kw")

    def _skip_gnu_attrs(self, sink=None) -> None:
        """PARSE + STRIP `__attribute__((...))` lists at a declaration
        head/specifier, a SPECIFIER/between-type position (M4 W2.5 — the
        positions are threaded with a SINK from the declarant owner) or a
        declarator/tag tail (§1 row 9, §2.9). The ignore-class (§1 row 9
        list + gnu_inline/unused/error/…) is parsed and DROPPED: it changes
        no code blcc emits. With a SINK the layout-class (`packed`/
        `aligned`) and `section` are CAPTURED for the owner to ACT on;
        without one the layout-class stays a LOUD wall — silently ignoring
        it would LIE about offsets the §2.13 legs pin. Names match after
        underscore-strip (`__aligned__` = `aligned`)."""
        while self._at_extension():
            self.s.next()             # GNU no-op marker (§1 row 9 family)
        while self._at_attr():
            tok = self.s.next()
            self.s.expect_punct("(")
            self.s.expect_punct("(")
            while not self.s.at_punct(")"):
                name_tok = self.s.peek()
                if name_tok.kind not in ("id", "kw"):
                    # `const`/`inline` attr names are KEYWORDS to the lexer
                    self._parse_err(name_tok, "malformed '__attribute__' "
                                              "list (§1 row 9)")
                nm = name_tok.text.strip("_")
                if nm == "mode":
                    # M4 W2.5 (MC 12557): gcc WIDENS the type — `typedef
                    # int register_t __attribute__((__mode__(__word__)))`
                    # is sizeof 8 (measured); a silent strip would LIE.
                    # Volume: 14 sites / 14 files, ALL host-tier
                    # (arch/x86/tools), 0 in kernel-tier streams.
                    self._sema(tok, "'__attribute__((mode))' changes type "
                               "width (measured mode(__word__) on int is "
                               "sizeof 8) and is not in the subset "
                               "(§1 row 9)", name_tok.text)
                if nm in self._LAYOUT_ATTRS and sink is None:
                    self._sema(tok, "'__attribute__(({}))' is a layout-"
                               "class attribute and is not in the subset "
                               "(§1 row 9)".format(name_tok.text),
                               name_tok.text)
                if nm == "aligned_with":
                    # 0 sites in the whole 5.10 tree (grep-measured): the
                    # honest LOUD class survives the M42 layout rule.
                    self._sema(tok, "'__attribute__((aligned_with))' is a "
                               "layout-class attribute and is not in the "
                               "subset (§1 row 9)", name_tok.text)
                if nm in self._LAYOUT_ATTRS and sink is not None:
                    self.s.next()
                    if nm == "aligned":
                        # M4 W2.5: bare `aligned` (NO argument) is the
                        # max-fundamental-alignment 16 (measured rc0);
                        # the argument rides the fold engines.
                        if self.s.accept_punct("("):
                            arg = self.expr.parse_expression()
                            self.s.expect_punct(")")
                        else:
                            arg = None
                        sink.append(("aligned", arg))
                    else:
                        if self.s.accept_punct("("):
                            self.s.expect_punct(")")
                        sink.append((nm, None))
                    if not self.s.accept_punct(","):
                        break
                    continue
                self.s.next()
                if nm == "alias" and sink is not None:
                    # M4 W2 §6 nm-corner (MC 12545): CAPTURE the target
                    # name (`alias("tgt")` — a string literal; the vdso/
                    # sched_clock form of the in-universe 4 streams).
                    # Without a sink the generic class still ignores it.
                    self.s.expect_punct("(")
                    tgt = self.s.next()
                    if tgt.kind != "str":
                        self._parse_err(tgt, "'alias' attribute needs a "
                                             "string target name (§6)")
                    self.s.expect_punct(")")
                    sink.append(("alias", tgt.text[1:-1]))
                    if not self.s.accept_punct(","):
                        break
                    continue
                if nm == "section" and sink is not None:
                    # M4 W2.5 (MC 12557): CAPTURE the section NAME — the
                    # 59249-site placement class now lands in the named
                    # section (§6 emission law). gcc rc1 twin measured:
                    # a non-string argument is an ERROR.
                    self.s.expect_punct("(")
                    sn = self.s.next()
                    if sn.kind != "str":
                        self._parse_err(sn, "'section' attribute argument "
                                            "not a string constant "
                                            "(§1 row 9)")
                    self.s.expect_punct(")")
                    sink.append(("section", sn.text[1:-1]))
                    if not self.s.accept_punct(","):
                        break
                    continue
                if self.s.accept_punct("("):
                    depth = 1
                    while depth:
                        t = self.s.next()
                        if t.kind == "punct" and t.text == "(":
                            depth += 1
                        elif t.kind == "punct" and t.text == ")":
                            depth -= 1
                if not self.s.accept_punct(","):
                    break
            self.s.expect_punct(")")
            self.s.expect_punct(")")

    # -- types ------------------------------------------------------------------

    def parse_type(self) -> ast.Node:
        """Base type + trailing pointer stars and array suffixes (casts,
        sizeof, declarators, §2.6d `_Generic` keys: `int[4]`)."""
        ty = self.parse_base_type()
        while True:
            # M4 W-I (MC 12650): the abstract-declarator star tail — a
            # cast/sizeof TYPE has NO entity, so a star-interleaved attr
            # rides the W2.5 no-SINK posture: markers drop, layout class
            # stays the LOUD wall (probe r22: gcc rc0 + "does not apply
            # to types" warning; the named LOUD-DIV twin with volume 0
            # is pinned in tests/test_core_m4wi1.py).
            if self._at_attr() or self._at_extension():
                self._skip_gnu_attrs()
                continue
            star = self.s.accept_punct("*")
            if star is not None:
                ty = ast.PtrType(star.file, star.line, star.col, ty)
                continue
            lb = self.s.peek()
            if lb.kind == "punct" and lb.text == "[":
                self.s.next()
                if self.s.accept_punct("]"):
                    size = None
                else:
                    size = self.expr.parse_expression()
                    self.s.expect_punct("]")
                ty = ast.ArrayType(lb.file, lb.line, lb.col, ty, size)
                continue
            if self.s.at_punct("(") and \
                    self.s.peek(1).kind == "punct" and \
                    self.s.peek(1).text in ("*", "(", ")"):
                # M4 W2 VALUES (MC 12545): the ABSTRACT declarator in a
                # type position — the fn-ptr CAST `(int (*)(void))x` and
                # the §Generic KEY `int(*)(void):` — IS that cast's
                # spelling (§2 R11). ONE mechanism: the SAME
                # _declarator_walk + _fold_ops the named W1 rows ride;
                # the 1g/1h twins keep their arms unchanged.
                _, ops = self._declarator_walk("cast")
                return self._fold_ops(ty, ops, False, "cast")
            return ty

    def parse_base_type(self, attr_sink=None) -> ast.Node:
        # §2.12/§2.6d: qualifiers LAYOUT-IGNORE stays true — everything
        # resolves through TypeMap._untype — but a TYPE-level qualifier is
        # MARKED (Qualified wrapper) because the oracle makes it
        # significant in exactly two places: the pointee of
        # __builtin_types_compatible_p and the association types of
        # _Generic. The wrapper is stripped by every other consumer.
        #
        # M4 W2.5 (MC 12557): `attr_sink` extends the §1 row 9 skip to the
        # SPECIFIER positions the kernel streams actually use — between
        # the base type and the declarator name (`__u64 __attribute__((
        # aligned(8))) flags;`). With a SINK the layout/section class is
        # CAPTURED for the consumer to ACT on; without one (cast/sizeof
        # TYPE context, where no object exists to lay out) the layout
        # class keeps its LOUD wall — never a silent strip.
        quals: List = []
        self._skip_gnu_attrs(attr_sink)  # decl-head/specifier (§1 row 9)
        ty = self._base_type_core(quals, attr_sink)
        self._skip_gnu_attrs(attr_sink)  # between type and declarator
        for q, qt in sorted(set(quals)):
            ty = ast.Qualified(qt.file, qt.line, qt.col, q, ty)
        return ty

    def _take_qualifiers(self, out) -> None:
        while self.s.peek().kind == "kw" and \
                self.s.peek().text in _QUAL_WORDS:
            qt = self.s.next()
            out.append((_QUAL_WORDS[qt.text], qt))

    # M4 W2 COMMIT-0 (AMENDMENT-2 arms a+c, MC 12545): the scalar
    # specifier words fully COMMUTE (all combinations re-measured against
    # gcc 11.4 gnu89 this card) — `long unsigned int` is the stddef.h:207
    # `__SIZE_TYPE__` family (arm c), `int long` rc 0, `long unsigned
    # long` rc 0 — and C99 `_Bool` (arm a: `typedef _Bool bool;`,
    # include/linux/types.h:30, the uniform first-blocker of all 689
    # kernel streams) rides the SAME word loop. Measured ERROR twins, LOUD
    # here and rc 1 in the oracle: two DISTINCT length words (`char long`,
    # `char int`, `short long`), three `long`, `signed` + `unsigned`,
    # either sign with `_Bool`, a repeated word. `__Bool` is NOT a keyword
    # in gcc 11.4 (measured rc 1 "unknown type name") — it stays an id.
    _SPEC_WORDS = ("_Bool", "void", "unsigned", "signed", "__signed__",
                   "__signed", "char", "short", "int", "long",
                   # M4 W-B (MC 12596): __int128 is a LENGTH word of its
                   # own — measured gcc 11.4 law (probes): it COMMUTES
                   # with the sign family and qualifiers (`unsigned
                   # __int128`, `__int128 unsigned`, `__signed__ __int128`
                   # all rc 0) but joins NO other length party (`long
                   # __int128`, `int __int128`, `__int128 long`, `_Bool
                   # __int128`, `void __int128`, a repeat — ALL rc 1).
                   "__int128")

    def _base_type_core(self, quals: List, attr_sink=None) -> ast.Node:
        # M2 §1 rows 2/14: the full scalar specifier family. signedness
        # combines per C: `unsigned`, bare `signed`, `unsigned long long`,
        # `long long`, order-free spec words.
        self._take_qualifiers(quals)
        t = self.s.peek()
        if t.kind == "kw":
            if t.text in ("float", "double"):
                self.s.next()          # §1 row 14: storage parses; arith LOUD
                return ast.BuiltinType(t.file, t.line, t.col, t.text)
            if t.text in ("typeof", "__typeof__", "__typeof"):
                # §1 row 6c / §2.6 (M2-C5 leg 3): __typeof__(expr|type) —
                # a TYPE that stands for its operand's type. Operand is
                # TYPED, never evaluated (`__typeof__(called=1)` leaves
                # `called` untouched); resolution rides TypeMap._untype.
                self.s.next()
                self.s.expect_punct("(")
                if self.expr._starts_type(0):
                    typ = self.parse_type()
                    self.s.expect_punct(")")
                    return ast.TypeOf(t.file, t.line, t.col, None, typ)
                operand = self.expr.parse_expression()
                self.s.expect_punct(")")
                return ast.TypeOf(t.file, t.line, t.col, operand, None)
            if t.text == "struct" or t.text == "union":
                return self.parse_struct_type()
            if t.text == "enum":
                return self.parse_enum_type()
        unsigned = signed = is_bool = is_void = False
        i128 = False
        longs = 0
        lengths: List[str] = []          # any of char / short / int
        while True:
            self._skip_gnu_attrs(attr_sink)   # M4 W2.5: attr BETWEEN spec
            t = self.s.peek()                 # words (§1 row 9 family)
            if t.kind != "kw" or t.text not in self._SPEC_WORDS:
                break
            self.s.next()
            if t.text == "void":
                # `void` rides the SAME commutative word loop (its TYPE
                # answers like the old _TYPE_KW arm did — storage laws
                # downstream UNCHANGED); mixing it with any other data
                # word is the measured gcc ERROR, judged ONCE at COMPOSE
                # below ("both 'unsigned' and 'void'…" / "two or more
                # data types") — a loop-side check would miss the order
                # `void unsigned`.
                is_void = True
            elif t.text == "_Bool":
                if is_bool:
                    self._sema(t, "two or more data types in declaration "
                                  "specifiers ('_Bool' repeated) is a gcc "
                                  "ERROR (§1 row 2)")
                if unsigned or signed:
                    self._sema(t, "mixing a sign specifier with '_Bool' is "
                                  "a gcc ERROR (§1 row 2: both 'unsigned' "
                                  "and '_Bool' in declaration specifiers)")
                is_bool = True
            elif t.text == "unsigned":
                if is_bool or unsigned or signed:
                    self._sema(t, "'unsigned' combined with {} is a gcc "
                                  "ERROR (§1 row 2)".format(
                                      "'_Bool'" if is_bool else
                                      "another sign specifier"))
                unsigned = True
            elif t.text in ("signed", "__signed__", "__signed"):
                if is_bool or unsigned or signed:
                    self._sema(t, "'signed' combined with {} is a gcc "
                                  "ERROR (§1 row 2)".format(
                                      "'_Bool'" if is_bool else
                                      "another sign specifier"))
                signed = True
            elif t.text == "__int128":
                if i128:
                    self._sema(t, "two or more data types in declaration "
                                  "specifiers ('__int128' repeated) is a "
                                  "gcc ERROR (§1 row 2)")
                i128 = True
            elif t.text == "long":
                longs += 1
                if longs > 2:
                    self._sema(t, "'long long long' is too long (§1 row 2, "
                                  "gcc ERROR)")
            else:                        # char | short | int
                if t.text in lengths:
                    self._sema(t, "two or more data types in declaration "
                                  "specifiers ('{}' repeated) is a gcc "
                                  "ERROR (§1 row 2)".format(t.text))
                lengths.append(t.text)
            self._take_qualifiers(quals)
        if is_void:
            # ONE judge for both orders (`void unsigned` and `unsigned
            # void`): the measured gcc ERROR "both 'unsigned' and 'void'
            # in declaration specifiers" / "two or more data types". A
            # bare `void` answers as the BuiltinType it always has been —
            # storage laws (size of void) ride downstream UNCHANGED.
            if is_bool or lengths or longs or unsigned or signed \
                        or i128:
                self._sema(t, "'void' combined with another data "
                              "specifier is a gcc ERROR (§1 row 2)")
            return ast.BuiltinType(t.file, t.line, t.col, "void")
        if is_bool:
            if i128:
                self._sema(t, "two or more data types in declaration "
                              "specifiers ('_Bool' and '__int128') is "
                              "a gcc ERROR (§1 row 2)")
            return ast.BuiltinType(t.file, t.line, t.col, "_Bool")
        if i128:
            # Measured (M4 W-B, MC 12596): __int128 answers ALONE or
            # with a sign word only; `unsigned __int128` keeps its
            # distinct identity (types.py SIZE/UNSIGNED tables).
            if lengths or longs:
                self._sema(t, "two or more data types in declaration "
                              "specifiers ({}) is a gcc ERROR "
                              "(§1 row 2)".format(
                                  " and ".join(
                                      lengths + ["long"] * longs)))
            name = ("unsigned __int128" if unsigned else "__int128")
            return ast.BuiltinType(t.file, t.line, t.col, name)
        if lengths or longs:
            # Two DISTINCT length words are the measured gcc ERROR ("both
            # 'long' and 'char'…" / "two or more data types") with ONE
            # exception: `int` is the filler noun of a length pair, so
            # `short int`, `long int` and `int long` (rc 0 measured) fold
            # into the OTHER word.
            lenset = set(lengths) - {"int"}
            if len(lenset) > 1:
                self._sema(t, "two or more data types in declaration "
                              "specifiers ({}) is a gcc ERROR (§1 row 2)"
                              .format(" and ".join(lengths)))
            if longs and "char" in lenset:
                self._sema(t, "both 'long' and 'char' in declaration "
                              "specifiers is a gcc ERROR (§1 row 2)")
            if longs and "short" in lenset:
                self._sema(t, "both 'short' and 'long' in declaration "
                              "specifiers is a gcc ERROR (§1 row 2)")
            name = ("long long" if longs > 1 else
                    "long" if longs else
                    "short" if "short" in lenset else
                    "char" if "char" in lenset else "int")
            if unsigned:
                name = "unsigned " + name
            elif signed and name == "char":
                name = "signed char"
            return ast.BuiltinType(t.file, t.line, t.col, name)
        if t.kind == "id" and self.is_typename(t.text):
            # TYPEDEF noun, with or without sign words: the plain `U x;`,
            # and `unsigned U` over an integer typedef — the typedef
            # carries the base; blcc composes the unsigned view of its
            # underlying type (old law, UNCHANGED).
            base = self.lookup(t.text)[1]
            self.s.next()
            if unsigned and isinstance(base, ast.BuiltinType) \
                    and base.name in ("char", "short", "int", "long",
                                       "long long"):
                return ast.BuiltinType(t.file, t.line, t.col,
                                       "unsigned " + base.name)
            return base
        if unsigned or signed:
            name = "unsigned int" if unsigned else "int"  # bare sign word
            return ast.BuiltinType(t.file, t.line, t.col, name)
        self._parse_err(t, "expected a type")

    def _skip_qualifiers(self) -> None:
        while self._at("const", "volatile", "__volatile__", "restrict",
                       "__restrict", "__restrict__", "__const",
                       "__const__"):
            self.s.next()

    def parse_struct_type(self) -> ast.Node:
        # §2.8: struct AND union share the grammar; the tag namespace is
        # shared too (C keeps them in one space). is_union rides the KEY-
        # WORD, so a brace-less re-reference (`union U u;`) keeps it.
        tok = self.s.next()  # 'struct' or 'union'
        is_union = tok.text == "union"
        # M4 W2.5 (MC 12557): the tag-PREFIX position — `struct
        # __attribute__((__packed__)) S {…}` (3 corpus sites) joins the
        # tag-definition law: attrs captured here register IDENTICALLY
        # to the tag tail.
        pre_sink: List[tuple] = []
        self._skip_gnu_attrs(pre_sink)
        if self.s.at_punct("{"):
            # Minted tags must be UNIQUE: post-pp kernel streams place
            # whole structs on one line, so file:line was not enough for
            # two inline definitions (T+7 same-line leg).
            self._anon_n += 1
            tag = "<anon@{}:{}#{}>".format(tok.file, tok.line, self._anon_n)
        else:
            tag = self.s.expect_id("parse").text
        if self.s.accept_punct("{"):
            members = self.parse_struct_members(is_union)
            tsink: List[tuple] = []
            self._skip_gnu_attrs(tsink)  # tag-definition tail (§1 row 9)
            tsink = pre_sink + tsink     # M4 W2.5: prefix registers like
                                         # the tail (one law)
            if tag in self.struct_tags:
                self._sema(tok, "struct/union '{}' is already defined"
                           .format(tag))
            self.struct_tags[tag] = members
            if tsink:
                reg = getattr(self, "struct_tag_attrs", None)
                if reg is None:
                    reg = self.struct_tag_attrs = {}
                reg[tag] = tuple(tsink)   # M42: layout attrs ACT (§1 row 9)
            self._pending.append(ast.StructDecl(tok.file, tok.line, tok.col,
                                                tag, members, is_union,
                                                tuple(tsink)))
            self._bare_type_ok = True
        elif self.s.at_punct(";"):
            self._pending.append(ast.StructDecl(tok.file, tok.line, tok.col,
                                                tag, None, is_union))
            self._bare_type_ok = True
        return ast.StructType(tok.file, tok.line, tok.col, tag, is_union)

    def _flat_member_names(self, members) -> List[str]:
        from blcc.types import walk_fields
        return [n for n, _t in walk_fields(members, self.struct_tags)]

    def parse_struct_members(self, is_union=False) -> Tuple[ast.Member, ...]:
        members: List[ast.Member] = []
        seen: set = set()             # flat member namespace, promoted §
        while not self.s.at_punct("}"):
            if self.s.accept_punct(";"):
                continue
            bsink: List[tuple] = []     # M4 W2.5: SPEC-position member attrs
            base = self.parse_base_type(bsink)
            if isinstance(base, ast.StructType) and self.s.at_punct(";"):
                pos = self.s.next()   # the terminating ';'
                if base.tag.startswith("<anon@"):
                    # §1 T+7 ANONYMOUS MEMBER: untagged inline struct/union
                    # with no declarator (gcc gnu89: names PROMOTED into
                    # this struct's namespace; layout embeds at this point).
                    for n in self._flat_member_names(
                            self.struct_tags.get(base.tag, ())):
                        if n in seen:
                            self._sema(pos, "duplicate member '{}'".format(n))
                        seen.add(n)
                    members.append(ast.Member(None, base))
                else:
                    # Tagged specifier with NO declarator: gnu89 measures
                    # "declaration does not declare anything" (rc0) — the
                    # tag is registered, there is NO member (§1 T+7 pin).
                    pass
                continue
            pos = self.s.peek()
            # M4 W2 COMMIT-0 arm b (AMENDMENT-2, MC 12545): ONE declarator,
            # ',', declarator, ';' — the comma list REUSES the very
            # parse_declarator the single form rides (one mechanism). The
            # bitfield width applies to EACH member of the list; the
            # anonymous `: w` form may open the list and continue in it
            # (measured gcc: `int :2, x:3;` rc 0). The list_head witness
            # `struct list_head { struct list_head *next, *prev; };` is the
            # uniform shape behind all 689 kernel streams.
            while True:
                msink: List[tuple] = []
                width = None
                if self.s.at_punct(":"):
                    # §1 row 12 (M45): ANONYMOUS bitfield `: w` — no
                    # declarator at all (gcc gnu89 measured: it consumes
                    # bits, contributes NO alignment; w==0 pads to the
                    # next unit).
                    self.s.next()
                    name, ty, is_fn = None, base, False
                    width = self._bitfield_width(None, base, pos)
                else:
                    name, ty, is_fn, _ = self.parse_declarator(
                        base, ctx="member", attr_sink=msink)
                    if name is None:
                        self._parse_err(pos, "struct member needs a name")
                    if is_fn:
                        # M4 W1: the declarator now BUILDS the FuncType — a
                        # member stays LOUD because a member is an OBJECT;
                        # gcc rc1 "invalid use of void type" / "function
                        # declared void" — the twin agrees, nothing
                        # regressed.
                        self._parse_err(pos, "struct member with 'function' "
                                        "type is a gcc ERROR (§4)")
                    if self.s.accept_punct(":"):
                        width = self._bitfield_width(name, ty, pos)
                if name is not None:
                    # measured gcc 11.4: plain `int a; int a;` is the SAME
                    # ERROR "duplicate member 'a'" the promoted names
                    # join. ANONYMOUS members carry NO name — None must
                    # never enter the namespace (tip FALSE-LOUD finding,
                    # this commit: `int :2; int :3;` is gcc rc 0, measured
                    # — the old single-slot code collided on None).
                    if name in seen:
                        self._sema(pos, "duplicate member '{}'".format(name))
                    seen.add(name)
                    # M4 W-I (MC 12650): a member has no placement —
                    # `section` is a measured gcc rc1 twin at BOTH the
                    # spec position (probe s1: tip silently DROPPED it,
                    # the W2.5 sink had no judge) and the new star
                    # position (probe r16). The sentence mirrors gcc.
                    for _nm, _a in tuple(bsink) + tuple(msink):
                        if _nm == "section":
                            self._sema(pos, "section attribute not "
                                       "allowed for '{}' (§1 row 9, "
                                       "measured gcc rc1 twin)"
                                       .format(name), "section")
                members.append(ast.Member(name, ty,
                                         tuple(bsink) + tuple(msink),
                                         width))
                if self.s.accept_punct(","):
                    continue                  # next declarator, same base
                self.s.expect_punct(";")
                break
        # §1 row 13 (M46) FAM PLACEMENT law — every arm measured as a
        # gcc gnu89 ERROR: a flexible array in a union; a FAM with ANY
        # member after it ("flexible array member is not at the end");
        # and a struct whose only named content IS the FAM ("structure
        # has no members").
        fam_at = [i for i, m in enumerate(members)
                  if isinstance(m.type, ast.ArrayType) and m.type.fam]
        for i in fam_at:
            m = members[i]
            if is_union:
                self._sema(m.type, "flexible array member in a union is a "
                           "gcc ERROR (§1 row 13)", m.name)
            if i != len(members) - 1:
                self._sema(m.type, "flexible array member '{}' is not at "
                           "the end (§1 row 13, gcc error)".format(
                               m.name), m.name)
        if fam_at:
            from blcc.types import walk_fields
            named = {n for n, t in walk_fields(members, self.struct_tags)
                     if not (isinstance(t, ast.ArrayType) and t.fam)}
            if not named:
                self._sema(members[fam_at[0]].type,
                           "structure has no named member besides the "
                           "flexible array member (§1 row 13, gcc: "
                           "structure has no members)",
                           members[fam_at[0]].name)
        self.s.expect_punct("}")
        return tuple(members)

    def _bitfield_width(self, name, unit_ty, pos) -> int:
        """§1 row 12 (M45): bitfield `: width` with the gcc-11.4 gnu89
        error law measured this session — the UNIT must be a scalar
        integer type (its SIZE is the allocation unit); a NAMED zero
        width is the gcc ERROR "zero width for bit-field"; a width that
        exceeds the unit type is the gcc ERROR "width of 'a' exceeds its
        type"; negatives LOUD too. Family `sema` throughout."""
        from blcc.types import TYPE_SIZE
        w = self.parse_int_constant("bitfield width")
        uname = unit_ty.name if isinstance(unit_ty, ast.BuiltinType) \
            else None
        if uname is None or uname == "void" or uname in ("float", "double"):
            self._sema(pos, "bitfield unit '{}' is not a scalar integer "
                       "type (§1 row 12)".format(uname or "non-scalar"))
        if w < 0:
            self._sema(pos, "negative width '{}' for bit-field '{}' "
                       "(§1 row 12, gcc error)".format(w, name))
        if name is not None and w == 0:
            self._sema(pos, "zero width for bit-field '{}' (§1 row 12, "
                       "gcc error: only ANONYMOUS fields may be : 0)"
                       .format(name))
        if w > TYPE_SIZE[uname] * 8:
            self._sema(pos, "width of '{}' exceeds its type (§1 row 12: "
                       "'{}' units are {} bits)".format(
                           name, uname, TYPE_SIZE[uname] * 8))
        return w

    def parse_enum_type(self) -> ast.Node:
        tok = self.s.next()  # 'enum'
        if self.s.peek().kind == "id":
            self.s.next()  # tag (constants, not tags, are what §4 pins)
        int_ty = ast.BuiltinType(tok.file, tok.line, tok.col, "int")
        if not self.s.accept_punct("{"):
            return int_ty
        consts: List[Tuple[str, int]] = []
        prev = 0
        while not self.s.at_punct("}"):
            name = self.s.expect_id("parse")
            value = prev
            if self.s.accept_punct("="):
                value = self.parse_int_constant(
                    "'enum' initializer must be an integer constant (§4)")
            consts.append((name.text, value))
            self.define(name.text, ("enum", value), name)
            prev = value + 1
            if not self.s.accept_punct(","):
                break
        self.s.expect_punct("}")
        self._skip_gnu_attrs()          # enum tag-definition tail (§1 row 9)
        self._pending.append(ast.EnumDecl(tok.file, tok.line, tok.col, tuple(consts)))
        self._bare_type_ok = True
        return int_ty

    def parse_int_constant(self, message: str) -> int:
        # T+10b: enums and case labels take the FULL constant grammar the
        # kernel's post-pp text feeds them — `(1 << (3+2))`, `A | B`,
        # `sizeof(long)` … the §1 row 10 walk (inat/idt/mmap witnesses)
        # hit the missing arms. fold_truthy is the folder; None = LOUD.
        t = self.s.peek()
        node = self.expr.parse_expression()
        v = self.fold_truthy(node)
        if v is None:
            self._sema(t, message)
        return v

    # -- declarators ---------------------------------------------------------------

    def parse_declarator(self, base: ast.Node, ctx: str = "var",
                         attr_sink=None):
        """ctx: 'var' | 'param' | 'member' | 'typedef'. Returns
        (name, type, is_fn, params). M4 W1 (MC 12541): when the ENTITY is a
        function, type is its ast.FuncType (parse_decl unpacks ret/params/
        variadic from it; the C 6.7.6.3p7 param-decay arm lives in
        parse_params). Every fn-ptr spelling `(*name)(…)` lands as
        PtrType(FuncType) with is_fn False — an OBJECT (§1 rows 1a–1f).

        M4 W-I (MC 12650): `attr_sink` now reaches the POINTER SECTION of
        the declarator too (the W2.5 tail skip below always took it; the
        walk never did) — the attribute-between-* family lands here."""
        name, ops = self._declarator_walk(ctx, attr_sink)
        dims = [op for op in ops if op[0] == "arr"]
        unsized = [op for op in dims if op[2] is None]
        # §1 row 13 (M46): `int v[];` — a member's SINGLE unsized bracket
        # is the FLEXIBLE ARRAY declarator (gcc gnu89; the last-member/
        # union/alone rules belong to the member list, checked by
        # parse_struct_members). Any other unsized member dimension keeps
        # the M1 wall (gcc: "array size missing").
        fam_only = ctx == "member" and len(dims) == 1 and len(unsized) == 1
        if unsized and ctx == "member" and not fam_only:
            self._sema(unsized[0][1], "'array' members of a struct must "
                       "have a fixed size (§5)")
        ty = self._fold_ops(base, ops, fam_only, ctx)
        self._skip_gnu_attrs(attr_sink)  # declarator tail (§1 row 9)
        if isinstance(ty, ast.FuncType):
            return name, ty, True, ty.params
        return name, ty, False, ()

    def _fold_ops(self, base: ast.Node, ops, fam_only: bool,
                  ctx: str) -> ast.Node:
        """The INSIDE-OUT fold of the walk's operator chain onto the base
        type (M4 W1 law). ONE mechanism: the NAMED declarator and, since
        M4 W2 (MC 12545), the ABSTRACT declarator of a cast/_Generic key
        both land here — no second type-builder beside this one."""
        ty = base
        for idx, op in enumerate(ops):
            kind = op[0]
            if kind == "ptr":
                _, ppos = op
                ty = ast.PtrType(ppos.file, ppos.line, ppos.col, ty)
            elif kind == "arr":
                _, bracket, size = op
                if isinstance(ty, ast.FuncType):
                    # arrays hold OBJECTS — gcc ERROR (twin agrees rc 1).
                    self._sema(bracket, "'array' of 'function' elements is "
                               "a gcc ERROR (§4)", "array")
                ty = ast.ArrayType(bracket.file, bracket.line, bracket.col,
                                   ty, size, fam=(fam_only
                                                  and size is None))
            else:                          # ("fn", lp, params, var, nostd)
                _, lp, params, variadic, nostd = op
                if isinstance(ty, ast.FuncType):
                    self._sema(lp, "'function' returning a 'function' is a "
                               "gcc ERROR (§4)", "function")
                if isinstance(ty, ast.ArrayType):
                    self._sema(lp, "'function' returning an 'array' is a "
                               "gcc ERROR (§4)", "function")
                if (idx == len(ops) - 1             # the ENTITY is the
                        and isinstance(ty, ast.PtrType)   # FUNCTION here
                        and isinstance(ty.inner, ast.FuncType)
                        and ty is not base):
                    # §1 row 1g — LOUD TWIN kept by v4 §7 W1 (census EXACT
                    # class, kernel volume 0): the star-form `T (*f(…))(…)`
                    # — the ENTITY is a function whose return fn-ptr is
                    # BUILT IN THIS declarator. `int *(*(*q)(void))(int)`
                    # (an inner fn-ptr RETURNS a fn-ptr; entity is a ptr)
                    # is NOT this row — gcc rc 0, leg-pinned. A typedef'd
                    # fn-ptr base (`ty is base`) — `work_func_t
                    # wq_worker_last_func(…)` (5 corpus streams) — passes.
                    self._sema(lp, "'function pointer' as a RETURN type "
                               "(row 1g) is not in the subset (§5 LOUD "
                               "twin)", "function pointer")
                ty = ast.FuncType(lp.file, lp.line, lp.col, ty, params,
                                  variadic, nostd)
        return ty

    def _declarator_walk(self, ctx, attr_sink=None):
        """M4 W1: the paren-aware declarator walk. Returns (name, ops), ops
        being the INSIDE-OUT type-operator chain (each entry wraps what the
        previous produced, starting from the base type). The composition
        law — verified form-by-form against gcc in test_core_m4w1 — is
        ops(level) = [ptr × stars] + reversed(postfixes as they appear)
        + ops(child). The paren group is what REORDERS the operators: a
        postfix after `( … )` applies UNDER the group's outer stars and
        BEFORE the child's operators — exactly why `int (*f)(void)` is
        pointer-to-function while `int *f(void)` is function-returning-
        pointer. The M1 §5 wall on this shape ('function pointer'
        declarations are not in the subset) DIES here (MC 12541)."""
        pos0 = self.s.peek()
        stars = 0
        while True:
            # T+10b: `int * const p`, `char * volatile v`, `int const * q`
            # — qualifiers may sit on either side of every `*` (kernel
            # style; the §1 row 10 walk exposed the missing arms). They
            # are parsed-and-dropped like every other qualifier here.
            # M4 W-I (MC 12650): and so do the `__attribute__` runs —
            # the attribute-between-* family. The MEASURED gcc 11.4 law
            # (probes .tmp/m4-wi/probes/, table pinned in
            # tests/test_core_m4wi1.py): an attr run FOLLOWED by another
            # `*` — or by a group `(` whose interior opens with `*` —
            # attaches to the POINTER TYPE (markers drop; `section`
            # warns+emits nothing; `aligned` has no spellable effect →
            # the no-sink layout wall, the W2.5 cast-position posture).
            # The FINAL run, before the declarator name / group name /
            # abstract `)`, attaches to the ENTITY — the witness
            # position: `extern struct pcpu_alloc_info * __section__(
            # ".init.text") __cold pcpu_alloc_alloc_info(...)`
            # (percpu.h:105, the 574-stream first-blocker).
            self._skip_qualifiers()
            if self._at_attr() or self._at_extension():
                self._skip_gnu_attrs(None if self._ptr_run_is_type()
                                     else attr_sink)
                continue
            if self.s.accept_punct("*") is None:
                break
            stars += 1
        self._skip_qualifiers()
        nxt = self.s.peek(1)
        if self.s.at_punct("(") and (nxt.text in self._ATTR_WORDS
                                     or (nxt.kind == "kw"
                                         and nxt.text == "__extension__")):
            # M4 W-I (MC 12650): `int (__attribute__((unused)) * fp)
            # (void)` — the run rides INSIDE the opening paren (probe
            # p2d); the group detector sees through it. The walk
            # recursion then JUDGES the run: its interior opens with
            # `*` → TYPE position (markers drop, r9).
            nxt = self.s.peek(self._peek_past_run(1))
        group = (self.s.at_punct("(")
                 and (nxt.kind == "id"
                      or (nxt.kind == "punct"
                          and (nxt.text in ("*", "(")
                               or (nxt.text == ")" and stars)))))
        if group:
            self.s.next()
            if stars and self.s.accept_punct(")"):   # abstract `(* )` group
                name, c_ops = None, []
            else:
                # M4 W-I: the group's interior rides the SAME sink —
                # `(* __aligned__(16) fp)` raises the declared object
                # (probe r14), the entity is one and the same.
                name, c_ops = self._declarator_walk(ctx, attr_sink)
            self.s.expect_punct(")")
        else:
            name = None
            if stars and self.s.at_punct(")"):
                # M4 W2 (MC 12545): ABSTRACT group tail — the `( * )`
                # inside `int (*)(void)`; the name slot is EMPTY (the
                # cast/_Generic-key declarator has no identifier).
                pass
            elif not (ctx == "param" and (self.s.at_punct(")")
                                          or self.s.at_punct(","))):
                name = self.s.expect_id("parse").text
            c_ops = []
        postfixes = []
        while True:
            if self.s.at_punct("["):
                bracket = self.s.next()
                size = (None if self.s.at_punct("]")
                        else self.expr.parse_expression())
                self.s.expect_punct("]")
                postfixes.append(("arr", bracket, size))
                continue
            if self.s.at_punct("("):
                lparen = self.s.peek()       # parse_params CONSUMES it
                params = self.parse_params()
                postfixes.append(("fn", lparen, params,
                                  self._params_variadic,
                                  self._params_no_proto))
                continue
            break
        return name, ([("ptr", pos0)] * stars
                      + list(reversed(postfixes)) + c_ops)

    def _peek_past_run(self, k0: int) -> int:
        """M4 W-I (MC 12650): index of the first token AFTER the
        `__attribute__`/`__extension__`/qualifier runs starting at
        peek(k0) — the scan shared by the TYPE/ENTITY judge and the
        group detector (a group may open with the attr INSIDE the
        paren: `int (__attribute__((unused)) * fp)(void)`, probe p2d).
        A malformed attr list returns the EOF-clamped index; the REAL
        skip (_skip_gnu_attrs) LOUDs at the same token."""
        k = k0
        while True:
            t = self.s.peek(k)
            if t.text in self._ATTR_WORDS and t.kind in ("id", "kw"):
                k += 1
                depth = 0
                while True:
                    u = self.s.peek(k)
                    if u.kind == "eof":
                        return k
                    if u.kind == "punct" and u.text == "(":
                        depth += 1
                    elif u.kind == "punct" and u.text == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                k += 1
                continue
            if t.kind == "kw" and (t.text == "__extension__"
                                   or t.text in _QUAL_WORDS):
                k += 1
                continue
            return k

    def _ptr_run_is_type(self) -> bool:
        """M4 W-I (MC 12650): does the `__attribute__` run the cursor
        sits on attach to the POINTER TYPE or to the ENTITY?

        MEASURED gcc 11.4 law (probes .tmp/m4-wi/probes/ r1/r2/r9/r14/
        r20): TYPE when another `*` follows the run (after any further
        attrs/quals of the run — stars, attrs and qualifiers all
        interleave), or when a paren GROUP opens whose interior starts
        with `*` (the `( __attr * p )` shape — probe r9: `section`
        warns "does not apply to types" and the object is untouched).
        ENTITY otherwise: the final run before the declarator name
        (the percpu witness), before the group of a NAMED interior
        (`( fp )`), or before the abstract `)` — those land on the
        declared fn/object exactly as the spec/tail positions do."""
        k = self._peek_past_run(0)
        if self.s.at_punct("*", k):
            return True
        if self.s.at_punct("(", k):
            nxt = self.s.peek(k + 1)
            # `(` opening an IDENTIFIER is the parenthesized NAME — the
            # entity lives INSIDE, so the run precedes the entity.
            return not (nxt.kind == "id"
                        or (nxt.kind == "punct" and nxt.text == "("
                            and self.s.peek(k + 2).kind == "id"))
        return False

    def parse_params(self) -> Tuple[ast.Param, ...]:
        self.s.expect_punct("(")
        params: List[ast.Param] = []
        self._params_variadic = False
        self._params_no_proto = False
        if self.s.accept_punct(")"):
            self._params_variadic = False   # M4 W1: the side channel
            self._params_no_proto = True    # M4 W3 C0: `()` = NO info
            return ()                       # describes THIS list only —
        if self._at("void") and self.s.at_punct(")", 1):
            self.s.next()                   # nesting cannot clobber it:
            self.s.next()                   # _declarator_walk snapshots it
            self._params_variadic = False   # per '(' right after the call
            self._params_no_proto = False   # (void) says ZERO params
            return ()
        while True:
            t = self.s.peek()
            if t.kind == "punct" and t.text == "...":
                # §1 row 17 SUPPORT: a trailing `...` marks the function
                # variadic (callee §2.7 + caller §2.14). `...` may only be
                # LAST in the list — anything after it hits the ordinary
                # "expected a type" path (loud, never silent).
                self.s.next()
                self.s.expect_punct(")")
                self._params_variadic = True
                return tuple(params)
            psink: List[tuple] = []    # M4 W-I: the STAR-position attrs of
            ppos = self.s.peek()       # THIS parameter declarator
            base = self.parse_base_type()
            name, ty, is_fn, _ = self.parse_declarator(base, ctx="param",
                                                       attr_sink=psink)
            if name is not None:
                for _nm, _a in psink:
                    if _nm == "section":
                        # M4 W-I (MC 12650): measured gcc rc1 twin
                        # (probe r12): "section attribute not allowed
                        # for 'q'" — a parameter has no placement. The
                        # TYPE-position classes the walk already dropped
                        # (markers) and LOUDed (layout) ride §1 row 9.
                        self._sema(ppos, "section attribute not allowed "
                                   "for '{}' (§1 row 9, measured gcc rc1 "
                                   "twin)".format(name), "section")
            if is_fn:
                # C 6.7.6.3p7 (M4 W1 row 1b): a parameter of FUNCTION type
                # is ADJUSTED to pointer-to-function — `void cb(int)` and
                # `void (*cb)(int)` declare the same thing. The M1 wall
                # ("parameter with function type is not in the subset")
                # dies here; the oracle twin is test_core_m4w1 1b-decay.
                ty = ast.PtrType(ty.file, ty.line, ty.col, ty)
            params.append(ast.Param(name, ty))
            if self.s.accept_punct(","):
                continue
            self.s.expect_punct(")")
            break
        self._params_variadic = False
        return tuple(params)

    # -- declarations -----------------------------------------------------------------

    def parse_decl(self, at_file: bool) -> List[ast.Node]:
        out: List[ast.Node] = []
        # §1 row 9: attributes may lead a declaration (`__attribute__((x))
        # static int f(...)`) — skip BEFORE the storage-class keywords.
        # M4 W2.5 (MC 12557): every skip position in THIS declarant owner
        # shares one SINK — the kernel shapes put the attr BETWEEN the base
        # type and the declarator name (`__u64 __attribute__((aligned(8)))
        # flags;` 88 files; `extern char __attribute__((__section__(
        # ".init.data"))) boot_command_line[];` 67 files), and the
        # captured layout/placement class ACTS on the object or function.
        decl_sink: List[tuple] = []
        self._skip_gnu_attrs(decl_sink)
        is_static = False
        static_tok = self._accept("static")
        if static_tok is not None:
            # §1c AMENDMENT v4.2 (MC 12486): function-scope `static`
            # locals are SUPPORTED. Static storage, the SAME constant-
            # initializer law as file scope (enforced by the §4 _const
            # walk at the data layer, gcc "initializer element is not
            # constant" rc1 measured); codegen binds the name to the
            # gcc-form `name.N` LOCAL symbol and it SHADOWS the same-
            # name global for the whole function (both measured).
            is_static = True
        extern_tok = self._accept("extern")
        is_extern = extern_tok is not None
        # §2.8 gnu89 inline specifiers: consume (in any remaining order);
        # only LINKAGE acts — blcc never inlines and has NO DCE.
        inline_tok = None
        while True:
            self._skip_gnu_attrs(decl_sink)  # attrs may interleave keywords
            tok = (self._accept("inline") or self._accept("__inline__")
                   or self._accept("__inline"))
            if tok is None:
                break
            inline_tok = inline_tok or tok
        inline_kind = ""
        if inline_tok is not None:
            inline_kind = ("extern-inline" if is_extern
                           else "static-inline" if is_static else "inline")
        if self._accept("typedef"):
            return self._parse_typedef()
        # M47 keyword row (T+12): bare `register` is a hint — parses and
        # DROPS (the stack machine has no allocation choice to make).
        # gnu89's address-of-register ERROR side is NOT implemented
        # (documented laxness; the run-pair leg takes no address).
        # M3 §3.10 (L10): the register SPECIFIER is now load-bearing for
        # the `register T name asm("reg")` bind shape (tracked below).
        is_register = False
        while self._accept("register") is not None:
            is_register = True
            self._skip_gnu_attrs(decl_sink)
        # M4 W-H (MC 12645): __auto_type — the jiffies.h:427 class. It
        # is a DECLARATION specifier, not a type word: it rides its own
        # ONE arm here, after the storage-class/inline/typedef/register
        # specifiers are consumed (so `static __auto_type` measures rc 0
        # both sides) and BEFORE parse_base_type (which must never see
        # it). MEASURED law table in tests/test_core_m4wh1.py.
        if self._at("__auto_type"):
            return self._parse_auto_type(self.s.next(), is_static, out)
        base = self.parse_base_type(decl_sink)
        out.extend(self._drain_pending())
        if self._bare_type_ok and self.s.accept_punct(";"):
            return out  # bare 'struct S;' / 'enum E { ... };' definition
        self._bare_type_ok = False
        while True:
            pos = self.s.peek()
            vsink: List[tuple] = []
            name, ty, is_fn, params = self.parse_declarator(base, ctx="var",
                                                            attr_sink=vsink)
            # M4 W2.5 (MC 12557): the SPEC-position attrs (decl_sink) apply
            # to EVERY declarator of the list (measured: `char
            # __attribute__((aligned(8))) gc, gd;` raises BOTH), merged
            # with this declarator's own tail attrs (vsink).
            sink = decl_sink + vsink
            for _nm, _a in sink:             # M42 typedef/decl-tail layout
                if _nm and isinstance(self._unqual(ty), ast.StructType):
                    reg = getattr(self, "struct_tag_attrs", None)
                    if reg is None:
                        reg = self.struct_tag_attrs = {}
                    reg[self._unqual(ty).tag] = tuple(
                        list(reg.get(self._unqual(ty).tag, ())) + [(_nm, _a)])
            oattr = tuple(x for x in sink if x[0] in ("aligned", "section"))
            _secs = {v for _k, v in oattr if _k == "section"}
            if len(_secs) > 1:
                # M4 W-I (MC 12650): probe r19 — TWO DIFFERENT sections
                # on one declarator (in ANY two positions of the one
                # sink: spec+star, star+tail, …) are the gcc ERROR
                # "section of 'f19' conflicts with previous
                # declaration" rc1. Picking one silently would be
                # SECTION LOSS; the SAME name twice is rc0 (probe dq) —
                # the judge is conflict-shaped, not count-shaped.
                self._sema(pos, "section of '{}' conflicts with previous"
                           " declaration (two '__section__' names on one"
                           " declarator, §1 row 9 measured gcc rc1 twin)"
                           .format(name), "section")
            for _nm, _a in oattr:      # M4 W2.5: the OBJECT-position
                if _nm == "aligned":   # aligned argument law (measured gcc
                    v = 16 if _a is None else self.fold_truthy(_a)
                    if v is None or v <= 0 or (v & (v - 1)):
                        # twins: aligned(3)/(−8)/non-constant all rc1;
                        # aligned(0) is rc0+IGNORE with corpus volume 0 —
                        # the wall stays (never silently mis-aligns).
                        self._sema(pos, "'aligned' needs a positive power-"
                                   "of-two constant (measured gcc twins "
                                   "3/negative/non-constant are rc1)",
                                   "aligned")
            bind = None
            alias = next((v for k, v in sink if k == "alias"), None)
            if alias is not None and not is_fn:
                self._sema(pos, "'alias' attribute on an OBJECT declarator "
                           "is not in the subset (§5 — the §6 nm-corner is "
                           "the FUNCTION form; object volume in the kernel "
                           "universe is 0, measured)")
            if self._at("asm", "__asm__"):
                # M3 §3.10 (L10): the `register T name asm("reg")` bind
                # suffix. Any OTHER use — a function declarator, or a
                # non-register object (the `__asm__("alias")` symbol form)
                # — is L4 LOUD (0 active x86_64 sites, §3 L4).
                st = self.s.peek()
                if is_fn or not is_register:
                    self._parse_err(
                        st, "declaration-suffix __asm__(\"…\") symbol "
                        "aliasing is L4 LOUD (0 active x86_64 sites; §3 "
                        "L4) — only a `register` OBJECT declarator may "
                        "bind a register (S17)")
                bind = self.asm_bind_suffix(st)
            if is_fn:
                if self.s.at_punct("{") and len(self.scopes) > 1:
                    self._parse_err(pos, "function definition inside a function is not in the subset")
                # M4 W1: `ty` IS the ast.FuncType the declarator built
                # (§1 row 1b/1d law) — the symbol table keeps the plain
                # RETURN type (the shipped `("fn", ret)` shape), the
                # FuncDecl carries ret/params/variadic from the FuncType.
                fty = ty
                ret = fty.ret
                # M4 W3 COMMIT-0 (MC 12563): the MEASURED re-declaration
                # law (implicit-builtin arity arm + the general fn-vs-fn
                # collision, the non-builtin twin stays LOUD) runs BEFORE
                # the name lands in the scope table.
                self._fn_redecl_law(name, fty, is_static, pos)
                self.define(name, ("fn", ret), pos)
                body = self.parse_function_body(params) if self.s.at_punct("{") else None
                if alias is not None and body is not None:
                    # gcc rc1 "alias definition is not allowed here" —
                    # the twin refuses to pick one of the two bodies.
                    self._sema(pos, "a function carrying 'alias' cannot "
                               "also have a definition (§6 twin of the "
                               "gcc error)", "alias")
                # M4 W2 COMMIT-0 (MC 12545): comma continuation for
                # PROTOTYPE lists — `int f(int x), h(int y);` (the S20/S22
                # probe wall; the same declarator-list grammar the object
                # row already rode). A DEFINITION cannot continue the list
                # (measured gcc ERROR "expected identifier or '(' before
                # ','" for `int f(void){…} , g;` — the twin stays LOUD).
                comma = body is None and self.s.accept_punct(",")
                if body is None and not comma:
                    self.s.expect_punct(";")
                out.append(ast.FuncDecl(
                    pos.file, pos.line, pos.col, name, ret, fty.params,
                    body, is_static, variadic=fty.variadic,
                    inline_kind=inline_kind, alias_of=alias,
                    attrs=oattr))            # M4 W2.5: section placement
                if comma:
                    continue
                break
            init = self.parse_initializer() if self.s.accept_punct("=") else None
            if init is not None:
                if isinstance(init, ast.CompoundLit) and \
                        isinstance(self._unqual(ty),
                                   (ast.ArrayType, ast.StructType)):
                    # §1 row 11 in initializer position: gnu89 makes an
                    # aggregate object initialized from a compound literal
                    # byte-identical to writing the brace list — use it.
                    init = init.init
                init = self._norm_init(ty, init, pos)   # §1 row 10
            if is_extern and init is None and not at_file:
                # an extern LOCAL re-declares a file-scope object; the
                # name already resolves through the enclosing scope —
                # nothing to register or emit (§2.8).
                if self.s.accept_punct(","):
                    continue
                self.s.expect_punct(";")
                break
            if (isinstance(ty, ast.ArrayType) and ty.size is None
                    and not isinstance(init, (ast.InitList, ast.StrLit))
                    and not is_extern):
                # T+10b: `extern unsigned char _ctype[];` declares without
                # defining — no size is needed here (the §1 row 10 walk
                # hit this wall on 7 corpus files behind the fn-ptr gate).
                self._sema(pos, "'array' declaration without size needs an initializer list (§4)")
            if (is_static and not at_file
                    and name in self.scopes[-1]):
                # gcc rc1 measured: "'x' redeclared as different kind of
                # symbol" — a static local may not re-share a PARAMETER
                # (or same-scope object) name inside the function.
                self._sema(pos, "'static' local '{}' collides with a name "
                           "declared in this scope (parameter or object)"
                           .format(name))
            self.define(name, ("var", ty), pos)
            # M4 W2.5 (MC 12557): an AUTO local `aligned(N)` beyond 16 is
            # LOUD-DIV (measured: gcc REALIGNS the frame — `andq $-64,
            # %rsp`, rc0; blcc's frame base is the 16-ABI §6 law). Up to
            # 16 the slot raise is HONEST; static storage is fine at any
            # N (the .align data law, ARM 3).
            if not at_file and not is_static and not is_extern:
                for _nm, _a in oattr:
                    if _nm == "aligned":
                        v = 16 if _a is None else self.fold_truthy(_a)
                        if v is not None and v > 16:
                            self._sema(pos, "'aligned' beyond 16 on an "
                                       "auto local is LOUD-DIV (measured: "
                                       "gcc realigns the frame, blcc's "
                                       "frame base is the 16-ABI; §6) — "
                                       "never a silently-misaligned slot")
            out.append(ast.VarDecl(pos.file, pos.line, pos.col, name, ty,
                                   init, is_static,
                                   is_extern=(is_extern and init is None),
                                   asm_bind=bind, attrs=oattr))
            if self.s.accept_punct(","):
                continue
            self.s.expect_punct(";")
            break
        return out

    def _parse_auto_type(self, at_tok, is_static, out):
        """M4 W-H (MC 12645): `__auto_type ID = init;`.

        THE MEASURED LAW (gcc 11.4 gnu89, probes .tmp/m4-wh/probes/):
        ID takes the type of `init` after VALUE CONVERSION — arrays and
        functions DECAY, TOP-level qualifiers DROP, pointed-to
        qualifiers KEEP. One mechanism: the SAME TypeOf node §2.6/§1 row
        6c rides, flagged `auto`; TypeMap._untype materializes it with
        that law (so `_ty`, `_size`, stmt-expr locals, the data layer
        and every existing consumer resolve it — no second typeer).
        Equivalence AND the measured differences vs `__typeof__(init)`
        are pinned in tests/test_core_m4wh1.py (typeof does NOT decay
        or drop: `__typeof__(ca)` is int[4]; `__typeof__(ci) v; v = 7;`
        rc 1 while the auto form is rc 0).

        Reject twins (all measured gcc rc 1, sentences mirrored): the
        declarator must be a PLAIN identifier; the initializer is
        REQUIRED; a bit-field init; a `void` init (variable or field
        declared void); a SECOND declarator. ACCEPT: file scope,
        `static`, statement expressions (the corpus shape).
        """
        t = self.s.peek()
        if t.kind != "id":
            self._parse_err(
                t, "'__auto_type' requires a plain identifier as "
                "declarator (measured gcc rc1: '*v =', 'v[2] =', "
                "'(v) =' are not pointer/array-of-inferred)")
        name_tok = self.s.next()
        # MEASURED sentence split: a `[`/`(` after the name is the
        # DECLARATOR arm (gcc: "requires a plain identifier as
        # declarator" — array-decl probe), NOT the missing-init arm;
        # the pointer form already LOUDed above (peek is `*`, not id).
        if self.s.at_punct("[") or self.s.at_punct("("):
            self._parse_err(
                self.s.peek(), "'__auto_type' requires a plain identifier "
                "as declarator (measured gcc rc1: the array/function "
                "declarator forms are not inferred types)")
        if self.s.accept_punct("=") is None:
            self._sema(name_tok, "'__auto_type' requires an initialized "
                       "data declaration (measured gcc rc1: the type "
                       "comes from the initializer or nowhere)")
        init = self.expr.parse_expression()
        if self._auto_bitfield(init):
            self._sema(name_tok, "'__auto_type' used with a bit-field "
                       "initializer (measured gcc rc1; typeof(bit-field) "
                       "is the same refusal — the member has no value "
                       "form)")
        self._auto_void(name_tok, init)
        if self.s.at_punct(","):
            self._parse_err(
                self.s.peek(), "'__auto_type' may only be used with a "
                "single declarator (measured gcc rc1: each variable "
                "gets its own declaration)")
        self.s.expect_punct(";")
        ty = ast.TypeOf(at_tok.file, at_tok.line, at_tok.col, init, None,
                        auto=True)
        self.define(name_tok.text, ("var", ty), name_tok)
        out.append(ast.VarDecl(at_tok.file, at_tok.line, at_tok.col,
                               name_tok.text, ty, init, is_static,
                               is_extern=False, asm_bind=None, attrs=()))
        return out

    def _auto_bitfield(self, init) -> bool:
        """Light check for the measured bit-field reject: a Select whose
        declared member carries a bit width (walked through the SAME
        anon-promotion walk walk_fields mirrors). Coverage: the forms
        the light mirror types (Ident/Select/arrow bases); a base the
        mirror cannot type is volume 0 in the corpus and rides the
        engine's ordinary member read — named limit, never silent
        WRONG (the read itself ships; only the gcc rc1 twin is
        light-side)."""
        if not isinstance(init, ast.Select):
            return False
        base = self.expr_type(init.base)
        if isinstance(base, ast.Qualified):
            base = self._unqual(base)
        if isinstance(base, ast.PtrType):
            base = self._unqual(base.inner)
        if not isinstance(base, ast.StructType):
            return False

        def walk(members):
            for m in members:
                if m.name is not None:
                    if m.name == init.field and \
                            getattr(m, "width", None) is not None:
                        return True
                    continue
                if getattr(m, "width", None) is None:
                    nested = self.struct_tags.get(m.type.tag)
                    if nested and walk(nested):
                        return True
            return False
        return walk(self.struct_tags.get(base.tag, ()))

    def _auto_void(self, name_tok, init) -> None:
        """Measured `void` twin (gcc: `variable or field 'v' declared
        void`). Light side: a Cast to void, or a call to a KNOWN
        void-returning function; everything else the engine can only
        see at materialization — TypeMap._untype's auto arm keeps the
        matching sentence for the forms the mirror cannot type."""
        ty = self.expr_type(init)
        void = isinstance(ty, ast.BuiltinType) and ty.name == "void"
        if not void and isinstance(init, ast.Call) and \
                isinstance(init.callee, ast.Ident):
            sym = self.lookup(init.callee.name)
            if sym is not None and sym[0] == "fn":
                ret = self._unqual(sym[1])
                void = isinstance(ret, ast.BuiltinType) and ret.name == "void"
        if void:
            self._sema(name_tok, "variable or field '%s' declared void "
                       "(measured gcc rc1: there is no type to infer "
                       "from a void expression)" % name_tok.text)

    def _parse_typedef(self) -> List[ast.Node]:
        out: List[ast.Node] = []
        spec_sink: List[tuple] = []     # M4 W2.5: spec-position attrs
        base = self.parse_base_type(spec_sink)
        out.extend(self._drain_pending())
        while True:
            pos = self.s.peek()
            tsink: List[tuple] = []
            name, ty, is_fn, _ = self.parse_declarator(base, ctx="typedef",
                                                       attr_sink=tsink)
            if is_fn:
                # M4 W1 (§1 row 1c): typedef of a FUNCTION TYPE is a
                # synonym for that function type — the kernel spells it
                # `typedef void __signalfn_t(int);` in 586 streams and
                # `wait_bit_action_f` in 461. The typedef stores the
                # FuncType; `FT *p;` then builds the fn-ptr. The M1 wall
                # ("typedef of a function type is a function pointer")
                # dies here.
                pass
            else:
                bare = ty is base
                u = self._unqual(ty)
                if bare and isinstance(u, ast.PtrType) and \
                        isinstance(u.inner, ast.FuncType):
                    # §1 row 1h — LOUD TWIN kept by v4 §7 W1 (census
                    # NAME-KEYED; the universe site is scripts/mod/modpost
                    # `typedef FN_T x;`, HOST tier): a bare typedef NAME
                    # over an existing fn-ptr typedef just RENAMES it —
                    # deferred with its wave. A star-spelled `typedef
                    # hnd_t *pp_t;` builds a NEW type and passes.
                    self._parse_err(pos, "'function pointer' typedef "
                                    "chain (row 1h) is not in the subset "
                                    "(§5 LOUD twin)")
            for _nm, _a in spec_sink + tsink:  # M42 typedef-tail layout
                if _nm == "section":
                    # M4 W-I (MC 12650): measured gcc rc1 twin (probe p2
                    # and s2 — ALSO for a typedef over a struct ptr):
                    # "section attribute not allowed for 'td'" — a
                    # typedef names a TYPE, it places nothing. Mirrors
                    # the member/param sentence; tip had NO judge for
                    # this sink (silent loss closed here).
                    self._sema(pos, "section attribute not allowed for "
                               "'{}' (§1 row 9, measured gcc rc1 twin)"
                               .format(name), "section")
                if isinstance(self._unqual(ty), ast.StructType):
                    reg = getattr(self, "struct_tag_attrs", None)
                    if reg is None:
                        reg = self.struct_tag_attrs = {}
                    reg[self._unqual(ty).tag] = tuple(
                        list(reg.get(self._unqual(ty).tag, ())) + [(_nm, _a)])
                elif _nm in ("aligned", "packed"):
                    # M4 W2.5 (MC 12557): a layout attr on a typedef of a
                    # NON-struct type raises the alignment OF THE TYPEDEF
                    # NAME only (measured: the tag's and the underlying
                    # type's own alignof stay put) — blcc has no per-name
                    # layout store and the volume is 0 measured (every
                    # typedef+aligned site in the 706 streams is the
                    # guid_t shape). LOUD, never a silent strip.
                    self._sema(pos, "'{}' on a typedef of a non-struct "
                               "type is LOUD-DIV (gcc raises the NAME's "
                               "alignment only; corpus volume 0, measured)"
                               .format(_nm), _nm)
            self.define(name, ("typedef", ty), pos)
            out.append(ast.TypedefDecl(pos.file, pos.line, pos.col, name, ty))
            if self.s.accept_punct(","):
                continue
            self.s.expect_punct(";")
            break
        return out

    def _drain_pending(self) -> List[ast.Node]:
        pending, self._pending = self._pending, []
        return pending

    def parse_initializer(self) -> ast.Node:
        pos = self.s.peek()
        if self.s.accept_punct("{"):
            items: List[ast.Node] = []
            while not self.s.at_punct("}"):
                if self.s.at_punct(".") or self.s.at_punct("["):
                    desigs = self._parse_designators()
                    self.s.expect_punct("=")
                    items.append(ast.Desig(pos.file, pos.line, pos.col,
                                           desigs, self.parse_initializer()))
                else:
                    items.append(self.parse_initializer())
                if not self.s.accept_punct(","):
                    break
            self.s.expect_punct("}")
            return ast.InitList(pos.file, pos.line, pos.col, tuple(items))
        return self.expr.parse_expression()

    def _parse_designators(self) -> Tuple[tuple, ...]:
        out: List[tuple] = []
        while True:
            if self.s.accept_punct(".") is not None:
                out.append(("f", self.s.expect_id("parse").text))
                continue
            lb = self.s.accept_punct("[")
            if lb is not None:
                lo = self.expr.parse_expression()
                if self.s.accept_punct("...") is not None:
                    hi = self.expr.parse_expression()
                    out.append(("r", lo, hi))
                else:
                    out.append(("i", lo))
                self.s.expect_punct("]")
                continue
            break
        if not out:
            self._parse_err(self.s.peek(), "designator expected "
                                          "(§1 row 10)")
        return tuple(out)

    # -- §1 row 10: designated-initializer NORMALIZATION ----------------------

    def _unqual(self, ty):
        while isinstance(ty, ast.Qualified):
            ty = ty.inner
        return ty

    def _init_slots(self, ty):
        """Slot view (name_or_None, type, off, size) in declaration order
        for a struct/union — the designator walk does NOT promote anonymous
        members (it DESCENDS their slots instead). Same layout family as
        _offsetof_flat; None = incomplete member layout (§2.13 posture)."""
        ty = self._unqual(ty)
        if not isinstance(ty, ast.StructType):
            return None
        members = self.struct_tags.get(ty.tag)
        if members is None:
            return None
        slots: List[tuple] = []
        off = 0
        packed = self._attr_packed(ty)
        for m in members:
            msz = self._csize(m.type)
            mal = self._calign(m.type)
            if msz is None or mal is None:
                return None
            mal = self._malign_f(m, packed, mal, ty)
            if ty.is_union:
                slots.append((m.name, m.type, 0, msz))
            else:
                o = (off + mal - 1) // mal * mal
                slots.append((m.name, m.type, o, msz))
                off = o + msz
        return slots

    def _desig_idx(self, node, at) -> int:
        v = self.fold_truthy(node)
        if v is None:
            self._sema(at, "array designator requires a constant index "
                       "(§1 row 10)")
        if v < 0:
            self._sema(at, "array designator index must be non-negative "
                       "(§1 row 10)")
        return v

    def _find_field_slot(self, slots, ty, name, at):
        """Resolve `.name` against a slot list: a named slot wins; else a
        PROMOTED name inside an anonymous member — descend (T+7 promotion
        law; returns the anon slot + the name to resolve INSIDE it)."""
        for i, (sname, sty, mo, ssz) in enumerate(slots):
            if sname == name:
                return i, ()
        from blcc.types import walk_fields
        for i, (sname, sty, mo, ssz) in enumerate(slots):
            if sname is None:
                inner = self.struct_tags.get(self._unqual(sty).tag) \
                    if isinstance(self._unqual(sty), ast.StructType) \
                    else None
                if inner is not None and any(n2 == name
                                             for n2, _t2 in
                                             walk_fields(inner,
                                                         self.struct_tags)):
                    return i, (("f", name),)
        self._sema(at, "designator: no member '{}' in the initialized "
                   "aggregate (§1 row 10)".format(name))

    def _merge_init(self, a, b, pos):
        """Two normalizations of the SAME subobject merge per C: a later
        designation overwrites leaf-by-leaf (redesignation last-wins), a
        ZERO fill never erases what an earlier item placed."""
        if a is None or isinstance(a, ast.ZeroFill):
            return b
        if isinstance(b, ast.ZeroFill):
            return a
        if isinstance(a, ast.InitList) and isinstance(b, ast.InitList):
            out = []
            for i in range(max(len(a.items), len(b.items))):
                out.append(self._merge_init(
                    a.items[i] if i < len(a.items)
                    else ast.ZeroFill(pos.file, pos.line, pos.col),
                    b.items[i] if i < len(b.items)
                    else ast.ZeroFill(pos.file, pos.line, pos.col), pos))
            return ast.InitList(pos.file, pos.line, pos.col, tuple(out))
        return b                        # last written leaf wins

    def _norm_init(self, ty, init, at):
        """Normalize ONE brace level: designators expand into a positional
        list padded with ZeroFill; positional runs RESUME AFTER the last
        designated member/element (gnu89 measured, d-mix leg); repeated
        designation = later wins; ranges fill every index; designator
        runs MIX with nested paths by RE-WRAPPING the tail ([0].hi = 5 →
        index here, `.hi` descends into the element's own normalization)."""
        ty = self._unqual(ty)
        if isinstance(init, ast.Desig):
            # re-wrapped nested path ([0].hi = 5 descends here as a bare
            # designator run): same brace-level normalization
            init = ast.InitList(init.file, init.line, init.col, (init,))
        if not isinstance(init, ast.InitList):
            if isinstance(init, ast.Desig):
                self._sema(at, "designator used on an object of "
                           "non-aggregate type (§1 row 10)")
            return init
        if not any(isinstance(it, ast.Desig) for it in init.items):
            return init                          # positional: as written
        pos = init
        if isinstance(ty, ast.ArrayType):
            esz = self._csize(ty.inner)
            if esz is None:
                self._sema(at, "cannot size array elements for the "
                           "initializer (§1 row 10)")
            declared = None
            if ty.size is not None:
                declared = self._desig_idx(ty.size, at)
            out: List[ast.Node] = []
            cur = 0

            def pad_to(k):
                while len(out) <= k:
                    out.append(ast.ZeroFill(pos.file, pos.line, pos.col))

            for it in init.items:
                if isinstance(it, ast.Desig):
                    kind = it.desigs[0][0]
                    if kind == "f":
                        self._sema(at, "'.field' designator in an array "
                                   "initializer (§1 row 10)")
                    if kind == "i":
                        idxs = [self._desig_idx(it.desigs[0][1], at)]
                        rest = it.desigs[1:]
                    else:
                        lo = self._desig_idx(it.desigs[0][1], at)
                        hi = self._desig_idx(it.desigs[0][2], at)
                        if hi < lo:
                            self._sema(at, "range designator '{}' beyond "
                                       "'{}' (§1 row 10)".format(hi, lo))
                        if hi - lo > 2 ** 20:
                            self._sema(at, "range designator exceeds the "
                                       "implementation limit (§4)")
                        idxs = list(range(lo, hi + 1))
                        rest = it.desigs[1:]
                    for k in idxs:
                        if declared is not None and k >= declared:
                            self._sema(at, "too many initializers for "
                                       "{} elements (§4)".format(declared))
                        pad_to(k)
                        out[k] = self._merge_init(
                            out[k], self._norm_init(
                                ty.inner,
                                ast.Desig(pos.file, pos.line, pos.col,
                                          rest, it.value) if rest
                                else it.value, at), pos)
                    cur = max(idxs) + 1
                else:
                    if declared is not None and cur >= declared:
                        self._sema(at, "too many initializers for {} "
                                   "elements (§4)".format(declared))
                    pad_to(cur)
                    out[cur] = self._norm_init(ty.inner, it, at)
                    cur += 1
            return ast.InitList(pos.file, pos.line, pos.col, tuple(out))
        slots = self._init_slots(ty)
        if slots is None:
            return init                          # non-aggregate: as written
        out = [None] * len(slots)
        cur = 0
        for it in init.items:
            if isinstance(it, ast.Desig):
                kind = it.desigs[0][0]
                if kind != "f":
                    self._sema(at, "'[index]' designator in a struct/"
                               "union initializer (§1 row 10)")
                s_i, descend = self._find_field_slot(slots, ty,
                                                     it.desigs[0][1], at)
                rest = (descend + it.desigs[1:]) if descend \
                    else it.desigs[1:]
                out[s_i] = self._merge_init(
                    out[s_i], self._norm_init(
                        slots[s_i][1],
                        ast.Desig(pos.file, pos.line, pos.col, rest,
                                  it.value) if rest else it.value,
                        at), pos)
                cur = s_i + 1
            else:
                if cur >= len(slots):
                    self._sema(at, "excess elements in struct initializer "
                               "(§4)")
                out[cur] = self._norm_init(slots[cur][1], it, at)
                cur += 1
        filled = tuple(z if z is not None else
                       ast.ZeroFill(pos.file, pos.line, pos.col)
                       for z in out)
        return ast.InitList(pos.file, pos.line, pos.col, filled)

    def parse_function_body(self, params: Tuple[ast.Param, ...]) -> ast.Node:
        opening = self.s.expect_punct("{")
        self.scopes.append({})
        for p in params:
            if p.name:
                self.scopes[-1][p.name] = ("var", p.type)
        stmts = self._block_stmts_until_brace()
        self.scopes.pop()
        return ast.Compound(opening.file, opening.line, opening.col, stmts)

    def _block_stmts_until_brace(self) -> Tuple[ast.Node, ...]:
        stmts: List[ast.Node] = []
        while not self.s.at_punct("}"):
            stmts.extend(self.parse_block_item())
        self.s.expect_punct("}")
        return tuple(stmts)

    # -- translation unit ---------------------------------------------------------------

    def parse_translation_unit(self) -> ast.TranslationUnit:
        decls: List[ast.Node] = []
        while self.s.peek().kind != "eof":
            if self.s.accept_punct(";"):
                continue
            if self.starts_decl():
                decls.extend(self.parse_decl(at_file=True))
            else:
                self._parse_err(self.s.peek(), "expected a top-level declaration")
        eof = self.s.peek()
        return ast.TranslationUnit(eof.file, eof.line, eof.col, tuple(decls))

    # -- statements --------------------------------------------------------------------------

    def parse_block_item(self) -> List[ast.Node]:
        if self.starts_decl():
            return self.parse_decl(at_file=False)
        return [self.parse_statement()]

    def parse_compound(self) -> ast.Compound:
        opening = self.s.expect_punct("{")
        self.scopes.append({})
        stmts = self._block_stmts_until_brace()
        self.scopes.pop()
        return ast.Compound(opening.file, opening.line, opening.col, stmts)

    def parse_statement(self) -> ast.Node:
        t = self.s.peek()
        if t.kind == "kw":
            handler = self._STMT_HANDLERS.get(t.text)
            if handler is not None:
                return getattr(self, handler)()
            if t.text == "goto":
                # M2 §1 row 4: real goto. `goto *p` stays a LOUD parse wall
                # (§1 row 4c / M56 — the new grammar must not eat the '*').
                self.s.next()
                if self.s.at_punct("*"):
                    st = self.s.next()
                    self._parse_err(
                        st, "a computed 'goto' (goto *ptr) is not in the "
                        "subset (§5 — DEFER, 0 sites in the 692)")
                lt = self.s.expect_id()
                self.s.expect_punct(";")
                return ast.Goto(t.file, t.line, t.col, lt.text)
            if t.text == "__label__":
                return self.parse_label_decl()
            if t.text in ("break", "continue"):
                self.s.next()
                self.s.expect_punct(";")
                cls = ast.Break if t.text == "break" else ast.Continue
                return cls(t.file, t.line, t.col)
            if t.text == "return":
                self.s.next()
                # W-G (MC 12633): `return a, b;` — the grammar's return
                # takes a full `expression` (m25/m12: value = RIGHT).
                value = (None if self.s.at_punct(";")
                         else self.expr.parse_comma_expression())
                self.s.expect_punct(";")
                return ast.Return(t.file, t.line, t.col, value)
            if self.starts_decl():
                self._parse_err(t, "'declaration' in an unbraced statement — use a '{ ... }' block")
        if t.kind == "id" and self.s.peek(1).kind == "punct" and \
                self.s.peek(1).text == ":":
            # M2 §1 row 4: real label statement (`lab: stmt`), flat
            # function-wide namespace (§2.5); a label and an identifier of
            # the same spelling COEXIST — the label namespace is separate.
            self.s.next()                      # the identifier
            self.s.next()                      # ':'
            stmt = self.parse_statement()
            return ast.Label(t.file, t.line, t.col, t.text, stmt)
        if t.kind == "punct" and t.text == "{":
            return self.parse_compound()
        if self.s.at_punct(";"):
            pos = self.s.next()
            return ast.ExprStmt(pos.file, pos.line, pos.col, None)
        # W-G (MC 12633): expression statements take the comma (m26).
        expr = self.expr.parse_comma_expression()
        self.s.expect_punct(";")
        return ast.ExprStmt(expr.file, expr.line, expr.col, expr)

    def _parse_control_head(self, kw: str):
        t = self._accept(kw)
        self.s.expect_punct("(")
        # W-G (MC 12633): selection/iteration conditions are
        # `expression` slots — the comma rides (m8/m11).
        cond = self.expr.parse_comma_expression()
        self.s.expect_punct(")")
        return t, cond

    def parse_if(self) -> ast.Node:
        t, cond = self._parse_control_head("if")
        then = self.parse_statement()
        orelse = self.parse_statement() if self._accept("else") else None
        return ast.If(t.file, t.line, t.col, cond, then, orelse)

    def parse_while(self) -> ast.Node:
        t, cond = self._parse_control_head("while")
        return ast.While(t.file, t.line, t.col, cond, self.parse_statement())

    def parse_do_while(self) -> ast.Node:
        t = self._accept("do")
        body = self.parse_statement()
        if self._accept("while") is None:
            self._parse_err(self.s.peek(), "expected 'while' after 'do' body")
        self.s.expect_punct("(")
        cond = self.expr.parse_comma_expression()   # W-G (MC 12633)
        self.s.expect_punct(")")
        self.s.expect_punct(";")
        return ast.DoWhile(t.file, t.line, t.col, body, cond)

    def parse_for(self) -> ast.Node:
        t = self._accept("for")
        self.s.expect_punct("(")
        init = None
        if self.s.at_punct(";"):
            self.s.expect_punct(";")
        elif self.starts_decl():
            decls = self.parse_decl(at_file=False)  # consumes its ';'
            var_decls = [d for d in decls if isinstance(d, ast.VarDecl)]
            if len(decls) != 1 or not var_decls:
                self._sema(self.s.peek(), "'for' init must be a single simple "
                                          "declaration (§5)", "declaration")
            init = var_decls[0]
        else:
            expr = self.expr.parse_comma_expression()
            init = ast.ExprStmt(expr.file, expr.line, expr.col, expr)
            self.s.expect_punct(";")
        # W-G (MC 12633): ALL THREE for clauses are `expression` slots
        # (m3/m4/m29) — this also carries the legacy W-D "for-comma
        # increment" class (276 files): ONE comma mechanism, the wave
        # re-ranked behind W-G per AMENDMENT-5.
        cond = None if self.s.at_punct(";") \
            else self.expr.parse_comma_expression()
        self.s.expect_punct(";")
        step = None if self.s.at_punct(")") \
            else self.expr.parse_comma_expression()
        self.s.expect_punct(")")
        return ast.For(t.file, t.line, t.col, init, cond, step, self.parse_statement())

    # -- switch -----------------------------------------------------------------------------------

    def parse_label_decl(self) -> ast.Node:
        # §1 row 4d: `__label__ a, b;` — names ONLY; the labels themselves
        # are ordinary `a:` statements (M2-C1 map resolves &&a).
        t = self._accept("__label__")
        names: List[str] = []
        while True:
            names.append(self.s.expect_id("parse").text)
            if not self.s.accept_punct(","):
                break
        self.s.expect_punct(";")
        return ast.LabelDecl(t.file, t.line, t.col, tuple(names))

    def parse_case_arm(self):
        """`case EXPR :` or `case EXPR ... EXPR :` (§1 row 4b, gnu89 range
        extension IN this gcc — measured; reversed range is an EMPTY set,
        gcc accepts it silently)."""
        ct = self.s.next()                      # 'case'
        lo = self.parse_int_constant("'case' label needs an integer "
                                     "constant (§4)")
        if self.s.accept_punct("..."):
            hi = self.parse_int_constant("'case' range bound needs an "
                                         "integer constant (§4b)")
            self.s.expect_punct(":")
            return ("range", (lo, hi), ct)
        self.s.expect_punct(":")
        return ("case", lo, ct)

    def parse_switch(self) -> ast.Node:
        t = self._accept("switch")
        self.s.expect_punct("(")
        control = self.expr.parse_comma_expression()   # W-G (MC 12633)
        self.s.expect_punct(")")
        self.s.expect_punct("{")
        self.switch_depth += 1
        stmts: List[ast.Node] = []
        labels: List[tuple] = []
        while not self.s.at_punct("}") and self.s.peek().kind != "eof":
            if self._at("case"):
                kind, value, ct = self.parse_case_arm()
                labels.append((kind, value, ct))
                continue
            if self._at("default"):
                dt = self.s.next()
                self.s.expect_punct(":")
                labels.append(("default", None, dt))
                continue
            stmt = self.parse_statement()
            for kind, value, ltok in reversed(labels):
                stmt = self._wrap_case(kind, value, ltok, stmt)
            labels = []
            stmts.append(stmt)
        for kind, value, ltok in labels:  # trailing labels: empty arms are legal
            stmts.append(self._wrap_case(kind, value, ltok, None))
        self.s.expect_punct("}")
        self.switch_depth -= 1
        self._check_case_labels(stmts)
        return ast.Switch(t.file, t.line, t.col, control, tuple(stmts))

    def _wrap_case(self, kind, value, ltok, stmt) -> ast.Node:
        if kind == "case":
            return ast.Case(ltok.file, ltok.line, ltok.col, value, stmt)
        if kind == "range":
            return ast.CaseRange(ltok.file, ltok.line, ltok.col,
                                 value[0], value[1], stmt)
        return ast.Default(ltok.file, ltok.line, ltok.col, stmt)

    def parse_nested_label(self) -> ast.Node:
        t = self.s.peek()  # 'case' / 'default' outside the body loop
        if self.switch_depth == 0:
            self._sema(t, "'{}' label outside a 'switch' is not in the subset (§4)".format(t.text))
        if t.text == "case":
            kind, value, ct = self.parse_case_arm()
            return self._wrap_case(kind, value, ct, self.parse_statement())
        self.s.next()
        self.s.expect_punct(":")
        return ast.Default(t.file, t.line, t.col, self.parse_statement())

    def _check_case_labels(self, stmts: List[ast.Node]) -> None:
        # §2.5 dup/overlap RULES (M37; oracle-worded gcc 11.4): duplicate
        # value = error; value inside an earlier range = "duplicate (or
        # overlapping) case value"; two overlapping ranges likewise; a
        # SECOND default in a SECOND switch of one function is FINE (each
        # switch's labels are its own — the inner-Switch skip below).
        seen: Dict[int, bool] = {}
        spans: List[tuple] = []              # (lo, hi) ranges
        has_default = False
        stack = list(stmts)
        while stack:
            s = stack.pop()
            if isinstance(s, ast.Switch):
                continue  # inner switch: its labels are its own business
            if isinstance(s, ast.Case):
                if s.value in seen:
                    self._sema(s, "'duplicate case' label value {} in one switch (§4)".format(s.value))
                seen[s.value] = True
                for (lo, hi, _lt) in spans:
                    if lo <= s.value <= hi:
                        self._sema(s, "'duplicate (or overlapping) case' "
                                   "value {} lies in an earlier case range "
                                   "({} ... {}) (§2.5)".format(
                                       s.value, lo, hi),
                                   "duplicate (or overlapping) case value")
            elif isinstance(s, ast.CaseRange):
                for v in seen:                             # small, exact
                    if s.lo <= v <= s.hi:
                        self._sema(s, "'duplicate (or overlapping) case' "
                                   "value {} in one switch (§2.5)".format(v),
                                   "duplicate (or overlapping) case value")
                if s.lo <= s.hi:
                    for (lo, hi, lt) in spans:
                        if lo <= s.hi and s.lo <= hi:
                            self._sema(s, "'duplicate (or overlapping) "
                                       "case' range {} ... {} overlaps "
                                       "{} ... {} (§2.5)".format(
                                           s.lo, s.hi, lo, hi),
                                       "duplicate (or overlapping) case value")
                    spans.append((s.lo, s.hi, s))
            elif isinstance(s, ast.Default):
                if has_default:
                    self._sema(s, "'default' appears more than once in one switch (§4)", "default")
                has_default = True
            if isinstance(s, ast.Compound):
                stack.extend(s.body)
            elif isinstance(s, (ast.Case, ast.Default, ast.CaseRange)):
                if s.stmt is not None:
                    stack.append(s.stmt)
            elif isinstance(s, ast.Label):
                if s.stmt is not None:
                    stack.append(s.stmt)
            elif isinstance(s, ast.If):
                stack.append(s.then)
                if s.orelse is not None:
                    stack.append(s.orelse)
            elif isinstance(s, (ast.While, ast.DoWhile, ast.For)):
                stack.append(s.body)


def parse_tokens(toks: List[Token]) -> ast.TranslationUnit:
    return Parser(toks).parse_translation_unit()


def parse_text(text: str, filename: str = "<input>",
               require_main: bool = False) -> ast.TranslationUnit:
    """Lex + parse a source string (no preprocessor run). Used by tests and
    by the driver after preprocessing (see driver.py for the full pipeline)."""
    lines = [SourceLine(filename, i + 1, ln) for i, ln in enumerate(text.splitlines())]
    toks = Lexer(lines).tokenize()
    tu = parse_tokens(toks)
    if require_main and not any(
            isinstance(d, ast.FuncDecl) and d.name == "main" and d.body
            for d in tu.decls):
        eof = toks[-1]
        raise DiagError("sema", eof.file, eof.line, eof.col,
                        "no 'main' function defined (§8)", "<eof>")
    return tu
