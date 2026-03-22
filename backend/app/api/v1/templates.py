from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.scholarship import Scholarship, ScholarshipTemplate
from app.models.user import User
from app.models.workflow import ScholarshipStage
from app.schemas.scholarship import ScholarshipOut
from app.schemas.template import (
    ScholarshipTemplateCreate,
    ScholarshipTemplateInstantiate,
    ScholarshipTemplateOut,
)
from app.services.template_service import (
    build_scholarship_template_snapshot,
    build_template_summary,
    instantiate_scholarship_from_template,
)


router = APIRouter(prefix="/scholarship-templates", tags=["scholarship-templates"])


@router.get("", response_model=list[ScholarshipTemplateOut])
async def list_scholarship_templates(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ScholarshipTemplateOut]:
    result = await db.execute(
        select(ScholarshipTemplate).order_by(ScholarshipTemplate.created_at.desc())
    )
    return [ScholarshipTemplateOut(**build_template_summary(item)) for item in result.scalars().all()]


@router.post("", response_model=ScholarshipTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_scholarship_template(
    payload: ScholarshipTemplateCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScholarshipTemplateOut:
    result = await db.execute(
        select(Scholarship)
        .options(
            selectinload(Scholarship.columns),
            selectinload(Scholarship.stages).selectinload(ScholarshipStage.tasks),
        )
        .where(Scholarship.id == payload.scholarship_id)
    )
    scholarship = result.scalar_one_or_none()
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    template = ScholarshipTemplate(
        created_by=current_user.id,
        source_scholarship_id=scholarship.id,
        name=payload.name,
        description=payload.description,
        snapshot=build_scholarship_template_snapshot(scholarship),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return ScholarshipTemplateOut(**build_template_summary(template))


@router.post("/{template_id}/instantiate", response_model=ScholarshipOut, status_code=status.HTTP_201_CREATED)
async def instantiate_scholarship_template(
    template_id: uuid.UUID,
    payload: ScholarshipTemplateInstantiate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScholarshipOut:
    template = await db.get(ScholarshipTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template topilmadi")

    scholarship, columns, stages, tasks = instantiate_scholarship_from_template(
        template,
        created_by=current_user.id,
    )
    scholarship.title = payload.title
    scholarship.description = payload.description if payload.description is not None else scholarship.description
    scholarship.deadline = payload.deadline

    if payload.starts_at is not None and stages:
        original_base = min(stage.starts_at for stage in stages)
        shift = payload.starts_at - original_base
        for stage in stages:
            stage.starts_at = stage.starts_at + shift
            stage.ends_at = stage.ends_at + shift
        for task in tasks:
            if task.due_at is not None:
                task.due_at = task.due_at + shift

    db.add(scholarship)
    for item in columns:
        db.add(item)
    for item in stages:
        db.add(item)
    for item in tasks:
        db.add(item)

    await db.commit()
    await db.refresh(scholarship)
    return ScholarshipOut.model_validate(scholarship)
