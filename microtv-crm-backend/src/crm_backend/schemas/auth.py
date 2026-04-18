"""Authentication API schemas."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Represent the CRM login request payload.

    Attributes:
        email: User email.
        password: User password.
    """

    email: EmailStr
    password: str = Field(..., min_length=1)


class MembershipOptionResponse(BaseModel):
    """Represent an auth membership available for selection.

    Attributes:
        membership_id: External membership identifier.
        tenant_type: Tenant type returned by auth.
        tenant_id: Tenant identifier returned by auth.
        roles: External roles returned by auth.
        company_name: Optional company name.
        company_logo_url: Optional company logo URL.
    """

    membership_id: str
    tenant_type: str
    tenant_id: str
    roles: list[str]
    company_name: str | None = None
    company_logo_url: str | None = None


class ActiveMembershipResponse(BaseModel):
    """Represent the active auth membership echoed by the CRM.

    Attributes:
        membership_id: External membership identifier.
        tenant_type: External tenant type.
        tenant_id: External tenant identifier.
        auth_roles: External roles snapshot.
    """

    membership_id: str
    tenant_type: str
    tenant_id: str
    auth_roles: list[str]


class AuthenticatedUserResponse(BaseModel):
    """Represent the authenticated CRM user returned to the frontend.

    Attributes:
        crm_user_id: Internal CRM user id.
        auth_user_id: External auth user id.
        email: Cached email.
        display_name: Display name usable by the frontend.
        primary_role: Primary local CRM role for the current UI.
        role_keys: Local CRM roles available to the user.
        active_membership: Active external membership snapshot.
    """

    crm_user_id: str
    auth_user_id: str
    email: str | None
    display_name: str | None
    primary_role: str
    role_keys: list[str]
    active_membership: ActiveMembershipResponse


class TokenBundleResponse(BaseModel):
    """Represent auth tokens proxied back to the frontend.

    Attributes:
        access_token: Auth access token.
        refresh_token: Auth refresh token.
        token_type: Token type.
        expires_in: Access token duration in seconds.
        refresh_expires_in: Refresh token duration in seconds.
    """

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int


class LoginSuccessResponse(BaseModel):
    """Represent a fully authenticated CRM login response.

    Attributes:
        status: Stable login status.
        tokens: Auth token bundle.
        user: Authenticated CRM user payload.
    """

    status: Literal["authenticated"] = "authenticated"
    tokens: TokenBundleResponse
    user: AuthenticatedUserResponse


class ContextSelectionRequiredResponse(BaseModel):
    """Represent a response that requires tenant context selection.

    Attributes:
        status: Stable login status.
        login_ticket: Login ticket returned by auth.
        memberships: Membership candidates.
    """

    status: Literal["context_selection_required"] = "context_selection_required"
    login_ticket: str
    memberships: list[MembershipOptionResponse]


class AccessPendingResponse(BaseModel):
    """Represent a response for users pending CRM access.

    Attributes:
        status: Stable login status.
        user_type: External user type returned by auth.
    """

    status: Literal["access_pending"] = "access_pending"
    user_type: str
