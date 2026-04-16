from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationValue
from app.models.scholarship import Scholarship
from app.repositories.base import CRUDBase


class CRUDApplication(CRUDBase[Application, BaseModel, BaseModel]):
    async def get_with_relations(
        self, db: AsyncSession, id: UUID
    ) -> Optional[Application]:
        query = (
            select(Application)
            .options(
                selectinload(Application.values).selectinload(ApplicationValue.column),
                selectinload(Application.scholarship).selectinload(Scholarship.columns),
                selectinload(Application.student),
                selectinload(Application.supervisor),
            )
            .where(Application.id == id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


application = CRUDApplication(Application)
