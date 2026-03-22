from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationValue
from app.models.enums import ColumnFieldType
from app.models.scholarship import ScholarshipColumn

TEXTUAL_FIELD_TYPES = {
    ColumnFieldType.TEXT,
    ColumnFieldType.TEXTAREA,
    ColumnFieldType.URL,
}
PLAGIARISM_MATCH_THRESHOLD_PERCENT = 70.0
PLAGIARISM_TOP_MATCH_LIMIT = 3


@dataclass
class _ValueEntry:
    value: ApplicationValue
    application_status: str
    normalized_text: str


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _extract_words(value: str) -> set[str]:
    return set(re.findall(r"\w+", value, flags=re.UNICODE))


def calculate_text_similarity_percent(source_text: str | None, candidate_text: str | None) -> float:
    source = _normalize_text(source_text)
    candidate = _normalize_text(candidate_text)
    if not source or not candidate:
        return 0.0
    if source == candidate:
        return 100.0

    sequence_ratio = SequenceMatcher(None, source, candidate).ratio()
    source_words = _extract_words(source)
    candidate_words = _extract_words(candidate)
    if source_words and candidate_words:
        overlap_ratio = len(source_words & candidate_words) / max(1, min(len(source_words), len(candidate_words)))
    else:
        overlap_ratio = 0.0

    weighted = max(sequence_ratio, (sequence_ratio * 0.65) + (overlap_ratio * 0.35), overlap_ratio * 0.92)
    return round(min(weighted * 100, 100.0), 2)


def _build_excerpt(text: str | None, limit: int = 180) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _reset_plagiarism_fields(value: ApplicationValue) -> None:
    value.plagiarism_score = None
    value.plagiarism_matches = None
    value.plagiarism_checked_at = None


async def refresh_plagiarism_for_column(
    db: AsyncSession,
    *,
    scholarship_id: uuid.UUID,
    column: ScholarshipColumn,
) -> None:
    if column.field_type not in TEXTUAL_FIELD_TYPES:
        return

    await db.flush()
    result = await db.execute(
        select(ApplicationValue, Application.status)
        .join(Application, Application.id == ApplicationValue.application_id)
        .where(
            Application.scholarship_id == scholarship_id,
            ApplicationValue.column_id == column.id,
        )
    )
    rows = result.all()
    checked_at = datetime.now(timezone.utc)

    entries: list[_ValueEntry] = []
    for value, application_status in rows:
        normalized = _normalize_text(value.value_text)
        entries.append(
            _ValueEntry(
                value=value,
                application_status=getattr(application_status, "value", str(application_status)),
                normalized_text=normalized,
            )
        )

    for entry in entries:
        if not entry.normalized_text:
            _reset_plagiarism_fields(entry.value)
            continue

        top_score = 0.0
        matches: list[dict] = []
        for candidate in entries:
            if candidate.value.application_id == entry.value.application_id:
                continue
            if not candidate.normalized_text:
                continue

            similarity_percent = calculate_text_similarity_percent(
                entry.normalized_text,
                candidate.normalized_text,
            )
            top_score = max(top_score, similarity_percent)
            if similarity_percent < PLAGIARISM_MATCH_THRESHOLD_PERCENT:
                continue

            matches.append(
                {
                    "application_id": str(candidate.value.application_id),
                    "application_status": candidate.application_status,
                    "similarity_percent": similarity_percent,
                    "matched_text_excerpt": _build_excerpt(candidate.value.value_text),
                }
            )

        matches.sort(key=lambda item: item["similarity_percent"], reverse=True)
        entry.value.plagiarism_score = round(top_score, 2)
        entry.value.plagiarism_matches = matches[:PLAGIARISM_TOP_MATCH_LIMIT]
        entry.value.plagiarism_checked_at = checked_at


async def refresh_application_plagiarism_checks(
    db: AsyncSession,
    *,
    application: Application,
    columns_by_id: dict[uuid.UUID, ScholarshipColumn] | None = None,
    target_column_ids: set[uuid.UUID] | None = None,
) -> None:
    effective_columns = columns_by_id or {
        column.id: column
        for column in getattr(getattr(application, "scholarship", None), "columns", []) or []
    }

    for column_id, column in effective_columns.items():
        if target_column_ids is not None and column_id not in target_column_ids:
            continue
        await refresh_plagiarism_for_column(
            db,
            scholarship_id=application.scholarship_id,
            column=column,
        )
