"""Filesystem storage for public task pre-form image uploads."""

from __future__ import annotations

from dataclasses import dataclass
import errno
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from crm_backend.core.config import Settings
from crm_backend.core.exceptions import ApplicationError


_logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StoredPreFormMedia:
    file_name: str
    file_url: str
    mime_type: str
    file_size_bytes: int


class PreFormMediaStorageFacade:
    """Persist public pre-form image uploads with lightweight content validation."""

    _allowed_mime_by_signature = {
        "image/jpeg": ("jpg", "jpeg"),
        "image/png": ("png",),
        "image/webp": ("webp",),
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._target_dir = settings.pre_form_images_dir
        self._public_prefix = settings.pre_form_images_public_prefix.rstrip("/")
        self._max_bytes = settings.pre_form_images_max_bytes

    async def store(self, upload: UploadFile) -> StoredPreFormMedia:
        content = await upload.read()
        mime_type = self._detect_image_type(content)
        self._validate(upload, content, mime_type)

        suffix = self._resolve_suffix(upload, mime_type)
        file_name = f"{uuid4().hex}.{suffix}"
        destination = self._target_dir / file_name
        try:
            self._target_dir.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        except OSError as exc:
            _logger.exception("Pre-form media storage write failed. destination=%s", destination)
            raise ApplicationError("pre_form_attachment_storage_error", self._storage_error_message(exc), 422) from exc

        return StoredPreFormMedia(
            file_name=file_name,
            file_url=f"{self._public_prefix}/{file_name}",
            mime_type=mime_type,
            file_size_bytes=len(content),
        )

    def _validate(self, upload: UploadFile, content: bytes, detected_mime_type: str | None) -> None:
        if not content:
            raise ApplicationError("pre_form_attachment_empty", "El archivo enviado esta vacio.", 422)
        if len(content) > self._max_bytes:
            raise ApplicationError("pre_form_attachment_too_large", "La imagen supera el limite permitido de 8 MB.", 413)
        if detected_mime_type is None:
            raise ApplicationError("pre_form_attachment_invalid_type", "Solo se admiten imagenes JPEG, PNG o WEBP.", 415)

        header_mime_type = (upload.content_type or "").split(";")[0].strip().lower()
        if header_mime_type and header_mime_type not in self._allowed_mime_by_signature:
            raise ApplicationError("pre_form_attachment_invalid_type", "Solo se admiten imagenes JPEG, PNG o WEBP.", 415)

    def _detect_image_type(self, content: bytes) -> str | None:
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if len(content) >= 12 and content[0:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "image/webp"
        return None

    def _resolve_suffix(self, upload: UploadFile, mime_type: str) -> str:
        allowed_extensions = self._allowed_mime_by_signature[mime_type]
        if upload.filename and "." in upload.filename:
            extension = upload.filename.lower().rsplit(".", 1)[1]
            if extension in allowed_extensions:
                return extension
        return allowed_extensions[0]

    def _storage_error_message(self, exc: OSError) -> str:
        error_number = getattr(exc, "errno", None)
        if error_number in {errno.EACCES, errno.EPERM}:
            return "No se pudo acceder al almacenamiento de formularios: permisos insuficientes."
        if error_number == errno.EROFS:
            return "No se pudo acceder al almacenamiento de formularios: filesystem de solo lectura."
        if error_number == errno.ENOSPC:
            return "No se pudo acceder al almacenamiento de formularios: no hay espacio disponible."
        return "No se pudo acceder al almacenamiento de formularios."
