import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

JWT_SECRET = os.environ.get('JWT_SECRET', 'fallback_secret')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_id: int, email: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expired')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return decode_token(credentials.credentials)


def require_permission(permission: str):
    """Dependency to check if current user has specific permission"""
    async def check_permission(current_user: dict = Depends(get_current_user)):
        from database import get_db
        from models import User, Role
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Get a new database session
        from database import async_session_maker
        async with async_session_maker() as db:
            # Get user
            result = await db.execute(select(User).where(User.id == current_user['user_id']))
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user permissions
            role_result = await db.execute(select(Role).where(Role.name == user.role))
            role = role_result.scalar_one_or_none()
            permissions = role.permissions if role else []
            
            if permission not in permissions:
                raise HTTPException(status_code=403, detail=f"Permission '{permission}' required")
            
            return current_user
    
    return check_permission
