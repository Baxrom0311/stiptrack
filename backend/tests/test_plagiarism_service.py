from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.enums import ApplicationStatus, ColumnFieldType
import app.services.plagiarism_service as plagiarism_service


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class DummyDB:
    def __init__(self, execute_results=None):
        self._execute_results = list(execute_results or [])
        self.flush_calls = 0

    async def flush(self):
        self.flush_calls += 1

    async def execute(self, _stmt):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call")
        return self._execute_results.pop(0)


def _build_value(application_id, column_id, text: str | None):
    return SimpleNamespace(
        id=uuid4(),
        application_id=application_id,
        column_id=column_id,
        value_text=text,
        plagiarism_score=None,
        plagiarism_matches=None,
        plagiarism_checked_at=None,
    )


@pytest.mark.asyncio
async def test_refresh_plagiarism_for_column_sets_score_and_matches_for_similar_texts():
    scholarship_id = uuid4()
    column_id = uuid4()
    column = SimpleNamespace(id=column_id, field_type=ColumnFieldType.TEXTAREA)

    application_a = uuid4()
    application_b = uuid4()
    application_c = uuid4()
    value_a = _build_value(
        application_a,
        column_id,
        "Men ushbu stipendiyaga ilmiy loyihamni davom ettirish uchun ariza topshiryapman.",
    )
    value_b = _build_value(
        application_b,
        column_id,
        "Men ushbu stipendiyaga ilmiy loyihamni davom ettirish uchun ariza topshiryapman va katta natija kutyapman.",
    )
    value_c = _build_value(application_c, column_id, "Bu boshqa mazmundagi mustaqil motivatsiya matni.")

    db = DummyDB(
        execute_results=[
            _ExecuteResult(
                rows=[
                    (value_a, ApplicationStatus.SUBMITTED),
                    (value_b, ApplicationStatus.SUBMITTED),
                    (value_c, ApplicationStatus.DRAFT),
                ]
            )
        ]
    )

    await plagiarism_service.refresh_plagiarism_for_column(
        db=db,
        scholarship_id=scholarship_id,
        column=column,
    )

    assert db.flush_calls == 1
    assert value_a.plagiarism_score is not None and value_a.plagiarism_score >= 70
    assert value_b.plagiarism_score is not None and value_b.plagiarism_score >= 70
    assert value_a.plagiarism_matches and value_a.plagiarism_matches[0]["application_id"] == str(application_b)
    assert value_a.plagiarism_matches[0]["application_status"] == ApplicationStatus.SUBMITTED.value
    assert value_c.plagiarism_score is not None and value_c.plagiarism_score < 70
    assert value_c.plagiarism_matches == []
    assert value_a.plagiarism_checked_at is not None


@pytest.mark.asyncio
async def test_refresh_plagiarism_for_column_clears_empty_values():
    column_id = uuid4()
    column = SimpleNamespace(id=column_id, field_type=ColumnFieldType.TEXT)
    value = _build_value(uuid4(), column_id, None)
    value.plagiarism_score = 82.0
    value.plagiarism_matches = [{"application_id": str(uuid4())}]
    value.plagiarism_checked_at = datetime.now(timezone.utc)

    db = DummyDB(execute_results=[_ExecuteResult(rows=[(value, ApplicationStatus.SUBMITTED)])])

    await plagiarism_service.refresh_plagiarism_for_column(
        db=db,
        scholarship_id=uuid4(),
        column=column,
    )

    assert value.plagiarism_score is None
    assert value.plagiarism_matches is None
    assert value.plagiarism_checked_at is None
