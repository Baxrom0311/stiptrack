from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.api.v1.applications as applications_api
import app.schemas.application as application_schema
import app.schemas.scholarship as scholarship_schema
import app.schemas.workflow as workflow_schema
import app.services.application_service as application_service
from app.models.enums import (
    AchievementType,
    AppealStatus,
    ApplicationStatus,
    ColumnFieldType,
    ScholarshipStageType,
    ScholarshipStatus,
    UserRole,
)
from app.schemas.application import ApplicationStatusUpdate, ApplicationValueUpdate
from app.schemas.workflow import AppealCreate, AppealDecision


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

    def scalar_one(self):
        if self._scalar is not None:
            return self._scalar
        if len(self._items) == 1:
            return self._items[0]
        raise AssertionError("Expected exactly one item")


class DummyDB:
    def __init__(self, execute_results=None, get_map=None) -> None:
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
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        return None

    async def refresh(self, obj) -> None:
        now = datetime.now(timezone.utc)
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        if obj.__class__.__name__ == "Application":
            if getattr(obj, "supervisor_id", None) is None:
                obj.supervisor_id = None
            if getattr(obj, "submitted_at", None) is None:
                obj.submitted_at = None
            if getattr(obj, "ai_summary", None) is None:
                obj.ai_summary = None
            if getattr(obj, "total_score", None) is None:
                obj.total_score = None
        if obj.__class__.__name__ == "Appeal":
            if getattr(obj, "resolved_at", None) is None:
                obj.resolved_at = None
            if getattr(obj, "resolved_by", None) is None:
                obj.resolved_by = None
            if getattr(obj, "response_text", None) is None:
                obj.response_text = None
            if getattr(obj, "score_after", None) is None:
                obj.score_after = None
        self.refresh_calls += 1

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


def _build_user(role: UserRole = UserRole.STUDENT, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "full_name": "Student User",
        "email": "student@example.com",
        "role": role,
        "department": "CS",
        "student_id": "S-100",
        "is_supervisor": False,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_column(max_score: int = 10, is_required: bool = True, ai_analyze: bool = False, **overrides: object):
    data = {
        "id": uuid4(),
        "scholarship_id": uuid4(),
        "name": "Motivatsiya",
        "description": "Motivatsiya xati",
        "field_type": ColumnFieldType.TEXTAREA,
        "select_options": None,
        "is_required": is_required,
        "ai_analyze": ai_analyze,
        "max_score": max_score,
        "input_min": None,
        "input_max": None,
        "order_index": 0,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_scholarship(
    status: ScholarshipStatus = ScholarshipStatus.OPEN,
    *,
    columns: list | None = None,
    ai_analysis_enabled: bool = False,
    blind_review_enabled: bool = False,
    max_winners: int = 2,
    **overrides: object,
) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "created_by": uuid4(),
        "title": "Rektor stipendiyasi",
        "description": "desc",
        "nizom_file_url": None,
        "status": status,
        "deadline": None,
        "ai_analysis_enabled": ai_analysis_enabled,
        "blind_review_enabled": blind_review_enabled,
        "max_winners": max_winners,
        "ai_provider": "claude",
        "ai_model": None,
        "created_at": now,
        "updated_at": now,
        "columns": columns or [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_value(column, **overrides: object) -> SimpleNamespace:
    data = {
        "id": uuid4(),
        "column_id": column.id,
        "value_text": "Old value",
        "value_file_url": None,
        "ai_analysis": None,
        "ai_score": None,
        "plagiarism_score": None,
        "plagiarism_matches": None,
        "plagiarism_checked_at": None,
        "column": column,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_application(
    status: ApplicationStatus,
    *,
    scholarship=None,
    student=None,
    supervisor=None,
    values=None,
    total_score: float | None = None,
    **overrides: object,
) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    scholarship_obj = scholarship or _build_scholarship()
    student_obj = student or _build_user()
    data = {
        "id": uuid4(),
        "scholarship_id": scholarship_obj.id,
        "student_id": student_obj.id,
        "supervisor_id": getattr(supervisor, "id", None),
        "status": status,
        "submitted_at": None,
        "ai_summary": None,
        "total_score": total_score,
        "created_at": now,
        "updated_at": now,
        "scholarship": scholarship_obj,
        "student": student_obj,
        "supervisor": supervisor,
        "values": values or [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_achievement(student_id, **overrides: object) -> SimpleNamespace:
    data = {
        "id": uuid4(),
        "student_id": student_id,
        "title": "Respublika olimpiadasi",
        "type": AchievementType.OLYMPIAD,
        "file_url": None,
        "date": date(2025, 5, 1),
        "description": "1-o'rin",
        "created_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_appeal(application_id, scholarship_id, student_id, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "scholarship_id": scholarship_id,
        "application_id": application_id,
        "student_id": student_id,
        "status": AppealStatus.SUBMITTED,
        "reason": "Qayta ko'rib chiqishni so'rayman",
        "response_text": None,
        "attachment_url": None,
        "filed_at": now,
        "resolved_at": None,
        "resolved_by": None,
        "score_before": 73.0,
        "score_after": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_status_log(application, **overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    actor = overrides.pop("changed_by_user", None)
    data = {
        "id": uuid4(),
        "application_id": application.id,
        "scholarship_id": application.scholarship_id,
        "previous_status": None,
        "new_status": application.status,
        "changed_by": getattr(actor, "id", None),
        "source": "system",
        "note": None,
        "created_at": now,
        "changed_by_user": actor,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_create_or_get_application_creates_draft_when_missing(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    scholarship = _build_scholarship(status=ScholarshipStatus.OPEN)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=None)], get_map={("Scholarship", scholarship.id): scholarship})
    ensure_stage = AsyncMock(return_value=None)
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)

    result = await applications_api.create_or_get_application(
        scholarship_id=scholarship.id,
        current_user=student,
        db=db,
    )

    assert len(db.added) == 2
    assert db.added[0].__class__.__name__ == "Application"
    assert db.added[1].__class__.__name__ == "ApplicationStatusLog"
    assert result.status == ApplicationStatus.DRAFT
    assert db.commits == 1
    assert db.refresh_calls == 1
    ensure_stage.assert_awaited_once_with(
        db=db,
        scholarship_id=scholarship.id,
        allowed_stage_types=(ScholarshipStageType.APPLICATION,),
    )


@pytest.mark.asyncio
async def test_get_my_application_for_scholarship_returns_existing_detail():
    student = _build_user()
    column = _build_column()
    scholarship = _build_scholarship(columns=[column])
    application = _build_application(
        ApplicationStatus.DRAFT,
        scholarship=scholarship,
        student=student,
        values=[_build_value(column, value_text="Men iqtidorli talabaman")],
    )
    db = DummyDB(
        execute_results=[_ExecuteResult(scalar=application)],
        get_map={("Scholarship", scholarship.id): scholarship},
    )

    result = await applications_api.get_my_application_for_scholarship(
        scholarship_id=scholarship.id,
        current_user=student,
        db=db,
    )

    assert result.id == application.id
    assert result.student_id == student.id
    assert len(result.values) == 1


@pytest.mark.asyncio
async def test_my_applications_returns_student_list():
    student = _build_user()
    scholarship = _build_scholarship()
    app_item = _build_application(ApplicationStatus.SUBMITTED, scholarship=scholarship, student=student)
    db = DummyDB(execute_results=[_ExecuteResult(items=[app_item])])

    result = await applications_api.my_applications(current_user=student, db=db)

    assert len(result) == 1
    assert result[0].scholarship.title == scholarship.title


@pytest.mark.asyncio
async def test_get_application_returns_detail_for_admin(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    column = _build_column(field_type=ColumnFieldType.FILE, name="Sertifikat")
    scholarship = _build_scholarship(columns=[column], nizom_file_url="nizom/rektor.pdf")
    application = _build_application(
        ApplicationStatus.SUBMITTED,
        scholarship=scholarship,
        student=student,
        values=[_build_value(column, value_text=None, value_file_url="application/certificate.pdf")],
    )

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(
        application_schema,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )
    monkeypatch.setattr(
        scholarship_schema,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await applications_api.get_application(
        application_id=application.id,
        current_user=_build_user(role=UserRole.ADMIN),
        db=object(),
    )

    assert result.id == application.id
    assert result.student.email == student.email
    assert result.scholarship.nizom_file_url == "https://signed.example/nizom/rektor.pdf"
    assert result.values[0].value_file_url == "https://signed.example/application/certificate.pdf"


@pytest.mark.asyncio
async def test_get_application_hides_participant_info_for_blind_review_jury(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    supervisor = _build_user(role=UserRole.JURY, is_supervisor=True, full_name="Supervisor User")
    value_column = _build_column()
    scholarship = _build_scholarship(blind_review_enabled=True)
    application = _build_application(
        ApplicationStatus.SUBMITTED,
        scholarship=scholarship,
        student=student,
        supervisor=supervisor,
        values=[
            _build_value(
                value_column,
                plagiarism_score=88.0,
                plagiarism_checked_at=datetime.now(timezone.utc),
                plagiarism_matches=[
                    {
                        "application_id": str(uuid4()),
                        "application_status": "submitted",
                        "similarity_percent": 88.0,
                        "matched_text_excerpt": "o'xshash matn",
                    }
                ],
            )
        ],
    )

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(applications_api, "_is_active_jury_assignment", AsyncMock(return_value=True))

    result = await applications_api.get_application(
        application_id=application.id,
        current_user=_build_user(role=UserRole.JURY, email="jury@example.com"),
        db=object(),
    )

    assert result.student is None
    assert result.supervisor is None
    assert result.scholarship.blind_review_enabled is True
    assert result.values[0].plagiarism_matches[0].application_id is None


@pytest.mark.asyncio
async def test_get_application_hides_plagiarism_details_for_student_owner(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    column = _build_column()
    application = _build_application(
        ApplicationStatus.DRAFT,
        student=student,
        values=[
            _build_value(
                column,
                plagiarism_score=74.0,
                plagiarism_checked_at=datetime.now(timezone.utc),
                plagiarism_matches=[
                    {
                        "application_id": str(uuid4()),
                        "application_status": "submitted",
                        "similarity_percent": 74.0,
                        "matched_text_excerpt": "o'xshash excerpt",
                    }
                ],
            )
        ],
    )

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    result = await applications_api.get_application(
        application_id=application.id,
        current_user=student,
        db=object(),
    )

    assert result.values[0].plagiarism_score is None
    assert result.values[0].plagiarism_matches is None
    assert result.values[0].plagiarism_checked_at is None


@pytest.mark.asyncio
async def test_get_application_denies_unrelated_student(monkeypatch: pytest.MonkeyPatch):
    owner = _build_user()
    outsider = _build_user(email="other-student@example.com")
    application = _build_application(ApplicationStatus.SUBMITTED, student=owner)

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.get_application(
            application_id=application.id,
            current_user=outsider,
            db=object(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Ruxsat yo'q"


@pytest.mark.asyncio
async def test_get_application_achievements_returns_student_portfolio(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    application = _build_application(ApplicationStatus.SUBMITTED, student=student)
    achievement = _build_achievement(student.id)
    db = DummyDB(execute_results=[_ExecuteResult(items=[achievement])])

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    result = await applications_api.get_application_achievements(
        application_id=application.id,
        current_user=_build_user(role=UserRole.ADMIN),
        db=db,
    )

    assert len(result) == 1
    assert result[0].title == achievement.title


@pytest.mark.asyncio
async def test_list_application_status_history_hides_actor_for_blind_review_jury(monkeypatch: pytest.MonkeyPatch):
    actor = _build_user(role=UserRole.JURY, email="actor@example.com")
    student = _build_user()
    scholarship = _build_scholarship(blind_review_enabled=True)
    application = _build_application(ApplicationStatus.IN_REVIEW, scholarship=scholarship, student=student)
    status_log = _build_status_log(application, changed_by_user=actor)
    db = DummyDB(execute_results=[_ExecuteResult(items=[status_log])])

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(applications_api, "_is_active_jury_assignment", AsyncMock(return_value=True))

    result = await applications_api.list_application_status_history(
        application_id=application.id,
        current_user=_build_user(role=UserRole.JURY, email="jury@example.com"),
        db=db,
    )

    assert len(result) == 1
    assert result[0].changed_by_user is None


@pytest.mark.asyncio
async def test_get_application_achievements_denies_unrelated_student(monkeypatch: pytest.MonkeyPatch):
    owner = _build_user()
    outsider = _build_user(email="outsider@example.com")
    application = _build_application(ApplicationStatus.SUBMITTED, student=owner)

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.get_application_achievements(
            application_id=application.id,
            current_user=outsider,
            db=object(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Ruxsat yo'q"


def test_transition_application_status_adds_log_entry():
    db = DummyDB()
    admin = _build_user(role=UserRole.ADMIN)
    application = _build_application(ApplicationStatus.SUBMITTED)

    status_log = application_service.transition_application_status(
        db=db,
        application=application,
        new_status=ApplicationStatus.IN_REVIEW,
        changed_by_user_id=admin.id,
        source="admin_manual",
        note="Admin tekshiruvni boshladi",
    )

    assert status_log is not None
    assert application.status == ApplicationStatus.IN_REVIEW
    assert len(db.added) == 1
    assert db.added[0].__class__.__name__ == "ApplicationStatusLog"
    assert db.added[0].previous_status == ApplicationStatus.SUBMITTED
    assert db.added[0].new_status == ApplicationStatus.IN_REVIEW
    assert db.added[0].changed_by == admin.id


@pytest.mark.asyncio
async def test_update_application_updates_supervisor_and_values(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    supervisor = _build_user(is_supervisor=True, role=UserRole.JURY, email="sup@example.com")
    col1 = _build_column(name="GPA", max_score=30)
    col2 = _build_column(name="Motivatsiya", max_score=40)
    scholarship = _build_scholarship(columns=[col1, col2])
    existing_value = _build_value(col1, value_text="3.8")
    application = _build_application(
        ApplicationStatus.DRAFT,
        scholarship=scholarship,
        student=student,
        values=[existing_value],
    )
    db = DummyDB(
        execute_results=[_ExecuteResult(scalar=application), _ExecuteResult(scalar=application)],
        get_map={("User", supervisor.id): supervisor},
    )
    ensure_stage = AsyncMock(return_value=None)
    plagiarism_check = AsyncMock(return_value=None)
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)
    monkeypatch.setattr(applications_api, "_check_application_plagiarism", plagiarism_check)

    result = await applications_api.update_application(
        application_id=application.id,
        payload=ApplicationValueUpdate(
            supervisor_id=supervisor.id,
            values={
                str(col1.id): "3.9",
                str(col2.id): "Motivatsiya xati matni",
            },
        ),
        current_user=student,
        db=db,
    )

    assert application.supervisor_id == supervisor.id
    assert existing_value.value_text == "3.9"
    assert len(db.added) == 1
    assert db.commits == 1
    assert plagiarism_check.await_args.kwargs["target_column_ids"] == {col1.id, col2.id}


@pytest.mark.asyncio
async def test_list_scholarship_applications_hides_student_for_blind_review_jury(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    scholarship = _build_scholarship(blind_review_enabled=True)
    application = _build_application(ApplicationStatus.SUBMITTED, scholarship=scholarship, student=student)
    db = DummyDB(execute_results=[_ExecuteResult(items=[application])])
    monkeypatch.setattr(applications_api, "_is_active_jury_assignment", AsyncMock(return_value=True))

    result = await applications_api.list_scholarship_applications(
        scholarship_id=scholarship.id,
        current_user=_build_user(role=UserRole.JURY, email="jury@example.com"),
        db=db,
        app_status=None,
        skip=0,
        limit=50,
    )

    assert len(result) == 1
    assert result[0].student is None
    assert result[0].scholarship.blind_review_enabled is True
    assert result[0].id == application.id


@pytest.mark.asyncio
async def test_list_application_status_history_returns_logs_for_admin(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    admin = _build_user(role=UserRole.ADMIN, email="admin@example.com")
    application = _build_application(ApplicationStatus.WINNER, student=student)
    status_log = _build_status_log(
        application,
        previous_status=ApplicationStatus.IN_REVIEW,
        new_status=ApplicationStatus.WINNER,
        source="winner_announcement",
        note="Yakuniy g'oliblar qayta hisoblandi",
        changed_by_user=admin,
    )
    db = DummyDB(execute_results=[_ExecuteResult(items=[status_log])])

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    result = await applications_api.list_application_status_history(
        application_id=application.id,
        current_user=admin,
        db=db,
    )

    assert len(result) == 1
    assert result[0].new_status == ApplicationStatus.WINNER
    assert result[0].changed_by_user.full_name == admin.full_name


@pytest.mark.asyncio
async def test_list_application_status_history_denies_unrelated_student(monkeypatch: pytest.MonkeyPatch):
    owner = _build_user()
    outsider = _build_user(email="history-outsider@example.com")
    application = _build_application(ApplicationStatus.SUBMITTED, student=owner)

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.list_application_status_history(
            application_id=application.id,
            current_user=outsider,
            db=object(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Ruxsat yo'q"


@pytest.mark.asyncio
async def test_update_application_rejects_number_value_below_min(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    number_column = _build_column(
        name="GPA",
        field_type=ColumnFieldType.NUMBER,
        input_min=3,
        input_max=5,
    )
    scholarship = _build_scholarship(columns=[number_column])
    application = _build_application(
        ApplicationStatus.DRAFT,
        scholarship=scholarship,
        student=student,
        values=[],
    )
    db = DummyDB(execute_results=[_ExecuteResult(scalar=application)])
    ensure_stage = AsyncMock(return_value=None)
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.update_application(
            application_id=application.id,
            payload=ApplicationValueUpdate(values={str(number_column.id): "2.5"}),
            current_user=student,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "3 dan kichik" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_value_file_creates_new_file_value(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    column = _build_column(field_type=ColumnFieldType.FILE)
    scholarship = _build_scholarship(columns=[column])
    application = _build_application(ApplicationStatus.DRAFT, scholarship=scholarship, student=student, values=[])
    db = DummyDB(execute_results=[_ExecuteResult(scalar=application), _ExecuteResult(scalar=application)])
    ensure_stage = AsyncMock(return_value=None)
    upload_file = AsyncMock(return_value="application/test.pdf")
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)
    monkeypatch.setattr(applications_api, "upload_file", upload_file)
    monkeypatch.setattr(
        applications_api,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await applications_api.upload_value_file(
        application_id=application.id,
        column_id=column.id,
        current_user=student,
        db=db,
        file=SimpleNamespace(filename="test.pdf"),
    )

    assert result["file_url"] == "https://signed.example/application/test.pdf"
    assert len(db.added) == 1
    assert db.added[0].value_file_url == "application/test.pdf"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_update_application_clears_file_value_when_null_sent(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    file_column = _build_column(field_type=ColumnFieldType.FILE, name="Sertifikat")
    scholarship = _build_scholarship(columns=[file_column])
    existing_value = _build_value(file_column, value_text=None, value_file_url="https://files.example.com/old.pdf")
    application = _build_application(
        ApplicationStatus.DRAFT,
        scholarship=scholarship,
        student=student,
        values=[existing_value],
    )
    db = DummyDB(execute_results=[_ExecuteResult(scalar=application), _ExecuteResult(scalar=application)])
    ensure_stage = AsyncMock(return_value=None)
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)

    result = await applications_api.update_application(
        application_id=application.id,
        payload=ApplicationValueUpdate(values={str(file_column.id): None}),
        current_user=student,
        db=db,
    )

    assert existing_value.value_file_url is None
    assert db.commits == 1
    assert result.id == application.id


@pytest.mark.asyncio
async def test_submit_application_marks_submitted_when_required_fields_present(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    required_column = _build_column(is_required=True, ai_analyze=False)
    scholarship = _build_scholarship(
        status=ScholarshipStatus.OPEN,
        columns=[required_column],
        ai_analysis_enabled=False,
    )
    application = _build_application(
        ApplicationStatus.DRAFT,
        scholarship=scholarship,
        student=student,
        values=[_build_value(required_column, value_text="To'liq javob")],
    )
    db = DummyDB(execute_results=[_ExecuteResult(scalar=application)])
    ensure_stage = AsyncMock(return_value=None)
    plagiarism_check = AsyncMock(return_value=None)
    queued_status_log_ids: list[list] = []
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)
    monkeypatch.setattr(applications_api, "_check_application_plagiarism", plagiarism_check)
    monkeypatch.setattr(
        applications_api,
        "queue_application_status_email_tasks",
        lambda status_log_ids: queued_status_log_ids.append(list(status_log_ids)),
    )

    result = await applications_api.submit_application(
        application_id=application.id,
        current_user=student,
        db=db,
    )

    assert application.status == ApplicationStatus.SUBMITTED
    assert application.submitted_at is not None
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert result.status == ApplicationStatus.SUBMITTED
    assert queued_status_log_ids and len(queued_status_log_ids[0]) == 1
    assert plagiarism_check.await_args.kwargs["target_column_ids"] == {required_column.id}


@pytest.mark.asyncio
async def test_submit_application_rejects_number_value_above_max(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    number_column = _build_column(
        name="GPA",
        field_type=ColumnFieldType.NUMBER,
        input_min=0,
        input_max=4,
        is_required=True,
    )
    scholarship = _build_scholarship(
        status=ScholarshipStatus.OPEN,
        columns=[number_column],
        ai_analysis_enabled=False,
    )
    application = _build_application(
        ApplicationStatus.DRAFT,
        scholarship=scholarship,
        student=student,
        values=[_build_value(number_column, value_text="4.5")],
    )
    db = DummyDB(execute_results=[_ExecuteResult(scalar=application)])
    ensure_stage = AsyncMock(return_value=None)
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.submit_application(
            application_id=application.id,
            current_user=student,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "4 dan katta" in exc_info.value.detail


@pytest.mark.asyncio
async def test_list_scholarship_applications_returns_ranked_rows_for_admin():
    student = _build_user()
    scholarship = _build_scholarship()
    application = _build_application(
        ApplicationStatus.IN_REVIEW,
        scholarship=scholarship,
        student=student,
        total_score=88.5,
    )
    db = DummyDB(execute_results=[_ExecuteResult(items=[application])])

    result = await applications_api.list_scholarship_applications(
        scholarship_id=scholarship.id,
        current_user=_build_user(role=UserRole.ADMIN),
        db=db,
        app_status=None,
        skip=0,
        limit=50,
    )

    assert len(result) == 1
    assert result[0].student.full_name == student.full_name


@pytest.mark.asyncio
async def test_update_application_status_sets_submitted_at(monkeypatch: pytest.MonkeyPatch):
    application = _build_application(ApplicationStatus.DRAFT)
    db = DummyDB()
    queued_status_log_ids: list[list] = []

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(
        applications_api,
        "queue_application_status_email_tasks",
        lambda status_log_ids: queued_status_log_ids.append(list(status_log_ids)),
    )

    result = await applications_api.update_application_status(
        application_id=application.id,
        payload=ApplicationStatusUpdate(status=ApplicationStatus.SUBMITTED),
        _=object(),
        db=db,
    )

    assert application.status == ApplicationStatus.SUBMITTED
    assert application.submitted_at is not None
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert result.status == ApplicationStatus.SUBMITTED
    assert len(queued_status_log_ids) == 1
    assert len(queued_status_log_ids[0]) == 1


@pytest.mark.asyncio
async def test_announce_winners_marks_scholarship_done(monkeypatch: pytest.MonkeyPatch):
    scholarship = _build_scholarship(status=ScholarshipStatus.CLOSED)
    db = DummyDB(get_map={("Scholarship", scholarship.id): scholarship})
    ensure_stage = AsyncMock(return_value=None)
    queued_status_log_ids: list[list] = []

    async def _fake_recalculate(*args, **kwargs):
        kwargs["status_log_ids_out"].extend([uuid4(), uuid4()])
        return ["app-1", "app-2"]

    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)
    monkeypatch.setattr(applications_api, "_recalculate_winners_for_scholarship", _fake_recalculate)
    monkeypatch.setattr(
        applications_api,
        "queue_application_status_email_tasks",
        lambda status_log_ids: queued_status_log_ids.append(list(status_log_ids)),
    )

    result = await applications_api.announce_winners(
        scholarship_id=scholarship.id,
        _=object(),
        db=db,
    )

    assert scholarship.status == ScholarshipStatus.DONE
    assert result.winner_ids == ["app-1", "app-2"]
    assert db.commits == 1
    assert queued_status_log_ids and len(queued_status_log_ids[0]) == 2


@pytest.mark.asyncio
async def test_create_appeal_creates_new_record(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    scholarship = _build_scholarship(status=ScholarshipStatus.DONE)
    application = _build_application(
        ApplicationStatus.REJECTED,
        scholarship=scholarship,
        student=student,
        total_score=73.0,
    )
    db = DummyDB(
        execute_results=[_ExecuteResult(scalar=None)],
        get_map={("Scholarship", scholarship.id): scholarship},
    )
    ensure_stage = AsyncMock(return_value=None)

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)

    result = await applications_api.create_appeal(
        application_id=application.id,
        payload=AppealCreate(
            reason="Baholash natijasini qayta ko'rib chiqing",
            attachment_url="https://localhost:9000/stipendiya-files/appeal/test.pdf?X-Amz-Signature=abc",
        ),
        current_user=student,
        db=db,
    )

    assert len(db.added) == 1
    assert result.application_id == application.id
    assert result.score_before == 73.0
    assert db.added[0].attachment_url == "appeal/test.pdf"
    assert db.commits == 1
    assert db.refresh_calls == 1


@pytest.mark.asyncio
async def test_create_appeal_denies_non_owner_student(monkeypatch: pytest.MonkeyPatch):
    owner = _build_user()
    outsider = _build_user(email="appeal-outsider@example.com")
    scholarship = _build_scholarship(status=ScholarshipStatus.DONE)
    application = _build_application(
        ApplicationStatus.REJECTED,
        scholarship=scholarship,
        student=owner,
        total_score=64.0,
    )

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.create_appeal(
            application_id=application.id,
            payload=AppealCreate(reason="Baholashni qayta tekshiring iltimos"),
            current_user=outsider,
            db=object(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Ruxsat yo'q"


@pytest.mark.asyncio
async def test_upload_appeal_file_returns_uploaded_url(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    scholarship = _build_scholarship(status=ScholarshipStatus.DONE)
    application = _build_application(ApplicationStatus.REJECTED, scholarship=scholarship, student=student)
    db = DummyDB(get_map={("Scholarship", scholarship.id): scholarship})
    ensure_stage = AsyncMock(return_value=None)
    upload_file = AsyncMock(return_value="appeal/test.pdf")

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(applications_api, "_ensure_stage_allows", ensure_stage)
    monkeypatch.setattr(applications_api, "upload_file", upload_file)
    monkeypatch.setattr(
        applications_api,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await applications_api.upload_appeal_file(
        application_id=application.id,
        current_user=student,
        db=db,
        file=SimpleNamespace(filename="appeal.pdf"),
    )

    assert result["file_url"] == "https://signed.example/appeal/test.pdf"


@pytest.mark.asyncio
async def test_upload_appeal_file_denies_non_owner_student(monkeypatch: pytest.MonkeyPatch):
    owner = _build_user()
    outsider = _build_user(email="appeal-file-outsider@example.com")
    scholarship = _build_scholarship(status=ScholarshipStatus.DONE)
    application = _build_application(ApplicationStatus.REJECTED, scholarship=scholarship, student=owner)

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.upload_appeal_file(
            application_id=application.id,
            current_user=outsider,
            db=object(),
            file=SimpleNamespace(filename="appeal.pdf"),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Ruxsat yo'q"


@pytest.mark.asyncio
async def test_list_application_appeals_returns_entries_for_admin(monkeypatch: pytest.MonkeyPatch):
    student = _build_user()
    scholarship = _build_scholarship(status=ScholarshipStatus.DONE)
    application = _build_application(ApplicationStatus.REJECTED, scholarship=scholarship, student=student)
    appeal = _build_appeal(application.id, scholarship.id, student.id, attachment_url="appeal/test.pdf")
    db = DummyDB(execute_results=[_ExecuteResult(items=[appeal])])

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)
    monkeypatch.setattr(
        workflow_schema,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await applications_api.list_application_appeals(
        application_id=application.id,
        current_user=_build_user(role=UserRole.ADMIN),
        db=db,
    )

    assert len(result) == 1
    assert result[0].application_id == application.id
    assert result[0].attachment_url == "https://signed.example/appeal/test.pdf"


@pytest.mark.asyncio
async def test_list_application_appeals_denies_unrelated_student(monkeypatch: pytest.MonkeyPatch):
    owner = _build_user()
    outsider = _build_user(email="appeals-outsider@example.com")
    scholarship = _build_scholarship(status=ScholarshipStatus.DONE)
    application = _build_application(ApplicationStatus.REJECTED, scholarship=scholarship, student=owner)

    async def _fake_get_application(*args, **kwargs):
        return application

    monkeypatch.setattr(applications_api, "_get_application_or_404", _fake_get_application)

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.list_application_appeals(
            application_id=application.id,
            current_user=outsider,
            db=object(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Ruxsat yo'q"


@pytest.mark.asyncio
async def test_list_appeals_returns_admin_filtered_list():
    student = _build_user()
    scholarship = _build_scholarship(status=ScholarshipStatus.DONE)
    appeal = _build_appeal(uuid4(), scholarship.id, student.id)
    db = DummyDB(execute_results=[_ExecuteResult(items=[appeal])])

    result = await applications_api.list_appeals(
        _=object(),
        db=db,
        scholarship_id=scholarship.id,
        appeal_status=AppealStatus.SUBMITTED,
        skip=0,
        limit=50,
    )

    assert len(result) == 1
    assert result[0].scholarship_id == scholarship.id


@pytest.mark.asyncio
async def test_recalculate_winners_marks_top_n():
    scholarship = SimpleNamespace(id=uuid4(), max_winners=2)

    app1 = _build_application(ApplicationStatus.SUBMITTED, total_score=91.5)
    app2 = _build_application(ApplicationStatus.IN_REVIEW, total_score=88.0)
    app3 = _build_application(ApplicationStatus.WINNER, total_score=77.0)
    app4 = _build_application(ApplicationStatus.DRAFT, total_score=None)

    db = DummyDB(
        execute_results=[
            _ExecuteResult(items=[app1, app2]),
            _ExecuteResult(items=[app1, app2, app3, app4]),
        ]
    )

    winner_ids = await applications_api._recalculate_winners_for_scholarship(db=db, scholarship=scholarship)

    assert winner_ids == [str(app1.id), str(app2.id)]
    assert app1.status == ApplicationStatus.WINNER
    assert app2.status == ApplicationStatus.WINNER
    assert app3.status == ApplicationStatus.REJECTED
    assert app4.status == ApplicationStatus.DRAFT


@pytest.mark.asyncio
async def test_decide_appeal_requires_score_after_when_accepted():
    appeal_id = uuid4()
    appeal = SimpleNamespace(
        id=appeal_id,
        application_id=uuid4(),
        status=AppealStatus.SUBMITTED,
    )
    db = DummyDB(get_map={("Appeal", appeal_id): appeal})

    with pytest.raises(HTTPException) as exc_info:
        await applications_api.decide_appeal(
            appeal_id=appeal_id,
            payload=AppealDecision(status=AppealStatus.ACCEPTED, response_text="Qayta ko'rildi"),
            current_user=SimpleNamespace(id=uuid4()),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "score_after" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_decide_appeal_updates_score_and_recalculates_winners(monkeypatch: pytest.MonkeyPatch):
    now = datetime.now(timezone.utc)
    appeal_id = uuid4()
    application_id = uuid4()
    scholarship_id = uuid4()

    appeal = SimpleNamespace(
        id=appeal_id,
        scholarship_id=scholarship_id,
        application_id=application_id,
        student_id=uuid4(),
        status=AppealStatus.SUBMITTED,
        reason="Baholash noto'g'ri hisoblangan",
        response_text=None,
        attachment_url=None,
        filed_at=now,
        resolved_at=None,
        resolved_by=None,
        score_before=73.0,
        score_after=None,
        created_at=now,
        updated_at=now,
    )
    application = SimpleNamespace(id=application_id, scholarship_id=scholarship_id, total_score=73.0)
    scholarship = SimpleNamespace(id=scholarship_id, status=ScholarshipStatus.DONE)

    db = DummyDB(
        get_map={
            ("Appeal", appeal_id): appeal,
            ("Application", application_id): application,
            ("Scholarship", scholarship_id): scholarship,
        }
    )

    queued_status_log_ids: list[list] = []

    async def _fake_recalculate(*args, **kwargs):
        kwargs["status_log_ids_out"].append(uuid4())
        return [str(application_id)]

    monkeypatch.setattr(applications_api, "_recalculate_winners_for_scholarship", _fake_recalculate)
    monkeypatch.setattr(
        applications_api,
        "queue_application_status_email_tasks",
        lambda status_log_ids: queued_status_log_ids.append(list(status_log_ids)),
    )

    admin_user = SimpleNamespace(id=uuid4())
    result = await applications_api.decide_appeal(
        appeal_id=appeal_id,
        payload=AppealDecision(
            status=AppealStatus.ACCEPTED,
            response_text="Qayta tekshiruv yakunlandi",
            score_after=88.5,
        ),
        current_user=admin_user,
        db=db,
    )

    assert result.status == AppealStatus.ACCEPTED
    assert result.score_after == 88.5
    assert application.total_score == 88.5
    assert appeal.resolved_by == admin_user.id
    assert appeal.resolved_at is not None
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert queued_status_log_ids and len(queued_status_log_ids[0]) == 1
