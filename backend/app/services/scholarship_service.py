from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScholarshipStatus, UserRole, ColumnFieldType
from app.models.scholarship import Scholarship, ScholarshipColumn, JuryAssignment


STATUS_TRANSITIONS = {
    ScholarshipStatus.DRAFT: ScholarshipStatus.OPEN,
    ScholarshipStatus.OPEN: ScholarshipStatus.CLOSED,
    ScholarshipStatus.CLOSED: ScholarshipStatus.DONE,
}


async def get_scholarship_or_404(db: AsyncSession, scholarship_id: uuid.UUID) -> Scholarship:
    from app.repositories.scholarship import scholarship as scholarship_repo
    from app.core.constants import ErrorMessages
    
    scholarship = await scholarship_repo.get(db, id=scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorMessages.SCHOLARSHIP_NOT_FOUND)
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
    from app.core.constants import ErrorMessages
    expected_next = STATUS_TRANSITIONS.get(scholarship.status)
    if expected_next is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorMessages.FINAL_STATUS_REACHED)

    if target_status != expected_next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorMessages.INVALID_STATUS_TRANSITION.format(current=scholarship.status, expected=expected_next),
        )

    scholarship.status = target_status
    await db.commit()
    await db.refresh(scholarship)
    return scholarship


def _normalize_column_payload(payload: dict, field_type: str) -> dict:
    from app.models.enums import ColumnFieldType
    from app.core.constants import ErrorMessages
    
    normalized = dict(payload)
    if field_type != ColumnFieldType.NUMBER:
        normalized["input_min"] = None
        normalized["input_max"] = None
        return normalized

    input_min = normalized.get("input_min")
    input_max = normalized.get("input_max")
    if input_min is not None and input_max is not None and input_min > input_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorMessages.INVALID_MIN_MAX,
        )
    return normalized


async def create_scholarship_column(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    payload_data: dict,
    field_type: str,
) -> Any:
    from app.models.scholarship import ScholarshipColumn
    
    await get_scholarship_or_404(db, scholarship_id)

    result = await db.execute(
        select(ScholarshipColumn.order_index)
        .where(ScholarshipColumn.scholarship_id == scholarship_id)
        .order_by(ScholarshipColumn.order_index.desc())
        .limit(1)
    )
    last_order = result.scalar_one_or_none() or -1

    column_payload = _normalize_column_payload(payload_data, field_type)
    column = ScholarshipColumn(
        scholarship_id=scholarship_id,
        order_index=last_order + 1,
        **column_payload,
    )
    db.add(column)
    await db.commit()
    await db.refresh(column)
    return column


async def update_scholarship_column(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    column_id: uuid.UUID,
    payload_data: dict,
) -> Any:
    from app.models.scholarship import ScholarshipColumn
    from app.core.constants import ErrorMessages
    
    result = await db.execute(
        select(ScholarshipColumn).where(
            ScholarshipColumn.id == column_id,
            ScholarshipColumn.scholarship_id == scholarship_id,
        )
    )
    column = result.scalar_one_or_none()
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorMessages.COLUMN_NOT_FOUND)

    next_field_type = payload_data.get("field_type", column.field_type)
    normalized_payload = _normalize_column_payload(payload_data, next_field_type)

    for field, value in normalized_payload.items():
        setattr(column, field, value)

    await db.commit()
    await db.refresh(column)
    return column


async def delete_scholarship_column(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    column_id: uuid.UUID,
) -> None:
    from app.models.scholarship import ScholarshipColumn
    from app.core.constants import ErrorMessages
    
    result = await db.execute(
        select(ScholarshipColumn).where(
            ScholarshipColumn.id == column_id,
            ScholarshipColumn.scholarship_id == scholarship_id,
        )
    )
    column = result.scalar_one_or_none()
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorMessages.COLUMN_NOT_FOUND)

    await db.delete(column)
    await db.commit()


async def reorder_scholarship_columns(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    order: list[uuid.UUID],
) -> None:
    from app.models.scholarship import ScholarshipColumn
    
    await get_scholarship_or_404(db, scholarship_id)

    for idx, column_id in enumerate(order):
        result = await db.execute(
            select(ScholarshipColumn).where(
                ScholarshipColumn.id == column_id,
                ScholarshipColumn.scholarship_id == scholarship_id,
            )
        )
        column = result.scalar_one_or_none()
        if column is not None:
            column.order_index = idx

    await db.commit()


async def assign_scholarship_jury(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
) -> Any:
    from app.models.scholarship import JuryAssignment
    from app.models.user import User
    from app.core.constants import ErrorMessages
    
    await get_scholarship_or_404(db, scholarship_id)

    result = await db.execute(
        select(User).where(User.id == jury_id, User.role == UserRole.JURY)
    )
    jury_user = result.scalar_one_or_none()
    if jury_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorMessages.JURY_NOT_FOUND)

    existing = await db.execute(
        select(JuryAssignment).where(
            JuryAssignment.scholarship_id == scholarship_id,
            JuryAssignment.jury_id == jury_id,
        )
    )
    assignment = existing.scalar_one_or_none()

    if assignment is not None:
        assignment.is_active = True
    else:
        assignment = JuryAssignment(
            scholarship_id=scholarship_id,
            jury_id=jury_id,
            is_active=True,
        )
        db.add(assignment)

    await db.commit()
    await db.refresh(assignment)
    return assignment


async def remove_scholarship_jury(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
) -> None:
    from app.models.scholarship import JuryAssignment
    from app.core.constants import ErrorMessages
    
    result = await db.execute(
        select(JuryAssignment).where(
            JuryAssignment.scholarship_id == scholarship_id,
            JuryAssignment.jury_id == jury_id,
        )
    )
    assignment = result.scalar_one_or_none()

    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorMessages.JURY_ASSIGNMENT_NOT_FOUND)

    assignment.is_active = False
    await db.commit()
