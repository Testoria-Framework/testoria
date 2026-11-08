"""Mock HTTP server.

* Loads WireMock mapping files (`{"request": ..., "response": ...}` or `{"mappings": [...]}`)
  and MockServer expectations (`{"httpRequest": ..., "httpResponse": ...}`).
* Supports response templating ({{request.pathSegments.[1]}}, {{jsonPath request.body '$.x'}},
  {{now format='yyyy-MM-dd'}}, {{randomValue length=8 type='ALPHANUMERIC'}}, {{request.query.x}}, ...).
* Optional stateful REST mode (`--db db.json`): every top-level key becomes a CRUD resource.
* Admin API: GET /__admin/health, GET/POST /__admin/mappings, GET /__admin/requests, POST /__admin/reset.
"""

from __future__ import annotations

import datetime as _dt
import json
import random
import re
import string
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from testoria import jsonpath


# ---------------------------------------------------------------------------- mapping model
def _normalize(raw: Dict[str, Any], source: str, order: int) -> Optional[Dict[str, Any]]:
    if "request" in raw and "response" in raw:
        m = dict(raw)
    elif "httpRequest" in raw:
        req, resp = raw.get("httpRequest") or {}, raw.get("httpResponse") or {}
        headers = {k: (v[0] if isinstance(v, list) and v else v) for k, v in (resp.get("headers") or {}).items()}
        body = resp.get("body")
        m = {
            "request": {"method": req.get("method"), "urlPath": req.get("path")},
            "response": {"status": resp.get("statusCode", 200), "headers": headers},
        }
        if isinstance(body, (dict, list)):
            if isinstance(body, dict) and body.get("type") == "JSON" and "json" in body:
                m["response"]["jsonBody"] = body["json"]
            else:
                m["response"]["jsonBody"] = body
        elif body is not None:
            m["response"]["body"] = str(body)
        if req.get("queryStringParameters"):
            m["request"]["queryParameters"] = {
                k: {"equalTo": (v[0] if isinstance(v, list) else v)} for k, v in req["queryStringParameters"].items()
            }
        if req.get("headers"):
            m["request"]["headers"] = {
                k: {"matches": ".*" if v in ([".*"], ".*") else re.escape(v[0] if isinstance(v, list) else v) + ".*"}
                for k, v in req["headers"].items()
            }
        if isinstance(req.get("body"), dict):
            rb = req["body"]
            m["request"]["bodyPatterns"] = [{"equalToJson": rb.get("json", rb)}] if rb.get("type") in (None, "JSON") else []
        delay = (raw.get("httpResponse") or {}).get("delay") or {}
        if delay.get("value"):
            mult = {"MILLISECONDS": 1, "SECONDS": 1000}.get(delay.get("timeUnit", "MILLISECONDS"), 1)
            m["response"]["fixedDelayMilliseconds"] = delay["value"] * mult
    else:
        return None
    m["_source"] = source
    m["_order"] = order
    m.setdefault("priority", 5)
    m.setdefault("id", str(uuid.uuid4()))
    return m


def load_mappings(paths: List[str]) -> List[Dict[str, Any]]:
    files: List[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            files.extend(sorted(x for x in pp.rglob("*.json") if "__files" not in x.parts))
        elif pp.is_file():
            files.append(pp)
    out: List[Dict[str, Any]] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except ValueError as e:
            raise ValueError(f"Invalid mapping JSON in {f}: {e}") from e
        items = data.get("mappings", [data]) if isinstance(data, dict) else data
        for item in items:
            m = _normalize(item, str(f), len(out))
            if m:
                m["_dir"] = str(f.parent)
                out.append(m)
    return out


# ---------------------------------------------------------------------------- matching
def _match_value(actual: Optional[str], spec: Any) -> bool:
    if not isinstance(spec, dict):
        return actual == str(spec)
    if spec.get("absent"):
        return actual is None
    if actual is None:
        return False
    a = actual.lower() if spec.get("caseInsensitive") else actual
    for op, exp in spec.items():
        if op == "caseInsensitive":
            continue
        e = str(exp).lower() if spec.get("caseInsensitive") else str(exp)
        if op == "equalTo" and a != e:
            return False
        if op == "contains" and e not in a:
            return False
        if op == "matches" and not re.fullmatch(e, actual):
            return False
        if op == "doesNotMatch" and re.fullmatch(e, actual):
            return False
    return True


def _match_body(body: str, patterns: List[Dict[str, Any]]) -> bool:
    data: Any = None
    parsed = False
    for p in patterns:
        if "matchesJsonPath" in p:
            if not parsed:
                parsed = True
                try:
                    data = json.loads(body) if body else None
                except ValueError:
                    data = None
            if data is None:
                return False
            expr = p["matchesJsonPath"]
            path = expr if isinstance(expr, str) else expr.get("expression", "$")
            filt = re.match(r"^\$\[\?\(@\.(\w+)\s*(<|>|<=|>=|==|!=)\s*(.+)\)\]$", path)
            if filt:
                key, op, val = filt.groups()
                try:
                    v = data.get(key) if isinstance(data, dict) else None
                    target = json.loads(val.strip().strip("'").replace("'", '"')) if val.strip()[0] not in "'" else val.strip("'")
                    ok = v is not None and {"<": v < target, ">": v > target, "<=": v <= target,
                                            ">=": v >= target, "==": v == target, "!=": v != target}[op]
                except (TypeError, ValueError, AttributeError):
                    ok = False
                if not ok:
                    return False
                continue
            try:
                matches = jsonpath.query(data, path)
            except ValueError:
                return False
            if not matches:
                return False
            sub = expr if isinstance(expr, dict) else {k: v for k, v in p.items() if k != "matchesJsonPath"}
            sub = {k: v for k, v in sub.items() if k != "expression"}
            if sub:
                # Sibling operators: apply to the matched value, or the raw body for "$".
                target = body if path == "$" else (matches[0] if isinstance(matches[0], str) else json.dumps(matches[0]))
                if "lessThan" in sub:
                    try:
                        if not float(matches[0]) < float(sub.pop("lessThan")):
                            return False
                    except (TypeError, ValueError):
                        return False
                if "greaterThan" in sub:
                    try:
                        if not float(matches[0]) > float(sub.pop("greaterThan")):
                            return False
                    except (TypeError, ValueError):
                        return False
                if "doesNotMatch" in sub and re.fullmatch(sub["doesNotMatch"], target, re.S):
                    return False
                if "equalTo" in sub and str(target) != str(sub["equalTo"]):
                    return False
                if "contains" in sub and str(sub["contains"]) not in target:
                    return False
                if "matches" in sub and not re.fullmatch(sub["matches"], target, re.S):
                    return False
        elif "equalToJson" in p:
            try:
                exp = p["equalToJson"]
                exp = json.loads(exp) if isinstance(exp, str) else exp
                got = json.loads(body) if body else None
            except ValueError:
                return False
            if p.get("ignoreExtraElements") and isinstance(exp, dict) and isinstance(got, dict):
                if any(got.get(k) != v for k, v in exp.items()):
                    return False
            elif got != exp:
                return False
        elif "equalTo" in p:
            if body != p["equalTo"]:
                return False
        elif "contains" in p:
            if p["contains"] not in body:
                return False
        elif "matches" in p:
            if not re.fullmatch(p["matches"], body, re.S):
                return False
        elif "doesNotMatch" in p:
            if re.fullmatch(p["doesNotMatch"], body, re.S):
                return False
    return True


def matches(mapping: Dict[str, Any], method: str, path: str, query: Dict[str, List[str]],
            headers: Dict[str, str], body: str) -> bool:
    r = mapping["request"]
    m = (r.get("method") or "ANY").upper()
    if m not in ("ANY", method):
        return False
    full = path + (("?" + "&".join(f"{k}={v}" for k, vs in query.items() for v in vs)) if query else "")
    if "url" in r and r["url"] != full and r["url"] != path:
        return False
    if "urlPath" in r and r["urlPath"] != path:
        return False
    if "urlPattern" in r and not re.fullmatch(r["urlPattern"], full) and not re.fullmatch(r["urlPattern"], path):
        return False
    if "urlPathPattern" in r and not re.fullmatch(r["urlPathPattern"], path):
        return False
    for k, spec in (r.get("queryParameters") or {}).items():
        vals = query.get(k)
        if not _match_value(vals[0] if vals else None, spec):
            return False
    lower = {k.lower(): v for k, v in headers.items()}
    for k, spec in (r.get("headers") or {}).items():
        if not _match_value(lower.get(k.lower()), spec):
            return False
    if r.get("bodyPatterns") and not _match_body(body, r["bodyPatterns"]):
        return False
    return True


# ---------------------------------------------------------------------------- templating
def _java_fmt(fmt: str, now: _dt.datetime) -> str:
    table = [("yyyy", "%Y"), ("MM", "%m"), ("dd", "%d"), ("HH", "%H"), ("mm", "%M"), ("ss", "%S"), ("SSS", "{ms}")]
    out = fmt
    for j, p in table:
        out = out.replace(j, p)
    return now.strftime(out).replace("{ms}", f"{now.microsecond // 1000:03d}")


def _tmpl_value(expr: str, req: Dict[str, Any]) -> Any:
    expr = expr.strip()
    args = dict(re.findall(r"(\w+)=['\"]?([^'\"\s]+)['\"]?", expr))
    if expr.startswith("now"):
        now = _dt.datetime.now(_dt.timezone.utc)
        if "offset" in args:
            n, unit = args["offset"].split(" ") if " " in args["offset"] else (args["offset"], "days")
            now += _dt.timedelta(**{unit if unit.endswith("s") else unit + "s": int(n)})
        return _java_fmt(args.get("format", "yyyy-MM-dd'T'HH:mm:ss'Z'").replace("'", ""), now) if "format" in args \
            else now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if expr.startswith("randomValue"):
        length = int(args.get("length", 10))
        kind = args.get("type", "ALPHANUMERIC").upper()
        if kind == "UUID":
            return str(uuid.uuid4())
        alphabet = {"NUMERIC": string.digits, "ALPHABETIC": string.ascii_letters,
                    "HEXADECIMAL": "0123456789abcdef"}.get(kind, string.ascii_letters + string.digits)
        return "".join(random.choice(alphabet) for _ in range(length))
    m = re.match(r"jsonPath\s+request\.body\s+['\"](.+?)['\"]", expr)
    if m:
        try:
            data = json.loads(req["body"]) if req["body"] else None
            res = jsonpath.query(data, m.group(1))
            return res[0] if res else ""
        except ValueError:
            return ""
    m = re.match(r"request\.pathSegments\.\[(\d+)\]", expr)
    if m:
        segs = [s for s in req["path"].split("/") if s]
        i = int(m.group(1))
        return segs[i] if i < len(segs) else ""
    m = re.match(r"request\.(?:query|requestLine\.query)\.(\w+)", expr)
    if m:
        v = req["query"].get(m.group(1))
        return v[0] if v else ""
    m = re.match(r"request\.headers\.([\w-]+)", expr)
    if m:
        return {k.lower(): v for k, v in req["headers"].items()}.get(m.group(1).lower(), "")
    if expr in ("request.path", "request.url"):
        return req["path"]
    if expr == "request.method":
        return req["method"]
    if expr == "request.body":
        return req["body"]
    return "{{" + expr + "}}"


_TMPL = re.compile(r"\{\{\s*(.+?)\s*\}\}")


def render_template(obj: Any, req: Dict[str, Any]) -> Any:
    if isinstance(obj, str):
        whole = re.fullmatch(r"\{\{\s*(.+?)\s*\}\}", obj)
        if whole:
            return _tmpl_value(whole.group(1), req)
        return _TMPL.sub(lambda m: _to_str(_tmpl_value(m.group(1), req)), obj)
    if isinstance(obj, dict):
        return {k: render_template(v, req) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render_template(v, req) for v in obj]
    return obj


def _to_str(v: Any) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return "" if v is None else str(v)


# ---------------------------------------------------------------------------- stateful CRUD
class CrudStore:
    def __init__(self, path: Optional[str]):
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {}
        if self.path and self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def handle(self, method: str, path: str, query: Dict[str, List[str]], body: str) -> Optional[Tuple[int, Any]]:
        parts = [p for p in path.split("/") if p]
        if not parts or parts[0] not in self.data:
            return None
        res = parts[0]
        with self.lock:
            coll = self.data[res]
            if not isinstance(coll, list):
                if method == "GET" and len(parts) == 1:
                    return 200, coll
                return None
            if len(parts) == 1:
                if method == "GET":
                    def _same(val: Any, raw: str) -> bool:
                        return str(val) == raw or json.dumps(val) == raw
                    items = [i for i in coll if all(_same(i.get(k), v[0]) for k, v in query.items()
                                                    if k not in ("_page", "_limit", "_sort", "_order", "q"))]
                    if "q" in query:
                        items = [i for i in items if query["q"][0].lower() in json.dumps(i).lower()]
                    if "_sort" in query:
                        items.sort(key=lambda i: (i.get(query["_sort"][0]) is None, i.get(query["_sort"][0])),
                                   reverse=query.get("_order", ["asc"])[0] == "desc")
                    if "_limit" in query:
                        lim = int(query["_limit"][0])
                        page = int(query.get("_page", ["1"])[0])
                        items = items[(page - 1) * lim: page * lim]
                    return 200, items
                if method == "POST":
                    try:
                        item = json.loads(body or "{}")
                    except ValueError:
                        return 400, {"error": "Invalid JSON body"}
                    if not isinstance(item, dict):
                        return 400, {"error": "Body must be a JSON object"}
                    if "id" not in item:
                        ids = [i.get("id") for i in coll if isinstance(i.get("id"), int)]
                        item["id"] = (max(ids) + 1) if ids or not coll else str(uuid.uuid4())
                    coll.append(item)
                    self._save()
                    return 201, item
                return 405, {"error": "Method not allowed"}
            item_id = parts[1]
            idx = next((n for n, i in enumerate(coll) if str(i.get("id")) == item_id), None)
            if idx is None:
                return 404, {"error": f"{res} {item_id} not found"}
            if method == "GET":
                return 200, coll[idx]
            if method in ("PUT", "PATCH"):
                try:
                    upd = json.loads(body or "{}")
                except ValueError:
                    return 400, {"error": "Invalid JSON body"}
                if method == "PUT":
                    upd["id"] = coll[idx]["id"]
                    coll[idx] = upd
                else:
                    coll[idx].update(upd)
                self._save()
                return 200, coll[idx]
            if method == "DELETE":
                coll.pop(idx)
                self._save()
                return 204, None
            return 405, {"error": "Method not allowed"}

    def _save(self) -> None:
        pass  # in-memory by design; the db file is a seed and is never modified


# ---------------------------------------------------------------------------- server
class MockState:
    def __init__(self, mappings: List[Dict[str, Any]], store: Optional[CrudStore], cors: bool, latency_ms: int,
                 verbose: bool, record_limit: int = 1000):
        self.mappings = mappings
        self.store = store
        self.cors = cors
        self.latency_ms = latency_ms
        self.verbose = verbose
        self.requests: List[Dict[str, Any]] = []
        self.record_limit = record_limit
        self.lock = threading.Lock()

    def find(self, method, path, query, headers, body) -> Optional[Dict[str, Any]]:
        candidates = [m for m in self.mappings if matches(m, method, path, query, headers, body)]
        if not candidates:
            return None
        # WireMock semantics: lowest priority number wins; among equals, the most recently added wins.
        return sorted(candidates, key=lambda m: (m.get("priority", 5), -m["_order"]))[0]


def make_handler(state: MockState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TestoriaMock/2.0"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # quiet by default
            if state.verbose:
                super().log_message(fmt, *args)

        def _send(self, status: int, body: Any = None, headers: Optional[Dict[str, str]] = None):
            payload = b""
            hdrs = dict(headers or {})
            if body is not None:
                if isinstance(body, (dict, list, int, float, bool)):
                    payload = json.dumps(body).encode("utf-8")
                    hdrs.setdefault("Content-Type", "application/json")
                elif isinstance(body, bytes):
                    payload = body
                else:
                    payload = str(body).encode("utf-8")
            if state.cors:
                hdrs.setdefault("Access-Control-Allow-Origin", "*")
                hdrs.setdefault("Access-Control-Allow-Headers", "*")
                hdrs.setdefault("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD")
            self.send_response(status)
            for k, v in hdrs.items():
                if k.lower() != "content-length":
                    self.send_header(k, str(v))
            self.send_header("Content-Length", str(len(payload)) if status not in (204, 304) else "0")
            self.end_headers()
            if payload and self.command != "HEAD" and status not in (204, 304):
                self.wfile.write(payload)

        def _handle(self):
            split = urlsplit(self.path)
            path, query = split.path, parse_qs(split.query, keep_blank_values=True)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
            method = self.command.upper()
            headers = dict(self.headers.items())

            if path.startswith("/__admin"):
                return self._admin(method, path, body)
            if method == "OPTIONS" and state.cors:
                return self._send(204)

            entry = {"method": method, "path": self.path, "headers": headers, "body": body,
                     "time": _dt.datetime.now(_dt.timezone.utc).isoformat(), "matched": None}
            if state.latency_ms:
                time.sleep(state.latency_ms / 1000.0)

            mapping = state.find(method, path, query, headers, body)
            if mapping:
                entry["matched"] = mapping.get("id")
                self._record(entry)
                return self._respond(mapping, {"method": method, "path": path, "query": query,
                                               "headers": headers, "body": body})
            if state.store:
                res = state.store.handle(method, path, query, body)
                if res is not None:
                    entry["matched"] = "crud"
                    self._record(entry)
                    return self._send(res[0], res[1])
            self._record(entry)
            near = [f"{m['request'].get('method', 'ANY')} {m['request'].get('url') or m['request'].get('urlPath') or m['request'].get('urlPattern') or m['request'].get('urlPathPattern')}"
                    for m in state.mappings if path.split("/")[1:2] == str(m["request"].get("url") or m["request"].get("urlPath") or m["request"].get("urlPattern") or m["request"].get("urlPathPattern") or "").split("/")[1:2]][:5]
            self._send(404, {"error": "No mock mapping matched", "method": method, "path": self.path, "closest": near})

        def _record(self, entry):
            with state.lock:
                state.requests.append(entry)
                if len(state.requests) > state.record_limit:
                    del state.requests[0]

        def _respond(self, mapping, req):
            r = mapping["response"]
            if r.get("fixedDelayMilliseconds"):
                time.sleep(float(r["fixedDelayMilliseconds"]) / 1000.0)
            if r.get("fault"):
                self.close_connection = True
                return
            templ = "response-template" in (r.get("transformers") or []) or mapping.get("templated", True)
            headers = r.get("headers") or {}
            if "jsonBody" in r:
                body: Any = render_template(r["jsonBody"], req) if templ else r["jsonBody"]
                headers = {"Content-Type": "application/json", **headers}
            elif "body" in r:
                body = render_template(r["body"], req) if templ else r["body"]
            elif "bodyFileName" in r:
                f = Path(mapping.get("_dir", ".")).parent / "__files" / r["bodyFileName"]
                body = f.read_bytes() if f.exists() else b""
            else:
                body = None
            self._send(int(r.get("status", 200)), body, headers)

        def _admin(self, method, path, body):
            if path == "/__admin/health":
                return self._send(200, {"status": "ok", "mappings": len(state.mappings)})
            if path == "/__admin/mappings":
                if method == "GET":
                    return self._send(200, {"mappings": [{k: v for k, v in m.items() if not k.startswith("_")}
                                                         for m in state.mappings], "total": len(state.mappings)})
                if method == "POST":
                    try:
                        m = _normalize(json.loads(body), "admin", len(state.mappings) + 100000)
                    except ValueError:
                        m = None
                    if not m:
                        return self._send(400, {"error": "Invalid mapping"})
                    with state.lock:
                        state.mappings.append(m)
                    return self._send(201, {k: v for k, v in m.items() if not k.startswith("_")})
                if method == "DELETE":
                    with state.lock:
                        state.mappings.clear()
                    return self._send(200, {"status": "cleared"})
            if path == "/__admin/requests":
                if method == "DELETE":
                    with state.lock:
                        state.requests.clear()
                    return self._send(200, {"status": "cleared"})
                return self._send(200, {"requests": state.requests, "total": len(state.requests)})
            if path == "/__admin/requests/unmatched":
                return self._send(200, {"requests": [r for r in state.requests if not r["matched"]]})
            if path == "/__admin/reset" and method == "POST":
                with state.lock:
                    state.requests.clear()
                return self._send(200, {"status": "reset"})
            return self._send(404, {"error": "Unknown admin endpoint"})

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _handle

    return Handler


def create_server(host: str, port: int, mapping_paths: List[str], db: Optional[str] = None, cors: bool = True,
                  latency_ms: int = 0, verbose: bool = False) -> Tuple[ThreadingHTTPServer, MockState]:
    mappings = load_mappings(mapping_paths)
    store = CrudStore(db) if db else None
    state = MockState(mappings, store, cors, latency_ms, verbose)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    server.daemon_threads = True
    return server, state


def start_background(host: str, port: int, mapping_paths: List[str], **kw) -> Tuple[ThreadingHTTPServer, MockState]:
    server, state = create_server(host, port, mapping_paths, **kw)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, state
