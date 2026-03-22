from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScholarshipStatus, UserRole
from app.models.scholarship import Scholarship


STATUS_TRANSITIONS = {
    ScholarshipStatus.DRAFT: ScholarshipStatus.OPEN,
    ScholarshipStatus.OPEN: ScholarshipStatus.CLOSED,
    ScholarshipStatus.CLOSED: ScholarshipStatus.DONE,
}


async def get_scholarship_or_404(db: AsyncSession, scholarship_id: uuid.UUID) -> Scholarship:
    result = await db.execute(select(Scholarship).where(Scholarship.id == scholarship_id))
    scholarship = result.scalar_one_or_none()
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")
    return scholarship


async def list_scholarships(
    db: AsyncSession,
    current_user_role: UserRole,
    status_filter: ScholarshipStatus | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Scholarship]:
    query = select(Scholarship)

    if current_user_role == UserRole.STUDENT:
        query = query.where(Scholarship.status == ScholarshipStatus.OPEN)
    elif status_filter is not None:
        query = query.where(Scholarship.status == status_filter)

    if search:
        query = query.where(Scholarship.title.ilike(f"%{search.strip()}%"))

    query = query.order_by(Scholarship.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def change_scholarship_status(
    db: AsyncSession,
    scholarship: Scholarship,
    target_status: ScholarshipStatus,
) -> Scholarship:
    expected_next = STATUS_TRANSITIONS.get(scholarship.status)
    if expected_next is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Yakuniy holatga yetilgan")

    if target_status != expected_next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Holat faqat '{scholarship.status}' -> '{expected_next}' bo'lishi mumkin",
        )

    scholarship.status = target_status
    await db.commit()
    await db.refresh(scholarship)
    return scholarship
