"""Persist Gemini-extracted calendar rows into Events after document analysis."""
from __future__ import annotations

import datetime
import re

import mysql.connector

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def try_save_extracted_events(conn, user_id: int, document_id: int, events: list) -> None:
    if not events:
        return
    cur = conn.cursor()
    try:
        for e in events:
            if not isinstance(e, dict):
                continue
            title = (e.get("title") or "").strip() or "Important Deadline"
            date_iso = (e.get("date") or "").strip()
            time_s = (e.get("time") or "09:00").strip()
            if not _ISO_DATE.match(date_iso):
                continue
            try:
                datetime.date.fromisoformat(date_iso)
            except ValueError:
                continue
            try:
                datetime.datetime.strptime(time_s, "%H:%M")
            except ValueError:
                time_s = "09:00"

            cur.execute(
                """
                SELECT event_id FROM Events
                WHERE user_id=%s AND title=%s AND event_date=%s AND event_time=%s
                LIMIT 1
                """,
                (user_id, title, date_iso, time_s),
            )
            if cur.fetchone():
                continue

            cur.execute(
                """
                INSERT INTO Events (user_id, document_id, title, event_date, event_time, status, google_event_id)
                VALUES (%s, %s, %s, %s, %s, 'draft', NULL)
                """,
                (user_id, document_id, title, date_iso, time_s),
            )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1146:
            return
        print(f"try_save_extracted_events: {err}")
    finally:
        cur.close()
