"""Schemas for CRM client endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientLocationPayload(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address_label: str | None = Field(default=None, max_length=500)
    formatted_address: str | None = Field(default=None, max_length=2000)


class ClientLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latitude: float
    longitude: float
    address_label: str | None
    formatted_address: str | None


class ClientSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: str
    business_name: str
    tax_id: str
    email: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    location: ClientLocationResponse | None


class CreateClientRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    tax_id: str = Field(min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None, max_length=50)
    location: ClientLocationPayload | None = Field(default=None)


class UpdateClientRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    tax_id: str = Field(min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None, max_length=50)
    is_active: bool = True
    location: ClientLocationPayload | None = Field(default=None)