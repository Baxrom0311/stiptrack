from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.api.v1.scholarships as scholarships_api
import app.schemas.scholarship as scholarship_schema
from app.models.enums import ColumnFieldType, ScholarshipStatus, UserRole
from app.schemas.scholarship import (
    ColumnCreate,
    ColumnReorder,
    ColumnUpdate,
    JuryAssignRequest,
    ScholarshipCreate,
    ScholarshipUpdate,
    StatusUpdate,
)


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _ExecuteResult:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def all(self):
        return self._rows

    def scalar_one(self):
        if self._scalar is not None:
            return self._scalar
        if len(self._rows) == 1:
            return self._rows[0]
        raise AssertionError("Expected exactly one row")

    def scalar_one_or_none(self):
        if self._scalar is not None:
            return self._scalar
        if len(self._rows) == 1:
            return self._rows[0]
        if not self._rows:
            return None
        raise AssertionError("Expected zero or one row")

    def scalars(self):
        return _ScalarResult(self._rows)


class DummyDB:
    def __init__(self, execute_results=None):
        self._execute_results = list(execute_results or [])
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commits = 0
        self.refreshed: list[object] = []

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
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        if obj.__class__.__name__ == "Scholarship":
            if getattr(obj, "status", None) is None:
                obj.status = ScholarshipStatus.DRAFT
            if getattr(obj, "description", None) is None:
                obj.description = None
            if getattr(obj, "nizom_file_url", None) is None:
                obj.nizom_file_url = None
            if getattr(obj, "deadline", None) is None:
                obj.deadline = None
            if getattr(obj, "ai_analysis_enabled", None) is None:
                obj.ai_analysis_enabled = False
            if getattr(obj, "blind_review_enabled", None) is None:
                obj.blind_review_enabled = False
            if getattr(obj, "max_winners", None) is None:
                obj.max_winners = 1
            if getattr(obj, "ai_provider", None) is None:
                obj.ai_provider = "claude"
            if getattr(obj, "ai_model", None) is None:
                obj.ai_model = None
        self.refreshed.append(obj)

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


def _build_scholarship(status: ScholarshipStatus) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        created_by=uuid4(),
        title="Test stipendiya",
        description="desc",
        nizom_file_url=None,
        status=status,
        deadline=None,
        ai_analysis_enabled=False,
        blind_review_enabled=False,
        max_winners=2,
        ai_provider="claude",
        ai_model=None,
        created_at=now,
        updated_at=now,
        columns=[],
    )


def _build_column(order_index: int = 0, **overrides: object) -> SimpleNamespace:
    data = {
        "id": uuid4(),
        "scholarship_id": uuid4(),
        "name": "GPA",
        "description": "Akademik ko'rsatkich",
        "field_type": ColumnFieldType.NUMBER,
        "select_options": None,
        "is_required": True,
        "ai_analyze": False,
        "max_score": 30,
        "input_min": None,
        "input_max": None,
        "order_index": order_index,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_user(role: UserRole = UserRole.JURY, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "Jury User",
        "email": "jury@example.com",
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


@pytest.mark.asyncio
async def test_list_scholarships_returns_service_results(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(ScholarshipStatus.OPEN)

    async def _list_scholarships_service(db, current_user_role, status_filter, search, skip, limit):
        assert current_user_role == UserRole.ADMIN
        assert status_filter == ScholarshipStatus.OPEN
        assert search == "rektor"
        assert skip == 0
        assert limit == 20
        return [scholarship]

    monkeypatch.setattr(scholarships_api, "list_scholarships_service", _list_scholarships_service)

    result = await scholarships_api.list_scholarships(
        current_user=_build_user(role=UserRole.ADMIN),
        db=object(),
        status_filter=ScholarshipStatus.OPEN,
        search="rektor",
        skip=0,
        limit=20,
    )

    assert len(result) == 1
    assert result[0].title == scholarship.title


@pytest.mark.asyncio
async def test_create_scholarship_creates_record():
    db = DummyDB()
    admin = _build_user(role=UserRole.ADMIN)

    result = await scholarships_api.create_scholarship(
        payload=ScholarshipCreate(
            title="Rektor stipendiyasi",
            description="Iqtidorli talabalar uchun",
            deadline=None,
            ai_analysis_enabled=True,
            blind_review_enabled=True,
            ai_provider="openai",
            ai_model="gpt-4.1-mini",
            max_winners=3,
        ),
        current_user=admin,
        db=db,
    )

    assert db.commits == 1
    assert len(db.added) == 1
    assert result.created_by == admin.id
    assert result.title == "Rektor stipendiyasi"
    assert result.ai_analysis_enabled is True
    assert result.blind_review_enabled is True
    assert result.ai_provider.value == "openai"
    assert result.ai_model == "gpt-4.1-mini"
    assert result.max_winners == 3


@pytest.mark.asyncio
async def test_get_scholarship_returns_detail(monkeypatch: pytest.MonkeyPatch):
    column = _build_column()
    scholarship = _build_scholarship(ScholarshipStatus.OPEN)
    scholarship.nizom_file_url = "nizom/test.pdf"
    scholarship.columns = [column]
    db = DummyDB(execute_results=[_ExecuteResult(scalar=scholarship)])
    monkeypatch.setattr(
        scholarship_schema,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await scholarships_api.get_scholarship(scholarship_id=scholarship.id, db=db)

    assert result.id == scholarship.id
    assert len(result.columns) == 1
    assert result.columns[0].name == column.name
    assert result.nizom_file_url == "https://signed.example/nizom/test.pdf"


@pytest.mark.asyncio
async def test_update_scholarship_updates_allowed_fields(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(ScholarshipStatus.DRAFT)
    db = DummyDB()

    async def _fake_get_scholarship(*args, **kwargs):
        return scholarship

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    result = await scholarships_api.update_scholarship(
        scholarship_id=scholarship.id,
        payload=ScholarshipUpdate(
            title="Yangilangan nom",
            max_winners=5,
            blind_review_enabled=True,
            ai_provider="deepseek",
            ai_model="deepseek-reasoner",
        ),
        _=object(),
        db=db,
    )

    assert scholarship.title == "Yangilangan nom"
    assert scholarship.max_winners == 5
    assert scholarship.blind_review_enabled is True
    assert scholarship.ai_provider == "deepseek"
    assert scholarship.ai_model == "deepseek-reasoner"
    assert db.commits == 1
    assert db.refreshed == [scholarship]
    assert result.title == "Yangilangan nom"


@pytest.mark.asyncio
async def test_delete_scholarship_removes_draft(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(ScholarshipStatus.DRAFT)
    db = DummyDB()

    async def _fake_get_scholarship(*args, **kwargs):
        return scholarship

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    await scholarships_api.delete_scholarship(
        scholarship_id=scholarship.id,
        _=object(),
        db=db,
    )

    assert db.deleted == [scholarship]
    assert db.commits == 1


@pytest.mark.asyncio
async def test_change_status_accepts_only_next_transition(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(ScholarshipStatus.DRAFT)
    db = DummyDB()

    async def _fake_get_scholarship(*args, **kwargs):
        return scholarship

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    result = await scholarships_api.change_scholarship_status(
        scholarship_id=uuid4(),
        payload=StatusUpdate(status=ScholarshipStatus.OPEN),
        _=object(),
        db=db,
    )

    assert result.status == ScholarshipStatus.OPEN
    assert scholarship.status == ScholarshipStatus.OPEN
    assert db.commits == 1
    assert db.refreshed == [scholarship]


@pytest.mark.asyncio
async def test_change_status_rejects_skipped_transition(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(ScholarshipStatus.DRAFT)
    db = DummyDB()

    async def _fake_get_scholarship(*args, **kwargs):
        return scholarship

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    with pytest.raises(HTTPException) as exc_info:
        await scholarships_api.change_scholarship_status(
            scholarship_id=uuid4(),
            payload=StatusUpdate(status=ScholarshipStatus.DONE),
            _=object(),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "faqat" in str(exc_info.value.detail)
    assert db.commits == 0


@pytest.mark.asyncio
async def test_change_status_rejects_when_already_final(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(ScholarshipStatus.DONE)
    db = DummyDB()

    async def _fake_get_scholarship(*args, **kwargs):
        return scholarship

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    with pytest.raises(HTTPException) as exc_info:
        await scholarships_api.change_scholarship_status(
            scholarship_id=uuid4(),
            payload=StatusUpdate(status=ScholarshipStatus.DONE),
            _=object(),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "Yakuniy holatga yetilgan" in str(exc_info.value.detail)
    assert db.commits == 0


@pytest.mark.asyncio
async def test_upload_nizom_stores_object_key_and_returns_presigned_url(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(ScholarshipStatus.DRAFT)
    db = DummyDB()
    upload_file = AsyncMock(return_value="nizom/test.pdf")

    async def _fake_get_scholarship(*args, **kwargs):
        return scholarship

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)
    monkeypatch.setattr(scholarships_api, "upload_file", upload_file)
    monkeypatch.setattr(
        scholarships_api,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await scholarships_api.upload_nizom(
        scholarship_id=scholarship.id,
        _=object(),
        db=db,
        file=SimpleNamespace(content_type="application/pdf"),
    )

    assert result["nizom_file_url"] == "https://signed.example/nizom/test.pdf"
    assert scholarship.nizom_file_url == "nizom/test.pdf"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_list_columns_returns_sorted_items():
    col1 = _build_column(order_index=0, name="GPA")
    col2 = _build_column(order_index=1, name="Motivatsiya", field_type=ColumnFieldType.TEXTAREA)
    db = DummyDB(execute_results=[_ExecuteResult(rows=[col1, col2])])

    result = await scholarships_api.list_columns(scholarship_id=uuid4(), db=db)

    assert [item.name for item in result] == ["GPA", "Motivatsiya"]


@pytest.mark.asyncio
async def test_create_column_uses_next_order_index(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    db = DummyDB(execute_results=[_ExecuteResult(scalar=2)])

    async def _fake_get_scholarship(*args, **kwargs):
        return _build_scholarship(ScholarshipStatus.DRAFT)

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    result = await scholarships_api.create_column(
        scholarship_id=scholarship_id,
        payload=ColumnCreate(
            name="Maqolalar",
            description="Scopus indexed papers",
            field_type=ColumnFieldType.TEXTAREA,
            select_options=None,
            is_required=True,
            ai_analyze=True,
            max_score=25,
        ),
        _=object(),
        db=db,
    )

    assert len(db.added) == 1
    assert result.order_index == 3
    assert result.ai_analyze is True
    assert db.commits == 1


@pytest.mark.asyncio
async def test_create_number_column_saves_input_range(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    db = DummyDB(execute_results=[_ExecuteResult(scalar=None)])

    async def _fake_get_scholarship(*args, **kwargs):
        return _build_scholarship(ScholarshipStatus.DRAFT)

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    result = await scholarships_api.create_column(
        scholarship_id=scholarship_id,
        payload=ColumnCreate(
            name="GPA",
            description="Baholash balli",
            field_type=ColumnFieldType.NUMBER,
            select_options=None,
            is_required=True,
            ai_analyze=False,
            max_score=10,
            input_min=60,
            input_max=100,
        ),
        _=object(),
        db=db,
    )

    assert result.input_min == 60
    assert result.input_max == 100
    assert db.commits == 1


@pytest.mark.asyncio
async def test_update_column_changes_existing_column():
    column = _build_column()
    db = DummyDB(execute_results=[_ExecuteResult(scalar=column)])

    result = await scholarships_api.update_column(
        scholarship_id=column.scholarship_id,
        column_id=column.id,
        payload=ColumnUpdate(name="Updated GPA", max_score=35),
        _=object(),
        db=db,
    )

    assert column.name == "Updated GPA"
    assert column.max_score == 35
    assert db.commits == 1
    assert db.refreshed == [column]
    assert result.name == "Updated GPA"


@pytest.mark.asyncio
async def test_update_column_sets_number_range():
    column = _build_column(field_type=ColumnFieldType.NUMBER, input_min=None, input_max=None)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=column)])

    result = await scholarships_api.update_column(
        scholarship_id=column.scholarship_id,
        column_id=column.id,
        payload=ColumnUpdate(input_min=1, input_max=5),
        _=object(),
        db=db,
    )

    assert column.input_min == 1
    assert column.input_max == 5
    assert result.input_min == 1
    assert result.input_max == 5


@pytest.mark.asyncio
async def test_delete_column_removes_existing_column():
    column = _build_column()
    db = DummyDB(execute_results=[_ExecuteResult(scalar=column)])

    await scholarships_api.delete_column(
        scholarship_id=column.scholarship_id,
        column_id=column.id,
        _=object(),
        db=db,
    )

    assert db.deleted == [column]
    assert db.commits == 1


@pytest.mark.asyncio
async def test_reorder_columns_updates_all_known_columns(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    col1 = _build_column(order_index=0)
    col2 = _build_column(order_index=1)
    db = DummyDB(
        execute_results=[
            _ExecuteResult(scalar=col2),
            _ExecuteResult(scalar=col1),
        ]
    )

    async def _fake_get_scholarship(*args, **kwargs):
        return _build_scholarship(ScholarshipStatus.DRAFT)

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    result = await scholarships_api.reorder_columns(
        scholarship_id=scholarship_id,
        payload=ColumnReorder(order=[col2.id, col1.id]),
        _=object(),
        db=db,
    )

    assert result["detail"] == "Tartib yangilandi"
    assert col2.order_index == 0
    assert col1.order_index == 1
    assert db.commits == 1


@pytest.mark.asyncio
async def test_list_jury_returns_active_assignments():
    jury_user = _build_user(role=UserRole.JURY)
    assignment = SimpleNamespace(jury=jury_user)
    db = DummyDB(execute_results=[_ExecuteResult(rows=[assignment])])

    result = await scholarships_api.list_jury(
        scholarship_id=uuid4(),
        _=object(),
        db=db,
    )

    assert len(result) == 1
    assert result[0].email == jury_user.email


@pytest.mark.asyncio
async def test_assign_jury_creates_new_assignment(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    jury_user = _build_user(role=UserRole.JURY)
    db = DummyDB(
        execute_results=[
            _ExecuteResult(scalar=jury_user),
            _ExecuteResult(scalar=None),
        ]
    )

    async def _fake_get_scholarship(*args, **kwargs):
        return _build_scholarship(ScholarshipStatus.DRAFT)

    monkeypatch.setattr(scholarships_api, "_get_scholarship_or_404", _fake_get_scholarship)

    result = await scholarships_api.assign_jury(
        scholarship_id=scholarship_id,
        payload=JuryAssignRequest(jury_id=jury_user.id),
        _=object(),
        db=db,
    )

    assert result["detail"] == "Hakam biriktirildi"
    assert len(db.added) == 1
    assert db.commits == 1


@pytest.mark.asyncio
async def test_remove_jury_marks_assignment_inactive():
    assignment = SimpleNamespace(is_active=True)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=assignment)])

    await scholarships_api.remove_jury(
        scholarship_id=uuid4(),
        jury_id=uuid4(),
        _=object(),
        db=db,
    )

    assert assignment.is_active is False
    assert db.commits == 1
