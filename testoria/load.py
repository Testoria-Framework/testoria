"""Lightweight load generator with latency percentiles and threshold checks."""

from __future__ import annotations

import statistics
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from testoria import http


@dataclass
class LoadResult:
    url: str
    method: str
    duration_s: float
    total: int = 0
    errors: int = 0
    latencies: List[float] = field(default_factory=list)
    status_counts: Counter = field(default_factory=Counter)
    error_samples: List[str] = field(default_factory=list)

    def pct(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        data = sorted(self.latencies)
        k = max(0, min(len(data) - 1, int(round(p / 100.0 * (len(data) - 1)))))
        return data[k]

    def summary(self) -> Dict[str, Any]:
        lat = self.latencies or [0.0]
        return {
            "url": self.url, "method": self.method, "requests": self.total, "errors": self.errors,
            "error_rate": round(self.errors / self.total, 4) if self.total else 0.0,
            "rps": round(self.total / self.duration_s, 2) if self.duration_s else 0.0,
            "duration_s": round(self.duration_s, 2),
            "latency_ms": {
                "min": round(min(lat), 2), "mean": round(statistics.fmean(lat), 2),
                "p50": round(self.pct(50), 2), "p90": round(self.pct(90), 2),
                "p95": round(self.pct(95), 2), "p99": round(self.pct(99), 2), "max": round(max(lat), 2),
            },
            "status_codes": {str(k): v for k, v in sorted(self.status_counts.items(), key=lambda kv: str(kv[0]))},
            "error_samples": self.error_samples[:5],
        }


def run_load(url: str, method: str = "GET", users: int = 10, duration_s: float = 10.0,
             requests_total: Optional[int] = None, ramp_up_s: float = 0.0, headers: Optional[Dict[str, str]] = None,
             body: Any = None, timeout: float = 30.0, think_ms: float = 0.0, verify_tls: bool = True,
             expect_status: Any = "2xx-3xx", on_tick=None) -> LoadResult:
    from testoria.assertions import status_matches

    result = LoadResult(url=url, method=method.upper(), duration_s=0.0)
    lock = threading.Lock()
    stop_at = time.perf_counter() + duration_s
    budget = [requests_total] if requests_total else None
    expect = ["2xx", "3xx"] if expect_status == "2xx-3xx" else expect_status

    def take() -> bool:
        if budget is None:
            return time.perf_counter() < stop_at
        with lock:
            if budget[0] <= 0:
                return False
            budget[0] -= 1
            return True

    def worker(delay: float):
        if delay:
            time.sleep(delay)
        while take():
            resp = http.request(method, url, headers=headers, json_body=body if isinstance(body, (dict, list)) else None,
                                body=body if isinstance(body, str) else None, timeout=timeout, verify_tls=verify_tls)
            bad = bool(resp.error) or not status_matches(resp.status, expect)
            with lock:
                result.total += 1
                result.latencies.append(resp.elapsed_ms)
                result.status_counts[resp.status if not resp.error else "conn_error"] += 1
                if bad:
                    result.errors += 1
                    if len(result.error_samples) < 5:
                        result.error_samples.append(resp.error or f"HTTP {resp.status}")
            if think_ms:
                time.sleep(think_ms / 1000.0)

    start = time.perf_counter()
    threads = [threading.Thread(target=worker, args=((ramp_up_s * i / users) if ramp_up_s else 0.0,), daemon=True)
               for i in range(users)]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        time.sleep(0.5)
        if on_tick:
            with lock:
                on_tick(result.total, result.errors, time.perf_counter() - start)
    result.duration_s = time.perf_counter() - start
    return result


def check_thresholds(summary: Dict[str, Any], thresholds: Dict[str, Any]) -> List[str]:
    """thresholds: {p95: 500, p99: 1000, mean: 300, error_rate: 0.01, rps_min: 50}"""
    fails = []
    lat = summary["latency_ms"]
    for key in ("p50", "p90", "p95", "p99", "mean", "max"):
        if key in thresholds and lat[key] > float(thresholds[key]):
            fails.append(f"{key} {lat[key]}ms > {thresholds[key]}ms")
    if "error_rate" in thresholds and summary["error_rate"] > float(thresholds["error_rate"]):
        fails.append(f"error_rate {summary['error_rate']} > {thresholds['error_rate']}")
    if "rps_min" in thresholds and summary["rps"] < float(thresholds["rps_min"]):
        fails.append(f"rps {summary['rps']} < {thresholds['rps_min']}")
    return fails
