"""Google Calendar API helpers — uses backend/credentials.json + backend/token.json."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
DEFAULT_CALENDAR_TZ = "Asia/Colombo"

_BACKEND = Path(__file__).resolve().parent
CREDENTIALS_PATH = _BACKEND / "credentials.json"
TOKEN_PATH = _BACKEND / "token.json"


def format_time(t: Any) -> Optional[str]:
    """Normalize MySQL TIME / timedelta / str to HH:MM."""
    if t is None:
        return None
    if isinstance(t, timedelta):
        secs = int(t.total_seconds()) % 86400
        h, m = secs // 3600, (secs % 3600) // 60
        return f"{h:02d}:{m:02d}"
    if hasattr(t, "hour") and hasattr(t, "minute"):
        return f"{int(t.hour):02d}:{int(t.minute):02d}"
    s = str(t).strip()
    return s[:5] if len(s) >= 5 else s


def get_calendar_service():
    """
    Build Calendar API service using backend/token.json (create via google_oauth_setup.py).
    Refreshes expired access tokens; does not open a browser during API requests.
    """
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"Missing {TOKEN_PATH}. Run once: python backend/google_oauth_setup.py "
            f"(with {CREDENTIALS_PATH} present)."
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise FileNotFoundError(
                "Token invalid or missing refresh. Run: python backend/google_oauth_setup.py"
            )

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _resolve_timezone():
    """
    Windows often has no IANA DB until `tzdata` is installed (pip install tzdata).
    Try CALENDAR_TZ / default / UTC so sync never raises ZoneInfoNotFoundError.
    """
    preferred = os.getenv("CALENDAR_TZ", DEFAULT_CALENDAR_TZ)
    for candidate in (preferred, DEFAULT_CALENDAR_TZ, "UTC"):
        try:
            return ZoneInfo(candidate), candidate
        except ZoneInfoNotFoundError:
            continue
    # If no IANA data (e.g. tzdata not installed), use fixed UTC.
    return timezone.utc, "UTC"


def build_event_body(title: str, date_str: str, time_hhmm: str) -> dict:
    """Single timed event (1 hour) for the selected local calendar date/time."""
    tz, tz_name = _resolve_timezone()

    start = datetime.strptime(f"{date_str} {time_hhmm}", "%Y-%m-%d %H:%M").replace(
        tzinfo=tz
    )
    end = start + timedelta(hours=1)
    return {
        "summary": title,
        "start": {"dateTime": start.isoformat(), "timeZone": tz_name},
        "end": {"dateTime": end.isoformat(), "timeZone": tz_name},
    }
