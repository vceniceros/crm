import re

from pydantic import BaseModel, Field, field_validator

_COMPANY_ID_RE = re.compile(r"^[a-zA-Z0-9\-]{1,20}$")


class CreateCompanyRequest(BaseModel):
    company_id: str
    company_name: str
    logo_url: str | None = None

    @field_validator("company_id")
    @classmethod
    def validate_company_id(cls, v: str) -> str:
        v = v.strip()
        if not _COMPANY_ID_RE.match(v):
            raise ValueError("company_id must be alphanumeric + hyphens, max 20 characters.")
        return v.upper()

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("company_name must be at least 2 characters.")
        if len(v) > 255:
            raise ValueError("company_name must be at most 255 characters.")
        return v


class UpdateCompanyRequest(BaseModel):
    company_name: str | None = None
    logo_url: str | None = None

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("company_name must be at least 2 characters.")
        if len(v) > 255:
            raise ValueError("company_name must be at most 255 characters.")
        return v


class AssignAdminRequest(BaseModel):
    user_email: str

    @field_validator("user_email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class AssignAdminResponse(BaseModel):
    status: str                        # "assigned" | "invited"
    user_id: str | None = None         # populated when status="assigned"
    invitation_id: str | None = None   # populated when status="invited"


class AdminMemberResponse(BaseModel):
    user_id: str
    email: str
    display_name: str


class AcceptInvitationRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8)

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, v: str) -> str:
        return v.strip()


class InvitationPreviewResponse(BaseModel):
    invitation_id: str
    email: str
    company_id: str
    company_name: str
    expires_at: str   # ISO 8601
    status: str
