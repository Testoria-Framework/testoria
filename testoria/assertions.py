"""Expectation engine used by the declarative runner."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from testoria import jsonpath, schema as schema_mod
from testoria.http import Response

OPERATORS = {
    "eq", "equals", "ne", "not_equals", "gt", "gte", "lt", "lte", "contains", "not_contains",
    "matches", "type", "exists", "length", "min_length", "max_length", "in", "one_of", "not_in",
    "startswith", "starts_with", "endswith", "ends_with", "empty", "not_empty", "schema", "approx",
    "between", "is_null", "not_null",
}

_TYPE_NAMES = {
    "string": str, "str": str, "number": (int, float), "integer": int, "int": int, "float": float,
    "boolean": bool, "bool": bool, "array": list, "list": list, "object": dict, "dict": dict,
    "null": type(None), "none": type(None),
}


def _is_operator_dict(v: Any) -> bool:
    return isinstance(v, dict) and v and all(k in OPERATORS for k in v)


def _type_check(value: Any, tname: str) -> bool:
    if tname in ("integer", "int"):
        return isinstance(value, int) and not isinstance(value, bool)
    if tname == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    t = _TYPE_NAMES.get(tname.lower())
    if t is None:
        raise ValueError(f"Unknown type '{tname}'")
    return isinstance(value, t)


def check_value(actual: Any, expected: Any, label: str, present: bool = True) -> List[str]:
    """Compare a value with a literal or operator dict. Returns failure messages."""
    errs: List[str] = []
    if not _is_operator_dict(expected):
        if not present:
            return [f"{label}: path not found (expected {expected!r})"]
        if actual != expected and not (_num(actual) and _num(expected) and float(actual) == float(expected)):
            errs.append(f"{label}: expected {expected!r}, got {actual!r}")
        return errs

    for op, exp in expected.items():
        if op == "exists":
            if bool(exp) != present:
                errs.append(f"{label}: expected {'to exist' if exp else 'not to exist'}")
            continue
        if not present:
            errs.append(f"{label}: path not found (operator {op})")
            continue
        ok = True
        try:
            if op in ("eq", "equals"):
                ok = actual == exp or (_num(actual) and _num(exp) and float(actual) == float(exp))
            elif op in ("ne", "not_equals"):
                ok = actual != exp
            elif op == "gt":
                ok = actual > exp
            elif op == "gte":
                ok = actual >= exp
            elif op == "lt":
                ok = actual < exp
            elif op == "lte":
                ok = actual <= exp
            elif op == "between":
                ok = exp[0] <= actual <= exp[1]
            elif op == "approx":
                target, tol = (exp if isinstance(exp, list) else [exp, 0.01])
                ok = abs(float(actual) - float(target)) <= float(tol)
            elif op == "contains":
                ok = _contains(actual, exp)
            elif op == "not_contains":
                ok = not _contains(actual, exp)
            elif op == "matches":
                ok = re.search(str(exp), str(actual)) is not None
            elif op == "type":
                types = exp if isinstance(exp, list) else [exp]
                ok = any(_type_check(actual, t) for t in types)
            elif op == "length":
                if isinstance(exp, dict):
                    errs.extend(check_value(len(actual), exp, f"{label}.length()"))
                    continue
                ok = len(actual) == exp
            elif op == "min_length":
                ok = len(actual) >= exp
            elif op == "max_length":
                ok = len(actual) <= exp
            elif op in ("in", "one_of"):
                ok = actual in exp
            elif op == "not_in":
                ok = actual not in exp
            elif op in ("startswith", "starts_with"):
                ok = str(actual).startswith(str(exp))
            elif op in ("endswith", "ends_with"):
                ok = str(actual).endswith(str(exp))
            elif op == "empty":
                ok = (not actual) == bool(exp)
            elif op == "not_empty":
                ok = bool(actual) == bool(exp)
            elif op == "is_null":
                ok = (actual is None) == bool(exp)
            elif op == "not_null":
                ok = (actual is not None) == bool(exp)
            elif op == "schema":
                problems = schema_mod.validate(actual, exp)
                if problems:
                    errs.extend(f"{label} schema: {p}" for p in problems[:10])
                continue
        except (TypeError, ValueError) as e:
            errs.append(f"{label}: cannot apply {op} to {actual!r}: {e}")
            continue
        if not ok:
            errs.append(f"{label}: expected {op} {exp!r}, got {actual!r}")
    return errs


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _contains(actual: Any, exp: Any) -> bool:
    if isinstance(actual, str):
        return str(exp) in actual
    if isinstance(actual, list):
        if isinstance(exp, dict):
            return any(isinstance(i, dict) and all(i.get(k) == v for k, v in exp.items()) for i in actual)
        return exp in actual
    if isinstance(actual, dict):
        if isinstance(exp, dict):
            return all(k in actual and actual[k] == v for k, v in exp.items())
        return exp in actual
    return False


def status_matches(status: int, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(status_matches(status, e) for e in expected)
    if isinstance(expected, str):
        e = expected.strip().lower()
        if re.fullmatch(r"[1-5]xx", e):
            return str(status)[0] == e[0]
        if "-" in e:
            lo, hi = e.split("-", 1)
            return int(lo) <= status <= int(hi)
        return status == int(e)
    return status == int(expected)


def evaluate_expectations(resp: Response, expect: Dict[str, Any]) -> List[str]:
    """Return a list of failure messages for a response against an `expect` block."""
    failures: List[str] = []
    if not expect:
        return failures
    if resp.error and "status" not in expect:
        return [f"request failed: {resp.error}"]

    if "status" in expect:
        if not status_matches(resp.status, expect["status"]):
            detail = f" ({resp.error})" if resp.error else ""
            snippet = resp.text[:200].replace("\n", " ")
            failures.append(f"status: expected {expect['status']}, got {resp.status}{detail}"
                            + (f" body: {snippet}" if snippet else ""))

    for key in ("max_time_ms", "response_time_ms", "max_ms"):
        if key in expect and resp.elapsed_ms > float(expect[key]):
            failures.append(f"response time {resp.elapsed_ms:.0f}ms exceeded {expect[key]}ms")

    for name, exp in (expect.get("headers") or {}).items():
        val = resp.header(name)
        if isinstance(exp, str) and not _is_operator_dict(exp):
            if val is None:
                failures.append(f"header {name}: missing")
            elif exp.lower() not in val.lower():
                failures.append(f"header {name}: expected to contain {exp!r}, got {val!r}")
        else:
            failures.extend(check_value(val, exp, f"header {name}", present=val is not None))

    if "content_type" in expect:
        ct = resp.header("Content-Type") or ""
        if str(expect["content_type"]).lower() not in ct.lower():
            failures.append(f"content-type: expected {expect['content_type']!r}, got {ct!r}")

    body_checks = expect.get("body")
    if isinstance(body_checks, str):
        if resp.text != body_checks:
            failures.append(f"body: expected {body_checks[:80]!r}, got {resp.text[:80]!r}")
    elif isinstance(body_checks, dict):
        failures.extend(check_value(resp.text, body_checks, "body"))
    for s in _as_list(expect.get("body_contains")):
        if str(s) not in resp.text:
            failures.append(f"body: expected to contain {s!r}")
    for s in _as_list(expect.get("body_not_contains")):
        if str(s) in resp.text:
            failures.append(f"body: expected not to contain {s!r}")

    data = None
    needs_json = any(k in expect for k in ("json", "json_equals", "schema", "json_contains"))
    if needs_json:
        if not resp.is_json():
            failures.append(f"body is not valid JSON: {resp.text[:120]!r}")
            return failures
        data = resp.json()

    if "json_equals" in expect and data != expect["json_equals"]:
        failures.append(f"json: expected exactly {expect['json_equals']!r}, got {data!r}")
    if "json_contains" in expect and not _contains(data if isinstance(data, (dict, list)) else {}, expect["json_contains"]):
        failures.append(f"json: expected to contain {expect['json_contains']!r}")
    for path, exp in (expect.get("json") or {}).items():
        p = path if path.startswith("$") else "$." + path
        try:
            matches = jsonpath.query(data, p)
            multi = any(t in p for t in ("[*]", ".*", ".."))
            present = len(matches) > 0
            actual = matches if multi else (matches[0] if matches else None)
        except ValueError as e:
            failures.append(f"{path}: {e}")
            continue
        failures.extend(check_value(actual, exp, path, present=present))
    if "schema" in expect and isinstance(expect["schema"], dict):
        for p in schema_mod.validate(data, expect["schema"])[:20]:
            failures.append(f"schema: {p}")
    return failures


def _as_list(v: Any) -> List[Any]:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]
