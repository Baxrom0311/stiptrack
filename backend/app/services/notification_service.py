from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Iterable

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import SecretStr

from app.core.config import settings
from app.models.application import Application, ApplicationStatusLog
from app.models.enums import ApplicationStatus


logger = logging.getLogger(__name__)


APPLICATION_STATUS_LABELS = {
    ApplicationStatus.DRAFT: "Qoralama",
    ApplicationStatus.SUBMITTED: "Topshirildi",
    ApplicationStatus.IN_REVIEW: "Ko'rib chiqilmoqda",
    ApplicationStatus.WINNER: "G'olib",
    ApplicationStatus.REJECTED: "Rad etildi",
}


def is_email_notifications_enabled() -> bool:
    return settings.email_enabled


def should_send_application_status_email(status_log: ApplicationStatusLog) -> bool:
    if not is_email_notifications_enabled():
        return False
    return not (status_log.previous_status is None and status_log.new_status == ApplicationStatus.DRAFT)


def _get_status_label(status: ApplicationStatus | None) -> str:
    if status is None:
        return "Mavjud emas"
    return APPLICATION_STATUS_LABELS.get(status, status.value)


def _build_application_url(application_id: uuid.UUID) -> str | None:
    if not settings.frontend_base_url:
        return None
    return f"{settings.frontend_base_url.rstrip('/')}/student/applications/{application_id}/result"


def _format_score(total_score: Decimal | float | int | None) -> str | None:
    if total_score is None:
        return None
    return f"{float(total_score):.2f}"


def build_application_status_email_payload(
    application: Application,
    status_log: ApplicationStatusLog,
) -> dict[str, str | list[str] | None] | None:
    if not should_send_application_status_email(status_log):
        return None

    student = application.student
    scholarship = application.scholarship
    if student is None or scholarship is None or not student.email:
        return None

    scholarship_title = scholarship.title
    status_label = _get_status_label(status_log.new_status)
    previous_label = _get_status_label(status_log.previous_status)

    if status_log.new_status == ApplicationStatus.WINNER:
        subject = f"Tabriklaymiz, siz g'olib bo'ldingiz: {scholarship_title}"
    elif status_log.new_status == ApplicationStatus.REJECTED:
        subject = f"Ariza natijasi yangilandi: {scholarship_title}"
    elif status_log.new_status == ApplicationStatus.IN_REVIEW:
        subject = f"Arizangiz ko'rib chiqilmoqda: {scholarship_title}"
    elif status_log.new_status == ApplicationStatus.SUBMITTED:
        subject = f"Arizangiz qabul qilindi: {scholarship_title}"
    else:
        subject = f"Ariza holati yangilandi: {scholarship_title}"

    lines = [
        f"Salom, {student.full_name}.",
        "",
        f"\"{scholarship_title}\" stipendiyasi bo'yicha arizangiz holati yangilandi.",
        f"Oldingi holat: {previous_label}",
        f"Yangi holat: {status_label}",
    ]

    score_text = _format_score(application.total_score)
    if score_text is not None:
        lines.append(f"Joriy o'rtacha ball: {score_text}")

    if status_log.note:
        lines.extend(["", f"Izoh: {status_log.note}"])

    application_url = _build_application_url(application.id)
    if application_url:
        lines.extend(["", f"Natijani ko'rish: {application_url}"])

    lines.extend(["", "Hurmat bilan,", settings.mail_from_name or settings.app_name])

    return {
        "recipients": [student.email],
        "subject": subject,
        "body": "\n".join(lines),
    }


def get_mail_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=SecretStr(settings.mail_password),
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        MAIL_FROM=settings.mail_from,
        MAIL_FROM_NAME=settings.mail_from_name,
        USE_CREDENTIALS=settings.mail_use_credentials,
        VALIDATE_CERTS=settings.mail_validate_certs,
    )


async def send_message(payload: dict[str, str | list[str] | None]) -> None:
    message = MessageSchema(
        recipients=list(payload["recipients"] or []),
        subject=str(payload["subject"] or ""),
        body=str(payload["body"] or ""),
        subtype=MessageType.plain,
    )
    await FastMail(get_mail_config()).send_message(message)


def queue_application_status_email_tasks(status_log_ids: Iterable[uuid.UUID]) -> int:
    if not is_email_notifications_enabled():
        return 0

    queued = 0
    try:
        from workers.tasks import send_application_status_email

        for status_log_id in status_log_ids:
            send_application_status_email.delay(str(status_log_id))
            queued += 1
    except Exception:
        logger.exception("Email notification taskini navbatga qo'shib bo'lmadi")
        return queued

    return queued
