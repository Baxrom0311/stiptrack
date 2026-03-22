from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.database import get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.enums import UserRole


class FakeRedis:
    async def close(self) -> None:
        return None


def _build_user(role: UserRole, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "Security Test User",
        "email": f"{role.value}@example.com",
        "role": role,
        "department": None,
        "student_id": None,
        "is_supervisor": False,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    async def _ensure_bucket_exists() -> bool:
        return True

    fake_redis = FakeRedis()
    monkeypatch.setattr(main_module, "ensure_bucket_exists", _ensure_bucket_exists)
    monkeypatch.setattr(main_module, "get_redis", lambda: fake_redis)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


_NOW = datetime.now(timezone.utc)
_SCHOLARSHIP_ID = uuid4()
_TEMPLATE_ID = uuid4()
_APPLICATION_ID = uuid4()
_USER_ID = uuid4()
_APPEAL_ID = uuid4()

ADMIN_ONLY_ENDPOINT_CASES = [
    ("GET", "/api/v1/users", None),
    (
        "POST",
        "/api/v1/users",
        {
            "full_name": "New User",
            "email": "new.user@example.com",
            "password": "strongpass123",
            "role": "student",
            "department": "CS",
            "student_id": "S-101",
            "is_supervisor": False,
            "is_active": True,
        },
    ),
    ("PATCH", f"/api/v1/users/{_USER_ID}/toggle-active", None),
    ("GET", "/api/v1/admin/stats", None),
    ("GET", "/api/v1/appeals", None),
    ("GET", "/api/v1/scholarship-templates", None),
    (
        "POST",
        "/api/v1/scholarships",
        {
            "title": "Security Scholarship",
            "description": "Test",
            "ai_analysis_enabled": False,
            "max_winners": 1,
        },
    ),
    (
        "POST",
        "/api/v1/scholarship-templates",
        {
            "scholarship_id": str(_SCHOLARSHIP_ID),
            "name": "Base template",
            "description": "Security test template",
        },
    ),
    (
        "POST",
        f"/api/v1/scholarship-templates/{_TEMPLATE_ID}/instantiate",
        {
            "title": "Template instance",
            "description": "From template",
        },
    ),
    (
        "PATCH",
        f"/api/v1/applications/{_APPLICATION_ID}/status",
        {
            "status": "submitted",
        },
    ),
    ("POST", f"/api/v1/ai/scholarships/{_SCHOLARSHIP_ID}/parse-nizom", None),
    (
        "POST",
        f"/api/v1/ai/scholarships/{_SCHOLARSHIP_ID}/generate-columns",
        {
            "purpose": "Talabalarni rag'batlantirish",
            "requirements": ["GPA 3.5+"],
            "evaluation_criteria": ["GPA", "Motivatsiya"],
            "additional_docs": ["Diplom"],
            "total_max_score": 100,
            "scoring_type": "table",
            "eligible_students": "2-4 kurs",
            "selection_stages": "Ariza -> Review",
        },
    ),
    (
        "POST",
        f"/api/v1/scholarships/{_SCHOLARSHIP_ID}/stages",
        {
            "name": "Hujjat qabul qilish",
            "stage_type": "application",
            "description": "Asosiy bosqich",
            "starts_at": _NOW.isoformat(),
            "ends_at": (_NOW + timedelta(days=7)).isoformat(),
            "is_required": True,
            "is_active": True,
            "config": {"days": 7},
        },
    ),
    (
        "PATCH",
        f"/api/v1/appeals/{_APPEAL_ID}/decision",
        {
            "status": "accepted",
            "response_text": "Qayta ko'rib chiqildi",
            "score_after": 91,
        },
    ),
]


@pytest.mark.parametrize("role", [UserRole.STUDENT, UserRole.JURY], ids=["student", "jury"])
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    ADMIN_ONLY_ENDPOINT_CASES,
    ids=[
        "users-list",
        "users-create",
        "users-toggle-active",
        "admin-stats",
        "appeals-list",
        "templates-list",
        "scholarships-create",
        "templates-create",
        "templates-instantiate",
        "application-status-update",
        "ai-parse-nizom",
        "ai-generate-columns",
        "stages-create",
        "appeal-decision",
    ],
)
def test_admin_endpoints_reject_non_admin_users(
    client: TestClient,
    role: UserRole,
    method: str,
    path: str,
    payload: dict | None,
):
    user = _build_user(role)

    async def override_get_db():
        yield SimpleNamespace()

    async def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    request_kwargs = {}
    if payload is not None:
        request_kwargs["json"] = payload

    response = client.request(method, path, **request_kwargs)

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin role required"}
