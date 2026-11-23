"""blcc/pp_tok.py — the preprocessor stream primitives (MC 12775
clean-code split of pp_expand.py; MOVED VERBATIM — zero behavior change):
the stream-item alias (token text + per-token hidden extras, F-3/MC 12436),
the whitespace test, and the item->text reader. A LEAF module: no blcc
imports — blcc/pp_args.py and blcc/pp_expand.py both build on it.
"""
from __future__ import annotations

from typing import Tuple, Union


Item = Union[str, Tuple[str, frozenset]]


def is_ws(tok: str) -> bool:
    return tok.strip() == ""


def plain(item: Item) -> str:
    """The token text of a stream item (items carry per-token hidden extras
    as (tok, extras) tuples — see Expander._expand, F-3/MC 12436)."""
    return item if isinstance(item, str) else item[0]
