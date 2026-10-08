from __future__ import annotations

import os
import tempfile

from google import genai
from google.genai import types

from gemini_fallback import normalize_model_id

NON_MEDICAL_TOKEN = "##NONMEDICAL##"

NON_MEDICAL_RESPONSE = (
    "🚫 **Oops! That doesn't look like a medical document or image.**\n\n"
    "🏥 This assistant is designed **exclusively for medical and health-related documents**, such as:\n\n"
    "• 📋 Lab reports & blood test results\n"
    "• 🩺 Clinical notes & doctor's prescriptions\n"
    "• 🧬 Diagnostic reports & health records\n"
    "• 🩻 Medical scans & imaging reports (X-ray, MRI, CT)\n"
    "• 💊 Medication summaries & discharge papers\n"
    "• 📄 Health certificates & vaccination records\n\n"
    "⚠️ The file you uploaded **does not appear to be a medical document or image**.\n\n"
    "✅ Please upload a **valid medical document or image** and I'll be happy to help you "
    "understand it and answer any health-related questions! 😊"
)
_SYSTEM_INSTRUCTION_LEGAL_DB = (
    "You are an AI assistant helping with questions about the user's analyzed legal or commercial documents.\n"
    "REFERENCE MATERIAL below was loaded from the application's database (stored summaries, benchmark notes, "
    "deadlines, and extracted text). Prefer that material when answering about this document. "
    "If the answer is not supported by the reference material, say so clearly.\n"
    "This is not legal advice; encourage consulting a qualified attorney for legal decisions.\n"
)

_SYSTEM_INSTRUCTION = (
    "You are an AI medical assistant that ONLY helps with medical and health-related documents and questions.\n\n"
    "IMPORTANT RULE — When the user uploads a file:\n"
    "1. First, determine if the uploaded file is a medical or health document.\n"
    "   Medical documents include: lab/blood test reports, doctor prescriptions, clinical notes, "
    "   patient discharge summaries, X-ray/MRI/CT/ultrasound images or reports, vaccination records, "
    "   pathology reports, radiology reports, ECG/EEG results, hospital bills, pharmacy receipts, "
    "   patient health records, medical certificates.\n"
    "2. If the file is NOT a medical document (e.g., university/academic assignment, IT or computer "
    "   science document, engineering report, legal contract, business document, resume, financial "
    "   statement, news article, or ANY non-health content), you MUST reply with EXACTLY this token "
    "   and NOTHING ELSE: ##NONMEDICAL##\n"
    "3. If the file IS a medical document, answer the user's question about it clearly and helpfully.\n\n"
    "When no file is uploaded, answer health and medical questions helpfully. "
    "Always remind users to consult a qualified healthcare professional for medical decisions."
)

_client: genai.Client | None = None


def _client_singleton() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set in the environment.")
        _client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
    return _client


def _build_file_part(client: genai.Client, file_bytes: bytes, mime_type: str):
    """Build a Gemini Part for the given file bytes."""
    if "image" in mime_type:
        return types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
    elif "pdf" in mime_type:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            uploaded = client.files.upload(file=tmp_path)
            return types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type)
        finally:
            os.unlink(tmp_path)
    return None


def get_gemini_response(
    history_contents: list,
    prompt: str,
    file_bytes: bytes | None = None,
    mime_type: str | None = None,
    model: str = "gemini-2.5-flash",
    database_context: str | None = None,
) -> str:
    """
    history_contents: list of {"role": "user"|"model", "parts": [{"text": "..."}, ...]}
    Appends one final user turn with optional file + prompt.
    If database_context is set, the model uses stored document analysis from the DB.
    If a non-medical file is uploaded (no DB context), Gemini may return ##NONMEDICAL## which we swap for
    the rejection message.
    """
    model = normalize_model_id(model) or "gemini-2.5-flash"

    client = _client_singleton()
    contents: list = []

    for msg in history_contents:
        msg_parts = []
        for p in msg.get("parts", []):
            if isinstance(p, str):
                msg_parts.append(types.Part.from_text(text=p))
            elif isinstance(p, dict) and "text" in p:
                msg_parts.append(types.Part.from_text(text=p["text"]))
            else:
                msg_parts.append(p)
        contents.append(types.Content(role=msg.get("role"), parts=msg_parts))

    parts: list = []

    if file_bytes and mime_type:
        file_part = _build_file_part(client, file_bytes, mime_type)
        if file_part:
            parts.append(file_part)

    if database_context and database_context.strip():
        full_prompt = (
            f"{_SYSTEM_INSTRUCTION_LEGAL_DB}\n\n"
            f"REFERENCE MATERIAL (from database):\n{database_context.strip()}\n\n"
            f"---\n\nUser question:\n{prompt}"
        )
    else:
        full_prompt = f"{_SYSTEM_INSTRUCTION}\n\nUser question:\n{prompt}"
    parts.append(types.Part.from_text(text=full_prompt))

    contents.append(types.Content(role="user", parts=parts))

    try:
        response = client.models.generate_content(model=model, contents=contents)
        text = (response.text or "").strip()
        if NON_MEDICAL_TOKEN in text and not (database_context and database_context.strip()):
            print("[Chat] Non-medical document detected — returning rejection message.")
            return NON_MEDICAL_RESPONSE
        return text or "I could not generate a response. Please try again."
    except Exception as e:
        print(f"Gemini chat error: {e}")
        raise