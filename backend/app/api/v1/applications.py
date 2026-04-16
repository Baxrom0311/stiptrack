import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_student
from app.core.rate_limit import (
    limit_appeal_create,
    limit_appeal_upload,
    limit_application_submit,
    limit_value_upload,
    limit_winner_announce,
    limiter,
)
from app.models.application import Application, ApplicationStatusLog, ApplicationValue, StudentAchievement
from app.models.enums import (
    AppealStatus,
    ApplicationStatus,
    ColumnFieldType,
    ScholarshipStageType,
    ScholarshipStatus,
    UserRole,
)
from app.models.scholarship import Scholarship, ScholarshipColumn
from app.models.user import User
from app.models.workflow import Appeal, ScholarshipStage
from app.schemas.achievement import AchievementOut
from app.schemas.application import (
    AnnounceWinnersResponse,
    ApplicationCreateResponse,
    ApplicationDetail,
    ApplicationListOut,
    ApplicationOut,
    ApplicationValuePlagiarismMatchOut,
    ApplicationStatusLogOut,
    ApplicationStatusUpdate,
    ApplicationValueUpdate,
)
from app.schemas.workflow import AppealCreate, AppealDecision, AppealOut
from app.services.file_service import build_file_download_url, normalize_stored_file_ref, upload_file
from app.services.application_service import (
    ensure_stage_allows as ensure_stage_allows_service,
    get_application_or_404 as get_application_or_404_service,
    is_active_jury_assignment as is_active_jury_assignment_service,
    log_initial_application_status,
    recalculate_winners_for_scholarship as recalculate_winners_for_scholarship_service,
    transition_application_status,
)
from app.services.notification_service import queue_application_status_email_tasks
from app.services.plagiarism_service import refresh_application_plagiarism_checks


logger = logging.getLogger(__name__)

router = APIRouter(tags=["applications"])

APPEALABLE_APPLICATION_STATUSES = {
    ApplicationStatus.WINNER,
    ApplicationStatus.REJECTED,
}


def _validate_number_value(column: ScholarshipColumn, value_text: str | None) -> None:
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


async def _get_application_or_404(
    db: AsyncSession,
    application_id: uuid.UUID,
    with_relations: bool = False,
) -> Application:
    return await get_application_or_404_service(
        db=db,
        application_id=application_id,
        with_relations=with_relations,
    )


async def _is_active_jury_assignment(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
) -> bool:
    return await is_active_jury_assignment_service(
        db=db,
        scholarship_id=scholarship_id,
        jury_id=jury_id,
    )


async def _ensure_stage_allows(
    db: AsyncSession,
    scholarship_id: uuid.UUID,
    allowed_stage_types: tuple[ScholarshipStageType, ...],
) -> ScholarshipStage | None:
    return await ensure_stage_allows_service(
        db=db,
        scholarship_id=scholarship_id,
        allowed_stage_types=allowed_stage_types,
    )


async def _recalculate_winners_for_scholarship(
    db: AsyncSession,
    scholarship: Scholarship,
    *,
    changed_by_user_id: uuid.UUID | None = None,
    source: str = "system",
    note: str | None = None,
    status_log_ids_out: list[uuid.UUID] | None = None,
) -> list[str]:
    return await recalculate_winners_for_scholarship_service(
        db=db,
        scholarship=scholarship,
        changed_by_user_id=changed_by_user_id,
        source=source,
        note=note,
        status_log_ids_out=status_log_ids_out,
    )


async def _ensure_can_view_application(
    db: AsyncSession,
    application: Application,
    current_user: User,
) -> None:
    is_owner = application.student_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN
    is_assigned_jury = False
    if current_user.role == UserRole.JURY:
        is_assigned_jury = await _is_active_jury_assignment(
            db=db,
            scholarship_id=application.scholarship_id,
            jury_id=current_user.id,
        )

    if not (is_owner or is_admin or is_assigned_jury):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")


def _is_blind_review_for_jury(application: Application, current_user: User) -> bool:
    scholarship = getattr(application, "scholarship", None)
    return current_user.role == UserRole.JURY and bool(
        scholarship is not None and getattr(scholarship, "blind_review_enabled", False)
    )


def _serialize_application_list_item(application: Application, current_user: User) -> ApplicationListOut:
    payload = ApplicationListOut.model_validate(application)
    if _is_blind_review_for_jury(application, current_user):
        payload.student = None
    return payload


def _serialize_application_detail(application: Application, current_user: User) -> ApplicationDetail:
    payload = ApplicationDetail.model_validate(application)
    is_blind_jury = _is_blind_review_for_jury(application, current_user)
    if is_blind_jury:
        payload.student = None
        payload.supervisor = None
    if current_user.role == UserRole.STUDENT:
        for value in payload.values:
            value.plagiarism_score = None
            value.plagiarism_matches = None
            value.plagiarism_checked_at = None
    elif is_blind_jury:
        for value in payload.values:
            if not value.plagiarism_matches:
                continue
            value.plagiarism_matches = [
                ApplicationValuePlagiarismMatchOut(
                    application_id=None,
                    application_status=match.application_status,
                    similarity_percent=match.similarity_percent,
                    matched_text_excerpt=match.matched_text_excerpt,
                )
                for match in value.plagiarism_matches
            ]
    return payload


def _serialize_application_status_log(
    status_log: ApplicationStatusLog,
    *,
    hide_actor: bool,
) -> ApplicationStatusLogOut:
    payload = ApplicationStatusLogOut.model_validate(status_log)
    if hide_actor:
        payload.changed_by_user = None
    return payload


async def _check_application_plagiarism(
    db: AsyncSession,
    *,
    application: Application,
    columns_by_id: dict[uuid.UUID, ScholarshipColumn] | None = None,
    target_column_ids: set[uuid.UUID] | None = None,
) -> None:
    await refresh_application_plagiarism_checks(
        db=db,
        application=application,
        columns_by_id=columns_by_id,
        target_column_ids=target_column_ids,
    )


@router.post("/scholarships/{scholarship_id}/apply", response_model=ApplicationCreateResponse)
async def create_or_get_application(
    scholarship_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationCreateResponse:
    scholarship = await db.get(Scholarship, scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    if scholarship.status != ScholarshipStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat ochiq stipendiyaga ariza topshirish mumkin",
        )

    await _ensure_stage_allows(
        db=db,
        scholarship_id=scholarship_id,
        allowed_stage_types=(ScholarshipStageType.APPLICATION,),
    )

    existing = await db.execute(
        select(Application).where(
            Application.scholarship_id == scholarship_id,
            Application.student_id == current_user.id,
        )
    )
    application = existing.scalar_one_or_none()

    if application is None:
        application = Application(
            scholarship_id=scholarship_id,
            student_id=current_user.id,
            status=ApplicationStatus.DRAFT,
        )
        db.add(application)
        log_initial_application_status(
            db=db,
            application=application,
            changed_by_user_id=current_user.id,
            source="student_apply",
            note="Ariza qoralama holatida yaratildi",
        )
        await db.commit()
        await db.refresh(application)

    return ApplicationCreateResponse(application_id=application.id, status=application.status)


@router.get("/scholarships/{scholarship_id}/apply", response_model=ApplicationDetail)
async def get_my_application_for_scholarship(
    scholarship_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationDetail:
    scholarship = await db.get(Scholarship, scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.values).selectinload(ApplicationValue.column),
            selectinload(Application.scholarship).selectinload(Scholarship.columns),
            selectinload(Application.student),
            selectinload(Application.supervisor),
        )
        .where(
            Application.scholarship_id == scholarship_id,
            Application.student_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()

    if application is None:
        application = Application(
            scholarship_id=scholarship_id,
            student_id=current_user.id,
            status=ApplicationStatus.DRAFT,
        )
        db.add(application)
        log_initial_application_status(
            db=db,
            application=application,
            changed_by_user_id=current_user.id,
            source="student_apply",
            note="Ariza qoralama holatida yaratildi",
        )
        await db.commit()

        result = await db.execute(
            select(Application)
            .options(
                selectinload(Application.values).selectinload(ApplicationValue.column),
                selectinload(Application.scholarship).selectinload(Scholarship.columns),
                selectinload(Application.student),
                selectinload(Application.supervisor),
            )
            .where(Application.id == application.id)
        )
        application = result.scalar_one()

    return _serialize_application_detail(application, current_user)


@router.get("/applications/my", response_model=list[ApplicationListOut])
async def my_applications(
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApplicationListOut]:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.scholarship))
        .where(Application.student_id == current_user.id)
        .order_by(Application.created_at.desc())
    )
    applications = result.scalars().all()
    return [_serialize_application_list_item(item, current_user) for item in applications]


@router.get("/applications/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationDetail:
    application = await _get_application_or_404(db, application_id, with_relations=True)
    await _ensure_can_view_application(db=db, application=application, current_user=current_user)
    return _serialize_application_detail(application, current_user)


@router.get("/applications/{application_id}/achievements", response_model=list[AchievementOut])
async def get_application_achievements(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AchievementOut]:
    application = await _get_application_or_404(db, application_id)
    await _ensure_can_view_application(db=db, application=application, current_user=current_user)
    result = await db.execute(
        select(StudentAchievement)
        .where(StudentAchievement.student_id == application.student_id)
        .order_by(
            StudentAchievement.date.desc().nullslast(),
            StudentAchievement.created_at.desc(),
        )
    )
    achievements = result.scalars().all()
    return [AchievementOut.model_validate(item) for item in achievements]


@router.patch("/applications/{application_id}", response_model=ApplicationDetail)
async def update_application(
    application_id: uuid.UUID,
    payload: ApplicationValueUpdate,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationOut:
    from app.services.application_service import update_draft_application
    
    application = await update_draft_application(
        db=db,
        application_id=application_id,
        user_id=current_user.id,
        payload_data=payload.model_dump(exclude_unset=True),
    )
    
    refreshed = await _get_application_or_404(db, application.id, with_relations=True)
    return _serialize_application_detail(refreshed, current_user)


@router.get("/applications/{application_id}/history", response_model=list[ApplicationStatusLogOut])
async def list_application_status_history(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApplicationStatusLogOut]:
    application = await _get_application_or_404(db, application_id, with_relations=True)
    await _ensure_can_view_application(db=db, application=application, current_user=current_user)
    hide_actor = _is_blind_review_for_jury(application, current_user)

    result = await db.execute(
        select(ApplicationStatusLog)
        .options(selectinload(ApplicationStatusLog.changed_by_user))
        .where(ApplicationStatusLog.application_id == application_id)
        .order_by(ApplicationStatusLog.created_at.desc())
    )
    return [
        _serialize_application_status_log(item, hide_actor=hide_actor)
        for item in result.scalars().all()
    ]


@router.post("/applications/{application_id}/values/{column_id}/upload")
@limiter.limit(limit_value_upload)
async def upload_value_file(
    application_id: uuid.UUID,
    column_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    request: Request = None,
) -> dict:
    result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.values),
            selectinload(Application.scholarship).selectinload(Scholarship.columns),
        )
        .where(
            Application.id == application_id,
            Application.student_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ariza topilmadi")

    if application.status != ApplicationStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat draft ariza uchun fayl yuklash mumkin",
        )

    await _ensure_stage_allows(
        db=db,
        scholarship_id=application.scholarship_id,
        allowed_stage_types=(ScholarshipStageType.APPLICATION,),
    )

    columns_by_id = {column.id: column for column in application.scholarship.columns}
    column = columns_by_id.get(column_id)
    if column is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ustun ushbu stipendiyaga tegishli emas",
        )
    if column.field_type != ColumnFieldType.FILE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat fayl turidagi ustun uchun upload qilish mumkin",
        )

    file_ref = await upload_file(file=file, folder="application")

    existing_value = next((value for value in application.values if value.column_id == column_id), None)
    if existing_value is None:
        db.add(
            ApplicationValue(
                application_id=application.id,
                column_id=column_id,
                value_file_url=file_ref,
            )
        )
    else:
        existing_value.value_text = None
        existing_value.value_file_url = file_ref

    await db.commit()

    return {"file_url": build_file_download_url(file_ref)}


@router.post("/applications/{application_id}/submit", response_model=ApplicationOut)
@limiter.limit(limit_application_submit)
async def submit_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> ApplicationOut:
    from app.services.application_service import submit_application as submit_app_service

    application, status_log = await submit_app_service(
        db=db,
        application_id=application_id,
        user_id=current_user.id,
    )
    
    if status_log is not None:
        queue_application_status_email_tasks([status_log.id])
        
    should_run_ai = application.scholarship.ai_analysis_enabled and any(
        column.ai_analyze for column in application.scholarship.columns
    )

    if should_run_ai:
        try:
            from workers.tasks import run_application_analysis

            run_application_analysis.delay(str(application.id))
        except Exception:
            logger.exception("AI ariza tahlili taskini ishga tushirib bo'lmadi: %s", application.id)

    return ApplicationOut.model_validate(application)


@router.get("/scholarships/{scholarship_id}/applications", response_model=list[ApplicationListOut])
async def list_scholarship_applications(
    scholarship_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    app_status: ApplicationStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ApplicationListOut]:
    if current_user.role not in (UserRole.ADMIN, UserRole.JURY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    if current_user.role == UserRole.JURY:
        is_assigned = await _is_active_jury_assignment(
            db=db,
            scholarship_id=scholarship_id,
            jury_id=current_user.id,
        )
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Siz bu stipendiya uchun hakam sifatida biriktirilmagansiz",
            )

    query = (
        select(Application)
        .options(selectinload(Application.student), selectinload(Application.scholarship))
        .where(Application.scholarship_id == scholarship_id)
    )

    if app_status is not None:
        query = query.where(Application.status == app_status)

    query = query.order_by(Application.total_score.desc().nullslast(), Application.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    applications = result.scalars().all()
    return [_serialize_application_list_item(item, current_user) for item in applications]


@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
async def update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationOut:
    application = await _get_application_or_404(db, application_id)

    status_log = transition_application_status(
        db=db,
        application=application,
        new_status=payload.status,
        changed_by_user_id=getattr(_, "id", None),
        source="admin_manual",
        note="Admin ariza holatini qo'lda yangiladi",
    )
    if payload.status == ApplicationStatus.SUBMITTED and application.submitted_at is None:
        application.submitted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(application)
    if status_log is not None:
        queue_application_status_email_tasks([status_log.id])
    return ApplicationOut.model_validate(application)


@router.post("/scholarships/{scholarship_id}/announce-winners", response_model=AnnounceWinnersResponse)
@limiter.limit(limit_winner_announce)
async def announce_winners(
    scholarship_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> AnnounceWinnersResponse:
    scholarship = await db.get(Scholarship, scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    await _ensure_stage_allows(
        db=db,
        scholarship_id=scholarship_id,
        allowed_stage_types=(ScholarshipStageType.FINAL_DECISION,),
    )

    status_log_ids: list[uuid.UUID] = []
    winner_ids = await _recalculate_winners_for_scholarship(
        db=db,
        scholarship=scholarship,
        changed_by_user_id=getattr(_, "id", None),
        source="winner_announcement",
        note="Yakuniy g'oliblar qayta hisoblandi",
        status_log_ids_out=status_log_ids,
    )

    scholarship.status = ScholarshipStatus.DONE

    await db.commit()
    queue_application_status_email_tasks(status_log_ids)

    return AnnounceWinnersResponse(
        detail=f"{len(winner_ids)} ta g'olib e'lon qilindi",
        winner_ids=winner_ids,
    )


@router.post("/applications/{application_id}/appeals", response_model=AppealOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(limit_appeal_create)
async def create_appeal(
    application_id: uuid.UUID,
    payload: AppealCreate,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> AppealOut:
    application = await _get_application_or_404(db, application_id)
    if application.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    scholarship = await db.get(Scholarship, application.scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    if scholarship.status != ScholarshipStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apellyatsiya faqat yakunlangan stipendiyada ochiladi",
        )
    if application.status not in APPEALABLE_APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apellyatsiya faqat yakuniy natija chiqqan ariza uchun ochiladi",
        )

    await _ensure_stage_allows(
        db=db,
        scholarship_id=scholarship.id,
        allowed_stage_types=(ScholarshipStageType.APPEAL,),
    )

    existing = await db.execute(
        select(Appeal).where(
            Appeal.application_id == application_id,
            Appeal.student_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ushbu ariza uchun apellyatsiya allaqachon yuborilgan",
        )

    appeal = Appeal(
        scholarship_id=application.scholarship_id,
        application_id=application_id,
        student_id=current_user.id,
        status=AppealStatus.SUBMITTED,
        reason=payload.reason,
        attachment_url=normalize_stored_file_ref(payload.attachment_url),
        filed_at=datetime.now(timezone.utc),
        score_before=application.total_score,
    )
    db.add(appeal)
    await db.commit()
    await db.refresh(appeal)
    return AppealOut.model_validate(appeal)


@router.post("/applications/{application_id}/appeals/upload")
@limiter.limit(limit_appeal_upload)
async def upload_appeal_file(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    request: Request = None,
) -> dict:
    application = await _get_application_or_404(db, application_id)
    if application.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    scholarship = await db.get(Scholarship, application.scholarship_id)
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")

    if scholarship.status != ScholarshipStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apellyatsiya fayli faqat yakunlangan stipendiyada yuklanadi",
        )
    if application.status not in APPEALABLE_APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apellyatsiya fayli faqat yakuniy natija chiqqan ariza uchun yuklanadi",
        )

    await _ensure_stage_allows(
        db=db,
        scholarship_id=scholarship.id,
        allowed_stage_types=(ScholarshipStageType.APPEAL,),
    )

    file_ref = await upload_file(file=file, folder="appeal")
    return {"file_url": build_file_download_url(file_ref)}


@router.get("/applications/{application_id}/appeals", response_model=list[AppealOut])
async def list_application_appeals(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AppealOut]:
    application = await _get_application_or_404(db, application_id)
    await _ensure_can_view_application(db=db, application=application, current_user=current_user)
    result = await db.execute(
        select(Appeal)
        .where(Appeal.application_id == application_id)
        .order_by(Appeal.filed_at.desc())
    )
    return [AppealOut.model_validate(item) for item in result.scalars().all()]


@router.get("/appeals", response_model=list[AppealOut])
async def list_appeals(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scholarship_id: uuid.UUID | None = Query(default=None),
    appeal_status: AppealStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AppealOut]:
    query = select(Appeal)
    if scholarship_id is not None:
        query = query.where(Appeal.scholarship_id == scholarship_id)
    if appeal_status is not None:
        query = query.where(Appeal.status == appeal_status)

    query = query.order_by(Appeal.filed_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return [AppealOut.model_validate(item) for item in result.scalars().all()]


@router.patch("/appeals/{appeal_id}/decision", response_model=AppealOut)
async def decide_appeal(
    appeal_id: uuid.UUID,
    payload: AppealDecision,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppealOut:
    appeal = await db.get(Appeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Apellyatsiya topilmadi")

    if payload.status == AppealStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision endpointda status submitted bo'lolmaydi",
        )

    if payload.status == AppealStatus.ACCEPTED and payload.score_after is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appeal accepted bo'lsa score_after berilishi shart",
        )

    appeal.status = payload.status
    appeal.response_text = payload.response_text

    if payload.status == AppealStatus.UNDER_REVIEW:
        appeal.resolved_by = None
        appeal.resolved_at = None
    else:
        appeal.resolved_by = current_user.id
        appeal.resolved_at = datetime.now(timezone.utc)

    status_log_ids: list[uuid.UUID] = []
    if payload.score_after is not None:
        appeal.score_after = payload.score_after
        if payload.status == AppealStatus.ACCEPTED:
            application = await db.get(Application, appeal.application_id)
            if application is not None:
                application.total_score = payload.score_after
                scholarship = await db.get(Scholarship, application.scholarship_id)
                if scholarship is not None and scholarship.status == ScholarshipStatus.DONE:
                    await _recalculate_winners_for_scholarship(
                        db=db,
                        scholarship=scholarship,
                        changed_by_user_id=current_user.id,
                        source="appeal_decision",
                        note="Apellyatsiya qaroridan keyin natija qayta hisoblandi",
                        status_log_ids_out=status_log_ids,
                    )

    await db.commit()
    await db.refresh(appeal)
    queue_application_status_email_tasks(status_log_ids)
    return AppealOut.model_validate(appeal)
