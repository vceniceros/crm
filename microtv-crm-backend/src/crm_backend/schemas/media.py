"""Schemas for media processing status."""

from pydantic import BaseModel, ConfigDict


class MediaStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    original_url: str
    optimized_url: str | None = None
    thumbnail_url: str | None = None
    error: str | None = None
