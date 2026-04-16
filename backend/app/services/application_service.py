from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationStatusLog, ApplicationValue
from app.models.enums import ApplicationStatus, ScholarshipStageType, ColumnFieldType, UserRole
from app.models.scholarship import JuryAssignment, Scholarship, ScholarshipColumn
from app.models.workflow import ScholarshipStage


async def get_application_or_404(
    db: AsyncSession,
    application_id: uuid.UUID,
    with_relations: bool = False,
) -> Application:
    from app.repositories.application import application as application_repo

    if with_relations:
        application_obj = await application_repo.get_with_relations(db, id=application_id)
    else:
        application_obj = await application_repo.get(db, id=application_id)

    if application_obj is None:
        from app.core.constants import ErrorMessages
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorMessages.APPLICATION_NOT_FOUND)

    return application_obj


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
        from app.core.constants import ErrorMessages
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorMessages.NO_ACTIVE_STAGE,
        )

    if active_stage.stage_type not in allowed_stage_types:
        from app.core.constants import ErrorMessages
        allowed_text = ", ".join(item.value for item in allowed_stage_types)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorMessages.INVALID_ACTIVE_STAGE.format(active=active_stage.stage_type.value, allowed=allowed_text),
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


def _validate_number_value(column: ScholarshipColumn, value_text: str | None) -> None:
    from app.models.enums import ColumnFieldType

    if column.field_type != ColumnFieldType.NUMBER or value_text is None:
        return

    stripped = value_text.strip()
    if not stripped:
        return

    try:
        numeric_value = float(stripped)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{column.name}' uchun raqam kiriting",
        ) from exc

    if column.input_min is not None and numeric_value < float(column.input_min):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{column.name}' uchun qiymat {column.input_min} dan kichik bo‘lishi mumkin emas",
        )

    if column.input_max is not None and numeric_value > float(column.input_max):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{column.name}' uchun qiymat {column.input_max} dan katta bo‘lishi mumkin emas",
        )


async def submit_application(
    db: AsyncSession, application_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Application, ApplicationStatusLog | None]:
    from app.models.enums import ColumnFieldType, ScholarshipStatus
    from app.services.plagiarism_service import refresh_application_plagiarism_checks
    
    result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.values),
            selectinload(Application.scholarship).selectinload(Scholarship.columns),
        )
        .where(
            Application.id == application_id,
            Application.student_id == user_id,
        )
    )
    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ariza topilmadi")

    if application.status != ApplicationStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ariza allaqachon topshirilgan",
        )

    if application.scholarship.status != ScholarshipStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stipendiya hozir ochiq emas",
        )

    await ensure_stage_allows(
        db=db,
        scholarship_id=application.scholarship_id,
        allowed_stage_types=(ScholarshipStageType.APPLICATION,),
    )

    columns_by_id = {column.id: column for column in application.scholarship.columns}
    filled_columns: set[uuid.UUID] = set()
    for value in application.values:
        column = columns_by_id.get(value.column_id)
        if column is None:
            continue

        if column.field_type == ColumnFieldType.FILE:
            if value.value_file_url:
                filled_columns.add(value.column_id)
            continue

        if value.value_text and value.value_text.strip():
            filled_columns.add(value.column_id)
    required_columns = {
        column.id
        for column in application.scholarship.columns
        if column.is_required
    }
    missing_columns = [str(column_id) for column_id in (required_columns - filled_columns)]

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Majburiy maydonlar to'ldirilmagan", "missing_columns": missing_columns},
        )

    for value in application.values:
        column = columns_by_id.get(value.column_id)
        if column is not None:
            _validate_number_value(column, value.value_text)

    await refresh_application_plagiarism_checks(
        db=db,
        application=application,
        columns_by_id=columns_by_id,
        target_column_ids={
            column.id
            for column in application.scholarship.columns
            if column.field_type in (ColumnFieldType.TEXT, ColumnFieldType.TEXTAREA, ColumnFieldType.URL)
        },
    )

    status_log = transition_application_status(
        db=db,
        application=application,
        new_status=ApplicationStatus.SUBMITTED,
        changed_by_user_id=user_id,
        source="student_submit",
        note="Talaba arizani topshirdi",
    )
    application.submitted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(application)
    
    return application, status_log


async def update_draft_application(
    db: AsyncSession, application_id: uuid.UUID, user_id: uuid.UUID, payload_data: dict
) -> Application:
    from app.models.enums import ColumnFieldType
    from app.models.user import User
    from app.services.plagiarism_service import refresh_application_plagiarism_checks
    
    result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.values),
            selectinload(Application.scholarship).selectinload(Scholarship.columns),
        )
        .where(
            Application.id == application_id,
            Application.student_id == user_id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ariza topilmadi")

    if application.status != ApplicationStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topshirilgan arizani o'zgartirish mumkin emas",
        )

    await ensure_stage_allows(
        db=db,
        scholarship_id=application.scholarship_id,
        allowed_stage_types=(ScholarshipStageType.APPLICATION,),
    )

    if "supervisor_id" in payload_data:
        supervisor_id = payload_data["supervisor_id"]
        if supervisor_id is None:
            application.supervisor_id = None
        else:
            supervisor = await db.get(User, supervisor_id)
            if (
                supervisor is None
                or not getattr(supervisor, "is_supervisor", False)
                or getattr(supervisor, "role", None) == UserRole.STUDENT
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Noto'g'ri ilmiy rahbar tanlandi",
                )
            application.supervisor_id = supervisor_id

    values_dict = payload_data.get("values")
    if values_dict:
        columns_by_id = {column.id: column for column in application.scholarship.columns}
        values_by_column_id = {value.column_id: value for value in application.values}
        touched_text_column_ids: set[uuid.UUID] = set()

        for raw_column_id, value_text in values_dict.items():
            try:
                column_id = uuid.UUID(str(raw_column_id))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Noto'g'ri column_id: {raw_column_id}",
                ) from exc

            if column_id not in columns_by_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ustun ushbu stipendiyaga tegishli emas",
                )

            column = columns_by_id[column_id]
            existing_value = values_by_column_id.get(column_id)

            if column.field_type == ColumnFieldType.FILE:
                if value_text is None and existing_value is not None:
                    existing_value.value_file_url = None
                continue

            _validate_number_value(column, value_text)
            if column.field_type in (ColumnFieldType.TEXT, ColumnFieldType.TEXTAREA, ColumnFieldType.URL):
                touched_text_column_ids.add(column_id)

            if existing_value is not None:
                existing_value.value_text = value_text
            elif value_text is not None:
                new_value = ApplicationValue(
                    application_id=application.id,
                    column_id=column_id,
                    value_text=value_text,
                )
                db.add(new_value)
                application.values.append(new_value)
                values_by_column_id[column_id] = new_value

        if touched_text_column_ids:
            await refresh_application_plagiarism_checks(
                db=db,
                application=application,
                columns_by_id=columns_by_id,
                target_column_ids=touched_text_column_ids,
            )

    await db.commit()
    return application
