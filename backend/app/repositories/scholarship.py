from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scholarship import Scholarship
from app.repositories.base import CRUDBase
from app.schemas.scholarship import ScholarshipCreate, ScholarshipUpdate


class CRUDScholarship(CRUDBase[Scholarship, ScholarshipCreate, ScholarshipUpdate]):
    async def get_with_columns(
        self, db: AsyncSession, id: UUID
    ) -> Optional[Scholarship]:
        query = (
            select(Scholarship)
            .options(selectinload(Scholarship.columns))
            .where(Scholarship.id == id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


scholarship = CRUDScholarship(Scholarship)
