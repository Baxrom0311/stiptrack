from __future__ import annotations

import io
import logging

import httpx
from pydantic import BaseModel, Field

from app.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Siz universitet stipendiya hujjatlarini tahlil qiluvchi mutaxassissiz.
Nizom matnidan faqat aniq ko'rsatilgan ma'lumotlarni ajrating.
Javob O'zbek tilida bo'lsin."""

PARSE_PROMPT = """Quyidagi stipendiya nizomini tahlil qiling va JSON qaytaring:

=== NIZOM MATNI ===
{text}
===================

Quyidagi JSON formatda qaytaring:
{{
  "title": "Stipendiya nomi (agar ko'rsatilgan bo'lsa)",
  "purpose": "Stipendiyaning asosiy maqsadi (2-3 jumlada)",
  "requirements": ["Talab 1", "Talab 2"],
  "evaluation_criteria": [
    {{
      "name": "Mezon nomi",
      "max_score": 20,
      "description": "Qisqa izoh",
      "sub_scores": [
        {{"label": "Xalqaro", "score": 20}},
        {{"label": "Respublika", "score": 10}}
      ]
    }}
  ],
  "additional_docs": ["Hujjat 1", "Hujjat 2"],
  "scoring_type": "table|text|mixed",
  "total_max_score": 100,
  "eligible_students": "Kimlar topshira oladi (yoki null)",
  "selection_stages": "Tanlov bosqichlari (yoki null)",
  "deadline_hint": "Muddat (yoki null)",
  "amount_hint": "Miqdor (yoki null)"
}}

Qoidalar:
1. Faqat hujjatda bor ma'lumotni yozing.
2. Ball aniq ko'rsatilmagan mezonlarda max_score=0 bo'lsin.
3. evaluation_criteria ba'zi hollarda string ro'yxatga ham tushishi mumkin.
"""


def _to_int(value: object, default: int = 0) -> int:
    try:
        parsed = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(parsed, 0)


def _to_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            items.append(item.strip())
    return items


class SubScore(BaseModel):
    label: str = Field(..., description="Daraja nomi")
    score: int = Field(default=0, ge=0, description="Ball")


class EvaluationCriterion(BaseModel):
    name: str = Field(..., description="Mezon nomi")
    max_score: int = Field(default=0, ge=0, description="Maksimal ball")
    description: str = Field(default="", description="Mezon izohi")
    sub_scores: list[SubScore] = Field(default_factory=list)


class NizomParseResult(BaseModel):
    title: str | None = Field(default=None)
    purpose: str
    requirements: list[str]
    evaluation_criteria: list[EvaluationCriterion]
    additional_docs: list[str] = Field(default_factory=list)
    scoring_type: str = Field(default="table")
    total_max_score: int = Field(default=0, ge=0)
    eligible_students: str | None = Field(default=None)
    selection_stages: str | None = Field(default=None)
    deadline_hint: str | None = Field(default=None)
    amount_hint: str | None = Field(default=None)
    raw_text: str


async def _extract_pdf_text(source: str | bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ImportError("pypdf kerak: pip install pypdf") from exc

    if isinstance(source, str):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(source)
            response.raise_for_status()
            pdf_bytes = response.content
    else:
        pdf_bytes = source

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text.strip())

    full_text = "\n\n".join(pages_text)

    if not full_text.strip():
        raise ValueError("PDF dan matn ajratib bo'lmadi")

    if len(full_text) > 12000:
        logger.warning("PDF matni juda uzun (%s), 12000 belgiga qisqartirildi", len(full_text))
        full_text = full_text[:12000] + "\n\n[... qolgan qism qisqartirildi ...]"

    return full_text


async def parse_nizom(
    file_url: str | None = None,
    file_bytes: bytes | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> NizomParseResult:
    if not file_url and not file_bytes:
        raise ValueError("file_url yoki file_bytes berilishi shart")

    source = file_url if file_url else file_bytes
    raw_text = await _extract_pdf_text(source)

    llm = get_llm_client(provider=llm_provider, model=llm_model)
    data = await llm.complete_json(
        prompt=PARSE_PROMPT.format(text=raw_text),
        system=SYSTEM_PROMPT,
    )

    raw_criteria = data.get("evaluation_criteria", [])
    parsed_criteria: list[EvaluationCriterion] = []

    if isinstance(raw_criteria, list):
        for item in raw_criteria:
            if isinstance(item, str):
                label = item.strip()
                if label:
                    parsed_criteria.append(EvaluationCriterion(name=label, max_score=0))
                continue

            if not isinstance(item, dict):
                continue

            sub_scores: list[SubScore] = []
            raw_sub_scores = item.get("sub_scores", [])
            if isinstance(raw_sub_scores, list):
                for sub in raw_sub_scores:
                    if not isinstance(sub, dict):
                        continue
                    sub_label = str(sub.get("label", "")).strip()
                    if not sub_label:
                        continue
                    sub_scores.append(
                        SubScore(
                            label=sub_label,
                            score=_to_int(sub.get("score"), 0),
                        )
                    )

            parsed_criteria.append(
                EvaluationCriterion(
                    name=str(item.get("name", "Nomsiz mezon")).strip() or "Nomsiz mezon",
                    max_score=_to_int(item.get("max_score"), 0),
                    description=str(item.get("description", "")).strip(),
                    sub_scores=sub_scores,
                )
            )

    llm_total = _to_int(data.get("total_max_score"), 0)
    calculated_total = sum(item.max_score for item in parsed_criteria)
    total_max_score = llm_total if llm_total > 0 else calculated_total

    scoring_type = str(data.get("scoring_type", "table")).strip().lower()
    if scoring_type not in {"table", "text", "mixed"}:
        scoring_type = "table"

    return NizomParseResult(
        title=data.get("title"),
        purpose=str(data.get("purpose", "")).strip(),
        requirements=_to_str_list(data.get("requirements")),
        evaluation_criteria=parsed_criteria,
        additional_docs=_to_str_list(data.get("additional_docs")),
        scoring_type=scoring_type,
        total_max_score=total_max_score,
        eligible_students=(
            str(data.get("eligible_students")).strip() if data.get("eligible_students") else None
        ),
        selection_stages=(
            str(data.get("selection_stages")).strip() if data.get("selection_stages") else None
        ),
        deadline_hint=data.get("deadline_hint"),
        amount_hint=data.get("amount_hint"),
        raw_text=raw_text,
    )
