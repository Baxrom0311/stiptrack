from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel, Field

from app.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Siz universitet stipendiya arizalarini baholovchi ekspertsiz. "
    "Faqat berilgan ma'lumot asosida xulosa bering, o'ylab topmang. "
    "Javob O'zbek tilida bo'lsin."
)

ANALYZE_PROMPT = """Stipendiya arizasidagi quyidagi ma'lumotni tahlil qiling:

Stipendiya: {scholarship_title}
Ustun: {column_name}
Tavsif: {column_description}
Maksimal ball: {max_score}

Student ma'lumoti:
{student_value}

JSON format:
{{
  "analysis": "3-5 jumla ob'ektiv tahlil",
  "strengths": ["Kuchli tomon 1"],
  "weaknesses": ["Kamchilik 1"],
  "suggested_score": 8.5,
  "score_reasoning": "Nega shu ball",
  "recommendation": "improve|accept|outstanding"
}}
"""

ANALYZE_FILE_PROMPT = """Stipendiya arizasida fayl yuklangan.

Stipendiya: {scholarship_title}
Ustun: {column_name}
Tavsif: {column_description}
Maksimal ball: {max_score}
Fayl URL: {file_url}
Fayl turi: {file_type}

Agar faylni bevosita ko'ra olmasangiz, URL/fayl nomi asosida konservativ tahlil bering.

JSON format:
{{
  "analysis": "Fayl bo'yicha qisqa tahlil",
  "strengths": ["Kuchli tomon 1"],
  "weaknesses": ["Kamchilik 1"],
  "suggested_score": {half_score},
  "score_reasoning": "Nega shu ball",
  "recommendation": "improve|accept|outstanding"
}}
"""

SUMMARY_PROMPT = """Stipendiya: {scholarship_title}
Quyidagi ustun tahlillari asosida umumiy xulosa yozing:
{analyses}

3-4 jumla, ob'ektiv va konstruktiv xulosa qaytaring.
"""


class ColumnAnalysisResult(BaseModel):
    column_id: str
    column_name: str
    analysis: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggested_score: float = Field(ge=0)
    score_reasoning: str
    recommendation: str


class ApplicationAnalysisResult(BaseModel):
    application_id: str
    column_analyses: list[ColumnAnalysisResult]
    overall_summary: str
    avg_suggested_score: float


async def analyze_single_column(
    column_id: str,
    column_name: str,
    column_description: str,
    max_score: int,
    student_value: str | None,
    file_url: str | None,
    scholarship_title: str,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> ColumnAnalysisResult:
    if not student_value and not file_url:
        return ColumnAnalysisResult(
            column_id=column_id,
            column_name=column_name,
            analysis="Student bu maydonni to'ldirmagan.",
            strengths=[],
            weaknesses=["Ma'lumot yuklanmagan"],
            suggested_score=0.0,
            score_reasoning="To'ldirilmagan maydon uchun ball berilmadi",
            recommendation="improve",
        )

    llm = get_llm_client(provider=llm_provider, model=llm_model)

    if file_url and not student_value:
        file_ext = file_url.rsplit(".", 1)[-1].lower() if "." in file_url else "unknown"
        prompt = ANALYZE_FILE_PROMPT.format(
            scholarship_title=scholarship_title,
            column_name=column_name,
            column_description=column_description or "",
            max_score=max_score,
            file_url=file_url,
            file_type=file_ext.upper(),
            half_score=round(max_score / 2, 1),
        )
    else:
        if file_url and student_value:
            student_value = f"{student_value}\n\nFayl: {file_url}"
        prompt = ANALYZE_PROMPT.format(
            scholarship_title=scholarship_title,
            column_name=column_name,
            column_description=column_description or "",
            max_score=max_score,
            student_value=(student_value or "")[:3000],
        )

    data = await llm.complete_json(prompt=prompt, system=SYSTEM_PROMPT)

    suggested_score = min(float(data.get("suggested_score", 0)), float(max_score))

    return ColumnAnalysisResult(
        column_id=column_id,
        column_name=column_name,
        analysis=data.get("analysis", ""),
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        suggested_score=round(suggested_score, 1),
        score_reasoning=data.get("score_reasoning", ""),
        recommendation=data.get("recommendation", "accept"),
    )


async def analyze_application(
    application_id: str,
    scholarship_title: str,
    columns_data: list[dict],
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> ApplicationAnalysisResult:
    logger.info("analyze_application boshlandi: application_id=%s columns=%s", application_id, len(columns_data))

    tasks = [
        analyze_single_column(
            column_id=item["column_id"],
            column_name=item["column_name"],
            column_description=item.get("column_description", ""),
            max_score=item.get("max_score", 10),
            student_value=item.get("student_value"),
            file_url=item.get("file_url"),
            scholarship_title=scholarship_title,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        for item in columns_data
    ]
    column_analyses = await asyncio.gather(*tasks)

    summary_input = "\n".join(f"- {item.column_name}: {item.analysis[:200]}" for item in column_analyses)

    llm = get_llm_client(provider=llm_provider, model=llm_model)
    overall_summary = await llm.complete(
        prompt=SUMMARY_PROMPT.format(scholarship_title=scholarship_title, analyses=summary_input),
        system=SYSTEM_PROMPT,
        max_tokens=512,
    )

    score_values = [item.suggested_score for item in column_analyses]
    avg_suggested_score = round(sum(score_values) / len(score_values), 2) if score_values else 0.0

    return ApplicationAnalysisResult(
        application_id=application_id,
        column_analyses=list(column_analyses),
        overall_summary=overall_summary.strip(),
        avg_suggested_score=avg_suggested_score,
    )
