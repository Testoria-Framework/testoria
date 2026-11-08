from __future__ import annotations

import os
import sys
from typing import List

from testoria.runner import StepResult

_COLORS = {"passed": "32", "failed": "31", "error": "35", "skipped": "33", "dim": "2", "bold": "1", "cyan": "36"}


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


def c(text: str, kind: str) -> str:
    if not use_color():
        return text
    return f"\033[{_COLORS.get(kind, '0')}m{text}\033[0m"


ICONS = {"passed": "✔", "failed": "✘", "error": "!", "skipped": "○"}
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    ICONS = {"passed": "+", "failed": "x", "error": "!", "skipped": "-"}


class ConsolePrinter:
    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self._suite = None

    def __call__(self, r: StepResult) -> None:
        if self.quiet and r.status in ("passed", "skipped"):
            return
        if r.suite != self._suite:
            self._suite = r.suite
            print("\n" + c(f"● {r.suite}", "bold") + c(f"  ({r.file})", "dim"))
        dur = c(f"{r.duration_ms:.0f}ms", "dim") if r.status != "skipped" else c(r.skip_reason, "dim")
        retry = c(f" (attempt {r.attempts})", "dim") if r.attempts > 1 else ""
        print(f"  {c(ICONS[r.status], r.status)} {r.name} {dur}{retry}")
        if r.status in ("failed", "error"):
            for f in r.failures:
                print("      " + c("→ " + f, r.status))
            if r.request:
                print("      " + c(f"{r.request.get('method')} {r.request.get('url')}", "dim"))
        elif self.verbose and r.request:
            print("      " + c(f"{r.request.get('method')} {r.request.get('url')} → {r.response.get('status')}", "dim"))


def print_summary(results: List[StepResult], elapsed_s: float) -> None:
    counts = {k: sum(1 for r in results if r.status == k) for k in ("passed", "failed", "error", "skipped")}
    parts = [c(f"{counts['passed']} passed", "passed")]
    if counts["failed"]:
        parts.append(c(f"{counts['failed']} failed", "failed"))
    if counts["error"]:
        parts.append(c(f"{counts['error']} errors", "error"))
    if counts["skipped"]:
        parts.append(c(f"{counts['skipped']} skipped", "skipped"))
    print("\n" + c("Summary: ", "bold") + ", ".join(parts) + c(f"  ({len(results)} tests in {elapsed_s:.2f}s)", "dim"))
