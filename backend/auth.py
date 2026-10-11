import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ingest.config import DEMO_USERS, JWT_SECRET, JWT_ALGORITHM

security = HTTPBearer(auto_error=False)

def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    user = DEMO_USERS.get(username.lower().strip())
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return user

def create_jwt_token(username: str, user_info: Dict[str, Any]) -> str:
    payload = {
        "sub": username,
        "role": user_info["role"],
        "name": user_info["name"],
        "dept": user_info["dept"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict[str, Any]:
    if not credentials:
        # Fallback for direct testing without header
        return {"username": "anonymous", "role": "doctor", "name": "Dr. Mehta", "dept": "Clinical"}
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
