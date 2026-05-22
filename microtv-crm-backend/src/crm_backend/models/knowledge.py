"""Knowledge base ORM models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class KnowledgeCategory(Base):
    """Read-only article taxonomy."""

    __tablename__ = "knowledge_categories"

    article_category_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    articles: Mapped[list[KnowledgeArticle]] = relationship("KnowledgeArticle", back_populates="category", lazy="selectin")


class KnowledgeArticle(Base):
    """Markdown article with soft delete."""

    __tablename__ = "knowledge_articles"

    article_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("knowledge_categories.article_category_id"), nullable=True, index=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published", server_default="published", index=True)
    created_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=False, index=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_auto_draft: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    category: Mapped[KnowledgeCategory | None] = relationship("KnowledgeCategory", back_populates="articles", lazy="selectin")
    created_by: Mapped[object] = relationship("CrmUser", foreign_keys=[created_by_user_id], lazy="selectin")
    updated_by: Mapped[object | None] = relationship("CrmUser", foreign_keys=[updated_by_user_id], lazy="selectin")
    attachments: Mapped[list[KnowledgeArticleAttachment]] = relationship(
        "KnowledgeArticleAttachment",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="KnowledgeArticleAttachment.created_at",
        lazy="selectin",
    )
    versions: Mapped[list[KnowledgeArticleVersion]] = relationship(
        "KnowledgeArticleVersion",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="KnowledgeArticleVersion.version_number",
        lazy="selectin",
    )


class KnowledgeArticleVersion(Base):
    """Immutable snapshot saved before an article update."""

    __tablename__ = "knowledge_article_versions"
    __table_args__ = (UniqueConstraint("article_id", "version_number", name="uq_article_version"),)

    version_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    article_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("knowledge_articles.article_id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    saved_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    article: Mapped[KnowledgeArticle] = relationship("KnowledgeArticle", back_populates="versions")


class KnowledgeArticleAttachment(Base):
    """Image or video attached to a knowledge article."""

    __tablename__ = "knowledge_article_attachments"

    attachment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    article_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("knowledge_articles.article_id"), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    article: Mapped[KnowledgeArticle] = relationship("KnowledgeArticle", back_populates="attachments")
