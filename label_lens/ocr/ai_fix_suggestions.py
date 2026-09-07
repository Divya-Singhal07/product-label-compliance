from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .llm_extractor import (
    GROQ_AVAILABLE,
    LLMExtractionError,
    _is_reasoning_model,
    _message_text,
    Groq,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are an expert Indian packaged-commodity label compliance assistant.

Your job is to explain how to fix an ALREADY DETECTED compliance violation.

IMPORTANT:
- The Rule Engine has already determined that the violation exists.
- Do NOT decide whether the violation is valid.
- Do NOT invent legal requirements.
- Do NOT change the severity.
- Do NOT provide legal advice beyond the supplied rule information.
- Use the supplied legal reference and existing rule suggestion as the authority.
- Give a practical correction that a product manufacturer/designer can apply to the label.
- Keep the answer concise and specific.

Return ONLY valid JSON:

{
  "ai_fix": "short practical fix",
  "example": "example label wording when useful",
  "confidence": 0.0
}

confidence must be a number between 0 and 1.
"""


def _parse_json(content: str) -> Dict[str, Any]:
    text = (content or "").strip()

    if not text:
        raise LLMExtractionError("AI fix suggestion returned empty content")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise LLMExtractionError(
                "AI fix suggestion returned invalid JSON"
            )

        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMExtractionError(
                f"Could not parse AI fix suggestion JSON: {exc}"
            ) from exc

    if not isinstance(parsed, dict):
        raise LLMExtractionError(
            "AI fix suggestion response was not an object"
        )

    return parsed


def generate_ai_fix_suggestions(
    violations: List[Dict[str, Any]],
    product_fields: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate contextual AI fixes for existing Rule Engine violations.

    The Rule Engine remains authoritative. This function only adds
    explanatory/contextual suggestions.
    """

    if not violations:
        return []

    if not GROQ_AVAILABLE:
        logger.warning("Groq package unavailable; skipping AI fix suggestions")
        return []

    import os

    api_key = api_key or os.getenv("GROQ_API_KEY")

    if not api_key:
        logger.warning("GROQ_API_KEY not configured; skipping AI fix suggestions")
        return []

    preferred = (
        os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b").strip()
        or "qwen/qwen3.6-27b"
    )

    client = Groq(api_key=api_key, timeout=60.0)

    results: List[Dict[str, Any]] = []

    for violation in violations:
        payload = {
            "violation": {
                "rule_id": violation.get("rule_id"),
                "field": violation.get("field"),
                "message": violation.get("message"),
                "severity": violation.get("severity"),
                "detected_value": violation.get("detected_value"),
                "expected": violation.get("expected"),
                "legal_reference": violation.get("legal_reference"),
                "explanation": violation.get("explanation"),
                "existing_suggestion": violation.get("suggestion"),
            },
            "product_fields": product_fields or {},
        }

        user_prompt = (
            "Generate a practical AI fix for this detected label violation.\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        )

        is_reasoning = _is_reasoning_model(preferred)

        token_kwargs: Dict[str, Any] = {}

        if is_reasoning:
            token_kwargs["max_completion_tokens"] = int(
                os.getenv("GROQ_MAX_COMPLETION_TOKENS", "800")
            )

            if "qwen3" in preferred.lower():
                token_kwargs["reasoning_effort"] = "none"
        else:
            token_kwargs["max_tokens"] = int(
                os.getenv("GROQ_MAX_TOKENS", "1000")
            )

        try:
            response = client.chat.completions.create(
                model=preferred,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                **token_kwargs,
            )

            raw = _message_text(response)
            parsed = _parse_json(raw)

            ai_fix = str(parsed.get("ai_fix", "") or "").strip()
            example = str(parsed.get("example", "") or "").strip()

            confidence_raw = parsed.get("confidence", 0.0)

            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.0

            confidence = max(0.0, min(1.0, confidence))

            results.append(
                {
                    "rule_id": violation.get("rule_id"),
                    "field": violation.get("field"),
                    "ai_fix": ai_fix,
                    "example": example or None,
                    "confidence": round(confidence, 3),
                }
            )

        except Exception as exc:
            logger.warning(
                "AI fix generation failed for %s: %s",
                violation.get("rule_id"),
                exc,
            )

            # Keep the system usable even if the AI call fails.
            results.append(
                {
                    "rule_id": violation.get("rule_id"),
                    "field": violation.get("field"),
                    "ai_fix": violation.get("suggestion"),
                    "example": None,
                    "confidence": 0.0,
                }
            )

    return results
