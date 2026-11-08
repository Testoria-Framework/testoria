"""Unit tests for the testoria package (run: python -m pytest tests/unit)."""

import json
import urllib.request

import pytest

from testoria import assertions, jsonpath, schema, templating
from testoria.http import Response
from testoria.importers import openapi, postman
from testoria.load import check_thresholds


def _resp(status=200, body=None, headers=None):
    raw = json.dumps(body).encode() if body is not None else b""
    return Response(status, headers or {"Content-Type": "application/json"}, raw, 12.0, "http://x", "GET")


class TestJsonPath:
    data = {"a": {"b": [1, 2, {"c": "x"}]}, "items": [{"id": 1}, {"id": 2}]}

    def test_dotted_and_index(self):
        assert jsonpath.get(self.data, "$.a.b[1]") == 2
        assert jsonpath.get(self.data, "a.b[-1].c") == "x"

    def test_wildcard_and_deep(self):
        assert jsonpath.get(self.data, "$.items[*].id") == [1, 2]
        assert jsonpath.get(self.data, "$..id") == [1, 2]

    def test_length_and_missing(self):
        assert jsonpath.get(self.data, "$.items.length()") == 2
        assert not jsonpath.exists(self.data, "$.nope")
        with pytest.raises(KeyError):
            jsonpath.get(self.data, "$.nope")


class TestTemplating:
    def test_native_types_and_filters(self):
        ctx = {"n": 5, "user": {"name": "ada"}}
        assert templating.render("{{ n }}", ctx) == 5
        assert templating.render("id={{ n }}", ctx) == "id=5"
        assert templating.render("{{ user.name | upper }}", ctx) == "ADA"
        assert templating.render("{{ missing | default('x') }}", ctx) == "x"

    def test_dynamic_and_env(self, monkeypatch):
        monkeypatch.setenv("TESTORIA_X", "1")
        assert templating.render("{{ env.TESTORIA_X }}", {}) == "1"
        assert "@example.com" in templating.render("{{ $randomEmail }}", {})
        assert len(templating.render("{{ $uuid }}", {})) == 36


class TestAssertions:
    def test_status_patterns(self):
        assert assertions.status_matches(204, "2xx")
        assert assertions.status_matches(404, [400, 404])
        assert assertions.status_matches(302, "300-399")
        assert not assertions.status_matches(500, "2xx")

    def test_json_operators(self):
        r = _resp(body={"id": 3, "tags": ["a", "b"], "email": "a@b.co", "items": [{"k": 1}]})
        fails = assertions.evaluate_expectations(r, {
            "status": 200,
            "json": {"$.id": {"gt": 1, "type": "integer"}, "$.tags": {"contains": "a", "length": 2},
                     "$.email": {"matches": "@b\\.co$"}, "$.items": {"contains": {"k": 1}},
                     "$.missing": {"exists": False}},
        })
        assert fails == []

    def test_failures_are_reported(self):
        r = _resp(status=500, body={"id": 1})
        fails = assertions.evaluate_expectations(r, {"status": 200, "json": {"$.id": 2}})
        assert any("status" in f for f in fails) and any("$.id" in f for f in fails)


def test_schema_fallback_validator():
    s = {"type": "object", "required": ["id"], "properties": {"id": {"type": "integer"}}}
    assert schema.validate({"id": 1}, s) == []
    assert schema.validate({"id": "x"}, s)
    assert schema.validate({}, s)


def test_openapi_import_generates_tests():
    doc = {"openapi": "3.0.0", "info": {"title": "Pets"}, "servers": [{"url": "https://pets.test"}],
           "paths": {"/pets/{id}": {"get": {"summary": "get pet", "parameters": [{"name": "id", "in": "path"}],
                                           "responses": {"200": {"content": {"application/json": {"schema": {
                                               "$ref": "#/components/schemas/Pet"}}}}}}}},
           "components": {"schemas": {"Pet": {"type": "object", "required": ["id"],
                                             "properties": {"id": {"type": "integer"}}}}}}
    spec = openapi.to_spec(doc)
    assert spec["base_url"] == "https://pets.test"
    t = spec["tests"][0]
    assert t["request"]["url"] == "/pets/1" and t["expect"]["status"] == 200
    assert t["expect"]["schema"]["required"] == ["id"]


def test_postman_import():
    col = {"info": {"name": "C"}, "item": [{"name": "folder", "item": [
        {"name": "get", "request": {"method": "GET", "url": {"raw": "{{host}}/a"}},
         "event": [{"script": {"exec": ["pm.response.to.have.status(201)"]}}]}]}]}
    spec = postman.to_spec(col)
    assert spec["tests"][0]["name"] == "folder / get"
    assert spec["tests"][0]["request"]["url"] == "{{ host }}/a"
    assert spec["tests"][0]["expect"]["status"] == 201


def test_load_thresholds():
    summary = {"latency_ms": {"p50": 1, "p90": 2, "p95": 900, "p99": 3, "mean": 1, "max": 5},
               "error_rate": 0.0, "rps": 10}
    assert check_thresholds(summary, {"p95": 500}) == ["p95 900ms > 500ms"]
    assert check_thresholds(summary, {"error_rate": 0.01}) == []


def test_mock_server_wiremock_and_crud(tmp_path):
    from testoria import mock
    (tmp_path / "m.json").write_text(json.dumps({"mappings": [
        {"request": {"method": "GET", "urlPattern": "/hello/[a-z]+"},
         "response": {"status": 200, "jsonBody": {"who": "{{request.pathSegments.[1]}}"}}}]}))
    db = tmp_path / "db.json"
    db.write_text(json.dumps({"notes": [{"id": 1, "done": True}]}))
    server, _ = mock.start_background("127.0.0.1", 0, [str(tmp_path / "m.json")], db=str(db))
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/hello/ada") as r:
            assert json.loads(r.read()) == {"who": "ada"}
        with urllib.request.urlopen(base + "/notes?done=true") as r:
            assert len(json.loads(r.read())) == 1
        req = urllib.request.Request(base + "/notes", data=b'{"text":"x"}', method="POST")
        with urllib.request.urlopen(req) as r:
            assert r.status == 201 and json.loads(r.read())["id"] == 2
    finally:
        server.shutdown()
