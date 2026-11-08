"""Declarative test runner.

A spec file looks like:

    name: Users API
    base_url: "{{ env.API_URL | default('http://localhost:8080') }}"
    variables: {user_name: Ada}
    setup: [ ...steps... ]
    tests:
      - name: create user
        tags: [smoke]
        request: {method: POST, url: /users, json: {name: "{{ user_name }}"}}
        expect: {status: 201, json: {"$.name": "{{ user_name }}"}}
        extract: {user_id: "$.id"}
    teardown: [ ...steps... ]
"""

from __future__ import annotations

import concurrent.futures as cf
import copy
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from testoria import assertions, http, jsonpath, loader, templating


@dataclass
class StepResult:
    name: str
    file: str
    suite: str
    status: str = "passed"          # passed | failed | skipped | error
    duration_ms: float = 0.0
    failures: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    attempts: int = 1
    request: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)
    skip_reason: str = ""


@dataclass
class RunOptions:
    env: Optional[str] = None
    base_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    grep: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    workers: int = 1
    retries: int = 0
    timeout: float = 30.0
    fail_fast: bool = False
    verify_tls: bool = True
    verbose: bool = False
    dry_run: bool = False


class Runner:
    def __init__(self, config: Dict[str, Any], options: RunOptions, printer=None):
        self.config = config or {}
        self.opts = options
        self.printer = printer
        self._stop = False

    # ------------------------------------------------------------------ context
    def _base_context(self) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {}
        ctx.update(self.config.get("variables") or {})
        env_name = self.opts.env or os.environ.get("TESTORIA_ENV") or self.config.get("default_env")
        envs = self.config.get("environments") or {}
        if env_name:
            if env_name not in envs:
                raise loader.LoadError(f"Environment '{env_name}' not defined in testoria.yaml (have: {', '.join(envs) or 'none'})")
            env_cfg = envs[env_name] or {}
            ctx.update(env_cfg.get("variables") or {})
            for k, v in env_cfg.items():
                if k != "variables":
                    ctx.setdefault(k, v)
        ctx["env_name"] = env_name or "default"
        return ctx

    def _settings(self, spec: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        base_url = self.opts.base_url or os.environ.get("TESTORIA_BASE_URL") or spec.get("base_url") \
            or ctx.get("base_url") or self.config.get("base_url") or ""
        headers = {}
        headers.update(self.config.get("headers") or {})
        headers.update(ctx.get("headers") or {})
        headers.update(spec.get("headers") or {})
        auth = spec.get("auth", ctx.get("auth", self.config.get("auth")))
        return {
            "base_url": templating.render(base_url, ctx),
            "headers": headers,
            "auth": auth,
            "timeout": float(spec.get("timeout", ctx.get("timeout", self.config.get("timeout", self.opts.timeout)))),
        }

    # ------------------------------------------------------------------ selection
    def _selected(self, test: Dict[str, Any], suite_tags: List[str]) -> Optional[str]:
        tags = set(suite_tags) | set(test.get("tags") or [])
        if test.get("skip"):
            return str(test.get("skip")) if isinstance(test.get("skip"), str) else "marked skip"
        if self.opts.tags and not (tags & set(self.opts.tags)):
            return None
        if self.opts.exclude_tags and (tags & set(self.opts.exclude_tags)):
            return None
        if self.opts.grep and not re.search(self.opts.grep, test.get("name", ""), re.I):
            return None
        return ""

    # ------------------------------------------------------------------ execution
    def run_files(self, files: List[Path]) -> List[StepResult]:
        specs = []
        for f in files:
            data = loader.load_file(f)
            if not isinstance(data, dict) or "tests" not in data:
                continue
            specs.append((f, data))
        results: List[StepResult] = []
        workers = max(1, self.opts.workers)
        if workers == 1 or len(specs) <= 1:
            for f, spec in specs:
                results.extend(self.run_spec(f, spec))
                if self._stop:
                    break
        else:
            with cf.ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(self.run_spec, f, spec) for f, spec in specs]
                for fut in futs:
                    results.extend(fut.result())
        return results

    def run_spec(self, file: Path, spec: Dict[str, Any]) -> List[StepResult]:
        suite = spec.get("name") or file.stem
        results: List[StepResult] = []
        try:
            ctx = self._base_context()
        except loader.LoadError as e:
            r = StepResult(name="(configuration)", file=str(file), suite=suite, status="error", failures=[str(e)])
            self._emit(r)
            return [r]
        ctx.update(templating.render(spec.get("variables") or {}, ctx))
        ctx.update(self.opts.variables)
        settings = self._settings(spec, ctx)
        ctx["base_url"] = settings["base_url"]
        suite_tags = list(spec.get("tags") or [])

        for i, step in enumerate(spec.get("setup") or []):
            r = self._run_step(step, ctx, settings, file, suite, step.get("name") or f"setup #{i + 1}")
            if r.status != "passed":
                r.name = f"[setup] {r.name}"
                results.append(r)
                self._emit(r)
                for t in spec.get("tests") or []:
                    sr = StepResult(name=t.get("name", "unnamed"), file=str(file), suite=suite,
                                    status="skipped", skip_reason="setup failed", tags=t.get("tags") or [])
                    results.append(sr)
                    self._emit(sr)
                return results

        tests = spec.get("tests") or []
        for idx, test in enumerate(tests):
            if self._stop:
                break
            name = test.get("name") or f"test #{idx + 1}"
            sel = self._selected(test, suite_tags)
            if sel is None:
                continue
            if sel:
                r = StepResult(name=name, file=str(file), suite=suite, status="skipped", skip_reason=sel,
                               tags=test.get("tags") or [])
                results.append(r)
                self._emit(r)
                continue
            for iteration, row in enumerate(self._data_rows(test, ctx, file)):
                local = dict(ctx)
                label = name
                if row is not None:
                    local.update(row)
                    label = templating.render(f"{name} [{iteration + 1}]" if "{{" not in name else name, local)
                if test.get("skip_if") and _truthy(templating.render(test["skip_if"], local)):
                    r = StepResult(name=label, file=str(file), suite=suite, status="skipped", skip_reason="skip_if")
                else:
                    r = self._run_step(test, local, settings, file, suite, label, suite_tags)
                    for k, v in local.items():
                        if k not in ctx or ctx[k] != v:
                            if row is None or k not in row:
                                ctx[k] = v
                results.append(r)
                self._emit(r)
                if r.status in ("failed", "error") and self.opts.fail_fast:
                    self._stop = True
                    break

        for i, step in enumerate(spec.get("teardown") or []):
            r = self._run_step(step, ctx, settings, file, suite, step.get("name") or f"teardown #{i + 1}")
            if r.status != "passed":
                r.name = f"[teardown] {r.name}"
                results.append(r)
                self._emit(r)
        return results

    def _data_rows(self, test: Dict[str, Any], ctx: Dict[str, Any], file: Path):
        data = test.get("data") or test.get("parametrize")
        if not data:
            yield None
            return
        if isinstance(data, str):
            path = (file.parent / data)
            if path.suffix.lower() == ".csv":
                import csv
                with open(path, newline="", encoding="utf-8") as fh:
                    rows = [{k: templating._coerce(v) for k, v in row.items()} for row in csv.DictReader(fh)]
            else:
                rows = loader.load_file(path)
        else:
            rows = data
        for row in rows:
            yield row

    def _run_step(self, step: Dict[str, Any], ctx: Dict[str, Any], settings: Dict[str, Any],
                  file: Path, suite: str, name: str, suite_tags: Optional[List[str]] = None) -> StepResult:
        result = StepResult(name=name, file=str(file), suite=suite,
                            tags=list(suite_tags or []) + list(step.get("tags") or []))
        retries = int(step.get("retries", self.opts.retries))
        retry_delay = float(step.get("retry_delay_ms", 500)) / 1000.0
        start = time.perf_counter()
        attempt = 0
        while True:
            attempt += 1
            failures, req_info, resp_info = self._attempt(step, ctx, settings)
            if not failures or attempt > retries:
                break
            time.sleep(retry_delay)
        result.attempts = attempt
        result.duration_ms = (time.perf_counter() - start) * 1000
        result.request, result.response = req_info, resp_info
        if failures:
            result.status = "error" if failures and failures[0].startswith("error:") else "failed"
            result.failures = failures
        if step.get("delay_ms"):
            time.sleep(float(step["delay_ms"]) / 1000.0)
        return result

    def _attempt(self, step: Dict[str, Any], ctx: Dict[str, Any], settings: Dict[str, Any]):
        req_info: Dict[str, Any] = {}
        resp_info: Dict[str, Any] = {}
        try:
            if "set" in step:
                ctx.update(templating.render(step["set"], ctx))
            if "request" not in step:
                return [], req_info, resp_info
            req = templating.render(copy.deepcopy(step["request"]), ctx)
            method = str(req.get("method", "GET")).upper()
            url = http.build_url(settings["base_url"], str(req.get("url") or req.get("path") or "/"), req.get("params") or req.get("query"))
            headers = templating.render(dict(settings["headers"]), ctx)
            headers.update(req.get("headers") or {})
            headers = {k: str(v) for k, v in headers.items() if v is not None}
            auth = templating.render(req.get("auth", settings["auth"]), ctx) if (req.get("auth", settings["auth"])) else None
            req_info = {"method": method, "url": url, "headers": http.mask_headers(headers)}
            if "json" in req:
                req_info["body"] = req["json"]
            elif "body" in req:
                req_info["body"] = req["body"]
            if self.opts.dry_run:
                return [], req_info, {"status": "dry-run"}
            resp = http.request(
                method, url, headers=headers, json_body=req.get("json"), body=req.get("body"), form=req.get("form"),
                timeout=float(req.get("timeout", settings["timeout"])), verify_tls=self.opts.verify_tls and req.get("verify_tls", True),
                follow_redirects=req.get("follow_redirects", True), auth=auth,
            )
            resp_info = {
                "status": resp.status, "elapsed_ms": round(resp.elapsed_ms, 2),
                "headers": http.mask_headers(resp.headers), "body": resp.text[:4000],
            }
            if resp.error:
                resp_info["error"] = resp.error
            ctx["response"] = {"status": resp.status, "headers": resp.headers, "body": resp.json() if resp.is_json() else resp.text,
                               "elapsed_ms": resp.elapsed_ms}
            expect = templating.render(step.get("expect") or {"status": "2xx"}, ctx)
            failures = assertions.evaluate_expectations(resp, expect)
            for var, path in (step.get("extract") or {}).items():
                value = _extract(resp, path)
                if value is _NOTFOUND:
                    failures.append(f"extract {var}: '{path}' not found in response")
                else:
                    ctx[var] = value
            return failures, req_info, resp_info
        except Exception as e:  # noqa: BLE001 - report any step error as a test error
            return [f"error: {type(e).__name__}: {e}"], req_info, resp_info

    def _emit(self, r: StepResult) -> None:
        if self.printer:
            self.printer(r)


_NOTFOUND = object()


def _extract(resp: http.Response, path: Any) -> Any:
    if isinstance(path, dict):
        if "header" in path:
            v = resp.header(path["header"])
            return _NOTFOUND if v is None else v
        if "regex" in path:
            m = re.search(path["regex"], resp.text)
            return _NOTFOUND if not m else (m.group(1) if m.groups() else m.group(0))
        if path.get("from") == "status":
            return resp.status
        path = path.get("json", "$")
    p = str(path)
    if p == "status":
        return resp.status
    if p.startswith("header:"):
        v = resp.header(p[7:].strip())
        return _NOTFOUND if v is None else v
    data = resp.json()
    if not p.startswith("$"):
        p = "$." + p
    matches = jsonpath.query(data, p)
    if not matches:
        return _NOTFOUND
    multi = any(t in p for t in ("[*]", ".*", ".."))
    return matches if multi else matches[0]


def _truthy(v: Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() not in ("", "0", "false", "no", "none", "null")
    return bool(v)
