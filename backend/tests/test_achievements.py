from __future__ import annotations

from datetime import date, datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

import app.api.v1.achievements as achievements_api
import app.schemas.achievement as achievement_schema
from app.models.enums import AchievementType, UserRole
from app.schemas.achievement import AchievementCreate, AchievementUpdate


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _ExecuteResult:
    def __init__(self, items=None, scalar=None):
        self._items = items or []
        self._scalar = scalar

    def scalars(self):
        return _ScalarResult(self._items)

    def scalar_one_or_none(self):
        if self._scalar is not None:
            return self._scalar
        if len(self._items) == 1:
            return self._items[0]
        if not self._items:
            return None
        raise AssertionError("Expected zero or one item")


class DummyDB:
    def __init__(self, execute_results=None) -> None:
        self._execute_results = list(execute_results or [])
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commits = 0

    async def execute(self, _stmt):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call")
        return self._execute_results.pop(0)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: object) -> None:
        now = datetime.now(timezone.utc)
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "file_url", None) is None:
            obj.file_url = None

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


def build_user() -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        full_name="Student User",
        email="student@example.com",
        role=UserRole.STUDENT,
        department="CS",
        student_id="S-200",
        is_supervisor=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_achievement(**overrides: object) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid4(),
        "student_id": uuid4(),
        "title": "Respublika olimpiadasi",
        "type": AchievementType.OLYMPIAD,
        "file_url": None,
        "date": date(2025, 5, 1),
        "description": "1-o‘rin",
        "created_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_list_achievements_returns_student_items(monkeypatch: pytest.MonkeyPatch):
    student = build_user()
    achievement = build_achievement(student_id=student.id, type=AchievementType.AWARD, file_url="achievement/test.pdf")
    db = DummyDB(execute_results=[_ExecuteResult(items=[achievement])])
    monkeypatch.setattr(
        achievement_schema,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    result = await achievements_api.list_achievements(
        current_user=student,
        db=db,
        achievement_type=AchievementType.AWARD,
    )

    assert len(result) == 1
    assert result[0].title == "Respublika olimpiadasi"
    assert result[0].type == AchievementType.AWARD
    assert result[0].file_url == "https://signed.example/achievement/test.pdf"


@pytest.mark.asyncio
async def test_create_achievement_persists_new_record():
    student = build_user()
    db = DummyDB()

    result = await achievements_api.create_achievement(
        payload=AchievementCreate(
            title="Ilmiy maqola",
            type=AchievementType.PAPER,
            description="Scopus indexed",
            date=date(2025, 3, 10),
        ),
        current_user=student,
        db=db,
    )

    assert db.commits == 1
    assert len(db.added) == 1
    assert result.student_id == student.id
    assert result.title == "Ilmiy maqola"
    assert result.type == AchievementType.PAPER


@pytest.mark.asyncio
async def test_upload_achievement_file_updates_file_url(monkeypatch: pytest.MonkeyPatch):
    student = build_user()
    achievement = build_achievement(student_id=student.id)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=achievement)])

    upload_file = AsyncMock(return_value="achievement/test.pdf")
    monkeypatch.setattr(achievements_api, "upload_file", upload_file)
    monkeypatch.setattr(
        achievements_api,
        "build_file_download_url",
        lambda value: f"https://signed.example/{value}" if value else None,
    )

    file = UploadFile(filename="test.pdf", file=BytesIO(b"pdf-content"))

    result = await achievements_api.upload_achievement_file(
        achievement_id=achievement.id,
        current_user=student,
        db=db,
        file=file,
    )

    assert result["file_url"] == "https://signed.example/achievement/test.pdf"
    assert achievement.file_url == "achievement/test.pdf"
    assert db.commits == 1
    upload_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_achievement_updates_existing_record():
    student = build_user()
    achievement = build_achievement(student_id=student.id, title="Eski nom")
    db = DummyDB(execute_results=[_ExecuteResult(scalar=achievement)])

    result = await achievements_api.update_achievement(
        achievement_id=achievement.id,
        payload=AchievementUpdate(title="Yangi nom", description="Yangilandi"),
        current_user=student,
        db=db,
    )

    assert achievement.title == "Yangi nom"
    assert achievement.description == "Yangilandi"
    assert db.commits == 1
    assert result.title == "Yangi nom"


@pytest.mark.asyncio
async def test_delete_achievement_removes_existing_record():
    student = build_user()
    achievement = build_achievement(student_id=student.id)
    db = DummyDB(execute_results=[_ExecuteResult(scalar=achievement)])

    await achievements_api.delete_achievement(
        achievement_id=achievement.id,
        current_user=student,
        db=db,
    )

    assert db.deleted == [achievement]
    assert db.commits == 1
