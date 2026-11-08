"""JSON Schema validation. Uses `jsonschema` when installed, otherwise a built-in draft-7 subset."""

from __future__ import annotations

import re
from typing import Any, Dict, List

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


def _type_ok(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    py = _TYPES.get(t)
    return isinstance(value, py) if py else True


def _validate(value: Any, schema: Dict[str, Any], path: str, errors: List[str], root: Dict[str, Any]) -> None:
    if not isinstance(schema, dict):
        return
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            target: Any = root
            for part in ref[2:].split("/"):
                target = target.get(part, {}) if isinstance(target, dict) else {}
            _validate(value, target, path, errors, root)
        return
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, x) for x in types):
            errors.append(f"{path}: expected type {t}, got {type(value).__name__}")
            return
    if schema.get("nullable") and value is None:
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum {schema['enum']}")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match pattern {schema['pattern']}")
        fmt = schema.get("format")
        if fmt == "email" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            errors.append(f"{path}: not a valid email")
        if fmt == "uuid" and not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
            errors.append(f"{path}: not a valid uuid")
        if fmt == "date-time" and not re.match(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", value):
            errors.append(f"{path}: not a valid date-time")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and isinstance(schema["exclusiveMinimum"], (int, float)) and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: {value} <= exclusiveMinimum {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and isinstance(schema["exclusiveMaximum"], (int, float)) and value >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: {value} >= exclusiveMaximum {schema['exclusiveMaximum']}")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required property '{req}'")
        props = schema.get("properties", {})
        for k, sub in props.items():
            if k in value:
                _validate(value[k], sub, f"{path}.{k}", errors, root)
        addl = schema.get("additionalProperties", True)
        extra = [k for k in value if k not in props]
        if addl is False and extra:
            errors.append(f"{path}: unexpected properties {extra}")
        elif isinstance(addl, dict):
            for k in extra:
                _validate(value[k], addl, f"{path}.{k}", errors, root)
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, v in enumerate(value):
                _validate(v, items, f"{path}[{i}]", errors, root)
    for key in ("allOf",):
        for sub in schema.get(key, []):
            _validate(value, sub, path, errors, root)
    if "anyOf" in schema or "oneOf" in schema:
        subs = schema.get("anyOf") or schema.get("oneOf")
        ok = 0
        for sub in subs:
            errs: List[str] = []
            _validate(value, sub, path, errs, root)
            ok += not errs
        if ok == 0:
            errors.append(f"{path}: does not match any allowed schema")


def validate(value: Any, schema: Dict[str, Any]) -> List[str]:
    """Return a list of validation error messages (empty when valid)."""
    try:
        import jsonschema  # type: ignore
        validator_cls = jsonschema.validators.validator_for(schema)
        validator = validator_cls(schema)
        return [f"$.{'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in validator.iter_errors(value)]
    except ImportError:
        errors: List[str] = []
        _validate(value, schema, "$", errors, schema)
        return errors
