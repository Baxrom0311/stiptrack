from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import AsyncSessionLocal
from app.core.redis_client import ping_redis
from app.services.file_service import ensure_bucket_exists, ping_minio


router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    db_ok = False
    redis_ok = False
    minio_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db_ok = False

    redis_ok = await ping_redis()
    minio_ok = await ping_minio()

    if minio_ok:
        minio_ok = await ensure_bucket_exists()

    overall = db_ok and redis_ok and minio_ok

    return {
        "status": "ok" if overall else "degraded",
        "services": {
            "database": db_ok,
            "redis": redis_ok,
            "minio": minio_ok,
        },
    }
