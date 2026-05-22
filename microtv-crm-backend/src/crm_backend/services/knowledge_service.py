"""Application service for the knowledge base module."""

from __future__ import annotations

import re
import unicodedata
from uuid import uuid4

from fastapi import UploadFile

from crm_backend.core.config import Settings
from crm_backend.core.exceptions import KnowledgeAccessDeniedError, KnowledgeNotFoundError, KnowledgeValidationError
from crm_backend.infrastructure.knowledge_media_storage import KnowledgeMediaStorageFacade
from crm_backend.infrastructure.task_media_storage import StoredTaskMedia
from crm_backend.models.knowledge import KnowledgeArticle, KnowledgeArticleAttachment
from crm_backend.models.settings import CrmCategory
from crm_backend.models.task_execution import TaskAttachmentType
from crm_backend.repositories.knowledge_repository import KnowledgeRepository
from crm_backend.schemas.knowledge import CreateKnowledgeArticleRequest, KnowledgeArticleFilterParams, UpdateKnowledgeArticleRequest
from crm_backend.services.auth_service import ResolvedCrmSession


class KnowledgeApplicationService:
    """Coordinate knowledge article use cases."""

    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        media_storage: KnowledgeMediaStorageFacade,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._media_storage = media_storage
        self._settings = settings

    def list_articles(self, actor: ResolvedCrmSession, filters: KnowledgeArticleFilterParams) -> list[KnowledgeArticle]:
        return self._repository.list(filters)

    def get_article(self, actor: ResolvedCrmSession, article_id: str) -> KnowledgeArticle:
        article = self._repository.get_by_id(article_id)
        if article is None:
            raise KnowledgeNotFoundError(f"Articulo {article_id} no encontrado.")
        return article

    def create_article(self, actor: ResolvedCrmSession, payload: CreateKnowledgeArticleRequest) -> KnowledgeArticle:
        title = payload.title.strip()
        if payload.status == "published" and len(title) < 3:
            raise KnowledgeValidationError("El titulo es obligatorio para articulos publicados.")
        article = KnowledgeArticle(
            article_id=str(uuid4()),
            title=title,
            slug=self._generate_slug(title),
            category_id=payload.category_id,
            content_md=payload.content_md,
            status=payload.status,
            created_by_user_id=actor.crm_user.crm_user_id,
            updated_by_user_id=actor.crm_user.crm_user_id,
            is_auto_draft=payload.is_auto_draft,
        )
        return self._repository.save(article)

    def update_article(self, actor: ResolvedCrmSession, article_id: str, payload: UpdateKnowledgeArticleRequest) -> KnowledgeArticle:
        article = self.get_article(actor, article_id)
        final_title = (payload.title if payload.title is not None else article.title).strip()
        final_status = payload.status or article.status
        if final_status == "published" and len(final_title) < 3:
            raise KnowledgeValidationError("El titulo es obligatorio para publicar articulos.")

        has_relevant_changes = any(
            [
                payload.title is not None and final_title != article.title,
                payload.category_id is not None and payload.category_id != article.category_id,
                payload.content_md is not None and payload.content_md != article.content_md,
                payload.status is not None and payload.status != article.status,
            ]
        )
        if has_relevant_changes:
            self._repository.save_version_snapshot(article, saved_by_user_id=actor.crm_user.crm_user_id)
        if payload.title is not None:
            article.title = final_title
            article.slug = self._generate_slug(final_title, exclude_id=article.article_id)
        if payload.content_md is not None:
            article.content_md = payload.content_md
        if payload.category_id is not None:
            article.category_id = payload.category_id
        if payload.status is not None:
            article.status = payload.status
            if payload.status == "published":
                article.is_auto_draft = False
        article.updated_by_user_id = actor.crm_user.crm_user_id
        return self._repository.save(article)

    def delete_article(self, actor: ResolvedCrmSession, article_id: str) -> None:
        if "admin" not in actor.role_keys:
            raise KnowledgeAccessDeniedError("Solo los administradores pueden eliminar articulos.")
        self._repository.soft_delete(self.get_article(actor, article_id))

    async def upload_attachment(self, actor: ResolvedCrmSession, article_id: str, upload_file: UploadFile) -> KnowledgeArticleAttachment:
        article = self.get_article(actor, article_id)
        stored = await self._media_storage.store(upload_file)
        attachment = KnowledgeArticleAttachment(
            attachment_id=str(uuid4()),
            article_id=article.article_id,
            file_type="image" if stored.attachment_type == TaskAttachmentType.PHOTO.value else "video",
            mime_type=stored.mime_type,
            original_filename=upload_file.filename or stored.file_name,
            stored_filename=stored.file_name,
            file_url=stored.file_url,
            storage_path=stored.storage_path,
            size_bytes=stored.file_size_bytes,
            created_by_user_id=actor.crm_user.crm_user_id,
        )
        return self._repository.save_attachment(attachment)

    def delete_attachment(self, actor: ResolvedCrmSession, article_id: str, attachment_id: str) -> None:
        article = self.get_article(actor, article_id)
        attachment = self._repository.get_attachment(attachment_id)
        if attachment is None or attachment.article_id != article.article_id:
            raise KnowledgeNotFoundError("Adjunto no encontrado.")
        is_admin = "admin" in actor.role_keys
        is_own_attachment = attachment.created_by_user_id == actor.crm_user.crm_user_id
        if not is_admin and not (is_own_attachment and article.status == "draft"):
            raise KnowledgeAccessDeniedError("Solo el administrador puede eliminar adjuntos de articulos publicados.")
        self._media_storage.delete(
            StoredTaskMedia(
                file_name=attachment.stored_filename,
                file_url=attachment.file_url,
                storage_path=attachment.storage_path,
                mime_type=attachment.mime_type,
                file_size_bytes=attachment.size_bytes or 0,
                attachment_type=TaskAttachmentType.PHOTO.value if attachment.file_type == "image" else TaskAttachmentType.VIDEO.value,
            )
        )
        self._repository.delete_attachment(attachment)

    def list_categories(self) -> list[CrmCategory]:
        return self._repository.list_categories()

    def _generate_slug(self, title: str, exclude_id: str | None = None) -> str:
        normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
        base_slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:240] or "sin-titulo"
        candidate = base_slug
        counter = 2
        while self._repository.slug_exists(candidate, exclude_id=exclude_id):
            suffix = f"-{counter}"
            candidate = f"{base_slug[: 255 - len(suffix)]}{suffix}"
            counter += 1
        return candidate
