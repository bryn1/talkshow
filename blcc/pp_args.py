"""blcc/pp_args.py — THE macro-argument collection & prescan law, one
home (MC 12775 clean-code split of pp_expand.py; methods MOVED VERBATIM —
zero behavior change). PpArgsMixin rides blcc.pp_expand.Expander (the
mixin idiom of blcc/memfold.py): single-argument reader, bracket-balanced
argument collection with the multi-line continuation splice, the GNU
min-args count law (F2), the variadic-tail RAW range rule (P2a), the
plain-parameter prescan (items survive the boundary, MC 12438) and the
param usage table that keeps `#`/`##` operands raw.
"""
from __future__ import annotations

from blcc.lexer import DiagError
from blcc.pp_tok import is_ws, plain


class PpArgsMixin:
    def _need_one_arg(self, toks, i, path, line, macro, more):
        k = i + 1
        n = len(toks)
        while k < n and is_ws(plain(toks[k])):
            k += 1
        if not (k < n and plain(toks[k]) == "("):
            return None, i
        args_list, close = self._collect_args(toks, k, path, line, macro, more)
        if len(args_list) != 1:
            raise DiagError("pp", path, line, 1,
                            "macro '%s' takes 1 argument" % macro.name,
                            macro.name)
        return args_list[0], close

    # -- argument collection ----------------------------------------------------

    def _collect_args(self, toks: List[Item], open_i: int, path: str,
                      line: int, macro: Macro, more):
        """Returns (list-of-arg-item-lists, index of the ')' token). Items
        (with their blue-paint extras) flow into the argument lists; the
        continuation callback appends further logical lines to THIS stream
        (`more(dst)`), so a splice that re-bound the list keeps working."""
        groups: List[List[Item]] = []
        group: List[Item] = []
        depth = 0
        k = open_i
        n = len(toks)
        while True:
            if k >= n:
                if more and more(toks):
                    n = len(toks)           # multi-line invocation (R2 spliced
                    continue                # logical line may still continue)
                raise DiagError("pp", path, line, 1,
                                "unterminated argument list for macro "
                                "'%s'" % macro.name, macro.name)
            t = plain(toks[k])
            if t in "([{":
                depth += 1
                if depth == 1:
                    k += 1
                    continue
            elif t in ")]}":
                depth -= 1
                if depth == 0:
                    groups.append(group)
                    return groups, k
            elif t == "," and depth == 1:
                groups.append(group)
                group = []
                k += 1
                continue
            if depth >= 1:
                group.append(toks[k])
            k += 1

    def _check_args(self, groups: List[List[Item]], macro: Macro, path: str,
                    line: int) -> List[List[Item]]:
        named = macro.params or []
        # F2 (GNU spelling `name(p..., x...)`): the NAMED variadic param
        # answers to the tail, so it is NOT a required argument — the call
        # needs only the non-variadic named params (mipi_dbi_command(dbi,
        # cmd, seq...) accepts mipi_dbi_command(dbi, 0x01); oracle).
        required = len(named) - (1 if (macro.variadic and
                                       macro.var_name in named) else 0)
        fixed = []
        for idx, g in enumerate(groups):
            # P2a (oracle stringify matrix): a variadic parameter answers to
            # ONE contiguous token range — the tail groups stay RAW here and
            # are flattened-with-commas + range-end trimmed in _substitute
            # (gcc keeps the source whitespace around the joining commas:
            # Q(a , b) -> "a , b", Q(a,b) -> "a,b", Q( ,) -> ","). Named
            # params keep their per-argument trim (S( a ) -> "a").
            tail = macro.variadic and idx >= required
            if not tail:
                while g and is_ws(plain(g[0])):
                    g = g[1:]
                while g and is_ws(plain(g[-1])):
                    g = g[:-1]
            fixed.append(g)
        if len(named) == 0 and len(fixed) == 1 and not fixed[0]:
            return []                      # zero-argument invocation() form
        if len(fixed) < required or (not macro.variadic and
                                       len(fixed) > required):
            raise DiagError("pp", path, line, 1,
                            "macro '%s' takes %s argument(s)" % (
                                macro.name, required if not macro.variadic
                                else "at least %d" % required), macro.name)
        return fixed

    # -- prescan (plain parameters only, fresh hidden set — oracle F(F(1))) ----

    def _prescan_args(self, args: List[List[Item]], macro: Macro, path: str,
                      line: int, more, protect: bool = False
                      ) -> List[List[Item]]:
        usage = self._param_usage(macro)
        out = []
        for idx, arg in enumerate(args):
            name = self._param_at(macro, idx)
            if name is not None and usage.get(name) == "plain":
                # ITEMS SURVIVE the prescan boundary (MC 12438): the
                # blue-paint extras of produced tokens must reach the
                # substitution-site rescan.
                out.append(self._expand_items(arg, set(), path, line, more,
                                              protect))
            else:
                out.append(arg)
        return out

    @staticmethod
    def _param_at(macro: Macro, idx: int) -> Optional[str]:
        if macro.params is None:
            return None
        start = len(macro.params) - (1 if (macro.variadic and
                                           macro.var_name in macro.params)
                                      else 0)
        if idx < start:
            return macro.params[idx]
        if macro.variadic and idx >= start:
            return macro.var_name
        return None

    @staticmethod
    def _param_usage(macro: Macro) -> Dict[str, str]:
        """param -> 'plain' | 'raw' (a #/## operand is raw: never prescanned)."""
        names = set(macro.params or [])
        if macro.variadic:
            names.add(macro.var_name)
        usage: Dict[str, str] = {}
        body = macro.body
        for j, t in enumerate(body):
            if t == "#":
                nxt = next((b for b in body[j + 1:] if not is_ws(b)), None)
                if nxt in names:
                    usage[nxt] = "raw"
            elif t == "##":
                for side in (reversed(body[:j]), body[j + 1:]):
                    nxt = next((b for b in side if not is_ws(b)), None)
                    if nxt in names:
                        usage[nxt] = "raw"
            elif t in names:
                usage.setdefault(t, "plain")
        return usage
