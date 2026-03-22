from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.api.v1.users as users_api
from app.models.enums import UserRole
from app.schemas.user import UserAdminCreate, UserAdminUpdate


def build_user(**overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "Test User",
        "email": "user@example.com",
        "role": UserRole.STUDENT,
        "department": "CS",
        "student_id": "S-100",
        "is_supervisor": False,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_get_users_returns_service_results(monkeypatch: pytest.MonkeyPatch):
    student = build_user(full_name="Ali Valiyev", email="ali@example.com")

    async def _list_users(db, role, is_active, search, limit, offset):
        assert role == UserRole.STUDENT
        assert is_active is True
        assert search == "ali"
        assert limit == 10
        assert offset == 0
        return [student]

    monkeypatch.setattr(users_api, "list_users", _list_users)

    result = await users_api.get_users(
        db=object(),
        _=build_user(role=UserRole.ADMIN),
        role=UserRole.STUDENT,
        is_active=True,
        search="ali",
        limit=10,
        offset=0,
    )

    assert len(result) == 1
    assert result[0].email == "ali@example.com"
    assert result[0].role == UserRole.STUDENT


@pytest.mark.asyncio
async def test_create_user_by_admin_returns_created_user(monkeypatch: pytest.MonkeyPatch):
    payload = UserAdminCreate(
        full_name="Jury Member",
        email="jury@example.com",
        password="strongpass123",
        role=UserRole.JURY,
        department="Science",
        is_supervisor=False,
        is_active=True,
    )

    async def _get_user_by_email(db, email: str):
        assert email == "jury@example.com"
        return None

    async def _create_user(db, payload: UserAdminCreate):
        return build_user(
            full_name=payload.full_name,
            email=payload.email,
            role=payload.role,
            department=payload.department,
            is_supervisor=payload.is_supervisor,
            is_active=payload.is_active,
        )

    monkeypatch.setattr(users_api, "get_user_by_email", _get_user_by_email)
    monkeypatch.setattr(users_api, "create_user", _create_user)

    result = await users_api.create_user_by_admin(
        payload=payload,
        db=object(),
        _=build_user(role=UserRole.ADMIN),
    )

    assert result.email == "jury@example.com"
    assert result.role == UserRole.JURY
    assert result.department == "Science"


@pytest.mark.asyncio
async def test_toggle_user_active_flips_current_state(monkeypatch: pytest.MonkeyPatch):
    user = build_user(role=UserRole.JURY, is_active=True)
    admin = build_user(id=uuid4(), role=UserRole.ADMIN)

    async def _get_user_by_id(db, user_id):
        assert user_id == user.id
        return user

    async def _update_user(db, user, payload):
        assert payload.is_active is False
        user.is_active = payload.is_active
        return user

    monkeypatch.setattr(users_api, "get_user_by_id", _get_user_by_id)
    monkeypatch.setattr(users_api, "update_user", _update_user)

    result = await users_api.toggle_user_active(user_id=user.id, db=object(), current_admin=admin)

    assert result.is_active is False
    assert user.is_active is False


@pytest.mark.asyncio
async def test_update_user_by_admin_returns_updated_user(monkeypatch: pytest.MonkeyPatch):
    user = build_user(role=UserRole.STUDENT, full_name="Old Name", department="Math")

    async def _get_user_by_id(db, user_id):
        assert user_id == user.id
        return user

    async def _get_user_by_email(db, email: str):
        assert email == "updated@example.com"
        return None

    async def _update_user(db, user, payload: UserAdminUpdate):
        user.full_name = payload.full_name or user.full_name
        user.email = payload.email or user.email
        user.department = payload.department or user.department
        user.role = payload.role or user.role
        return user

    monkeypatch.setattr(users_api, "get_user_by_id", _get_user_by_id)
    monkeypatch.setattr(users_api, "get_user_by_email", _get_user_by_email)
    monkeypatch.setattr(users_api, "update_user", _update_user)

    result = await users_api.update_user_by_admin(
        user_id=user.id,
        payload=UserAdminUpdate(
            full_name="Updated Name",
            email="updated@example.com",
            department="Engineering",
            role=UserRole.JURY,
        ),
        db=object(),
        _=build_user(role=UserRole.ADMIN),
    )

    assert result.full_name == "Updated Name"
    assert result.email == "updated@example.com"
    assert result.department == "Engineering"
    assert result.role == UserRole.JURY


@pytest.mark.asyncio
async def test_get_supervisors_returns_available_supervisors(monkeypatch: pytest.MonkeyPatch):
    supervisor = build_user(role=UserRole.JURY, is_supervisor=True, full_name="Prof. Karimov")

    async def _list_supervisors(db, only_active: bool):
        assert only_active is True
        return [supervisor]

    monkeypatch.setattr(users_api, "list_supervisors", _list_supervisors)

    result = await users_api.get_supervisors(db=object(), _=build_user())

    assert len(result) == 1
    assert result[0].full_name == "Prof. Karimov"
    assert result[0].is_supervisor is True
