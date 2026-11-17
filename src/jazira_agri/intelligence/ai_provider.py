"""Optional AI integration adapters for agriculture decision support.

AI is used only to summarize deterministic local engine outputs. It does not
replace the crop, irrigation, weather, soil, or image-analysis engines.
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol


class AgricultureAI(Protocol):
    """Provider interface for an optional Arabic field-assessment summary."""

    def summarize(self, assessment: dict[str, Any]) -> str: ...


class OpenAIAgricultureAI:
    """OpenAI Responses API adapter, imported only when instantiated.

    Set OPENAI_API_KEY and optionally JAZIRA_AI_MODEL. Do not send personally
    identifying or confidential farm data to an external provider.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("Set OPENAI_API_KEY before enabling the OpenAI adapter")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the optional AI dependencies: pip install 'jazira-agri-os[ai]'") from exc
        self._client = OpenAI(api_key=key)
        self._model = model or os.environ.get("JAZIRA_AI_MODEL", "gpt-4.1-mini")

    def summarize(self, assessment: dict[str, Any]) -> str:
        prompt = (
            "أنت مساعد زراعي يشرح نتائج محركات دعم القرار. لخّص البيانات التالية بالعربية "
            "بوضوح، وميّز بين القياس والتقدير. لا تخترع قيماً أو تشخّص مرضاً جديداً، "
            "ولا توصي بمبيد أو جرعة أو إجراء خطر. اذكر أن القرار النهائي للمهندس الزراعي.\n\n"
            + json.dumps(assessment, ensure_ascii=False, separators=(",", ":"))
        )
        response = self._client.responses.create(model=self._model, input=prompt)
        text = getattr(response, "output_text", "")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("AI provider returned an empty summary")
        return text.strip()[:4000]


__all__ = ["AgricultureAI", "OpenAIAgricultureAI"]
