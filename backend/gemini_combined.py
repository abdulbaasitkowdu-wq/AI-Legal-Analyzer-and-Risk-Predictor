"""
Single Gemini request that returns both AI summaries and calendar events.
Cuts API usage in half vs calling summarizer + calendar_service separately (helps free-tier quota).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_env_path = Path(__file__).resolve().parent / ".env"
try:
    from dotenv import load_dotenv

    load_dotenv(_env_path)
except ImportError:
    pass


def combined_summaries_and_events(
    text: str,
    model: Optional[str] = None,
) -> Tuple[Dict[str, str], List[dict], Dict[str, Any]]:
    """
    Returns (summaries dict, calendar event list, benchmark dict).
    On failure, benchmark returns the same structured fallback as benchmark_service.
    """
    from summarizer import _extract_json_object, _normalize_summary_dict
    from calendar_service import (
        _response_text_safe,
        _strip_json_fences,
        normalize_events_list,
    )
    from benchmark_service import _empty_benchmark, _normalize_benchmark
    from gemini_fallback import (
        call_with_fallback,
        is_transient_gemini_error,
        model_candidates,
        normalize_model_id,
    )

    empty_s: Dict[str, str] = {"technical": "", "layman": "", "actionable": ""}
    empty_b = _empty_benchmark("Combined Gemini call unavailable.")
    if not (text or "").strip():
        out = _empty_benchmark("No document text was provided for benchmarking.")
        out["error_code"] = "NO_TEXT"
        return empty_s, [], out

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[WARN] combined: google-genai not installed")
        out = _empty_benchmark("Benchmarking service is not available (missing dependency).")
        out["error_code"] = "DEPENDENCY_MISSING"
        return empty_s, [], out

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] combined: GEMINI_API_KEY not set")
        out = _empty_benchmark("Set GEMINI_API_KEY in backend/.env to enable benchmarking.")
        out["error_code"] = "MISSING_API_KEY"
        return empty_s, [], out

    model = normalize_model_id(model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")) or "gemini-2.5-flash"
    models = [model] if model else model_candidates()
    text = text[:12000]

    prompt = f"""
Return ONLY valid JSON. No markdown code fences. No text before or after the JSON object.

Required shape:
{{
  "summaries": {{
    "technical": "string",
    "layman": "string",
    "actionable": "string"
  }},
  "events": [
    {{"title": "string", "date": "YYYY-MM-DD", "time": "HH:MM"}}
  ],
  "benchmark": {{
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
}}

Summaries:
- technical: concise legal/contract summary for someone with legal training.
- layman: plain English for a non-lawyer.
- actionable: concrete next steps, deadlines to watch, decisions.

Events:
- Only include items with a real calendar date (YYYY-MM-DD).
- Resolve relative deadlines using base dates in the document; omit if impossible.
- time is HH:MM (24-hour); if missing use 09:00.

DOCUMENT:
{text}
""".strip()

    retry_window_sec = float(os.getenv("GEMINI_COMBINED_RETRY_WINDOW_SEC", "120"))
    max_backoff_sec = float(os.getenv("GEMINI_COMBINED_MAX_BACKOFF_SEC", "20"))

    try:
        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1"},
        )
        cfg = types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=8192,
        )
        deadline = time.monotonic() + max(5.0, retry_window_sec)
        attempt = 0
        response = None
        used_model: Optional[str] = None
        last_transient: Optional[BaseException] = None

        while time.monotonic() < deadline:
            attempt += 1
            try:
                response, used_model = call_with_fallback(
                    models,
                    lambda m: client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=cfg,
                    ),
                )
                break
            except Exception as e:  # noqa: BLE001
                if not is_transient_gemini_error(e):
                    raise
                last_transient = e
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                backoff = min(2.0 ** min(attempt - 1, 5), max_backoff_sec)
                sleep_s = min(backoff, remaining)
                print(
                    f"[WARN] combined: transient Gemini error (attempt {attempt}), "
                    f"retry in {sleep_s:.1f}s ({remaining:.0f}s left in window): {e}"
                )
                time.sleep(sleep_s)

        if response is None:
            err = last_transient or RuntimeError("Gemini request failed within retry window")
            raise err

        raw = _strip_json_fences(_response_text_safe(response))
        if not raw.strip():
            print("[WARN] combined: empty model response")
            out = _empty_benchmark("The model returned an empty response.")
            out["error_code"] = "EMPTY_MODEL_RESPONSE"
            out["retryable"] = True
            return empty_s, [], out
        blob = _extract_json_object(raw)
        data = json.loads(blob)
        if isinstance(data, dict):
            data.setdefault("benchmark", {})
            if isinstance(data["benchmark"], dict):
                data["benchmark"].setdefault(
                    "confidence_note",
                    f"Generated with model: {used_model}. Informational only; verify with counsel.",
                )
    except Exception as e:
        print(f"[WARN] combined Gemini analysis failed: {e}")
        out = _empty_benchmark(f"Combined Gemini analysis failed: {e!s}")
        out["error_code"] = "PROVIDER_UNAVAILABLE" if ("503" in str(e) or "UNAVAILABLE" in str(e)) else "BENCHMARK_RUNTIME_ERROR"
        out["retryable"] = True
        return empty_s, [], out

    if not isinstance(data, dict):
        return empty_s, [], empty_b

    sums = data.get("summaries")
    if not isinstance(sums, dict):
        sums = {}
    sums = _normalize_summary_dict(sums)

    ev_raw = data.get("events")
    if not isinstance(ev_raw, list):
        ev_raw = []

    events = normalize_events_list(ev_raw, default_time="09:00")
    bench_raw = data.get("benchmark")
    bench = _normalize_benchmark(bench_raw)
    return sums, events, bench
