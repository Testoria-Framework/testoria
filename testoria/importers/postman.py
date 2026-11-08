"""Convert a Postman v2.x collection into a Testoria spec."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _pm_vars(s: Any) -> Any:
    if isinstance(s, str):
        return re.sub(r"\{\{\s*([\w.\-]+)\s*\}\}", lambda m: "{{ " + m.group(1).replace("-", "_") + " }}", s)
    if isinstance(s, dict):
        return {k: _pm_vars(v) for k, v in s.items()}
    if isinstance(s, list):
        return [_pm_vars(v) for v in s]
    return s


def _url(u: Any) -> str:
    if isinstance(u, str):
        return u
    if isinstance(u, dict):
        if u.get("raw"):
            return u["raw"]
        host = ".".join(u.get("host") or [])
        path = "/".join(u.get("path") or [])
        return f"{u.get('protocol', 'https')}://{host}/{path}"
    return "/"


def _walk(items: List[Dict[str, Any]], prefix: str, out: List[Dict[str, Any]]) -> None:
    for it in items:
        if "item" in it:
            _walk(it["item"], f"{prefix}{it.get('name', '')} / ", out)
            continue
        req = it.get("request") or {}
        if isinstance(req, str):
            req = {"url": req, "method": "GET"}
        test: Dict[str, Any] = {
            "name": prefix + it.get("name", "request"),
            "request": {"method": req.get("method", "GET"), "url": _url(req.get("url"))},
            "expect": {"status": "2xx"},
        }
        headers = {h["key"]: h.get("value", "") for h in req.get("header") or [] if not h.get("disabled")}
        if headers:
            test["request"]["headers"] = headers
        body = req.get("body") or {}
        if body.get("mode") == "raw" and body.get("raw"):
            import json
            try:
                test["request"]["json"] = json.loads(body["raw"])
            except ValueError:
                test["request"]["body"] = body["raw"]
        elif body.get("mode") == "urlencoded":
            test["request"]["form"] = {p["key"]: p.get("value", "") for p in body.get("urlencoded") or []}
        for ev in it.get("event") or []:
            src = "\n".join((ev.get("script") or {}).get("exec") or [])
            m = re.search(r"to\.have\.status\((\d+)\)", src)
            if m:
                test["expect"]["status"] = int(m.group(1))
        out.append(test)


def to_spec(collection: Dict[str, Any]) -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = []
    _walk(collection.get("item") or [], "", tests)
    variables = {v["key"].replace("-", "_"): v.get("value") for v in collection.get("variable") or [] if "key" in v}
    spec: Dict[str, Any] = {"name": (collection.get("info") or {}).get("name", "Postman collection"), "tests": _pm_vars(tests)}
    if variables:
        spec["variables"] = variables
    return spec
