import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import get_db_session
from src.models import Membership, Role, RoleAssignment, User
from src.models.company import Company
from src.schemas import CompanyResponse, GrantAccessRequest, MemberResponse
from src.security.jwt import validate_token
from src.services.auth_service import AuthService, get_user_memberships

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/companies", tags=["companies"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


def get_auth_service(session: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(session)


def _require_company_admin(
    company_id: str,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_db_session),
) -> str:
    """Dependency: validates token and checks company_admin role for company_id. Returns user_id."""
    try:
        claims = validate_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id: str = claims["sub"]
    memberships = get_user_memberships(session, user_id)
    for m in memberships:
        if m["tenant_type"] == "company" and m["tenant_id"] == company_id and "company_admin" in m["roles"]:
            return user_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="company_admin role required for this company.",
    )


def _require_authenticated(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Dependency: validates token and returns JWT claims."""
    try:
        return validate_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _build_member_response(session: Session, membership: Membership) -> MemberResponse:
    user = session.get(User, membership.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    role_names = [
        rn
        for (rn,) in session.execute(
            select(Role.role_name)
            .join(RoleAssignment, RoleAssignment.role_id == Role.role_id)
            .where(RoleAssignment.membership_id == membership.membership_id)
        ).all()
    ]
    return MemberResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        membership_id=membership.membership_id,
        roles=role_names,
    )


@router.get("/mine", response_model=list[CompanyResponse])
def get_my_companies(
    claims: dict = Depends(_require_authenticated),
    session: Session = Depends(get_db_session),
) -> list[CompanyResponse]:
    """Returns all companies where the caller has company_admin role."""
    user_id: str = claims["sub"]
    memberships = get_user_memberships(session, user_id)
    company_ids = [
        m["tenant_id"]
        for m in memberships
        if m["tenant_type"] == "company" and "company_admin" in m["roles"]
    ]
    if not company_ids:
        return []

    companies = session.scalars(select(Company).where(Company.company_id.in_(company_ids))).all()
    return [
        CompanyResponse(
            company_id=c.company_id,
            company_name=c.company_name,
            logo_url=c.logo_url,
            status=c.status,
        )
        for c in companies
    ]


@router.get("/{company_id}/members", response_model=list[MemberResponse])
def list_company_members(
    company_id: str,
    admin_user_id: str = Depends(_require_company_admin),
    session: Session = Depends(get_db_session),
) -> list[MemberResponse]:
    """Returns all members of the given company."""
    memberships = session.scalars(
        select(Membership).where(
            Membership.tenant_type == "company",
            Membership.tenant_id == company_id,
        )
    ).all()
    return [_build_member_response(session, m) for m in memberships]


@router.post("/{company_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def grant_member_access(
    company_id: str,
    payload: GrantAccessRequest,
    admin_user_id: str = Depends(_require_company_admin),
    auth_service: AuthService = Depends(get_auth_service),
    session: Session = Depends(get_db_session),
) -> MemberResponse:
    """Grants company_operator access to a user identified by email."""
    target_user = session.scalar(select(User).where(User.email == payload.user_email.lower().strip()))
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that email.",
        )

    try:
        membership = auth_service.grant_company_access(
            granting_admin_user_id=admin_user_id,
            target_user_id=target_user.user_id,
            company_id=company_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _build_member_response(session, membership)


@router.delete("/{company_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_member_access(
    company_id: str,
    user_id: str,
    admin_user_id: str = Depends(_require_company_admin),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Revokes company access for the specified user."""
    try:
        auth_service.revoke_company_access(
            granting_admin_user_id=admin_user_id,
            target_user_id=user_id,
            company_id=company_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
