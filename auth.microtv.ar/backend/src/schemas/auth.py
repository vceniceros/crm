import re
from typing import Literal

from pydantic import BaseModel, field_validator

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class LoginRequest(BaseModel):
    email: str
    password: str
    login_mode: Literal["cliente", "empresa"] | None = None


class MembershipOption(BaseModel):
    membership_id: str
    tenant_type: str
    tenant_id: str
    roles: list[str]
    company_name: str | None = None
    company_logo_url: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    requires_context_selection: bool = False


class LoginTicketResponse(BaseModel):
    login_ticket: str
    memberships: list[MembershipOption]
    requires_context_selection: bool = True


class SelectContextRequest(BaseModel):
    login_ticket: str
    membership_id: str


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    display_name: str
    email: str
    password: str
    recaptcha_token: str
    user_type: str = "customer"

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v: str) -> str:
        if v not in {"customer", "company_employee"}:
            raise ValueError("user_type must be 'customer' or 'company_employee'.")
        return v

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Display name must be at least 2 characters.")
        if len(v) > 80:
            raise ValueError("Display name must be at most 80 characters.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.lower().strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class RegisterResponse(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str
    recaptcha_token: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.lower().strip()


class ResendVerificationResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: str
    recaptcha_token: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.lower().strip()


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Reset token is required.")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class ResetPasswordResponse(BaseModel):
    message: str


# ── Access pending ────────────────────────────────────────────────────────────

class AccessPendingResponse(BaseModel):
    access_pending: bool = True
    user_type: str


# ── Company member management ─────────────────────────────────────────────────

class GrantAccessRequest(BaseModel):
    user_email: str


class MemberResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    membership_id: str
    roles: list[str]


class CompanyResponse(BaseModel):
    company_id: str
    company_name: str
    logo_url: str | None
    status: str
