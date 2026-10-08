"""
AI document summaries (technical / layman / actionable) via Gemini.
Uses plain JSON-in-text (no response_schema) — compatible with Gemini API v1.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure .env is loaded even if this module is imported before database.py
_env_path = Path(__file__).resolve().parent / ".env"
try:
    from dotenv import load_dotenv

    load_dotenv(_env_path)
except ImportError:
    pass


def _strip_json_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _model_text(response: Any) -> str:
    t = getattr(response, "text", None)
    if t:
        return t
    try:
        parts = response.candidates[0].content.parts
        return "".join(getattr(p, "text", "") or "" for p in parts)
    except (AttributeError, IndexError, TypeError):
        return ""


def _finish_debug(response: Any) -> str:
    try:
        c = response.candidates[0]
        fr = getattr(c, "finish_reason", None)
        return f"finish_reason={fr!r}"
    except (AttributeError, IndexError, TypeError):
        return "no candidate details"


def _extract_json_object(s: str) -> str:
    s = _strip_json_fences(s.strip())
    if not s:
        return s
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    start = s.find("{")
    if start < 0:
        return s
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return s


def _normalize_summary_dict(data: Any) -> Dict[str, str]:
    empty = {"technical": "", "layman": "", "actionable": ""}
    if not isinstance(data, dict):
        return empty

    lower_map = {}
    for k, v in data.items():
        if k is None:
            continue
        key = str(k).lower().strip().replace(" ", "_")
        lower_map[key] = v

    def pick(*names: str) -> str:
        for n in names:
            val = lower_map.get(n)
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""

    return {
        "technical": pick("technical", "technical_summary", "legal_summary"),
        "layman": pick("layman", "plain_english", "plainenglish", "simple", "non_technical"),
        "actionable": pick("actionable", "actions", "next_steps", "recommendations"),
    }


def _generate(client: Any, model: str, prompt: str) -> Any:
    """generate_content only accepts model, contents, config — not temperature as a kwarg."""
    from google.genai import types

    return client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=8192,
        ),
    )


def _summarize_one_model(client: Any, model: str, text: str) -> Optional[Dict[str, str]]:
    empty = {"technical": "", "layman": "", "actionable": ""}

    prompt = f"""
Return ONLY valid JSON. Do not use markdown code fences. No text before or after the JSON object.

The JSON must have exactly these keys (lowercase strings):
"technical", "layman", "actionable"

- technical: concise summary for someone with legal training.
- layman: plain English for a non-lawyer.
- actionable: concrete next steps or decisions.

Escape double quotes inside strings. Keep each value under 2000 characters.

DOCUMENT:
{text}
""".strip()

    try:
        response = _generate(client, model, prompt)
    except Exception as e:
        print(f"[WARN] summarize API error ({model}): {e}")
        return None

    raw_text = _model_text(response)
    if not raw_text.strip():
        print(f"[WARN] summarize: empty model text ({model}). {_finish_debug(response)}")
        return None

    try:
        blob = _extract_json_object(raw_text)
        data = json.loads(blob)
    except Exception as e:
        print(f"[WARN] summarize JSON parse failed ({model}): {e}")
        print(f"   (first 400 chars): {raw_text[:400]!r}")
        return None

    out = _normalize_summary_dict(data)
    if not any(out.values()):
        return None
    return out


def summarize_document_with_gemini(
    text: str,
    model: Optional[str] = None,
) -> dict:
    """
    Returns {"technical": str, "layman": str, "actionable": str}.
    On failure or missing deps, returns three empty strings (caller may omit from API response).
    """
    empty = {"technical": "", "layman": "", "actionable": ""}
    if not (text or "").strip():
        return empty

    try:
        from google import genai
    except ImportError:
        print("[WARN] summarize: google-genai not installed")
        return empty

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] summarize: GEMINI_API_KEY not set (check backend/.env)")
        return empty

    from gemini_fallback import normalize_model_id

    primary = normalize_model_id(
        model
        or os.getenv("GEMINI_SUMMARY_MODEL")
        or os.getenv("GEMINI_MODEL")
        or "gemini-2.5-flash",
    ) or "gemini-2.5-flash"
    fallback = normalize_model_id(os.getenv("GEMINI_SUMMARY_MODEL_FALLBACK", "gemini-2.0-flash")) or "gemini-2.0-flash"

    client = genai.Client(
        api_key=api_key,
        http_options={"api_version": "v1"},
    )

    text = text[:12000]

    out = _summarize_one_model(client, primary, text)
    if out:
        return out

    if fallback and fallback != primary:
        out = _summarize_one_model(client, fallback, text)
        if out:
            return out

    return empty
