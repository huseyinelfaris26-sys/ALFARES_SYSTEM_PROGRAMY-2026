from __future__ import annotations

from typing import Any

from ..advisor.farm_advice import build_farm_advice


class AgricultureEngine:
    """Orchestrate the Syrian knowledge-base advisory workflow.

    This engine returns a data-readiness checklist until local agronomic records
    have been reviewed; it does not invent fertilizer, pesticide, or yield values.
    """

    def assess(self, crop_id: str, region_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return build_farm_advice(crop_id=crop_id, region_id=region_id, inputs=inputs)


engine = AgricultureEngine()
