"""Load YAML/JSON files and project configuration (testoria.yaml)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_NAMES = ("testoria.yaml", "testoria.yml", "testoria.json")
SPEC_SUFFIXES = (".yaml", ".yml", ".json")


class LoadError(Exception):
    pass


def load_file(path: os.PathLike | str) -> Any:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise LoadError(f"Cannot read {p}: {e}") from e
    if p.suffix.lower() == ".json":
        try:
            return json.loads(text)
        except ValueError as e:
            raise LoadError(f"Invalid JSON in {p}: {e}") from e
    try:
        import yaml  # type: ignore
    except ImportError:
        try:
            return json.loads(text)
        except ValueError:
            raise LoadError(
                f"{p} is YAML but PyYAML is not installed. Run: pip install pyyaml (install.sh does this)"
            ) from None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise LoadError(f"Invalid YAML in {p}: {e}") from e


def dump_yaml(data: Any) -> str:
    try:
        import yaml  # type: ignore
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120)
    except ImportError:
        return json.dumps(data, indent=2)


def find_config(start: Optional[Path] = None) -> Optional[Path]:
    cur = (start or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        for name in CONFIG_NAMES:
            if (d / name).is_file():
                return d / name
    return None


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overriding existing values."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:]
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        os.environ.setdefault(key.strip(), val)


def load_project_config(path: Optional[str] = None) -> Dict[str, Any]:
    cfg_path = Path(path) if path else find_config()
    if not cfg_path:
        return {"_root": str(Path.cwd())}
    data = load_file(cfg_path) or {}
    if not isinstance(data, dict):
        raise LoadError(f"{cfg_path} must contain a mapping")
    data["_root"] = str(cfg_path.parent.resolve())
    data["_path"] = str(cfg_path)
    load_dotenv(cfg_path.parent / ".env")
    return data


def collect_spec_files(paths: List[str]) -> List[Path]:
    files: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.suffix.lower() in SPEC_SUFFIXES and f.is_file() and _looks_like_spec(f):
                    files.append(f)
        elif p.is_file():
            files.append(p)
        else:
            raise LoadError(f"Path not found: {raw}")
    seen, out = set(), []
    for f in files:
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            out.append(f)
    return out


def _looks_like_spec(f: Path) -> bool:
    if f.name in CONFIG_NAMES or "node_modules" in f.parts or ".git" in f.parts:
        return False
    try:
        head = f.read_text(encoding="utf-8", errors="ignore")[:4000]
    except OSError:
        return False
    return ("tests:" in head) or ('"tests"' in head)
