"""Schemas for authenticated self-service profile endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MeResponse(BaseModel):
    display_name: str | None
    email: str | None
    avatar_url: str | None
    roles: list[str] = Field(default_factory=list)


class MePatchRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: str | None = Field(default=None, min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("email must contain '@'.")
        return normalized

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
