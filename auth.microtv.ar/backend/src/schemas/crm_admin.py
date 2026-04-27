from pydantic import BaseModel, Field, field_validator


class CrmAuthUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    is_active: bool
    roles: list[str]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or "@" not in normalized:
            raise ValueError("email must contain '@'.")
        return normalized


class CrmAuthUserCreateRequest(BaseModel):
    email: str
    display_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8)
    is_active: bool = True
    roles: list[str] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def normalize_create_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or "@" not in normalized:
            raise ValueError("email must contain '@'.")
        return normalized


class CrmAuthUserUpdateRequest(BaseModel):
    email: str
    display_name: str = Field(..., min_length=2, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_update_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or "@" not in normalized:
            raise ValueError("email must contain '@'.")
        return normalized


class CrmAuthUserStatusRequest(BaseModel):
    is_active: bool


class CrmAuthUserRolesRequest(BaseModel):
    roles: list[str] = Field(default_factory=list)


class CrmAuthUserResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)
