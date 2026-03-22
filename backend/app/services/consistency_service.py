from __future__ import annotations

from statistics import pstdev

from app.models.evaluation import Evaluation
from app.schemas.admin import EvaluationConsistencyItem, EvaluationConsistencySummary


CONSISTENCY_WARNING_SPREAD = 15.0


def _submitted_scores(evaluations: list[Evaluation]) -> list[float]:
    scores: list[float] = []
    for evaluation in evaluations:
        if evaluation.is_submitted and evaluation.total_score is not None:
            scores.append(round(float(evaluation.total_score), 2))
    return scores


def build_evaluation_consistency_summary(
    evaluations: list[Evaluation],
    *,
    warning_threshold: float = CONSISTENCY_WARNING_SPREAD,
) -> EvaluationConsistencySummary:
    scores = _submitted_scores(evaluations)
    if not scores:
        return EvaluationConsistencySummary(
            jury_count=0,
            average_score=None,
            min_score=None,
            max_score=None,
            score_spread=None,
            score_stddev=None,
            warning_threshold=warning_threshold,
            is_flagged=False,
        )

    average_score = round(sum(scores) / len(scores), 2)
    min_score = round(min(scores), 2)
    max_score = round(max(scores), 2)
    score_spread = round(max_score - min_score, 2) if len(scores) >= 2 else None
    score_stddev = round(float(pstdev(scores)), 2) if len(scores) >= 2 else None

    return EvaluationConsistencySummary(
        jury_count=len(scores),
        average_score=average_score,
        min_score=min_score,
        max_score=max_score,
        score_spread=score_spread,
        score_stddev=score_stddev,
        warning_threshold=warning_threshold,
        is_flagged=score_spread is not None and score_spread >= warning_threshold,
    )


def build_evaluation_consistency_items(evaluations: list[Evaluation]) -> list[EvaluationConsistencyItem]:
    submitted_evaluations = [item for item in evaluations if item.is_submitted]
    submitted_evaluations.sort(
        key=lambda item: (
            float(item.total_score) if item.total_score is not None else -1,
            item.submitted_at.isoformat() if item.submitted_at is not None else "",
        ),
        reverse=True,
    )

    return [
        EvaluationConsistencyItem(
            evaluation_id=item.id,
            jury_id=item.jury_id,
            jury_name=item.jury.full_name if item.jury is not None else str(item.jury_id),
            total_score=round(float(item.total_score), 2) if item.total_score is not None else None,
            final_comment=item.final_comment,
            submitted_at=item.submitted_at,
        )
        for item in submitted_evaluations
    ]
