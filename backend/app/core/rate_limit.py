from __future__ import annotations

import hashlib

from fastapi import Request
from slowapi import Limiter

from app.core.config import settings


def rate_limit_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for

    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip

    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
            return f"bearer:{digest}"

    return request.client.host if request.client else "anonymous"


def limit_auth_register() -> str:
    return settings.rate_limit_auth_register


def limit_auth_login() -> str:
    return settings.rate_limit_auth_login


def limit_auth_refresh() -> str:
    return settings.rate_limit_auth_refresh


def limit_auth_logout() -> str:
    return settings.rate_limit_auth_logout


def limit_ai_job_poll() -> str:
    return settings.rate_limit_ai_job_poll


def limit_ai_parse_nizom() -> str:
    return settings.rate_limit_ai_parse_nizom


def limit_ai_generate_columns() -> str:
    return settings.rate_limit_ai_generate_columns


def limit_ai_generate_review() -> str:
    return settings.rate_limit_ai_generate_review


def limit_nizom_upload() -> str:
    return settings.rate_limit_nizom_upload


def limit_value_upload() -> str:
    return settings.rate_limit_value_upload


def limit_achievement_upload() -> str:
    return settings.rate_limit_achievement_upload


def limit_application_submit() -> str:
    return settings.rate_limit_application_submit


def limit_winner_announce() -> str:
    return settings.rate_limit_winner_announce


def limit_appeal_create() -> str:
    return settings.rate_limit_appeal_create


def limit_appeal_upload() -> str:
    return settings.rate_limit_appeal_upload


limiter = Limiter(
    key_func=rate_limit_key,
    headers_enabled=False,
    storage_uri=settings.rate_limit_storage_uri,
    enabled=settings.rate_limit_enabled,
    key_prefix="stiptrack",
    key_style="endpoint",
    in_memory_fallback_enabled=True,
)
