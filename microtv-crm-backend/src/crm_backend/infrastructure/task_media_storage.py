"""Filesystem storage for task media uploads using Facade + Strategy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from crm_backend.core.config import Settings
from crm_backend.core.exceptions import InvalidTaskAttachmentError
from crm_backend.models.task_execution import TaskAttachmentType


@dataclass(slots=True)
class StoredTaskMedia:
    file_name: str
    file_url: str
    storage_path: str
    mime_type: str
    file_size_bytes: int
    attachment_type: str


class TaskMediaUploadStrategy(Protocol):
    attachment_type: str

    def supports(self, upload: UploadFile) -> bool:
        ...

    def store(self, upload: UploadFile, content: bytes) -> StoredTaskMedia:
        ...

    def delete(self, stored_media: StoredTaskMedia) -> None:
        ...


class BaseTaskMediaUploadStrategy:
    attachment_type: str
    allowed_content_types: set[str]
    allowed_extensions: set[str]

    def __init__(self, *, target_dir: Path, public_prefix: str, max_bytes: int) -> None:
        self._target_dir = target_dir
        self._public_prefix = public_prefix.rstrip("/")
        self._max_bytes = max_bytes
        self._target_dir.mkdir(parents=True, exist_ok=True)

    def supports(self, upload: UploadFile) -> bool:
        return self._content_type_is_allowed(upload) or self._extension_is_allowed(upload.filename)

    def store(self, upload: UploadFile, content: bytes) -> StoredTaskMedia:
        self._validate(upload, content)
        suffix = self._resolve_suffix(upload)
        file_name = f"{uuid4().hex}{suffix}"
        destination = self._target_dir / file_name
        destination.write_bytes(content)

        return StoredTaskMedia(
            file_name=file_name,
            file_url=f"{self._public_prefix}/{file_name}",
            storage_path=str(Path("public") / Path(self._public_prefix.lstrip("/")) / file_name).replace("\\", "/"),
            mime_type=upload.content_type or self._default_mime_type(),
            file_size_bytes=len(content),
            attachment_type=self.attachment_type,
        )

    def delete(self, stored_media: StoredTaskMedia) -> None:
        candidate = self._target_dir / stored_media.file_name
        if candidate.exists():
            candidate.unlink()

    def _validate(self, upload: UploadFile, content: bytes) -> None:
        if not content:
            raise InvalidTaskAttachmentError("El archivo multimedia enviado está vacío.")
        if len(content) > self._max_bytes:
            raise InvalidTaskAttachmentError(self._size_error_message())
        if not self.supports(upload):
            raise InvalidTaskAttachmentError(self._type_error_message())

    def _content_type_is_allowed(self, upload: UploadFile) -> bool:
        return (upload.content_type or "").lower() in self.allowed_content_types

    def _extension_is_allowed(self, file_name: str | None) -> bool:
        if not file_name or "." not in file_name:
            return False
        return file_name.lower().rsplit(".", 1)[1] in self.allowed_extensions

    def _resolve_suffix(self, upload: UploadFile) -> str:
        if upload.filename and "." in upload.filename:
            extension = upload.filename.lower().rsplit(".", 1)[1]
            if extension in self.allowed_extensions:
                return f".{extension}"

        default_extension = next(iter(self.allowed_extensions), "bin")
        return f".{default_extension}"

    def _default_mime_type(self) -> str:
        return next(iter(self.allowed_content_types), "application/octet-stream")

    def _size_error_message(self) -> str:
        raise NotImplementedError

    def _type_error_message(self) -> str:
        raise NotImplementedError


class ImageTaskMediaUploadStrategy(BaseTaskMediaUploadStrategy):
    attachment_type = TaskAttachmentType.PHOTO.value
    allowed_content_types = {"image/jpeg", "image/png", "image/webp"}
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}

    def _size_error_message(self) -> str:
        return "La imagen supera el límite permitido de 8 MB."

    def _type_error_message(self) -> str:
        return "Solo se admiten imágenes JPEG, PNG o WEBP."


class VideoTaskMediaUploadStrategy(BaseTaskMediaUploadStrategy):
    attachment_type = TaskAttachmentType.VIDEO.value
    allowed_content_types = {"video/mp4", "video/webm", "video/quicktime"}
    allowed_extensions = {"mp4", "webm", "mov"}

    def _size_error_message(self) -> str:
        return "El video supera el límite permitido de 128 MB."

    def _type_error_message(self) -> str:
        return "Solo se admiten videos MP4, WEBM o MOV."


class TaskMediaStorageFacade:
    """Resolve the upload strategy and persist task media files."""

    def __init__(self, settings: Settings) -> None:
        self._strategies: list[TaskMediaUploadStrategy] = [
            ImageTaskMediaUploadStrategy(
                target_dir=settings.task_images_dir,
                public_prefix="/images/task",
                max_bytes=settings.task_images_max_bytes,
            ),
            VideoTaskMediaUploadStrategy(
                target_dir=settings.task_videos_dir,
                public_prefix="/videos/task",
                max_bytes=settings.task_videos_max_bytes,
            ),
        ]

    async def store(self, upload: UploadFile) -> StoredTaskMedia:
        content = await upload.read()
        return self._resolve_strategy(upload).store(upload, content)

    def delete(self, stored_media: StoredTaskMedia) -> None:
        self._resolve_strategy_from_attachment_type(stored_media.attachment_type).delete(stored_media)

    def delete_from_persisted_values(
        self,
        *,
        attachment_type: str,
        file_name: str,
        file_url: str,
        mime_type: str | None,
        file_size_bytes: int | None,
    ) -> None:
        self.delete(
            StoredTaskMedia(
                file_name=file_name,
                file_url=file_url,
                storage_path=str(Path("public") / Path(file_url.lstrip("/"))).replace("\\", "/"),
                mime_type=mime_type or "application/octet-stream",
                file_size_bytes=file_size_bytes or 0,
                attachment_type=attachment_type,
            )
        )

    def _resolve_strategy(self, upload: UploadFile) -> TaskMediaUploadStrategy:
        strategy = next((item for item in self._strategies if item.supports(upload)), None)
        if strategy is None:
            raise InvalidTaskAttachmentError("No existe una estrategia de carga para el archivo indicado.")
        return strategy

    def _resolve_strategy_from_attachment_type(self, attachment_type: str) -> TaskMediaUploadStrategy:
        strategy = next((item for item in self._strategies if item.attachment_type == attachment_type), None)
        if strategy is None:
            raise InvalidTaskAttachmentError("No existe una estrategia de borrado para el adjunto indicado.")
        return strategy