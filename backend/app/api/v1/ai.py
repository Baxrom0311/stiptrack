import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_jury
from app.core.llm_client import format_llm_selection
from app.core.rate_limit import (
    limit_ai_generate_columns,
    limit_ai_generate_review,
    limit_ai_job_poll,
    limit_ai_parse_nizom,
    limiter,
)
from app.models.ai_job import AIJob
from app.models.application import Application, ApplicationValue
from app.models.enums import AIJobStatus, AIJobType, UserRole
from app.models.evaluation import Evaluation
from app.models.scholarship import JuryAssignment, Scholarship
from app.models.user import User
from app.schemas.ai_job import AIJobOut, GenerateColumnsRequest
from app.schemas.evaluation import AIReviewRequest, AIReviewResponse
from app.services.file_service import build_file_download_url
from mcp.tools.generate_review import generate_review
from mcp.tools.parse_nizom import parse_nizom


router = APIRouter(prefix="/ai", tags=["ai"])


async def _is_active_jury_assignment(
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
    return result.scalar_one_or_none() is not None


@router.get("/jobs/{job_id}", response_model=AIJobOut)
@limiter.limit(limit_ai_job_poll)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> AIJobOut:
    job = await db.get(AIJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job topilmadi")

    if current_user.role == UserRole.ADMIN:
        return AIJobOut.model_validate(job)

    if job.job_type == AIJobType.COLUMN_GEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    application = await db.get(Application, job.ref_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jobga bog'langan ariza topilmadi")

    is_owner = application.student_id == current_user.id
    is_assigned_jury = (
        current_user.role == UserRole.JURY
        and await _is_active_jury_assignment(db, application.scholarship_id, current_user.id)
    )
    if not (is_owner or is_assigned_jury):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    return AIJobOut.model_validate(job)


@router.post("/scholarships/{scholarship_id}/parse-nizom")
@limiter.limit(limit_ai_parse_nizom)
async def parse_nizom_endpoint(
    scholarship_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> dict:
    scholarship = await db.get(Scholarship, scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    if not scholarship.nizom_file_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avval nizom yuklanishi kerak",
        )

    nizom_file_url = build_file_download_url(scholarship.nizom_file_url)
    if not nizom_file_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nizom fayli uchun vaqtinchalik havola yaratib bo'lmadi",
        )

    parse_result = await parse_nizom(
        file_url=nizom_file_url,
        llm_provider=scholarship.ai_provider,
        llm_model=scholarship.ai_model,
    )

    return {
        "title": parse_result.title,
        "purpose": parse_result.purpose,
        "requirements": parse_result.requirements,
        "evaluation_criteria": [item.name for item in parse_result.evaluation_criteria],
        "evaluation_criteria_detailed": [
            {
                "name": item.name,
                "max_score": item.max_score,
                "description": item.description,
                "sub_scores": [{"label": sub.label, "score": sub.score} for sub in item.sub_scores],
            }
            for item in parse_result.evaluation_criteria
        ],
        "additional_docs": parse_result.additional_docs,
        "scoring_type": parse_result.scoring_type,
        "total_max_score": parse_result.total_max_score,
        "eligible_students": parse_result.eligible_students,
        "selection_stages": parse_result.selection_stages,
        "deadline_hint": parse_result.deadline_hint,
        "amount_hint": parse_result.amount_hint,
    }


@router.post("/scholarships/{scholarship_id}/generate-columns")
@limiter.limit(limit_ai_generate_columns)
async def generate_columns(
    scholarship_id: uuid.UUID,
    payload: GenerateColumnsRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> dict:
    scholarship = await db.get(Scholarship, scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    if not scholarship.nizom_file_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avval nizom yuklanishi kerak",
        )

    job = AIJob(
        job_type=AIJobType.COLUMN_GEN,
        ref_id=scholarship_id,
        model_used=format_llm_selection(scholarship.ai_provider, scholarship.ai_model),
        status=AIJobStatus.PENDING,
        input_data=payload.model_dump(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    try:
        from workers.tasks import run_column_generation

        run_column_generation.delay(
            job_id=str(job.id),
            scholarship_id=str(scholarship_id),
            purpose=payload.purpose,
            requirements=payload.requirements,
            criteria=payload.evaluation_criteria,
            docs=payload.additional_docs,
            total_max_score=payload.total_max_score,
            scoring_type=payload.scoring_type,
            eligible_students=payload.eligible_students,
            selection_stages=payload.selection_stages,
            llm_provider=scholarship.ai_provider,
            llm_model=scholarship.ai_model,
        )
    except Exception as exc:  # pragma: no cover
        job.status = AIJobStatus.FAILED
        job.error_msg = "Column generation taskini ishga tushirib bo'lmadi"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Column generation taskini ishga tushirib bo'lmadi",
        ) from exc

    return {
        "detail": "Ustun generatsiyasi boshlandi",
        "job_id": str(job.id),
    }


@router.post("/evaluations/{application_id}/ai-review", response_model=AIReviewResponse)
@limiter.limit(limit_ai_generate_review)
async def generate_ai_review(
    application_id: uuid.UUID,
    payload: AIReviewRequest,
    current_user: Annotated[User, Depends(require_jury)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> AIReviewResponse:
    app_result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.values).selectinload(ApplicationValue.column),
            selectinload(Application.scholarship).selectinload(Scholarship.columns),
            selectinload(Application.student),
        )
        .where(Application.id == application_id)
    )
    application = app_result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ariza topilmadi")

    is_assigned = await _is_active_jury_assignment(
        db=db,
        scholarship_id=application.scholarship_id,
        jury_id=current_user.id,
    )
    if not is_assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz bu stipendiya uchun hakam sifatida biriktirilmagansiz",
        )

    evaluation_result = await db.execute(
        select(Evaluation).where(
            Evaluation.application_id == application_id,
            Evaluation.jury_id == current_user.id,
        )
    )
    evaluation = evaluation_result.scalar_one_or_none()
    if evaluation is None or not evaluation.scores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avval balllar kiritilishi kerak",
        )

    columns_info = [
        {
            "id": str(column.id),
            "name": column.name,
            "max_score": column.max_score,
        }
        for column in application.scholarship.columns
    ]

    ai_analyses = [
        {
            "column_name": value.column.name,
            "analysis": value.ai_analysis,
        }
        for value in application.values
        if value.column is not None and value.column.ai_analyze and value.ai_analysis
    ]

    student_name = "Anonim nomzod" if application.scholarship.blind_review_enabled else application.student.full_name

    review_result = await generate_review(
        student_name=student_name,
        scholarship_title=application.scholarship.title,
        scores=evaluation.scores,
        columns_info=columns_info,
        ai_analyses=ai_analyses or None,
        jury_notes=payload.jury_notes,
        llm_provider=application.scholarship.ai_provider,
        llm_model=application.scholarship.ai_model,
    )

    # AI generated review ni evaluationga saqlab qo'yamiz.
    evaluation.final_comment = review_result.review_text
    evaluation.ai_generated = True
    await db.commit()

    return AIReviewResponse(**review_result.model_dump())
