"""Load JSON knowledge files. تحميل ملفات المعرفة.

The data folder is found automatically (repo/data) or via env JAZIRA_DATA.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def data_dir() -> Path:
    """Return the data folder. إرجاع مجلد البيانات."""
    env = os.environ.get("JAZIRA_DATA")
    if env:
        return Path(env)
    # this file: <repo>/src/jazira_agri/knowledge/loader.py
    return Path(__file__).resolve().parents[3] / "data"


def load_json(relative: str) -> dict[str, Any]:
    path = data_dir() / relative
    if not path.is_file():
        raise FileNotFoundError(f"missing data file: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_crops() -> dict[str, Any]:
    crops = load_json("knowledge/crops.json")
    return {k: v for k, v in crops.items() if not k.startswith("_")}


def load_diseases() -> dict[str, Any]:
    return load_json("knowledge/diseases.json")


def load_region(name: str) -> dict[str, Any]:
    return load_json(f"regions/{name}.json")
