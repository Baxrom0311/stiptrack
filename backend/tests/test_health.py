from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import app.api.v1.health as health_api


class DummySessionContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _stmt):
        return 1


@pytest.mark.asyncio
async def test_health_check_returns_ok_when_all_services_are_available(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(health_api, "AsyncSessionLocal", lambda: DummySessionContext())
    monkeypatch.setattr(health_api, "ping_redis", AsyncMock(return_value=True))
    monkeypatch.setattr(health_api, "ping_minio", AsyncMock(return_value=True))
    ensure_bucket_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(health_api, "ensure_bucket_exists", ensure_bucket_exists)

    result = await health_api.health_check()

    assert result == {
        "status": "ok",
        "services": {
            "database": True,
            "redis": True,
            "minio": True,
        },
    }
    ensure_bucket_exists.assert_awaited_once()
