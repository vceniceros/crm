"""Filesystem storage for knowledge base media."""

from __future__ import annotations

from fastapi import UploadFile

from crm_backend.core.config import Settings
from crm_backend.infrastructure.task_media_storage import (
    BaseTaskMediaUploadStrategy,
    StoredTaskMedia,
    TaskMediaUploadStrategy,
)
from crm_backend.models.task_execution import TaskAttachmentType


class ImageKnowledgeMediaStrategy(BaseTaskMediaUploadStrategy):
    attachment_type = TaskAttachmentType.PHOTO.value
    allowed_content_types = {"image/jpeg", "image/png", "image/webp"}
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}

    def _size_error_message(self) -> str:
        return "La imagen supera el limite permitido de 8 MB."

    def _type_error_message(self) -> str:
        return "Solo se admiten imagenes JPEG, PNG o WEBP."


class VideoKnowledgeMediaStrategy(BaseTaskMediaUploadStrategy):
    attachment_type = TaskAttachmentType.VIDEO.value
    allowed_content_types = {"video/mp4", "video/webm"}
    allowed_extensions = {"mp4", "webm"}

    def supports(self, upload: UploadFile) -> bool:
        return self._content_type_is_allowed(upload)

    def _content_type_is_allowed(self, upload: UploadFile) -> bool:
        return (upload.content_type or "").lower().split(";")[0].strip() in self.allowed_content_types

    def _size_error_message(self) -> str:
        return "El video supera el limite permitido de 128 MB."

    def _type_error_message(self) -> str:
        return "Solo se admiten videos MP4 o WEBM."


class KnowledgeMediaStorageFacade:
    """Resolve and persist knowledge media files."""

    def __init__(self, settings: Settings) -> None:
        self._strategies: list[TaskMediaUploadStrategy] = [
            ImageKnowledgeMediaStrategy(
                settings=settings,
                target_dir=settings.knowledge_images_dir,
                public_prefix=settings.knowledge_images_public_prefix,
                max_bytes=settings.knowledge_images_max_bytes,
            ),
            VideoKnowledgeMediaStrategy(
                settings=settings,
                target_dir=settings.knowledge_videos_dir,
                public_prefix=settings.knowledge_videos_public_prefix,
                max_bytes=settings.knowledge_videos_max_bytes,
            ),
        ]

    async def store(self, upload: UploadFile) -> StoredTaskMedia:
        content = await upload.read()
        return self._resolve_strategy(upload).store(upload, content)

    def delete(self, stored_media: StoredTaskMedia) -> None:
        self._resolve_strategy_from_attachment_type(stored_media.attachment_type).delete(stored_media)

    def _resolve_strategy(self, upload: UploadFile) -> TaskMediaUploadStrategy:
        strategy = next((item for item in self._strategies if item.supports(upload)), None)
        if strategy is None:
            from crm_backend.core.exceptions import InvalidTaskAttachmentError

            raise InvalidTaskAttachmentError("No existe una estrategia de carga para el archivo indicado.")
        return strategy

    def _resolve_strategy_from_attachment_type(self, attachment_type: str) -> TaskMediaUploadStrategy:
        strategy = next((item for item in self._strategies if item.attachment_type == attachment_type), None)
        if strategy is None:
            from crm_backend.core.exceptions import InvalidTaskAttachmentError

            raise InvalidTaskAttachmentError("No existe una estrategia de borrado para el adjunto indicado.")
        return strategy
