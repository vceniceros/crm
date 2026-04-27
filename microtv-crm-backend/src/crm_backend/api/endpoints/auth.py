"""Endpoints de autenticación del backend CRM."""

from fastapi import APIRouter, Depends

from crm_backend.adapters.auth_service_adapter import AccessPendingResult, ContextSelectionRequiredResult
from crm_backend.api.dependencies import extract_bearer_token, get_auth_application_service
from crm_backend.schemas import (
    AccessPendingResponse,
    ActiveMembershipResponse,
    AuthenticatedUserResponse,
    ContextSelectionRequiredResponse,
    ErrorResponse,
    LoginRequest,
    LoginSuccessResponse,
    MembershipOptionResponse,
    TokenBundleResponse,
)
from crm_backend.services.auth_service import AuthApplicationService, ResolvedCrmSession


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginSuccessResponse | ContextSelectionRequiredResponse | AccessPendingResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def login(
    payload: LoginRequest,
    auth_service: AuthApplicationService = Depends(get_auth_application_service),
) -> LoginSuccessResponse | ContextSelectionRequiredResponse | AccessPendingResponse:
    """Autentica un usuario del CRM vía auth.microtv.ar.

    Args:
        payload: Payload del request de login.
        auth_service: Servicio de aplicación de autenticación.

    Returns:
        LoginSuccessResponse | ContextSelectionRequiredResponse | AccessPendingResponse:
            Resultado de login apto para el frontend.
    """

    result = auth_service.login(email=payload.email, password=payload.password)
    if isinstance(result, ContextSelectionRequiredResult):
        return ContextSelectionRequiredResponse(
            login_ticket=result.login_ticket,
            memberships=[MembershipOptionResponse.model_validate(membership) for membership in result.memberships],
        )
    if isinstance(result, AccessPendingResult):
        return AccessPendingResponse(user_type=result.user_type)
    return _build_login_success_response(result)


@router.get(
    "/me",
    response_model=LoginSuccessResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def get_me(
    bearer_token: str = Depends(extract_bearer_token),
    auth_service: AuthApplicationService = Depends(get_auth_application_service),
) -> LoginSuccessResponse:
    """Resuelve el bearer token actual de auth hacia una sesión del CRM.

    Args:
        bearer_token: Bearer token extraído del header Authorization.
        auth_service: Servicio de aplicación de autenticación.

    Returns:
        LoginSuccessResponse: Sesión actual del CRM para el frontend.
    """

    session = auth_service.resolve_session_from_token(bearer_token)
    return _build_login_success_response(session)


def _build_login_success_response(session: ResolvedCrmSession) -> LoginSuccessResponse:
    """Mapea una sesión resuelta del CRM al schema público de la API.

    Args:
        session: Sesión resuelta del CRM.

    Returns:
        LoginSuccessResponse: Payload serializado de login exitoso.
    """

    return LoginSuccessResponse(
        tokens=TokenBundleResponse(
            access_token=session.auth_result.access_token,
            refresh_token=session.auth_result.refresh_token,
            token_type=session.auth_result.token_type,
            expires_in=session.auth_result.expires_in,
            refresh_expires_in=session.auth_result.refresh_expires_in,
        ),
        user=AuthenticatedUserResponse(
            crm_user_id=session.crm_user.crm_user_id,
            auth_user_id=session.crm_user.auth_user_id,
            email=session.crm_user.email,
            display_name=session.crm_user.display_name,
            primary_role=session.primary_role,
            role_keys=session.role_keys,
            active_membership=ActiveMembershipResponse(
                membership_id=session.auth_result.active_membership.membership_id,
                tenant_type=session.auth_result.active_membership.tenant_type,
                tenant_id=session.auth_result.active_membership.tenant_id,
                auth_roles=session.auth_result.active_membership.roles,
            ),
        ),
    )
