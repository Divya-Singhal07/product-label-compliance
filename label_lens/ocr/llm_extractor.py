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


# Default to a non-reasoning model with reliable json_object output.
# Override with GROQ_MODEL env var if needed.
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
REASONING_MODELS = frozenset({"openai/gpt-oss-20b"})
