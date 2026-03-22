from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.enums import ScholarshipStageType
from app.models.scholarship import JuryAssignment, Scholarship
from app.models.workflow import ScholarshipStage


async def get_application_or_404(db: AsyncSession, application_id: uuid.UUID) -> Application:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.scholarship).selectinload(Scholarship.columns))
        .where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ariza topilmadi")
    return application


async def is_active_assignment(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(JuryAssignment).where(
            JuryAssignment.scholarship_id == scholarship_id,
            JuryAssignment.jury_id == jury_id,
            JuryAssignment.is_active.is_(True),
        )
    )
    assignment = result.scalar_one_or_none()
    return assignment is not None


async def ensure_active_assignment(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
) -> None:
    if await is_active_assignment(db=db, scholarship_id=scholarship_id, jury_id=jury_id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Siz bu stipendiya uchun hakam sifatida biriktirilmagansiz",
    )


def calculate_total_percent(
    scores: dict[str, float],
    columns: list,
) -> float:
    score_map = {str(column.id): float(scores.get(str(column.id), 0.0)) for column in columns}

    total_score = sum(score_map.values())
    max_total = sum(float(column.max_score) for column in columns)

    return round((total_score / max_total * 100) if max_total else 0.0, 2)


def validate_scores_before_submit(scores: dict[str, float], columns: list) -> dict[str, float]:
    normalized: dict[str, float] = {}
    missing_columns: list[str] = []

    for column in columns:
        column_id = str(column.id)
        max_score = float(column.max_score)

        # max_score=0 bo'lgan texnik ustunlarda ball majburiy emas
        if max_score <= 0:
            continue

        raw_score = scores.get(column_id)
        if raw_score is None:
            missing_columns.append(column_id)
            continue

        score = float(raw_score)
        if score < 0 or score > max_score:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{column.name}' uchun ball 0 va {column.max_score} oralig'ida bo'lishi kerak",
            )
        normalized[column_id] = round(score, 2)

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Baholashni topshirish uchun barcha baholanuvchi ustunlar to'ldirilishi kerak",
                "missing_columns": missing_columns,
            },
        )

    return normalized


async def ensure_stage_allows_jury_actions(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
) -> ScholarshipStage | None:
    existing_stage = await db.execute(
        select(ScholarshipStage.id)
        .where(ScholarshipStage.scholarship_id == scholarship_id)
        .limit(1)
    )
    if existing_stage.scalar_one_or_none() is None:
        return None

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
    if stage is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hozir faol bosqich yo'q")

    allowed = {
        ScholarshipStageType.REVIEW,
        ScholarshipStageType.EXAM,
        ScholarshipStageType.INTERVIEW,
    }
    if stage.stage_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hozir '{stage.stage_type.value}' bosqichida baholashga ruxsat yo'q",
        )
    return stage
