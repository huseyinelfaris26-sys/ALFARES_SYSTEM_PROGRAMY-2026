"""Crop problem diagnosis from a photo plus symptoms. تشخيص مشاكل المحصول من صورة وأعراض.

HONEST LIMITS: the colour analysis is a weak hint only. The reliable part is the
symptom list. A real trained model can be plugged in through ImageClassifier.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from ..knowledge.loader import data_dir, load_diseases

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_HINT_WEIGHT = 0.5


class ImageClassifier(Protocol):
    """Plug a trained model here. Return {disease_id: probability 0..1}."""

    def predict(self, path: Path) -> dict[str, float]: ...


def analyze_colors(path: Path) -> dict[str, float]:
    """Share of green/yellow/orange/brown/white pixels. نسب الألوان في الصورة."""
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        rgb.thumbnail((256, 256))
        data = rgb.convert("HSV").tobytes()
    counts = {"green": 0, "yellow": 0, "orange": 0, "brown": 0, "white": 0}
    total = len(data) // 3 or 1
    for i in range(0, len(data) - 2, 3):
        h, s, v = data[i], data[i + 1], data[i + 2]
        deg = h * 360 / 255
        if s < 30 and v > 200:
            counts["white"] += 1
        elif 70 <= deg <= 170 and s > 60:
            counts["green"] += 1
        elif 40 <= deg < 70 and s > 80 and v > 120:
            counts["yellow"] += 1
        elif 15 <= deg < 40 and s > 120 and v > 150:
            counts["orange"] += 1
        elif 15 <= deg < 40 and s > 60 and v <= 150:
            counts["brown"] += 1
    return {k: c / total for k, c in counts.items()}


def hints_from_colors(ratios: dict[str, float]) -> set[str]:
    hints: set[str] = set()
    if ratios["yellow"] > 0.15:
        hints.add("yellowing")
    if ratios["brown"] > 0.08:
        hints.add("brown_spots")
    if ratios["orange"] > 0.03:
        hints.add("orange_pustules")
    if ratios["white"] > 0.10:
        hints.add("white_powder")
    return hints


def _store_photo(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    inbox = data_dir() / "photos" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    dest = inbox / f"{digest}{path.suffix.lower()}"
    if not dest.exists():
        shutil.copy2(path, dest)
    return str(dest)


def diagnose(
    crop: str,
    symptoms: list[str],
    photo: Path | None = None,
    classifier: ImageClassifier | None = None,
) -> dict[str, Any]:
    """Rank likely problems. ترتيب المشاكل المحتملة."""
    kb = load_diseases()
    vocab = kb["symptoms"]
    unknown = [s for s in symptoms if s not in vocab]
    if unknown:
        raise ValueError(f"unknown symptoms: {unknown}. valid: {sorted(vocab)}")

    hints: set[str] = set()
    ratios: dict[str, float] = {}
    stored = None
    model_scores: dict[str, float] = {}
    if photo is not None:
        photo = Path(photo)
        if not photo.is_file():
            raise FileNotFoundError(f"photo not found: {photo}")
        if photo.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"photo must be one of {sorted(ALLOWED_SUFFIXES)}")
        ratios = analyze_colors(photo)
        hints = hints_from_colors(ratios) - set(symptoms)
        stored = _store_photo(photo)
        if classifier is not None:
            model_scores = classifier.predict(photo)

    results = []
    for disease_id, d in kb["diseases"].items():
        if crop not in d["crops"]:
            continue
        possible = sum(d["symptoms"].values())
        got = sum(w for s, w in d["symptoms"].items() if s in symptoms)
        got += sum(w * IMAGE_HINT_WEIGHT for s, w in d["symptoms"].items() if s in hints)
        score = min(got / possible, 1.0)
        if disease_id in model_scores:
            score = 0.5 * score + 0.5 * model_scores[disease_id]
        if score <= 0:
            continue
        results.append({
            "id": disease_id,
            "name_ar": d["name_ar"],
            "score": round(score, 2),
            "confidence": "medium" if score >= 0.6 else "low",
            "treatment_ar": d["treatment_ar"],
        })
    results.sort(key=lambda r: r["score"], reverse=True)

    out = {
        "crop": crop,
        "symptoms_used": symptoms,
        "image_hints": sorted(hints),
        "color_ratios": {k: round(v, 3) for k, v in ratios.items()},
        "stored_photo": stored,
        "candidates": results[:3],
        "disclaimer_ar": "هذا تشخيص أولي مساعد فقط وليس نهائياً. أرسل الصورة للمرشد الزراعي قبل أي رش.",
    }
    log = data_dir() / "logs" / "diagnoses.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": int(time.time()), **out}, ensure_ascii=False) + "\n")
    return out
