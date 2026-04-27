"""Common API schemas."""

from pydantic import BaseModel, Field


class ErrorDetailResponse(BaseModel):
    """Represent the error payload body.

    Attributes:
        code: Stable machine-readable error code.
        message: Human-readable message.
    """

    code: str = Field(...)
    message: str = Field(...)


class ErrorResponse(BaseModel):
    """Wrap an error response in a stable envelope.

    Attributes:
        error: Error details.
    """

    error: ErrorDetailResponse
