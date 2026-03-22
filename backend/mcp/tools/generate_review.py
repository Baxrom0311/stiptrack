from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Siz universitet stipendiya komissiyasining professional kotibisiz. "
    "Hakam ballari va izohlari asosida student uchun aniq va konstruktiv yakuniy tahlil yozing. "
    "Javob O'zbek tilida bo'lsin."
)

REVIEW_PROMPT = """Stipendiya baholash natijasi asosida yakuniy tahlil yozing.

Student: {student_name}
Stipendiya: {scholarship_title}
Jami ball: {total_score:.1f} / {max_total_score}

Ustun balllari:
{scores_text}

AI xulosalar:
{ai_analyses_text}

Hakam izohi:
{jury_notes}

JSON format:
{{
  "review_text": "4-6 jumla yakuniy tahlil (konstruktiv)",
  "summary": "1-2 jumla qisqa xulosa",
  "recommendation_note": "1 jumla keyingi qadam"
}}
"""


class GenerateReviewResult(BaseModel):
    review_text: str
    summary: str
    recommendation_note: str = ""
    total_score: float
    max_total_score: float
    score_percent: float


async def generate_review(
    student_name: str,
    scholarship_title: str,
    scores: dict[str, float],
    columns_info: list[dict],
    ai_analyses: list[dict] | None = None,
    jury_notes: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> GenerateReviewResult:
    logger.info("generate_review boshlandi: student=%s scholarship=%s", student_name, scholarship_title)

    column_map = {str(col["id"]): col for col in columns_info}

    lines: list[str] = []
    total_score = 0.0
    max_total_score = 0.0

    for col_id, raw_score in scores.items():
        col = column_map.get(str(col_id), {})
        col_name = col.get("name", f"Ustun ({str(col_id)[:8]})")
        max_score = float(col.get("max_score", 10))
        score = float(raw_score)

        lines.append(f"- {col_name}: {score:.1f} / {max_score:.1f}")
        total_score += score
        max_total_score += max_score

    scores_text = "\n".join(lines) if lines else "Ball kiritilmagan"

    if ai_analyses:
        ai_lines: list[str] = []
        for item in ai_analyses:
            recommendation = str(item.get("recommendation", "accept")).strip()
            ai_lines.append(
                f"- {item.get('column_name', '?')} ({recommendation}): "
                f"{str(item.get('analysis', ''))[:200]}"
            )
        ai_analyses_text = "\n".join(ai_lines)
    else:
        ai_analyses_text = "AI tahlil ma'lumotlari yo'q"

    llm = get_llm_client(provider=llm_provider, model=llm_model)

    data = await llm.complete_json(
        prompt=REVIEW_PROMPT.format(
            student_name=student_name,
            scholarship_title=scholarship_title,
            total_score=total_score,
            max_total_score=max_total_score,
            scores_text=scores_text,
            ai_analyses_text=ai_analyses_text,
            jury_notes=(jury_notes or "Qo'shimcha izoh yo'q"),
        ),
        system=SYSTEM_PROMPT,
    )

    score_percent = round((total_score / max_total_score * 100) if max_total_score else 0.0, 1)

    result = GenerateReviewResult(
        review_text=data.get("review_text", ""),
        summary=data.get("summary", ""),
        recommendation_note=data.get("recommendation_note", ""),
        total_score=round(total_score, 2),
        max_total_score=round(max_total_score, 2),
        score_percent=score_percent,
    )

    logger.info(
        "generate_review tugadi: total=%.1f max=%.1f percent=%.1f",
        result.total_score,
        result.max_total_score,
        result.score_percent,
    )
    return result
