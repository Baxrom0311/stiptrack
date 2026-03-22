from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.llm_client import format_llm_selection
from app.models.ai_job import AIJob
from app.models.application import Application, ApplicationStatusLog, ApplicationValue
from app.models.enums import AIJobStatus, AIJobType
from app.models.scholarship import Scholarship
from app.services.notification_service import build_application_status_email_payload, send_message
from mcp.tools.analyze_application import analyze_application
from mcp.tools.suggest_columns import suggest_columns
from workers.celery_app import celery_app


logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_session_factory() -> async_sessionmaker:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=5,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _session_factory


def _run_async(coro: Any) -> Any:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="health.echo")
def health_echo(payload: str) -> str:
    return payload


@celery_app.task(name="ai.run_application_analysis", bind=True, max_retries=3, default_retry_delay=30)
def run_application_analysis(self, application_id: str) -> dict:
    logger.info("[Celery] run_application_analysis application_id=%s", application_id)

    try:
        application_uuid = uuid.UUID(str(application_id))
    except ValueError as exc:
        raise ValueError(f"Invalid application_id: {application_id}") from exc

    async def _run() -> dict:
        session_factory = _get_session_factory()

        async with session_factory() as db:
            job = AIJob(
                job_type=AIJobType.APP_ANALYSIS,
                ref_id=application_uuid,
                model_used=None,
                status=AIJobStatus.RUNNING,
                input_data={"application_id": application_id},
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            try:
                result = await db.execute(
                    select(Application)
                    .options(
                        selectinload(Application.values),
                        selectinload(Application.scholarship).selectinload(Scholarship.columns),
                    )
                    .where(Application.id == application_uuid)
                )
                application = result.scalar_one_or_none()
                if application is None:
                    raise ValueError(f"Ariza topilmadi: {application_id}")

                job.model_used = format_llm_selection(
                    application.scholarship.ai_provider,
                    application.scholarship.ai_model,
                )

                ai_columns = [column for column in application.scholarship.columns if column.ai_analyze]
                if not ai_columns:
                    job.status = AIJobStatus.DONE
                    job.result = {"message": "ai_analyze yoqilgan ustunlar topilmadi"}
                    job.finished_at = datetime.now(timezone.utc)
                    await db.commit()
                    return {"status": "done", "job_id": str(job.id), "result": job.result}

                values_by_column_id = {value.column_id: value for value in application.values}
                columns_data: list[dict[str, Any]] = []

                for column in ai_columns:
                    value = values_by_column_id.get(column.id)
                    columns_data.append(
                        {
                            "column_id": str(column.id),
                            "column_name": column.name,
                            "column_description": column.description or "",
                            "max_score": column.max_score,
                            "student_value": value.value_text if value else None,
                            "file_url": value.value_file_url if value else None,
                        }
                    )

                analysis_result = await analyze_application(
                    application_id=application_id,
                    scholarship_title=application.scholarship.title,
                    columns_data=columns_data,
                    llm_provider=application.scholarship.ai_provider,
                    llm_model=application.scholarship.ai_model,
                )

                now = datetime.now(timezone.utc)
                for item in analysis_result.column_analyses:
                    try:
                        column_uuid = uuid.UUID(item.column_id)
                    except ValueError:
                        continue

                    value = values_by_column_id.get(column_uuid)
                    if value is None:
                        value = ApplicationValue(
                            application_id=application.id,
                            column_id=column_uuid,
                        )
                        db.add(value)
                        values_by_column_id[column_uuid] = value

                    value.ai_analysis = item.analysis
                    value.ai_score = item.suggested_score
                    value.analyzed_at = now

                application.ai_summary = analysis_result.overall_summary

                job.status = AIJobStatus.DONE
                job.result = analysis_result.model_dump()
                job.finished_at = now

                await db.commit()

                return {"status": "done", "job_id": str(job.id), "result": job.result}
            except Exception as exc:
                logger.exception("run_application_analysis xatolik: %s", exc)
                job.status = AIJobStatus.FAILED
                job.error_msg = str(exc)
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                raise

    try:
        return _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(name="notifications.send_application_status_email", bind=True, max_retries=3, default_retry_delay=60)
def send_application_status_email(self, status_log_id: str) -> dict:
    logger.info("[Celery] send_application_status_email status_log_id=%s", status_log_id)

    try:
        status_log_uuid = uuid.UUID(str(status_log_id))
    except ValueError as exc:
        raise ValueError(f"Invalid status_log_id: {status_log_id}") from exc

    async def _run() -> dict:
        session_factory = _get_session_factory()

        async with session_factory() as db:
            result = await db.execute(
                select(ApplicationStatusLog)
                .options(
                    selectinload(ApplicationStatusLog.application).selectinload(Application.student),
                    selectinload(ApplicationStatusLog.application).selectinload(Application.scholarship),
                )
                .where(ApplicationStatusLog.id == status_log_uuid)
            )
            status_log = result.scalar_one_or_none()
            if status_log is None:
                return {"status": "skipped", "reason": "status_log_not_found"}

            application = status_log.application
            if application is None:
                return {"status": "skipped", "reason": "application_not_found"}

            payload = build_application_status_email_payload(application=application, status_log=status_log)
            if payload is None:
                return {"status": "skipped", "reason": "notification_not_applicable"}

            await send_message(payload)
            return {
                "status": "sent",
                "status_log_id": str(status_log.id),
                "application_id": str(application.id),
                "recipient": application.student.email if application.student else None,
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("send_application_status_email xatolik: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="ai.run_column_generation", bind=True, max_retries=3, default_retry_delay=30)
def run_column_generation(
    self,
    scholarship_id: str,
    purpose: str,
    requirements: list[str],
    criteria: list[str | dict[str, Any]],
    docs: list[str] | None = None,
    total_max_score: int = 0,
    scoring_type: str = "table",
    eligible_students: str | None = None,
    selection_stages: str | None = None,
    job_id: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> dict:
    logger.info("[Celery] run_column_generation scholarship_id=%s", scholarship_id)

    try:
        scholarship_uuid = uuid.UUID(str(scholarship_id))
    except ValueError as exc:
        raise ValueError(f"Invalid scholarship_id: {scholarship_id}") from exc

    job_uuid: uuid.UUID | None = None
    if job_id is not None:
        try:
            job_uuid = uuid.UUID(str(job_id))
        except ValueError as exc:
            raise ValueError(f"Invalid job_id: {job_id}") from exc

    async def _run() -> dict:
        session_factory = _get_session_factory()

        async with session_factory() as db:
            scholarship = await db.get(Scholarship, scholarship_uuid)
            if scholarship is None:
                raise ValueError(f"Stipendiya topilmadi: {scholarship_id}")

            effective_provider = llm_provider or scholarship.ai_provider
            effective_model = llm_model if llm_model is not None else scholarship.ai_model
            model_used = format_llm_selection(effective_provider, effective_model)
            input_data = {
                "scholarship_id": scholarship_id,
                "purpose": purpose,
                "requirements": requirements,
                "criteria": criteria,
                "docs": docs or [],
                "total_max_score": total_max_score,
                "scoring_type": scoring_type,
                "eligible_students": eligible_students,
                "selection_stages": selection_stages,
            }

            job: AIJob | None = None
            if job_uuid is not None:
                job = await db.get(AIJob, job_uuid)

            if job is None:
                job = AIJob(
                    job_type=AIJobType.COLUMN_GEN,
                    ref_id=scholarship_uuid,
                    model_used=model_used,
                    status=AIJobStatus.PENDING,
                    input_data=input_data,
                )
                db.add(job)

            job.job_type = AIJobType.COLUMN_GEN
            job.ref_id = scholarship_uuid
            job.model_used = model_used
            job.status = AIJobStatus.RUNNING
            job.input_data = input_data
            job.error_msg = None
            job.finished_at = None
            await db.commit()
            await db.refresh(job)

            try:
                columns_result = await suggest_columns(
                    scholarship_title=scholarship.title,
                    purpose=purpose,
                    requirements=requirements,
                    evaluation_criteria=criteria,
                    additional_docs=docs or [],
                    total_max_score=total_max_score,
                    scoring_type=scoring_type,
                    eligible_students=eligible_students,
                    selection_stages=selection_stages,
                    llm_provider=effective_provider,
                    llm_model=effective_model,
                )

                job.status = AIJobStatus.DONE
                job.result = columns_result.model_dump()
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()

                return {"status": "done", "job_id": str(job.id), "result": job.result}
            except Exception as exc:
                logger.exception("run_column_generation xatolik: %s", exc)
                job.status = AIJobStatus.FAILED
                job.error_msg = str(exc)
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                raise

    try:
        return _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
