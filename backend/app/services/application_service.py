from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationStatusLog, ApplicationValue
from app.models.enums import ApplicationStatus, ScholarshipStageType
from app.models.scholarship import JuryAssignment, Scholarship
from app.models.workflow import ScholarshipStage


async def get_application_or_404(
    db: AsyncSession,
    application_id: uuid.UUID,
    with_relations: bool = False,
) -> Application:
    query = select(Application)
    if with_relations:
        query = query.options(
            selectinload(Application.values).selectinload(ApplicationValue.column),
            selectinload(Application.scholarship).selectinload(Scholarship.columns),
            selectinload(Application.student),
            selectinload(Application.supervisor),
        )

    result = await db.execute(query.where(Application.id == application_id))
    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ariza topilmadi")

    return application


async def is_active_jury_assignment(
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


async def ensure_stage_allows(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    allowed_stage_types: tuple[ScholarshipStageType, ...],
) -> ScholarshipStage | None:
    existing_stage = await db.execute(
        select(ScholarshipStage.id)
        .where(ScholarshipStage.scholarship_id == scholarship_id)
        .limit(1)
    )
    if existing_stage.scalar_one_or_none() is None:
        return None

    now = datetime.now(timezone.utc)
    active_stage_result = await db.execute(
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
    active_stage = active_stage_result.scalar_one_or_none()
    if active_stage is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hozir faol bosqich yo'q",
        )

    if active_stage.stage_type not in allowed_stage_types:
        allowed_text = ", ".join(item.value for item in allowed_stage_types)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Hozir '{active_stage.stage_type.value}' bosqichi faol. "
                f"Ruxsat berilgan bosqichlar: {allowed_text}"
            ),
        )

    return active_stage


async def recalculate_winners_for_scholarship(
    db: AsyncSession,
    scholarship: Scholarship,
    *,
    changed_by_user_id: uuid.UUID | None = None,
    source: str = "system",
    note: str | None = None,
    status_log_ids_out: list[uuid.UUID] | None = None,
) -> list[str]:
    result = await db.execute(
        select(Application)
        .where(
            Application.scholarship_id == scholarship.id,
            Application.status.in_(
                [
                    ApplicationStatus.SUBMITTED,
                    ApplicationStatus.IN_REVIEW,
                    ApplicationStatus.WINNER,
                    ApplicationStatus.REJECTED,
                ]
            ),
        )
        .order_by(Application.total_score.desc().nullslast(), Application.created_at.asc())
        .limit(scholarship.max_winners)
    )
    winners = result.scalars().all()
    winner_ids = [str(application.id) for application in winners]
    winner_id_set = {application.id for application in winners}

    all_apps_result = await db.execute(
        select(Application).where(Application.scholarship_id == scholarship.id)
    )
    all_apps = all_apps_result.scalars().all()

    for application in all_apps:
        if application.id in winner_id_set:
            status_log = transition_application_status(
                db=db,
                application=application,
                new_status=ApplicationStatus.WINNER,
                changed_by_user_id=changed_by_user_id,
                source=source,
                note=note,
            )
            if status_log is not None and status_log_ids_out is not None:
                status_log_ids_out.append(status_log.id)
        elif application.status in (
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.IN_REVIEW,
            ApplicationStatus.WINNER,
            ApplicationStatus.REJECTED,
        ):
            status_log = transition_application_status(
                db=db,
                application=application,
                new_status=ApplicationStatus.REJECTED,
                changed_by_user_id=changed_by_user_id,
                source=source,
                note=note,
            )
            if status_log is not None and status_log_ids_out is not None:
                status_log_ids_out.append(status_log.id)

    return winner_ids


def add_application_status_log(
    db: AsyncSession,
    application: Application,
    *,
    previous_status: ApplicationStatus | None,
    new_status: ApplicationStatus,
    changed_by_user_id: uuid.UUID | None = None,
    source: str = "system",
    note: str | None = None,
) -> ApplicationStatusLog:
    if application.id is None:
        application.id = uuid.uuid4()

    log = ApplicationStatusLog(
        application_id=application.id,
        scholarship_id=application.scholarship_id,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=changed_by_user_id,
        source=source,
        note=note,
    )
    db.add(log)
    return log


def log_initial_application_status(
    db: AsyncSession,
    application: Application,
    *,
    changed_by_user_id: uuid.UUID | None = None,
    source: str = "system",
    note: str | None = None,
) -> ApplicationStatusLog:
    return add_application_status_log(
        db=db,
        application=application,
        previous_status=None,
        new_status=application.status,
        changed_by_user_id=changed_by_user_id,
        source=source,
        note=note,
    )


def transition_application_status(
    db: AsyncSession,
    application: Application,
    *,
    new_status: ApplicationStatus,
    changed_by_user_id: uuid.UUID | None = None,
    source: str = "system",
    note: str | None = None,
) -> ApplicationStatusLog | None:
    previous_status = application.status
    if previous_status == new_status:
        return None

    application.status = new_status
    return add_application_status_log(
        db=db,
        application=application,
        previous_status=previous_status,
        new_status=new_status,
        changed_by_user_id=changed_by_user_id,
        source=source,
        note=note,
    )
