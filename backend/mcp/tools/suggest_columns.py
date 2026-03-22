from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)

FieldType = Literal["text", "textarea", "file", "number", "date", "select", "url"]

SYSTEM_PROMPT = """Siz universitet stipendiya tizimi mutaxassisi va UX dizaynerisiz.
Stipendiya nizomi asosida faqat shu nizomga mos ariza ustunlarini taklif qiling.
Javob O'zbek tilida bo'lsin."""

SUGGEST_PROMPT = """Quyidagi stipendiya uchun ariza formasi ustunlarini taklif qiling.

STIPENDIYA MA'LUMOTLARI:
Nomi: {title}
Maqsad: {purpose}
Ariza topshira oladiganlar: {eligible}
Tanlov bosqichlari: {stages}

Talablar:
{requirements}

Baholash tizimi (scoring_type: {scoring_type}):
{criteria_block}

Qo'shimcha hujjatlar:
{docs}

Qoidalar:
1. Har bir baholash mezoni uchun kamida bitta ustun bo'lsin.
2. Ball aniq ko'rsatilgan bo'lsa max_score'ni o'sha raqamdan oling.
3. Darajali mezonlarda field_type="select" va select_options to'ldiring.
4. Matn/fayl mazmuni tahlili kerak bo'lsa ai_analyze=true bo'lsin.
5. Faqat quyidagi field_type ishlatilsin:
   text, textarea, file, number, date, select, url

Quyidagi JSON formatda qaytaring:
{{
  "reasoning": "Qisqa izoh",
  "columns": [
    {{
      "name": "Ustun nomi",
      "criterion_ref": "Qaysi mezonga tegishli",
      "description": "To'ldirish ko'rsatmasi",
      "field_type": "text|textarea|file|number|date|select|url",
      "select_options": ["Variant 1", "Variant 2"],
      "is_required": true,
      "ai_analyze": false,
      "max_score": 20,
      "order_index": 0,
      "validation_hint": "Nima tekshiriladi"
    }}
  ]
}}
"""


def _format_criteria_block(
    criteria: list[str | dict[str, object]],
    scoring_type: str,
    total_max_score: int,
) -> str:
    if not criteria:
        return f"Ball tizimi: {scoring_type}. Jami maksimal ball: {total_max_score}"

    lines = [f"Ball tizimi: {scoring_type} | Jami maksimal: {total_max_score} ball", ""]
    for index, item in enumerate(criteria, start=1):
        if isinstance(item, str):
            if item.strip():
                lines.append(f"{index}. {item.strip()}")
            continue

        if not isinstance(item, dict):
            continue

        name = str(item.get("name", f"Mezon {index}")).strip() or f"Mezon {index}"
        max_score = item.get("max_score", 0)
        description = str(item.get("description", "")).strip()
        lines.append(f"{index}. {name} -> maksimal {max_score} ball")
        if description:
            lines.append(f"   Izoh: {description}")

        raw_sub_scores = item.get("sub_scores", [])
        if isinstance(raw_sub_scores, list) and raw_sub_scores:
            lines.append("   Darajalar:")
            for sub in raw_sub_scores:
                if not isinstance(sub, dict):
                    continue
                label = str(sub.get("label", "")).strip()
                score = sub.get("score", 0)
                if label:
                    lines.append(f"   - {label}: {score} ball")

    return "\n".join(lines)


class SuggestedColumn(BaseModel):
    name: str
    criterion_ref: str = "umumiy"
    description: str
    field_type: FieldType = "text"
    select_options: list[str] | None = None
    is_required: bool = True
    ai_analyze: bool = False
    max_score: int = Field(default=10, ge=0, le=100)
    order_index: int = Field(default=0, ge=0)
    validation_hint: str | None = None

    @field_validator("select_options")
    @classmethod
    def normalize_select_options(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [v.strip() for v in value if v and v.strip()]
        return cleaned or None


class SuggestColumnsResult(BaseModel):
    columns: list[SuggestedColumn]
    total_max_score: int
    ai_columns_count: int
    reasoning: str = ""


async def suggest_columns(
    scholarship_title: str,
    purpose: str,
    requirements: list[str],
    evaluation_criteria: list[str | dict[str, object]],
    additional_docs: list[str] | None = None,
    total_max_score: int = 0,
    scoring_type: str = "table",
    eligible_students: str | None = None,
    selection_stages: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> SuggestColumnsResult:
    llm = get_llm_client(provider=llm_provider, model=llm_model)

    criteria_block = _format_criteria_block(
        criteria=evaluation_criteria,
        scoring_type=scoring_type,
        total_max_score=total_max_score,
    )

    prompt = SUGGEST_PROMPT.format(
        title=scholarship_title,
        purpose=purpose,
        eligible=eligible_students or "Ko'rsatilmagan",
        stages=selection_stages or "Ko'rsatilmagan",
        requirements="\n".join(f"- {x}" for x in requirements) or "- Ko'rsatilmagan",
        scoring_type=scoring_type,
        criteria_block=criteria_block,
        docs="\n".join(f"- {x}" for x in (additional_docs or [])) or "- Ko'rsatilmagan",
    )

    data = await llm.complete_json(prompt=prompt, system=SYSTEM_PROMPT)
    raw_columns = data.get("columns", [])
    if not raw_columns:
        raise ValueError("LLM hech qanday ustun taklif qilmadi")

    columns: list[SuggestedColumn] = []
    for idx, raw in enumerate(raw_columns):
        if not isinstance(raw, dict):
            continue
        raw["order_index"] = idx
        raw.setdefault("criterion_ref", "umumiy")
        raw.setdefault("validation_hint", None)
        try:
            columns.append(SuggestedColumn(**raw))
        except Exception as exc:
            logger.warning("Yaroqsiz ustun o'tkazib yuborildi: %s", exc)

    if not columns:
        raise ValueError("Taklif qilingan ustunlar validatsiyadan o'tmadi")

    total_max_score = sum(col.max_score for col in columns)
    ai_columns_count = sum(1 for col in columns if col.ai_analyze)

    return SuggestColumnsResult(
        columns=columns,
        total_max_score=total_max_score,
        ai_columns_count=ai_columns_count,
        reasoning=str(data.get("reasoning", "")).strip(),
    )
