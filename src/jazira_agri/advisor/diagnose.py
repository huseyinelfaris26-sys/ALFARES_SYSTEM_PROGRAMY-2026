"""Crop problem diagnosis from a photo plus symptoms.

Color analysis is a weak hint only; symptoms and a validated trained model are
more useful. Results are advisory and must not replace local agronomy advice.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import time
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image, UnidentifiedImageError

from ..knowledge.loader import data_dir, load_crops, load_diseases

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_HINT_WEIGHT = 0.5
MAX_PHOTO_BYTES = 20 * 1024 * 1024


class ImageClassifier(Protocol):
    """Plug in a trained model; return disease-id to probability (0..1)."""

    def predict(self, path: Path) -> dict[str, float]: ...


def analyze_colors(path: Path) -> dict[str, float]:
    """Share of green/yellow/orange/brown/white pixels."""
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            rgb.thumbnail((256, 256))
            hsv = np.asarray(rgb.convert("HSV"), dtype=np.uint8)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"cannot read a valid image from {path}") from exc

    h = hsv[..., 0].astype(np.float32)
    s = hsv[..., 1].astype(np.float32)
    v = hsv[..., 2].astype(np.float32)
    degrees = h * 360.0 / 255.0
    total = h.size or 1

    counts = {
        "green": int(((70.0 <= degrees) & (degrees <= 170.0) & (s > 60.0)).sum()),
        "yellow": int(((40.0 <= degrees) & (degrees < 70.0) & (s > 80.0) & (v > 120.0)).sum()),
        "orange": int(((15.0 <= degrees) & (degrees < 40.0) & (s > 120.0) & (v > 150.0)).sum()),
        "brown": int(((15.0 <= degrees) & (degrees < 40.0) & (s > 60.0) & (v <= 150.0)).sum()),
        "white": int(((s < 30.0) & (v > 200.0)).sum()),
    }
    return {key: count / total for key, count in counts.items()}


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
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    inbox = data_dir() / "photos" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    destination = inbox / f"{digest.hexdigest()[:16]}{path.suffix.lower()}"
    if not destination.exists():
        shutil.copy2(path, destination)
    return str(destination)


def diagnose(
    crop: str,
    symptoms: list[str],
    photo: Path | None = None,
    classifier: ImageClassifier | None = None,
) -> dict[str, Any]:
    """Rank likely crop problems from symptoms and optional image cues."""
    crop_data = load_crops()
    if crop not in crop_data:
        raise ValueError(f"unknown crop '{crop}'. choices: {', '.join(crop_data)}")
    kb = load_diseases()
    vocab = kb["symptoms"]
    symptoms = list(dict.fromkeys(symptoms))
    unknown = [symptom for symptom in symptoms if symptom not in vocab]
    if unknown:
        raise ValueError(f"unknown symptoms: {unknown}. valid: {sorted(vocab)}")

    hints: set[str] = set()
    ratios: dict[str, float] = {}
    stored: str | None = None
    model_scores: dict[str, float] = {}
    if photo is not None:
        photo = Path(photo)
        if not photo.is_file():
            raise FileNotFoundError(f"photo not found: {photo}")
        if photo.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"photo must be one of {sorted(ALLOWED_SUFFIXES)}")
        if photo.stat().st_size > MAX_PHOTO_BYTES:
            raise ValueError(f"photo exceeds the {MAX_PHOTO_BYTES // (1024 * 1024)} MB size limit")
        ratios = analyze_colors(photo)
        hints = hints_from_colors(ratios) - set(symptoms)
        stored = _store_photo(photo)
        if classifier is not None:
            predicted = classifier.predict(photo)
            if not isinstance(predicted, dict):
                raise ValueError("classifier must return a mapping of disease ids to probabilities")
            for disease_id, score in predicted.items():
                if disease_id not in kb["diseases"]:
                    raise ValueError(f"classifier returned unknown disease id: {disease_id!r}")
                if not isinstance(score, int | float) or not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError(f"classifier score for {disease_id!r} must be finite and within 0..1")
                model_scores[disease_id] = float(score)

    results = []
    for disease_id, disease in kb["diseases"].items():
        if crop not in disease["crops"]:
            continue
        possible = sum(disease["symptoms"].values())
        if possible <= 0:
            continue
        got = sum(weight for symptom, weight in disease["symptoms"].items() if symptom in symptoms)
        got += sum(weight * IMAGE_HINT_WEIGHT for symptom, weight in disease["symptoms"].items() if symptom in hints)
        score = min(got / possible, 1.0)
        if disease_id in model_scores:
            score = 0.5 * score + 0.5 * model_scores[disease_id]
        if score <= 0:
            continue
        results.append({
            "id": disease_id,
            "name_ar": disease["name_ar"],
            "score": round(score, 2),
            "confidence": "medium" if score >= 0.6 else "low",
            "treatment_ar": disease["treatment_ar"],
        })
    results.sort(key=lambda result: (-result["score"], result["id"]))

    output = {
        "crop": crop,
        "symptoms_used": symptoms,
        "image_hints": sorted(hints),
        "color_ratios": {key: round(value, 3) for key, value in ratios.items()},
        "stored_photo": stored,
        "candidates": results[:3],
        "disclaimer_ar": "هذا تشخيص أولي مساعد فقط وليس نهائياً. أرسل الصورة للمرشد الزراعي قبل أي رش.",
    }
    log = data_dir() / "logs" / "diagnoses.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": int(time.time()), **output}, ensure_ascii=False) + "\n")
    return output
