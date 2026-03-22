from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


def _normalize_password_bytes(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    normalized = _normalize_password_bytes(password)
    return bcrypt.hashpw(normalized, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    normalized = _normalize_password_bytes(plain_password)
    return bcrypt.checkpw(normalized, hashed_password.encode("utf-8"))


def _build_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
) -> tuple[str, int, str]:
    expire_at = datetime.now(timezone.utc) + expires_delta
    token_jti = str(uuid.uuid4())

    payload = {
        "sub": subject,
        "type": token_type,
        "jti": token_jti,
        "exp": expire_at,
    }

    encoded_jwt = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    expires_in_seconds = int(expires_delta.total_seconds())

    return encoded_jwt, expires_in_seconds, token_jti


def create_access_token(subject: str) -> tuple[str, int, str]:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _build_token(subject=subject, token_type=TokenType.ACCESS, expires_delta=expires_delta)


def create_refresh_token(subject: str) -> tuple[str, int, str]:
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    return _build_token(subject=subject, token_type=TokenType.REFRESH, expires_delta=expires_delta)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def decode_token_by_type(token: str, expected_type: str) -> dict:
    payload = decode_token(token)
    token_type = payload.get("type")

    if token_type != expected_type:
        raise JWTError("Invalid token type")

    return payload
