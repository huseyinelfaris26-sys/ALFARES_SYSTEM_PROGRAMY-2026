from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_image_path(path: str | Path, *, max_bytes: int = 12_000_000) -> dict[str, Any]:
    """Validate a local image file envelope. This does not classify disease."""
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    size = candidate.stat().st_size
    if size <= 0 or size > max_bytes:
        raise ValueError(f"image must be between 1 and {max_bytes} bytes")
    suffix = candidate.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
        raise ValueError("unsupported image extension")
    return {"path": str(candidate), "size_bytes": size, "extension": suffix, "classification": None, "status": "validated_not_classified", "note": "A locally trained and validated model is not configured."}
