"""
One-time OAuth: creates backend/token.json for Google Calendar sync.
Requires backend/credentials.json (OAuth 2.0 Desktop client from Google Cloud Console).
Run from repo:  python backend/google_oauth_setup.py
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

_backend = Path(__file__).resolve().parent
cred = _backend / "credentials.json"
tok = _backend / "token.json"

if not cred.exists():
    raise SystemExit(f"Place OAuth client JSON at: {cred}")

flow = InstalledAppFlow.from_client_secrets_file(str(cred), SCOPES)
creds = flow.run_local_server(port=1963, prompt='consent')
tok.write_text(creds.to_json(), encoding="utf-8")
print(f"Saved refresh token to {tok}")
