"""Application error handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from crm_backend.core.exceptions import ApplicationError


def register_error_handlers(app: FastAPI) -> None:
    """Register custom exception handlers in the FastAPI app.

    Args:
        app: FastAPI application.
    """

    @app.exception_handler(ApplicationError)
    def handle_application_error(_: Request, exc: ApplicationError) -> JSONResponse:
        """Translate application errors into the API envelope.

        Args:
            _: Current request instance.
            exc: Raised application error.

        Returns:
            JSONResponse: Serialized error response.
        """

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
