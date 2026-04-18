"""Schemas for CRM user lookup endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CrmUserOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    crm_user_id: str
    display_name: str | None
    email: str | None