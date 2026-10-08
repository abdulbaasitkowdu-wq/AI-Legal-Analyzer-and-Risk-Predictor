"""
Small optional model fallback helper.
Designed to be easy to remove: delete imports/calls to this module.
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional, Tuple, TypeVar

T = TypeVar("T")


def normalize_model_id(name: Optional[str]) -> str:
    """
    The Gemini API expects ids like 'gemini-2.0-flash', not UI labels like 'Gemini-2.0-Flash'.
    """
    s = (name or "").strip()
    if not s:
        return ""
    s = s.lower().replace(" ", "-")
    if s.startswith("models/"):
        s = s[7:]
    return s


def model_candidates() -> List[str]:
    """
    Build ordered model candidates from env.
    - Primary: GEMINI_MODEL
    - Optional fallbacks: GEMINI_FALLBACK_MODELS=comma,separated,list
    - Toggle: GEMINI_ENABLE_FALLBACK=1|true|yes
    """
    primary = normalize_model_id(os.getenv("GEMINI_MODEL", "gemini-2.5-flash")) or "gemini-2.5-flash"
    enabled = os.getenv("GEMINI_ENABLE_FALLBACK", "0").strip().lower() in ("1", "true", "yes")
    if not enabled:
        return [primary]

    raw = os.getenv("GEMINI_FALLBACK_MODELS", "").strip()
    extras = [normalize_model_id(m) or "" for m in raw.split(",") if m.strip()]
    out: List[str] = []
    for m in [primary] + extras:
        if m and m not in out:
            out.append(m)
    return out or [primary]


def is_transient_gemini_error(exc: BaseException) -> bool:
    """
    Overload / temporary upstream errors worth retrying (503, 429, etc.).
    Uses string matching because the google-genai SDK may wrap errors inconsistently.
    """
    s = str(exc)
    u = s.upper()
    if "503" in s or "UNAVAILABLE" in u:
        return True
    if "429" in s or "RESOURCE_EXHAUSTED" in u:
        return True
    if "500" in s and ("INTERNAL" in u or "INTERNAL_ERROR" in u):
        return True
    if "504" in s or "DEADLINE" in u:
        return True
    return False


def call_with_fallback(models: List[str], fn: Callable[[str], T]) -> Tuple[T, str]:
    """
    Call fn(model) in order; return (result, model_used).
    Raises final exception if all models fail.
    """
    last_err = None
    for model in models:
        try:
            return fn(model), model
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[WARN] model '{model}' failed: {e}")
    raise last_err if last_err else RuntimeError("No model candidates available")

