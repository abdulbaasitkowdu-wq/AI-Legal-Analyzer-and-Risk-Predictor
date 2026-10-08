"""
Industry benchmarking for uploaded legal documents via Gemini.
Compares a document to common market patterns (not other users' documents).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_env_path = Path(__file__).resolve().parent / ".env"
try:
    from dotenv import load_dotenv

    load_dotenv(_env_path)
except ImportError:
    pass


def _empty_benchmark(error_note: str = "") -> Dict[str, Any]:
    return {
        "alignment_score": None,
        "reassurance_summary": "",
        "document_type_guess": "",
        "similarities": [],
        "standard_aligned_themes": [],
        "areas_to_review": [],
        "status": "error",
        "error_code": "BENCHMARK_UNAVAILABLE",
        "retryable": False,
        "confidence_note": error_note
        or "AI-assisted comparison only — not legal advice. Verify important terms with counsel.",
    }


def _clamp_score(v: Any) -> Optional[int]:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, n))


def _normalize_benchmark(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return _empty_benchmark()

    sims: List[Dict[str, str]] = []
    raw_sims = data.get("similarities")
    if isinstance(raw_sims, list):
        for item in raw_sims[:20]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("topic") or "").strip()
            detail = str(item.get("detail") or item.get("description") or "").strip()
            ind = str(item.get("industry_standard") or item.get("standard") or "").strip()
            if title or detail:
                sims.append(
                    {
                        "title": title or "Theme",
                        "detail": detail,
                        "industry_standard": ind,
                    }
                )

    themes: List[str] = []
    raw_themes = data.get("standard_aligned_themes")
    if isinstance(raw_themes, list):
        themes = [str(t).strip() for t in raw_themes if str(t).strip()][:15]

    review: List[str] = []
    raw_review = data.get("areas_to_review")
    if isinstance(raw_review, list):
        review = [str(t).strip() for t in raw_review if str(t).strip()][:10]

    conf = str(
        data.get("confidence_note")
        or "AI-assisted comparison only — not legal advice. Verify important terms with counsel."
    ).strip()

    return {
        "alignment_score": _clamp_score(data.get("alignment_score")),
        "reassurance_summary": str(data.get("reassurance_summary") or "").strip(),
        "document_type_guess": str(data.get("document_type_guess") or "").strip(),
        "similarities": sims,
        "standard_aligned_themes": themes,
        "areas_to_review": review,
        "status": "success",
        "error_code": None,
        "retryable": False,
        "confidence_note": conf,
    }


def benchmark_document_with_gemini(text: str, filename: str = "") -> Dict[str, Any]:
    from summarizer import _extract_json_object
    from calendar_service import _response_text_safe, _strip_json_fences
    from gemini_fallback import model_candidates, call_with_fallback, normalize_model_id

    if not (text or "").strip():
        out = _empty_benchmark("No document text was provided for benchmarking.")
        out["error_code"] = "NO_TEXT"
        return out

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        out = _empty_benchmark("Benchmarking service is not available (missing dependency).")
        out["error_code"] = "DEPENDENCY_MISSING"
        return out

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        out = _empty_benchmark("Set GEMINI_API_KEY in backend/.env to enable benchmarking.")
        out["error_code"] = "MISSING_API_KEY"
        return out

    model = normalize_model_id(os.getenv("GEMINI_MODEL", "gemini-2.5-flash")) or "gemini-2.5-flash"
    models = [model] if model else model_candidates()
    max_chars = int(os.getenv("BENCHMARK_MAX_INPUT_CHARS", "14000"))
    snippet = text[:max_chars]
    name_hint = (filename or "document")[:200]

    prompt = f"""
Return ONLY valid JSON. No markdown code fences. No text before or after the JSON object.

You compare this legal document to common industry and market drafting practices.
You do NOT have access to other users' files.

Required JSON shape:
{{
  "alignment_score": <integer 0-100>,
  "document_type_guess": "<short label>",
  "reassurance_summary": "<2-4 sentences>",
  "similarities": [
    {{
      "title": "<short heading>",
      "detail": "<how this document aligns>",
      "industry_standard": "<brief standard note>"
    }}
  ],
  "standard_aligned_themes": ["<theme 1>", "<theme 2>"],
  "areas_to_review": ["<optional item>"],
  "confidence_note": "<informational only, not legal advice>"
}}

Filename hint: {name_hint}
DOCUMENT TEXT:
{snippet}
""".strip()

    retries = int(os.getenv("BENCHMARK_RETRIES", "2"))
    base_delay_s = float(os.getenv("BENCHMARK_RETRY_BASE_DELAY_SEC", "1.0"))
    max_attempts = max(1, retries + 1)
    last_error = None
    data = None
    for attempt in range(1, max_attempts + 1):
        try:
            client = genai.Client(api_key=api_key, http_options={"api_version": "v1"})
            response, used_model = call_with_fallback(
                models,
                lambda m: client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.35,
                        max_output_tokens=4096,
                    ),
                ),
            )
            raw = _strip_json_fences(_response_text_safe(response))
            if not raw.strip():
                raise ValueError("EMPTY_MODEL_RESPONSE")
            blob = _extract_json_object(raw)
            data = json.loads(blob)
            if isinstance(data, dict) and not data.get("confidence_note"):
                data["confidence_note"] = f"Generated with model: {used_model}. Informational only; verify with counsel."
            break
        except Exception as e:
            last_error = e
            if attempt >= max_attempts:
                break
            # Exponential backoff for transient provider load spikes.
            sleep_s = base_delay_s * (2 ** (attempt - 1))
            time.sleep(sleep_s)

    if data is None:
        out = _empty_benchmark(f"Benchmarking failed: {last_error!s}")
        msg = str(last_error or "")
        if "503" in msg or "UNAVAILABLE" in msg:
            out["error_code"] = "PROVIDER_UNAVAILABLE"
        elif "EMPTY_MODEL_RESPONSE" in msg:
            out["error_code"] = "EMPTY_MODEL_RESPONSE"
        else:
            out["error_code"] = "BENCHMARK_RUNTIME_ERROR"
        out["retryable"] = True
        return out

    return _normalize_benchmark(data)
