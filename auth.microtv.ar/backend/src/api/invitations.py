import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db import get_db_session
from src.models.company import Company
from src.schemas import AcceptInvitationRequest, InvitationPreviewResponse, TokenResponse
from src.services.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/invitations", tags=["invitations"])


def get_admin_service(session: Session = Depends(get_db_session)) -> AdminService:
    return AdminService(session)


@router.get("/{token}", response_model=InvitationPreviewResponse)
def get_invitation(
    token: str,
    admin_service: AdminService = Depends(get_admin_service),
    session: Session = Depends(get_db_session),
) -> InvitationPreviewResponse:
    """
    Returns invitation details for the accept-invitation page.
    404 if token unknown.
    410 if expired, accepted, or revoked.
    """
    invitation = admin_service.get_invitation_by_token(token)

    company = session.get(Company, invitation.company_id)
    company_name = company.company_name if company else invitation.company_id

    expires_str = invitation.expires_at.isoformat()

    return InvitationPreviewResponse(
        invitation_id=invitation.invitation_id,
        email=invitation.email,
        company_id=invitation.company_id,
        company_name=company_name,
        expires_at=expires_str,
        status=invitation.status,
    )


@router.post(
    "/{token}/accept",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def accept_invitation(
    token: str,
    payload: AcceptInvitationRequest,
    admin_service: AdminService = Depends(get_admin_service),
) -> TokenResponse:
    """
    Creates the user, assigns company_admin, marks invitation accepted.
    Returns access + refresh tokens ready to use.
    410 if invitation is no longer valid.
    """
    result = admin_service.accept_invitation(
        token=token,
        display_name=payload.display_name,
        password=payload.password,
    )
    return TokenResponse(**result)
