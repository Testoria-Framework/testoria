"""JUnit XML, JSON and self-contained HTML reports."""

from __future__ import annotations

import datetime as _dt
import html
import json
import platform
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List

from testoria import __version__
from testoria.runner import StepResult


def _group(results: List[StepResult]) -> "OrderedDict[str, List[StepResult]]":
    groups: "OrderedDict[str, List[StepResult]]" = OrderedDict()
    for r in results:
        groups.setdefault(r.suite, []).append(r)
    return groups


def write_junit(results: List[StepResult], path: Path) -> Path:
    root = ET.Element("testsuites", name="testoria", tests=str(len(results)),
                      failures=str(sum(r.status == "failed" for r in results)),
                      errors=str(sum(r.status == "error" for r in results)),
                      skipped=str(sum(r.status == "skipped" for r in results)),
                      time=f"{sum(r.duration_ms for r in results) / 1000:.3f}")
    for suite, items in _group(results).items():
        s = ET.SubElement(root, "testsuite", name=suite, tests=str(len(items)),
                          failures=str(sum(r.status == "failed" for r in items)),
                          errors=str(sum(r.status == "error" for r in items)),
                          skipped=str(sum(r.status == "skipped" for r in items)),
                          time=f"{sum(r.duration_ms for r in items) / 1000:.3f}",
                          timestamp=_dt.datetime.now().isoformat(timespec="seconds"))
        for r in items:
            tc = ET.SubElement(s, "testcase", name=r.name, classname=suite, file=r.file, time=f"{r.duration_ms / 1000:.3f}")
            if r.status == "failed":
                ET.SubElement(tc, "failure", message=(r.failures[0] if r.failures else "failed")[:500]).text = "\n".join(r.failures)
            elif r.status == "error":
                ET.SubElement(tc, "error", message=(r.failures[0] if r.failures else "error")[:500]).text = "\n".join(r.failures)
            elif r.status == "skipped":
                ET.SubElement(tc, "skipped", message=r.skip_reason)
            if r.request:
                ET.SubElement(tc, "system-out").text = json.dumps({"request": r.request, "response": r.response}, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


def to_dict(results: List[StepResult], elapsed_s: float, meta: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tool": "testoria", "version": __version__,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "platform": f"{platform.system()} {platform.release()} / Python {platform.python_version()}",
        "meta": meta, "elapsed_s": round(elapsed_s, 3),
        "summary": {**{k: sum(1 for r in results if r.status == k) for k in ("passed", "failed", "error", "skipped")},
                    "total": len(results)},
        "results": [r.__dict__ for r in results],
    }


def write_json(results: List[StepResult], path: Path, elapsed_s: float, meta: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(results, elapsed_s, meta), indent=2, default=str), encoding="utf-8")
    return path


_CSS = """
:root{--bg:#0f1220;--card:#181c2f;--txt:#e6e8f0;--dim:#8b90a8;--ok:#2ecc71;--bad:#ff5c6c;--err:#c77dff;--skip:#f5c542;--acc:#5b8cff}
@media (prefers-color-scheme: light){:root{--bg:#f5f6fb;--card:#fff;--txt:#1b1f33;--dim:#666c85}}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--txt)}
header{padding:28px 32px 8px}h1{margin:0;font-size:22px}h1 span{color:var(--acc)}.meta{color:var(--dim);font-size:12px;margin-top:4px}
.cards{display:flex;gap:12px;flex-wrap:wrap;padding:16px 32px}.card{background:var(--card);border-radius:12px;padding:14px 18px;min-width:120px;box-shadow:0 1px 3px #0003}
.card b{display:block;font-size:24px}.card small{color:var(--dim);text-transform:uppercase;letter-spacing:.06em;font-size:11px}
.bar{height:8px;border-radius:4px;display:flex;overflow:hidden;margin:0 32px 8px;background:var(--card)}
.toolbar{display:flex;gap:8px;padding:8px 32px;flex-wrap:wrap}.toolbar input{flex:1;min-width:200px;padding:8px 12px;border-radius:8px;border:1px solid #8884;background:var(--card);color:var(--txt)}
.toolbar button{padding:8px 12px;border-radius:8px;border:1px solid #8884;background:var(--card);color:var(--txt);cursor:pointer}.toolbar button.on{border-color:var(--acc);color:var(--acc)}
main{padding:8px 32px 40px}.suite{background:var(--card);border-radius:12px;margin:12px 0;overflow:hidden}
.suite h2{font-size:15px;margin:0;padding:12px 16px;border-bottom:1px solid #8882;display:flex;justify-content:space-between}
details{border-bottom:1px solid #8881}summary{padding:9px 16px;cursor:pointer;display:flex;gap:10px;align-items:center;list-style:none}
summary::-webkit-details-marker{display:none}.dot{width:10px;height:10px;border-radius:50%;flex:none}
.passed .dot{background:var(--ok)}.failed .dot{background:var(--bad)}.error .dot{background:var(--err)}.skipped .dot{background:var(--skip)}
.name{flex:1}.dur{color:var(--dim);font-variant-numeric:tabular-nums}.tag{font-size:11px;padding:1px 7px;border-radius:9px;background:#5b8cff22;color:var(--acc)}
.body{padding:4px 16px 14px 36px}.fail{color:var(--bad);font-family:ui-monospace,monospace;font-size:12px;white-space:pre-wrap}
pre{background:#0004;padding:10px;border-radius:8px;overflow:auto;font-size:12px;max-height:320px}
"""

_JS = """
const q=document.getElementById('q');let st='all';
function apply(){const t=q.value.toLowerCase();document.querySelectorAll('details').forEach(d=>{
const ok=(st==='all'||d.classList.contains(st))&&d.textContent.toLowerCase().includes(t);d.style.display=ok?'':'none'});
document.querySelectorAll('.suite').forEach(s=>{s.style.display=[...s.querySelectorAll('details')].some(d=>d.style.display!=='none')?'':'none'})}
q.oninput=apply;document.querySelectorAll('[data-s]').forEach(b=>b.onclick=()=>{st=b.dataset.s;
document.querySelectorAll('[data-s]').forEach(x=>x.classList.toggle('on',x===b));apply()});
"""


def write_html(results: List[StepResult], path: Path, elapsed_s: float, meta: Dict[str, Any]) -> Path:
    d = to_dict(results, elapsed_s, meta)
    s = d["summary"]
    total = max(1, s["total"])
    e = html.escape
    bar = "".join(
        f'<div style="width:{s[k] * 100 / total:.2f}%;background:var(--{v})"></div>'
        for k, v in (("passed", "ok"), ("failed", "bad"), ("error", "err"), ("skipped", "skip")) if s[k])
    suites = []
    for suite, items in _group(results).items():
        rows = []
        for r in items:
            tags = "".join(f'<span class="tag">{e(t)}</span>' for t in r.tags)
            detail = ""
            if r.failures:
                detail += "".join(f'<div class="fail">✘ {e(f)}</div>' for f in r.failures)
            if r.skip_reason:
                detail += f"<div>Skipped: {e(r.skip_reason)}</div>"
            if r.request:
                detail += f"<pre>{e(json.dumps(r.request, indent=2, default=str))}</pre>"
            if r.response:
                detail += f"<pre>{e(json.dumps(r.response, indent=2, default=str))}</pre>"
            rows.append(f'<details class="{r.status}"><summary><span class="dot"></span><span class="name">{e(r.name)}</span>'
                        f'{tags}<span class="dur">{r.duration_ms:.0f} ms</span></summary><div class="body">{detail or "No details"}</div></details>')
        ok = sum(r.status == "passed" for r in items)
        suites.append(f'<section class="suite"><h2><span>{e(suite)}</span><span class="dur">{ok}/{len(items)} passed</span></h2>{"".join(rows)}</section>')
    rate = s["passed"] * 100 / max(1, s["total"] - s["skipped"])
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Testoria report</title><style>{_CSS}</style></head><body>
<header><h1><span>Testoria</span> test report</h1><div class="meta">{e(d['generated_at'])} · {e(d['platform'])} · env: {e(str(meta.get('env', 'default')))} · v{__version__}</div></header>
<div class="cards"><div class="card"><small>Total</small><b>{s['total']}</b></div><div class="card"><small>Passed</small><b style="color:var(--ok)">{s['passed']}</b></div>
<div class="card"><small>Failed</small><b style="color:var(--bad)">{s['failed']}</b></div><div class="card"><small>Errors</small><b style="color:var(--err)">{s['error']}</b></div>
<div class="card"><small>Skipped</small><b style="color:var(--skip)">{s['skipped']}</b></div><div class="card"><small>Pass rate</small><b>{rate:.1f}%</b></div>
<div class="card"><small>Duration</small><b>{elapsed_s:.2f}s</b></div></div><div class="bar">{bar}</div>
<div class="toolbar"><input id="q" placeholder="Filter tests…"><button data-s="all" class="on">All</button><button data-s="failed">Failed</button>
<button data-s="error">Errors</button><button data-s="passed">Passed</button><button data-s="skipped">Skipped</button></div>
<main>{''.join(suites) or '<p>No tests were run.</p>'}</main><script>{_JS}</script></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    return path
