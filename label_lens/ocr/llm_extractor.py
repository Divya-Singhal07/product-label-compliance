"""
LLM-based field extractor – upgraded for Rule Engine compatibility.

Failures (API errors, empty content, invalid JSON) raise LLMExtractionError
so callers never treat an empty schema as a successful extraction.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class LLMExtractionError(RuntimeError):
    """Raised when Groq extraction fails or returns unusable content."""


# llama-3.3-70b-versatile was shut down for Groq free/dev on 2026-08-16.
# Override with GROQ_MODEL. If that id 404s, we try FALLBACK_GROQ_MODELS.
DEFAULT_GROQ_MODEL = "qwen/qwen3.6-27b"
FALLBACK_GROQ_MODELS = (
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
)
REASONING_MODELS = frozenset({
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "qwen/qwen3.8-27b",
})


SYSTEM_PROMPT = """You are an expert Indian packaged-commodity label analyst specializing in
Legal Metrology (Packaged Commodities) Rules and food-label declarations.

Your task is to extract ONLY information that is actually present in the supplied OCR text.
OCR may contain spelling errors, broken words, incorrect characters, missing punctuation,
or lines in an unusual order.

Return ONLY one valid JSON object matching the exact schema below.

{
  "brand": null,
  "product_name": null,
  "generic_name": null,
  "net_quantity": null,
  "mrp": null,
  "mrp_inclusive_of_taxes": null,
  "unit_sale_price": null,
  "manufacturer_address": null,
  "packer": null,
  "importer": null,
  "consumer_care": null,
  "mfg_date": null,
  "best_before": null,
  "use_by": null,
  "country_of_origin": null,
  "product_type": "general",
  "specific_product": null,
  "is_food": false,
  "is_cosmetic": false,
  "is_electronic": false,
  "is_imported": false,
  "has_shelf_life": false
}

EXTRACTION RULES:

1. BRAND
- Extract the primary brand printed on the package.
- Do not confuse the manufacturer with the brand.

2. PRODUCT NAME
- Extract the complete marketed/product name.
- Preserve meaningful words from the label.

3. GENERIC NAME
- Extract the common/category name describing what the product actually is.
- Examples:
  "Fruit Juice", "Biscuits", "Honey", "Shampoo", "Toothpaste".
- Do NOT simply copy the brand name.
- If the label clearly says something such as "Nimboora with Nimbu Juice",
  infer "Fruit Juice" ONLY when the product wording itself clearly establishes
  that it is fruit juice.
- Otherwise use null.

4. NET QUANTITY
- Extract the declared net quantity together with its unit.
- Examples: "350 ml", "500 g", "1 L", "10 Nos".
- Normalize obvious OCR spacing errors where safe.

5. MRP
- Search carefully for all common MRP forms:
  "MRP", "M.R.P", "M R P", "MAXIMUM RETAIL PRICE", "MAX RETAIL PRICE",
  "Rs.", "₹", "INR" when clearly associated with a retail price.
- Extract the complete printed MRP declaration when available.
- Examples: "₹40", "Rs. 40/-", "MRP ₹40.00".
- Do NOT confuse selling price, discount price, batch number, barcode numbers,
  phone numbers, or other numeric values with MRP.
- Do NOT invent an MRP.

6. MRP INCLUSIVE OF TAXES
- Set true ONLY if the OCR text explicitly indicates that MRP includes taxes,
  such as "inclusive of all taxes", "incl. of all taxes", or equivalent wording.
- Otherwise use false or null according to the available evidence.
- Never assume this merely because an MRP exists.

7. UNIT SALE PRICE
- Extract the unit sale price ONLY if it is explicitly printed or clearly
  derivable from a declared unit-sale-price statement on the label.
- Do not invent or calculate it from MRP unless the label/rules explicitly
  provide sufficient information.
- Examples may include "₹/kg", "₹/L", or an explicitly printed unit price.

8. MANUFACTURER ADDRESS
- Extract the complete manufacturer name and address when present.
- Preserve the address as accurately as possible.

9. PACKER / IMPORTER
- Extract separately when explicitly present.

10. CONSUMER CARE
- Extract phone number, email address, website, or consumer-care contact
  information when present.

11. MANUFACTURING DATE
- Look for:
  "MFD", "MFG", "MANUFACTURED ON", "DATE OF MANUFACTURE",
  "PKD", "PACKED ON", "DATE OF PACKING".
- Put the actual manufacturing/packing declaration into "mfg_date".
- Preserve the date/period exactly as printed where possible.
- Do not confuse batch numbers with dates.

12. BEST BEFORE
- Look for:
  "BEST BEFORE", "BEST BEFORE END", "BB", or equivalent wording.
- Examples:
  "BEST BEFORE 6 MONTHS",
  "BEST BEFORE 12 MONTHS FROM MFD",
  "BB 6 MONTHS".
- Put this information into "best_before".

13. USE BY / EXPIRY
- Look for:
  "USE BY", "EXP", "EXPIRY", "EXPIRY DATE", "USE BEFORE".
- Put this information into "use_by".
- Do not put an expiry date into best_before unless the label specifically
  uses best-before wording.

14. COUNTRY OF ORIGIN
- Extract only when explicitly mentioned.

15. PRODUCT CLASSIFICATION
- product_type MUST be exactly one of:
  "food", "cosmetics", "electronic", "general".
  Use the plural "cosmetics" (not "cosmetic") so it matches rule YAML keys.
- specific_product should be lowercase with underscores.
- Examples:
  "fruit_juices", "biscuits", "honey", "shampoo", "toothpaste".
- Use the most specific classification supported by the text.
- Do not classify based only on the brand name.

16. BOOLEAN FLAGS
- Set is_food true only when clearly a food product.
- Set is_cosmetic true only when clearly a cosmetic.
- Set is_electronic true only when clearly an electronic product.
- Set is_imported true only when imported status is clearly indicated.
- Set has_shelf_life true when the label contains best-before, use-by,
  expiry, or an explicitly stated shelf-life period.

17. OCR ERROR HANDLING
- Correct obvious OCR errors when the intended declaration is unambiguous.
- For example, "MRP Rs 4O/-" may represent "MRP Rs 40/-" if the context
  clearly indicates a price.
- Do not guess when multiple interpretations are possible.

18. MISSING VALUES
- Use null for missing text fields.
- Use false for boolean flags when clearly not applicable.
- Never fabricate information.

19. IMPORTANT
- Every extracted value must be supported by the OCR text or an unambiguous
  interpretation of it.
- Return ONLY JSON.
"""


def _is_reasoning_model(model: str) -> bool:
    name = (model or "").lower()
    return (
        model in REASONING_MODELS
        or name.startswith("openai/gpt-oss")
        or "qwen3" in name
    )


def _parse_json_content(content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise LLMExtractionError("LLM returned empty content")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise LLMExtractionError(f"LLM returned non-JSON content: {e}") from e
        try:
            parsed = json.loads(match.group(0))
        except Exception as parse_exc:
            raise LLMExtractionError(
                f"LLM returned invalid JSON that could not be recovered: {parse_exc}"
            ) from parse_exc
    if not isinstance(parsed, dict):
        raise LLMExtractionError("LLM response JSON was not an object")
    return parsed


def _message_text(response: Any) -> str:
    message = response.choices[0].message
    content = getattr(message, "content", None)
    if content and str(content).strip():
        return str(content)
    # Reasoning models sometimes put the answer in extra fields.
    for attr in ("reasoning", "reasoning_content"):
        extra = getattr(message, attr, None)
        if extra and str(extra).strip():
            return str(extra)
    return ""


def extract_fields_with_llm(
    ocr_lines: List[Dict[str, Any]],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    if not GROQ_AVAILABLE:
        raise ImportError("Please install groq: pip install groq")

    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")

    texts = [line["text"] for line in ocr_lines if line.get("text")]
    ocr_text = "\n".join(texts)

    empty_result = {
        "brand": None,
        "product_name": None,
        "generic_name": None,
        "net_quantity": None,
        "mrp": None,
        "mrp_inclusive_of_taxes": False,
        "unit_sale_price": None,
        "manufacturer_address": None,
        "packer": None,
        "importer": None,
        "consumer_care": None,
        "mfg_date": None,
        "best_before": None,
        "use_by": None,
        "country_of_origin": None,
        "product_type": "general",
        "specific_product": None,
        "is_food": False,
        "is_cosmetic": False,
        "is_electronic": False,
        "is_imported": False,
        "has_shelf_life": False,
    }

    if not ocr_text.strip():
        # No OCR text is not an LLM failure; return empty schema.
        return empty_result

    preferred = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    models_to_try: List[str] = []
    for candidate in (preferred, *FALLBACK_GROQ_MODELS):
        if candidate and candidate not in models_to_try:
            models_to_try.append(candidate)

    client = Groq(api_key=api_key, timeout=90.0)
    last_error: Optional[Exception] = None
    fields: Optional[Dict[str, Any]] = None

    for model in models_to_try:
        is_reasoning = _is_reasoning_model(model)
        token_kwargs: Dict[str, Any] = {}
        if is_reasoning:
            token_kwargs["max_completion_tokens"] = int(
                os.getenv("GROQ_MAX_COMPLETION_TOKENS", "8000")
            )
        else:
            token_kwargs["max_tokens"] = int(os.getenv("GROQ_MAX_TOKENS", "2500"))

        # Reasoning models often fail Groq json_object validation (empty
        # failed_generation). Try strict JSON first, then plain text.
        format_modes: List[Optional[Dict[str, str]]] = [
            {"type": "json_object"},
            None,
        ]

        for response_format in format_modes:
            create_kwargs: Dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"OCR Text from product label:\n\n{ocr_text}",
                    },
                ],
                "temperature": 0.1,
                **token_kwargs,
            }
            if response_format is not None:
                create_kwargs["response_format"] = response_format

            try:
                response = client.chat.completions.create(**create_kwargs)
                parsed = _parse_json_content(_message_text(response))
                fields = parsed
                if model != preferred or response_format is None:
                    logger.info(
                        "LLM extraction succeeded with model=%s json_mode=%s",
                        model,
                        response_format is not None,
                    )
                break
            except LLMExtractionError as e:
                last_error = e
                logger.warning("LLM parse failed (model=%s): %s", model, e)
                continue
            except Exception as e:
                last_error = e
                err_text = str(e)
                if "model_not_found" in err_text or "does not exist" in err_text:
                    logger.warning("Groq model %s not available: %s", model, e)
                    break
                if "json_validate_failed" in err_text or "Failed to validate JSON" in err_text:
                    logger.warning(
                        "Groq json_object rejected for %s; retrying without JSON mode",
                        model,
                    )
                    continue
                logger.error("LLM extraction failed: %s", e)
                continue
        if fields is not None:
            break
    else:
        raise LLMExtractionError(
            f"LLM extraction failed: {last_error}. "
            "Set GROQ_MODEL in backend/.env to a model your Groq key can access "
            "(see https://console.groq.com/docs/models)."
        ) from last_error

    if fields is None:
        raise LLMExtractionError(
            f"LLM extraction failed: {last_error}."
        ) from last_error

    # Ensure all keys exist
    for k, v in empty_result.items():
        if k not in fields:
            fields[k] = v

    return fields
