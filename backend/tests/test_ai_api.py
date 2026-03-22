from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.api.v1.ai as ai_api
from app.models.enums import AIJobStatus, AIJobType, ColumnFieldType, UserRole
from app.schemas.ai_job import GenerateColumnsRequest
from app.schemas.evaluation import AIReviewRequest


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
        if getattr(obj, "result", None) is None:
            obj.result = None
        if getattr(obj, "error_msg", None) is None:
            obj.error_msg = None
        if getattr(obj, "finished_at", None) is None:
            obj.finished_at = None
        self.refresh_calls += 1


def _build_user(role: UserRole, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "AI User",
        "email": "ai@example.com",
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


def _build_job(job_type: AIJobType, ref_id, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "job_type": job_type,
        "ref_id": ref_id,
        "model_used": "claude",
        "status": AIJobStatus.DONE,
        "result": {"ok": True},
        "error_msg": None,
        "created_at": now,
        "finished_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_column(ai_analyze: bool = False, **overrides: object) -> SimpleNamespace:
    data = {
        "id": uuid4(),
        "name": "Motivatsiya",
        "description": "Motivatsiya xati",
        "field_type": ColumnFieldType.TEXTAREA,
        "select_options": None,
        "is_required": True,
        "ai_analyze": ai_analyze,
        "max_score": 30,
        "input_min": None,
        "input_max": None,
        "order_index": 0,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class _SubScore:
    def __init__(self, label: str, score: int):
        self.label = label
        self.score = score


class _Criterion:
    def __init__(self, name: str, max_score: int, description: str):
        self.name = name
        self.max_score = max_score
        self.description = description
        self.sub_scores = [_SubScore("A'lo", max_score)]


class _ReviewResult:
    def __init__(self):
        self.review_text = "AI review text"
        self.summary = "Summary"
        self.recommendation_note = "Recommendation"
        self.total_score = 87.0
        self.max_total_score = 100.0
        self.score_percent = 87.0

    def model_dump(self):
        return {
            "review_text": self.review_text,
            "summary": self.summary,
            "recommendation_note": self.recommendation_note,
            "total_score": self.total_score,
            "max_total_score": self.max_total_score,
            "score_percent": self.score_percent,
        }


@pytest.mark.asyncio
async def test_get_job_status_returns_job_for_admin():
    ref_id = uuid4()
    job = _build_job(AIJobType.COLUMN_GEN, ref_id)
    db = DummyDB(get_map={("AIJob", job.id): job})

    result = await ai_api.get_job_status(
        job_id=job.id,
        current_user=_build_user(UserRole.ADMIN),
        db=db,
    )

    assert result.id == job.id
    assert result.status == AIJobStatus.DONE


@pytest.mark.asyncio
async def test_get_job_status_denies_unrelated_student_for_application_job():
    owner = _build_user(UserRole.STUDENT, email="owner@example.com")
    outsider = _build_user(UserRole.STUDENT, email="outsider@example.com")
    application = SimpleNamespace(
        id=uuid4(),
        scholarship_id=uuid4(),
        student_id=owner.id,
    )
    job = _build_job(AIJobType.APP_ANALYSIS, application.id)
    db = DummyDB(
        get_map={
            ("AIJob", job.id): job,
            ("Application", application.id): application,
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        await ai_api.get_job_status(
            job_id=job.id,
            current_user=outsider,
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Ruxsat yo'q"


@pytest.mark.asyncio
async def test_parse_nizom_endpoint_returns_transformed_response(monkeypatch: pytest.MonkeyPatch):
    scholarship = SimpleNamespace(
        id=uuid4(),
        nizom_file_url="nizom/rektor.pdf",
        ai_provider="openai",
        ai_model="gpt-4.1-mini",
    )
    parse_result = SimpleNamespace(
        title="Rektor stipendiyasi",
        purpose="Iqtidorli talabalarni rag'batlantirish",
        requirements=["GPA 3.5+"],
        evaluation_criteria=[_Criterion("GPA", 30, "Akademik ko'rsatkich")],
        additional_docs=["Diplom"],
        scoring_type="table",
        total_max_score=30,
        eligible_students="2-4 kurs",
        selection_stages="Ariza -> Review",
        deadline_hint="2026-04-01",
        amount_hint="1 000 000 so'm",
    )
    db = DummyDB(get_map={("Scholarship", scholarship.id): scholarship})

    async def _parse_nizom(file_url: str, llm_provider: str | None = None, llm_model: str | None = None):
        assert file_url == "https://signed.example/nizom/rektor.pdf"
        assert llm_provider == "openai"
        assert llm_model == "gpt-4.1-mini"
        return parse_result

    monkeypatch.setattr(ai_api, "parse_nizom", _parse_nizom)
    monkeypatch.setattr(
        ai_api,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await ai_api.parse_nizom_endpoint(
        scholarship_id=scholarship.id,
        _=object(),
        db=db,
    )

    assert result["title"] == "Rektor stipendiyasi"
    assert result["evaluation_criteria"] == ["GPA"]
    assert result["evaluation_criteria_detailed"][0]["max_score"] == 30


@pytest.mark.asyncio
async def test_generate_columns_creates_job_and_dispatches_worker(monkeypatch: pytest.MonkeyPatch):
    scholarship = SimpleNamespace(
        id=uuid4(),
        title="Test scholarship",
        nizom_file_url="https://files/nizom.pdf",
        ai_provider="gemini",
        ai_model="gemini-2.5-flash",
    )
    db = DummyDB(get_map={("Scholarship", scholarship.id): scholarship})
    delayed_calls: list[dict] = []

    class _Task:
        @staticmethod
        def delay(**kwargs):
            delayed_calls.append(kwargs)

    import workers.tasks as worker_tasks

    monkeypatch.setattr(worker_tasks, "run_column_generation", _Task)

    result = await ai_api.generate_columns(
        scholarship_id=scholarship.id,
        payload=GenerateColumnsRequest(
            purpose="Maqsad",
            requirements=["GPA 3.5+"],
            evaluation_criteria=["GPA"],
            additional_docs=["Diplom"],
            total_max_score=100,
            scoring_type="table",
            eligible_students="2-4 kurs",
            selection_stages="Ariza -> Review",
        ),
        _=object(),
        db=db,
    )

    assert result["detail"] == "Ustun generatsiyasi boshlandi"
    assert len(db.added) == 1
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert delayed_calls
    assert delayed_calls[0]["scholarship_id"] == str(scholarship.id)
    assert delayed_calls[0]["llm_provider"] == "gemini"
    assert delayed_calls[0]["llm_model"] == "gemini-2.5-flash"
    assert db.added[0].model_used == "gemini:gemini-2.5-flash"


@pytest.mark.asyncio
async def test_generate_ai_review_updates_evaluation_with_ai_output(monkeypatch: pytest.MonkeyPatch):
    jury = _build_user(UserRole.JURY)
    ai_column = _build_column(ai_analyze=True)
    scholarship = SimpleNamespace(
        id=uuid4(),
        title="Rektor stipendiyasi",
        columns=[ai_column],
        blind_review_enabled=False,
        ai_provider="claude",
        ai_model="claude-3-7-sonnet",
    )
    student = _build_user(UserRole.STUDENT, full_name="Ali Valiyev")
    application = SimpleNamespace(
        id=uuid4(),
        scholarship_id=scholarship.id,
        scholarship=scholarship,
        student=student,
        values=[
            SimpleNamespace(
                column=ai_column,
                ai_analysis="AI tahlil",
            )
        ],
    )
    evaluation = SimpleNamespace(
        application_id=application.id,
        jury_id=jury.id,
        scores={str(ai_column.id): 26.0},
        final_comment=None,
        ai_generated=False,
    )
    db = DummyDB(
        execute_results=[
            _ExecuteResult(scalar=application),
            _ExecuteResult(scalar=evaluation),
        ]
    )

    monkeypatch.setattr(ai_api, "_is_active_jury_assignment", AsyncMock(return_value=True))
    review_mock = AsyncMock(return_value=_ReviewResult())
    monkeypatch.setattr(ai_api, "generate_review", review_mock)

    result = await ai_api.generate_ai_review(
        application_id=application.id,
        payload=AIReviewRequest(jury_notes="Manual note"),
        current_user=jury,
        db=db,
    )

    assert result.review_text == "AI review text"
    assert evaluation.final_comment == "AI review text"
    assert evaluation.ai_generated is True
    assert db.commits == 1
    assert review_mock.await_args.kwargs["llm_provider"] == "claude"
    assert review_mock.await_args.kwargs["llm_model"] == "claude-3-7-sonnet"


@pytest.mark.asyncio
async def test_generate_ai_review_uses_anonymous_student_name_for_blind_review(monkeypatch: pytest.MonkeyPatch):
    jury = _build_user(UserRole.JURY)
    ai_column = _build_column(ai_analyze=True)
    scholarship = SimpleNamespace(
        id=uuid4(),
        title="Rektor stipendiyasi",
        columns=[ai_column],
        blind_review_enabled=True,
        ai_provider="openai",
        ai_model="gpt-4.1",
    )
    student = _build_user(UserRole.STUDENT, full_name="Ali Valiyev")
    application = SimpleNamespace(
        id=uuid4(),
        scholarship_id=scholarship.id,
        scholarship=scholarship,
        student=student,
        values=[SimpleNamespace(column=ai_column, ai_analysis="AI tahlil")],
    )
    evaluation = SimpleNamespace(
        application_id=application.id,
        jury_id=jury.id,
        scores={str(ai_column.id): 26.0},
        final_comment=None,
        ai_generated=False,
    )
    db = DummyDB(
        execute_results=[
            _ExecuteResult(scalar=application),
            _ExecuteResult(scalar=evaluation),
        ]
    )
    review_mock = AsyncMock(return_value=_ReviewResult())

    monkeypatch.setattr(ai_api, "_is_active_jury_assignment", AsyncMock(return_value=True))
    monkeypatch.setattr(ai_api, "generate_review", review_mock)

    await ai_api.generate_ai_review(
        application_id=application.id,
        payload=AIReviewRequest(jury_notes="Manual note"),
        current_user=jury,
        db=db,
    )

    assert review_mock.await_args.kwargs["student_name"] == "Anonim nomzod"
    assert review_mock.await_args.kwargs["llm_provider"] == "openai"
    assert review_mock.await_args.kwargs["llm_model"] == "gpt-4.1"
