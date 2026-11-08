"""Command-line interface: testoria <command> [options]."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from testoria import __version__, loader
from testoria.reporters.console import ConsolePrinter, c, print_summary


def _kv(items: Optional[List[str]]) -> Dict[str, Any]:
    from testoria.templating import _coerce
    out: Dict[str, Any] = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--var expects KEY=VALUE, got '{it}'")
        k, v = it.split("=", 1)
        out[k.strip()] = _coerce(v)
    return out


def _headers(items: Optional[List[str]]) -> Dict[str, str]:
    out = {}
    for it in items or []:
        if ":" not in it:
            raise SystemExit(f"--header expects 'Name: value', got '{it}'")
        k, v = it.split(":", 1)
        out[k.strip()] = v.strip()
    return out


# ---------------------------------------------------------------------------- run
def cmd_run(a: argparse.Namespace) -> int:
    from testoria.reporters import files as rep
    from testoria.runner import RunOptions, Runner

    cfg = loader.load_project_config(a.config)
    root = Path(cfg["_root"])
    paths = a.paths or [str(root / p) for p in (cfg.get("tests") or ["tests/api"])]
    try:
        spec_files = loader.collect_spec_files(paths)
    except loader.LoadError as e:
        print(c(str(e), "failed"), file=sys.stderr)
        return 2
    if not spec_files:
        print(c("No spec files found. Create one with: testoria init", "skipped"))
        return 2 if not a.allow_empty else 0

    mock_server = None
    mock_cfg = cfg.get("mock") or {}
    if a.mock or (mock_cfg.get("auto_start") and not a.no_mock):
        from testoria import mock
        port = a.mock_port or int(mock_cfg.get("port", 8080))
        maps = [str(root / p) for p in (mock_cfg.get("mappings") or ["mocks"])]
        db = str(root / mock_cfg["db"]) if mock_cfg.get("db") else None
        try:
            mock_server, state = mock.start_background("127.0.0.1", port, maps, db=db)
        except OSError as e:
            print(c(f"Could not start mock server on port {port}: {e}", "failed"), file=sys.stderr)
            return 2
        os.environ.setdefault("TESTORIA_MOCK_URL", f"http://127.0.0.1:{port}")
        print(c(f"Mock server on http://127.0.0.1:{port} ({len(state.mappings)} mappings)", "cyan"))
        if not a.base_url and not os.environ.get("TESTORIA_BASE_URL"):
            a.base_url = f"http://127.0.0.1:{port}"

    opts = RunOptions(env=a.env, base_url=a.base_url, tags=a.tag or [], exclude_tags=a.exclude_tag or [],
                      grep=a.grep, variables=_kv(a.var), workers=a.workers, retries=a.retries,
                      timeout=a.timeout, fail_fast=a.fail_fast, verify_tls=not a.insecure, verbose=a.verbose,
                      dry_run=a.dry_run)
    printer = ConsolePrinter(verbose=a.verbose, quiet=a.quiet)
    print(c(f"Testoria {__version__}", "bold") + c(f" · {len(spec_files)} spec file(s) · env={a.env or cfg.get('default_env') or 'default'}", "dim"))
    start = time.perf_counter()
    try:
        results = Runner(cfg, opts, printer).run_files(spec_files)
    except loader.LoadError as e:
        print(c(str(e), "failed"), file=sys.stderr)
        return 2
    finally:
        if mock_server:
            mock_server.shutdown()
    elapsed = time.perf_counter() - start
    print_summary(results, elapsed)

    meta = {"env": a.env or cfg.get("default_env") or "default", "files": [str(f) for f in spec_files]}
    out = Path(a.output or cfg.get("reports_dir") or (root / "reports"))
    formats = set((a.report or ",".join(cfg.get("reports") or ["html", "junit", "json"])).split(","))
    written = []
    if "junit" in formats:
        written.append(rep.write_junit(results, out / "junit.xml"))
    if "json" in formats:
        written.append(rep.write_json(results, out / "results.json", elapsed, meta))
    if "html" in formats:
        html_path = rep.write_html(results, out / "report.html", elapsed, meta)
        written.append(html_path)
        if a.open:
            webbrowser.open(html_path.resolve().as_uri())
    if written and not a.quiet:
        print(c("Reports: " + ", ".join(str(p) for p in written), "dim"))
    failed = any(r.status in ("failed", "error") for r in results)
    return 1 if failed else 0


def cmd_watch(a: argparse.Namespace) -> int:
    cfg = loader.load_project_config(a.config)
    root = Path(cfg["_root"])
    watch_paths = [Path(p) for p in (a.paths or [str(root / p) for p in (cfg.get("tests") or ["tests/api"])])]
    watch_paths.append(root)

    def snapshot():
        state = {}
        for p in watch_paths:
            it = p.rglob("*") if p.is_dir() else [p]
            for f in it:
                if f.is_file() and f.suffix in (".yaml", ".yml", ".json", ".csv") and "reports" not in f.parts \
                        and "node_modules" not in f.parts and ".git" not in f.parts:
                    try:
                        state[str(f)] = f.stat().st_mtime
                    except OSError:
                        pass
        return state

    print(c("Watching for changes (Ctrl+C to stop)…", "cyan"))
    last = None
    try:
        while True:
            snap = snapshot()
            if snap != last:
                last = snap
                os.system("cls" if os.name == "nt" else "clear") if not a.no_clear else None
                cmd_run(a)
                print(c("\nWaiting for changes…", "dim"))
            time.sleep(1.0)
    except KeyboardInterrupt:
        return 0


# ---------------------------------------------------------------------------- mock
def cmd_mock(a: argparse.Namespace) -> int:
    from testoria import mock
    cfg = loader.load_project_config(a.config)
    root = Path(cfg["_root"])
    mcfg = cfg.get("mock") or {}
    maps = a.mappings or [str(root / p) for p in (mcfg.get("mappings") or ["mocks"])]
    db = a.db or (str(root / mcfg["db"]) if mcfg.get("db") else None)
    port = a.port or int(mcfg.get("port", 8080))
    try:
        server, state = mock.create_server(a.host, port, maps, db=db, cors=not a.no_cors, latency_ms=a.latency,
                                           verbose=a.verbose)
    except (OSError, ValueError) as e:
        print(c(f"Cannot start mock server: {e}", "failed"), file=sys.stderr)
        return 2
    print(c(f"Testoria mock server listening on http://{a.host}:{port}", "bold"))
    print(c(f"  {len(state.mappings)} mappings from: {', '.join(maps)}", "dim"))
    if db:
        print(c(f"  CRUD resources from {db}: {', '.join(state.store.data.keys())}", "dim"))
    print(c("  Admin: /__admin/health  /__admin/mappings  /__admin/requests", "dim"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock server")
    finally:
        server.server_close()
    return 0


# ---------------------------------------------------------------------------- demo api
def cmd_demo_api(a: argparse.Namespace) -> int:
    from testoria import demo_api
    try:
        server, _ = demo_api.create_server(a.host, a.port, rate_limit=a.rate_limit, verbose=a.verbose)
    except OSError as e:
        print(c(f"Cannot start demo API: {e}", "failed"), file=sys.stderr)
        return 2
    print(c(f"Testoria demo API on http://{a.host}:{server.server_address[1]}", "bold"))
    print(c("  public: /health /version /docs POST /auth/login · token for everything else: Bearer test_token", "dim"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping demo API")
    finally:
        server.server_close()
    return 0


# ---------------------------------------------------------------------------- load
def cmd_load(a: argparse.Namespace) -> int:
    from testoria import load
    body = None
    if a.data:
        body = json.loads(Path(a.data[1:]).read_text()) if a.data.startswith("@") else json.loads(a.data)
    print(c(f"Load test: {a.method} {a.url}", "bold") +
          c(f"  users={a.users} " + (f"requests={a.requests}" if a.requests else f"duration={a.duration}s"), "dim"))

    def tick(n, errs, t):
        if sys.stdout.isatty():
            sys.stdout.write(f"\r  {t:5.1f}s  {n} requests  {errs} errors  {n / t if t else 0:.1f} rps   ")
            sys.stdout.flush()

    res = load.run_load(a.url, a.method, users=a.users, duration_s=a.duration, requests_total=a.requests,
                        ramp_up_s=a.ramp_up, headers=_headers(a.header), body=body, timeout=a.timeout,
                        think_ms=a.think, verify_tls=not a.insecure, on_tick=tick)
    s = res.summary()
    if sys.stdout.isatty():
        print()
    lat = s["latency_ms"]
    print(f"  requests: {s['requests']}   rps: {s['rps']}   errors: {s['errors']} ({s['error_rate'] * 100:.2f}%)")
    print(f"  latency ms  min {lat['min']}  mean {lat['mean']}  p50 {lat['p50']}  p90 {lat['p90']}  "
          f"p95 {lat['p95']}  p99 {lat['p99']}  max {lat['max']}")
    print(f"  status codes: {s['status_codes']}")
    if s["error_samples"]:
        print(c(f"  sample errors: {s['error_samples']}", "failed"))
    thresholds = {k: v for k, v in {"p95": a.p95, "p99": a.p99, "mean": a.max_mean, "error_rate": a.max_error_rate,
                                    "rps_min": a.min_rps}.items() if v is not None}
    fails = load.check_thresholds(s, thresholds)
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps({**s, "thresholds": thresholds, "threshold_failures": fails}, indent=2))
        print(c(f"  saved {a.output}", "dim"))
    if fails:
        for f in fails:
            print(c(f"  ✘ threshold: {f}", "failed"))
        return 1
    if thresholds:
        print(c("  ✔ all thresholds met", "passed"))
    return 0


# ---------------------------------------------------------------------------- scan
def cmd_scan(a: argparse.Namespace) -> int:
    from testoria import security
    if not a.i_own_this:
        print(c("Only scan systems you own or are authorised to test.", "skipped"))
    order = security.SEVERITY_ORDER
    all_findings = []
    for url in a.urls:
        print(c(f"Scanning {url}" + (" (active probes)" if a.active else " (passive)"), "bold"))
        f = security.scan(url, headers=_headers(a.header), active=a.active, timeout=a.timeout,
                          verify_tls=not a.insecure, auth_header="Authorization" if a.check_auth else None)
        all_findings.extend(f)
        if not f:
            print(c("  ✔ no findings", "passed"))
        for x in sorted(f, key=lambda x: -order.get(x.severity, 0)):
            color = {"high": "failed", "medium": "error", "low": "skipped"}.get(x.severity, "dim")
            print(f"  {c(x.severity.upper().ljust(6), color)} {x.check:<11} {x.message}" + (c(f"  [{x.evidence}]", "dim") if x.evidence else ""))
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps([x.__dict__ for x in all_findings], indent=2))
    threshold = order[a.fail_on] if a.fail_on != "none" else 99
    return 1 if any(order.get(x.severity, 0) >= threshold for x in all_findings) else 0


# ---------------------------------------------------------------------------- import
def cmd_import(a: argparse.Namespace) -> int:
    from testoria.importers import openapi, postman
    src = a.source
    if src.startswith(("http://", "https://")):
        from testoria import http
        r = http.request("GET", src)
        if r.error or r.status >= 400:
            print(c(f"Cannot download {src}: {r.error or r.status}", "failed"), file=sys.stderr)
            return 2
        tmp = Path(".testoria-import" + (".json" if r.is_json() else ".yaml"))
        tmp.write_bytes(r.body)
        doc = loader.load_file(tmp)
        tmp.unlink()
    else:
        doc = loader.load_file(src)
    if a.kind == "openapi":
        spec = openapi.to_spec(doc, include_mutations=a.include_mutations, base_url=a.base_url or "")
    else:
        spec = postman.to_spec(doc)
    text = loader.dump_yaml(spec)
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(text, encoding="utf-8")
        print(c(f"Wrote {len(spec['tests'])} tests to {a.output}", "passed"))
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------- init
SAMPLE_CONFIG = """# Testoria project configuration
# Docs: https://github.com/Testoria-Framework/testoria
tests: [tests/api]          # where spec files live
reports: [html, junit, json]
reports_dir: reports
default_env: local

variables:
  api_version: v1

environments:
  local:
    base_url: "{{ env.API_URL | default('http://127.0.0.1:8080') }}"
  staging:
    base_url: https://staging.example.com
    headers:
      Authorization: "Bearer {{ env.STAGING_TOKEN }}"

mock:
  port: 8080
  mappings: [mocks]
  db: mocks/db.json         # optional: instant CRUD API for each top-level key
  auto_start: false         # set true (or pass --mock) to start the mock during `testoria run`
"""

SAMPLE_SPEC = """name: Users API (example)
tags: [example]

tests:
  - name: health check responds
    tags: [smoke]
    request: {method: GET, url: /health}
    expect:
      status: 200
      max_time_ms: 2000
      json: {status: ok}

  - name: create a user
    request:
      method: POST
      url: /users
      json: {name: "{{ $randomName }}", email: "{{ $randomEmail }}"}
    expect:
      status: 201
      json:
        $.id: {exists: true}
        $.email: {matches: "@example.com$"}
    extract:
      user_id: $.id

  - name: read the created user
    request: {method: GET, url: "/users/{{ user_id }}"}
    expect:
      status: 200
      schema:
        type: object
        required: [id, name, email]
        properties:
          id: {type: [integer, string]}
          email: {type: string, format: email}

  - name: list users is an array
    request: {method: GET, url: /users}
    expect:
      status: 200
      json:
        $: {type: array, min_length: 1}

  - name: unknown user returns 404 for each id
    data: [{id: 999999}, {id: 888888}]
    request: {method: GET, url: "/users/{{ id }}"}
    expect: {status: 404}

  - name: delete the user
    request: {method: DELETE, url: "/users/{{ user_id }}"}
    expect: {status: [200, 204]}
"""

SAMPLE_DB = {"users": [{"id": 1, "name": "Ada Lovelace", "email": "ada@example.com"}],
             "health": {"status": "ok"}}


def cmd_init(a: argparse.Namespace) -> int:
    root = Path(a.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    files = {
        root / "testoria.yaml": SAMPLE_CONFIG,
        root / "tests/api/example.yaml": SAMPLE_SPEC,
        root / "mocks/db.json": json.dumps(SAMPLE_DB, indent=2) + "\n",
        root / ".env.example": "API_URL=http://127.0.0.1:8080\nSTAGING_TOKEN=\n",
    }
    for path, content in files.items():
        if path.exists() and not a.force:
            print(c(f"  skip  {path.relative_to(root)} (exists)", "dim"))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(c(f"  create {path.relative_to(root)}", "passed"))
    print("\nNext steps:")
    print(f"  cd {root}")
    print("  testoria run --mock        # runs the example against the built-in mock API")
    return 0


# ---------------------------------------------------------------------------- doctor
def cmd_doctor(a: argparse.Namespace) -> int:
    print(c(f"Testoria {__version__}", "bold"))
    print(f"  platform  {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  python    {sys.version.split()[0]} at {sys.executable}")
    opt = {"yaml": "PyYAML (YAML specs)", "jsonschema": "jsonschema (full JSON Schema support)"}
    for mod, desc in opt.items():
        try:
            __import__(mod)
            print(f"  {c('✔', 'passed')} {desc}")
        except ImportError:
            print(f"  {c('○', 'skipped')} {desc} - pip install {'pyyaml' if mod == 'yaml' else mod}")
    tools = {"node": "JavaScript suites", "npm": "JavaScript deps", "java": "Java suites", "mvn": "Maven (optional, ./mvnw works)",
             "docker": "Docker image", "k6": "k6 load scripts", "locust": "Locust load scripts", "allure": "Allure reports"}
    for tool, desc in tools.items():
        p = shutil.which(tool)
        print(f"  {c('✔', 'passed') if p else c('○', 'skipped')} {tool:<7} {desc}" + (c(f"  {p}", "dim") if p else ""))
    cfg = loader.find_config()
    print(f"  config    {cfg or c('none found (run: testoria init)', 'skipped')}")
    return 0


# ---------------------------------------------------------------------------- suites (legacy language runners)
def cmd_suite(a: argparse.Namespace) -> int:
    script = Path(__file__).resolve().parent.parent / "scripts" / "run_tests.sh"
    if not script.exists():
        print(c("scripts/run_tests.sh not found (only available in a repository checkout)", "failed"))
        return 2
    bash = shutil.which("bash")
    if not bash:
        print(c("bash is required for language suites (on Windows use Git Bash or WSL)", "failed"))
        return 2
    return subprocess.call([bash, str(script), *a.args])


# ---------------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="testoria", description="Testoria - API testing for any project, on any platform.")
    p.add_argument("--version", action="version", version=f"testoria {__version__}")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    sub = p.add_subparsers(dest="command")

    r = sub.add_parser("run", help="run declarative YAML/JSON API tests")
    r.add_argument("paths", nargs="*", help="spec files or directories (default: 'tests' from testoria.yaml)")
    r.add_argument("-c", "--config", help="path to testoria.yaml")
    r.add_argument("-e", "--env", help="environment from testoria.yaml")
    r.add_argument("-u", "--base-url", help="override base URL")
    r.add_argument("-t", "--tag", action="append", help="only run tests with this tag (repeatable)")
    r.add_argument("-x", "--exclude-tag", action="append", help="skip tests with this tag (repeatable)")
    r.add_argument("-k", "--grep", help="only run tests whose name matches this regex")
    r.add_argument("--var", action="append", help="set a variable KEY=VALUE (repeatable)")
    r.add_argument("-w", "--workers", type=int, default=1, help="run spec files in parallel")
    r.add_argument("--retries", type=int, default=0, help="retry failed tests N times")
    r.add_argument("--timeout", type=float, default=30.0, help="request timeout in seconds")
    r.add_argument("--fail-fast", action="store_true", help="stop at the first failure")
    r.add_argument("--insecure", action="store_true", help="skip TLS certificate verification")
    r.add_argument("--dry-run", action="store_true", help="render requests without sending them")
    r.add_argument("--report", help="comma list: html,junit,json (default from config)")
    r.add_argument("-o", "--output", help="report directory (default: reports)")
    r.add_argument("--open", action="store_true", help="open the HTML report when done")
    r.add_argument("--mock", action="store_true", help="start the built-in mock server for this run")
    r.add_argument("--no-mock", action="store_true", help="do not auto-start the mock server")
    r.add_argument("--mock-port", type=int, help="mock server port")
    r.add_argument("--allow-empty", action="store_true", help="exit 0 when no specs are found")
    r.add_argument("-v", "--verbose", action="store_true")
    r.add_argument("-q", "--quiet", action="store_true", help="only print failures and the summary")
    r.set_defaults(func=cmd_run)

    w = sub.add_parser("watch", help="re-run tests whenever spec files change", parents=[], add_help=True)
    for action in r._actions[1:]:
        w._add_action(action)
    w.add_argument("--no-clear", action="store_true", help="do not clear the screen between runs")
    w.set_defaults(func=cmd_watch)

    m = sub.add_parser("mock", help="start a WireMock-compatible mock server")
    m.add_argument("mappings", nargs="*", help="mapping files/dirs (default: mock.mappings from testoria.yaml)")
    m.add_argument("-c", "--config")
    m.add_argument("-p", "--port", type=int)
    m.add_argument("--host", default="127.0.0.1", help="bind address (use 0.0.0.0 inside containers)")
    m.add_argument("--db", help="JSON file whose top-level keys become CRUD resources")
    m.add_argument("--latency", type=int, default=0, help="add N ms latency to every response")
    m.add_argument("--no-cors", action="store_true")
    m.add_argument("-v", "--verbose", action="store_true")
    m.set_defaults(func=cmd_mock)

    da = sub.add_parser("demo-api", help="start the bundled stateful demo REST API (users/products/orders/auth)")
    da.add_argument("-p", "--port", type=int, default=8080)
    da.add_argument("--host", default="127.0.0.1")
    da.add_argument("--rate-limit", type=int, default=1000, help="requests per client before HTTP 429")
    da.add_argument("-v", "--verbose", action="store_true")
    da.set_defaults(func=cmd_demo_api)

    lo = sub.add_parser("load", help="run a quick load test against one endpoint")
    lo.add_argument("url")
    lo.add_argument("-X", "--method", default="GET")
    lo.add_argument("-u", "--users", type=int, default=10, help="concurrent virtual users")
    lo.add_argument("-d", "--duration", type=float, default=10.0, help="seconds to run")
    lo.add_argument("-n", "--requests", type=int, help="total requests (overrides duration)")
    lo.add_argument("--ramp-up", type=float, default=0.0, help="seconds to ramp up all users")
    lo.add_argument("--think", type=float, default=0.0, help="pause in ms between requests per user")
    lo.add_argument("-H", "--header", action="append", help="'Name: value' (repeatable)")
    lo.add_argument("--data", help="JSON body or @file.json")
    lo.add_argument("--timeout", type=float, default=30.0)
    lo.add_argument("--insecure", action="store_true")
    lo.add_argument("--p95", type=float, help="fail if p95 latency (ms) exceeds this")
    lo.add_argument("--p99", type=float, help="fail if p99 latency (ms) exceeds this")
    lo.add_argument("--max-mean", type=float, help="fail if mean latency (ms) exceeds this")
    lo.add_argument("--max-error-rate", type=float, help="fail if error rate (0-1) exceeds this")
    lo.add_argument("--min-rps", type=float, help="fail if throughput is below this")
    lo.add_argument("-o", "--output", help="write JSON summary to this file")
    lo.set_defaults(func=cmd_load)

    s = sub.add_parser("scan", help="baseline API security checks (only for systems you are authorised to test)")
    s.add_argument("urls", nargs="+")
    s.add_argument("-H", "--header", action="append", help="'Name: value' (repeatable)")
    s.add_argument("--active", action="store_true", help="also send harmless injection probes")
    s.add_argument("--check-auth", action="store_true", help="verify the URL rejects missing/invalid credentials")
    s.add_argument("--fail-on", choices=["low", "medium", "high", "none"], default="high")
    s.add_argument("--timeout", type=float, default=15.0)
    s.add_argument("--insecure", action="store_true")
    s.add_argument("--i-own-this", action="store_true", help="suppress the authorisation reminder")
    s.add_argument("-o", "--output", help="write findings JSON to this file")
    s.set_defaults(func=cmd_scan)

    im = sub.add_parser("import", help="generate tests from OpenAPI/Swagger or a Postman collection")
    im.add_argument("kind", choices=["openapi", "postman"])
    im.add_argument("source", help="file path or URL")
    im.add_argument("-o", "--output", help="output spec file (default: stdout)")
    im.add_argument("--base-url", help="base URL to put in the generated spec")
    im.add_argument("--include-mutations", action="store_true", help="also generate POST/PUT/PATCH/DELETE tests")
    im.set_defaults(func=cmd_import)

    i = sub.add_parser("init", help="scaffold testoria.yaml, an example spec and a mock DB")
    i.add_argument("directory", nargs="?", default=".")
    i.add_argument("-f", "--force", action="store_true", help="overwrite existing files")
    i.set_defaults(func=cmd_init)

    d = sub.add_parser("doctor", help="show environment and optional tool status")
    d.set_defaults(func=cmd_doctor)

    su = sub.add_parser("suite", help="run the bundled Python/JavaScript/Java suites (scripts/run_tests.sh)")
    su.add_argument("args", nargs=argparse.REMAINDER, help="arguments for run_tests.sh, e.g. -l python -t functional")
    su.set_defaults(func=cmd_suite)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            os.system("")  # enable ANSI colors on Windows 10+
        except Exception:  # noqa: BLE001
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.no_color:
        os.environ["NO_COLOR"] = "1"
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return int(args.func(args) or 0)
    except loader.LoadError as e:
        print(c(f"error: {e}", "failed"), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
