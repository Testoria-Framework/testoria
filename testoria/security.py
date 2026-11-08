"""Passive and light active API security checks.

Only run this against systems you own or are authorised to test.
Active probes send a handful of harmless payloads (no exploitation, no brute force).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from testoria import http

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}


@dataclass
class Finding:
    check: str
    severity: str
    message: str
    url: str
    evidence: str = ""


SQL_ERRORS = re.compile(r"(SQL syntax|mysql_fetch|ORA-\d{5}|PostgreSQL.*ERROR|SQLite.*error|SQLSTATE|"
                        r"unclosed quotation mark|syntax error at or near)", re.I)
STACK_TRACES = re.compile(r"(Traceback \(most recent call last\)|at [\w$.]+\([\w]+\.java:\d+\)|"
                          r"System\.\w+Exception|node_modules/|\.php on line \d+)", re.I)
XSS_PROBE = "<testoria-xss>\"'"
SQLI_PROBE = "'\"`;--"
TRAVERSAL_PROBE = "../../../../etc/passwd"


def scan(url: str, headers: Optional[Dict[str, str]] = None, active: bool = False, timeout: float = 15.0,
         verify_tls: bool = True, auth_header: Optional[str] = None) -> List[Finding]:
    findings: List[Finding] = []
    hdrs = dict(headers or {})
    resp = http.request("GET", url, headers=hdrs, timeout=timeout, verify_tls=verify_tls)
    if resp.error:
        return [Finding("connectivity", "high", f"Target unreachable: {resp.error}", url)]

    parts = urlsplit(url)
    is_https = parts.scheme == "https"
    if not is_https and parts.hostname not in ("localhost", "127.0.0.1", "::1"):
        findings.append(Finding("transport", "high", "API served over plain HTTP", url))
    if is_https and not resp.header("Strict-Transport-Security"):
        findings.append(Finding("hsts", "medium", "Missing Strict-Transport-Security header", url))

    for h, sev, msg in [
        ("X-Content-Type-Options", "low", "Missing X-Content-Type-Options: nosniff"),
        ("Cache-Control", "info", "No Cache-Control header (sensitive responses may be cached)"),
    ]:
        if not resp.header(h):
            findings.append(Finding("headers", sev, msg, url))
    ct = (resp.header("Content-Type") or "").lower()
    if "text/html" in ct:
        if not resp.header("Content-Security-Policy"):
            findings.append(Finding("headers", "low", "HTML response without Content-Security-Policy", url))
        if not resp.header("X-Frame-Options") and "frame-ancestors" not in (resp.header("Content-Security-Policy") or ""):
            findings.append(Finding("headers", "low", "HTML response without clickjacking protection", url))

    for h in ("Server", "X-Powered-By", "X-AspNet-Version", "X-AspNetMvc-Version"):
        v = resp.header(h)
        if v and re.search(r"\d", v):
            findings.append(Finding("disclosure", "low", f"{h} header discloses version", url, v))

    acao = resp.header("Access-Control-Allow-Origin")
    acac = (resp.header("Access-Control-Allow-Credentials") or "").lower() == "true"
    if acao == "*" and acac:
        findings.append(Finding("cors", "high", "CORS allows any origin with credentials", url))
    probe = http.request("GET", url, headers={**hdrs, "Origin": "https://evil.testoria.invalid"}, timeout=timeout,
                         verify_tls=verify_tls)
    if probe.header("Access-Control-Allow-Origin") == "https://evil.testoria.invalid":
        sev = "high" if (probe.header("Access-Control-Allow-Credentials") or "").lower() == "true" else "medium"
        findings.append(Finding("cors", sev, "CORS reflects arbitrary Origin", url))

    for c in [c for k, c in resp.headers.items() if k.lower() == "set-cookie"]:
        low = c.lower()
        name = c.split("=", 1)[0]
        if "httponly" not in low:
            findings.append(Finding("cookies", "medium", f"Cookie '{name}' missing HttpOnly", url))
        if is_https and "secure" not in low:
            findings.append(Finding("cookies", "medium", f"Cookie '{name}' missing Secure", url))
        if "samesite" not in low:
            findings.append(Finding("cookies", "low", f"Cookie '{name}' missing SameSite", url))

    if STACK_TRACES.search(resp.text):
        findings.append(Finding("disclosure", "medium", "Response contains a stack trace", url))

    trace = http.request("TRACE", url, headers=hdrs, timeout=timeout, verify_tls=verify_tls)
    if trace.status == 200 and "TRACE" in trace.text.upper():
        findings.append(Finding("methods", "medium", "HTTP TRACE is enabled", url))

    if auth_header:
        stripped = {k: v for k, v in hdrs.items() if k.lower() not in ("authorization", auth_header.lower())}
        anon = http.request("GET", url, headers=stripped, timeout=timeout, verify_tls=verify_tls)
        if anon.status < 400 and resp.status < 400:
            findings.append(Finding("auth", "high", "Endpoint returns success without credentials", url,
                                    f"HTTP {anon.status}"))
        bogus = http.request("GET", url, headers={**stripped, "Authorization": "Bearer invalid.testoria.token"},
                             timeout=timeout, verify_tls=verify_tls)
        if bogus.status < 400 and resp.status < 400:
            findings.append(Finding("auth", "high", "Endpoint accepts an invalid bearer token", url,
                                    f"HTTP {bogus.status}"))

    if active:
        sep = "&" if "?" in url else "?"
        for label, payload in (("sqli", SQLI_PROBE), ("xss", XSS_PROBE), ("traversal", TRAVERSAL_PROBE)):
            r = http.request("GET", f"{url}{sep}q={http_quote(payload)}&id={http_quote(payload)}", headers=hdrs,
                             timeout=timeout, verify_tls=verify_tls)
            if r.error:
                continue
            if label == "sqli" and SQL_ERRORS.search(r.text):
                findings.append(Finding("injection", "high", "Database error leaked for SQL metacharacters", r.url,
                                        SQL_ERRORS.search(r.text).group(0)))
            if label == "xss" and XSS_PROBE in r.text and "html" in (r.header("Content-Type") or "").lower():
                findings.append(Finding("injection", "high", "Input reflected unescaped in HTML response", r.url))
            if label == "traversal" and "root:x:0:0" in r.text:
                findings.append(Finding("injection", "high", "Path traversal returned /etc/passwd", r.url))
            if r.status >= 500:
                findings.append(Finding("robustness", "medium", f"Server error ({r.status}) on {label} probe", r.url))
            if STACK_TRACES.search(r.text):
                findings.append(Finding("disclosure", "medium", f"Stack trace on {label} probe", r.url))
        big = http.request("POST", url, headers={**hdrs, "Content-Type": "application/json"}, body="{" * 2000,
                           timeout=timeout, verify_tls=verify_tls)
        if big.status >= 500:
            findings.append(Finding("robustness", "medium", f"Malformed JSON causes HTTP {big.status}", url))
    return findings


def http_quote(s: str) -> str:
    from urllib.parse import quote
    return quote(s, safe="")


def worst(findings: List[Finding]) -> str:
    if not findings:
        return "none"
    return max(findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 0)).severity
