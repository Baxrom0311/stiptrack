from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.api.v1.templates as templates_api
from app.models.enums import ColumnFieldType, ScholarshipStageType, ScholarshipStatus, StageTaskStatus, UserRole
from app.schemas.template import ScholarshipTemplateCreate, ScholarshipTemplateInstantiate
from app.services.template_service import build_scholarship_template_snapshot, instantiate_scholarship_from_template


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _ExecuteResult:
    def __init__(self, items=None, scalar=None):
        self._items = items or []
        self._scalar = scalar

    def scalars(self):
        return _ScalarResult(self._items)

    def scalar_one_or_none(self):
        if self._scalar is not None:
            return self._scalar
        if len(self._items) == 1:
            return self._items[0]
        if not self._items:
            return None
        raise AssertionError("Expected zero or one item")


class DummyDB:
    def __init__(self, execute_results=None, get_map=None):
        self._execute_results = list(execute_results or [])
        self._get_map = dict(get_map or {})
        self.added: list[object] = []
        self.commits = 0
        self.refresh_calls = 0

    async def execute(self, _stmt):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call")
        return self._execute_results.pop(0)

    async def get(self, model, obj_id):
        key = (getattr(model, "__name__", str(model)), obj_id)
        if key in self._get_map:
            return self._get_map[key]
        return self._get_map.get(getattr(model, "__name__", str(model)))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        now = datetime.now(timezone.utc)
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        self.refresh_calls += 1


def _build_user(role: UserRole = UserRole.ADMIN, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "Admin User",
        "email": "admin@example.com",
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


def _build_column(order_index: int = 0, **overrides: object) -> SimpleNamespace:
    data = {
        "id": uuid4(),
        "name": "Motivatsiya",
        "description": "Motivatsion xat",
        "field_type": ColumnFieldType.TEXTAREA,
        "select_options": None,
        "is_required": True,
        "ai_analyze": True,
        "max_score": 30,
        "input_min": None,
        "input_max": None,
        "order_index": order_index,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_task(stage_id, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "stage_id": stage_id,
        "title": "Task",
        "description": "Task desc",
        "assigned_to": None,
        "assigned_role": UserRole.JURY,
        "status": StageTaskStatus.TODO,
        "due_at": now + timedelta(days=1),
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_stage(order_index: int = 0, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    stage_id = overrides.pop("id", uuid4())
    data = {
        "id": stage_id,
        "scholarship_id": uuid4(),
        "name": "Application stage",
        "stage_type": ScholarshipStageType.APPLICATION,
        "description": "15 kun",
        "order_index": order_index,
        "starts_at": now,
        "ends_at": now + timedelta(days=15),
        "is_required": True,
        "is_active": True,
        "config": {"days": 15},
        "tasks": [_build_task(stage_id)],
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_scholarship(**overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "created_by": uuid4(),
        "title": "Rektor stipendiyasi",
        "description": "Iqtidorli talabalar uchun",
        "nizom_file_url": "nizom/rektor.pdf",
        "status": ScholarshipStatus.DRAFT,
        "deadline": None,
        "ai_analysis_enabled": True,
        "blind_review_enabled": True,
        "max_winners": 2,
        "ai_provider": "openai",
        "ai_model": "gpt-4.1-mini",
        "created_at": now,
        "updated_at": now,
        "columns": [_build_column()],
        "stages": [_build_stage()],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_template(snapshot: dict | None = None, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    scholarship = _build_scholarship()
    data = {
        "id": uuid4(),
        "created_by": uuid4(),
        "source_scholarship_id": scholarship.id,
        "name": "Base template",
        "description": "Template desc",
        "snapshot": snapshot or build_scholarship_template_snapshot(scholarship),
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_build_scholarship_template_snapshot_includes_columns_stages_and_tasks():
    scholarship = _build_scholarship()

    snapshot = build_scholarship_template_snapshot(scholarship)

    assert snapshot["scholarship"]["title"] == scholarship.title
    assert snapshot["scholarship"]["blind_review_enabled"] is True
    assert snapshot["scholarship"]["ai_provider"] == "openai"
    assert snapshot["scholarship"]["ai_model"] == "gpt-4.1-mini"
    assert len(snapshot["columns"]) == 1
    assert len(snapshot["stages"]) == 1
    assert len(snapshot["stages"][0]["tasks"]) == 1


def test_instantiate_scholarship_from_template_returns_entities():
    template = _build_template()
    admin = _build_user()

    scholarship, columns, stages, tasks = instantiate_scholarship_from_template(template, created_by=admin.id)

    assert scholarship.created_by == admin.id
    assert scholarship.title == "Rektor stipendiyasi"
    assert scholarship.blind_review_enabled is True
    assert scholarship.ai_provider.value == "openai"
    assert scholarship.ai_model == "gpt-4.1-mini"
    assert len(columns) == 1
    assert len(stages) == 1
    assert len(tasks) == 1
    assert tasks[0].stage_id == stages[0].id


@pytest.mark.asyncio
async def test_list_scholarship_templates_returns_summaries():
    template = _build_template()
    db = DummyDB(execute_results=[_ExecuteResult(items=[template])])

    result = await templates_api.list_scholarship_templates(_=_build_user(), db=db)

    assert len(result) == 1
    assert result[0].name == template.name
    assert result[0].ai_provider.value == "openai"
    assert result[0].ai_model == "gpt-4.1-mini"
    assert result[0].column_count == 1
    assert result[0].stage_count == 1
    assert result[0].task_count == 1


@pytest.mark.asyncio
async def test_create_scholarship_template_snapshots_existing_scholarship():
    scholarship = _build_scholarship()
    db = DummyDB(execute_results=[_ExecuteResult(scalar=scholarship)])
    admin = _build_user()

    result = await templates_api.create_scholarship_template(
        payload=ScholarshipTemplateCreate(
            scholarship_id=scholarship.id,
            name="Rektor base",
            description="Reusable template",
        ),
        current_user=admin,
        db=db,
    )

    assert db.commits == 1
    assert db.refresh_calls == 1
    assert len(db.added) == 1
    assert db.added[0].snapshot["scholarship"]["title"] == scholarship.title
    assert db.added[0].snapshot["scholarship"]["ai_provider"] == "openai"
    assert result.name == "Rektor base"
    assert result.column_count == 1


@pytest.mark.asyncio
async def test_instantiate_template_endpoint_creates_new_scholarship_with_overrides():
    template = _build_template()
    template_id = template.id
    admin = _build_user()
    db = DummyDB(get_map={("ScholarshipTemplate", template_id): template})
    starts_at = datetime.now(timezone.utc) + timedelta(days=7)

    result = await templates_api.instantiate_scholarship_template(
        template_id=template_id,
        payload=ScholarshipTemplateInstantiate(
            title="Rektor stipendiyasi 2026",
            description="Yangi oqim",
            deadline=starts_at + timedelta(days=30),
            starts_at=starts_at,
        ),
        current_user=admin,
        db=db,
    )

    assert db.commits == 1
    assert db.refresh_calls == 1
    assert len(db.added) == 4
    assert result.title == "Rektor stipendiyasi 2026"
    assert result.description == "Yangi oqim"
    assert result.blind_review_enabled is True
