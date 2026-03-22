from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from jose import JWTError

import app.api.v1.auth as auth_api
import app.main as main_module
from app.core.database import get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.enums import UserRole


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, tuple[int, str]] = {}

    async def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = (ttl, value)

    async def close(self) -> None:
        return None


class FakeSession:
    def __init__(self, user: SimpleNamespace | None = None) -> None:
        self.user = user

    async def get(self, model: object, user_id: UUID) -> SimpleNamespace | None:
        if self.user is None:
            return None
        if getattr(self.user, "id", None) == user_id:
            return self.user
        return None


def build_user(**overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "Test Student",
        "email": "student@example.com",
        "role": UserRole.STUDENT,
        "department": "CS",
        "student_id": "S12345",
        "is_supervisor": False,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.fixture
def fake_user() -> SimpleNamespace:
    return build_user()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, fake_user: SimpleNamespace, fake_redis: FakeRedis):
    async def _ensure_bucket_exists() -> bool:
        return True

    monkeypatch.setattr(main_module, "ensure_bucket_exists", _ensure_bucket_exists)
    monkeypatch.setattr(main_module, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(auth_api, "get_redis", lambda: fake_redis)

    fake_db = FakeSession(user=fake_user)

    async def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: fake_user

    with TestClient(app) as test_client:
        yield test_client, fake_db

    app.dependency_overrides.clear()


def test_register_success(client, monkeypatch: pytest.MonkeyPatch):
    test_client, _ = client

    async def _get_user_by_email(db, email: str):
        return None

    async def _create_student_user(db, user_in):
        return build_user(email=user_in.email, full_name=user_in.full_name)

    monkeypatch.setattr(auth_api, "get_user_by_email", _get_user_by_email)
    monkeypatch.setattr(auth_api, "create_student_user", _create_student_user)

    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ali Valiyev",
            "email": "ali@example.com",
            "password": "strongpass123",
            "department": "Math",
            "student_id": "M-001",
            "is_supervisor": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ali@example.com"
    assert body["role"] == "student"


def test_login_returns_token_pair(client, fake_user: SimpleNamespace, monkeypatch: pytest.MonkeyPatch):
    test_client, _ = client

    async def _authenticate_user(db, email: str, password: str):
        return fake_user

    monkeypatch.setattr(auth_api, "authenticate_user", _authenticate_user)
    monkeypatch.setattr(auth_api, "create_access_token", lambda subject: ("access-token", 3600, "a-jti"))
    monkeypatch.setattr(auth_api, "create_refresh_token", lambda subject: ("refresh-token", 2592000, "r-jti"))

    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "strongpass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "access-token"
    assert body["refresh_token"] == "refresh-token"
    assert body["token_type"] == "bearer"


def test_refresh_rotates_tokens_and_blacklists_old_one(
    client,
    fake_user: SimpleNamespace,
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
):
    test_client, _ = client

    exp = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())

    monkeypatch.setattr(
        auth_api,
        "decode_token_by_type",
        lambda token, expected_type: {
            "jti": "old-refresh-jti",
            "exp": exp,
            "sub": str(fake_user.id),
            "type": "refresh",
        },
    )
    monkeypatch.setattr(auth_api, "create_access_token", lambda subject: ("new-access", 3600, "a-jti"))
    monkeypatch.setattr(auth_api, "create_refresh_token", lambda subject: ("new-refresh", 2592000, "r-jti"))

    response = test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "new-access"
    assert body["refresh_token"] == "new-refresh"

    blacklist_key = f"{auth_api.REFRESH_BLACKLIST_KEY_PREFIX}old-refresh-jti"
    assert blacklist_key in fake_redis.store


def test_refresh_rejects_blacklisted_token(client, fake_user: SimpleNamespace, fake_redis: FakeRedis, monkeypatch):
    test_client, _ = client

    exp = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
    blacklist_key = f"{auth_api.REFRESH_BLACKLIST_KEY_PREFIX}old-refresh-jti"
    fake_redis.store[blacklist_key] = (300, "1")

    monkeypatch.setattr(
        auth_api,
        "decode_token_by_type",
        lambda token, expected_type: {
            "jti": "old-refresh-jti",
            "exp": exp,
            "sub": str(fake_user.id),
            "type": "refresh",
        },
    )

    response = test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "blacklisted-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token revoked"


def test_logout_blacklists_refresh_token(client, fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch):
    test_client, _ = client

    exp = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())

    monkeypatch.setattr(
        auth_api,
        "decode_token_by_type",
        lambda token, expected_type: {
            "jti": "logout-jti",
            "exp": exp,
            "sub": str(uuid4()),
            "type": "refresh",
        },
    )

    response = test_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "some-refresh-token"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    assert f"{auth_api.REFRESH_BLACKLIST_KEY_PREFIX}logout-jti" in fake_redis.store


def test_refresh_invalid_token_returns_401(client, monkeypatch: pytest.MonkeyPatch):
    test_client, _ = client

    def _decode_invalid(token: str, expected_type: str):
        raise JWTError("invalid token")

    monkeypatch.setattr(auth_api, "decode_token_by_type", _decode_invalid)

    response = test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


def test_get_me_returns_current_user(client):
    test_client, _ = client

    response = test_client.get("/api/v1/auth/me")

    assert response.status_code == 200


def test_update_me_returns_updated_profile(client, fake_user: SimpleNamespace, monkeypatch: pytest.MonkeyPatch):
    test_client, fake_db = client

    async def _update_own_profile(db, user, updates):
        assert db is fake_db
        assert user.id == fake_user.id
        assert updates == {"full_name": "Updated Student", "department": "Engineering"}
        return build_user(
            id=user.id,
            full_name="Updated Student",
            email=user.email,
            role=user.role,
            department="Engineering",
            student_id=user.student_id,
            is_supervisor=user.is_supervisor,
            is_active=user.is_active,
        )

    monkeypatch.setattr(auth_api, "update_own_profile", _update_own_profile)

    response = test_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated Student", "department": "Engineering"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Updated Student"
    assert body["department"] == "Engineering"
    body = response.json()
    assert body["email"] == "student@example.com"
    assert body["role"] == "student"


def test_update_me_rejects_student_supervisor_toggle(
    client,
    fake_user: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
):
    test_client, _ = client

    async def _update_own_profile(db, user, updates):
        raise AssertionError("update_own_profile should not be called for invalid student supervisor toggle")

    monkeypatch.setattr(auth_api, "update_own_profile", _update_own_profile)

    response = test_client.patch(
        "/api/v1/auth/me",
        json={"is_supervisor": True},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student akkaunti o‘zini ilmiy rahbar sifatida belgilay olmaydi"
