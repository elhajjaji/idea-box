from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from src.models.user import User
from src.services.database import Database
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import os
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_email(email: str):
    return await Database.engine.find_one(User, User.email == email)

async def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme), access_token: Optional[str] = Cookie(None)):
    """
    Get current user from either Authorization header or cookie
    Retourne None si non authentifié ou token invalide (pas d'exception).
    """
    auth_token = token or access_token
    if not auth_token:
        return None
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = await get_user_by_email(email)
        if user is None:
            return None
        return user
    except JWTError:
        return None

async def get_current_user_optional(request: Request, token: Optional[str] = Depends(oauth2_scheme), access_token: Optional[str] = Cookie(None)):
    """
    Variante de get_current_user : retourne None si non authentifié (pas d'exception).
    """
    auth_token = token or access_token
    if not auth_token:
        return None
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = await get_user_by_email(email)
        if user:
            # user.roles = payload.get("roles", []) # Assign roles from JWT to user object
            pass # Roles are already loaded from DB
        return user
    except JWTError:
        return None
