from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.redis_client import get_redis
from app.services.file_service import ensure_bucket_exists, ensure_bucket_policy


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.secret_key:
        raise RuntimeError(
            "SECRET_KEY is not set! Application cannot start without a secret key. "
            "Set it via the SECRET_KEY environment variable or in .env file."
        )
    await ensure_bucket_exists()
    await ensure_bucket_policy()
    yield
    await get_redis().close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
