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
from blcc.types import (CompatLawMixin, UNSIGNED_NAMES, _RANK,
                        call_target_ret)
from blcc.parse_fold import ParseFoldMixin
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
                             # M4 W-J (MC 12655): the C11 static-assertion
                             # IS a declaration — parse_decl intercepts it
                             # BEFORE any base-type walk.
                             "_Static_assert",
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


class Parser(ParseFoldMixin, AsmParseMixin, CompatLawMixin):
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
        # M4 W-Q (MC 12712): block-scope TAG namespace — NAME -> identity.
        # The layout tables (struct_tags / codegen.structs) key on the
        # IDENTITY, not the name (measured law q05/q06: ONE name, TWO live
        # layouts in one TU); file scope keeps the name as identity (all
        # pre-W-Q behavior byte-unchanged). Pushed/popped with self.scopes.
        self._tag_scopes: List[Dict[str, str]] = [{}]
        self._file_tags = set()           # names bound as tags at file
        self._blk_tag_n = 0               # block-tag identity mint counter
        # M4 W3 COMMIT-0 (MC 12563): the re-declaration ledger — name →
        # (return key, param key list or None for the old-style empty
        # list, variadic). ONE table, judged by _fn_redecl_law.
        self.fn_decls: Dict[str, Tuple] = {}
        self._pending: List[ast.Node] = []  # Struct/EnumDecls made by types
        # M4 W-U COMMIT-2 (MC 12739): an `extern` local naming a thing
        # this TU never declares is a REFERENCE to an object defined in
        # another TU; the binding is DEFERRED to TU end (where the file
        # scope is complete) so a later file-scope definition wins.
        self._ext_refs: dict = {}   # name -> (pos, type), deduped
        self._bare_type_ok = False          # a tag/enum definition just read
        self.switch_depth = 0
        self._sizing = set()   # M4 W-K (MC 12663, gate F-5): tags whose
        #                              fold-mirror layout is IN PROGRESS;
        #                              re-entry IS the circular aligned/
        #                              sizeof dependency (never legal C).
        self._ft_run = False   # M4 W-K (MC 12663, gate F-1): the last
        #                              EFFECTIVE item was an FT attribute-
        #                              declaration (empty stmts/empty attr
        #                              decls do NOT reset; real items and
        #                              labels do — measured grid).
        self.expr = ExprParser(self.s, self.is_typename, self.parse_type,
                               self.callable_known, self.expr_type,
                               self.parse_stmt_expr, self.fold_truthy,
                               self.resolve_offsetof,
                               parse_init=self.parse_initializer,
                               norm_init=self._norm_init,
                               objsize=self.resolve_objsize,
                               volatile_final=self.volatile_final)

    # -- §2.4 GNU statement-expressions (M2-C5 leg 1) ------------------------

    def parse_stmt_expr(self, open_tok: Token) -> ast.Node:
        """`({ stmts… final; })` — the primary already consumed `(` AND
        verified `{` opens the braced group; it is consumed here."""
        self.s.expect_punct("{")
        self.scopes.append({})
        self._tag_scopes.append({})
        stmts: List[ast.Node] = []
        while not self.s.at_punct("}"):
            if self.s.peek().kind == "eof":
                self._parse_err(open_tok, "unterminated statement expression")
            stmts.extend(self.parse_block_item())
        self._tag_scopes.pop()
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

    # -- CompatLawMixin host hooks (M4 W-L, MC 12665) ----------------------

    def _tyof_materialize(self, expr):
        # the fold-side materializer: the SHIPPED expr_type mirror — the
        # same peel _csize/_calign ride. None flows through the law's
        # isinstance chain as "not compatible": the SAFE direction
        # (the const_p no-lie doctrine), never a crash, never a false 1.
        return self.expr_type(expr)


    def _calign(self, ty) -> Optional[int]:
        """§2.13 alignof mirror entry: same W-K cycle guard (ONE set) as
        `_csize`; the law is `_calign_impl`."""
        key = self._layout_enter(ty)
        if key is None:
            return self._calign_impl(ty)
        try:
            return self._calign_impl(ty)
        finally:
            self._sizing.discard(key)

    def _calign_impl(self, ty) -> Optional[int]:
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
            if ty.name == "void":
                return 1        # W-K mirror: __alignof__(void) MEASURED 1
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
        # M4 W-K (MC 12663): the TYPE slot may spell `typeof(...)` — the
        # kernel's container_of() family (`offsetof(typeof(*(ptr)), m)`:
        # 176 stream first-blockers, 88 of them resource_ext.h:74). The
        # MEASURED oracle (ot_* probes): the builtin resolves the member
        # path THROUGH the materialized type — pointer targets included
        # (offsetof(typeof(*p), next) rc0), dot-chains and array members
        # included; `->` INSIDE a path stays rc1 (the chain parser never
        # sees that arrow — unchanged law). Materialize ONCE at the walk
        # ENTRY through the same expr_type mirror the rest of the fold
        # uses; every step arm below rides untouched.
        while True:
            if isinstance(cur, ast.Qualified):
                cur = cur.inner
                continue
            if isinstance(cur, ast.TypeOf):
                cur = cur.typ if cur.typ is not None else \
                    self.expr_type(cur.expr)
                continue
            break
        off = 0
        dyn = None                     # M4 W-J: runtime term, once built
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
            if isinstance(step, tuple) and step[0] == "dyn":
                # M4 W-J (MC 12655): the RUNTIME INDEX arm (the rbtree_
                # latch.h:72 `node[idx]` family, 118 first-blockers). The
                # gcc law measured at my hands (probes of_a..of_n): the
                # builtin becomes `off + idx * esize` — the SAME walk,
                # the SAME §2.13 mirrors (flat layout for the constant
                # prefix, _csize for the element, packed/bitfield shrink
                # included), the arithmetic built as ordinary shipped
                # nodes (of_l runs `/8` on the result; no libcall, see
                # the asm legs). Both LOUD arms ride the existing
                # sentences (not-an-array, element size).
                node = step[1]
                if not isinstance(cur, ast.ArrayType):
                    self._parse_err(at, "__builtin_offsetof: indexed "
                                        "member is not an array (§2.13)")
                esz = self._csize(cur.inner)
                if esz is None:
                    self._parse_err(at, "__builtin_offsetof: element "
                                        "size unknown (§2.13)")
                term = ast.Binary(node.file, node.line, node.col, "*",
                                  node, ast.IntLit(at.file, at.line,
                                                   at.col, esz, "int"))
                dyn = term if dyn is None else ast.Binary(
                    node.file, node.line, node.col, "+", dyn, term)
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
        if dyn is not None:
            # M4 W-J: constant prefix + runtime terms, shipped arithmetic
            # (the int-typing law rides the shipped fold, divergence row
            # pinned in tests/test_core_m4wj2.py).
            return ast.Binary(at.file, at.line, at.col, "+",
                              ast.IntLit(at.file, at.line, at.col, off,
                                         "int"), dyn)
        return off

    def _layout_enter(self, ty):
        """M4 W-K (MC 12663, gate F-5): ONE layout-in-progress guard for
        BOTH fold mirrors (`_csize`, `_calign`). The measured cycle
        `_csize(T) -> _tag_aligned(T) -> fold_truthy(sizeof(struct T2))
        -> _csize(T2) -> _tag_aligned(T2) -> ... -> _csize(T)` has no
        legitimate C shape: re-entry while T's layout is in progress means
        T's size depends on T's own attribute argument — the error gcc
        11.4 answers rc1 (incomplete-type sizeof). Tip posture died with
        a raw RecursionError (the gate: raising the limit SEGFAULTS), an
        ICE that DESTROYS the actionable diagnostic; the guard LOUDs
        NAMING THE tag. Returns the key to discard, or None (unguarded
        type)."""
        t = ty
        while isinstance(t, ast.Qualified):
            t = t.inner
        if not isinstance(t, ast.StructType):
            return None
        key = (t.tag, t.is_union)
        if key in self._sizing:
            self._sema(t, "circular layout dependency: '{}{}' is being "
                       "sized while its 'aligned' attribute argument "
                       "sizes it (§2.13 cycle guard)"
                       .format("union " if t.is_union else "struct ",
                               t.tag))
        self._sizing.add(key)
        return key

    def _csize(self, ty) -> Optional[int]:
        """§2.13 fold mirror entry: the W-K cycle guard rides the shared
        `_layout_enter` set; the layout law itself is `_csize_impl`."""
        key = self._layout_enter(ty)
        if key is None:
            return self._csize_impl(ty)
        try:
            return self._csize_impl(ty)
        finally:
            self._sizing.discard(key)

    def _csize_impl(self, ty) -> Optional[int]:
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
            if ty.name == "void":
                # M4 W-K (MC 12663): GNU sizeof(void) is 1 — MEASURED rc0
                # at EVERY std flag (gnu89/c89/c99/c11/c2x), no warning
                # under -Wall -Werror; it is what makes `void *p + k` a
                # byte-unit walk — the bitops CONST_MASK_ADDR law. The
                # old fold answered 0 (TYPE_SIZE["void"] documents that
                # void has no OBJECT — the table stays; THIS arm carries
                # the GNU law, the codegen mirror TypeMap._size mirrors
                # it, alignof(void)=1 already rode the shipped fold).
                return 1
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
                    # M4 W-J mirror fix: member alignment is the type's
                    # align, NOT min(size,8) — the shipped SOURCE OF
                    # TRUTH TypeMap._align aligns ARRAYS BY ELEMENT, so
                    # `{int a[3];}` aligns 4 and sizes 12 (codegen and
                    # gcc agree); the old proxy said 8/16 and made every
                    # `sizeof(struct …array…) == N` static assertion
                    # (44 corpus sites) fold FALSE.
                    base = self._calign(m.type)
                    if base is None:
                        return None
                    align = max(align, self._malign_f(m, packed, base, ty))
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
                # M4 W-J mirror fix (MC 12655): the member's alignment is
                # its TYPE's align per the source of truth TypeMap._align
                # ("arrays by element") — the old min(size,8) proxy
                # aligned an array member by its BYTES ({int a[3];} -> 8),
                # so the fold sized `{int a[3];}` at 16 while codegen and
                # gcc both say 12: every
                # `sizeof(struct …array…) == N` static assertion (44
                # corpus sites) folded FALSE. Bitfields keep the unit law
                # above; this is the byte-member arm the §1c fix already
                # adopted for the struct loop via _calign.
                mal = self._malign_f(m, packed, self._calign(m.type) or ms,
                                      ty)
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

    def _q_volatile(self, ty) -> bool:
        """Top-level `volatile` on a type node (the peel `expr_type` does
        NOT do — this is the qualifier view, so it must not drop it)."""
        while isinstance(ty, ast.Qualified):
            if ty.qual == "volatile":
                return True
            ty = ty.inner
        return False

    def _qual_type_of(self, node: ast.Node) -> Optional[ast.Node]:
        """§2.4e M4 W-U (MC 12739): the QUALIFIER-KEEPING view of the four
        shapes `_se_lvalue_law` can admit as a final expression. The light
        `expr_type` mirror `_unqual`s at every arm BY DESIGN (§5 struct
        checks do not want qualifiers); this is the second host view the
        CompatLawMixin idiom calls for, deliberately narrow: Ident,
        `*`-deref, `[]`, and a member select. None = no view = not
        volatile as far as the law can tell (never a guess)."""
        if isinstance(node, ast.Ident):
            sym = self.lookup(node.name)
            return sym[1] if sym is not None and sym[0] == "var" else None
        if isinstance(node, ast.Cast):
            return node.type
        if isinstance(node, ast.Unary) and node.op == "*":
            t = self._qual_type_of(node.operand)
            while isinstance(t, ast.Qualified) and t.qual != "volatile":
                t = t.inner
            return t.inner if isinstance(t, (ast.PtrType, ast.ArrayType)) \
                else None
        if isinstance(node, ast.Index):
            t = self._qual_type_of(node.base)
            while isinstance(t, ast.Qualified) and t.qual != "volatile":
                t = t.inner
            return t.inner if isinstance(t, (ast.PtrType, ast.ArrayType)) \
                else None
        if isinstance(node, ast.Select):
            t = self.expr_type(node)     # its member arm answers the RAW
            return t                     # member type (qualifier kept)
        return None

    def volatile_final(self, node: ast.Node) -> bool:
        """§2.4e L5 (M4 W-U, MC 12739): does this final expression name a
        VOLATILE-qualified object? Measured own hands, all gcc LOUD
        'lvalue required' where blcc-tip was QUIET: a volatile name
        (`({ v; }) = 2`), a cast-to-volatile-pointer deref, a
        `volatile int *p` deref, a volatile MEMBER and a volatile ARRAY
        element; the rvalue use of the SAME expressions stays legal (gcc
        rc0) because this leg runs only in lvalue position."""
        return self._q_volatile(self._qual_type_of(node))

    def expr_type(self, node: ast.Node) -> Optional[ast.Node]:
        """Light type-of-expression: only what §5 struct checks need."""
        if isinstance(node, ast.IntLit):
            # M4 W-Z COMMIT-CH37T (MC 12774): the typing mirror TYPES
            # literals too — the __is_constexpr/__auto_type crowd feeds
            # bare literals through the seam (sims ch09 measured: without
            # these arms the mirror answered None for every bare-integer
            # initializer and the A-shape never reached its C0 refusal).
            return ast.BuiltinType(node.file, node.line, node.col,
                                   node.itype)
        if isinstance(node, ast.CharLit):
            return ast.BuiltinType(node.file, node.line, node.col, "int")
        if isinstance(node, ast.IncDec):
            # §6.5.2.6p2: the result is the PROMOTED operand type; for the
            # sizeof mirror the operand's own type is what decays — the
            # `sizeof(*(u++))` dispatch (ptrace.c:441 corpus row).
            return self.expr_type(node.operand)
        if isinstance(node, ast.Cond):
            # M4 W-Z COMMIT-CH37T (MC 12774, SIMS-LAW MEASURED at card
            # 12768): the §6.5.15p5 conditional TYPING the Linus
            # __is_constexpr / BUILD_BUG constant-detect tricks ride —
            # `sizeof(*(8 ? ((void *)((long)(x) * 0l)) : (int *)8))`
            # answers through the TYPE of the `?:`, never a folded value.
            # A FOLDABLE test picks the arm; a NULL POINTER CONSTANT arm
            # (C 6.3.2.3p3 — integer-constant expr of value 0) takes the
            # OTHER arm's pointer type; two different real pointers
            # compose to void* (gnu89 MEASURED: sizeof(void) == 1 — the
            # trick's runtime answer). A test the fold cannot resolve
            # answers None — the §2.12 safe direction, never a guessed
            # arm. THE bcp/C0 GUARD IS NOT TOUCHED BY THIS ARM: the 18
            # A-shape streams shift from the choose-wall to the C0 LOUD
            # refusal (ch09 pinned in tests/test_core_m4wz2.py) —
            # accepting them would be the y27 silent re-armed.
            v = self.fold_truthy(node.test)
            if v is None:
                return None
            if node.gnu:
                chosen, other = ((node.test, node.arm2) if v != 0
                                 else (node.arm2, None))
            else:
                chosen, other = ((node.arm1, node.arm2) if v != 0
                                 else (node.arm2, node.arm1))
            ty = self.expr_type(chosen)
            if ty is None:
                return None
            if other is None:
                return ty
            oty = self.expr_type(other)
            if oty is None:
                return ty
            ty, oty = self._unqual(ty), self._unqual(oty)
            if isinstance(ty, ast.PtrType) and isinstance(oty, ast.PtrType):
                if self._light_null_ptr_const(chosen):
                    return oty
                if self._light_null_ptr_const(other):
                    return ty
                if self._light_ptr_key(ty) is not None and \
                        self._light_ptr_key(ty) == self._light_ptr_key(oty):
                    return ty
                return ast.PtrType(
                    node.file, node.line, node.col,
                    ast.BuiltinType(node.file, node.line, node.col, "void"))
            return ty
        if isinstance(node, ast.Ident):
            sym = self.lookup(node.name)
            ty = (self._unqual(sym[1]) if sym is not None
                  and sym[0] == "var" else None)
            # M4 W-Z COMMIT-CH37T (MC 12774): an __auto_type var carries a
            # LAZY TypeOf(auto=True) (W-H shipped the form); the mirror
            # MATERIALIZES it here with W-H's OWN decay law — arrays DECAY,
            # top quals DROP. Scope-blind materialization is the sims'
            # plant-p4 class (shadowing eats the outer); the lookup above
            # is scope-correct, so the mirror answers the DECLARING scope's
            # initializer (ch08 run-pair pinned).
            if isinstance(ty, ast.TypeOf) and ty.auto:
                ity = self.expr_type(ty.expr) if ty.expr is not None \
                    else None
                if ity is None:
                    return None
                ity = self._unqual(ity)
                if isinstance(ity, ast.ArrayType):
                    return ast.PtrType(ty.file, ty.line, ty.col,
                                       self._unqual(ity.inner))
                return ity
            if isinstance(ty, ast.TypeOf):
                # M4 W-AF {T2} (MC 12404.2.144 / job 12831): the mirror
                # MATERIALIZES the non-auto typeof spelling — engine
                # twin TypeMap._untype. The TYPED form recurses through
                # _unqual (W-AD's ONE shipped home); the EXPR form
                # types through THIS mirror and does NOT decay (W-H's
                # measured difference table). An operand this mirror
                # cannot type answers None — NEVER a guessed type (the
                # §2.12 safe direction; card-12825 plant p2 documents
                # that the downstream judge enforces it today and a
                # later fix must not quietly remove that judge). Rows
                # af12/af13 NAMED: the _Generic operand and the CAST
                # path are not claimed here — kernel_events_core.c.i
                # keeps its §8 wall (P3c).
                if ty.typ is not None:
                    return self._unqual(ty.typ)
                if ty.expr is None:
                    return None
                return self.expr_type(ty.expr)
            return ty
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
            # M4 W-X COMMIT-0 (MC 12756, gate F6): the INTEGER arm of the
            # SAME light mirror — the engine's _binary_ty answer computed
            # from its OWN tables (_RANK/UNSIGNED_NAMES imported, never
            # copied): comparisons answer int, a shift takes its promoted
            # LEFT operand, + - * / % take the §2.2 usual arithmetic
            # conversions. tip answered None for EVERY int-arith shape, so
            # `__builtin_types_compatible_p(typeof(cs_nsec - wd_nsec), …)`
            # folded NOT-compatible (the §2.12 safe direction, W-L) where
            # gcc folds 1: the kernel abs() choose-chain took its
            # `((void)0)` arm — the F6 clocksource ICE at _uac, and a
            # SILENT wrong arm wherever both arms typecheck (own run-pair
            # at tip: blcc 142, gcc 102 — tests/test_core_m4wx0.py).
            # fp operands STAY None: the §2.12 safe direction pinned by
            # the fp leg there (l13-class NAMED-DIVERGE family).
            return self._arith_ty_light(node, left, right)
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
        if isinstance(node, ast.Call):
            # M4 W-AA (MC 12780): the CALL arm of the light mirror — the
            # §8 crowd's missing arm (sims card 12778: 15 of the 17 §8
            # first-walls are a call-result MEMBER callee; the walk's
            # sentence is `skb_dst(skb)->output(...)` at dst.h:450, the
            # crypto family `crypto_ahash_reqtfm(req)->export(...)`).
            # TWO answers, NO second law text: the NAMED fn rides the
            # shipped light symbol shape ("fn", ret) — the engine's
            # `sigs[name][1]` twin, not a new home (ca01/ca02, plant P2);
            # EVERY other callee shape — the fn-ptr VAR `fp()`, the
            # designator `(*fp)`, an array element `t[0]` — DELEGATES to
            # `types.call_target_ret`, the pure body lifted out of
            # `TypeMap._ind_call_ty` (the sims' stub RESTATING the decay
            # law in this arm is the two-homes defect their §5 P2/P3
            # plants kill — the one-home guard test pins this text). A
            # target this mirror cannot type answers None and the §8
            # gate (expr_parser.py) keeps its gcc-rc1-twin sentence —
            # ca16/ca17 stay BOTH-REFUSE, the safe direction (S4: the
            # StmtExpr-callee streams are a DIFFERENT missing arm and
            # stay walled here; the wave claims 15, never 17).
            if isinstance(node.callee, ast.Ident):
                sym = self.lookup(node.callee.name)
                if sym is not None and sym[0] == "fn":
                    return sym[1]
            return call_target_ret(self.expr_type(node.callee))
        if isinstance(node, ast.Unary) and node.op == "*":
            base = self.expr_type(node.operand)
            if isinstance(base, ast.Qualified):
                base = self._unqual(base)
            if isinstance(base, (ast.PtrType, ast.ArrayType)):
                return self._unqual(base.inner)
        if isinstance(node, ast.StmtExpr):
            # M4 W-AF {T1} (MC 12404.2.144 / job 12831): the light
            # mirror TYPES the GNU statement-expression — the engine
            # twin TypeMap._ty_stmtexpr (§2.4c: the group's type IS its
            # LAST value). The corpus rider is the static_call
            # trampoline spelling `({…; (&__SCT__x);})()`
            # (arch/x86/events/core.c:699:246, the walk's first RED;
            # battery rows af04/af05/af06/af26 move WALL→PAIR here,
            # card-12825 census: the ONLY corpus carrier of the
            # `(&__SCT__…)` callee form is that ONE stream, 18 sites).
            # The HONEST limit is NAMED: the mirror has no group-locals
            # home, so a value referring to a group-local decl stays
            # un-typeable and answers None (row af03), the §2.12 safe
            # direction — the shipped §8 refusal keeps it walled.
            return self.expr_type(node.value)
        if isinstance(node, ast.Unary) and node.op == "&":
            # W3 commit-2 (S22 chain `**(&f)`): ADDRESS-OF builds the
            # pointer view — the mirror the deref arm decays back.
            inner = self.expr_type(node.operand)
            if inner is not None:
                return ast.PtrType(node.file, node.line, node.col, inner)
        return None

    _NARROW_NAMES = frozenset(("char", "signed char", "unsigned char",
                               "short", "unsigned short", "_Bool"))

    def _promote_light(self, ty):
        """§2.2 integer promotion — fold-side twin of TypeMap._promote
        (the narrow types → int, LP64; M4 W-X COMMIT-0, MC 12756)."""
        if isinstance(ty, ast.BuiltinType) and ty.name in self._NARROW_NAMES:
            return ast.BuiltinType(ty.file, ty.line, ty.col, "int")
        return ty

    _NON_SWITCH_LABEL_NAMES = frozenset(("void", "float", "double"))

    def _switch_label_width(self, control):
        """M4 W-Z COMMIT-0 (MC 12774, cl16): the (width, signedness) of the
        switch control's PROMOTED type — the width every case label is
        converted TO. One home with the shipped width law: this is
        TypeMap._fold_w's answer computed on this side's `_promote_light`
        twin. None = this mirror cannot name an integer scalar control
        (fp/void/unresolvable) — every label then keeps today's
        un-converted posture (the safe direction, never a guess)."""
        from blcc.types import TYPE_SIZE, is_i128, is_unsigned
        ty = self.expr_type(control)
        if ty is None:
            return None
        ty = self._promote_light(self._unqual(ty))
        if not isinstance(ty, ast.BuiltinType) \
                or ty.name not in TYPE_SIZE \
                or ty.name in self._NON_SWITCH_LABEL_NAMES:
            return None
        if is_i128(ty):
            return 128, not is_unsigned(ty)
        return 8 * TYPE_SIZE[ty.name], not is_unsigned(ty)

    def _case_to_control(self, v: int) -> int:
        """M4 W-Z COMMIT-0 (MC 12774): gcc converts EVERY case label to the
        control's promoted type — `case 0x100000000L:` under an `int`
        control TRUNCATES to 0 ("overflow in conversion", measured gcc
        11.4 -Os, and the case then MATCHES 0). blcc's fold answered the
        UNBOUNDED Python integer, so such a label matched nothing and the
        switch silently rode its default arm — a SILENT divergence, the
        same conversion-to-control-type family W-O's switch door rides
        (W-Z sims cl16; corpus volume 0, named at tip, repaired here
        FIRST). The wrap IS the shipped width law (TypeMap._wrapw,
        WHG-B's home) — not a second oracle."""
        ws = getattr(self, "_case_ctrl_ws", None)
        w = ws[-1] if ws else None
        if w is None:
            return v
        from blcc.types import TypeMap
        return TypeMap._wrapw(v, *w)

    def _arith_ty_light(self, node, left, right):
        """M4 W-X COMMIT-0 (MC 12756, gate F6) — the light INTEGER twin of
        the engine's _binary_ty arithmetic law, reached from expr_type.
        Comparisons answer int; a shift takes its promoted LEFT operand;
        `+ - * / %` take the §2.2 UAC over the promoted operands using the
        ENGINE'S OWN rank/signedness tables (imported, never copied).
        None = this mirror cannot type the shape (fp, void, struct,
        pointers that are not the +/− arms above, unresolvable names):
        the §2.12 safe direction stays None, never a guess."""
        if node.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
            return ast.BuiltinType(node.file, node.line, node.col, "int")
        if node.op not in ("+", "-", "*", "/", "%", "<<", ">>"):
            return None
        if node.op in ("<<", ">>"):
            # a shift's result type is its promoted LEFT ALONE — the
            # RIGHT operand needs no type here (a literal has none in
            # this mirror); a LEFT this mirror cannot type stays None.
            if not isinstance(left, ast.BuiltinType):
                return None
            lt0 = self._promote_light(left)
            return lt0 if lt0.name in _RANK else None
        if not (isinstance(left, ast.BuiltinType)
                and isinstance(right, ast.BuiltinType)):
            return None
        lt, rt = self._promote_light(left), self._promote_light(right)
        if lt.name not in _RANK or rt.name not in _RANK:
            return None                      # fp/void: None, never a lie
        if lt.name == rt.name:
            return lt
        lu, ru = lt.name in UNSIGNED_NAMES, rt.name in UNSIGNED_NAMES
        lr, rr = _RANK[lt.name], _RANK[rt.name]
        if lu == ru:
            name = lt.name if lr >= rr else rt.name
        else:
            un, ur = (lt.name, lr) if lu else (rt.name, rr)
            sn, sr = (rt.name, rr) if lu else (lt.name, lr)
            name = un if ur >= sr else sn
        return ast.BuiltinType(node.file, node.line, node.col, name)

    def _light_null_ptr_const(self, node) -> bool:
        """M4 W-Z COMMIT-CH37T (MC 12774): a NULL POINTER CONSTANT is an
        integer constant expression of value 0 (C 6.3.2.3p3), cast or
        not. The parse-side test: the fold answers 0 for the WHOLE node
        without needing any runtime operand."""
        return self.fold_truthy(node) == 0

    def _light_ptr_key(self, ty):
        """Identity key for pointee equality in the conditional's
        pointer-combination arm (builtins by name, tags by tag)."""
        ty = self._unqual(ty)
        if isinstance(ty, ast.BuiltinType):
            return ty.name
        return getattr(ty, "tag", None)

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
                if nm == "fallthrough" and sink is not None:
                    # M4 W-J (MC 12655): CAPTURE the marker for the
                    # attribute-declaration law (the kernel `fallthrough;`
                    # statement). Every OTHER sink owner filters by name
                    # and DROPS it — where gcc says "ignored" rc0
                    # (params/typedefs/decl heads) the drop is pair-clean;
                    # only the attr+`;\` doors (_attr_decl_law) consult it.
                    sink.append(("fallthrough", None))
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

    def _attr_decl_law(self, sink, at_file, pos, prev_ft=False) -> bool:
        """M4 W-J (MC 12655): the GNU/C23 attribute-DECLARATION —
        `__attribute__((...));` with NO declarator (the kernel
        `fallthrough;` macro after pp). Measured law (gcc 11.4 gnu89
        -Os, .tmp/m4-wj/probes/ out-gcc.txt): the form is an EMPTY
        DECLARATION — `unused`/`aligned`/`section` runs rc0 in any
        function position (ft_j/k/q, warning "empty declaration"); at
        FILE SCOPE even a `fallthrough` run is rc0 (ft_i, "'fallthrough'
        attribute at top level" warning); INSIDE a function body the
        `fallthrough` attribute is SWITCH-GATED: gcc rc1 "invalid use of
        attribute 'fallthrough'" unless an enclosing switch exists
        (ft_h plain body, ft_o unbraced-if — the shipped switch_depth
        counter answers BOTH, it spans nested compounds/loops exactly
        like gcc's in_switch flag, ft_s/ft_t measured). The statement
        emits NOTHING: blcc's switch already falls through; the attr is
        a -Wimplicit-fallthrough marker and that flag is NOT in the
        kernel recipe (the level-3 end-of-compound and not-preceding
        warnings, ft_e/ft_t, are rc0 noise).
        M4 W-K (MC 12663, gate F-1) GROWS the law — the CONSECUTIVE
        shape: two FT attribute-declarations in a row are gcc rc1
        "invalid use of attribute 'fallthrough'" AT THE SECOND (measured
        grid .tmp/m4-wk/probes/ ftc1-10, b1-b9: empty statements and
        empty attr-decls do NOT break the adjacency (ftc6/ftc9), real
        items, real declarations and labels DO (ftc3/ftc10/b2); file
        scope is exempt (ftc4); a compound with a REAL item resets, an
        all-empty/FT-only compound is TRANSPARENT (b5/b7 vs b8, oracle-
        decided). ONE flag `self._ft_run` carries the adjacency; this
        law is the ONLY decider and RETURNS the new value — both doors
        store it, no second tracker."""
        ft = any(nm == "fallthrough" for nm, _a in sink)
        if not at_file and self.switch_depth == 0 and ft:
            self._sema(pos, "invalid use of attribute 'fallthrough'"
                       " (§1 row 9, measured gcc rc1 twin)", "fallthrough")
        if at_file:
            return False
        if not ft:
            return prev_ft          # empty NON-FT attr-decl: transparent
        if prev_ft:
            self._sema(pos, "invalid use of attribute 'fallthrough' — a "
                       "second consecutive fallthrough attribute-"
                       "declaration has no preceding statement (gate "
                       "F-1 law, gcc rc1 at the second, ftc1/b1 grid)",
                       "fallthrough")
        return True

    def _parse_static_assert(self, out):
        """M4 W-J (MC 12655): the C11 `_Static_assert` declaration (file
        scope AND block scope — both gcc rc0, sa_l/sa_n measured; the
        label-preceded unbraced form is gnu89-accepted, wj1_und). The
        condition rides the SHIPPED fold_truthy — that is the whole point
        of this wave: EVERY corpus condition (461-site
        `offsetof(struct filename, iname) % sizeof(long) == 0`, 60-site
        string-size `<= 64 - sizeof(unsigned long)`, 11-site enum-count,
        `sizeof(struct printf_spec) == 8`, `16 == ('0' - ' ')`) is an
        expression the existing fold already answers — no new evaluator.
        Measured sentences (gcc 11.4 gnu89 -Os, out-gcc.txt): fold None →
        "expression in static assertion is not constant" (SAME sentence
        with OR without the message, sa_j/sa_s — the pin pair); folds to
        0 → "static assertion failed: MSG" / bare "static assertion
        failed" (sa_a/sa_f); message not a string literal → "expected
        string literal" (sa_t); the C23 ONE-ARG form is rc0 even in
        gnu89 (sa_k). Div-by-zero conditions fold None → the "not
        constant" sentence, same verdict (sa_q). Emits NOTHING: both
        compilers generate no code for an assertion."""
        t = self.s.next()                       # the _Static_assert kw
        self.s.expect_punct("(")
        cond = self.expr.parse_expression()
        msg = None
        if self.s.accept_punct(","):
            mt = self.s.peek()
            if mt.kind != "str":
                self._parse_err(mt, "expected string literal before the"
                                " _Static_assert message argument")
            msg = self.s.next().text
        self.s.expect_punct(")")
        self.s.expect_punct(";")
        v = self.fold_truthy(cond)
        if v is None:
            self._sema(t, "expression in static assertion is not constant"
                       " (measured gcc twin, sa_j/sa_s)")
            return out
        if v == 0:
            if msg is not None:
                self._sema(t, "static assertion failed: {} (measured gcc"
                           " twin, sa_a)".format(msg))
            else:
                self._sema(t, "static assertion failed (measured gcc"
                           " twin, sa_f)")
        return out

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
                self._void_array_judge(lb, ty)
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

    # -- M4 W-Q (MC 12712): block-scope TAG identity (measured law table
    # .tmp/m4-wq: q01b/q02/q04/q05/q06/q09/q16b at gcc -Os). A block-scope
    # NAMED tag gets a MINTED identity — it SHADOWS (never completes) the
    # outer tag (q01b: the file tag stays incomplete after an inner
    # definition, gcc rc1 at its sizeof), and layout is keyed by IDENTITY
    # so two live layouts share one name (q05/q06). File scope keeps the
    # name as its identity — every pre-W-Q behavior is byte-unchanged.

    def _tag_mint(self, name: str, tok: Token) -> str:
        self._blk_tag_n += 1
        return "%s#blk@%s:%d#%d" % (name, tok.file, tok.line,
                                    self._blk_tag_n)

    def _tag_ref(self, name: str, tok: Token) -> str:
        """Resolve a tag NAME to its layout identity at the CURRENT scope."""
        for sc in reversed(self._tag_scopes[1:]):
            if name in sc:
                return sc[name]
        if name in self._file_tags or name in self.struct_tags:
            return name                    # the visible file-scope tag
        if len(self._tag_scopes) == 1:     # file scope: identity == name
            self._file_tags.add(name)
            return name
        # A name first mentioned in a block is a NEW block-scope tag
        # (q09: the LATER file definition of the same name is DIFFERENT).
        ident = self._tag_mint(name, tok)
        self._tag_scopes[-1][name] = ident
        self.struct_tags[ident] = None     # block-scope, INCOMPLETE
        return ident

    def _tag_define(self, name: str, tok: Token) -> str:
        """Identity for a tag DEFINITION: complete the current scope's
        incomplete tag, LOUD on same-scope redefinition, else mint."""
        if len(self._tag_scopes) == 1:
            if self.struct_tags.get(name) is not None:
                self._sema(tok, "struct/union '{}' is already defined"
                           .format(name))
            self._file_tags.add(name)
            return name
        cur = self._tag_scopes[-1]
        ident = cur.get(name)
        if ident is not None:
            if self.struct_tags.get(ident) is not None:
                self._sema(tok, "struct/union '{}' is already defined"
                           .format(name))
            return ident                   # COMPLETES this block's forward
        ident = self._tag_mint(name, tok)  # SHADOWS any outer same-name
        cur[name] = ident                  # tag (b01/b13/b15 law)
        return ident

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
            named = False                  # anon id IS the identity (W-Q)
        else:
            tag = self.s.expect_id("parse").text
            named = True
        if self.s.accept_punct("{"):
            members = self.parse_struct_members(is_union)
            tsink: List[tuple] = []
            self._skip_gnu_attrs(tsink)  # tag-definition tail (§1 row 9)
            tsink = pre_sink + tsink     # M4 W2.5: prefix registers like
                                         # the tail (one law)
            if named:                    # M4 W-Q: identity + redefinition
                tag = self._tag_define(tag, tok)   # law at THIS seam
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
            if named:                    # forward-decl arm (W-Q scope law)
                tag = self._tag_ref(tag, tok)
            self._pending.append(ast.StructDecl(tok.file, tok.line, tok.col,
                                                tag, None, is_union))
            self._bare_type_ok = True
        elif named:                      # BARE reference: W-Q tag lookup
            tag = self._tag_ref(tag, tok)
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
            # M4 W-Y COMMIT-ID (MC 12764): the TAG-ONLY declaration
            # `enum ttu_flags;` — no body, no declarator — is the ONE
            # arm of the struct twin this door never grew. The corpus
            # witness is 29 streams deep and identical (sims §3a:
            # mm/internal.h:617, `enum ttu_flags;` in 28 mm/* TUs +
            # arch/x86/mm/pat/memtype.c.i); gcc accepts it at REC (row
            # y25 rc0 exit=3), blcc refused with `expected an identifier,
            # found ';'` because the declaration layer, finding no
            # declarator, met the ';' — the STRUCT arm's
            # `_bare_type_ok` + the `;`-swallow at the declaration layer
            # is the shipped twin (and a bare enum body already marks
            # itself below), so THIS is that home, not a new mechanism.
            if self.s.at_punct(";"):
                self._bare_type_ok = True
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

    def _void_array_judge(self, at, el) -> None:
        """F-5 LOUD RESTORE (gate MC 12664 F-5, AMENDMENT-13 W-L commit-0,
        RED-at-tip in tests/test_core_m4wl0.py): `void a[4];` was LOUD rc2
        until W-K's sizeof(void)=GNU-1 made the ELEMENT size answer 1 and
        the declaration silently passed (gcc rc1 "declaration of 'a' as
        array of voids", volume 0 in the 706). The judge rides BOTH array
        builders — the declarator fold and the sizeof/alignof type suffix —
        so no void-array spelling slips one arm. The NON-array void decls
        (`void v;`) were already accepted at the W-K base: a pre-existing
        divergence pinned with its own leg, NOT silently widened here."""
        while isinstance(el, ast.Qualified):
            el = el.inner
        if isinstance(el, ast.BuiltinType) and el.name == "void":
            self._sema(at, "declaration as array of 'voids' is a gcc "
                       "ERROR (§4 twin rc1)")

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
                self._void_array_judge(bracket, ty)
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
                _idt = self.s.expect_id("parse")
                name = _idt.text
                if name == "__func__":
                    # M4 W-N (MC 12687): gcc's gnu89 KEYWORD law — the
                    # function-name object is not declarable AT ANY
                    # position (param/local/file/static-const/member all
                    # measured rc1 'expected identifier or ( before
                    # __func__'); the implicit binding below is the only
                    # way the name exists.
                    self._parse_err(
                        _idt, "expected identifier or '(' before "
                        "'__func__' — the implicit function-name object "
                        "is not declarable (gcc keyword law, MC 12687)")
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
            # M4 W-J WIG-A (MC 12655): the SPEC position feeds the SAME
            # sink (was: parse_base_type() with NO sink — the gate's
            # `param_nonptr_spec` silent section sink; layout class then
            # rode the blunt §1-row-9 no-sink wall instead of the gcc
            # sentence). One sink, every position.
            base = self.parse_base_type(psink)
            name, ty, is_fn, _ = self.parse_declarator(base, ctx="param",
                                                       attr_sink=psink)
            if is_fn:
                # C 6.7.6.3p7 (M4 W1 row 1b): a parameter of FUNCTION type
                # is ADJUSTED to pointer-to-function — `void cb(int)` and
                # `void (*cb)(int)` declare the same thing. The M1 wall
                # ("parameter with function type is not in the subset")
                # dies here; the oracle twin is test_core_m4w1 1b-decay.
                ty = ast.PtrType(ty.file, ty.line, ty.col, ty)
            # M4 W-J WIG-A (MC 12655): the rc1 judge covers ABSTRACT
            # declarators too (the gate's WAVE-OPENED `param_fnptr_star`
            # sink: `name is None` silently rode the old `is not None`
            # guard; gcc spells the name '({anonymous})'), and the
            # measured `aligned` law rides the DECLARED TYPE (my matrix
            # am_1..am_9: scalar/array SPEC or TAIL → rc1 "alignment may
            # not be specified for 'p'"; POINTER/adj-fn STAR aligned is a
            # TYPE attribute, gcc rc0 — the shipped silent drop STAYS, a
            # LOUD there would be the false divergence; packed is "ignored"
            # rc0 everywhere — pair-clean drop). The ONE shape the sink
            # cannot see is POSITION: aligned at a POINTER param's TAIL is
            # gcc rc1 (am_4) and stays a named SILENT-DIV pin, volume 0.
            _disp = name if name is not None else "({anonymous})"
            for _nm, _a in psink:
                if _nm == "section":
                    # M4 W-I (MC 12650): measured gcc rc1 twin
                    # (probe r12): "section attribute not allowed
                    # for 'q'" — a parameter has no placement.
                    self._sema(ppos, "section attribute not allowed "
                               "for '{}' (§1 row 9, measured gcc rc1 "
                               "twin)".format(_disp), "section")
                if _nm == "aligned" and \
                        not isinstance(self._unqual(ty), ast.PtrType):
                    self._sema(ppos, "alignment may not be specified for "
                               "'{}' (gcc rc1 measured twin, am_1/am_2/"
                               "am_5/am_6)".format(_disp), "aligned")
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
        # W-K F-1: a REAL declaration item resets the FT adjacency; the
        # attr-declaration door below restores or sets it via the law.
        _ft_prev = self._ft_run
        self._ft_run = False
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
        if self.s.at_punct(";"):
            # M4 W-J (MC 12655): the GNU/C23 attribute-DECLARATION — the
            # runs are consumed, the declarator list is EMPTY: a no-op.
            # Blocks and file scope take this ONE door (statement
            # position has its own arm applying the SAME law).
            self._ft_run = self._attr_decl_law(decl_sink, at_file,
                                               self.s.peek(), _ft_prev)
            self.s.next()
            return out
        if self._at("_Static_assert"):
            # M4 W-J (MC 12655): the C11 static-assertion DECLARATION —
            # it OPENS the declaration (in _DECL_START_KW), so this is
            # the single door at file scope AND in blocks.
            return self._parse_static_assert(out)
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
            # M4 W-J WIG-A (MC 12655): the PRE-KEYWORD attrs the leading
            # skip captured ride INTO the typedef sinks — the gate's three
            # `td_pre_kw` spellings were silent because this arm dropped
            # decl_sink on the floor.
            return self._parse_typedef(decl_sink)
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
        pmark = len(self._pending)   # W-T COMMIT-2: own only own facts
        base = self.parse_base_type(decl_sink)
        facts = self._pending[pmark:]
        del self._pending[pmark:]
        out.extend(facts)
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
                body = (self.parse_function_body(params, name)
                        if self.s.at_punct("{") else None)
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
                # M4 W-T COMMIT-1: the §1 row 11 decl-position unwrap
                # MOVED into _norm_init (ONE home, now at every depth)
                # — the byte-identical law is stated ONCE.
                init = self._norm_init(ty, init, pos)   # §1 row 10
            if is_extern and init is None and not at_file:
                # §2.8 — an extern LOCAL RE-DECLARES THE SAME OBJECT the
                # file scope would name: a reference, never new storage.
                # M4 W-U COMMIT-2 (MC 12739) splits the ONE question the
                # seam asks (own hands, shapes b1..b6 at the wave REC):
                #   * a name an enclosing scope ALREADY declares: the
                #     local declaration adds nothing — DROP, the tip
                #     posture unchanged (b2/b3/b4 PAIR before and after);
                #   * a name NOTHING in this TU declares yet (the corpus
                #     `zero_pfn` class: the object is DEFINED IN ANOTHER
                #     TU and this TU only ever spells it inside a
                #     function). Tip dropped the only declaration the name
                #     ever had and codegen LOUDed "'zero_pfn' undeclared"
                #     where gcc answers rc0 (a LINK-time fact, not a
                #     compile-time error — b1: gcc rc0, tip rc2). Recorded
                #     here, BOUND AT TU END below, where the file scope is
                #     complete: DEFERRING is what keeps `int f(void){
                #     extern int t; … } int t = 7;` (b2) answering the
                #     same object instead of colliding with a hoisted
                #     re-decl;
                #   * an extern INCOMPLETE-ARRAY local (`extern char
                #     __init_begin[], __init_end[];` — 304 corpus streams,
                #     the #1 first-wall class at the W-U close bytes)
                #     BINDS like every other extern reference: M4 W-V
                #     COMMIT-E DELETES the §4 LOUD that stood here. gcc
                #     binds the name as a REFERENCE to the object defined
                #     elsewhere; incompleteness owns only SIZE, and
                #     sizeof-on-a-never-completed array has been LOUD
                #     since COMMIT-0 — the REFERENCE shipped while the
                #     SIZE door stayed shut (law rows e02/e11/e16,
                #     own-hands ladder .tmp/m4-wv).
                if self.lookup(name) is None:
                    self._ext_refs.setdefault(name, (pos, ty))
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
                if at_file:
                    # M4 W-AE COMMIT-2 (MC 12404.2.141 / job 12819): a
                    # file-scope TENTATIVE `[]` array without initializer
                    # DEFERS through the EXISTING §2.8 home `_ext_refs`
                    # (ONE deferral mechanism — the b2 law just above; a
                    # second deferral home is what this wave's own plant
                    # must find RED, never a second dict). C 6.7.5.2p4:
                    # the later definition-with-init of the same TU
                    # completes the tentative and supplies size+storage;
                    # the real wall kernel/cpu.c:134 (`static struct
                    # cpuhp_step cpuhp_hp_states[];`, corpus row + live
                    # walk) answers rc0 under it. A LOCAL spelling keeps
                    # the §4 wall (both-refuse twin x07); a name the TU
                    # never completes rides the TU-end bind — NAMED
                    # residual x05 (gcc COMPLETES to 1 element `B a`;
                    # blcc leaves the object absent — link-time-only,
                    # own future pricing, never silently merged).
                    if self.lookup(name) is None:
                        self._ext_refs.setdefault(name, (pos, ty))
                    if self.s.accept_punct(","):
                        continue
                    self.s.expect_punct(";")
                    break
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

    def _parse_typedef(self, pre_sink=()) -> List[ast.Node]:
        out: List[ast.Node] = []
        spec_sink: List[tuple] = []     # M4 W2.5: spec-position attrs
        # M4 W-J WIG-A: pre_sink = the PRE-KEYWORD run parse_decl skipped
        # before `typedef` — one law, every position (section rc1, layout
        # = the shipped LOUD-DIV posture, markers drop).
        pre_sink = list(pre_sink)
        pmark = len(self._pending)   # W-T COMMIT-2: own only own facts
        base = self.parse_base_type(spec_sink)
        facts = self._pending[pmark:]
        del self._pending[pmark:]
        out.extend(facts)
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
            # M4 W-J WIG-A (MC 12655): the PRE-KEYWORD run rides a JUDGE-
            # ONLY pass — `section` is the gate's rc1 twin (td_pre_kw /
            # td_struct_pre_kw / td_struct_plain_pre: parse_decl captured
            # it and the OLD typedef arm discarded the whole sink); layout
            # attrs on a NON-struct typedef join the shipped LOUD-DIV
            # posture below. The tag REGISTRATION arm must NOT see it:
            # gcc 11.4 IGNORES a PRE-KW layout attr outright (probe am_10
            # measured this session: "packed attribute ignored", sizeof
            # UNCHANGED, rc0), so registering one on the tag would raise
            # a layout the oracle never raised.
            for _nm, _a in pre_sink:
                if _nm == "section":
                    self._sema(pos, "section attribute not allowed for "
                               "'{}' (§1 row 9, measured gcc rc1 twin)"
                               .format(name), "section")
                elif _nm in ("aligned", "packed") and \
                        not isinstance(self._unqual(ty), ast.StructType):
                    self._sema(pos, "'{}' on a typedef of a non-struct "
                               "type is LOUD-DIV (gcc raises the NAME's "
                               "alignment only; corpus volume 0, measured)"
                               .format(_nm), _nm)
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
        if isinstance(ty, ast.TypeOf) and not ty.auto \
                and ty.typ is not None:
            # M4 W-AD (MC 12801): TypeOf materialization has ONE
            # parser-side home — this type LOOKUP, mirroring the
            # data-side law `types._untype` already ships. A
            # `__typeof__(struct X)` declaration therefore resolves
            # through EVERY `_unqual` call site (designator slots,
            # struct/array arms) instead of reaching data as a bare
            # Desig run — the printk DEFINE_PER_CPU struct-form wall
            # and its radix-tree/mm_swap twins (sims ib10/ib22/ib33,
            # real-make wall printk/printk.c:3090). KEEP the refusal
            # OUTSIDE this guard: `__auto_type` and `__typeof__(expr)`
            # ride the TypeMap VALUE law (sims ib18/ib31 posture
            # stands; battery wd109/wd110 pin both non-materializing).
            return self._unqual(ty.typ)
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
            if getattr(m, "width", None) == 0:
                # M4 W-AE COMMIT-1 (MC 12404.2.141 / job 12819): the slot-
                # model PAIRING LAW, parser half. A width-0 pad consumes NO
                # init slot — the SAME law types._struct_layout already
                # ships (`if w == 0: continue`, both arms), and battery row
                # ae03 measures it as the gcc-11.4 law: the positional item
                # SKIPS the :0 position (exit=1, 2 truncated to 0 into `b`).
                # The anonymous `unsigned :0;` inside struct task_struct was
                # the ONE member where the two homes forked: the parser
                # counted 120 slots, data + gcc DWARF 119 (sizeof 5824) —
                # DATA is gcc; the PARSER table was the divergent home, and
                # the designated arm padding items to len(slots) fired the
                # init_task.c:69:3 wall at data.py:580. The agreement
                # invariant (slot names/counts equal; byte-offset parity
                # where both tables carry byte truth; residual parser bit-
                # slot drift PINNED as measured) rides BOTH homes through
                # tests/test_core_m4wae1.py — a change to one home without
                # the other turns that pin-test RED.
                continue
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
        # M4 W-T COMMIT-1 (MC 12736): the §1 row 11 byte-identical law
        # at EVERY brace level — an AGGREGATE object or MEMBER
        # initialized from a compound literal measures byte-identical
        # to writing the brace list (gnu89). The law lived at the
        # decl-position splice ONLY (parser top level); nested depths
        # never saw it, and `(struct N){ (struct M){4} }` SILENTLY
        # stored the member's ADDRESS (measured at tip bytes: answers
        # 82 vs gcc 6 — the gate's t06 row, now measured own hands).
        # THE LOUD REFUSAL THIS REPLACES: at nested depths the raw CL
        # reached the _expr emitter (`cannot emit expression, found
        # 'construct'` — the walk stopper); the unwrap makes depth
        # behave like depth 0, at the ONE normalization home.
        if isinstance(init, ast.CompoundLit) and \
                isinstance(ty, (ast.ArrayType, ast.StructType)):
            init = init.init
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
            # M4 W-T COMMIT-1 (MC 12736): positional at THIS brace
            # level says nothing about the levels BELOW — the gnu89
            # spin-init crowd writes `{ { .rlock = { .raw_lock = {} } } }`:
            # a positional OUTER hiding a DESIGNATED inner. The raw
            # Desig node reaching the _expr emitter is the
            # `cannot emit expression, found 'construct'` wall — 321
            # first-blockers, the walk stopper at xarray.h:377:79
            # (init/main.o). ONE law, this function, no second emitter:
            # recurse the normalization to member/element depth.
            if isinstance(ty, ast.ArrayType):
                return ast.InitList(init.file, init.line, init.col, tuple(
                    self._norm_init(ty.inner, it, at) for it in init.items))
            _sl = self._init_slots(ty)
            if _sl is None:
                return init                      # scalar: as written
            return ast.InitList(init.file, init.line, init.col, tuple(
                self._norm_init(_sl[i][1], it, at) if i < len(_sl) else it
                for i, it in enumerate(init.items)))
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

    def parse_function_body(self, params: Tuple[ast.Param, ...],
                            fn_name: Optional[str] = None) -> ast.Node:
        opening = self.s.expect_punct("{")
        self.scopes.append({})
        self._tag_scopes.append({})
        for p in params:
            if p.name:
                self.scopes[-1][p.name] = ("var", p.type)
        stmts = self._block_stmts_until_brace()
        self._tag_scopes.pop()
        self.scopes.pop()
        # M4 W-N (MC 12687): gnu89 binds an implicit
        # `char __func__[len+1] = "<name>"` in EVERY function body
        # (measured law: sizeof len+1, indexable, decays). The ONE
        # binding point injects a REAL local string-array declaration —
        # the shipped §1c local-array law carries sizeof/index/decay/
        # frame, no second vocabulary; the declarator gate above makes
        # a user spelling of the name impossible, so the injection can
        # never collide. Injected ONLY when the body mentions the name
        # (an unused function pays no frame slot — the shipped frame
        # pins stay untouched).
        if fn_name is not None and _uses_funcname(stmts):
            vd = ast.VarDecl(
                opening.file, opening.line, opening.col, "__func__",
                ast.ArrayType(
                    opening.file, opening.line, opening.col,
                    ast.BuiltinType(opening.file, opening.line,
                                    opening.col, "char"),
                    ast.IntLit(opening.file, opening.line, opening.col,
                               len(fn_name) + 1)),
                ast.StrLit(opening.file, opening.line, opening.col,
                           fn_name),
                is_static=True)
            stmts = (vd,) + tuple(stmts)
        return ast.Compound(opening.file, opening.line, opening.col, stmts)

    def _block_stmts_until_brace(self) -> Tuple[ast.Node, ...]:
        stmts: List[ast.Node] = []
        while not self.s.at_punct("}"):
            mark = len(stmts)
            # M4 W-T COMMIT-2 (MC 12736): OWNERSHIP STACK — _pending is
            # a stack of UN-OWNED layout facts and a seam owns ONLY
            # what was minted past its OWN mark. A STATEMENT-position
            # expression mints anon struct/enum facts (the
            # `sizeof(struct { int:(-!!(e)); })` BUILD_BUG_ON_ZERO
            # family — 111 first-wall streams at the sealed sweep);
            # the fact rides IN FRONT of its own item, so codegen
            # meets the layout before the use. The mark law is not
            # pedantry: a full drain here lets a NESTED compound STEAL
            # the enclosing if-condition's fact (measured on the pre-
            # wave sim sweep: arch_x86/lib/copy_mc + lib/usercopy, two
            # long-accepted TUs, LOST — the stream then walled
            # `undefined struct <anon@…>` at the condition).
            pmark = len(self._pending)
            stmts.extend(self.parse_block_item())
            if len(self._pending) > pmark:
                facts = self._pending[pmark:]
                del self._pending[pmark:]
                stmts[mark:] = facts + stmts[mark:]
        self.s.expect_punct("}")
        return tuple(stmts)

    # -- translation unit ---------------------------------------------------------------

    def parse_translation_unit(self) -> ast.TranslationUnit:
        decls: List[ast.Node] = []
        while self.s.peek().kind != "eof":
            if self.s.accept_punct(";"):
                continue
            if self.s.peek().kind in ("id", "kw") and \
                    self.s.peek().text in ("asm", "__asm__"):
                # M4 W-N COMMIT-3 (MC 12687): file-scope asm(...) — the
                # alias/annotation family the kernel TUs ship wholesale
                # (the sys_ni compat_sys_* `.weak`/`.set` blocks).
                # MEASURED gcc gnu89 law: ONE (lexically merged) string
                # literal argument; the text is the ASSEMBLER's — blcc
                # never parses it. `volatile` and operand COLONS are
                # gcc rc1 (measured) — the refusal below is the twin;
                # a non-literal argument refuses through the same arm.
                pos = self.s.next()
                if self.s.peek().text in ("volatile", "__volatile__"):
                    self._parse_err(self.s.peek(), "file-scope asm "
                                    "cannot be 'volatile' (gcc rc1 law, "
                                    "MC 12687)")
                self.s.expect_punct("(")
                parts = []
                while True:
                    t = self.s.peek()
                    if t.kind != "str":
                        self._parse_err(
                            t, "file-scope asm takes exactly string "
                            "literals — operands/expressions are gcc "
                            "rc1 here (MC 12687)")
                    parts.append(self.s.next().value)
                    if self.s.accept_punct(",") is None:
                        break
                self.s.expect_punct(")")
                self.s.expect_punct(";")
                decls.append(ast.TopAsm(pos.file, pos.line, pos.col,
                                        "".join(parts)))
                continue
            if self.starts_decl():
                decls.extend(self.parse_decl(at_file=True))
            else:
                self._parse_err(self.s.peek(), "expected a top-level declaration")
        # M4 W-L (MC 12665): the LAST declaration's body can mint anon
        # struct/enum definitions whose StructDecls sat in _pending —
        # the loop only drained at the NEXT top-level decl, so the
        # trailing ones were DROPPED (sizeof(struct{...}) in the final
        # function LOUD "undefined struct" at codegen). Same mechanism,
        # now complete at TU end; collect's first pass registers them
        # wherever they land in the list.
        decls.extend(self._drain_pending())
        # M4 W-U COMMIT-2 (MC 12739) — the OTHER half of §2.8: bind the
        # extern locals this TU never declared, now that the file scope
        # is complete. A name the TU declared itself afterwards keeps the
        # tip posture (the drop was right; no second declaration). Every
        # remaining one gets the SAME shape the file-scope `extern T x;`
        # spelling produces — ONE `is_extern` VarDecl (data.py never
        # emits it: §2.8 "re-decl, never emits") plus ONE file-scope
        # entry — so the use rides the globals door `_ex_ident` already
        # has and nm answers a bare `U name`, exactly the b6 twin's
        # measured shape (a DEFINED-in-this-TU twin shows `T main` +
        # `U yy`). This REPLACES tip's silent deletion of the declaration
        # (which is what made the corpus `zero_pfn` class a COMPILE-time
        # refusal of a link-time fact); it is NOT the sim stub's posture,
        # which minted a fresh LOCAL frame slot and answers garbage where
        # gcc answers the object — the two-TU value leg in
        # tests/test_core_m4wu2.py pins that difference.
        for nm, (rpos, rty) in self._ext_refs.items():
            if self.lookup(nm) is not None:
                continue
            decls.append(ast.VarDecl(rpos.file, rpos.line, rpos.col, nm,
                                     rty, None, is_static=False,
                                     is_extern=True))
            self.define(nm, ("var", rty), rpos)
        self._ext_refs.clear()
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
        self._tag_scopes.append({})
        stmts = self._block_stmts_until_brace()
        self._tag_scopes.pop()
        self.scopes.pop()
        return ast.Compound(opening.file, opening.line, opening.col, stmts)

    def parse_statement(self) -> ast.Node:
        t = self.s.peek()
        # W-K F-1: capture the FT adjacency; every REAL item path resets,
        # the empty `;` arm and the empty attr-declaration arm restore
        # (measured: they do NOT break adjacency), the law decides FT.
        _ft_prev = self._ft_run
        self._ft_run = False
        if t.kind == "kw":
            handler = self._STMT_HANDLERS.get(t.text)
            if handler is not None:
                _st = getattr(self, handler)()
                self._ft_run = False         # a real statement resets
                return _st
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
            if t.text == "_Static_assert":
                # M4 W-J (MC 12655): gnu89 ACCEPTS the static-assertion
                # declaration after a label (label+decl rc0, wj1_und
                # measured) — the same law through _parse_static_assert;
                # the assertion emits nothing.
                self._parse_static_assert([])
                return ast.ExprStmt(t.file, t.line, t.col, None)
            if self.starts_decl():
                # M4 W-J (MC 12655): the GNU/C23 attribute-DECLARATION in
                # STATEMENT position — `case 1: r+=1; fallthrough;` (the
                # signal.h:155 shape, 205+128 streams). Snapshot the
                # cursor, probe the runs + ';'; on the attr+`;` shape
                # apply the SAME _attr_decl_law and emit an empty
                # statement (the shipped `;` no-op node — codegen already
                # ignores it). A REAL declaration RESTORES the cursor and
                # answers with the shipped wall VERBATIM (the W-H guard
                # class; ft_r measured gcc rc1 for attr-before-stmt, so
                # the same-verdict wall stays for the non-`;` shape).
                if self._at_attr() or self._at_extension():
                    saved = self.s.i
                    stmt_sink: List[tuple] = []
                    self._skip_gnu_attrs(stmt_sink)
                    if self.s.at_punct(";"):
                        self._ft_run = self._attr_decl_law(
                            stmt_sink, False, t, _ft_prev)
                        pos = self.s.next()
                        return ast.ExprStmt(pos.file, pos.line, pos.col,
                                            None)
                    self.s.i = saved
                self._parse_err(t, "'declaration' in an unbraced statement — use a '{ ... }' block")
        if t.kind == "id" and self.s.peek(1).kind == "punct" and \
                self.s.peek(1).text == ":":
            # M2 §1 row 4: real label statement (`lab: stmt`), flat
            # function-wide namespace (§2.5); a label and an identifier of
            # the same spelling COEXIST — the label namespace is separate.
            self.s.next()                      # the identifier
            self.s.next()                      # ':'
            self._ft_run = False               # a label resets (ftc10)
            stmt = self.parse_statement()
            return ast.Label(t.file, t.line, t.col, t.text, stmt)
        if t.kind == "punct" and t.text == "{":
            self._ft_run = _ft_prev    # compound ENTRY is transparent:
            #                              b7 rc1 — the FT outside stays
            #                              the last thing seen INSIDE
            _cmp = self.parse_compound()
            if any(not (isinstance(sx, ast.ExprStmt) and sx.expr is None)
                   for sx in _cmp.body):
                self._ft_run = False   # a compound with a REAL item IS a
            #                              statement (b8 rc0); an all-
            #                              empty/FT-only compound is
            #                              TRANSPARENT — the FT inside
            #                              stays the last thing seen
            #                              (b5/b7 rc1, oracle-decided)
            return _cmp
        if self.s.at_punct(";"):
            pos = self.s.next()
            self._ft_run = _ft_prev    # empty statement: NO reset (ftc9)
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
            return ("range", (self._case_to_control(lo),
                              self._case_to_control(hi)), ct)
        self.s.expect_punct(":")
        return ("case", self._case_to_control(lo), ct)

    def parse_switch(self) -> ast.Node:
        t = self._accept("switch")
        self.s.expect_punct("(")
        control = self.expr.parse_comma_expression()   # W-G (MC 12633)
        self.s.expect_punct(")")
        self.s.expect_punct("{")
        self.switch_depth += 1
        # M4 W-Z COMMIT-0 (MC 12774): the innermost switch owns every label
        # parsed while it is open (C 6.8.5.3), so the control widths ride a
        # STACK, pushed here and consumed in parse_case_arm — both label
        # paths (body loop and parse_nested_label) convert the SAME way and
        # the duplicate check below keys on the CONVERTED values, exactly
        # as gcc's does.
        self._case_ctrl_ws = getattr(self, "_case_ctrl_ws", [])
        self._case_ctrl_ws.append(self._switch_label_width(control))
        stmts: List[ast.Node] = []
        labels: List[tuple] = []
        while not self.s.at_punct("}") and self.s.peek().kind != "eof":
            if self._at("case"):
                kind, value, ct = self.parse_case_arm()
                labels.append((kind, value, ct))
                self._ft_run = False   # W-K F-1: a case label resets
                continue               #   the FT adjacency (ftc10/b4)
            if self._at("default"):
                dt = self.s.next()
                self.s.expect_punct(":")
                labels.append(("default", None, dt))
                self._ft_run = False
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
        self._case_ctrl_ws.pop()
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


def _uses_funcname(nodes) -> bool:
    """Any Ident named `__func__` anywhere under the given AST nodes
    (M4 W-N, MC 12687) — the ONE scan that decides the implicit
    binding's injection; frozen-dataclass children ride __dict__."""
    stack = list(nodes)
    while stack:
        n = stack.pop()
        if n is None or type(n) in (int, str, float, bytes, bool):
            continue
        if isinstance(n, (tuple, list)):
            stack.extend(n)
            continue
        if type(n).__name__ == "Ident" and getattr(n, "name", None) == \
                "__func__":
            return True
        stack.extend(getattr(n, "__dict__", {}).values())
    return False

