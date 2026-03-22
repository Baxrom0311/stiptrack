from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from openpyxl import load_workbook

from app.models.enums import ApplicationStatus, ScholarshipStatus
from app.schemas.admin import ScholarshipResultRow, ScholarshipResultsOut
from app.services.export_service import (
    build_scholarship_results_excel,
    build_scholarship_results_pdf,
    slugify_filename,
)


def _build_results() -> ScholarshipResultsOut:
    now = datetime.now(timezone.utc)
    return ScholarshipResultsOut(
        scholarship_id=uuid4(),
        scholarship_title="Rektor stipendiyasi 2026",
        scholarship_status=ScholarshipStatus.DONE,
        max_winners=2,
        winners_count=1,
        rows=[
            ScholarshipResultRow(
                rank=1,
                application_id=uuid4(),
                student_id=uuid4(),
                student_name="Ali Valiyev",
                status=ApplicationStatus.WINNER,
                total_score=95.5,
                is_winner=True,
                submitted_at=now,
            ),
            ScholarshipResultRow(
                rank=2,
                application_id=uuid4(),
                student_id=uuid4(),
                student_name="Dilshod Karimov",
                status=ApplicationStatus.REJECTED,
                total_score=87.25,
                is_winner=False,
                submitted_at=now,
            ),
        ],
    )


def test_slugify_filename_normalizes_title():
    assert slugify_filename("Rektor stipendiyasi 2026!") == "rektor-stipendiyasi-2026"


def test_build_scholarship_results_excel_contains_summary_and_rows():
    content = build_scholarship_results_excel(_build_results())

    workbook = load_workbook(BytesIO(content))
    sheet = workbook.active

    assert sheet["A1"].value == "Scholarship"
    assert sheet["B1"].value == "Rektor stipendiyasi 2026"
    assert sheet["A6"].value == "Rank"
    assert sheet["B7"].value == "Ali Valiyev"
    assert sheet["F7"].value == "95.50"


def test_build_scholarship_results_pdf_returns_pdf_bytes():
    content = build_scholarship_results_pdf(_build_results())

    assert content.startswith(b"%PDF")
    assert b"%%EOF" in content
    assert len(content) > 1000
