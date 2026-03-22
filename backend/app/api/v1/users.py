from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserAdminCreate, UserAdminUpdate, UserOut
from app.services.auth_service import get_user_by_email
from app.services.user_service import create_user, get_user_by_id, list_supervisors, list_users, update_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[UserOut]:
    users = await list_users(
        db=db,
        role=role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [UserOut.model_validate(user) for user in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    payload: UserAdminCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> UserOut:
    existing_user = await get_user_by_email(db=db, email=payload.email)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await create_user(db=db, payload=payload)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user_by_admin(
    user_id: uuid.UUID,
    payload: UserAdminUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> UserOut:
    user = await get_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.email is not None:
        existing_user = await get_user_by_email(db=db, email=payload.email)
        if existing_user is not None and existing_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await update_user(db=db, user=user, payload=payload)
    return UserOut.model_validate(user)


@router.patch("/{user_id}/toggle-active", response_model=UserOut)
async def toggle_user_active(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_admin)],
) -> UserOut:
    user = await get_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_admin.id and user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    payload = UserAdminUpdate(is_active=not user.is_active)
    updated_user = await update_user(db=db, user=user, payload=payload)
    return UserOut.model_validate(updated_user)


@router.get("/supervisors", response_model=list[UserOut])
async def get_supervisors(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[UserOut]:
    supervisors = await list_supervisors(db=db, only_active=True)
    return [UserOut.model_validate(user) for user in supervisors]
