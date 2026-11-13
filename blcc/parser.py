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
                             # M2: the extended specifier vocabulary (§4.1a)
                             "signed", "__signed__", "__signed", "register",
                             "inline", "__inline__", "__inline", "volatile",
                             "__volatile__", "restrict", "__restrict",
                             "__restrict__", "typeof", "__typeof__",
                             "__typeof", "__extension__")


class Parser:
    _STMT_HANDLERS = {"if": "parse_if", "while": "parse_while",
                      "do": "parse_do_while", "for": "parse_for",
                      "switch": "parse_switch", "case": "parse_nested_label",
                      "default": "parse_nested_label",
                      "__label__": "parse_label_decl"}

    def __init__(self, toks: List[Token]):
        self.s = TokenStream(toks)
        self.scopes: List[Dict[str, tuple]] = [{}]
        # §2.7: `__builtin_va_list` is supplied by the COMPILER (the .i
        # stream only carries `typedef __builtin_va_list va_list;`).
        self.scopes[0]["__builtin_va_list"] = ("typedef",
                                               predef.VA_LIST_TY)
        self.struct_tags: Dict[str, Tuple[ast.Member, ...]] = {
            predef.TAG: predef.VA_MEMBERS}
        self._anon_n = 0                  # unique minted-tag counter (T+7)
        self._pending: List[ast.Node] = []  # Struct/EnumDecls made by types
        self._bare_type_ok = False          # a tag/enum definition just read
        self.switch_depth = 0
        self.expr = ExprParser(self.s, self.is_typename, self.parse_type,
                               self.callable_known, self.expr_type,
                               self.parse_stmt_expr, self.fold_truthy,
                               self.resolve_offsetof)

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
        if isinstance(node, ast.Unary) and node.op in ("-", "+", "!"):
            v = self.fold_truthy(node.operand)
            if v is None:
                return None
            if node.op == "-":
                return -v
            if node.op == "!":
                return 0 if v else 1
            return v
        if isinstance(node, ast.Cast):
            return self.fold_truthy(node.operand)
        if isinstance(node, ast.Sizeof):
            if node.typ is not None:
                return self._csize(node.typ)
            ty = self.expr_type(node.arg)
            return self._csize(ty) if ty is not None else None
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
            a = 1
            for m in members:
                ma = self._calign(m.type)
                if ma is None:
                    return None
                a = max(a, ma)
            return a
        return None

    def _offsetof_flat(self, ty):
        """Flat [(name, byte-offset, type)] walk for the §2.13 fold:
        anonymous nested members are PROMOTED (T+7), and every union
        member sits at the union's base — §2.8, FINDING c2-F1: the T+6
        fold aligned union members like struct members, gcc 11.4 measures
        offsetof(union U, l) == 0 for EVERY member. Same layout family as
        _csize/_calign (the parse-time fold mirror of TypeMap)."""
        members = self.struct_tags.get(ty.tag)
        if members is None:
            return None
        out = []
        if ty.is_union:
            for m in members:
                if (self._csize(m.type) is None
                        or self._calign(m.type) is None):
                    return None
                if m.name is None:
                    inner = self._offsetof_flat(m.type)
                    if inner is None:
                        return None
                    out += inner
                else:
                    out.append((m.name, 0, m.type))
            return out
        o = 0
        for m in members:
            msz = self._csize(m.type)
            mal = self._calign(m.type)
            if msz is None or mal is None:
                return None
            o = (o + mal - 1) // mal * mal
            if m.name is None:
                inner = self._offsetof_flat(m.type)
                if inner is None:
                    return None
                out += [(n, o + io, t) for (n, io, t) in inner]
            else:
                out.append((m.name, o, m.type))
            o += msz
        return out

    def resolve_offsetof(self, ty, chain, at):
        # §2.13 fold: walk the layout table for the member chain. A
        # MISSING member LOUDs — a bitfield member never lands in
        # struct_tags (its declaration is itself LOUD), mirroring gcc's
        # ERROR "attempt to take address of bit-field structure member":
        # never a silent number.
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
                self._parse_err(at, "__builtin_offsetof: incomplete "
                                    "member layout (§2.13)")
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
            if ty.is_union:
                # §2.8 union: SIZE = max member (not the struct sum) —
                # FINDING c2-F1: the T+6 fold summed union members, which
                # desynced offsetof of members that FOLLOW a union.
                mss = [self._csize(m.type) for m in members]
                if any(ms is None for ms in mss):
                    return None
                align = max([min(ms, 8) for ms in mss] + [1])
                total = max(mss + [0])
                return (total + align - 1) // align * align
            off = 0
            align = 1
            for m in members:
                ms = self._csize(m.type)
                if ms is None:
                    return None
                align = max(align, min(ms, 8))
                off = (off + ms - 1) // ms * ms if ms > 1 else off
                off += ms
            return (off + align - 1) // align * align
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
        if name in BUILTINS:
            self._sema(at, "cannot re-declare the implicit builtin '{}' (§6)".format(name))
        self.scopes[-1][name] = sym

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
            return sym[1] if sym is not None and sym[0] == "var" else None
        if isinstance(node, ast.Index):
            base = self.expr_type(node.base)
            return base.inner if isinstance(base, (ast.ArrayType, ast.PtrType)) else None
        if isinstance(node, ast.Select):
            base = self.expr_type(node.base)
            if node.arrow and isinstance(base, ast.PtrType):
                base = base.inner
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
            if isinstance(base, (ast.PtrType, ast.ArrayType)):
                return base.inner
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
        if self._at_attr():
            return True                    # §1 row 9: attr rides decls
        return t.kind == "id" and self.is_typename(t.text)

    # -- §1 row 9: gcc __attribute__ (parse + strip) --------------------------

    _ATTR_WORDS = ("__attribute__", "__attribute")
    _LAYOUT_ATTRS = ("packed", "aligned", "aligned_with")

    def _at_attr(self) -> bool:
        t = self.s.peek()
        # the lexer keeps `__attribute__` a KEYWORD (§4.1 vocabulary) and
        # the single-underscore spelling an identifier — accept both kinds.
        return t.text in self._ATTR_WORDS and t.kind in ("id", "kw")

    def _skip_gnu_attrs(self) -> None:
        """PARSE + STRIP `__attribute__((...))` lists at a declaration
        head/specifier or a declarator/tag tail (§1 row 9, §2.9). The
        ignore-class (§1 row 9 list + gnu_inline/unused/section/error/…)
        is parsed and DROPPED: it changes no code blcc emits. The
        layout-class (`packed`/`aligned`) stays a §5 LOUD wall until the
        M42 layout rule lands — silently ignoring it would LIE about
        offsets the §2.13 legs pin. Names match after underscore-strip
        (`__aligned__` = `aligned`)."""
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
                if nm in self._LAYOUT_ATTRS:
                    self._sema(tok, "'__attribute__(({}))' is a layout-"
                               "class attribute and is not in the subset "
                               "(§1 row 9)".format(name_tok.text),
                               name_tok.text)
                self.s.next()
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
            return ty

    def parse_base_type(self) -> ast.Node:
        # §2.12/§2.6d: qualifiers LAYOUT-IGNORE stays true — everything
        # resolves through TypeMap._untype — but a TYPE-level qualifier is
        # MARKED (Qualified wrapper) because the oracle makes it
        # significant in exactly two places: the pointee of
        # __builtin_types_compatible_p and the association types of
        # _Generic. The wrapper is stripped by every other consumer.
        quals: List = []
        self._skip_gnu_attrs()          # decl-head/specifier position (§1 row 9)
        ty = self._base_type_core(quals)
        for q, qt in sorted(set(quals)):
            ty = ast.Qualified(qt.file, qt.line, qt.col, q, ty)
        return ty

    def _take_qualifiers(self, out) -> None:
        while self.s.peek().kind == "kw" and \
                self.s.peek().text in _QUAL_WORDS:
            qt = self.s.next()
            out.append((_QUAL_WORDS[qt.text], qt))

    def _base_type_core(self, quals: List) -> ast.Node:
        # M2 §1 rows 2/14: the full scalar specifier family. signedness
        # combines per C: `unsigned`, bare `signed`, `unsigned long long`,
        # `long long`, order-free spec words.
        self._take_qualifiers(quals)
        unsigned = signed = False
        t = self.s.peek()
        while t.kind == "kw" and t.text in ("unsigned", "signed",
                                            "__signed__"):
            if t.text == "unsigned":
                unsigned = True
            else:
                signed = True
            self.s.next()
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
            if t.text in _TYPE_KW:
                self.s.next()
                name = t.text
                if name == "long":       # `long long` (gnu89: C99 in gnu, rc0)
                    if self._at("long"):
                        self.s.next()
                        name = "long long"
                elif name == "short":
                    if self._at("int"):
                        self.s.next()
                if unsigned:
                    name = "unsigned " + name
                elif signed and name == "char":
                    name = "signed char"
                return ast.BuiltinType(t.file, t.line, t.col, name)
            if t.text == "struct" or t.text == "union":
                return self.parse_struct_type()
            if t.text == "enum":
                return self.parse_enum_type()
        if not unsigned and not signed:
            if t.kind == "id" and self.is_typename(t.text):
                self.s.next()
                return self.lookup(t.text)[1]
        elif t.kind == "id" and self.is_typename(t.text):
            # `unsigned U` over an integer typedef: the typedef carries the
            # base; blcc composes the unsigned view of its underlying type.
            base = self.lookup(t.text)[1]
            self.s.next()
            if unsigned and isinstance(base, ast.BuiltinType) \
                    and base.name in ("char", "short", "int", "long",
                                       "long long"):
                return ast.BuiltinType(t.file, t.line, t.col,
                                       "unsigned " + base.name)
            return base
        elif unsigned or signed:
            name = "unsigned int" if unsigned else "int"  # bare `unsigned`
            return ast.BuiltinType(t.file, t.line, t.col, name)
        self._parse_err(t, "expected a type")

    def _skip_qualifiers(self) -> None:
        while self._at("const", "volatile", "__volatile__", "restrict",
                       "__restrict", "__restrict__"):
            self.s.next()

    def parse_struct_type(self) -> ast.Node:
        # §2.8: struct AND union share the grammar; the tag namespace is
        # shared too (C keeps them in one space). is_union rides the KEY-
        # WORD, so a brace-less re-reference (`union U u;`) keeps it.
        tok = self.s.next()  # 'struct' or 'union'
        is_union = tok.text == "union"
        if self.s.at_punct("{"):
            # Minted tags must be UNIQUE: post-pp kernel streams place
            # whole structs on one line, so file:line was not enough for
            # two inline definitions (T+7 same-line leg).
            self._anon_n += 1
            tag = "<anon@{}:{}#{}>".format(tok.file, tok.line, self._anon_n)
        else:
            tag = self.s.expect_id("parse").text
        if self.s.accept_punct("{"):
            members = self.parse_struct_members()
            self._skip_gnu_attrs()      # tag-definition tail (§1 row 9)
            if tag in self.struct_tags:
                self._sema(tok, "struct/union '{}' is already defined"
                           .format(tag))
            self.struct_tags[tag] = members
            self._pending.append(ast.StructDecl(tok.file, tok.line, tok.col,
                                                tag, members, is_union))
            self._bare_type_ok = True
        elif self.s.at_punct(";"):
            self._pending.append(ast.StructDecl(tok.file, tok.line, tok.col,
                                                tag, None, is_union))
            self._bare_type_ok = True
        return ast.StructType(tok.file, tok.line, tok.col, tag, is_union)

    def _flat_member_names(self, members) -> List[str]:
        from blcc.types import walk_fields
        return [n for n, _t in walk_fields(members, self.struct_tags)]

    def parse_struct_members(self) -> Tuple[ast.Member, ...]:
        members: List[ast.Member] = []
        seen: set = set()             # flat member namespace, promoted §
        while not self.s.at_punct("}"):
            if self.s.accept_punct(";"):
                continue
            base = self.parse_base_type()
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
            name, ty, is_fn, _ = self.parse_declarator(base, ctx="member")
            if name is None:
                self._parse_err(pos, "struct member needs a name")
            if is_fn:
                self._parse_err(pos, "'function' member would be a function pointer")
            if self.s.accept_punct(":"):
                self._sema(pos, "'bitfield' members are not in the subset (§5)", ":")
            self.s.expect_punct(";")
            if name in seen:
                # measured gcc 11.4: plain `int a; int a;` is the SAME
                # ERROR "duplicate member 'a'" the promoted names join.
                self._sema(pos, "duplicate member '{}'".format(name))
            seen.add(name)
            members.append(ast.Member(name, ty))
        self.s.expect_punct("}")
        return tuple(members)

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
        sign = 1
        if self.s.accept_punct("-"):
            sign = -1
        else:
            self.s.accept_punct("+")
        t = self.s.peek()
        if t.kind in ("int", "char"):
            self.s.next()
            return sign * int(t.value)
        if t.kind == "id":
            sym = self.lookup(t.text)
            if sym is not None and sym[0] == "enum":
                self.s.next()
                return sign * sym[1]
        self._sema(t, message)

    # -- declarators ---------------------------------------------------------------

    def parse_declarator(self, base: ast.Node, ctx: str = "var"):
        """ctx: 'var' | 'param' | 'member'. Returns (name, type, is_fn, params)."""
        pos = self.s.peek()
        stars = 0
        while self.s.accept_punct("*") is not None:
            stars += 1
        if self.s.at_punct("("):
            nxt = self.s.peek(1)
            if stars or (nxt.kind == "punct" and nxt.text == "*"):
                self._sema(pos, "'function pointer' declarations are not in the subset (§5)", "(")
        name: Optional[str] = None
        if not (ctx == "param" and (self.s.at_punct(")") or self.s.at_punct(","))):
            name = self.s.expect_id("parse").text
        ty = base
        for _ in range(stars):
            ty = ast.PtrType(pos.file, pos.line, pos.col, ty)
        dims = []
        while self.s.at_punct("["):
            bracket = self.s.next()
            size = (None if self.s.at_punct("]") else self.expr.parse_expression())
            self.s.expect_punct("]")
            if size is None and ctx == "member":
                self._sema(bracket, "'array' members of a struct must have a fixed size (§5)")
            dims.append((bracket, size))
        # C reads declarators right-to-left: in `int m[2][3]` the bracket
        # CLOSEST to m ([2]) is the OUTERMOST array — array of 2 rows of 3.
        # Wrapping each successive bracket outward reversed the dimensions
        # (DA-c3 P0-2: stride 8, false "too many initializers", m[i][j] off).
        for bracket, size in reversed(dims):
            ty = ast.ArrayType(bracket.file, bracket.line, bracket.col, ty, size)
        params: Tuple[ast.Param, ...] = ()
        is_fn = False
        if self.s.at_punct("("):
            if ctx != "var":
                self._parse_err(pos, "'function' declarator is not allowed here")
            params = self.parse_params()
            is_fn = True
        self._skip_gnu_attrs()          # declarator tail (§1 row 9)
        return name, ty, is_fn, params

    def parse_params(self) -> Tuple[ast.Param, ...]:
        self.s.expect_punct("(")
        params: List[ast.Param] = []
        self._params_variadic = False
        if self.s.accept_punct(")"):
            return ()
        if self._at("void") and self.s.at_punct(")", 1):
            self.s.next()
            self.s.next()
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
            base = self.parse_base_type()
            name, ty, is_fn, _ = self.parse_declarator(base, ctx="param")
            if is_fn:
                self._parse_err(t, "parameter with function type is not in the subset")
            params.append(ast.Param(name, ty))
            if self.s.accept_punct(","):
                continue
            self.s.expect_punct(")")
            break
        return tuple(params)

    # -- declarations -----------------------------------------------------------------

    def parse_decl(self, at_file: bool) -> List[ast.Node]:
        out: List[ast.Node] = []
        # §1 row 9: attributes may lead a declaration (`__attribute__((x))
        # static int f(...)`) — skip BEFORE the storage-class keywords.
        self._skip_gnu_attrs()
        is_static = False
        static_tok = self._accept("static")
        if static_tok is not None:
            if not at_file:
                self._sema(static_tok, "'static' inside a function is not in the subset (§4)")
            is_static = True
        extern_tok = self._accept("extern")
        is_extern = extern_tok is not None
        # §2.8 gnu89 inline specifiers: consume (in any remaining order);
        # only LINKAGE acts — blcc never inlines and has NO DCE.
        inline_tok = None
        while True:
            self._skip_gnu_attrs()      # attrs may interleave the keywords
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
        base = self.parse_base_type()
        out.extend(self._drain_pending())
        if self._bare_type_ok and self.s.accept_punct(";"):
            return out  # bare 'struct S;' / 'enum E { ... };' definition
        self._bare_type_ok = False
        while True:
            pos = self.s.peek()
            name, ty, is_fn, params = self.parse_declarator(base, ctx="var")
            if is_fn:
                if self.s.at_punct("{") and len(self.scopes) > 1:
                    self._parse_err(pos, "function definition inside a function is not in the subset")
                self.define(name, ("fn", ty), pos)
                body = self.parse_function_body(params) if self.s.at_punct("{") else None
                if body is None:
                    self.s.expect_punct(";")
                out.append(ast.FuncDecl(
                    pos.file, pos.line, pos.col, name, ty, params,
                    body, is_static, variadic=self._params_variadic,
                    inline_kind=inline_kind))
                self._params_variadic = False
                break
            init = self.parse_initializer() if self.s.accept_punct("=") else None
            if init is not None:
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
                    and not isinstance(init, (ast.InitList, ast.StrLit))):
                self._sema(pos, "'array' declaration without size needs an initializer list (§4)")
            self.define(name, ("var", ty), pos)
            out.append(ast.VarDecl(pos.file, pos.line, pos.col, name, ty,
                                   init, is_static,
                                   is_extern=(is_extern and init is None)))
            if self.s.accept_punct(","):
                continue
            self.s.expect_punct(";")
            break
        return out

    def _parse_typedef(self) -> List[ast.Node]:
        out: List[ast.Node] = []
        base = self.parse_base_type()
        out.extend(self._drain_pending())
        while True:
            pos = self.s.peek()
            name, ty, is_fn, _ = self.parse_declarator(base, ctx="var")
            if is_fn:
                self._parse_err(pos, "typedef of a function type is a function pointer (§5)")
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
        for m in members:
            msz = self._csize(m.type)
            mal = self._calign(m.type)
            if msz is None or mal is None:
                return None
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
                value = (None if self.s.at_punct(";") else self.expr.parse_expression())
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
        expr = self.expr.parse_expression()
        self.s.expect_punct(";")
        return ast.ExprStmt(expr.file, expr.line, expr.col, expr)

    def _parse_control_head(self, kw: str):
        t = self._accept(kw)
        self.s.expect_punct("(")
        cond = self.expr.parse_expression()
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
        cond = self.expr.parse_expression()
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
            expr = self.expr.parse_expression()
            init = ast.ExprStmt(expr.file, expr.line, expr.col, expr)
            self.s.expect_punct(";")
        cond = None if self.s.at_punct(";") else self.expr.parse_expression()
        self.s.expect_punct(";")
        step = None if self.s.at_punct(")") else self.expr.parse_expression()
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
        control = self.expr.parse_expression()
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
