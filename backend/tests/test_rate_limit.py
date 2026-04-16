from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.api.v1.achievements as achievements_api
import app.api.v1.auth as auth_api
import app.main as main_module
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin, require_student
from app.core.rate_limit import rate_limit_key
from app.main import app
from app.models.enums import AIJobStatus, UserRole


class FakeRedis:
    async def close(self) -> None:
        return None


class _ExecuteResult:
    def __init__(self, scalar=None):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


class DummyDB:
    def __init__(self, *, get_map=None, execute_results=None):
        self._get_map = dict(get_map or {})
        self._execute_results = list(execute_results or [])
        self.added: list[object] = []
        self.commits = 0
        self.refresh_calls = 0

    async def get(self, model, obj_id):
        key = (getattr(model, "__name__", str(model)), obj_id)
        if key in self._get_map:
            return self._get_map[key]
        return self._get_map.get(getattr(model, "__name__", str(model)))

    async def execute(self, _stmt):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call")
        return self._execute_results.pop(0)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: object) -> None:
        now = datetime.now(timezone.utc)
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "status", None) is None:
            obj.status = AIJobStatus.PENDING
        self.refresh_calls += 1


def build_user(role: UserRole, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "Rate Limited User",
        "email": "rate@example.com",
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

    async def _ensure_bucket_policy() -> bool:
        return True

    fake_redis = FakeRedis()
    monkeypatch.setattr(main_module, "ensure_bucket_exists", _ensure_bucket_exists)
    monkeypatch.setattr(main_module, "ensure_bucket_policy", _ensure_bucket_policy)
    monkeypatch.setattr(main_module, "get_redis", lambda: fake_redis)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_login_rate_limit_returns_429(client, monkeypatch: pytest.MonkeyPatch):
    db = DummyDB()

    async def override_get_db():
        yield db

    async def _authenticate_user(db, email: str, password: str):
        return build_user(UserRole.STUDENT, email=email)

    monkeypatch.setattr(settings, "rate_limit_auth_login", "2/minute")
    monkeypatch.setattr(auth_api, "authenticate_user", _authenticate_user)
    monkeypatch.setattr(auth_api, "create_access_token", lambda subject, role="": ("access-token", 3600, "a-jti"))
    monkeypatch.setattr(auth_api, "create_refresh_token", lambda subject, role="": ("refresh-token", 2592000, "r-jti"))

    app.dependency_overrides[get_db] = override_get_db

    headers = {"x-forwarded-for": "10.10.0.1"}
    payload = {"email": "student@example.com", "password": "strongpass123"}

    first = client.post("/api/v1/auth/login", json=payload, headers=headers)
    second = client.post("/api/v1/auth/login", json=payload, headers=headers)
    third = client.post("/api/v1/auth/login", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Rate limit exceeded" in third.text


def test_rate_limit_key_ignores_spoofed_proxy_headers():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "root_path": "",
            "headers": [
                (b"x-forwarded-for", b"203.0.113.10"),
                (b"x-real-ip", b"203.0.113.11"),
            ],
            "client": ("127.0.0.1", 4321),
        }
    )

    assert rate_limit_key(request) == "127.0.0.1"


def test_generate_columns_rate_limit_returns_429(client, monkeypatch: pytest.MonkeyPatch):
    admin_user = build_user(UserRole.ADMIN)
    scholarship = SimpleNamespace(
        id=uuid4(),
        title="AI Scholarship",
        nizom_file_url="https://files/nizom.pdf",
        ai_provider="claude",
        ai_model=None,
    )
    db = DummyDB(get_map={("Scholarship", scholarship.id): scholarship})
    delayed_calls: list[dict] = []

    async def override_get_db():
        yield db

    class _Task:
        @staticmethod
        def delay(**kwargs):
            delayed_calls.append(kwargs)

    import workers.tasks as worker_tasks

    monkeypatch.setattr(settings, "rate_limit_ai_generate_columns", "2/minute")
    monkeypatch.setattr(worker_tasks, "run_column_generation", _Task)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin] = lambda: admin_user

    headers = {"x-forwarded-for": "10.10.0.2"}
    payload = {
        "purpose": "Maqsad",
        "requirements": ["GPA 3.5+"],
        "evaluation_criteria": ["GPA"],
        "additional_docs": ["Diplom"],
        "total_max_score": 100,
        "scoring_type": "table",
        "eligible_students": "2-4 kurs",
        "selection_stages": "Ariza -> Review",
    }

    first = client.post(
        f"/api/v1/ai/scholarships/{scholarship.id}/generate-columns",
        json=payload,
        headers=headers,
    )
    second = client.post(
        f"/api/v1/ai/scholarships/{scholarship.id}/generate-columns",
        json=payload,
        headers=headers,
    )
    third = client.post(
        f"/api/v1/ai/scholarships/{scholarship.id}/generate-columns",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert len(delayed_calls) == 2
    assert "Rate limit exceeded" in third.text


def test_achievement_upload_rate_limit_returns_429(client, monkeypatch: pytest.MonkeyPatch):
    student = build_user(UserRole.STUDENT)
    achievement = SimpleNamespace(
        id=uuid4(),
        student_id=student.id,
        file_url=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = DummyDB(
        execute_results=[
            _ExecuteResult(scalar=achievement),
            _ExecuteResult(scalar=achievement),
        ]
    )

    async def override_get_db():
        yield db

    async def _upload_file(file, folder: str):
        return f"https://files.example.com/{folder}/{file.filename}"

    monkeypatch.setattr(settings, "rate_limit_achievement_upload", "2/minute")
    monkeypatch.setattr(achievements_api, "upload_file", _upload_file)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_student] = lambda: student

    headers = {"x-forwarded-for": "10.10.0.3"}
    files = {"file": ("achievement.pdf", b"fake-pdf-content", "application/pdf")}

    first = client.post(
        f"/api/v1/achievements/{achievement.id}/upload",
        files=files,
        headers=headers,
    )
    second = client.post(
        f"/api/v1/achievements/{achievement.id}/upload",
        files=files,
        headers=headers,
    )
    third = client.post(
        f"/api/v1/achievements/{achievement.id}/upload",
        files=files,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Rate limit exceeded" in third.text
