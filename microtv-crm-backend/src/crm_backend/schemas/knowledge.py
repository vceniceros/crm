"""Pydantic schemas for the knowledge base module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KnowledgeCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_category_id: str
    name: str
    slug: str
    description: str | None = None


class KnowledgeAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attachment_id: str
    file_type: str
    mime_type: str
    original_filename: str
    file_url: str
    size_bytes: int | None = None
    created_at: datetime


class KnowledgeArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_id: str
    title: str
    slug: str
    category: KnowledgeCategoryResponse | None = None
    status: str
    excerpt: str | None = None
    created_by_display_name: str
    created_at: datetime
    updated_at: datetime


class KnowledgeArticleDetail(KnowledgeArticleListItem):
    content_md: str
    attachments: list[KnowledgeAttachmentResponse] = []


class CreateKnowledgeArticleRequest(BaseModel):
    title: str = Field(default="", max_length=255)
    category_id: str | None = None
    content_md: str = Field(default="")
    status: Literal["draft", "published"] = "published"
    is_auto_draft: bool = False

    @model_validator(mode="after")
    def validate_title_for_published(self) -> "CreateKnowledgeArticleRequest":
        if not self.is_auto_draft and self.status == "published" and len(self.title.strip()) < 3:
            raise ValueError("El titulo es obligatorio para articulos publicados (minimo 3 caracteres).")
        return self


class UpdateKnowledgeArticleRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    category_id: str | None = None
    content_md: str | None = None
    status: Literal["draft", "published"] | None = None

    @model_validator(mode="after")
    def validate_title_for_published(self) -> "UpdateKnowledgeArticleRequest":
        if self.status == "published" and self.title is not None and len(self.title.strip()) < 3:
            raise ValueError("El titulo es obligatorio para publicar articulos.")
        return self


class KnowledgeArticleFilterParams(BaseModel):
    search: str | None = None
    category_id: str | None = None
    status: Literal["draft", "published"] | None = "published"
