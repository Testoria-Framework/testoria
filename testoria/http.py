"""Minimal HTTP client built on the standard library (no third-party deps)."""

from __future__ import annotations

import base64
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "api-key"}


class Response:
    def __init__(self, status: int, headers: Dict[str, str], body: bytes, elapsed_ms: float,
                 url: str, method: str, error: Optional[str] = None):
        self.status = status
        self.headers = headers
        self.body = body
        self.elapsed_ms = elapsed_ms
        self.url = url
        self.method = method
        self.error = error
        self._json: Any = None
        self._json_parsed = False

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        lname = name.lower()
        for k, v in self.headers.items():
            if k.lower() == lname:
                return v
        return default

    def json(self) -> Any:
        if not self._json_parsed:
            self._json_parsed = True
            try:
                self._json = json.loads(self.text) if self.body else None
            except ValueError:
                self._json = None
        return self._json

    def is_json(self) -> bool:
        if not self.body:
            return False
        try:
            json.loads(self.text)
            return True
        except ValueError:
            return False


def mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: ("****" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()}


def build_url(base_url: str, url: str, params: Optional[Dict[str, Any]] = None) -> str:
    if url.startswith(("http://", "https://")):
        full = url
    else:
        full = (base_url or "").rstrip("/") + "/" + url.lstrip("/") if base_url else url
    if params:
        flat = []
        for k, v in params.items():
            if isinstance(v, (list, tuple)):
                flat.extend((k, str(i)) for i in v)
            else:
                flat.append((k, "" if v is None else str(v)))
        sep = "&" if "?" in full else "?"
        full = full + sep + urllib.parse.urlencode(flat)
    return full


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def request(method: str, url: str, headers: Optional[Dict[str, str]] = None, body: Any = None,
            json_body: Any = None, form: Optional[Dict[str, Any]] = None, timeout: float = 30.0,
            verify_tls: bool = True, follow_redirects: bool = True,
            auth: Optional[Dict[str, Any]] = None) -> Response:
    headers = dict(headers or {})
    data: Optional[bytes] = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        if not any(k.lower() == "content-type" for k in headers):
            headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form, doseq=True).encode("utf-8")
        if not any(k.lower() == "content-type" for k in headers):
            headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = body if isinstance(body, bytes) else str(body).encode("utf-8")

    apply_auth(headers, auth)
    if not any(k.lower() == "user-agent" for k in headers):
        from testoria import __version__
        headers["User-Agent"] = f"testoria/{__version__}"

    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    handlers = []
    if not verify_tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    if not follow_redirects:
        handlers.append(_NoRedirect())
    opener = urllib.request.build_opener(*handlers)

    start = time.perf_counter()
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
            resp_headers = dict(resp.headers.items())
    except urllib.error.HTTPError as e:
        raw = e.read() if e.fp else b""
        status = e.code
        resp_headers = dict(e.headers.items()) if e.headers else {}
    except (urllib.error.URLError, OSError, ValueError) as e:
        elapsed = (time.perf_counter() - start) * 1000
        reason = getattr(e, "reason", e)
        return Response(0, {}, b"", elapsed, url, method.upper(), error=f"{type(e).__name__}: {reason}")
    elapsed = (time.perf_counter() - start) * 1000
    return Response(status, resp_headers, raw, elapsed, url, method.upper())


def apply_auth(headers: Dict[str, str], auth: Optional[Dict[str, Any]]) -> None:
    if not auth:
        return
    kind = str(auth.get("type", "")).lower()
    if kind == "bearer" and auth.get("token"):
        headers["Authorization"] = f"Bearer {auth['token']}"
    elif kind == "basic":
        raw = f"{auth.get('username', '')}:{auth.get('password', '')}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    elif kind in ("apikey", "api_key", "api-key"):
        headers[auth.get("header", "X-API-Key")] = str(auth.get("key") or auth.get("value") or "")
