import bcrypt
import re

def validate_password_strength(password: str) -> dict:
    """
    Validates password strength.
    Returns: {
        "valid": bool,
        "message": str,
        "errors": list
    }
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        errors.append("Password must contain at least one special character: !@#$%^&*()_+-=[]{};\\':\",.<>?/\\|`~")
    
    return {
        "valid": len(errors) == 0,
        "message": "Password is strong" if len(errors) == 0 else "Password does not meet requirements",
        "errors": errors
    }

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        return False
