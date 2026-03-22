from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_parse_nizom_returns_structure():
    mock_result = {
        "title": "Test Stipendiyasi",
        "purpose": "Iqtidorli talabalarni qo'llab-quvvatlash",
        "requirements": ["GPA 3.5 dan yuqori", "3-kurs talabasi"],
        "evaluation_criteria": ["Akademik ko'rsatkichlar", "Ilmiy faoliyat"],
        "additional_docs": ["Diplom nusxasi"],
        "deadline_hint": None,
        "amount_hint": "500,000 so'm",
    }

    with patch("mcp.tools.parse_nizom._extract_pdf_text", new_callable=AsyncMock) as mock_pdf, patch(
        "mcp.tools.parse_nizom.get_llm_client"
    ) as mock_factory:
        mock_pdf.return_value = "Stipendiya nizomi matni..."
        mock_llm = AsyncMock()
        mock_llm.complete_json = AsyncMock(return_value=mock_result)
        mock_factory.return_value = mock_llm

        from mcp.tools.parse_nizom import parse_nizom

        result = await parse_nizom(file_url="http://example.com/nizom.pdf")

        assert result.title == "Test Stipendiyasi"
        assert len(result.requirements) == 2
        assert len(result.evaluation_criteria) == 2
        assert result.raw_text == "Stipendiya nizomi matni..."


@pytest.mark.asyncio
async def test_parse_nizom_no_source_raises():
    from mcp.tools.parse_nizom import parse_nizom

    with pytest.raises(ValueError, match="file_url yoki file_bytes"):
        await parse_nizom()


@pytest.mark.asyncio
async def test_suggest_columns_returns_valid_columns():
    mock_result = {
        "columns": [
            {
                "name": "GPA",
                "description": "O'rtacha akademik ball",
                "field_type": "number",
                "select_options": None,
                "is_required": True,
                "ai_analyze": False,
                "max_score": 30,
                "order_index": 0,
            },
            {
                "name": "Motivatsiya xati",
                "description": "Nega bu stipendiya kerak?",
                "field_type": "textarea",
                "select_options": None,
                "is_required": True,
                "ai_analyze": True,
                "max_score": 40,
                "order_index": 1,
            },
        ]
    }

    with patch("mcp.tools.suggest_columns.get_llm_client") as mock_factory:
        mock_llm = AsyncMock()
        mock_llm.complete_json = AsyncMock(return_value=mock_result)
        mock_factory.return_value = mock_llm

        from mcp.tools.suggest_columns import suggest_columns

        result = await suggest_columns(
            scholarship_title="Test Stipendiyasi",
            purpose="Iqtidorli talabalar",
            requirements=["GPA 3.5+"],
            evaluation_criteria=["Akademik ko'rsatkichlar"],
        )

        assert len(result.columns) == 2
        assert result.columns[0].name == "GPA"
        assert result.columns[1].ai_analyze is True
        assert result.ai_columns_count == 1
        assert result.total_max_score == 70


@pytest.mark.asyncio
async def test_suggest_columns_invalid_columns_raise_value_error():
    mock_result = {
        "columns": [
            {
                "name": "Test ustun",
                "description": "Noto'g'ri field type",
                "field_type": "invalid_type",
                "select_options": None,
                "is_required": True,
                "ai_analyze": False,
                "max_score": 10,
                "order_index": 0,
            }
        ]
    }

    with patch("mcp.tools.suggest_columns.get_llm_client") as mock_factory:
        mock_llm = AsyncMock()
        mock_llm.complete_json = AsyncMock(return_value=mock_result)
        mock_factory.return_value = mock_llm

        from mcp.tools.suggest_columns import suggest_columns

        with pytest.raises(ValueError, match="validatsiyadan o'tmadi"):
            await suggest_columns(
                scholarship_title="Test",
                purpose="Maqsad",
                requirements=[],
                evaluation_criteria=[],
            )


@pytest.mark.asyncio
async def test_analyze_application_empty_value():
    from mcp.tools.analyze_application import analyze_single_column

    result = await analyze_single_column(
        column_id="test-id",
        column_name="Motivatsiya xati",
        column_description="Nega kerak?",
        max_score=30,
        student_value=None,
        file_url=None,
        scholarship_title="Test",
    )

    assert result.suggested_score == 0.0
    assert result.recommendation == "improve"
    assert "to'ldirmagan" in result.analysis.lower()


@pytest.mark.asyncio
async def test_analyze_application_full_flow():
    mock_col_result = {
        "analysis": "Student yaxshi motivatsiya xati yozgan.",
        "strengths": ["Aniq maqsad", "Tajriba bor"],
        "weaknesses": [],
        "suggested_score": 25.0,
        "score_reasoning": "Kuchli motivatsiya",
        "recommendation": "outstanding",
    }

    with patch("mcp.tools.analyze_application.get_llm_client") as mock_factory:
        mock_llm = AsyncMock()
        mock_llm.complete_json = AsyncMock(return_value=mock_col_result)
        mock_llm.complete = AsyncMock(return_value="Ariza juda kuchli tayyorlangan.")
        mock_factory.return_value = mock_llm

        from mcp.tools.analyze_application import analyze_application

        result = await analyze_application(
            application_id="app-123",
            scholarship_title="Test Stipendiyasi",
            columns_data=[
                {
                    "column_id": "col-1",
                    "column_name": "Motivatsiya xati",
                    "column_description": "Nega kerak?",
                    "max_score": 30,
                    "student_value": "Men bu stipendiyaga...",
                    "file_url": None,
                }
            ],
        )

        assert result.application_id == "app-123"
        assert len(result.column_analyses) == 1
        assert result.column_analyses[0].suggested_score == 25.0
        assert result.column_analyses[0].recommendation == "outstanding"


@pytest.mark.asyncio
async def test_generate_review_score_calculation():
    mock_review = {
        "review_text": "Hurmatli Alisher, sizning arizangiz kuchli yozilgan.",
        "summary": "Kuchli ariza, tavsiya etiladi.",
        "recommendation_note": "Kelgusi yil ham ariza topshiring.",
    }

    with patch("mcp.tools.generate_review.get_llm_client") as mock_factory:
        mock_llm = AsyncMock()
        mock_llm.complete_json = AsyncMock(return_value=mock_review)
        mock_factory.return_value = mock_llm

        from mcp.tools.generate_review import generate_review

        result = await generate_review(
            student_name="Alisher Karimov",
            scholarship_title="Test Stipendiyasi",
            scores={"col-1": 25.0, "col-2": 18.0},
            columns_info=[
                {"id": "col-1", "name": "Motivatsiya", "max_score": 30},
                {"id": "col-2", "name": "GPA", "max_score": 20},
            ],
        )

        assert result.total_score == 43.0
        assert result.max_total_score == 50.0
        assert result.score_percent == 86.0
        assert "Alisher" in result.review_text


@pytest.mark.asyncio
async def test_generate_review_zero_max_score():
    mock_review = {"review_text": "...", "summary": "...", "recommendation_note": "..."}

    with patch("mcp.tools.generate_review.get_llm_client") as mock_factory:
        mock_llm = AsyncMock()
        mock_llm.complete_json = AsyncMock(return_value=mock_review)
        mock_factory.return_value = mock_llm

        from mcp.tools.generate_review import generate_review

        result = await generate_review(
            student_name="Test",
            scholarship_title="Test",
            scores={},
            columns_info=[],
        )

        assert result.score_percent == 0.0
