import os
from datetime import datetime, timedelta
from typing import Optional

import hashlib

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import Member

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_member(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Member:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    payload = decode_token(token)
    if not payload or "member_id" not in payload:
        raise credentials_exception
    member = db.query(Member).filter(Member.id == payload["member_id"]).first()
    if not member:
        raise credentials_exception
    return member


def get_current_member_optional(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[Member]:
    if not token:
        return None
    payload = decode_token(token)
    if not payload or "member_id" not in payload:
        return None
    return db.query(Member).filter(Member.id == payload["member_id"]).first()
