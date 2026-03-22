import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_student
from app.core.rate_limit import limit_achievement_upload, limiter
from app.models.application import StudentAchievement
from app.models.enums import AchievementType
from app.models.user import User
from app.schemas.achievement import AchievementCreate, AchievementOut, AchievementUpdate
from app.services.file_service import build_file_download_url, upload_file


router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("", response_model=list[AchievementOut])
async def list_achievements(
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
    achievement_type: AchievementType | None = Query(default=None, alias="type"),
) -> list[AchievementOut]:
    query = select(StudentAchievement).where(StudentAchievement.student_id == current_user.id)

    if achievement_type is not None:
        query = query.where(StudentAchievement.type == achievement_type)

    query = query.order_by(StudentAchievement.date.desc().nullslast(), StudentAchievement.created_at.desc())

    result = await db.execute(query)
    achievements = result.scalars().all()
    return [AchievementOut.model_validate(item) for item in achievements]


@router.post("", response_model=AchievementOut, status_code=status.HTTP_201_CREATED)
async def create_achievement(
    payload: AchievementCreate,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AchievementOut:
    achievement = StudentAchievement(student_id=current_user.id, **payload.model_dump())
    db.add(achievement)
    await db.commit()
    await db.refresh(achievement)
    return AchievementOut.model_validate(achievement)


@router.patch("/{achievement_id}", response_model=AchievementOut)
async def update_achievement(
    achievement_id: uuid.UUID,
    payload: AchievementUpdate,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AchievementOut:
    result = await db.execute(
        select(StudentAchievement).where(
            StudentAchievement.id == achievement_id,
            StudentAchievement.student_id == current_user.id,
        )
    )
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yutuq topilmadi")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(achievement, field, value)

    await db.commit()
    await db.refresh(achievement)
    return AchievementOut.model_validate(achievement)


@router.delete(
    "/{achievement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_achievement(
    achievement_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(StudentAchievement).where(
            StudentAchievement.id == achievement_id,
            StudentAchievement.student_id == current_user.id,
        )
    )
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yutuq topilmadi")

    await db.delete(achievement)
    await db.commit()


@router.post("/{achievement_id}/upload")
@limiter.limit(limit_achievement_upload)
async def upload_achievement_file(
    achievement_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_student)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    request: Request = None,
) -> dict:
    result = await db.execute(
        select(StudentAchievement).where(
            StudentAchievement.id == achievement_id,
            StudentAchievement.student_id == current_user.id,
        )
    )
    achievement = result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yutuq topilmadi")

    file_ref = await upload_file(file=file, folder="achievement")
    achievement.file_url = file_ref

    await db.commit()

    return {"file_url": build_file_download_url(file_ref)}
