from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.enums import ApplicationStatus
import app.services.notification_service as notification_service


def _build_application(*, total_score: Decimal | None = None):
    now = datetime.now(timezone.utc)
    student = SimpleNamespace(
        id=uuid4(),
        full_name="Ali Valiyev",
        email="ali@example.com",
        created_at=now,
        updated_at=now,
    )
    scholarship = SimpleNamespace(
        id=uuid4(),
        title="Rektor stipendiyasi",
        created_at=now,
        updated_at=now,
    )
    return SimpleNamespace(
        id=uuid4(),
        student=student,
        scholarship=scholarship,
        total_score=total_score,
    )


def _build_status_log(
    *,
    previous_status: ApplicationStatus | None,
    new_status: ApplicationStatus,
    note: str | None = None,
):
    return SimpleNamespace(
        id=uuid4(),
        previous_status=previous_status,
        new_status=new_status,
        note=note,
    )


def test_build_application_status_email_payload_skips_initial_draft(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    application = _build_application()
    status_log = _build_status_log(
        previous_status=None,
        new_status=ApplicationStatus.DRAFT,
        note="Ariza qoralama holatida yaratildi",
    )

    payload = notification_service.build_application_status_email_payload(application, status_log)

    assert payload is None


def test_build_application_status_email_payload_builds_winner_message(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "frontend_base_url", "http://localhost:3000")
    monkeypatch.setattr(settings, "mail_from_name", "StipTrack")
    application = _build_application(total_score=Decimal("91.5"))
    status_log = _build_status_log(
        previous_status=ApplicationStatus.IN_REVIEW,
        new_status=ApplicationStatus.WINNER,
        note="Yakuniy g'oliblar qayta hisoblandi",
    )

    payload = notification_service.build_application_status_email_payload(application, status_log)

    assert payload is not None
    assert payload["subject"] == "Tabriklaymiz, siz g'olib bo'ldingiz: Rektor stipendiyasi"
    assert "Oldingi holat: Ko'rib chiqilmoqda" in payload["body"]
    assert "Yangi holat: G'olib" in payload["body"]
    assert "Joriy o'rtacha ball: 91.50" in payload["body"]
    assert "Natijani ko'rish: http://localhost:3000/student/applications/" in payload["body"]


def test_queue_application_status_email_tasks_dispatches_delay(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    delayed_calls: list[str] = []

    class _Task:
        @staticmethod
        def delay(status_log_id: str):
            delayed_calls.append(status_log_id)

    import workers.tasks as worker_tasks

    monkeypatch.setattr(worker_tasks, "send_application_status_email", _Task)

    log_id = uuid4()
    queued = notification_service.queue_application_status_email_tasks([log_id])

    assert queued == 1
    assert delayed_calls == [str(log_id)]
