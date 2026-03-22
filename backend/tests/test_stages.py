from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.api.v1.stages as stages_api
from app.models.enums import ScholarshipStageType, StageTaskStatus, UserRole
from app.schemas.workflow import StageCreate, StageReorder, StageTaskCreate, StageTaskUpdate


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
        self.deleted: list[object] = []
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
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        if getattr(obj, "status", None) is None and hasattr(obj, "title"):
            obj.status = StageTaskStatus.TODO
        self.refresh_calls += 1

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


def _build_stage(stage_type: ScholarshipStageType = ScholarshipStageType.APPLICATION, **overrides: object):
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "scholarship_id": uuid4(),
        "name": "Bosqich",
        "stage_type": stage_type,
        "description": "desc",
        "order_index": 0,
        "starts_at": now,
        "ends_at": now + timedelta(days=3),
        "is_required": True,
        "is_active": True,
        "config": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_stage_task(stage_id, **overrides: object):
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "stage_id": stage_id,
        "title": "Task",
        "description": None,
        "assigned_to": None,
        "assigned_role": None,
        "status": StageTaskStatus.TODO,
        "due_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_list_stages_returns_ordered_stages(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage1 = _build_stage(order_index=0, name="Ariza")
    stage2 = _build_stage(order_index=1, name="Review")
    db = DummyDB(execute_results=[_ExecuteResult(items=[stage1, stage2])])

    async def _get_scholarship(*args, **kwargs):
        return SimpleNamespace(id=scholarship_id, status="open")

    monkeypatch.setattr(stages_api, "_get_scholarship_or_404", _get_scholarship)

    result = await stages_api.list_stages(
        scholarship_id=scholarship_id,
        current_user=SimpleNamespace(role=UserRole.ADMIN),
        db=db,
    )

    assert [item.name for item in result] == ["Ariza", "Review"]


@pytest.mark.asyncio
async def test_get_active_stage_returns_current_stage(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage = _build_stage(stage_type=ScholarshipStageType.REVIEW, name="Review")
    db = DummyDB(execute_results=[_ExecuteResult(scalar=stage)])

    async def _get_scholarship(*args, **kwargs):
        return SimpleNamespace(id=scholarship_id)

    monkeypatch.setattr(stages_api, "_get_scholarship_or_404", _get_scholarship)

    result = await stages_api.get_active_stage(
        scholarship_id=scholarship_id,
        _=object(),
        db=db,
    )

    assert result.id == stage.id
    assert result.stage_type == ScholarshipStageType.REVIEW


@pytest.mark.asyncio
async def test_create_stage_assigns_next_order(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    now = datetime.now(timezone.utc)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=1)])

    async def _get_scholarship(*args, **kwargs):
        return SimpleNamespace(id=scholarship_id)

    monkeypatch.setattr(stages_api, "_get_scholarship_or_404", _get_scholarship)

    result = await stages_api.create_stage(
        scholarship_id=scholarship_id,
        payload=StageCreate(
            name="Hujjatlarni qabul qilish",
            stage_type=ScholarshipStageType.APPLICATION,
            description="15 kunlik bosqich",
            starts_at=now,
            ends_at=now + timedelta(days=15),
            is_required=True,
            is_active=True,
            config=None,
        ),
        _=object(),
        db=db,
    )

    assert result.order_index == 2
    assert result.stage_type == ScholarshipStageType.APPLICATION
    assert db.commits == 1
    assert db.refresh_calls == 1


@pytest.mark.asyncio
async def test_update_stage_changes_existing_stage(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage = _build_stage(scholarship_id=scholarship_id, name="Old stage")
    db = DummyDB()

    async def _get_stage(*args, **kwargs):
        return stage

    monkeypatch.setattr(stages_api, "_get_stage_or_404", _get_stage)

    result = await stages_api.update_stage(
        scholarship_id=scholarship_id,
        stage_id=stage.id,
        payload=stages_api.StageUpdate(name="New stage", is_active=False),
        _=object(),
        db=db,
    )

    assert stage.name == "New stage"
    assert stage.is_active is False
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert result.name == "New stage"


@pytest.mark.asyncio
async def test_delete_stage_removes_existing_stage(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage = _build_stage(scholarship_id=scholarship_id)
    db = DummyDB()

    async def _get_stage(*args, **kwargs):
        return stage

    monkeypatch.setattr(stages_api, "_get_stage_or_404", _get_stage)

    await stages_api.delete_stage(
        scholarship_id=scholarship_id,
        stage_id=stage.id,
        _=object(),
        db=db,
    )

    assert db.deleted == [stage]
    assert db.commits == 1


@pytest.mark.asyncio
async def test_reorder_stages_updates_stage_indexes(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage1 = SimpleNamespace(id=uuid4(), order_index=0)
    stage2 = SimpleNamespace(id=uuid4(), order_index=1)
    db = DummyDB(execute_results=[_ExecuteResult(items=[stage1, stage2])])

    async def _get_scholarship(*args, **kwargs):
        return SimpleNamespace(id=scholarship_id)

    monkeypatch.setattr(stages_api, "_get_scholarship_or_404", _get_scholarship)

    result = await stages_api.reorder_stages(
        scholarship_id=scholarship_id,
        payload=StageReorder(order=[stage2.id, stage1.id]),
        _=object(),
        db=db,
    )

    assert result["detail"] == "Bosqichlar tartibi yangilandi"
    assert stage2.order_index == 0
    assert stage1.order_index == 1
    assert db.commits == 1


@pytest.mark.asyncio
async def test_list_stage_tasks_returns_all_tasks(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage_id = uuid4()
    task1 = _build_stage_task(stage_id, title="Task 1")
    task2 = _build_stage_task(stage_id, title="Task 2")
    db = DummyDB(execute_results=[_ExecuteResult(items=[task1, task2])])

    async def _get_stage(*args, **kwargs):
        return _build_stage(id=stage_id, scholarship_id=scholarship_id)

    monkeypatch.setattr(stages_api, "_get_stage_or_404", _get_stage)

    result = await stages_api.list_stage_tasks(
        scholarship_id=scholarship_id,
        stage_id=stage_id,
        _=object(),
        db=db,
    )

    assert [item.title for item in result] == ["Task 1", "Task 2"]


@pytest.mark.asyncio
async def test_create_stage_task_persists_assigned_user(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage_id = uuid4()
    assigned_to = uuid4()
    db = DummyDB(get_map={("User", assigned_to): SimpleNamespace(id=assigned_to)})

    async def _get_stage(*args, **kwargs):
        return SimpleNamespace(id=stage_id, scholarship_id=scholarship_id)

    monkeypatch.setattr(stages_api, "_get_stage_or_404", _get_stage)

    result = await stages_api.create_stage_task(
        scholarship_id=scholarship_id,
        stage_id=stage_id,
        payload=StageTaskCreate(
            title="Arizalarni tekshirish",
            description="Jury review",
            assigned_to=assigned_to,
            assigned_role=UserRole.JURY,
            due_at=None,
        ),
        _=object(),
        db=db,
    )

    assert result.assigned_to == assigned_to
    assert result.assigned_role == UserRole.JURY
    assert result.status == StageTaskStatus.TODO
    assert db.commits == 1


@pytest.mark.asyncio
async def test_update_stage_task_sets_completed_at_when_done(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage_id = uuid4()
    task_id = uuid4()
    now = datetime.now(timezone.utc)
    task = SimpleNamespace(
        id=task_id,
        stage_id=stage_id,
        title="Review task",
        description=None,
        assigned_to=None,
        assigned_role=None,
        status=StageTaskStatus.IN_PROGRESS,
        due_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    db = DummyDB(execute_results=[_ExecuteResult(scalar=task)])

    async def _get_stage(*args, **kwargs):
        return SimpleNamespace(id=stage_id, scholarship_id=scholarship_id)

    monkeypatch.setattr(stages_api, "_get_stage_or_404", _get_stage)

    result = await stages_api.update_stage_task(
        scholarship_id=scholarship_id,
        stage_id=stage_id,
        task_id=task_id,
        payload=StageTaskUpdate(status=StageTaskStatus.DONE),
        _=object(),
        db=db,
    )

    assert result.status == StageTaskStatus.DONE
    assert task.completed_at is not None
    assert db.commits == 1
    assert db.refresh_calls == 1


@pytest.mark.asyncio
async def test_delete_stage_task_removes_existing_task(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    stage_id = uuid4()
    task = _build_stage_task(stage_id)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=task)])

    async def _get_stage(*args, **kwargs):
        return _build_stage(id=stage_id, scholarship_id=scholarship_id)

    monkeypatch.setattr(stages_api, "_get_stage_or_404", _get_stage)

    await stages_api.delete_stage_task(
        scholarship_id=scholarship_id,
        stage_id=stage_id,
        task_id=task.id,
        _=object(),
        db=db,
    )

    assert db.deleted == [task]
    assert db.commits == 1
