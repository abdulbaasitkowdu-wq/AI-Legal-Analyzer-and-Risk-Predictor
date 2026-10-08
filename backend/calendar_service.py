import os
import re
import json
from typing import List, Optional
from docx import Document

# -------------------------
# 1) DOCX -> TEXT
# -------------------------
def read_docx_text(docx_path: str) -> str:
    doc = Document(docx_path)
    lines: List[str] = []

    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            lines.append(t)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                t = cell.text.strip()
                if t:
                    lines.append(t)

    return "\n".join(lines)


# -------------------------
# 2) Helpers
# -------------------------
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HHMM_RE = re.compile(r"^\d{2}:\d{2}$")

def _coerce_time_hhmm(t: Optional[str], default_time: str) -> str:
    t = (t or "").strip()

    # "9:00" -> "09:00"
    if re.match(r"^\d{1,2}:\d{2}$", t):
        h, m = t.split(":")
        return f"{int(h):02d}:{int(m):02d}"

    if HHMM_RE.match(t):
        return t

    return default_time

def _coerce_date_iso(d: Optional[str]) -> Optional[str]:
    d = (d or "").strip()
    return d if ISO_DATE_RE.match(d) else None


def _strip_json_fences(s: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if model returns them."""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _response_text_safe(response) -> str:
    """Avoid exceptions when the candidate is blocked or empty (SDK can raise on .text)."""
    try:
        t = getattr(response, "text", None)
        if t:
            return t
    except Exception:
        pass
    try:
        if response.candidates:
            parts = response.candidates[0].content.parts
            return "".join(getattr(p, "text", "") or "" for p in parts)
    except (AttributeError, IndexError, TypeError):
        pass
    return ""


def normalize_events_list(events_raw: List, default_time: str = "09:00") -> List[dict]:
    """
    Turn raw model event dicts into validated, deduplicated rows for the API.
    """
    cleaned: List[dict] = []
    seen = set()

    for ev in events_raw:
        if not isinstance(ev, dict):
            continue

        iso_date = _coerce_date_iso(ev.get("date"))
        if not iso_date:
            continue

        hhmm = _coerce_time_hhmm(ev.get("time"), default_time)
        title = (ev.get("title") or "").strip() or "Important Deadline"

        normalized_title = title.lower().strip()
        key = (normalized_title, iso_date, hhmm)

        if key in seen:
            continue
        seen.add(key)

        cleaned.append(
            {
                "title": title,
                "date": iso_date,
                "time": hhmm,
            }
        )

    return cleaned


# -------------------------
# 3) Gemini Extractor
# -------------------------
def extract_events_with_gemini(
    text: str,
    default_time: str = "09:00",
    model: str = "gemini-2.5-flash",
) -> List[dict]:
    """
    Returns:
      [{"title":"...", "date":"YYYY-MM-DD", "time":"HH:MM"}, ...]
    """
    from gemini_fallback import normalize_model_id

    model = normalize_model_id(model) or "gemini-2.5-flash"

    try:
        from google import genai
    except ImportError:
        print("[WARN] calendar: google-genai not installed; skipping calendar extraction.")
        return []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] calendar: GEMINI_API_KEY not set; skipping calendar extraction.")
        return []

    # reduce tokens / quota usage
    text = text[:12000]

    # Prompt rules adapted from SLIIT archive (minduli / medical-legal analyzer):
    # explicit dates plus relative deadlines resolved to concrete ISO dates.
    prompt = f"""
Return ONLY valid JSON. Do NOT use markdown. Do NOT wrap in ```.

Output format must be EXACTLY one of these:

Option A:
{{"events":[{{"title":"...","date":"YYYY-MM-DD","time":"HH:MM"}}]}}

Option B:
[{{"title":"...","date":"YYYY-MM-DD","time":"HH:MM"}}]

Rules:
- Extract explicit dates AND relative deadlines (e.g. contract signing, effective date, court order date).
- Relative phrases include:
  - within X days
  - after X days
  - before X days
  - no later than X days after [reference event]
- If a relative deadline is found:
  1. Find the related base date in the document (e.g. submission date, decision date, effective date).
  2. Calculate the final calendar date.
  3. Return ONLY the computed final date in YYYY-MM-DD.
- If no base date is available for a relative phrase, omit that event (do not guess).
- Always return final resolved dates only (never output text like "within 30 days" as the date field).
- Also extract explicit or strongly implied deadlines: renewals, expiries, meetings, hearings, follow-ups, admissions, tests.
- If time missing, use "{default_time}".
- date must be YYYY-MM-DD
- time must be HH:MM (24-hour)

DOCUMENT:
{text}
""".strip()

    try:
        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1"},
        )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        raw = _strip_json_fences(_response_text_safe(response))
        if not raw.strip():
            print("[WARN] calendar: empty model response; skipping calendar extraction.")
            return []

        try:
            data = json.loads(raw)
        except Exception:
            print("[WARN] calendar: model did not return valid JSON.")
            print(f"   Raw (first 500 chars): {raw[:500]!r}")
            return []
    except Exception as e:
        print(f"[WARN] calendar extraction failed: {e}")
        return []

    # Support both shapes
    if isinstance(data, list):
        events_raw = data
    else:
        events_raw = data.get("events", [])

    return normalize_events_list(events_raw, default_time=default_time)
