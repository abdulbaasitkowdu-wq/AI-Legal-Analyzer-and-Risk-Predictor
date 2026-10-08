"""REST API for Events + Google Calendar sync."""
from __future__ import annotations

import datetime
from typing import Optional

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, Query
from googleapiclient.errors import HttpError
from pydantic import BaseModel, field_validator

from database import get_db_connection, close_db_connection
from google_calendar_sync import (
    build_event_body,
    format_time,
    get_calendar_service,
)

router = APIRouter(tags=["calendar-events"])


def get_db():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        yield conn
    finally:
        close_db_connection(conn)


def event_exists(
    cur,
    user_id: int,
    title: str,
    event_date: str,
    event_time: str,
    exclude_id: Optional[int] = None,
) -> bool:
    if exclude_id is not None:
        cur.execute(
            """
            SELECT event_id FROM Events
            WHERE user_id=%s AND title=%s AND event_date=%s AND event_time=%s AND event_id != %s
            LIMIT 1
            """,
            (user_id, title, event_date, event_time, exclude_id),
        )
    else:
        cur.execute(
            """
            SELECT event_id FROM Events
            WHERE user_id=%s AND title=%s AND event_date=%s AND event_time=%s
            LIMIT 1
            """,
            (user_id, title, event_date, event_time),
        )
    return cur.fetchone() is not None


def synced_time_conflict(
    cur,
    user_id: int,
    event_date: str,
    event_time: str,
    exclude_id: Optional[int] = None,
) -> Optional[dict]:
    if exclude_id is not None:
        cur.execute(
            """
            SELECT event_id, title FROM Events
            WHERE user_id=%s
              AND status='synced'
              AND event_date=%s
              AND event_time=%s
              AND event_id != %s
            LIMIT 1
            """,
            (user_id, event_date, event_time, exclude_id),
        )
    else:
        cur.execute(
            """
            SELECT event_id, title FROM Events
            WHERE user_id=%s
              AND status='synced'
              AND event_date=%s
              AND event_time=%s
            LIMIT 1
            """,
            (user_id, event_date, event_time),
        )
    return cur.fetchone()


def refresh_deleted_google_events(db, user_id: int) -> list[int]:
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT event_id, google_event_id
            FROM Events
            WHERE user_id=%s AND status='synced' AND google_event_id IS NOT NULL
            """,
            (user_id,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    if not rows:
        return []

    try:
        service = get_calendar_service()
    except FileNotFoundError:
        return []

    deleted_event_ids = []
    for row in rows:
        try:
            google_event = (
                service.events()
                .get(calendarId="primary", eventId=row["google_event_id"])
                .execute()
            )
            if google_event.get("status") == "cancelled":
                deleted_event_ids.append(row["event_id"])
        except HttpError as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status in {404, 410}:
                deleted_event_ids.append(row["event_id"])

    if not deleted_event_ids:
        return []

    cur = db.cursor()
    try:
        placeholders = ", ".join(["%s"] * len(deleted_event_ids))
        cur.execute(
            f"""
            UPDATE Events
            SET status='draft', google_event_id=NULL
            WHERE user_id=%s AND event_id IN ({placeholders})
            """,
            (user_id, *deleted_event_ids),
        )
        db.commit()
    finally:
        cur.close()

    return deleted_event_ids


class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"draft", "synced", "pending", "cancelled"}
        value = v.strip().lower()
        if value not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(sorted(allowed))}")
        return value


class EventCreate(BaseModel):
    title: str
    event_date: str
    event_time: str = "09:00"

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        if len(value) < 3:
            raise ValueError("Title must be at least 3 characters long")
        if len(value) > 150:
            raise ValueError("Title must be less than 150 characters")
        return value

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: str) -> str:
        try:
            datetime.date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("event_time")
    @classmethod
    def validate_event_time(cls, v: str) -> str:
        try:
            datetime.datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM 24-hour format")
        return v


class EventUpdate(BaseModel):
    title: str
    event_date: str
    event_time: str
    status: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        if len(value) < 3:
            raise ValueError("Title must be at least 3 characters long")
        if len(value) > 150:
            raise ValueError("Title must be less than 150 characters")
        return value

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: str) -> str:
        try:
            datetime.date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("event_time")
    @classmethod
    def validate_event_time(cls, v: str) -> str:
        try:
            datetime.datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM 24-hour format")
        return v


@router.get("/events")
def list_events(
    user_id: int = Query(1, description="Owner user id"),
    db=Depends(get_db),
):
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT event_id, user_id, document_id, title, event_date, event_time, status, google_event_id
            FROM Events
            WHERE user_id = %s
            ORDER BY event_date, event_time
            """,
            (user_id,),
        )
        rows = cur.fetchall()

        for r in rows:
            if r.get("event_date"):
                if hasattr(r["event_date"], "isoformat"):
                    r["event_date"] = r["event_date"].isoformat()
                else:
                    r["event_date"] = str(r["event_date"])[:10]

            r["event_time"] = format_time(r.get("event_time"))

        return {"events": rows}
    except mysql.connector.Error as e:
        if e.errno == 1146:
            return {
                "events": [],
                "warning": "Events table missing — run migrations/002_create_events_table.sql",
            }
        raise HTTPException(status_code=500, detail=f"Database read failed: {e}")
    finally:
        cur.close()


@router.post("/events")
def create_event(body: EventCreate, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor()
    try:
        if event_exists(cur, user_id, body.title, body.event_date, body.event_time, exclude_id=None):
            raise HTTPException(
                status_code=400,
                detail="An event with the same title, date, and time already exists",
            )

        cur.execute(
            """
            INSERT INTO Events (user_id, document_id, title, event_date, event_time, status, google_event_id)
            VALUES (%s, NULL, %s, %s, %s, 'draft', NULL)
            """,
            (user_id, body.title, body.event_date, body.event_time),
        )
        db.commit()
        new_id = cur.lastrowid
        return {"ok": True, "event_id": new_id}
    except HTTPException:
        raise
    except mysql.connector.Error as e:
        if e.errno == 1146:
            raise HTTPException(
                status_code=503,
                detail="Events table missing — run migrations/002_create_events_table.sql",
            )
        raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")
    finally:
        cur.close()


@router.post("/events/refresh-google-status")
def refresh_google_status(user_id: int = Query(1), db=Depends(get_db)):
    try:
        changed_event_ids = refresh_deleted_google_events(db, user_id)
        return {
            "ok": True,
            "changed_event_ids": changed_event_ids,
            "status": "draft",
        }
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")


@router.put("/events/{event_id}/status")
def update_status(event_id: int, body: StatusUpdate, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT event_id FROM Events WHERE event_id=%s AND user_id=%s",
            (event_id, user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Event not found")

        cur.execute(
            "UPDATE Events SET status=%s WHERE event_id=%s AND user_id=%s",
            (body.status, event_id, user_id),
        )
        db.commit()
        return {"ok": True, "event_id": event_id, "new_status": body.status}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")
    finally:
        cur.close()


@router.post("/events/{event_id}/sync")
def sync_event_to_google(event_id: int, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT event_id, title, event_date, event_time, google_event_id
            FROM Events
            WHERE event_id=%s AND user_id=%s
            """,
            (event_id, user_id),
        )
        ev = cur.fetchone()

        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")

        title = ev["title"]
        date_str = ev["event_date"].isoformat() if ev["event_date"] else None
        time_hhmm = format_time(ev["event_time"]) or "09:00"
        google_event_id = ev.get("google_event_id")

        conflict = synced_time_conflict(
            cur,
            user_id,
            date_str,
            time_hhmm,
            exclude_id=event_id,
        )
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Another synced event already exists on this date and time. "
                    "Change the time before syncing this deadline."
                ),
            )

        try:
            service = get_calendar_service()
        except FileNotFoundError as e:
            raise HTTPException(status_code=503, detail=str(e))

        body = build_event_body(title, date_str, time_hhmm)

        if google_event_id:
            updated = (
                service.events()
                .patch(calendarId="primary", eventId=google_event_id, body=body)
                .execute()
            )
            g_id = updated["id"]
        else:
            created = (
                service.events()
                .insert(calendarId="primary", body=body)
                .execute()
            )
            g_id = created["id"]

        cur2 = db.cursor()
        cur2.execute(
            """
            UPDATE Events
            SET google_event_id=%s, status='synced'
            WHERE event_id=%s AND user_id=%s
            """,
            (g_id, event_id, user_id),
        )
        db.commit()
        cur2.close()

        return {
            "ok": True,
            "event_id": event_id,
            "google_event_id": g_id,
            "status": "synced",
        }

    except HttpError as e:
        raise HTTPException(status_code=500, detail=f"Google Calendar API error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {repr(e)}")
    finally:
        cur.close()


@router.post("/events/{event_id}/unsync")
def unsync_event(event_id: int, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT google_event_id FROM Events WHERE event_id=%s AND user_id=%s",
            (event_id, user_id),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        google_event_id = row.get("google_event_id")

        if google_event_id:
            try:
                service = get_calendar_service()
                service.events().delete(
                    calendarId="primary", eventId=google_event_id
                ).execute()
            except (HttpError, FileNotFoundError):
                pass

        cur2 = db.cursor()
        cur2.execute(
            """
            UPDATE Events
            SET google_event_id=NULL, status='draft'
            WHERE event_id=%s AND user_id=%s
            """,
            (event_id, user_id),
        )
        db.commit()
        cur2.close()

        return {"ok": True, "event_id": event_id, "unsynced": True}

    finally:
        cur.close()


@router.put("/events/{event_id}")
def update_event(event_id: int, body: EventUpdate, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT event_id, google_event_id FROM Events WHERE event_id=%s AND user_id=%s",
            (event_id, user_id),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        conflict = synced_time_conflict(
            cur,
            user_id,
            body.event_date,
            body.event_time,
            exclude_id=event_id,
        )

        google_event_id = row.get("google_event_id")
        keep_synced = bool(google_event_id) and conflict is None

        cur2 = db.cursor()
        if google_event_id and conflict:
            cur2.execute(
                """
                UPDATE Events
                SET title=%s, event_date=%s, event_time=%s, status='draft', google_event_id=NULL
                WHERE event_id=%s AND user_id=%s
                """,
                (body.title, body.event_date, body.event_time, event_id, user_id),
            )
        else:
            cur2.execute(
                """
                UPDATE Events
                SET title=%s, event_date=%s, event_time=%s
                WHERE event_id=%s AND user_id=%s
                """,
                (body.title, body.event_date, body.event_time, event_id, user_id),
            )
        db.commit()
        cur2.close()

        if google_event_id and conflict:
            try:
                service = get_calendar_service()
                service.events().delete(
                    calendarId="primary",
                    eventId=google_event_id,
                ).execute()
            except (HttpError, FileNotFoundError):
                pass
        elif google_event_id:
            try:
                service = get_calendar_service()
                g_body = build_event_body(body.title, body.event_date, body.event_time)
                service.events().patch(
                    calendarId="primary",
                    eventId=google_event_id,
                    body=g_body,
                ).execute()
            except FileNotFoundError as e:
                raise HTTPException(status_code=503, detail=str(e))

        return {
            "ok": True,
            "event_id": event_id,
            "updated": True,
            "synced_updated": keep_synced,
            "unsynced_due_to_conflict": bool(google_event_id and conflict),
            "status": (
                "synced"
                if keep_synced
                else ("draft" if (google_event_id and conflict) else None)
            ),
        }

    except HttpError as e:
        raise HTTPException(status_code=500, detail=f"Google update failed: {e}")
    except HTTPException:
        raise
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")
    finally:
        cur.close()


@router.delete("/events/{event_id}")
def delete_event(event_id: int, user_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT google_event_id FROM Events WHERE event_id=%s AND user_id=%s",
            (event_id, user_id),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        google_event_id = row.get("google_event_id")

        if google_event_id:
            try:
                service = get_calendar_service()
                service.events().delete(
                    calendarId="primary", eventId=google_event_id
                ).execute()
            except (HttpError, FileNotFoundError):
                pass

        cur2 = db.cursor()
        cur2.execute(
            "DELETE FROM Events WHERE event_id=%s AND user_id=%s",
            (event_id, user_id),
        )
        db.commit()
        cur2.close()

        return {
            "ok": True,
            "deleted": True,
            "event_id": event_id,
            "google_deleted": bool(google_event_id),
        }

    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database delete failed: {e}")
    finally:
        cur.close()
