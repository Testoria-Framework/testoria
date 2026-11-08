"""Small JSONPath subset: $.a.b, $.a[0], $.a[-1], $.a[*].b, $..b, $.a.length(), a.b.0"""

from __future__ import annotations

import re
from typing import Any, List

_MISSING = object()
_TOKEN = re.compile(r"\.\.([A-Za-z0-9_\-]+)|\.?([A-Za-z_\-][A-Za-z0-9_\-]*|\d+)(\(\))?|\[(\*|-?\d+|'[^']*'|\"[^\"]*\")\]|\.(\*)")


def _tokens(path: str) -> List[tuple]:
    path = path.strip()
    if path in ("$", ""):
        return []
    if path.startswith("$"):
        path = path[1:]
    out, pos = [], 0
    while pos < len(path):
        m = _TOKEN.match(path, pos)
        if not m or m.end() == pos:
            raise ValueError(f"Invalid JSON path near '{path[pos:]}'")
        deep, name, call, idx, star = m.groups()
        if deep:
            out.append(("deep", deep))
        elif name is not None:
            out.append(("call", name) if call else ("key", name))
        elif idx is not None:
            if idx == "*":
                out.append(("all", None))
            elif idx[0] in "'\"":
                out.append(("key", idx[1:-1]))
            else:
                out.append(("index", int(idx)))
        elif star:
            out.append(("all", None))
        pos = m.end()
    return out


def _deep(obj: Any, key: str) -> List[Any]:
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                found.append(v)
            found.extend(_deep(v, key))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_deep(v, key))
    return found


def query(obj: Any, path: str) -> List[Any]:
    """Return all matches for path (empty list when nothing matches)."""
    current = [obj]
    for kind, val in _tokens(path):
        nxt: List[Any] = []
        for item in current:
            if kind == "key":
                if isinstance(item, dict) and val in item:
                    nxt.append(item[val])
                elif isinstance(item, list) and val.isdigit() and int(val) < len(item):
                    nxt.append(item[int(val)])
            elif kind == "index":
                if isinstance(item, list) and -len(item) <= val < len(item):
                    nxt.append(item[val])
            elif kind == "all":
                if isinstance(item, list):
                    nxt.extend(item)
                elif isinstance(item, dict):
                    nxt.extend(item.values())
            elif kind == "deep":
                nxt.extend(_deep(item, val))
            elif kind == "call":
                if val in ("length", "size", "len"):
                    if isinstance(item, (list, dict, str)):
                        nxt.append(len(item))
                elif val == "keys" and isinstance(item, dict):
                    nxt.append(list(item.keys()))
                else:
                    raise ValueError(f"Unsupported function {val}()")
        current = nxt
    return current


def get(obj: Any, path: str, default: Any = _MISSING) -> Any:
    """Return a single value; wildcard/deep paths return a list."""
    toks = _tokens(path)
    matches = query(obj, path)
    multi = any(k in ("all", "deep") for k, _ in toks)
    if multi:
        return matches
    if not matches:
        if default is _MISSING:
            raise KeyError(path)
        return default
    return matches[0]


def exists(obj: Any, path: str) -> bool:
    try:
        return len(query(obj, path)) > 0
    except ValueError:
        return False
