from __future__ import annotations

import asyncio
import io
import json
import uuid
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlparse, urlunparse

from fastapi import HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error

from app.core.config import settings


@dataclass(frozen=True)
class FileValidationRule:
    allowed_content_types: tuple[str, ...]
    allowed_extensions: tuple[str, ...]
    max_size: int
    label: str


PDF_MIME = "application/pdf"
DOC_MIME = "application/msword"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
JPEG_MIME = "image/jpeg"
PNG_MIME = "image/png"
WEBP_MIME = "image/webp"

TEN_MB = 10 * 1024 * 1024
TWENTY_MB = 20 * 1024 * 1024

DEFAULT_FILE_RULE = FileValidationRule(
    allowed_content_types=(PDF_MIME, JPEG_MIME, PNG_MIME, WEBP_MIME, DOC_MIME, DOCX_MIME),
    allowed_extensions=("pdf", "jpg", "jpeg", "png", "webp", "doc", "docx"),
    max_size=TWENTY_MB,
    label="umumiy fayl",
)

FILE_VALIDATION_RULES: dict[str, FileValidationRule] = {
    "nizom": FileValidationRule(
        allowed_content_types=(PDF_MIME,),
        allowed_extensions=("pdf",),
        max_size=TEN_MB,
        label="nizom fayli",
    ),
    "achievement": FileValidationRule(
        allowed_content_types=(PDF_MIME, JPEG_MIME, PNG_MIME, WEBP_MIME),
        allowed_extensions=("pdf", "jpg", "jpeg", "png", "webp"),
        max_size=TEN_MB,
        label="yutuq fayli",
    ),
    "application": DEFAULT_FILE_RULE,
    "appeal": FileValidationRule(
        allowed_content_types=DEFAULT_FILE_RULE.allowed_content_types,
        allowed_extensions=DEFAULT_FILE_RULE.allowed_extensions,
        max_size=TEN_MB,
        label="apellyatsiya fayli",
    ),
    "uploads": DEFAULT_FILE_RULE,
}


_minio_client: Minio | None = None
_presign_minio_client: Minio | None = None


def _create_minio_client(endpoint: str) -> Minio:
    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )


def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = _create_minio_client(settings.minio_endpoint)
    return _minio_client


def get_presign_minio_client() -> Minio:
    global _presign_minio_client
    if _presign_minio_client is None:
        _presign_minio_client = _create_minio_client(settings.minio_public_endpoint or settings.minio_endpoint)
    return _presign_minio_client


def _normalized_public_path_prefix() -> str:
    prefix = settings.minio_public_path_prefix.strip()
    if not prefix:
        return ""
    return "/" + prefix.strip("/")


def _apply_public_path_prefix(url: str) -> str:
    prefix = _normalized_public_path_prefix()
    if not prefix:
        return url

    parsed = urlparse(url)
    path = parsed.path or "/"
    if path.startswith(f"{prefix}/") or path == prefix:
        return url

    prefixed_path = f"{prefix}{path if path.startswith('/') else f'/{path}'}"
    return urlunparse(parsed._replace(path=prefixed_path))


def _normalized_public_read_prefixes(prefixes: list[str] | None = None) -> tuple[str, ...]:
    raw_prefixes = prefixes if prefixes is not None else settings.minio_public_read_prefixes
    normalized: list[str] = []
    for prefix in raw_prefixes:
        cleaned = prefix.strip().strip("/")
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return tuple(normalized)


def _canonicalize_bucket_policy(policy: str) -> str:
    normalized = policy.strip()
    if not normalized:
        return ""

    try:
        return json.dumps(json.loads(normalized), sort_keys=True, separators=(",", ":"))
    except json.JSONDecodeError:
        return normalized


def build_bucket_public_read_policy(
    bucket_name: str | None = None,
    public_read_prefixes: list[str] | None = None,
) -> str:
    bucket = bucket_name or settings.minio_bucket
    prefixes = _normalized_public_read_prefixes(public_read_prefixes)
    if not prefixes:
        return ""

    resources = [f"arn:aws:s3:::{bucket}/{prefix}/*" for prefix in prefixes]
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowAnonymousReadForExplicitPrefixes",
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": resources,
            }
        ],
    }
    return json.dumps(policy, sort_keys=True, separators=(",", ":"))


async def ensure_bucket_exists(bucket_name: str | None = None) -> bool:
    bucket = bucket_name or settings.minio_bucket

    def _ensure() -> bool:
        client = get_minio_client()
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        return True

    try:
        return await asyncio.to_thread(_ensure)
    except S3Error:
        return False


async def ensure_bucket_policy(bucket_name: str | None = None) -> bool:
    bucket = bucket_name or settings.minio_bucket
    desired_policy = build_bucket_public_read_policy(bucket_name=bucket)

    def _ensure() -> bool:
        client = get_minio_client()
        current_policy = ""
        try:
            current_policy = client.get_bucket_policy(bucket)
        except S3Error as exc:
            if exc.code != "NoSuchBucketPolicy":
                raise

        if _canonicalize_bucket_policy(current_policy) == _canonicalize_bucket_policy(desired_policy):
            return True

        client.set_bucket_policy(bucket, desired_policy)
        return True

    try:
        return await asyncio.to_thread(_ensure)
    except S3Error:
        return False


async def ping_minio() -> bool:
    def _ping() -> bool:
        client = get_minio_client()
        client.list_buckets()
        return True

    try:
        return await asyncio.to_thread(_ping)
    except Exception:
        return False


def get_file_validation_rule(folder: str) -> FileValidationRule:
    return FILE_VALIDATION_RULES.get(folder, DEFAULT_FILE_RULE)


def _format_allowed_extensions(rule: FileValidationRule) -> str:
    return ", ".join(f".{extension}" for extension in rule.allowed_extensions)


def _get_file_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _matches_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF-")


def _matches_jpeg(content: bytes) -> bool:
    return content.startswith(b"\xff\xd8\xff")


def _matches_png(content: bytes) -> bool:
    return content.startswith(b"\x89PNG\r\n\x1a\n")


def _matches_webp(content: bytes) -> bool:
    return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"


def _matches_doc(content: bytes) -> bool:
    return content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")


def _matches_docx(content: bytes) -> bool:
    if not content.startswith(b"PK\x03\x04"):
        return False

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return False

    return "[Content_Types].xml" in names and any(name.startswith("word/") for name in names)


def detect_content_type_from_bytes(content: bytes) -> str | None:
    detectors: tuple[tuple[str, Callable[[bytes], bool]], ...] = (
        (PDF_MIME, _matches_pdf),
        (JPEG_MIME, _matches_jpeg),
        (PNG_MIME, _matches_png),
        (WEBP_MIME, _matches_webp),
        (DOC_MIME, _matches_doc),
        (DOCX_MIME, _matches_docx),
    )

    for mime, matcher in detectors:
        if matcher(content):
            return mime

    return None


def validate_upload_file(file: UploadFile, content: bytes, folder: str) -> None:
    rule = get_file_validation_rule(folder)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bo'sh fayl yuklab bo'lmaydi",
        )

    if len(content) > rule.max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{rule.label.capitalize()} hajmi {rule.max_size // 1024 // 1024}MB dan oshmasligi kerak",
        )

    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in rule.allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{rule.label.capitalize()} uchun faqat {_format_allowed_extensions(rule)} turlari qabul qilinadi",
        )

    extension = _get_file_extension(file.filename)
    if extension not in rule.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{rule.label.capitalize()} nomi {_format_allowed_extensions(rule)} formatlaridan biri bilan tugashi kerak",
        )

    detected_content_type = detect_content_type_from_bytes(content)
    if detected_content_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{rule.label.capitalize()} mazmuni tekshiruvdan o'tmadi",
        )

    if detected_content_type not in rule.allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{rule.label.capitalize()} mazmuni ruxsat etilgan formatga mos emas",
        )

    if detected_content_type != content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{rule.label.capitalize()} MIME turi fayl mazmuniga mos emas",
        )


def extract_object_name(file_ref: str | None) -> str | None:
    if file_ref is None:
        return None

    normalized = file_ref.strip()
    if not normalized:
        return None

    bucket_prefix = f"{settings.minio_bucket}/"
    if "://" not in normalized:
        path = normalized.lstrip("/")
        if path.startswith(bucket_prefix):
            return path[len(bucket_prefix) :]
        return path

    parsed = urlparse(normalized)
    path = parsed.path or ""
    public_prefix = _normalized_public_path_prefix()
    if public_prefix and path.startswith(f"{public_prefix}/"):
        path = path[len(public_prefix) :]
    path = path.lstrip("/")
    if path.startswith(bucket_prefix):
        return path[len(bucket_prefix) :]
    return None


def normalize_stored_file_ref(file_ref: str | None) -> str | None:
    object_name = extract_object_name(file_ref)
    if object_name:
        return object_name
    return file_ref


def build_file_download_url(file_ref: str | None) -> str | None:
    if file_ref is None:
        return None

    object_name = extract_object_name(file_ref)
    if object_name is None:
        return file_ref

    try:
        presigned_url = get_presign_minio_client().presigned_get_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            expires=timedelta(seconds=settings.minio_presigned_expiry_seconds),
        )
        return _apply_public_path_prefix(presigned_url)
    except Exception:
        protocol = "https" if settings.minio_use_ssl else "http"
        endpoint = settings.minio_public_endpoint or settings.minio_endpoint
        prefix = _normalized_public_path_prefix()
        return f"{protocol}://{endpoint}{prefix}/{settings.minio_bucket}/{object_name}"


async def upload_file(file: UploadFile, folder: str = "uploads") -> str:
    content = await file.read()
    validate_upload_file(file=file, content=content, folder=folder)
    rule = get_file_validation_rule(folder)
    content_type = (file.content_type or "application/octet-stream").lower()

    filename = file.filename or "file.bin"
    ext = _get_file_extension(filename) or rule.allowed_extensions[0]
    object_name = f"{folder}/{uuid.uuid4()}.{ext}"

    await ensure_bucket_exists()

    def _put() -> None:
        get_minio_client().put_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            data=io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )

    try:
        await asyncio.to_thread(_put)
    except S3Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Faylni saqlashda xatolik yuz berdi",
        ) from exc

    return object_name


async def delete_file(file_ref: str) -> bool:
    object_name = extract_object_name(file_ref)
    if not object_name:
        return False

    def _delete() -> bool:
        get_minio_client().remove_object(settings.minio_bucket, object_name)
        return True

    try:
        return await asyncio.to_thread(_delete)
    except S3Error:
        return False
