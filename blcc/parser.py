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

from blcc import ast
from blcc.lexer import DiagError, Lexer, SourceLine, Token, TokenStream
from blcc.expr_parser import ExprParser
from blcc.runtime import BUILTINS as _RUNTIME_BUILTINS

# §6 implicit builtins: always callable, never re-declarable. The NAME set is
# DERIVED from blcc/runtime.py's BUILTINS — one table, no mirrored list (P3-4).
BUILTINS = frozenset(_RUNTIME_BUILTINS)

_TYPE_KW = ("char", "short", "int", "long", "void")
_DECL_START_KW = _TYPE_KW + ("const", "struct", "enum", "static", "typedef",
                             "extern", "float", "double", "union", "unsigned")


class Parser:
    _STMT_HANDLERS = {"if": "parse_if", "while": "parse_while",
                      "do": "parse_do_while", "for": "parse_for",
                      "switch": "parse_switch", "case": "parse_nested_label",
                      "default": "parse_nested_label"}

    def __init__(self, toks: List[Token]):
        self.s = TokenStream(toks)
        self.scopes: List[Dict[str, tuple]] = [{}]
        self.struct_tags: Dict[str, Tuple[ast.Member, ...]] = {}
        self._pending: List[ast.Node] = []  # Struct/EnumDecls made by types
        self._bare_type_ok = False          # a tag/enum definition just read
        self.switch_depth = 0
        self.expr = ExprParser(self.s, self.is_typename, self.parse_type,
                               self.callable_known, self.expr_type)

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
                for m in self.struct_tags.get(base.tag, ()):
                    if m.name == node.field:
                        return m.type
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
        return t.kind == "id" and self.is_typename(t.text)

    # -- types ------------------------------------------------------------------

    def parse_type(self) -> ast.Node:
        """Base type + trailing pointer stars (casts, sizeof, declarators)."""
        ty = self.parse_base_type()
        while True:
            star = self.s.accept_punct("*")
            if star is None:
                return ty
            ty = ast.PtrType(star.file, star.line, star.col, ty)

    def parse_base_type(self) -> ast.Node:
        self._accept("const")  # §4 helper signatures use const; layout-irrelevant
        t = self.s.peek()
        if t.kind == "kw":
            if t.text in ("float", "double"):
                self._sema(t, "'{}' is not in the subset (§4: int types only)".format(t.text))
            if t.text == "union":
                self._sema(t, "'union' is not in the subset (§5)")
            if t.text == "unsigned":
                self._sema(t, "'unsigned' is not in the subset (§4: signed types only)")
            if t.text in _TYPE_KW:
                self.s.next()
                return ast.BuiltinType(t.file, t.line, t.col, t.text)
            if t.text == "struct":
                return self.parse_struct_type()
            if t.text == "enum":
                return self.parse_enum_type()
        if t.kind == "id" and self.is_typename(t.text):
            self.s.next()
            return self.lookup(t.text)[1]
        self._parse_err(t, "expected a type")

    def parse_struct_type(self) -> ast.Node:
        tok = self.s.next()  # 'struct'
        if self.s.at_punct("{"):
            tag = "<anon@{}:{}>".format(tok.file, tok.line)
        else:
            tag = self.s.expect_id("parse").text
        if self.s.accept_punct("{"):
            members = self.parse_struct_members()
            if tag in self.struct_tags:
                self._sema(tok, "struct '{}' is already defined".format(tag))
            self.struct_tags[tag] = members
            self._pending.append(ast.StructDecl(tok.file, tok.line, tok.col, tag, members))
            self._bare_type_ok = True
        elif self.s.at_punct(";"):
            self._pending.append(ast.StructDecl(tok.file, tok.line, tok.col, tag, None))
            self._bare_type_ok = True
        return ast.StructType(tok.file, tok.line, tok.col, tag)

    def parse_struct_members(self) -> Tuple[ast.Member, ...]:
        members: List[ast.Member] = []
        while not self.s.at_punct("}"):
            if self.s.accept_punct(";"):
                continue
            base = self.parse_base_type()
            pos = self.s.peek()
            name, ty, is_fn, _ = self.parse_declarator(base, ctx="member")
            if name is None:
                self._parse_err(pos, "struct member needs a name")
            if is_fn:
                self._parse_err(pos, "'function' member would be a function pointer")
            if self.s.accept_punct(":"):
                self._sema(pos, "'bitfield' members are not in the subset (§5)", ":")
            self.s.expect_punct(";")
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
        while self.s.at_punct("["):
            bracket = self.s.next()
            size = (None if self.s.at_punct("]") else self.expr.parse_expression())
            self.s.expect_punct("]")
            if size is None and ctx == "member":
                self._sema(bracket, "'array' members of a struct must have a fixed size (§5)")
            ty = ast.ArrayType(bracket.file, bracket.line, bracket.col, ty, size)
        params: Tuple[ast.Param, ...] = ()
        is_fn = False
        if self.s.at_punct("("):
            if ctx != "var":
                self._parse_err(pos, "'function' declarator is not allowed here")
            params = self.parse_params()
            is_fn = True
        return name, ty, is_fn, params

    def parse_params(self) -> Tuple[ast.Param, ...]:
        self.s.expect_punct("(")
        params: List[ast.Param] = []
        if self.s.accept_punct(")"):
            return ()
        if self._at("void") and self.s.at_punct(")", 1):
            self.s.next()
            self.s.next()
            return ()
        while True:
            t = self.s.peek()
            if t.kind == "punct" and t.text == "...":
                self._sema(t, "'variadic' functions are not in the subset (§5)")
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
        is_static = False
        static_tok = self._accept("static")
        if static_tok is not None:
            if not at_file:
                self._sema(static_tok, "'static' inside a function is not in the subset (§4)")
            is_static = True
        extern_tok = self._accept("extern")
        if extern_tok is not None:
            self._sema(extern_tok, "'extern' linkage is not in the subset (§4: file-scope static only)")
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
                out.append(ast.FuncDecl(pos.file, pos.line, pos.col, name, ty, params,
                                        body, is_static))
                break
            init = self.parse_initializer() if self.s.accept_punct("=") else None
            if (isinstance(ty, ast.ArrayType) and ty.size is None
                    and not isinstance(init, (ast.InitList, ast.StrLit))):
                self._sema(pos, "'array' declaration without size needs an initializer list (§4)")
            self.define(name, ("var", ty), pos)
            out.append(ast.VarDecl(pos.file, pos.line, pos.col, name, ty, init, is_static))
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
                items.append(self.parse_initializer())
                if not self.s.accept_punct(","):
                    break
            self.s.expect_punct("}")
            return ast.InitList(pos.file, pos.line, pos.col, tuple(items))
        return self.expr.parse_expression()

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
                self._sema(t, "'goto' is not in the subset (§5)")
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
        if t.kind == "id" and self.s.peek(1).kind == "punct" and self.s.peek(1).text == ":":
            self._sema(t, "'label' (goto label) is not in the subset — only case/default exist (§5)")
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
                ct = self.s.next()
                value = self.parse_int_constant("'case' label needs an integer constant (§4)")
                self.s.expect_punct(":")
                labels.append(("case", value, ct))
                continue
            if self._at("default"):
                dt = self.s.next()
                self.s.expect_punct(":")
                labels.append(("default", None, dt))
                continue
            stmt = self.parse_statement()
            for kind, value, ltok in reversed(labels):
                stmt = ast.Case(ltok.file, ltok.line, ltok.col, value, stmt) if kind == "case" \
                    else ast.Default(ltok.file, ltok.line, ltok.col, stmt)
            labels = []
            stmts.append(stmt)
        for kind, value, ltok in labels:  # trailing labels: empty arms are legal
            stmts.append(ast.Case(ltok.file, ltok.line, ltok.col, value, None) if kind == "case"
                         else ast.Default(ltok.file, ltok.line, ltok.col, None))
        self.s.expect_punct("}")
        self.switch_depth -= 1
        self._check_case_labels(stmts)
        return ast.Switch(t.file, t.line, t.col, control, tuple(stmts))

    def parse_nested_label(self) -> ast.Node:
        t = self.s.next()  # 'case' / 'default' outside the body loop
        if self.switch_depth == 0:
            self._sema(t, "'{}' label outside a 'switch' is not in the subset (§4)".format(t.text))
        if t.text == "case":
            value = self.parse_int_constant("'case' label needs an integer constant (§4)")
            self.s.expect_punct(":")
            return ast.Case(t.file, t.line, t.col, value, self.parse_statement())
        self.s.expect_punct(":")
        return ast.Default(t.file, t.line, t.col, self.parse_statement())

    def _check_case_labels(self, stmts: List[ast.Node]) -> None:
        seen: Dict[int, bool] = {}
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
            elif isinstance(s, ast.Default):
                if has_default:
                    self._sema(s, "'default' appears more than once in one switch (§4)", "default")
                has_default = True
            if isinstance(s, ast.Compound):
                stack.extend(s.body)
            elif isinstance(s, (ast.Case, ast.Default)):
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
