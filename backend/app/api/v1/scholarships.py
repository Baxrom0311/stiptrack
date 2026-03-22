import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.rate_limit import limit_nizom_upload, limiter
from app.models.enums import ColumnFieldType, ScholarshipStatus, UserRole
from app.models.scholarship import JuryAssignment, Scholarship, ScholarshipColumn
from app.models.user import User
from app.schemas.scholarship import (
    ColumnCreate,
    ColumnOut,
    ColumnReorder,
    ColumnUpdate,
    JuryAssignRequest,
    JuryOut,
    ScholarshipCreate,
    ScholarshipDetail,
    ScholarshipOut,
    ScholarshipUpdate,
    StatusUpdate,
)
from app.services.scholarship_service import (
    change_scholarship_status as change_scholarship_status_service,
    get_scholarship_or_404 as get_scholarship_or_404_service,
    list_scholarships as list_scholarships_service,
)
from app.services.file_service import build_file_download_url, upload_file

router = APIRouter(prefix="/scholarships", tags=["scholarships"])

async def _get_scholarship_or_404(db: AsyncSession, scholarship_id: uuid.UUID) -> Scholarship:
    return await get_scholarship_or_404_service(db=db, scholarship_id=scholarship_id)


def _normalize_column_payload(payload: dict, field_type: ColumnFieldType) -> dict:
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
            detail="Number ustunida min qiymat max qiymatdan katta bo‘lishi mumkin emas",
        )
    return normalized


@router.get("", response_model=list[ScholarshipOut])
async def list_scholarships(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: ScholarshipStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ScholarshipOut]:
    scholarships = await list_scholarships_service(
        db=db,
        current_user_role=current_user.role,
        status_filter=status_filter,
        search=search,
        skip=skip,
        limit=limit,
    )
    return [ScholarshipOut.model_validate(item) for item in scholarships]


@router.post("", response_model=ScholarshipOut, status_code=status.HTTP_201_CREATED)
async def create_scholarship(
    payload: ScholarshipCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScholarshipOut:
    scholarship = Scholarship(created_by=current_user.id, **payload.model_dump())
    db.add(scholarship)
    await db.commit()
    await db.refresh(scholarship)
    return ScholarshipOut.model_validate(scholarship)


@router.get("/{scholarship_id}", response_model=ScholarshipDetail)
async def get_scholarship(
    scholarship_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScholarshipDetail:
    result = await db.execute(
        select(Scholarship)
        .options(selectinload(Scholarship.columns))
        .where(Scholarship.id == scholarship_id)
    )
    scholarship = result.scalar_one_or_none()
    if scholarship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stipendiya topilmadi")
    return ScholarshipDetail.model_validate(scholarship)


@router.patch("/{scholarship_id}", response_model=ScholarshipOut)
async def update_scholarship(
    scholarship_id: uuid.UUID,
    payload: ScholarshipUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScholarshipOut:
    scholarship = await _get_scholarship_or_404(db, scholarship_id)
    if scholarship.status not in (ScholarshipStatus.DRAFT, ScholarshipStatus.OPEN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat draft yoki open stipendiyani tahrirlash mumkin",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(scholarship, field, value)

    await db.commit()
    await db.refresh(scholarship)
    return ScholarshipOut.model_validate(scholarship)


@router.delete(
    "/{scholarship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_scholarship(
    scholarship_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    scholarship = await _get_scholarship_or_404(db, scholarship_id)
    if scholarship.status != ScholarshipStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat draft stipendiyani o'chirish mumkin",
        )

    await db.delete(scholarship)
    await db.commit()


@router.patch("/{scholarship_id}/status", response_model=ScholarshipOut)
async def change_scholarship_status(
    scholarship_id: uuid.UUID,
    payload: StatusUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScholarshipOut:
    scholarship = await _get_scholarship_or_404(db, scholarship_id)
    scholarship = await change_scholarship_status_service(
        db=db,
        scholarship=scholarship,
        target_status=payload.status,
    )
    return ScholarshipOut.model_validate(scholarship)


@router.post("/{scholarship_id}/upload-nizom")
@limiter.limit(limit_nizom_upload)
async def upload_nizom(
    scholarship_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    request: Request = None,
) -> dict:
    scholarship = await _get_scholarship_or_404(db, scholarship_id)

    file_ref = await upload_file(file=file, folder="nizom")
    scholarship.nizom_file_url = file_ref
    await db.commit()

    return {"nizom_file_url": build_file_download_url(file_ref)}


@router.get("/{scholarship_id}/columns", response_model=list[ColumnOut])
async def list_columns(
    scholarship_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ColumnOut]:
    result = await db.execute(
        select(ScholarshipColumn)
        .where(ScholarshipColumn.scholarship_id == scholarship_id)
        .order_by(ScholarshipColumn.order_index)
    )
    columns = result.scalars().all()
    return [ColumnOut.model_validate(column) for column in columns]


@router.post("/{scholarship_id}/columns", response_model=ColumnOut, status_code=status.HTTP_201_CREATED)
async def create_column(
    scholarship_id: uuid.UUID,
    payload: ColumnCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ColumnOut:
    await _get_scholarship_or_404(db, scholarship_id)

    result = await db.execute(
        select(ScholarshipColumn.order_index)
        .where(ScholarshipColumn.scholarship_id == scholarship_id)
        .order_by(ScholarshipColumn.order_index.desc())
        .limit(1)
    )
    last_order = result.scalar_one_or_none() or -1

    column_payload = _normalize_column_payload(payload.model_dump(), payload.field_type)
    column = ScholarshipColumn(
        scholarship_id=scholarship_id,
        order_index=last_order + 1,
        **column_payload,
    )
    db.add(column)
    await db.commit()
    await db.refresh(column)
    return ColumnOut.model_validate(column)


@router.patch("/{scholarship_id}/columns/{column_id}", response_model=ColumnOut)
async def update_column(
    scholarship_id: uuid.UUID,
    column_id: uuid.UUID,
    payload: ColumnUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ColumnOut:
    result = await db.execute(
        select(ScholarshipColumn).where(
            ScholarshipColumn.id == column_id,
            ScholarshipColumn.scholarship_id == scholarship_id,
        )
    )
    column = result.scalar_one_or_none()
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ustun topilmadi")

    payload_data = payload.model_dump(exclude_unset=True)
    next_field_type = payload_data.get("field_type", column.field_type)
    payload_data = _normalize_column_payload(payload_data, next_field_type)

    for field, value in payload_data.items():
        setattr(column, field, value)

    await db.commit()
    await db.refresh(column)
    return ColumnOut.model_validate(column)


@router.delete(
    "/{scholarship_id}/columns/{column_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_column(
    scholarship_id: uuid.UUID,
    column_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(ScholarshipColumn).where(
            ScholarshipColumn.id == column_id,
            ScholarshipColumn.scholarship_id == scholarship_id,
        )
    )
    column = result.scalar_one_or_none()
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ustun topilmadi")

    await db.delete(column)
    await db.commit()


@router.patch("/{scholarship_id}/columns/reorder")
async def reorder_columns(
    scholarship_id: uuid.UUID,
    payload: ColumnReorder,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _get_scholarship_or_404(db, scholarship_id)

    for idx, column_id in enumerate(payload.order):
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
    return {"detail": "Tartib yangilandi"}


@router.get("/{scholarship_id}/jury", response_model=list[JuryOut])
async def list_jury(
    scholarship_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[JuryOut]:
    result = await db.execute(
        select(JuryAssignment)
        .options(selectinload(JuryAssignment.jury))
        .where(
            JuryAssignment.scholarship_id == scholarship_id,
            JuryAssignment.is_active.is_(True),
        )
    )
    assignments = result.scalars().all()
    return [JuryOut.model_validate(item.jury) for item in assignments if item.jury is not None]


@router.post("/{scholarship_id}/jury", status_code=status.HTTP_201_CREATED)
async def assign_jury(
    scholarship_id: uuid.UUID,
    payload: JuryAssignRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _get_scholarship_or_404(db, scholarship_id)

    result = await db.execute(
        select(User).where(User.id == payload.jury_id, User.role == UserRole.JURY)
    )
    jury_user = result.scalar_one_or_none()
    if jury_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hakam topilmadi")

    existing = await db.execute(
        select(JuryAssignment).where(
            JuryAssignment.scholarship_id == scholarship_id,
            JuryAssignment.jury_id == payload.jury_id,
        )
    )
    assignment = existing.scalar_one_or_none()

    if assignment is not None:
        assignment.is_active = True
    else:
        db.add(JuryAssignment(scholarship_id=scholarship_id, jury_id=payload.jury_id, is_active=True))

    await db.commit()
    return {"detail": "Hakam biriktirildi"}


@router.delete(
    "/{scholarship_id}/jury/{jury_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_jury(
    scholarship_id: uuid.UUID,
    jury_id: uuid.UUID,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(JuryAssignment).where(
            JuryAssignment.scholarship_id == scholarship_id,
            JuryAssignment.jury_id == jury_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biriktirilgan hakam topilmadi")

    assignment.is_active = False
    await db.commit()
