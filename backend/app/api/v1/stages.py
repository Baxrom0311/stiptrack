from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_admin_or_jury
from app.models.enums import ScholarshipStatus, StageTaskStatus, UserRole
from app.models.scholarship import Scholarship
from app.models.user import User
from app.models.workflow import ScholarshipStage, StageTask
from app.schemas.workflow import (
    StageCreate,
    StageOut,
    StageReorder,
    StageTaskCreate,
    StageTaskOut,
    StageTaskUpdate,
    StageUpdate,
)


router = APIRouter(prefix="/scholarships", tags=["stages"])


async def _get_scholarship_or_404(db: AsyncSession, scholarship_id: uuid.UUID) -> Scholarship:
    scholarship = await db.get(Scholarship, scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")
    return scholarship


async def _get_stage_or_404(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> ScholarshipStage:
    result = await db.execute(
        select(ScholarshipStage).where(
            ScholarshipStage.id == stage_id,
            ScholarshipStage.scholarship_id == scholarship_id,
        )
    )
    stage = result.scalar_one_or_none()
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bosqich topilmadi")
    return stage


def _validate_stage_window(start_at: datetime, end_at: datetime) -> None:
    if start_at >= end_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bosqichda starts_at < ends_at bo'lishi shart",
        )


@router.get("/{scholarship_id}/stages", response_model=list[StageOut])
async def list_stages(
    scholarship_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[StageOut]:
    scholarship = await _get_scholarship_or_404(db, scholarship_id)
    if current_user.role == UserRole.STUDENT and scholarship.status == ScholarshipStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    result = await db.execute(
        select(ScholarshipStage)
        .where(ScholarshipStage.scholarship_id == scholarship_id)
        .order_by(ScholarshipStage.order_index)
    )
    return [StageOut.model_validate(item) for item in result.scalars().all()]


@router.get("/{scholarship_id}/stages/active", response_model=StageOut | None)
async def get_active_stage(
    scholarship_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StageOut | None:
    await _get_scholarship_or_404(db, scholarship_id)

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ScholarshipStage)
        .where(
            ScholarshipStage.scholarship_id == scholarship_id,
            ScholarshipStage.is_active.is_(True),
            ScholarshipStage.starts_at <= now,
            ScholarshipStage.ends_at >= now,
        )
        .order_by(ScholarshipStage.order_index)
        .limit(1)
    )
    stage = result.scalar_one_or_none()
    return StageOut.model_validate(stage) if stage is not None else None


@router.post("/{scholarship_id}/stages", response_model=StageOut, status_code=status.HTTP_201_CREATED)
async def create_stage(
    scholarship_id: uuid.UUID,
    payload: StageCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StageOut:
    await _get_scholarship_or_404(db, scholarship_id)
    _validate_stage_window(payload.starts_at, payload.ends_at)

    result = await db.execute(
        select(ScholarshipStage.order_index)
        .where(ScholarshipStage.scholarship_id == scholarship_id)
        .order_by(ScholarshipStage.order_index.desc())
        .limit(1)
    )
    last_order = result.scalar_one_or_none() or -1

    stage = ScholarshipStage(
        scholarship_id=scholarship_id,
        order_index=last_order + 1,
        **payload.model_dump(),
    )
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return StageOut.model_validate(stage)


@router.patch("/{scholarship_id}/stages/{stage_id}", response_model=StageOut)
async def update_stage(
    scholarship_id: uuid.UUID,
    stage_id: uuid.UUID,
    payload: StageUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StageOut:
    stage = await _get_stage_or_404(db, scholarship_id, stage_id)

    update_data = payload.model_dump(exclude_unset=True)
    start_at = update_data.get("starts_at", stage.starts_at)
    end_at = update_data.get("ends_at", stage.ends_at)
    if start_at is not None and end_at is not None:
        _validate_stage_window(start_at, end_at)

    for field, value in update_data.items():
        setattr(stage, field, value)

    await db.commit()
    await db.refresh(stage)
    return StageOut.model_validate(stage)


@router.delete(
    "/{scholarship_id}/stages/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_stage(
    scholarship_id: uuid.UUID,
    stage_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stage = await _get_stage_or_404(db, scholarship_id, stage_id)
    await db.delete(stage)
    await db.commit()


@router.patch("/{scholarship_id}/stages/reorder")
async def reorder_stages(
    scholarship_id: uuid.UUID,
    payload: StageReorder,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _get_scholarship_or_404(db, scholarship_id)

    result = await db.execute(
        select(ScholarshipStage).where(ScholarshipStage.scholarship_id == scholarship_id)
    )
    stage_map = {item.id: item for item in result.scalars().all()}

    if set(payload.order) != set(stage_map.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reorder ro'yxatida barcha bosqichlar bo'lishi kerak",
        )

    for index, stage_id in enumerate(payload.order):
        stage_map[stage_id].order_index = index

    await db.commit()
    return {"detail": "Bosqichlar tartibi yangilandi"}


@router.get("/{scholarship_id}/stages/{stage_id}/tasks", response_model=list[StageTaskOut])
async def list_stage_tasks(
    scholarship_id: uuid.UUID,
    stage_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin_or_jury)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[StageTaskOut]:
    await _get_stage_or_404(db, scholarship_id, stage_id)
    result = await db.execute(
        select(StageTask)
        .where(StageTask.stage_id == stage_id)
        .order_by(StageTask.due_at.asc().nullslast(), StageTask.created_at.asc())
    )
    return [StageTaskOut.model_validate(item) for item in result.scalars().all()]


@router.post("/{scholarship_id}/stages/{stage_id}/tasks", response_model=StageTaskOut, status_code=status.HTTP_201_CREATED)
async def create_stage_task(
    scholarship_id: uuid.UUID,
    stage_id: uuid.UUID,
    payload: StageTaskCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StageTaskOut:
    await _get_stage_or_404(db, scholarship_id, stage_id)
    if payload.assigned_to is not None:
        assignee = await db.get(User, payload.assigned_to)
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user topilmadi")

    task = StageTask(stage_id=stage_id, **payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return StageTaskOut.model_validate(task)


@router.patch("/{scholarship_id}/stages/{stage_id}/tasks/{task_id}", response_model=StageTaskOut)
async def update_stage_task(
    scholarship_id: uuid.UUID,
    stage_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: StageTaskUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StageTaskOut:
    await _get_stage_or_404(db, scholarship_id, stage_id)

    result = await db.execute(
        select(StageTask).where(
            and_(
                StageTask.id == task_id,
                StageTask.stage_id == stage_id,
            )
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task topilmadi")

    update_data = payload.model_dump(exclude_unset=True)
    if "assigned_to" in update_data and update_data["assigned_to"] is not None:
        assignee = await db.get(User, update_data["assigned_to"])
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user topilmadi")

    status_value = update_data.get("status")
    if status_value in (StageTaskStatus.DONE, StageTaskStatus.DONE.value):
        update_data["completed_at"] = datetime.now(timezone.utc)
    elif status_value is not None:
        update_data["completed_at"] = None

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return StageTaskOut.model_validate(task)


@router.delete(
    "/{scholarship_id}/stages/{stage_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_stage_task(
    scholarship_id: uuid.UUID,
    stage_id: uuid.UUID,
    task_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _get_stage_or_404(db, scholarship_id, stage_id)

    result = await db.execute(
        select(StageTask).where(
            StageTask.id == task_id,
            StageTask.stage_id == stage_id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task topilmadi")
    await db.delete(task)
    await db.commit()
