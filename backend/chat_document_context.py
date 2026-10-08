"""
Build prompt context from stored document analysis (document_insights + documents.analysis_json fallback).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple


def _truncate(s: str, max_len: int) -> str:
    if max_len <= 0:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 24].rstrip() + "\n...[truncated]"


def _parse_json_field(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _analysis_from_document_row(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _parse_json_field(doc.get("analysis_json"))


def fetch_document_context_for_chat(
    conn,
    *,
    user_id: int,
    document_id: int,
) -> Tuple[str, Optional[str]]:
    """
    Returns (context_text, error_message). error_message is None on success.
    context_text is empty string only when error_message is set.
    """
    max_chars = int(os.getenv("CHAT_DOCUMENT_CONTEXT_MAX_CHARS", "32000"))
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT id, filename, analysis_json
            FROM documents
            WHERE id = %s AND user_id = %s
            LIMIT 1
            """,
            (document_id, user_id),
        )
        doc = cur.fetchone()
        if not doc:
            return "", "Document not found or access denied."

        insights: Optional[Dict[str, Any]] = None
        try:
            cur.execute(
                """
                SELECT extracted_text, summaries_json, benchmark_json, calendar_events_json
                FROM document_insights
                WHERE document_id = %s AND user_id = %s
                LIMIT 1
                """,
                (document_id, user_id),
            )
            insights = cur.fetchone()
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] document_insights read skipped: {e}")
            insights = None

        aj = _analysis_from_document_row(doc) or {}

        parts: list[str] = []
        fname = (doc.get("filename") or "document").strip()
        parts.append(f"Document: {fname} (database id={document_id})")

        summaries = None
        if insights and insights.get("summaries_json"):
            summaries = _parse_json_field(insights["summaries_json"])
        if not isinstance(summaries, dict):
            summaries = aj.get("summaries") if isinstance(aj.get("summaries"), dict) else None
        if isinstance(summaries, dict):
            for k in ("technical", "layman", "actionable"):
                v = summaries.get(k)
                if v and str(v).strip():
                    label = k.replace("_", " ").title()
                    parts.append(f"{label}:\n{v}")

        benchmark = None
        if insights and insights.get("benchmark_json"):
            benchmark = _parse_json_field(insights["benchmark_json"])
        if not isinstance(benchmark, dict):
            b = aj.get("benchmark")
            benchmark = b if isinstance(b, dict) else None
        if isinstance(benchmark, dict) and benchmark.get("status") != "error":
            score = benchmark.get("alignment_score")
            if score is not None:
                parts.append(f"Benchmark alignment score: {score}")
            for key in ("reassurance_summary", "document_type_guess"):
                if benchmark.get(key):
                    parts.append(f"{key}: {benchmark[key]}")

        events = None
        if insights and insights.get("calendar_events_json"):
            events = _parse_json_field(insights["calendar_events_json"])
        if not isinstance(events, list):
            ev = aj.get("calendar_events")
            events = ev if isinstance(ev, list) else None
        if isinstance(events, list) and events:
            dumped = json.dumps(events, indent=2)
            parts.append("Extracted calendar / deadline events:\n" + _truncate(dumped, min(12000, max_chars)))

        ext = ""
        if insights and insights.get("extracted_text"):
            ext = str(insights["extracted_text"]).strip()
        if not ext:
            ext = (aj.get("extracted_text") or "").strip()

        if ext:
            parts.append("Extracted document text (may be truncated):\n" + _truncate(ext, max_chars))

        useful = [p for p in parts if p and not p.startswith("Document:")]
        if not useful:
            return "", (
                "No stored analysis text for this document yet. "
                "Upload and analyze it on the analyzer page first."
            )

        body = "\n\n---\n\n".join(parts)
        if len(body) > max_chars + 8000:
            body = _truncate(body, max_chars + 8000)
        return body, None
    finally:
        cur.close()
