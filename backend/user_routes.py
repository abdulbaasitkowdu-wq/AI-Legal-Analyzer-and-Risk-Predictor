from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db_connection, close_db_connection
from password_utils import hash_password, verify_password, validate_password_strength

router = APIRouter()

def get_db():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        yield conn
    finally:
        close_db_connection(conn)

class UpdateUserRequest(BaseModel):
    name: str
    email: str
    password: Optional[str] = None

@router.put("/users/{user_id}")
def update_user_profile(user_id: int, request: UpdateUserRequest, db = Depends(get_db)):
    """Allow users to update their profile (name, email, and optionally password)."""
    try:
        print(f"[DEBUG] Update profile request: user_id={user_id}, name={request.name}, email={request.email}")
        cursor = db.cursor(dictionary=True)
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if new email is already in use by another user
        if request.email != user['email']:
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (request.email, user_id))
            if cursor.fetchone():
                cursor.close()
                raise HTTPException(status_code=400, detail="Email already in use by another user")
        
        # Update user profile
        if request.password and request.password.strip():
            # Validate new password strength
            password_validation = validate_password_strength(request.password)
            if not password_validation["valid"]:
                cursor.close()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Password requirements not met: {'; '.join(password_validation['errors'])}"
                )
            
            # Hash the new password
            hashed_password = hash_password(request.password)
            
            # Update name, email, and password
            cursor.execute(
                "UPDATE users SET name = %s, email = %s, password = %s WHERE id = %s",
                (request.name, request.email, hashed_password, user_id)
            )
        else:
            # Update only name and email
            cursor.execute(
                "UPDATE users SET name = %s, email = %s WHERE id = %s",
                (request.name, request.email, user_id)
            )
        
        db.commit()
        
        # Fetch updated user data to return
        cursor.execute("SELECT id, name, email, role FROM users WHERE id = %s", (user_id,))
        updated_user = cursor.fetchone()
        cursor.close()
        
        print(f"[USER] Profile updated for user: {request.email} (ID: {user_id})")
        
        return {
            "message": "Profile updated successfully",
            "user": {
                "id": updated_user['id'],
                "name": updated_user['name'],
                "email": updated_user['email'],
                "initials": "".join([n[0] for n in updated_user['name'].split()][:2]).upper(),
                "role": updated_user['role']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Update user error: {e}")
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")