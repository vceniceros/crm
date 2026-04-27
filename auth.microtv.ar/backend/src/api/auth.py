import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.db import get_db_session
from src.schemas import (
    AccessPendingResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginTicketResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SelectContextRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from src.security.jwt import validate_login_ticket
from src.services.auth_service import AuthService
from src.services.email import send_password_reset_email, send_verification_email
from src.services.rate_limiter import rate_limiter
from src.services.recaptcha import verify_recaptcha

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["auth"])
LOGIN_BODY_LIMIT_BYTES = 64 * 1024


async def enforce_login_body_limit(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > LOGIN_BODY_LIMIT_BYTES:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large.")
        except ValueError:
            pass

    body = await request.body()
    if len(body) > LOGIN_BODY_LIMIT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large.")


def get_auth_service(session: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(session)


@router.post("/login", response_model=TokenResponse | LoginTicketResponse | AccessPendingResponse)
async def login(
    payload: LoginRequest,
    _: None = Depends(enforce_login_body_limit),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user = auth_service.authenticate(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        return auth_service.get_login_response(user, login_mode=payload.login_mode)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/select-context", response_model=TokenResponse)
def select_context(payload: SelectContextRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        ticket_claims = validate_login_ticket(payload.login_ticket)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        user = auth_service.get_user_by_id(ticket_claims["sub"])
        if user.email != ticket_claims["email"]:
            raise ValueError("Invalid login ticket.")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        membership = auth_service.get_membership_context(user.user_id, payload.membership_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        auth_service.consume_login_ticket(ticket_claims)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return auth_service.issue_tokens(user, membership)


# ── Registration flow ─────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    """
    Create a new user account in pending_verification status.
    Sends an email with a verification link. Does NOT issue JWT tokens.
    Rate limited: 5 requests / hour per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check(f"register:{client_ip}", max_requests=5, window_seconds=3600)

    try:
        await verify_recaptcha(payload.recaptcha_token, action="register")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        user = auth_service.register_user(
            display_name=payload.display_name,
            email=payload.email,
            password=payload.password,
            user_type=payload.user_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Best-effort email send — failure is logged but does not block the response
    try:
        await send_verification_email(user.email, user.display_name, user.verification_token)  # type: ignore[arg-type]
    except Exception:
        logger.error("Failed to send verification email to %s", user.email)

    return RegisterResponse(message="Verification email sent")


@router.post("/verify-email", response_model=TokenResponse | LoginTicketResponse | AccessPendingResponse)
def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse | LoginTicketResponse | AccessPendingResponse:
    """
    Consume a verification token, activate the account, and issue JWT tokens.
    Customers receive tokens immediately; company_employees receive an access_pending response.
    """
    try:
        user = auth_service.verify_email_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        return auth_service.get_login_response(user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ResendVerificationResponse:
    """
    Regenerate and resend the email verification link for a pending account.
    Always returns the same message to avoid leaking account existence.
    Rate limited: 3 requests / hour per email address.
    """
    rate_limiter.check(f"resend:{payload.email}", max_requests=3, window_seconds=3600)

    try:
        await verify_recaptcha(payload.recaptcha_token, action="resend_verification")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    _GENERIC_RESPONSE = ResendVerificationResponse(
        message="If a pending account exists for this email, a new verification link has been sent."
    )

    try:
        user = auth_service.resend_verification(payload.email)
    except ValueError:
        # Do not reveal whether the email exists or is already verified
        return _GENERIC_RESPONSE

    try:
        await send_verification_email(user.email, user.display_name, user.verification_token)  # type: ignore[arg-type]
    except Exception:
        logger.error("Failed to resend verification email to %s", user.email)

    return _GENERIC_RESPONSE


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ForgotPasswordResponse:
    """
    Request a password reset link for an account.
    Always returns the same message to avoid leaking account existence.
    """
    rate_limiter.check(f"forgot-password:{payload.email}", max_requests=3, window_seconds=3600)

    try:
        await verify_recaptcha(payload.recaptcha_token, action="forgot_password")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    generic_response = ForgotPasswordResponse(
        message="If an active account exists for this email, a password reset link has been sent."
    )

    user = auth_service.request_password_reset(payload.email)
    if user is None:
        return generic_response

    try:
        await send_password_reset_email(
            to_email=user.email,
            display_name=user.display_name,
            reset_token=user.password_reset_token,  # type: ignore[arg-type]
        )
    except Exception:
        logger.error("Failed to send password reset email to %s", user.email)

    return generic_response


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> ResetPasswordResponse:
    """Consume a password reset token and update the user's password."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check(f"reset-password:{client_ip}", max_requests=10, window_seconds=3600)

    try:
        auth_service.reset_password(payload.token, payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return ResetPasswordResponse(message="Password updated successfully.")
