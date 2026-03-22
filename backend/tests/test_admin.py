from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.api.v1.admin as admin_api
from app.models.enums import AIJobStatus, AIJobType, ApplicationStatus, ScholarshipStatus, UserRole


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
        return self._scalar

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
    def __init__(self, execute_results, get_map=None):
        self._execute_results = list(execute_results)
        self._get_map = dict(get_map or {})

    async def execute(self, _stmt):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call")
        return self._execute_results.pop(0)

    async def get(self, model, obj_id):
        key = (getattr(model, "__name__", str(model)), obj_id)
        if key in self._get_map:
            return self._get_map[key]
        return self._get_map.get(getattr(model, "__name__", str(model)))


@pytest.mark.asyncio
async def test_get_admin_stats_aggregates_all_sections(monkeypatch: pytest.MonkeyPatch):
    async def _fake_trend(db, days: int = 7):
        return [{"date": "2026-03-19", "count": 3}]

    async def _fake_recent_activity(db, limit: int = 12):
        return [
            {
                "entity_type": "scholarship",
                "entity_id": str(uuid4()),
                "title": "Rektor stipendiyasi",
                "subtitle": "Yangi stipendiya yaratildi",
                "status": "open",
                "created_at": datetime.now(timezone.utc),
            }
        ]

    monkeypatch.setattr(admin_api, "_build_application_trend", _fake_trend)
    monkeypatch.setattr(admin_api, "_build_recent_activity", _fake_recent_activity)

    db = DummyDB(
        execute_results=[
            _ExecuteResult(rows=[(ScholarshipStatus.OPEN, 4), (ScholarshipStatus.DONE, 1)]),
            _ExecuteResult(rows=[(ApplicationStatus.SUBMITTED, 5), (ApplicationStatus.WINNER, 2)]),
            _ExecuteResult(rows=[(UserRole.STUDENT, 20), (UserRole.ADMIN, 1)]),
            _ExecuteResult(rows=[(AIJobStatus.DONE, 7), (AIJobStatus.FAILED, 1)]),
            _ExecuteResult(rows=[(AIJobType.COLUMN_GEN, 3), (AIJobType.APP_ANALYSIS, 5)]),
            _ExecuteResult(scalar=5),
            _ExecuteResult(scalar=9),
            _ExecuteResult(scalar=21),
            _ExecuteResult(scalar=8),
        ]
    )

    result = await admin_api.get_admin_stats(_=object(), db=db)

    assert result.total_scholarships == 5
    assert result.total_applications == 9
    assert result.total_users == 21
    assert result.total_ai_jobs == 8
    assert result.scholarships_by_status["open"] == 4
    assert result.users_by_role["student"] == 20
    assert result.ai_jobs_by_type["app_analysis"] == 5
    assert result.application_trend[0].count == 3
    assert result.recent_activity[0].entity_type == "scholarship"


@pytest.mark.asyncio
async def test_get_scholarship_results_builds_ranked_rows():
    scholarship_id = uuid4()
    scholarship = SimpleNamespace(
        id=scholarship_id,
        title="Rektor stipendiyasi",
        status=ScholarshipStatus.DONE,
        max_winners=2,
    )
    now = datetime.now(timezone.utc)

    app1 = SimpleNamespace(
        id=uuid4(),
        student_id=uuid4(),
        student=SimpleNamespace(full_name="Ali Valiyev"),
        status=ApplicationStatus.WINNER,
        total_score=95.0,
        submitted_at=now,
        created_at=now,
        evaluations=[
            SimpleNamespace(
                id=uuid4(),
                jury_id=uuid4(),
                jury=SimpleNamespace(full_name="Jury One"),
                total_score=95.0,
                final_comment="A'lo",
                is_submitted=True,
                submitted_at=now,
            ),
            SimpleNamespace(
                id=uuid4(),
                jury_id=uuid4(),
                jury=SimpleNamespace(full_name="Jury Two"),
                total_score=80.0,
                final_comment="Yaxshi",
                is_submitted=True,
                submitted_at=now,
            ),
        ],
    )
    app2 = SimpleNamespace(
        id=uuid4(),
        student_id=uuid4(),
        student=SimpleNamespace(full_name="Dilshod Karimov"),
        status=ApplicationStatus.REJECTED,
        total_score=87.5,
        submitted_at=now,
        created_at=now,
        evaluations=[],
    )
    app3 = SimpleNamespace(
        id=uuid4(),
        student_id=uuid4(),
        student=SimpleNamespace(full_name="Nozima Aliyeva"),
        status=ApplicationStatus.DRAFT,
        total_score=None,
        submitted_at=None,
        created_at=now,
        evaluations=[],
    )

    db = DummyDB(
        execute_results=[_ExecuteResult(rows=[app1, app2, app3])],
        get_map={("Scholarship", scholarship_id): scholarship},
    )

    result = await admin_api.get_scholarship_results(
        scholarship_id=scholarship_id,
        _=object(),
        db=db,
    )

    assert result.scholarship_id == scholarship_id
    assert result.winners_count == 1
    assert result.rows[0].rank == 1
    assert result.rows[0].is_winner is True
    assert result.rows[0].consistency is not None
    assert result.rows[0].consistency.is_flagged is True
    assert result.rows[0].consistency.score_spread == 15.0
    assert result.rows[1].rank == 2
    assert result.rows[2].rank is None


@pytest.mark.asyncio
async def test_export_scholarship_results_returns_xlsx_attachment(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    payload = admin_api.ScholarshipResultsOut(
        scholarship_id=scholarship_id,
        scholarship_title="Rektor stipendiyasi",
        scholarship_status=ScholarshipStatus.DONE,
        max_winners=2,
        winners_count=1,
        rows=[],
    )

    async def _fake_payload_builder(*args, **kwargs):
        return payload

    monkeypatch.setattr(admin_api, "_build_scholarship_results_payload", _fake_payload_builder)
    monkeypatch.setattr(admin_api, "build_scholarship_results_excel", lambda results: b"xlsx-content")

    response = await admin_api.export_scholarship_results(
        scholarship_id=scholarship_id,
        export_format="xlsx",
        _=object(),
        db=object(),
    )

    assert response.body == b"xlsx-content"
    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert 'attachment; filename="rektor-stipendiyasi-results-' in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_scholarship_results_returns_pdf_attachment(monkeypatch: pytest.MonkeyPatch):
    scholarship_id = uuid4()
    payload = admin_api.ScholarshipResultsOut(
        scholarship_id=scholarship_id,
        scholarship_title="Presidential Grant",
        scholarship_status=ScholarshipStatus.CLOSED,
        max_winners=1,
        winners_count=0,
        rows=[],
    )

    async def _fake_payload_builder(*args, **kwargs):
        return payload

    monkeypatch.setattr(admin_api, "_build_scholarship_results_payload", _fake_payload_builder)
    monkeypatch.setattr(admin_api, "build_scholarship_results_pdf", lambda results: b"%PDF-test")

    response = await admin_api.export_scholarship_results(
        scholarship_id=scholarship_id,
        export_format="pdf",
        _=object(),
        db=object(),
    )

    assert response.body == b"%PDF-test"
    assert response.media_type == "application/pdf"
    assert 'attachment; filename="presidential-grant-results-' in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_get_application_consistency_returns_summary_and_items():
    application_id = uuid4()
    scholarship_id = uuid4()
    student_id = uuid4()
    now = datetime.now(timezone.utc)
    application = SimpleNamespace(
        id=application_id,
        scholarship_id=scholarship_id,
        student_id=student_id,
        status=ApplicationStatus.IN_REVIEW,
        evaluations=[
            SimpleNamespace(
                id=uuid4(),
                jury_id=uuid4(),
                jury=SimpleNamespace(full_name="Jury One"),
                total_score=90.0,
                final_comment="Kuchli ish",
                is_submitted=True,
                submitted_at=now,
            ),
            SimpleNamespace(
                id=uuid4(),
                jury_id=uuid4(),
                jury=SimpleNamespace(full_name="Jury Two"),
                total_score=72.0,
                final_comment="Ba'zi kamchiliklar bor",
                is_submitted=True,
                submitted_at=now,
            ),
            SimpleNamespace(
                id=uuid4(),
                jury_id=uuid4(),
                jury=SimpleNamespace(full_name="Draft Jury"),
                total_score=None,
                final_comment=None,
                is_submitted=False,
                submitted_at=None,
            ),
        ],
    )
    db = DummyDB(execute_results=[_ExecuteResult(rows=[application])])

    result = await admin_api.get_application_consistency(
        application_id=application_id,
        _=object(),
        db=db,
    )

    assert result.application_id == application_id
    assert result.summary.jury_count == 2
    assert result.summary.average_score == 81.0
    assert result.summary.score_spread == 18.0
    assert result.summary.is_flagged is True
    assert len(result.evaluations) == 2
    assert result.evaluations[0].jury_name in {"Jury One", "Jury Two"}
