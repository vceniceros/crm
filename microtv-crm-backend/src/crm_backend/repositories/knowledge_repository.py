"""Repository for knowledge base data."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from crm_backend.models.knowledge import (
    KnowledgeArticle,
    KnowledgeArticleAttachment,
    KnowledgeArticleVersion,
    KnowledgeCategory,
)
from crm_backend.schemas.knowledge import KnowledgeArticleFilterParams


class KnowledgeRepository:
    """Persistence operations for knowledge base articles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, filters: KnowledgeArticleFilterParams) -> list[KnowledgeArticle]:
        statement = select(KnowledgeArticle).where(KnowledgeArticle.deleted_at.is_(None)).order_by(KnowledgeArticle.updated_at.desc())
        if filters.status is not None:
            statement = statement.where(KnowledgeArticle.status == filters.status)
        if filters.category_id:
            statement = statement.where(KnowledgeArticle.category_id == filters.category_id)
        if filters.search:
            term = f"%{filters.search.strip()}%"
            statement = statement.outerjoin(KnowledgeArticle.category).where(
                or_(
                    KnowledgeArticle.title.ilike(term),
                    KnowledgeArticle.content_md.ilike(term),
                    KnowledgeCategory.name.ilike(term),
                )
            )
        return list(self._session.scalars(statement).unique())

    def get_by_id(self, article_id: str) -> KnowledgeArticle | None:
        return self._session.scalar(
            select(KnowledgeArticle).where(KnowledgeArticle.article_id == article_id, KnowledgeArticle.deleted_at.is_(None))
        )

    def get_by_slug(self, slug: str) -> KnowledgeArticle | None:
        return self._session.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == slug, KnowledgeArticle.deleted_at.is_(None)))

    def save(self, article: KnowledgeArticle) -> KnowledgeArticle:
        self._session.add(article)
        self._session.commit()
        self._session.refresh(article)
        return self.get_by_id(article.article_id) or article

    def soft_delete(self, article: KnowledgeArticle) -> None:
        article.deleted_at = func.now()
        self._session.commit()

    def list_categories(self) -> list[KnowledgeCategory]:
        return list(self._session.scalars(select(KnowledgeCategory).order_by(KnowledgeCategory.name)))

    def save_attachment(self, attachment: KnowledgeArticleAttachment) -> KnowledgeArticleAttachment:
        self._session.add(attachment)
        self._session.commit()
        self._session.refresh(attachment)
        return attachment

    def get_attachment(self, attachment_id: str) -> KnowledgeArticleAttachment | None:
        return self._session.get(KnowledgeArticleAttachment, attachment_id)

    def slug_exists(self, slug: str, exclude_id: str | None = None) -> bool:
        statement = select(KnowledgeArticle.article_id).where(KnowledgeArticle.slug == slug, KnowledgeArticle.deleted_at.is_(None))
        if exclude_id is not None:
            statement = statement.where(KnowledgeArticle.article_id != exclude_id)
        return self._session.scalar(statement) is not None

    def save_version_snapshot(self, article: KnowledgeArticle, saved_by_user_id: str) -> None:
        next_version = (
            self._session.scalar(
                select(func.coalesce(func.max(KnowledgeArticleVersion.version_number), 0) + 1).where(
                    KnowledgeArticleVersion.article_id == article.article_id
                )
            )
            or 1
        )
        self._session.add(
            KnowledgeArticleVersion(
                article_id=article.article_id,
                version_number=next_version,
                title=article.title,
                category_id=article.category_id,
                content_md=article.content_md,
                status=article.status,
                saved_by_user_id=saved_by_user_id,
            )
        )
        self._session.flush()

    def delete_attachment(self, attachment: KnowledgeArticleAttachment) -> None:
        self._session.delete(attachment)
        self._session.commit()
