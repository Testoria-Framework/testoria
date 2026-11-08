"""Shared pytest setup for the bundled Python suites.

By default the suites run against the bundled Testoria demo API, started on a free local port.
Set API_BASE_URL to run the same suites against your own deployment instead.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MARKERS = ("functional", "integration", "security", "performance", "smoke")


def pytest_configure(config):
    for m in MARKERS:
        config.addinivalue_line("markers", f"{m}: {m} tests")


@pytest.fixture(scope="session", autouse=True)
def demo_api_server():
    """Start the demo API for the test session unless an external API_BASE_URL is provided."""
    if os.environ.get("API_BASE_URL"):
        yield os.environ["API_BASE_URL"]
        return
    from testoria import demo_api

    server, _store = demo_api.start_background("127.0.0.1", 0)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    os.environ["API_BASE_URL"] = url
    try:
        yield url
    finally:
        server.shutdown()
        os.environ.pop("API_BASE_URL", None)
