from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenType, decode_token_by_type
from app.models.enums import UserRole
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _unauthorized_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    credentials_exception = _unauthorized_exception()

    try:
        payload = decode_token_by_type(token=token, expected_type=TokenType.ACCESS)
    except PyJWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(str(user_id))
    except ValueError as exc:
        raise credentials_exception from exc

    query = select(User).where(User.id == user_uuid)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user


async def require_jury(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.JURY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Jury role required")
    return current_user


async def require_student(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student role required")
    return current_user


async def require_admin_or_jury(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role not in (UserRole.ADMIN, UserRole.JURY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or jury role required",
        )
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
