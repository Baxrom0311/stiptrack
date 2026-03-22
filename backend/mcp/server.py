from __future__ import annotations

import logging

from fastmcp import FastMCP

from app.core.config import settings
from mcp.tools.analyze_application import analyze_application
from mcp.tools.generate_review import generate_review
from mcp.tools.parse_nizom import parse_nizom
from mcp.tools.suggest_columns import suggest_columns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP("stiptrack-ai")


@mcp.tool(name="parse_nizom")
async def tool_parse_nizom(file_url: str, llm_provider: str = "", llm_model: str = "") -> dict:
    result = await parse_nizom(
        file_url=file_url,
        llm_provider=llm_provider or None,
        llm_model=llm_model or None,
    )
    return result.model_dump()


@mcp.tool(name="suggest_columns")
async def tool_suggest_columns(
    scholarship_title: str,
    purpose: str,
    requirements: list[str],
    evaluation_criteria: list[str | dict[str, object]],
    additional_docs: list[str] | None = None,
    total_max_score: int = 0,
    scoring_type: str = "table",
    eligible_students: str | None = None,
    selection_stages: str | None = None,
    llm_provider: str = "",
    llm_model: str = "",
) -> dict:
    result = await suggest_columns(
        scholarship_title=scholarship_title,
        purpose=purpose,
        requirements=requirements,
        evaluation_criteria=evaluation_criteria,
        additional_docs=additional_docs,
        total_max_score=total_max_score,
        scoring_type=scoring_type,
        eligible_students=eligible_students,
        selection_stages=selection_stages,
        llm_provider=llm_provider or None,
        llm_model=llm_model or None,
    )
    return result.model_dump()


@mcp.tool(name="analyze_application")
async def tool_analyze_application(
    application_id: str,
    scholarship_title: str,
    columns_data: list[dict],
    llm_provider: str = "",
    llm_model: str = "",
) -> dict:
    result = await analyze_application(
        application_id=application_id,
        scholarship_title=scholarship_title,
        columns_data=columns_data,
        llm_provider=llm_provider or None,
        llm_model=llm_model or None,
    )
    return result.model_dump()


@mcp.tool(name="generate_review")
async def tool_generate_review(
    student_name: str,
    scholarship_title: str,
    scores: dict,
    columns_info: list[dict],
    ai_analyses: list[dict] | None = None,
    jury_notes: str = "",
    llm_provider: str = "",
    llm_model: str = "",
) -> dict:
    result = await generate_review(
        student_name=student_name,
        scholarship_title=scholarship_title,
        scores=scores,
        columns_info=columns_info,
        ai_analyses=ai_analyses,
        jury_notes=jury_notes,
        llm_provider=llm_provider or None,
        llm_model=llm_model or None,
    )
    return result.model_dump()


if __name__ == "__main__":
    logger.info("FastMCP server ishga tushmoqda: port=%s", settings.mcp_server_port)
    mcp.run(host="0.0.0.0", port=settings.mcp_server_port)
