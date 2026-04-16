from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.api.v1.evaluations as evaluations_api
from app.models.enums import ApplicationStatus, ScholarshipStatus, UserRole
from app.schemas.evaluation import EvaluationUpdate


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
        self.last_stmt = None
        self.added: list[object] = []
        self.commits = 0
        self.refresh_calls = 0

    async def execute(self, stmt):
        self.last_stmt = stmt
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
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "scores", None) is None:
            obj.scores = {}
        if getattr(obj, "total_score", None) is None:
            obj.total_score = None
        if getattr(obj, "final_comment", None) is None:
            obj.final_comment = None
        if getattr(obj, "ai_generated", None) is None:
            obj.ai_generated = False
        if getattr(obj, "is_submitted", None) is None:
            obj.is_submitted = False
        if getattr(obj, "submitted_at", None) is None:
            obj.submitted_at = None
        self.refresh_calls += 1


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


def _column(max_score: int, name: str = "column"):
    return SimpleNamespace(id=uuid4(), max_score=max_score, name=name)


def _build_application(status: ApplicationStatus, columns: list, student_id=None):
    return SimpleNamespace(
        id=uuid4(),
        scholarship_id=uuid4(),
        student_id=student_id or uuid4(),
        status=status,
        scholarship=SimpleNamespace(columns=columns),
    )


def _build_evaluation(application, jury_id, **overrides: object):
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "application_id": application.id,
        "jury_id": jury_id,
        "scores": {},
        "total_score": None,
        "final_comment": None,
        "ai_generated": False,
        "is_submitted": False,
        "submitted_at": None,
        "updated_at": now,
        "application": application,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_get_evaluation_returns_empty_payload_when_not_started(monkeypatch: pytest.MonkeyPatch):
    current_user = _build_user()
    application = _build_application(ApplicationStatus.SUBMITTED, columns=[])
    db = DummyDB(execute_results=[_ExecuteResult(scalar=None)])
    ensure_assignment = AsyncMock(return_value=None)

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(evaluations_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(evaluations_api, "_ensure_active_assignment", ensure_assignment)

    result = await evaluations_api.get_evaluation(
        application_id=application.id,
        current_user=current_user,
        db=db,
    )

    assert result.id is None
    assert result.application_id == application.id
    assert result.jury_id == current_user.id


@pytest.mark.asyncio
async def test_validate_scores_requires_all_scorable_columns():
    col1 = _column(max_score=20, name="GPA")
    col2 = _column(max_score=30, name="Motivatsiya")

    with pytest.raises(HTTPException) as exc_info:
        evaluations_api._validate_scores_before_submit(
            scores={str(col1.id): 18},
            columns=[col1, col2],
        )

    assert exc_info.value.status_code == 400
    assert "missing_columns" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_scores_ignores_zero_max_score_columns():
    technical_column = _column(max_score=0, name="Passport")
    scored_column = _column(max_score=40, name="Ilmiy ish")

    normalized = evaluations_api._validate_scores_before_submit(
        scores={str(scored_column.id): 35.678},
        columns=[technical_column, scored_column],
    )

    assert str(technical_column.id) not in normalized
    assert normalized[str(scored_column.id)] == 35.68


@pytest.mark.asyncio
async def test_list_visible_evaluations_for_owner_adds_submitted_filter(monkeypatch: pytest.MonkeyPatch):
    application_id = uuid4()
    student_id = uuid4()
    jury_id = uuid4()
    now = datetime.now(timezone.utc)

    app_obj = SimpleNamespace(
        id=application_id,
        scholarship_id=uuid4(),
        student_id=student_id,
        status=ApplicationStatus.REJECTED,
    )

    async def _fake_get_application(*args, **kwargs):
        return app_obj

    monkeypatch.setattr(evaluations_api, "_get_application_or_404", _fake_get_application)

    evaluation = SimpleNamespace(
        id=uuid4(),
        application_id=application_id,
        jury_id=jury_id,
        scores={},
        total_score=80.0,
        final_comment="Yaxshi",
        ai_generated=False,
        is_submitted=True,
        submitted_at=now,
    )
    db = DummyDB(
        execute_results=[_ExecuteResult(items=[evaluation])],
        get_map={
            ("Scholarship", app_obj.scholarship_id): SimpleNamespace(
                id=app_obj.scholarship_id,
                blind_review_enabled=False,
                status=ScholarshipStatus.DONE,
            )
        },
    )

    result = await evaluations_api.list_visible_evaluations(
        application_id=application_id,
        current_user=SimpleNamespace(id=student_id, role=UserRole.STUDENT),
        db=db,
    )

    assert len(result) == 1
    assert result[0].is_submitted is True
    assert "is_submitted" in str(db.last_stmt)


@pytest.mark.asyncio
async def test_list_visible_evaluations_hides_reviews_from_student_until_final_status(monkeypatch: pytest.MonkeyPatch):
    application_id = uuid4()
    student_id = uuid4()
    app_obj = SimpleNamespace(
        id=application_id,
        scholarship_id=uuid4(),
        student_id=student_id,
        status=ApplicationStatus.IN_REVIEW,
    )

    async def _fake_get_application(*args, **kwargs):
        return app_obj

    monkeypatch.setattr(evaluations_api, "_get_application_or_404", _fake_get_application)

    db = DummyDB(
        execute_results=[],
        get_map={
            ("Scholarship", app_obj.scholarship_id): SimpleNamespace(
                id=app_obj.scholarship_id,
                blind_review_enabled=False,
                status=ScholarshipStatus.OPEN,
            )
        },
    )
    result = await evaluations_api.list_visible_evaluations(
        application_id=application_id,
        current_user=SimpleNamespace(id=student_id, role=UserRole.STUDENT),
        db=db,
    )

    assert result == []
    assert db.last_stmt is None


@pytest.mark.asyncio
async def test_list_visible_evaluations_for_blind_review_jury_filters_to_current_jury(monkeypatch: pytest.MonkeyPatch):
    application_id = uuid4()
    scholarship_id = uuid4()
    jury_id = uuid4()
    app_obj = SimpleNamespace(
        id=application_id,
        scholarship_id=scholarship_id,
        student_id=uuid4(),
    )

    async def _fake_get_application(*args, **kwargs):
        return app_obj

    monkeypatch.setattr(evaluations_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(evaluations_api, "_is_active_assignment", AsyncMock(return_value=True))

    evaluation = SimpleNamespace(
        id=uuid4(),
        application_id=application_id,
        jury_id=jury_id,
        scores={},
        total_score=88.0,
        final_comment="Yaxshi",
        ai_generated=False,
        is_submitted=True,
        submitted_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = DummyDB(
        execute_results=[_ExecuteResult(items=[evaluation])],
        get_map={("Scholarship", scholarship_id): SimpleNamespace(id=scholarship_id, blind_review_enabled=True)},
    )

    result = await evaluations_api.list_visible_evaluations(
        application_id=application_id,
        current_user=SimpleNamespace(id=jury_id, role=UserRole.JURY),
        db=db,
    )

    assert len(result) == 1
    assert "jury_id" in str(db.last_stmt)


@pytest.mark.asyncio
async def test_list_visible_evaluations_denies_unrelated_student(monkeypatch: pytest.MonkeyPatch):
    application_id = uuid4()
    app_obj = SimpleNamespace(
        id=application_id,
        scholarship_id=uuid4(),
        student_id=uuid4(),
    )

    async def _fake_get_application(*args, **kwargs):
        return app_obj

    monkeypatch.setattr(evaluations_api, "_get_application_or_404", _fake_get_application)

    db = DummyDB(execute_results=[_ExecuteResult(items=[])])
    with pytest.raises(HTTPException) as exc_info:
        await evaluations_api.list_visible_evaluations(
            application_id=application_id,
            current_user=SimpleNamespace(id=uuid4(), role=UserRole.STUDENT),
            db=db,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_evaluation_starts_review_for_submitted_application(monkeypatch: pytest.MonkeyPatch):
    current_user = _build_user()
    application = _build_application(ApplicationStatus.SUBMITTED, columns=[_column(30)])
    db = DummyDB(execute_results=[_ExecuteResult(scalar=None)])
    ensure_assignment = AsyncMock(return_value=None)
    ensure_stage = AsyncMock(return_value=None)
    queued_status_log_ids: list[list] = []

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(evaluations_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(evaluations_api, "_ensure_active_assignment", ensure_assignment)
    monkeypatch.setattr(evaluations_api, "_ensure_stage_allows_jury_actions", ensure_stage)
    monkeypatch.setattr(
        evaluations_api,
        "queue_application_status_email_tasks",
        lambda status_log_ids: queued_status_log_ids.append(list(status_log_ids)),
    )

    result = await evaluations_api.create_evaluation(
        application_id=application.id,
        current_user=current_user,
        db=db,
    )

    assert len(db.added) == 2
    assert db.added[0].__class__.__name__ == "Evaluation"
    assert db.added[1].__class__.__name__ == "ApplicationStatusLog"
    assert application.status == ApplicationStatus.IN_REVIEW
    assert result.jury_id == current_user.id
    assert result.scores == {}
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert queued_status_log_ids and len(queued_status_log_ids[0]) == 1


@pytest.mark.asyncio
async def test_update_evaluation_updates_scores_and_comment(monkeypatch: pytest.MonkeyPatch):
    current_user = _build_user()
    col1 = _column(20, "GPA")
    col2 = _column(30, "Motivatsiya")
    application = _build_application(ApplicationStatus.IN_REVIEW, columns=[col1, col2])
    evaluation = _build_evaluation(application, current_user.id)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=evaluation)])
    ensure_stage = AsyncMock(return_value=None)
    monkeypatch.setattr(evaluations_api, "_ensure_stage_allows_jury_actions", ensure_stage)

    result = await evaluations_api.update_evaluation(
        application_id=application.id,
        payload=EvaluationUpdate(
            scores={
                str(col1.id): 18,
                str(col2.id): 27,
            },
            final_comment="Kuchli ariza",
            ai_generated=True,
        ),
        current_user=current_user,
        db=db,
    )

    assert evaluation.scores[str(col1.id)] == 18.0
    assert evaluation.scores[str(col2.id)] == 27.0
    assert evaluation.total_score == 90.0
    assert evaluation.final_comment == "Kuchli ariza"
    assert evaluation.ai_generated is True
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert result.total_score == 90.0


@pytest.mark.asyncio
async def test_submit_evaluation_marks_submitted_and_updates_application_average(monkeypatch: pytest.MonkeyPatch):
    current_user = _build_user()
    col1 = _column(20, "GPA")
    col2 = _column(30, "Motivatsiya")
    application = _build_application(ApplicationStatus.SUBMITTED, columns=[col1, col2])
    evaluation = _build_evaluation(
        application,
        current_user.id,
        scores={
            str(col1.id): 18,
            str(col2.id): 24,
        },
    )
    other_evaluation = _build_evaluation(
        application,
        uuid4(),
        scores={},
        total_score=84.0,
        is_submitted=True,
        submitted_at=datetime.now(timezone.utc),
    )
    db = DummyDB(
        execute_results=[
            _ExecuteResult(scalar=evaluation),
            _ExecuteResult(items=[evaluation, other_evaluation]),
        ]
    )
    ensure_stage = AsyncMock(return_value=None)
    queued_status_log_ids: list[list] = []
    monkeypatch.setattr(evaluations_api, "_ensure_stage_allows_jury_actions", ensure_stage)
    monkeypatch.setattr(
        evaluations_api,
        "queue_application_status_email_tasks",
        lambda status_log_ids: queued_status_log_ids.append(list(status_log_ids)),
    )

    result = await evaluations_api.submit_evaluation(
        application_id=application.id,
        current_user=current_user,
        db=db,
    )

    assert evaluation.is_submitted is True
    assert evaluation.submitted_at is not None
    assert evaluation.total_score == 84.0
    assert application.status == ApplicationStatus.IN_REVIEW
    assert application.total_score == 84.0
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert result.is_submitted is True
    assert queued_status_log_ids and len(queued_status_log_ids[0]) == 1
