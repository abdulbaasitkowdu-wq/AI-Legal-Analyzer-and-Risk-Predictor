"""AI chat assistant API (sessions + Gemini) — matches SLIIT assistant project routes."""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional

import mysql.connector
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from database import close_db_connection, get_db_connection
from chat_document_context import fetch_document_context_for_chat
from chat_gemini_service import get_gemini_response

router = APIRouter(tags=["chat"])

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "chat")
os.makedirs(UPLOADS_DIR, exist_ok=True)


def get_db():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        yield conn
    finally:
        close_db_connection(conn)


class RenameSessionRequest(BaseModel):
    title: str


def _table_missing(err: mysql.connector.Error) -> bool:
    return err.errno == 1146


@router.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    document_id: Optional[int] = Form(None),
    user_id: int = Query(1, description="Logged-in user id"),
    db=Depends(get_db),
):
    cur = db.cursor(dictionary=True)
    try:
        if session_id:
            cur.execute(
                "SELECT id FROM chat_sessions WHERE id=%s AND user_id=%s",
                (session_id, user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Session not found")
            sid = session_id
        else:
            title = (message[:30] + "...") if len(message) > 30 else message
            cur.execute(
                "INSERT INTO chat_sessions (user_id, title, created_at) VALUES (%s, %s, %s)",
                (user_id, title, datetime.utcnow()),
            )
            db.commit()
            sid = cur.lastrowid

        cur.execute(
            """
            SELECT message, response, document_path, document_mime_type
            FROM chat_history
            WHERE session_id=%s
            ORDER BY ts ASC, id ASC
            """,
            (sid,),
        )
        rows = cur.fetchall() or []

        history_contents = []
        for h in rows:
            history_contents.append({"role": "user", "parts": [{"text": h["message"]}]})
            history_contents.append({"role": "model", "parts": [{"text": h["response"]}]})

        file_bytes = None
        mime_type = None
        saved_path = None

        if file and file.filename:
            mime_type = file.content_type or "application/octet-stream"
            if "image" not in mime_type and "pdf" not in mime_type:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type. Use an image or PDF.",
                )
            file_bytes = await file.read()
            ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
            fname = f"{uuid.uuid4().hex}.{ext}"
            saved_path = os.path.join(UPLOADS_DIR, fname)
            with open(saved_path, "wb") as f:
                f.write(file_bytes)

        database_context = None
        if document_id is not None:
            ctx, ctx_err = fetch_document_context_for_chat(
                db, user_id=user_id, document_id=document_id
            )
            if ctx_err:
                raise HTTPException(status_code=400, detail=ctx_err)
            database_context = ctx

        try:
            response_text = get_gemini_response(
                history_contents,
                message,
                file_bytes=file_bytes,
                mime_type=mime_type,
                database_context=database_context,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Model error: {e!s}")

        cur2 = db.cursor()
        cur2.execute(
            """
            INSERT INTO chat_history (session_id, message, response, document_path, document_mime_type, ts)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (sid, message, response_text, saved_path, mime_type, datetime.utcnow()),
        )
        db.commit()
        cur2.close()

        return {"response": response_text, "session_id": sid}
    except HTTPException:
        raise
    except mysql.connector.Error as e:
        if _table_missing(e):
            raise HTTPException(
                status_code=503,
                detail="Chat tables missing — run migrations/003_chat_assistant.sql",
            )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.get("/sessions")
def list_sessions(user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT id, title, created_at
            FROM chat_sessions
            WHERE user_id=%s
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            ca = r.get("created_at")
            out.append(
                {
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": ca.isoformat() if hasattr(ca, "isoformat") else str(ca),
                }
            )
        return out
    except mysql.connector.Error as e:
        if _table_missing(e):
            return []
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.put("/sessions/{session_id}")
def rename_session(
    session_id: int,
    body: RenameSessionRequest,
    user_id: int = Query(1),
    db=Depends(get_db),
):
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE chat_sessions SET title=%s WHERE id=%s AND user_id=%s",
            (body.title, session_id, user_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        db.commit()
        return {"status": "renamed", "title": body.title}
    except mysql.connector.Error as e:
        if _table_missing(e):
            raise HTTPException(status_code=503, detail="Chat tables missing")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.get("/history/{session_id}")
def get_history(session_id: int, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT id FROM chat_sessions WHERE id=%s AND user_id=%s",
            (session_id, user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")

        cur.execute(
            """
            SELECT message, response, document_path, ts
            FROM chat_history
            WHERE session_id=%s
            ORDER BY ts ASC, id ASC
            """,
            (session_id,),
        )
        rows = cur.fetchall()
        results = []
        for h in rows:
            path = h.get("document_path")
            has_doc = bool(path)
            doc_name = os.path.basename(path) if path else None
            ts = h.get("ts")
            results.append(
                {
                    "message": h["message"],
                    "response": h["response"],
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    "has_document": has_doc,
                    "document_name": doc_name,
                }
            )
        return results
    except HTTPException:
        raise
    except mysql.connector.Error as e:
        if _table_missing(e):
            return []
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor()
    try:
        cur.execute(
            "DELETE FROM chat_sessions WHERE id=%s AND user_id=%s",
            (session_id, user_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        db.commit()
        return {"status": "deleted"}
    except mysql.connector.Error as e:
        if _table_missing(e):
            raise HTTPException(status_code=503, detail="Chat tables missing")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.delete("/history")
def clear_all_history(user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM chat_sessions WHERE user_id=%s", (user_id,))
        db.commit()
        return {"status": "cleared"}
    except mysql.connector.Error as e:
        if _table_missing(e):
            raise HTTPException(status_code=503, detail="Chat tables missing")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
