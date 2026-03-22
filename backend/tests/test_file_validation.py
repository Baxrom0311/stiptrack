from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock
import zipfile

import pytest
from fastapi import HTTPException, UploadFile, status

import app.services.file_service as file_service
from app.services.file_service import (
    FILE_VALIDATION_RULES,
    build_bucket_public_read_policy,
    build_file_download_url,
    ensure_bucket_policy,
    normalize_stored_file_ref,
    upload_file,
)


@pytest.mark.asyncio
async def test_nizom_upload_rejects_non_pdf_mime():
    file = UploadFile(filename="nizom.png", file=BytesIO(b"png-content"), headers={"content-type": "image/png"})

    with pytest.raises(HTTPException) as exc_info:
        await upload_file(file=file, folder="nizom")

    assert exc_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert ".pdf" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_achievement_upload_rejects_svg_extension():
    file = UploadFile(
        filename="certificate.svg",
        file=BytesIO(b"<svg></svg>"),
        headers={"content-type": "image/svg+xml"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await upload_file(file=file, folder="achievement")

    assert exc_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert ".webp" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_appeal_upload_rejects_oversized_file():
    max_size = FILE_VALIDATION_RULES["appeal"].max_size
    file = UploadFile(
        filename="appeal.pdf",
        file=BytesIO(b"a" * (max_size + 1)),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await upload_file(file=file, folder="appeal")

    assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "10MB" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_application_upload_rejects_empty_file():
    file = UploadFile(
        filename="application.pdf",
        file=BytesIO(b""),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await upload_file(file=file, folder="application")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Bo'sh fayl" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_upload_file_returns_object_name_for_valid_minio_upload(monkeypatch: pytest.MonkeyPatch):
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    stored_objects: list[str] = []

    class FakeMinioClient:
        def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str) -> None:
            assert bucket_name == file_service.settings.minio_bucket
            assert length == len(pdf_bytes)
            assert content_type == "application/pdf"
            stored_objects.append(object_name)

    monkeypatch.setattr(file_service, "ensure_bucket_exists", AsyncMock(return_value=True))
    monkeypatch.setattr(file_service, "get_minio_client", lambda: FakeMinioClient())

    file = UploadFile(
        filename="achievement.pdf",
        file=BytesIO(pdf_bytes),
        headers={"content-type": "application/pdf"},
    )

    object_name = await upload_file(file=file, folder="achievement")

    assert object_name.startswith("achievement/")
    assert object_name.endswith(".pdf")
    assert "://" not in object_name
    assert stored_objects == [object_name]


def test_build_file_download_url_returns_presigned_url(monkeypatch: pytest.MonkeyPatch):
    class FakePresignClient:
        def presigned_get_object(self, bucket_name: str, object_name: str, expires):
            assert bucket_name == file_service.settings.minio_bucket
            assert object_name == "achievement/test.pdf"
            assert int(expires.total_seconds()) == file_service.settings.minio_presigned_expiry_seconds
            return f"https://files.example.com/{bucket_name}/{object_name}?token=signed"

    monkeypatch.setattr(file_service, "get_presign_minio_client", lambda: FakePresignClient())

    result = build_file_download_url("achievement/test.pdf")

    assert result == "https://files.example.com/stipendiya-files/achievement/test.pdf?token=signed"


def test_build_bucket_public_read_policy_returns_empty_when_no_prefixes():
    assert build_bucket_public_read_policy(bucket_name="stipendiya-files", public_read_prefixes=[]) == ""


def test_build_bucket_public_read_policy_scopes_public_read_to_prefixes():
    policy = build_bucket_public_read_policy(
        bucket_name="stipendiya-files",
        public_read_prefixes=["nizom", "/public/results/"],
    )

    assert '"Action":["s3:GetObject"]' in policy
    assert '"arn:aws:s3:::stipendiya-files/nizom/*"' in policy
    assert '"arn:aws:s3:::stipendiya-files/public/results/*"' in policy
    assert '"arn:aws:s3:::stipendiya-files//*"' not in policy


def test_build_file_download_url_adds_public_path_prefix(monkeypatch: pytest.MonkeyPatch):
    class FakePresignClient:
        def presigned_get_object(self, bucket_name: str, object_name: str, expires):
            return f"https://files.example.com/{bucket_name}/{object_name}?token=signed"

    monkeypatch.setattr(file_service, "get_presign_minio_client", lambda: FakePresignClient())
    monkeypatch.setattr(file_service.settings, "minio_public_path_prefix", "/files")

    result = build_file_download_url("achievement/test.pdf")

    assert result == "https://files.example.com/files/stipendiya-files/achievement/test.pdf?token=signed"


@pytest.mark.asyncio
async def test_ensure_bucket_policy_clears_public_policy_when_no_prefixes(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    class FakeMinioClient:
        def get_bucket_policy(self, bucket_name: str) -> str:
            assert bucket_name == file_service.settings.minio_bucket
            return '{"Version":"2012-10-17","Statement":[{"Effect":"Allow"}]}'

        def set_bucket_policy(self, bucket_name: str, policy: str) -> None:
            assert bucket_name == file_service.settings.minio_bucket
            calls.append(policy)

    monkeypatch.setattr(file_service, "get_minio_client", lambda: FakeMinioClient())
    monkeypatch.setattr(file_service.settings, "minio_public_read_prefixes", [])

    result = await ensure_bucket_policy()

    assert result is True
    assert calls == [""]


@pytest.mark.asyncio
async def test_ensure_bucket_policy_applies_prefix_scoped_policy(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    class FakeMinioClient:
        def get_bucket_policy(self, bucket_name: str) -> str:
            raise file_service.S3Error(
                code="NoSuchBucketPolicy",
                message="missing",
                resource=bucket_name,
                request_id="req-1",
                host_id="host-1",
                response=None,
            )

        def set_bucket_policy(self, bucket_name: str, policy: str) -> None:
            assert bucket_name == file_service.settings.minio_bucket
            calls.append(policy)

    monkeypatch.setattr(file_service, "get_minio_client", lambda: FakeMinioClient())
    monkeypatch.setattr(file_service.settings, "minio_public_read_prefixes", ["nizom", "public/results"])

    result = await ensure_bucket_policy()

    assert result is True
    assert len(calls) == 1
    assert '"arn:aws:s3:::stipendiya-files/nizom/*"' in calls[0]
    assert '"arn:aws:s3:::stipendiya-files/public/results/*"' in calls[0]


def test_normalize_stored_file_ref_extracts_object_name_from_presigned_url():
    presigned = "http://localhost:9000/stipendiya-files/achievement/test.pdf?X-Amz-Signature=abc"

    result = normalize_stored_file_ref(presigned)

    assert result == "achievement/test.pdf"


def test_normalize_stored_file_ref_extracts_object_name_from_prefixed_presigned_url(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(file_service.settings, "minio_public_path_prefix", "/files")
    presigned = "https://example.com/files/stipendiya-files/achievement/test.pdf?X-Amz-Signature=abc"

    result = normalize_stored_file_ref(presigned)

    assert result == "achievement/test.pdf"


@pytest.mark.asyncio
async def test_nizom_upload_rejects_fake_pdf_payload():
    file = UploadFile(
        filename="nizom.pdf",
        file=BytesIO(b"this-is-not-a-real-pdf"),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await upload_file(file=file, folder="nizom")

    assert exc_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert "mazmuni tekshiruvdan o'tmadi" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_application_upload_accepts_real_docx_signature(monkeypatch: pytest.MonkeyPatch):
    stored_objects: list[str] = []

    class FakeMinioClient:
        def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str) -> None:
            assert bucket_name == file_service.settings.minio_bucket
            assert content_type == file_service.DOCX_MIME
            stored_objects.append(object_name)

    monkeypatch.setattr(file_service, "ensure_bucket_exists", AsyncMock(return_value=True))
    monkeypatch.setattr(file_service, "get_minio_client", lambda: FakeMinioClient())

    docx_buffer = BytesIO()
    with zipfile.ZipFile(docx_buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", "<w:document></w:document>")

    file = UploadFile(
        filename="application.docx",
        file=BytesIO(docx_buffer.getvalue()),
        headers={"content-type": file_service.DOCX_MIME},
    )

    object_name = await upload_file(file=file, folder="application")

    assert object_name.startswith("application/")
    assert object_name.endswith(".docx")
    assert stored_objects == [object_name]
