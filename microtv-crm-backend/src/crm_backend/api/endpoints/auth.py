"""Endpoints de autenticación del backend CRM."""

from fastapi import APIRouter, Depends, Request, Response, status

from crm_backend.adapters.auth_service_adapter import AccessPendingResult, ContextSelectionRequiredResult
from crm_backend.api.dependencies import (
    extract_bearer_token,
    get_activity_log_service,
    get_auth_application_service,
    get_authenticated_crm_session,
)
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
from crm_backend.services.activity_log_service import ActivityLogService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginSuccessResponse | ContextSelectionRequiredResponse | AccessPendingResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def login(
    payload: LoginRequest,
    request: Request,
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

    result = auth_service.login(email=payload.email, password=payload.password, ip_address=request.client.host if request.client else None)
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


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}},
)
def logout(
    request: Request,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
) -> Response:
    activity_log_service.log(
        "auth.logout",
        actor,
        entity_type="crm_user",
        entity_id=actor.crm_user.crm_user_id,
        entity_label=actor.crm_user.display_name or actor.crm_user.email,
        summary="Logout de CRM.",
        ip_address=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
            avatar_url=session.crm_user.avatar_url,
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
