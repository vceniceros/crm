import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

_CUIT_RE = re.compile(r"^\d{11}$")


class CreateApplicationRequest(BaseModel):
    company_type: Literal["transport_sub", "merchant_solo", "merchant_company"]
    company_name: str
    cuit: str
    contact_email: str
    contact_name: str
    parent_company_id: str | None = None
    documents: dict | None = None

    @field_validator("cuit")
    @classmethod
    def validate_cuit(cls, v: str) -> str:
        v = v.strip().replace("-", "").replace(" ", "")
        if not _CUIT_RE.match(v):
            raise ValueError("CUIT must be 11 digits (without dashes).")
        return v

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("company_name", "contact_name")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty.")
        return v


class UpdateApplicationRequest(BaseModel):
    """Allowed updates on a rejected application before re-submitting."""
    company_name: str | None = None
    cuit: str | None = None
    contact_email: str | None = None
    contact_name: str | None = None
    parent_company_id: str | None = None
    documents: dict | None = None

    @field_validator("cuit")
    @classmethod
    def validate_cuit(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().replace("-", "").replace(" ", "")
        if not _CUIT_RE.match(v):
            raise ValueError("CUIT must be 11 digits (without dashes).")
        return v

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else v


class MpVerifiedCallbackRequest(BaseModel):
    """Payload sent by pay.microtv.ar after successful MP OAuth."""
    mp_account_id: str


class RejectApplicationRequest(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Rejection reason cannot be empty.")
        return v


class ApplicationResponse(BaseModel):
    application_id: str
    company_type: str
    company_name: str
    cuit: str
    fiscal_type: str | None
    fiscal_verified: bool
    mp_verified: bool
    parent_company_id: str | None
    contact_email: str
    contact_name: str
    status: str
    rejection_reason: str | None
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    items: list[ApplicationResponse]
    total: int
    page: int
    size: int
