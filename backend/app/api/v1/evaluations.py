from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_jury
from app.models.application import Application
from app.models.enums import ApplicationStatus, UserRole
from app.models.evaluation import Evaluation
from app.models.scholarship import Scholarship
from app.models.user import User
from app.models.workflow import ScholarshipStage
from app.schemas.evaluation import EvaluationOut, EvaluationUpdate
from app.services.evaluation_service import (
    calculate_total_percent as calculate_total_percent_service,
    ensure_active_assignment as ensure_active_assignment_service,
    ensure_stage_allows_jury_actions as ensure_stage_allows_jury_actions_service,
    get_application_or_404 as get_application_or_404_service,
    is_active_assignment as is_active_assignment_service,
    validate_scores_before_submit as validate_scores_before_submit_service,
)
from app.services.application_service import transition_application_status
from app.services.notification_service import queue_application_status_email_tasks


router = APIRouter(prefix="/evaluations", tags=["evaluations"])


async def _get_application_or_404(db: AsyncSession, application_id: uuid.UUID) -> Application:
    return await get_application_or_404_service(db=db, application_id=application_id)


async def _ensure_active_assignment(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
) -> None:
    await ensure_active_assignment_service(db=db, scholarship_id=scholarship_id, jury_id=jury_id)


async def _is_active_assignment(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
) -> bool:
    return await is_active_assignment_service(db=db, scholarship_id=scholarship_id, jury_id=jury_id)


def _calculate_total_percent(
    scores: dict[str, float],
    columns: list,
) -> float:
    return calculate_total_percent_service(scores=scores, columns=columns)


def _validate_scores_before_submit(scores: dict[str, float], columns: list) -> dict[str, float]:
    return validate_scores_before_submit_service(scores=scores, columns=columns)


async def _ensure_stage_allows_jury_actions(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
) -> ScholarshipStage | None:
    return await ensure_stage_allows_jury_actions_service(db=db, scholarship_id=scholarship_id)


@router.get("/{application_id}", response_model=EvaluationOut)
async def get_evaluation(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_jury)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationOut:
    application = await _get_application_or_404(db, application_id)
    await _ensure_active_assignment(
        db=db,
        scholarship_id=application.scholarship_id,
        jury_id=current_user.id,
    )

    result = await db.execute(
        select(Evaluation).where(
            Evaluation.application_id == application_id,
            Evaluation.jury_id == current_user.id,
        )
    )
    evaluation = result.scalar_one_or_none()

    if evaluation is None:
        return EvaluationOut(
            id=None,
            application_id=application_id,
            jury_id=current_user.id,
            scores={},
            total_score=None,
            final_comment=None,
            ai_generated=False,
            is_submitted=False,
            submitted_at=None,
        )

    return EvaluationOut.model_validate(evaluation)


@router.get("/applications/{application_id}/visible", response_model=list[EvaluationOut])
async def list_visible_evaluations(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EvaluationOut]:
    application = await _get_application_or_404(db, application_id)
    scholarship = await db.get(Scholarship, application.scholarship_id)
    blind_review_enabled = bool(scholarship is not None and scholarship.blind_review_enabled)

    is_owner = application.student_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN
    is_assigned_jury = False
    if current_user.role == UserRole.JURY:
        is_assigned_jury = await _is_active_assignment(
            db=db,
            scholarship_id=application.scholarship_id,
            jury_id=current_user.id,
        )

    if not (is_owner or is_admin or is_assigned_jury):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    query = select(Evaluation).where(Evaluation.application_id == application_id)
    if is_owner:
        query = query.where(Evaluation.is_submitted.is_(True))
    elif current_user.role == UserRole.JURY and blind_review_enabled:
        query = query.where(Evaluation.jury_id == current_user.id)

    query = query.order_by(Evaluation.submitted_at.desc().nullslast(), Evaluation.updated_at.desc())
    result = await db.execute(query)
    evaluations = result.scalars().all()
    return [EvaluationOut.model_validate(item) for item in evaluations]


@router.post("/{application_id}", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_jury)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationOut:
    application = await _get_application_or_404(db, application_id)
    await _ensure_active_assignment(
        db=db,
        scholarship_id=application.scholarship_id,
        jury_id=current_user.id,
    )
    await _ensure_stage_allows_jury_actions(db=db, scholarship_id=application.scholarship_id)

    if application.status not in (ApplicationStatus.SUBMITTED, ApplicationStatus.IN_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat topshirilgan arizani baholash mumkin",
        )

    existing = await db.execute(
        select(Evaluation).where(
            Evaluation.application_id == application_id,
            Evaluation.jury_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Baholash allaqachon boshlangan")

    evaluation = Evaluation(
        application_id=application_id,
        jury_id=current_user.id,
        scores={},
    )
    db.add(evaluation)

    status_log = None
    if application.status == ApplicationStatus.SUBMITTED:
        status_log = transition_application_status(
            db=db,
            application=application,
            new_status=ApplicationStatus.IN_REVIEW,
            changed_by_user_id=current_user.id,
            source="jury_review_started",
            note="Hakam arizani ko'rib chiqishni boshladi",
        )

    await db.commit()
    await db.refresh(evaluation)
    if status_log is not None:
        queue_application_status_email_tasks([status_log.id])
    return EvaluationOut.model_validate(evaluation)


@router.patch("/{application_id}", response_model=EvaluationOut)
async def update_evaluation(
    application_id: uuid.UUID,
    payload: EvaluationUpdate,
    current_user: Annotated[User, Depends(require_jury)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationOut:
    result = await db.execute(
        select(Evaluation)
        .options(
            selectinload(Evaluation.application)
            .selectinload(Application.scholarship)
            .selectinload(Scholarship.columns)
        )
        .where(
            Evaluation.application_id == application_id,
            Evaluation.jury_id == current_user.id,
        )
    )
    evaluation = result.scalar_one_or_none()
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Baholash topilmadi")

    await _ensure_stage_allows_jury_actions(
        db=db,
        scholarship_id=evaluation.application.scholarship_id,
    )

    if evaluation.is_submitted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topshirilgan baholashni o'zgartirish mumkin emas",
        )

    columns = evaluation.application.scholarship.columns
    columns_by_id = {column.id: column for column in columns}

    if payload.scores is not None:
        normalized_scores: dict[str, float] = {}

        for raw_column_id, raw_score in payload.scores.items():
            try:
                column_id = uuid.UUID(str(raw_column_id))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Noto'g'ri ustun ID: {raw_column_id}",
                ) from exc

            column = columns_by_id.get(column_id)
            if column is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ball qo'yilgan ustun stipendiyaga tegishli emas",
                )

            score = float(raw_score)
            if score < 0 or score > float(column.max_score):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{column.name}' uchun ball 0 va {column.max_score} oralig'ida bo'lishi kerak",
                )

            normalized_scores[str(column_id)] = round(score, 2)

        evaluation.scores = normalized_scores
        evaluation.total_score = _calculate_total_percent(normalized_scores, columns)

    if payload.final_comment is not None:
        evaluation.final_comment = payload.final_comment

    if payload.ai_generated is not None:
        evaluation.ai_generated = payload.ai_generated

    await db.commit()
    await db.refresh(evaluation)
    return EvaluationOut.model_validate(evaluation)


@router.post("/{application_id}/submit", response_model=EvaluationOut)
async def submit_evaluation(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_jury)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationOut:
    result = await db.execute(
        select(Evaluation)
        .options(
            selectinload(Evaluation.application)
            .selectinload(Application.scholarship)
            .selectinload(Scholarship.columns)
        )
        .where(
            Evaluation.application_id == application_id,
            Evaluation.jury_id == current_user.id,
        )
    )
    evaluation = result.scalar_one_or_none()
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Baholash topilmadi")

    await _ensure_stage_allows_jury_actions(
        db=db,
        scholarship_id=evaluation.application.scholarship_id,
    )

    if evaluation.is_submitted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allaqachon topshirilgan")

    if not evaluation.scores:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avval ball qo'yish kerak")

    normalized_scores = _validate_scores_before_submit(
        evaluation.scores,
        evaluation.application.scholarship.columns,
    )
    evaluation.scores = normalized_scores
    evaluation.total_score = _calculate_total_percent(
        normalized_scores,
        evaluation.application.scholarship.columns,
    )

    evaluation.is_submitted = True
    evaluation.submitted_at = datetime.now(timezone.utc)

    application = evaluation.application
    status_log = None
    if application.status == ApplicationStatus.SUBMITTED:
        status_log = transition_application_status(
            db=db,
            application=application,
            new_status=ApplicationStatus.IN_REVIEW,
            changed_by_user_id=current_user.id,
            source="jury_review_started",
            note="Hakam baholashni topshirib ko'rib chiqish bosqichini boshladi",
        )

    submitted_result = await db.execute(
        select(Evaluation).where(
            Evaluation.application_id == application_id,
            Evaluation.is_submitted.is_(True),
        )
    )
    submitted_evaluations = submitted_result.scalars().all()
    score_values = [
        float(item.total_score)
        for item in submitted_evaluations
        if item.total_score is not None
    ]
    if score_values:
        application.total_score = round(sum(score_values) / len(score_values), 2)

    await db.commit()
    await db.refresh(evaluation)
    if status_log is not None:
        queue_application_status_email_tasks([status_log.id])
    return EvaluationOut.model_validate(evaluation)
