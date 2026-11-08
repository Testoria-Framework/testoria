"""Generate a Testoria spec (smoke + contract tests) from an OpenAPI 3 / Swagger 2 document."""

from __future__ import annotations

import re
from typing import Any, Dict, List

METHODS = ("get", "post", "put", "patch", "delete")


def _resolve(doc: Dict[str, Any], node: Any, depth: int = 0) -> Any:
    if depth > 20:
        return {}
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str) and node["$ref"].startswith("#/"):
            target: Any = doc
            for part in node["$ref"][2:].split("/"):
                target = target.get(part.replace("~1", "/").replace("~0", "~"), {}) if isinstance(target, dict) else {}
            return _resolve(doc, target, depth + 1)
        return {k: _resolve(doc, v, depth + 1) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(doc, v, depth + 1) for v in node]
    return node


def _example(schema: Dict[str, Any]) -> Any:
    if not isinstance(schema, dict):
        return None
    for key in ("example", "default"):
        if key in schema:
            return schema[key]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    for comb in ("allOf", "oneOf", "anyOf"):
        if comb in schema and schema[comb]:
            if comb == "allOf":
                merged: Dict[str, Any] = {}
                for sub in schema[comb]:
                    ex = _example(sub)
                    if isinstance(ex, dict):
                        merged.update(ex)
                return merged
            return _example(schema[comb][0])
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        return {k: _example(v) for k, v in (schema.get("properties") or {}).items()}
    if t == "array":
        return [_example(schema.get("items") or {})]
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return True
    fmt = schema.get("format")
    return {"email": "user@example.com", "uuid": "00000000-0000-4000-8000-000000000000",
            "date-time": "2024-01-01T00:00:00Z", "date": "2024-01-01", "uri": "https://example.com"}.get(fmt, "string")


def _strip_for_validation(schema: Any) -> Any:
    """Drop OpenAPI-only keywords so the schema validates as JSON Schema."""
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k in ("example", "examples", "xml", "externalDocs", "readOnly", "writeOnly", "deprecated", "discriminator"):
                continue
            out[k] = _strip_for_validation(v)
        if out.pop("nullable", False) and "type" in out:
            out["type"] = [out["type"], "null"] if isinstance(out["type"], str) else out["type"] + ["null"]
        return out
    if isinstance(schema, list):
        return [_strip_for_validation(v) for v in schema]
    return schema


def to_spec(doc: Dict[str, Any], include_mutations: bool = False, base_url: str = "") -> Dict[str, Any]:
    doc = _resolve(doc, doc)
    servers = doc.get("servers") or []
    if not base_url:
        if servers:
            base_url = servers[0].get("url", "")
        elif doc.get("host"):
            scheme = (doc.get("schemes") or ["https"])[0]
            base_url = f"{scheme}://{doc['host']}{doc.get('basePath', '')}"
    title = (doc.get("info") or {}).get("title", "API")
    tests: List[Dict[str, Any]] = []
    for path, item in (doc.get("paths") or {}).items():
        common = item.get("parameters") or []
        for method in METHODS:
            op = item.get(method)
            if not op:
                continue
            if method != "get" and not include_mutations:
                continue
            params = common + (op.get("parameters") or [])
            url = path
            query: Dict[str, Any] = {}
            for p in params:
                ex = p.get("example", _example(p.get("schema") or {"type": p.get("type", "string")}))
                if p.get("in") == "path":
                    url = url.replace("{" + p["name"] + "}", str(ex if ex not in (None, "string") else 1))
                elif p.get("in") == "query" and p.get("required"):
                    query[p["name"]] = ex
            url = re.sub(r"\{[^}]+\}", "1", url)
            responses = op.get("responses") or {}
            ok_codes = sorted(c for c in responses if str(c).startswith("2"))
            code = ok_codes[0] if ok_codes else "2xx"
            test: Dict[str, Any] = {
                "name": op.get("summary") or op.get("operationId") or f"{method.upper()} {path}",
                "tags": list(op.get("tags") or []) + ["openapi", "smoke" if method == "get" else "mutation"],
                "request": {"method": method.upper(), "url": url},
                "expect": {"status": int(code) if str(code).isdigit() else code},
            }
            if query:
                test["request"]["params"] = query
            body = (op.get("requestBody") or {}).get("content", {}).get("application/json", {}).get("schema")
            if body:
                test["request"]["json"] = _example(body)
            schema = None
            if ok_codes:
                r = responses[ok_codes[0]] or {}
                schema = (r.get("content") or {}).get("application/json", {}).get("schema") or r.get("schema")
            if schema:
                test["expect"]["schema"] = _strip_for_validation(schema)
            tests.append(test)
    return {"name": f"{title} (generated from OpenAPI)", "base_url": base_url or "{{ base_url }}", "tests": tests}
