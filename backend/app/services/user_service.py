from __future__ import annotations

import uuid

from sqlalchemy import String, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserAdminCreate, UserAdminUpdate


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def list_users(
    db: AsyncSession,
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    query = select(User)

    if role is not None:
        query = query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.department.cast(String).ilike(pattern),
                User.student_id.cast(String).ilike(pattern),
            )
        )

    query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_user(db: AsyncSession, payload: UserAdminCreate) -> User:
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        department=payload.department,
        student_id=payload.student_id,
        is_supervisor=payload.is_supervisor,
        is_active=payload.is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, payload: UserAdminUpdate) -> User:
    updates = payload.model_dump(exclude_unset=True)

    password = updates.pop("password", None)
    if password is not None:
        user.password_hash = hash_password(password)

    for field, value in updates.items():
        setattr(user, field, value)

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_own_profile(db: AsyncSession, user: User, updates: dict) -> User:
    for field, value in updates.items():
        setattr(user, field, value)

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_supervisors(db: AsyncSession, only_active: bool = True) -> list[User]:
    query = select(User).where(User.is_supervisor.is_(True))

    if only_active:
        query = query.where(User.is_active.is_(True))

    query = query.order_by(User.full_name.asc())

    result = await db.execute(query)
    return list(result.scalars().all())
