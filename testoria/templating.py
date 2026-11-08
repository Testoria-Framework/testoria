"""Variable interpolation: {{ name }}, {{ env.NAME }}, {{ $uuid }}, {{ name | default('x') }}."""

from __future__ import annotations

import base64
import datetime as _dt
import os
import random
import re
import string
import time
import uuid
from typing import Any, Dict

from testoria import jsonpath

_EXPR = re.compile(r"\{\{\s*(.+?)\s*\}\}")
_FULL = re.compile(r"^\{\{\s*(.+?)\s*\}\}$")


def _rand_str(n: int = 8) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def _dynamic(name: str, arg: str = "") -> Any:
    if name == "uuid":
        return str(uuid.uuid4())
    if name == "timestamp":
        return int(time.time())
    if name == "timestampMs":
        return int(time.time() * 1000)
    if name == "isoNow":
        return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if name == "date":
        return _dt.date.today().isoformat()
    if name == "randomInt":
        lo, hi = (arg.split(",") + ["1000000"])[:2] if arg else ("0", "1000000")
        return random.randint(int(lo or 0), int(hi))
    if name == "randomString":
        return _rand_str(int(arg) if arg else 8)
    if name == "randomEmail":
        return f"testoria.{_rand_str(10)}@example.com"
    if name == "randomName":
        return random.choice(["Ada", "Alan", "Grace", "Linus", "Margaret", "Dennis"]) + " " + _rand_str(5).title()
    if name == "randomBool":
        return random.choice([True, False])
    raise KeyError(f"Unknown dynamic variable ${name}")


def _apply_filter(value: Any, flt: str) -> Any:
    m = re.match(r"(\w+)(?:\((.*)\))?$", flt.strip())
    if not m:
        raise ValueError(f"Bad filter '{flt}'")
    name, arg = m.group(1), m.group(2)
    arg_val = arg.strip().strip("'\"") if arg is not None else None
    if name == "default":
        return value if value not in (None, "") else _coerce(arg_val)
    if name == "upper":
        return str(value).upper()
    if name == "lower":
        return str(value).lower()
    if name == "int":
        return int(value)
    if name == "float":
        return float(value)
    if name == "str":
        return str(value)
    if name == "length":
        return len(value)
    if name == "b64encode":
        return base64.b64encode(str(value).encode()).decode()
    if name == "b64decode":
        return base64.b64decode(str(value)).decode()
    if name == "json":
        import json
        return json.dumps(value)
    raise ValueError(f"Unknown filter '{name}'")


def _coerce(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    if v in ("true", "false"):
        return v == "true"
    if v == "null":
        return None
    return v


class _Undefined:
    pass


UNDEFINED = _Undefined()


def evaluate(expr: str, ctx: Dict[str, Any]) -> Any:
    parts = [p for p in re.split(r"\|(?![^()]*\))", expr)]
    head = parts[0].strip()
    value: Any
    if head.startswith("$"):
        m = re.match(r"\$(\w+)(?:\((.*)\))?$", head)
        if not m:
            raise ValueError(f"Bad dynamic expression '{head}'")
        value = _dynamic(m.group(1), (m.group(2) or "").strip())
    elif head.startswith("env."):
        value = os.environ.get(head[4:], None)
    elif head[:1] in "'\"" and head[-1:] == head[:1]:
        value = head[1:-1]
    else:
        root, _, rest = head.partition(".")
        root_name = re.match(r"[^\[]+", root).group(0) if root else root
        if root_name in ctx:
            base = ctx[root_name]
            tail = head[len(root_name):]
            if tail:
                try:
                    value = jsonpath.get(base, "$" + (tail if tail.startswith(("[", ".")) else "." + tail))
                except (KeyError, ValueError):
                    value = None
            else:
                value = base
        else:
            value = None
    for f in parts[1:]:
        value = _apply_filter(value, f)
    return value


def render(obj: Any, ctx: Dict[str, Any]) -> Any:
    """Recursively interpolate strings in dicts/lists. Whole-string expressions keep native type."""
    if isinstance(obj, str):
        full = _FULL.match(obj)
        if full:
            return evaluate(full.group(1), ctx)
        def repl(m: "re.Match[str]") -> str:
            v = evaluate(m.group(1), ctx)
            if v is None:
                return ""
            if isinstance(v, (dict, list)):
                import json
                return json.dumps(v)
            if isinstance(v, bool):
                return "true" if v else "false"
            return str(v)
        return _EXPR.sub(repl, obj)
    if isinstance(obj, dict):
        return {render(k, ctx) if isinstance(k, str) else k: render(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render(v, ctx) for v in obj]
    return obj
