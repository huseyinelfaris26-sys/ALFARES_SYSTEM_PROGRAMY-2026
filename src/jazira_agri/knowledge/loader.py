"""Load and validate project knowledge JSON files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def data_dir() -> Path:
    """Return the data folder (JAZIRA_DATA overrides the repository default)."""
    env = os.environ.get("JAZIRA_DATA")
    if env:
        return Path(env).expanduser().resolve()
    # <repo>/src/jazira_agri/knowledge/loader.py -> <repo>/data
    return Path(__file__).resolve().parents[3] / "data"


def load_json(relative: str) -> dict[str, Any]:
    """Load a JSON object confined to the configured data directory."""
    root = data_dir().resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("data file path must stay inside the configured data directory")
    if not path.is_file():
        raise FileNotFoundError(f"missing data file: {path}")
    try:
        with path.open(encoding="utf-8") as fh:
            value = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path} (line {exc.lineno}, column {exc.colno})") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def load_crops() -> dict[str, Any]:
    crops = load_json("knowledge/crops.json")
    return {key: value for key, value in crops.items() if not key.startswith("_")}


def load_diseases() -> dict[str, Any]:
    return load_json("knowledge/diseases.json")


def load_region(name: str) -> dict[str, Any]:
    """Load one named region, rejecting path separators and traversal attempts."""
    if not name or Path(name).name != name or name in {".", ".."}:
        raise ValueError("region must be a simple region identifier")
    return load_json(f"regions/{name}.json")
