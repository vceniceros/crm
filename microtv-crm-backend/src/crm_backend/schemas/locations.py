"""Schemas for reusable location persistence endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class CreateLocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address_label: str | None = Field(default=None, max_length=500)
    formatted_address: str | None = Field(default=None, max_length=2000)


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: str
    latitude: float
    longitude: float
    address_label: str | None
    formatted_address: str | None
