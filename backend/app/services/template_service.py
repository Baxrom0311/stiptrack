from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.models.enums import LLMProvider, ScholarshipStatus
from app.models.scholarship import Scholarship, ScholarshipColumn, ScholarshipTemplate
from app.models.workflow import ScholarshipStage, StageTask


def _column_snapshot(column: ScholarshipColumn) -> dict:
    return {
        "name": column.name,
        "description": column.description,
        "field_type": column.field_type.value,
        "select_options": column.select_options,
        "is_required": column.is_required,
        "ai_analyze": column.ai_analyze,
        "max_score": column.max_score,
        "input_min": column.input_min,
        "input_max": column.input_max,
        "order_index": column.order_index,
    }


def _task_snapshot(task: StageTask, *, stage_starts_at: datetime) -> dict:
    due_offset_seconds = None
    if task.due_at is not None:
        due_offset_seconds = int((task.due_at - stage_starts_at).total_seconds())

    return {
        "title": task.title,
        "description": task.description,
        "assigned_role": task.assigned_role.value if task.assigned_role is not None else None,
        "due_offset_seconds": due_offset_seconds,
    }


def _stage_snapshot(stage: ScholarshipStage, *, base_starts_at: datetime) -> dict:
    tasks = sorted(
        list(getattr(stage, "tasks", []) or []),
        key=lambda item: (
            item.due_at or datetime.max.replace(tzinfo=timezone.utc),
            item.created_at or datetime.max.replace(tzinfo=timezone.utc),
        ),
    )

    return {
        "name": stage.name,
        "stage_type": stage.stage_type.value,
        "description": stage.description,
        "order_index": stage.order_index,
        "starts_offset_seconds": int((stage.starts_at - base_starts_at).total_seconds()),
        "ends_offset_seconds": int((stage.ends_at - base_starts_at).total_seconds()),
        "is_required": stage.is_required,
        "is_active": stage.is_active,
        "config": stage.config,
        "tasks": [_task_snapshot(task, stage_starts_at=stage.starts_at) for task in tasks],
    }


def build_scholarship_template_snapshot(scholarship: Scholarship) -> dict:
    columns = sorted(list(getattr(scholarship, "columns", []) or []), key=lambda item: item.order_index)
    stages = sorted(list(getattr(scholarship, "stages", []) or []), key=lambda item: item.order_index)
    base_starts_at = min((stage.starts_at for stage in stages), default=datetime.now(timezone.utc))

    return {
        "scholarship": {
            "title": scholarship.title,
            "description": scholarship.description,
            "nizom_file_url": scholarship.nizom_file_url,
            "ai_analysis_enabled": scholarship.ai_analysis_enabled,
            "blind_review_enabled": scholarship.blind_review_enabled,
            "max_winners": scholarship.max_winners,
            "ai_provider": scholarship.ai_provider.value
            if hasattr(scholarship.ai_provider, "value")
            else scholarship.ai_provider,
            "ai_model": scholarship.ai_model,
        },
        "columns": [_column_snapshot(column) for column in columns],
        "stages": [_stage_snapshot(stage, base_starts_at=base_starts_at) for stage in stages],
    }


def build_template_summary(template: ScholarshipTemplate) -> dict:
    snapshot = template.snapshot or {}
    scholarship_defaults = snapshot.get("scholarship", {})
    columns = snapshot.get("columns", [])
    stages = snapshot.get("stages", [])
    task_count = sum(len(stage.get("tasks", [])) for stage in stages)

    return {
        "id": template.id,
        "created_by": template.created_by,
        "source_scholarship_id": template.source_scholarship_id,
        "name": template.name,
        "description": template.description,
        "snapshot_title": scholarship_defaults.get("title"),
        "ai_analysis_enabled": bool(scholarship_defaults.get("ai_analysis_enabled", False)),
        "blind_review_enabled": bool(scholarship_defaults.get("blind_review_enabled", False)),
        "max_winners": int(scholarship_defaults.get("max_winners", 1)),
        "ai_provider": scholarship_defaults.get("ai_provider", "claude"),
        "ai_model": scholarship_defaults.get("ai_model"),
        "column_count": len(columns),
        "stage_count": len(stages),
        "task_count": task_count,
        "nizom_file_url": scholarship_defaults.get("nizom_file_url"),
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def instantiate_scholarship_from_template(
    template: ScholarshipTemplate,
    *,
    created_by: uuid.UUID,
) -> tuple[Scholarship, list[ScholarshipColumn], list[ScholarshipStage], list[StageTask]]:
    snapshot = template.snapshot or {}
    defaults = snapshot.get("scholarship", {})
    title = str(defaults.get("title") or template.name).strip() or "Template scholarship"
    base_starts_at = datetime.now(timezone.utc)

    scholarship = Scholarship(
        id=uuid.uuid4(),
        created_by=created_by,
        title=title,
        description=defaults.get("description"),
        nizom_file_url=defaults.get("nizom_file_url"),
        status=ScholarshipStatus.DRAFT,
        deadline=None,
        ai_analysis_enabled=bool(defaults.get("ai_analysis_enabled", False)),
        blind_review_enabled=bool(defaults.get("blind_review_enabled", False)),
        max_winners=int(defaults.get("max_winners", 1)),
        ai_provider=LLMProvider(str(defaults.get("ai_provider", "claude"))),
        ai_model=defaults.get("ai_model"),
    )

    columns: list[ScholarshipColumn] = []
    for column_data in sorted(snapshot.get("columns", []), key=lambda item: item.get("order_index", 0)):
        columns.append(
            ScholarshipColumn(
                id=uuid.uuid4(),
                scholarship_id=scholarship.id,
                name=column_data.get("name", "Untitled column"),
                description=column_data.get("description"),
                field_type=column_data.get("field_type", "text"),
                select_options=column_data.get("select_options"),
                is_required=bool(column_data.get("is_required", True)),
                ai_analyze=bool(column_data.get("ai_analyze", False)),
                max_score=int(column_data.get("max_score", 0)),
                input_min=column_data.get("input_min"),
                input_max=column_data.get("input_max"),
                order_index=int(column_data.get("order_index", 0)),
            )
        )

    stages: list[ScholarshipStage] = []
    tasks: list[StageTask] = []
    for stage_data in sorted(snapshot.get("stages", []), key=lambda item: item.get("order_index", 0)):
        starts_at = base_starts_at + timedelta(seconds=int(stage_data.get("starts_offset_seconds", 0)))
        ends_at = base_starts_at + timedelta(seconds=int(stage_data.get("ends_offset_seconds", 0)))
        stage = ScholarshipStage(
            id=uuid.uuid4(),
            scholarship_id=scholarship.id,
            name=stage_data.get("name", "Untitled stage"),
            stage_type=stage_data.get("stage_type", "application"),
            description=stage_data.get("description"),
            order_index=int(stage_data.get("order_index", 0)),
            starts_at=starts_at,
            ends_at=ends_at,
            is_required=bool(stage_data.get("is_required", True)),
            is_active=bool(stage_data.get("is_active", True)),
            config=stage_data.get("config"),
        )
        stages.append(stage)

        for task_data in stage_data.get("tasks", []):
            due_at = None
            due_offset_seconds = task_data.get("due_offset_seconds")
            if due_offset_seconds is not None:
                due_at = starts_at + timedelta(seconds=int(due_offset_seconds))

            tasks.append(
                StageTask(
                    id=uuid.uuid4(),
                    stage_id=stage.id,
                    title=task_data.get("title", "Untitled task"),
                    description=task_data.get("description"),
                    assigned_role=task_data.get("assigned_role"),
                    due_at=due_at,
                )
            )

    return scholarship, columns, stages, tasks
