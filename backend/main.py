from pathlib import Path

from dotenv import load_dotenv
import mysql.connector
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import tempfile
import os
import json
import re
from datetime import datetime, timedelta

# Load backend/.env before any route uses os.getenv (GEMINI_API_KEY, MySQL, etc.)
load_dotenv(Path(__file__).resolve().parent / ".env")

# First-time DB bootstrap: default admin (override via .env in production)
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@gmail.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")
DEFAULT_ADMIN_NAME = os.getenv("DEFAULT_ADMIN_NAME", "Admin")

from database import get_db_connection, close_db_connection
from calendar_events_routes import router as calendar_events_router
from calendar_events_db import try_save_extracted_events
from chat_routes import router as chat_router

app = FastAPI(title="AI Legal Analyzer API")
app.include_router(calendar_events_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

# Configure CORS so your React frontend can talk to this FastAPI backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_BACKEND_DIR = Path(__file__).resolve().parent
_UPLOADS_DIR = _BACKEND_DIR / "uploads"
_AVATARS_DIR = _UPLOADS_DIR / "avatars"
_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")


def _public_user_from_row(user: dict) -> dict:
    """Shape user for API responses (login, profile)."""
    name = (user.get("name") or "").strip() or "User"
    parts = name.split()
    initials = "".join([p[0] for p in parts[:2]]).upper() if parts else "?"
    out = {
        "id": user["id"],
        "name": user.get("name"),
        "email": user.get("email"),
        "initials": initials,
        "role": user.get("role"),
    }
    av = user.get("avatar_url")
    if av:
        out["avatar_url"] = av
    return out


def ensure_default_admin() -> None:
    """Create a default Admin user if none exists with DEFAULT_ADMIN_EMAIL (plain password, matches /api/login)."""
    conn = get_db_connection()
    if conn is None:
        print("[STARTUP] Skipping default admin seed: database unavailable.")
        return
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (DEFAULT_ADMIN_EMAIL,))
        if cur.fetchone():
            return
        cur.close()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, password, role, status) VALUES (%s, %s, %s, %s, %s)",
            (DEFAULT_ADMIN_NAME, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, "Admin", "Active"),
        )
        conn.commit()
        print(
            f"[STARTUP] Created default admin ({DEFAULT_ADMIN_EMAIL}). "
            "Set DEFAULT_ADMIN_* in backend/.env or change the password after first login."
        )
    except Exception as e:
        print(f"[STARTUP] Default admin seed failed: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        close_db_connection(conn)


@app.on_event("startup")
def _startup_ensure_default_admin() -> None:
    ensure_default_admin()


# Dependency to get the DB connection for individual API routes
def get_db():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        yield conn
    finally:
        close_db_connection(conn)

# --- Data Models (What React sends to FastAPI) ---
class LoginRequest(BaseModel):
    email: str
    password: str
    is_admin: bool

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


def _is_strong_password(password: str) -> bool:
    """
    Minimum strength rule for account creation:
    at least 1 uppercase letter, 1 lowercase letter, and 1 digit.
    """
    if not isinstance(password, str):
        return False
    return bool(
        re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
    )

class BenchmarkRequest(BaseModel):
    document_id: Optional[int] = None
    text: Optional[str] = None
    filename: Optional[str] = None
    user_id: int = 1

def _benchmark_response_contract(benchmark_payload):
    payload = benchmark_payload if isinstance(benchmark_payload, dict) else {}
    status = "success" if payload.get("status") == "success" else "error"
    error_code = payload.get("error_code")
    message = payload.get("confidence_note") if status == "error" else None
    return {
        "status": status,
        "benchmark": payload if payload else None,
        "error": None
        if status == "success"
        else {
            "code": error_code or "BENCHMARK_UNAVAILABLE",
            "message": message or "Benchmarking is currently unavailable.",
            "retryable": bool(payload.get("retryable")),
        },
    }

# --- API Endpoints ---

@app.get("/api/status")
def read_status():
    return {"status": "success", "message": "FastAPI server is running perfectly!"}

@app.get("/api/admin/stats")
def get_admin_stats(db = Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)
        
        # Get total registered users
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        # Get active users (users with status 'Active')
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE status = 'Active'")
        active_users = cursor.fetchone()['active']
        
        # Get total documents
        cursor.execute("SELECT COUNT(*) as total_docs FROM documents")
        total_docs = cursor.fetchone()['total_docs']
        
        # --- NEW: Generate Weekly Chart Data ---
        today = datetime.now()
        weekly_data = []
        
        # Loop backwards through the last 7 days
        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            day_name = target_date.strftime("%a") # Gets 'Mon', 'Tue', etc.
            
            # Count documents uploaded on this specific date
            cursor.execute("SELECT COUNT(*) as count FROM documents WHERE DATE(uploaded_at) = DATE(%s)", (target_date,))
            day_count = cursor.fetchone()['count']
            
            weekly_data.append({
                "name": day_name,
                "docs": day_count
            })
            
        cursor.close()
        
        return {
            "totalUsers": total_users,
            "activeSessions": active_users,
            "totalDocuments": total_docs,
            "avgRiskScore": "0/100", # Placeholder until AI runs
            "weeklyData": weekly_data  # Send the real chart data to React!
        }
    except Exception as e:
        # Return mock data if database is unavailable
        print(f"Database error in admin stats: {e}")
        return {
            "totalUsers": 5,
            "activeSessions": 3,
            "totalDocuments": 12,
            "avgRiskScore": "42/100",
            "weeklyData": [
                {"name": "Mon", "docs": 2},
                {"name": "Tue", "docs": 3},
                {"name": "Wed", "docs": 1},
                {"name": "Thu", "docs": 0},
                {"name": "Fri", "docs": 4},
                {"name": "Sat", "docs": 2},
                {"name": "Sun", "docs": 0}
            ]
        }

@app.get("/api/admin/users")
def get_all_users(db = Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)
        
        # Fetch all users, formatting the dates cleanly
        cursor.execute("""
            SELECT id, name, email, role, status, 
            DATE_FORMAT(last_active, '%b %d, %Y') as last_active 
            FROM users ORDER BY id DESC
        """)
        users = cursor.fetchall()
        
        # Add initials and a temporary document count for the frontend
        for user in users:
            user['initials'] = "".join([n[0] for n in user['name'].split()][:2]).upper()
            
            # Count documents for this specific user
            cursor.execute("SELECT COUNT(*) as doc_count FROM documents WHERE user_id = %s", (user['id'],))
            user['docs'] = cursor.fetchone()['doc_count']
            
        cursor.close()
        
        return {"users": users}
    except Exception as e:

        # Return mock data if database is unavailable
        print(f"Database error in get users: {e}")
        return {"users": [
          {"id": 1, "name": "John Doe", "email": "john@example.com", "role": "User", "status": "Active", "last_active": "Mar 20, 2026", "initials": "JD", "docs": 3},
           {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "role": "Admin", "status": "Active", "last_active": "Mar 20, 2026", "initials": "JS", "docs": 5}
        ]}


def _admin_delete_user_cascade(cursor, user_id: int) -> None:
    """Remove related rows then the user. Ignores missing optional tables (errno 1146)."""
    cursor.execute("SELECT id FROM chat_sessions WHERE user_id = %s", (user_id,))
    session_ids = [row[0] for row in cursor.fetchall()]
    for sid in session_ids:
        try:
            cursor.execute("DELETE FROM chat_history WHERE session_id = %s", (sid,))
        except mysql.connector.Error as e:
            if e.errno != 1146:
                raise
    try:
        cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
    except mysql.connector.Error as e:
        if e.errno != 1146:
            raise

    cursor.execute("SELECT id FROM documents WHERE user_id = %s", (user_id,))
    doc_ids = [row[0] for row in cursor.fetchall()]
    for did in doc_ids:
        try:
            cursor.execute("DELETE FROM document_insights WHERE document_id = %s", (did,))
        except mysql.connector.Error as e:
            if e.errno != 1146:
                raise
    try:
        cursor.execute("DELETE FROM documents WHERE user_id = %s", (user_id,))
    except mysql.connector.Error as e:
        if e.errno != 1146:
            raise
    try:
        cursor.execute("DELETE FROM Events WHERE user_id = %s", (user_id,))
    except mysql.connector.Error as e:
        if e.errno != 1146:
            raise
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))


class AdminUserUpdateRequest(BaseModel):
    status: Optional[str] = None
    role: Optional[str] = None


@app.patch("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, body: AdminUserUpdateRequest, db=Depends(get_db)):
    """Update user status (Active/Suspended) or role (User/Admin/Super Admin)."""
    allowed_status = {"Active", "Suspended"}
    allowed_roles = {"User", "Admin", "Super Admin"}
    if body.status is None and body.role is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    if body.status is not None and body.status not in allowed_status:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(sorted(allowed_status))}")
    if body.role is not None and body.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"role must be one of: {', '.join(sorted(allowed_roles))}")

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, email, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        email = (user.get("email") or "").lower()
        if email == DEFAULT_ADMIN_EMAIL.lower():
            if body.role is not None and body.role == "User":
                raise HTTPException(status_code=403, detail="Cannot demote the default admin account")
            if body.status is not None and body.status == "Suspended":
                raise HTTPException(status_code=403, detail="Cannot suspend the default admin account")

        if body.role is not None and "Admin" in (user.get("role") or "") and body.role == "User":
            cursor.execute(
                "SELECT COUNT(*) as c FROM users WHERE role LIKE %s OR role LIKE %s",
                ("%Admin%", "%Super Admin%"),
            )
            adminish = cursor.fetchone()["c"]
            if adminish <= 1:
                raise HTTPException(status_code=403, detail="Cannot demote the last admin user")

        sets, params = [], []
        if body.status is not None:
            sets.append("status = %s")
            params.append(body.status)
        if body.role is not None:
            sets.append("role = %s")
            params.append(body.role)
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = %s", tuple(params))
        db.commit()
        return {"ok": True, "message": "User updated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] admin_update_user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, db=Depends(get_db)):
    """Delete a user and dependent rows (documents, events, chat, etc.)."""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, email, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        email = (user.get("email") or "").lower()
        if email == DEFAULT_ADMIN_EMAIL.lower():
            raise HTTPException(status_code=403, detail="Cannot delete the default admin account")
        if "Admin" in (user.get("role") or ""):
            cursor.execute(
                "SELECT COUNT(*) as c FROM users WHERE role LIKE %s OR role LIKE %s",
                ("%Admin%", "%Super Admin%"),
            )
            if cursor.fetchone()["c"] <= 1:
                raise HTTPException(status_code=403, detail="Cannot delete the last admin user")
    except HTTPException:
        cursor.close()
        raise

    cursor.close()
    cursor = db.cursor()
    try:
        _admin_delete_user_cascade(cursor, user_id)
        db.commit()
        return {"ok": True, "message": "User deleted"}
    except Exception as e:
        db.rollback()
        print(f"[ERROR] admin_delete_user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()


@app.get("/api/admin/users/{user_id}/activity")
def admin_user_activity(user_id: int, db=Depends(get_db)):
    """Recent uploads and chat usage for a standard user (role must be exactly User)."""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, name, email, role, status,
                   DATE_FORMAT(last_active, '%b %d, %Y') as last_active
            FROM users WHERE id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        if (row.get("role") or "") != "User":
            raise HTTPException(
                status_code=400,
                detail="Activity detail is only available for users with role User",
            )

        cursor.execute("SELECT COUNT(*) as c FROM documents WHERE user_id = %s", (user_id,))
        documents_count = cursor.fetchone()["c"]

        cursor.execute(
            """
            SELECT id, filename,
                   DATE_FORMAT(uploaded_at, '%b %d, %Y %h:%i %p') as uploaded_at,
                   risk_level, clauses_detected
            FROM documents
            WHERE user_id = %s
            ORDER BY uploaded_at DESC
            LIMIT 25
            """,
            (user_id,),
        )
        recent_documents = cursor.fetchall()

        chat_sessions_count = 0
        try:
            cursor.execute("SELECT COUNT(*) as c FROM chat_sessions WHERE user_id = %s", (user_id,))
            chat_sessions_count = cursor.fetchone()["c"]
        except mysql.connector.Error as e:
            if e.errno != 1146:
                raise

        return {
            "user": row,
            "documents_count": documents_count,
            "chat_sessions_count": chat_sessions_count,
            "recent_documents": recent_documents,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] admin_user_activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()


@app.get("/api/admin/analytics")
def get_platform_analytics(db = Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)
        
        # 1. Timeline Data (Last 6 Months)
        today = datetime.now()
        timeline_data = []
        
        for i in range(5, -1, -1):
            # Calculate the target month and year safely
            target_month = (today.month - i - 1) % 12 + 1
            target_year = today.year + ((today.month - i - 1) // 12)
            month_name = datetime(target_year, target_month, 1).strftime("%b")
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM documents 
                WHERE MONTH(uploaded_at) = %s AND YEAR(uploaded_at) = %s
            """, (target_month, target_year))
            
            count = cursor.fetchone()['count']
            timeline_data.append({"name": month_name, "docs": count})

        # Get total clauses detected across all documents
        cursor.execute("SELECT SUM(clauses_detected) as total FROM documents")
        result = cursor.fetchone()
        total_clauses = int(result['total']) if result and result['total'] else 0

        print(f"[Analytics] Total clauses = {total_clauses}")

        # Since we don't store exact clause names in the DB yet, we dynamically 
        # distribute the real total count across common legal categories
        clause_data = [
            { "name": 'Confidentiality', "count": int(total_clauses * 0.35) or 1 },
            { "name": 'Indemnification', "count": int(total_clauses * 0.25) or 1 },
            { "name": 'Termination', "count": int(total_clauses * 0.20) or 1 },
            { "name": 'Liability Limit', "count": int(total_clauses * 0.15) or 1 },
            { "name": 'Non-Compete', "count": int(total_clauses * 0.05) or 1 }
        ]

        risk_colors = {"Low": "#22c55e", "Medium": "#eab308", "High": "#ef4444"}
        cursor.execute(
            """
            SELECT risk_level, COUNT(*) AS cnt FROM documents
            WHERE risk_level IS NOT NULL AND risk_level != ''
            GROUP BY risk_level
            """
        )
        risk_rows = cursor.fetchall()
        by_level = {row["risk_level"]: row["cnt"] for row in risk_rows}
        risk_data = []
        for level in ("Low", "Medium", "High"):
            risk_data.append({
                "name": level,
                "value": int(by_level.get(level, 0)),
                "color": risk_colors[level],
            })

        print(f"[Analytics] Timeline={len(timeline_data)}, Risk={len(risk_data)}, Clauses={len(clause_data)}")

        cursor.close()
        return {
            "timelineData": timeline_data,
            "riskData": risk_data,
            "clauseData": clause_data
        }
    except Exception as e:
        print(f"[ERROR] Analytics error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error fetching analytics data")

@app.post("/api/login")
def login_user(request: LoginRequest, db = Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)
        
        # Query the database for the user by email and password
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (request.email, request.password))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            print(f"[AUTH] Failed login attempt for {request.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if str(user.get("status") or "").strip() == "Suspended":
            raise HTTPException(status_code=403, detail="This account has been suspended.")
        
        # Check if they are trying to log into the correct portal
        is_actually_admin = "Admin" in user['role']
        if request.is_admin and not is_actually_admin:
            raise HTTPException(status_code=403, detail="Access denied. You do not have admin privileges.")

        print(f"[AUTH] User logged in: {request.email}")

        # Return the real user data
        return {
            "message": "Login successful",
            "user": _public_user_from_row(user),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.post("/api/register")
def register_user(request: RegisterRequest, db = Depends(get_db)):
    try:
        cursor = db.cursor()
        if not _is_strong_password(request.password):
            raise HTTPException(
                status_code=400,
                detail="Password must include at least 1 uppercase letter, 1 lowercase letter, and 1 number.",
            )
        
        # Insert the new user into the database with plain-text password
        sql = "INSERT INTO users (name, email, password, role, status) VALUES (%s, %s, %s, 'User', 'Active')"
        cursor.execute(sql, (request.name, request.email, request.password))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        
        print(f"[AUTH] New user registered: {request.email} (ID: {new_id})")
        
        return {
            "message": "Registration successful",
            "user": _public_user_from_row(
                {
                    "id": new_id,
                    "name": request.name,
                    "email": request.email,
                    "role": "User",
                    "avatar_url": None,
                }
            ),
        }
    except HTTPException:
        raise
    except Exception as err:
        cursor.close()
        # Check for duplicate email (MySQL error 1062)
        if "Duplicate entry" in str(err):
            raise HTTPException(status_code=400, detail="Email already exists")
        print(f"[ERROR] Registration error: {err}")
        raise HTTPException(status_code=500, detail=f"Registration error: {str(err)}")


@app.put("/api/profile")
async def update_profile(
    user_id: int = Query(..., description="Logged-in user id"),
    name: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    db=Depends(get_db),
):
    """Update display name and/or profile photo (stored under /uploads/avatars/)."""
    has_file = bool(avatar and avatar.filename)
    if not has_file and not (name or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Provide a new name and/or an image file (max 2MB).",
        )

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, email, role, avatar_url FROM users WHERE id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
    except mysql.connector.Error as e:
        if e.errno == 1054:
            raise HTTPException(
                status_code=503,
                detail="Run migration backend/migrations/006_add_user_avatar_url.sql (adds avatar_url column).",
            )
        raise
    finally:
        cursor.close()

    new_name = (name or "").strip() if (name or "").strip() else row["name"]
    new_avatar_url = row.get("avatar_url")

    if has_file:
        contents = await avatar.read()
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image must be 2MB or smaller.")
        ext = ".jpg"
        ct = (avatar.content_type or "").lower()
        if "png" in ct:
            ext = ".png"
        elif "webp" in ct:
            ext = ".webp"
        elif "gif" in ct:
            ext = ".gif"
        elif "jpeg" in ct or "jpg" in ct:
            ext = ".jpg"
        for p in _AVATARS_DIR.glob(f"{user_id}.*"):
            try:
                p.unlink()
            except OSError:
                pass
        dest = _AVATARS_DIR / f"{user_id}{ext}"
        with open(dest, "wb") as f:
            f.write(contents)
        new_avatar_url = f"/uploads/avatars/{user_id}{ext}"

    cur2 = db.cursor()
    try:
        cur2.execute(
            "UPDATE users SET name = %s, avatar_url = %s WHERE id = %s",
            (new_name, new_avatar_url, user_id),
        )
        db.commit()
    except mysql.connector.Error as e:
        db.rollback()
        if e.errno == 1054:
            raise HTTPException(
                status_code=503,
                detail="Run migration backend/migrations/006_add_user_avatar_url.sql (adds avatar_url column).",
            )
        raise
    finally:
        cur2.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    updated = cursor.fetchone()
    cursor.close()
    return {"user": _public_user_from_row(updated)}


# --- Password Management Endpoints ---

class ChangePasswordRequest(BaseModel):
    user_id: int
    old_password: str
    new_password: str

@app.post("/api/change-password")
def change_password(request: ChangePasswordRequest, db = Depends(get_db)):
    """Allow users to change their password."""
    try:
        cursor = db.cursor(dictionary=True)
        
        # Get user
        cursor.execute("SELECT * FROM users WHERE id = %s", (request.user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify old password
        if request.old_password != user['password']:
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Update with new password
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (request.new_password, request.user_id))
        db.commit()
        cursor.close()
        
        print(f"[AUTH] User {user['email']} changed password")
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Change password error: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/admin/hash-existing-passwords")
def hash_existing_passwords(db = Depends(get_db)):
    """Admin endpoint to convert plain-text passwords to hashed ones (RUN ONCE)."""
    try:
        cursor = db.cursor(dictionary=True)
        
        # Get all users with plain-text passwords (not starting with $2b$ which is bcrypt)
        cursor.execute("SELECT id, email, password FROM users WHERE password NOT LIKE '$2b$%'")
        users = cursor.fetchall()
        
        if not users:
            cursor.close()
            return {"message": "No plain-text passwords found. All passwords are already hashed."}
        
        updated_count = 0
        errors = []
        
        for user in users:
            try:
                # Hash the plain-text password
                hashed_password = hash_password(user['password'])
                
                # Update the database
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user['id']))
                updated_count += 1
                print(f"[MIGRATION] Hashed password for user {user['email']} (ID: {user['id']})")
            except Exception as user_err:
                errors.append(f"Error hashing password for {user['email']}: {str(user_err)}")
                print(f"[ERROR] Failed to hash password for {user['email']}: {user_err}")
        
        db.commit()
        cursor.close()
        
        result = {
            "message": f"Password migration completed",
            "total_users": len(users),
            "updated": updated_count,
            "errors": errors
        }
        
        print(f"[MIGRATION] Hashed passwords for {updated_count} users")
        return result
        
    except Exception as e:
        print(f"[ERROR] Password migration error: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# --- Calendar Sync Endpoints ---

@app.post("/api/calendar/extract")
async def extract_calendar_events(
    file: UploadFile = File(None),
    document_id: Optional[int] = Form(None),
    user_id: int = Form(1),
    db = Depends(get_db),
):
    """
    Receives a DOCX file, extracts text, and uses Gemini to find calendar events.
    """
    from calendar_service import extract_events_with_gemini, read_docx_text, normalize_events_list

    # Preferred path: read already-saved events from DB (document_insights / analysis_json).
    if document_id is not None:
        cur = db.cursor(dictionary=True)
        try:
            cur.execute(
                """
                SELECT calendar_events_json
                FROM document_insights
                WHERE document_id = %s AND user_id = %s
                LIMIT 1
                """,
                (document_id, user_id),
            )
            row = cur.fetchone()
            if row and row.get("calendar_events_json"):
                try:
                    raw_events = json.loads(row["calendar_events_json"])
                    return {"status": "success", "events": normalize_events_list(raw_events)}
                except (TypeError, ValueError):
                    pass

            cur.execute(
                """
                SELECT analysis_json
                FROM documents
                WHERE id = %s AND user_id = %s
                LIMIT 1
                """,
                (document_id, user_id),
            )
            doc = cur.fetchone()
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            payload = _normalize_stored_analysis_payload(doc.get("analysis_json"))
            events = payload.get("calendar_events") if payload else []
            return {"status": "success", "events": normalize_events_list(events or [])}
        finally:
            cur.close()

    # Backward-compatible path for direct file extraction.
    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Provide document_id to read from database, or upload a .docx file.",
        )
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".docx") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        text = read_docx_text(temp_file_path)
        events = extract_events_with_gemini(text)
        return {"status": "success", "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting events: {str(e)}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# --- User documents (dashboard) ---

def _normalize_stored_analysis_payload(parsed):
    """
    Stored JSON should match POST /api/documents/analyze response body (what the UI shows after upload).
    Legacy rows only had { analysis, calendar_events } — normalize to the same shape.
    """
    if not parsed:
        return None
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            return None
    if (
        isinstance(parsed, dict)
        and parsed.get("status") == "success"
        and "analysis" in parsed
        and "calendar_events" in parsed
    ):
        return parsed
    if isinstance(parsed, dict) and "analysis" in parsed and "calendar_events" in parsed:
        return {
            "status": "success",
            "message": "Analysis Complete",
            "document_id": parsed.get("document_id"),
            "filename": parsed.get("filename"),
            "analysis": parsed["analysis"],
            "calendar_events": parsed.get("calendar_events") or [],
            "summaries": parsed.get("summaries"),
            "pdf_text_source": parsed.get("pdf_text_source"),
            "extracted_text": parsed.get("extracted_text"),
            "benchmark": parsed.get("benchmark"),
            "benchmark_status": parsed.get("benchmark_status"),
            "benchmark_error": parsed.get("benchmark_error"),
            "benchmark_schema_version": parsed.get("benchmark_schema_version"),
        }
    return None


def _save_document_insights(
    db,
    *,
    document_id: int,
    user_id: int,
    extracted_text: str,
    summaries,
    benchmark,
    calendar_events,
    benchmark_status: str,
    benchmark_error,
    schema_version: str = "1.1",
):
    """
    Best-effort dual-write to dedicated table.
    If migration has not run yet, this function is non-fatal.
    """
    cur = db.cursor()
    try:
        cur.execute(
            """
            INSERT INTO document_insights (
                document_id, user_id, extracted_text, summaries_json, benchmark_json,
                calendar_events_json, benchmark_status, benchmark_error_json, schema_version
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                extracted_text = VALUES(extracted_text),
                summaries_json = VALUES(summaries_json),
                benchmark_json = VALUES(benchmark_json),
                calendar_events_json = VALUES(calendar_events_json),
                benchmark_status = VALUES(benchmark_status),
                benchmark_error_json = VALUES(benchmark_error_json),
                schema_version = VALUES(schema_version)
            """,
            (
                document_id,
                user_id,
                extracted_text,
                json.dumps(summaries, default=str) if summaries is not None else None,
                json.dumps(benchmark, default=str) if benchmark is not None else None,
                json.dumps(calendar_events, default=str) if calendar_events is not None else None,
                benchmark_status,
                json.dumps(benchmark_error, default=str) if benchmark_error is not None else None,
                schema_version,
            ),
        )
        db.commit()
    except Exception as e:
        print(f"[WARN] document_insights write skipped: {e}")
    finally:
        cur.close()


def _load_document_insights_text(db, *, document_id: int, user_id: int):
    """Read extracted text from dedicated table; returns None if unavailable."""
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT extracted_text
            FROM document_insights
            WHERE document_id = %s AND user_id = %s
            LIMIT 1
            """,
            (document_id, user_id),
        )
        row = cur.fetchone()
        return row.get("extracted_text") if row else None
    except Exception:
        return None
    finally:
        cur.close()

@app.post("/api/documents/benchmark")
def post_benchmark_document(body: BenchmarkRequest, db = Depends(get_db)):
    from benchmark_service import benchmark_document_with_gemini

    text = None
    filename = body.filename or ""

    if body.document_id is not None:
        try:
            cursor = db.cursor(dictionary=True)
            try:
                cursor.execute(
                    """
                    SELECT id, filename, analysis_json
                    FROM documents
                    WHERE id = %s AND user_id = %s
                    LIMIT 1
                    """,
                    (body.document_id, body.user_id),
                )
            except Exception:
                cursor.execute(
                    """
                    SELECT id, filename
                    FROM documents
                    WHERE id = %s AND user_id = %s
                    LIMIT 1
                    """,
                    (body.document_id, body.user_id),
                )
            row = cursor.fetchone()
            cursor.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        if not row:
            raise HTTPException(status_code=404, detail="Document not found")

        filename = row.get("filename") or filename
        text = _load_document_insights_text(
            db,
            document_id=body.document_id,
            user_id=body.user_id,
        )
        raw = row.get("analysis_json")
        if not text:
            parsed = json.loads(raw) if raw else None
            norm = _normalize_stored_analysis_payload(parsed)
            if norm:
                text = norm.get("extracted_text")
    else:
        text = body.text

    if not text or not str(text).strip():
        raise HTTPException(
            status_code=400,
            detail="No document text available. Run a new analysis on this file to store text for benchmarking.",
        )

    max_chars = int(os.getenv("BENCHMARK_MAX_INPUT_CHARS", "14000"))
    text = str(text)
    if len(text) > max_chars:
        text = text[:max_chars]

    benchmark = benchmark_document_with_gemini(text, filename)
    return _benchmark_response_contract(benchmark)


def _rows_to_document_list(rows, include_json_column: bool):
    out = []
    for r in rows:
        item = dict(r)
        raw = None
        if include_json_column:
            raw = item.pop("analysis_json", None)
        result = _normalize_stored_analysis_payload(
            json.loads(raw) if raw else None
        )
        if result:
            if result.get("document_id") is None:
                result["document_id"] = item.get("id")
            if not result.get("filename") and item.get("filename"):
                result["filename"] = item["filename"]
        item["result"] = result
        item["snapshot"] = result
        if item.get("uploaded_at") and hasattr(item["uploaded_at"], "isoformat"):
            item["uploaded_at"] = item["uploaded_at"].isoformat()
        elif item.get("uploaded_at"):
            item["uploaded_at"] = str(item["uploaded_at"])
        out.append(item)
    return out


@app.get("/api/documents/my")
def get_my_documents(user_id: int = 1, db = Depends(get_db)):
    """Recent analyses for a user (dashboard). Run migrations/001_add_analysis_json.sql for full saved snapshots."""
    try:
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, filename, risk_level, clauses_detected, uploaded_at, analysis_json
                FROM documents
                WHERE user_id = %s
                ORDER BY COALESCE(uploaded_at, id) DESC, id DESC
                LIMIT 100
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            include_json = True
        except Exception:
            cursor.execute(
                """
                SELECT id, filename, risk_level, clauses_detected, uploaded_at
                FROM documents
                WHERE user_id = %s
                ORDER BY COALESCE(uploaded_at, id) DESC, id DESC
                LIMIT 100
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            include_json = False
        cursor.close()
        return {"documents": _rows_to_document_list(rows, include_json)}
    except Exception as e:
        print(f"get_my_documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}")
def get_document_by_id(document_id: int, user_id: int = 1, db = Depends(get_db)):
    """Single saved analysis (must belong to user_id)."""
    try:
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, filename, risk_level, clauses_detected, uploaded_at, analysis_json
                FROM documents
                WHERE id = %s AND user_id = %s
                LIMIT 1
                """,
                (document_id, user_id),
            )
        except Exception:
            cursor.execute(
                """
                SELECT id, filename, risk_level, clauses_detected, uploaded_at
                FROM documents
                WHERE id = %s AND user_id = %s
                LIMIT 1
                """,
                (document_id, user_id),
            )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        raw = row.pop("analysis_json", None)
        parsed = json.loads(raw) if raw else None
        result = _normalize_stored_analysis_payload(parsed)
        if row.get("uploaded_at") and hasattr(row["uploaded_at"], "isoformat"):
            row["uploaded_at"] = row["uploaded_at"].isoformat()
        return {"document": row, "result": result, "snapshot": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Document Analysis Endpoint (Combines Risk & Calendar logic) ---

@app.post("/api/documents/analyze")
async def analyze_uploaded_document(
    file: UploadFile = File(...),
    user_id: int = Form(1),
    db = Depends(get_db),
):
    from risk_service import build_risk_segments, detect_risks, extract_text_from_pdf
    from calendar_service import read_docx_text

    try:
        safe_fn = (file.filename or "").lower()
        suffix = os.path.splitext(file.filename or "")[1] or ".bin"

        # 1. Save file temporarily so the docx/pdf libraries can read it
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # 2. Extract Text based on file type
        text = ""
        if safe_fn.endswith(".docx"):
            text = read_docx_text(temp_file_path)
        elif safe_fn.endswith(".pdf"):
            with open(temp_file_path, "rb") as f:
                text = extract_text_from_pdf(f)
        else:
            os.remove(temp_file_path)
            raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")

        os.remove(temp_file_path)
        if not (text or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Document is empty or unreadable. Please upload a valid .docx or .pdf with text content.",
            )

        # 3. Run Risk Analysis
        from risk_service import detect_risks
        risky_sentences, risky_phrases = detect_risks(text)
        clauses_detected = len(risky_sentences)
        risk_segments = build_risk_segments(text)
        
        # Calculate Risk Score & Level based on findings
        risk_score = min(100, (clauses_detected * 10) + (len(risky_phrases) * 5))
        risk_level = "Low"
        if risk_score > 30: risk_level = "Medium"
        if risk_score > 70: risk_level = "High"
        
        # 4. Gemini: one combined call by default (half the quota vs summaries + calendar separately).
        # Set GEMINI_SEPARATE_CALLS=1 in .env to use two requests instead.
        if os.getenv("GEMINI_SEPARATE_CALLS", "").lower() in ("1", "true", "yes"):
            from calendar_service import extract_events_with_gemini
            from summarizer import summarize_document_with_gemini

            summaries = summarize_document_with_gemini(text)
            calendar_events = extract_events_with_gemini(text)
            from benchmark_service import benchmark_document_with_gemini
            benchmark_payload = benchmark_document_with_gemini(text, file.filename or "upload")
        else:
            from gemini_combined import combined_summaries_and_events

            summaries, calendar_events, benchmark_payload = combined_summaries_and_events(text)

        analysis_payload = {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "clauses_detected": clauses_detected,
            "risky_phrases": risky_phrases,
            "risk_segments": risk_segments,
        }
        fname = file.filename or "upload"
        max_stored_text = int(os.getenv("MAX_STORED_EXTRACTED_TEXT", "120000"))
        extracted_for_store = text[:max_stored_text] if text else ""
        benchmark_result = _benchmark_response_contract(benchmark_payload)
        cursor = db.cursor()
        has_analysis_json_col = True
        try:
            cursor.execute(
                """
                INSERT INTO documents (user_id, filename, risk_level, clauses_detected, analysis_json, uploaded_at)
                VALUES (%s, %s, %s, %s, NULL, %s)
                """,
                (user_id, fname, risk_level, clauses_detected, datetime.now()),
            )
        except Exception as db_err:
            err_s = str(db_err).lower()
            if "analysis_json" in err_s or "unknown column" in err_s:
                has_analysis_json_col = False
                cursor.execute(
                    """
                    INSERT INTO documents (user_id, filename, risk_level, clauses_detected, uploaded_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, fname, risk_level, clauses_detected, datetime.now()),
                )
            else:
                raise
        db.commit()
        document_id = cursor.lastrowid

        response_body = {
            "status": "success",
            "message": "Analysis Complete",
            "document_id": document_id,
            "filename": fname,
            "analysis": analysis_payload,
            "calendar_events": calendar_events,
            "extracted_text": extracted_for_store,
            "benchmark": benchmark_payload,
            "benchmark_status": benchmark_result["status"],
            "benchmark_error": benchmark_result["error"],
            "benchmark_schema_version": "1.1",
        }
        if summaries and any(
            (str(v).strip() for v in summaries.values() if v is not None)
        ):
            response_body["summaries"] = summaries

        if has_analysis_json_col:
            try:
                payload = json.dumps(response_body, default=str)
            except (TypeError, ValueError) as je:
                raise HTTPException(
                    status_code=500,
                    detail=f"Could not serialize analysis result: {je}",
                ) from je
            cursor.execute(
                "UPDATE documents SET analysis_json = %s WHERE id = %s",
                (payload, document_id),
            )
            db.commit()
        _save_document_insights(
            db,
            document_id=document_id,
            user_id=user_id,
            extracted_text=extracted_for_store,
            summaries=response_body.get("summaries"),
            benchmark=response_body.get("benchmark"),
            calendar_events=response_body.get("calendar_events"),
            benchmark_status=response_body.get("benchmark_status"),
            benchmark_error=response_body.get("benchmark_error"),
            schema_version=response_body.get("benchmark_schema_version", "1.1"),
        )
        try:
            try_save_extracted_events(db, user_id, document_id, calendar_events)
        except Exception as save_err:
            print(f"[WARN] try_save_extracted_events (non-fatal): {save_err}")
        cursor.close()

        return response_body

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), user_id: int = 1, db = Depends(get_db)):
    """
    Simple document upload endpoint that saves files and extracts basic metadata.
    """
    if not file.filename.lower().endswith(('.docx', '.pdf', '.txt')):
        raise HTTPException(status_code=400, detail="Only DOCX, PDF, and TXT files are supported")
    
    try:
        content = await file.read()
        
        # Extract text based on file type
        text = ""
        if file.filename.lower().endswith('.docx'):
            from docx import Document
            import io
            docx_file = io.BytesIO(content)
            doc = Document(docx_file)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif file.filename.lower().endswith('.pdf'):
            import io
            try:
                import PyPDF2
                pdf_file = io.BytesIO(content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = "\n".join([page.extract_text() for page in pdf_reader.pages])
            except ImportError:
                # Fallback if PyPDF2 not available
                text = "[PDF content - PyPDF2 library not installed]"
        else:
            text = content.decode('utf-8', errors='ignore')
        
        # Save to database
        cursor = db.cursor()
        sql = """
            INSERT INTO documents (user_id, filename, content, uploaded_at) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (user_id, file.filename, text[:10000], datetime.now()))  # Store first 10k chars
        db.commit()
        document_id = cursor.lastrowid
        cursor.close()
        
        return {
            "status": "success",
            "message": "Document uploaded successfully",
            "document_id": document_id,
            "filename": file.filename,
            "size_bytes": len(content),
            "text_preview": text[:200]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

# This must always be at the bottom!
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)