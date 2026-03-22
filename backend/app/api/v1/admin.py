from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.ai_job import AIJob
from app.models.application import Application
from app.models.evaluation import Evaluation
from app.models.enums import ApplicationStatus
from app.models.scholarship import Scholarship
from app.models.user import User
from app.schemas.admin import (
    ApplicationConsistencyOut,
    AdminStatsOut,
    EvaluationConsistencyItem,
    RecentActivityItem,
    ScholarshipResultRow,
    ScholarshipResultsOut,
    TrendPoint,
)
from app.services.consistency_service import (
    build_evaluation_consistency_items,
    build_evaluation_consistency_summary,
)
from app.services.export_service import (
    build_scholarship_results_excel,
    build_scholarship_results_pdf,
    slugify_filename,
)


router = APIRouter(prefix="/admin", tags=["admin"])


async def _count_by_group(db: AsyncSession, stmt) -> dict[str, int]:
    result = await db.execute(stmt)
    rows = result.all()
    return {str(key.value if hasattr(key, "value") else key): int(count) for key, count in rows}


async def _build_application_trend(db: AsyncSession, days: int = 7) -> list[TrendPoint]:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    stmt = (
        select(
            func.date(Application.created_at).label("bucket"),
            func.count(Application.id),
        )
        .where(func.date(Application.created_at) >= start_date)
        .group_by(func.date(Application.created_at))
        .order_by(func.date(Application.created_at))
    )
    result = await db.execute(stmt)
    rows = result.all()
    counts_by_date = {bucket.isoformat(): int(count) for bucket, count in rows if bucket is not None}

    return [
        TrendPoint(
            date=(start_date + timedelta(days=index)).isoformat(),
            count=counts_by_date.get((start_date + timedelta(days=index)).isoformat(), 0),
        )
        for index in range(days)
    ]


async def _build_recent_activity(db: AsyncSession, limit: int = 12) -> list[RecentActivityItem]:
    scholarships_result = await db.execute(
        select(Scholarship).order_by(Scholarship.created_at.desc()).limit(limit)
    )
    applications_result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.student),
            selectinload(Application.scholarship),
        )
        .order_by(Application.created_at.desc())
        .limit(limit)
    )
    ai_jobs_result = await db.execute(select(AIJob).order_by(AIJob.created_at.desc()).limit(limit))

    scholarship_items = [
        RecentActivityItem(
            entity_type="scholarship",
            entity_id=str(item.id),
            title=item.title,
            subtitle="Yangi stipendiya yaratildi",
            status=str(item.status.value if hasattr(item.status, "value") else item.status),
            created_at=item.created_at,
        )
        for item in scholarships_result.scalars().all()
    ]

    application_items = [
        RecentActivityItem(
            entity_type="application",
            entity_id=str(item.id),
            title=item.student.full_name if item.student is not None else "Ariza yuborildi",
            subtitle=item.scholarship.title if item.scholarship is not None else "Stipendiya arizasi",
            status=str(item.status.value if hasattr(item.status, "value") else item.status),
            created_at=item.created_at,
        )
        for item in applications_result.scalars().all()
    ]

    ai_job_items = [
        RecentActivityItem(
            entity_type="ai_job",
            entity_id=str(item.id),
            title=f"AI job: {item.job_type.value if hasattr(item.job_type, 'value') else item.job_type}",
            subtitle=item.model_used or "LLM task",
            status=str(item.status.value if hasattr(item.status, "value") else item.status),
            created_at=item.created_at,
        )
        for item in ai_jobs_result.scalars().all()
    ]

    items = scholarship_items + application_items + ai_job_items
    items.sort(key=lambda entry: entry.created_at, reverse=True)
    return items[:limit]


async def _build_scholarship_results_payload(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
) -> ScholarshipResultsOut:
    scholarship = await db.get(Scholarship, scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.student),
            selectinload(Application.evaluations).selectinload(Evaluation.jury),
        )
        .where(Application.scholarship_id == scholarship_id)
        .order_by(Application.total_score.desc().nullslast(), Application.created_at.asc())
    )
    applications = result.scalars().all()

    rows: list[ScholarshipResultRow] = []
    rank = 0
    for application in applications:
        rank_value: int | None = None
        if application.status in (
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.IN_REVIEW,
            ApplicationStatus.WINNER,
            ApplicationStatus.REJECTED,
        ) and application.total_score is not None:
            rank += 1
            rank_value = rank

        rows.append(
            ScholarshipResultRow(
                rank=rank_value,
                application_id=application.id,
                student_id=application.student_id,
                student_name=application.student.full_name if application.student is not None else "Unknown",
                status=application.status,
                total_score=application.total_score,
                is_winner=application.status == ApplicationStatus.WINNER,
                submitted_at=application.submitted_at,
                consistency=build_evaluation_consistency_summary(application.evaluations),
            )
        )

    winners_count = sum(1 for row in rows if row.is_winner)

    return ScholarshipResultsOut(
        scholarship_id=scholarship.id,
        scholarship_title=scholarship.title,
        scholarship_status=scholarship.status,
        max_winners=scholarship.max_winners,
        winners_count=winners_count,
        rows=rows,
    )


@router.get("/stats", response_model=AdminStatsOut)
async def get_admin_stats(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminStatsOut:
    scholarship_status_counts = await _count_by_group(
        db,
        select(Scholarship.status, func.count(Scholarship.id)).group_by(Scholarship.status),
    )
    application_status_counts = await _count_by_group(
        db,
        select(Application.status, func.count(Application.id)).group_by(Application.status),
    )
    user_role_counts = await _count_by_group(
        db,
        select(User.role, func.count(User.id)).group_by(User.role),
    )
    ai_job_status_counts = await _count_by_group(
        db,
        select(AIJob.status, func.count(AIJob.id)).group_by(AIJob.status),
    )
    ai_job_type_counts = await _count_by_group(
        db,
        select(AIJob.job_type, func.count(AIJob.id)).group_by(AIJob.job_type),
    )

    total_scholarships = int(
        (await db.execute(select(func.count(Scholarship.id)))).scalar_one() or 0
    )
    total_applications = int(
        (await db.execute(select(func.count(Application.id)))).scalar_one() or 0
    )
    total_users = int((await db.execute(select(func.count(User.id)))).scalar_one() or 0)
    total_ai_jobs = int((await db.execute(select(func.count(AIJob.id)))).scalar_one() or 0)
    application_trend = await _build_application_trend(db=db)
    recent_activity = await _build_recent_activity(db=db)

    return AdminStatsOut(
        total_scholarships=total_scholarships,
        scholarships_by_status=scholarship_status_counts,
        total_applications=total_applications,
        applications_by_status=application_status_counts,
        total_users=total_users,
        users_by_role=user_role_counts,
        total_ai_jobs=total_ai_jobs,
        ai_jobs_by_status=ai_job_status_counts,
        ai_jobs_by_type=ai_job_type_counts,
        application_trend=application_trend,
        recent_activity=recent_activity,
    )


@router.get("/scholarships/{scholarship_id}/results", response_model=ScholarshipResultsOut)
async def get_scholarship_results(
    scholarship_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScholarshipResultsOut:
    return await _build_scholarship_results_payload(db=db, scholarship_id=scholarship_id)


@router.get("/scholarships/{scholarship_id}/results/export")
async def export_scholarship_results(
    scholarship_id: uuid.UUID,
    export_format: Annotated[Literal["xlsx", "pdf"], Query(alias="format")],
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    results = await _build_scholarship_results_payload(db=db, scholarship_id=scholarship_id)

    if export_format == "xlsx":
        content = build_scholarship_results_excel(results)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = build_scholarship_results_pdf(results)
        media_type = "application/pdf"

    filename = (
        f"{slugify_filename(results.scholarship_title)}-results-"
        f"{datetime.now(timezone.utc).date().isoformat()}.{export_format}"
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/applications/{application_id}/consistency", response_model=ApplicationConsistencyOut)
async def get_application_consistency(
    application_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationConsistencyOut:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.evaluations).selectinload(Evaluation.jury))
        .where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ariza topilmadi")

    summary = build_evaluation_consistency_summary(application.evaluations)
    items: list[EvaluationConsistencyItem] = build_evaluation_consistency_items(application.evaluations)

    return ApplicationConsistencyOut(
        application_id=application.id,
        scholarship_id=application.scholarship_id,
        student_id=application.student_id,
        application_status=application.status,
        summary=summary,
        evaluations=items,
    )
