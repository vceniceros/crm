import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import get_db_session
from src.models import Membership, Role, RoleAssignment
from src.models.company import Company
from src.schemas import (
    AdminMemberResponse,
    AssignAdminRequest,
    AssignAdminResponse,
    CompanyResponse,
    CreateCompanyRequest,
    UpdateCompanyRequest,
)
from src.schemas.application import (
    ApplicationListResponse,
    ApplicationResponse,
    RejectApplicationRequest,
)
from src.security.jwt import validate_token
from src.services.admin_service import AdminService, ConflictError
from src.services.application_service import ApplicationService
from src.services.email import send_company_admin_invitation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


def get_admin_service(session: Session = Depends(get_db_session)) -> AdminService:
    return AdminService(session)


def get_application_service(session: Session = Depends(get_db_session)) -> ApplicationService:
    return ApplicationService(session)


def _require_platform_admin(
    token: str = Depends(oauth2_scheme),
) -> str:
    """
    Dependency: validates token and verifies the caller has platform_admin role.
    Returns user_id (sub claim). Raises 403 on failure.
    """
    try:
        claims = validate_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    active_membership = claims.get("active_membership", {})
    roles = active_membership.get("roles", [])
    if "platform_admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="platform_admin role required.",
        )
    return claims["sub"]


def _company_to_response(company: Company) -> CompanyResponse:
    return CompanyResponse(
        company_id=company.company_id,
        company_name=company.company_name,
        logo_url=company.logo_url,
        status=company.status,
    )


# ── Company CRUD ────────────────────────────────────────────────────────────

@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[CompanyResponse]:
    return [_company_to_response(c) for c in admin_service.list_companies()]


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CreateCompanyRequest,
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> CompanyResponse:
    try:
        company = admin_service.create_company(
            company_id=payload.company_id,
            company_name=payload.company_name,
            logo_url=payload.logo_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _company_to_response(company)


@router.get("/companies/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: str,
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> CompanyResponse:
    return _company_to_response(admin_service.get_company(company_id))


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: str,
    payload: UpdateCompanyRequest,
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> CompanyResponse:
    return _company_to_response(
        admin_service.update_company(
            company_id=company_id,
            company_name=payload.company_name,
            logo_url=payload.logo_url,
        )
    )


@router.post("/companies/{company_id}/suspend", response_model=CompanyResponse)
def suspend_company(
    company_id: str,
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> CompanyResponse:
    return _company_to_response(admin_service.suspend_company(company_id))


@router.post("/companies/{company_id}/reactivate", response_model=CompanyResponse)
def reactivate_company(
    company_id: str,
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> CompanyResponse:
    return _company_to_response(admin_service.reactivate_company(company_id))


# ── company_admin management ────────────────────────────────────────────────

@router.get(
    "/companies/{company_id}/admins",
    response_model=list[AdminMemberResponse],
)
def list_company_admins(
    company_id: str,
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[AdminMemberResponse]:
    rows = admin_service.list_company_admins(company_id)
    return [AdminMemberResponse(**r) for r in rows]


@router.post(
    "/companies/{company_id}/admins",
    response_model=AssignAdminResponse,
)
async def assign_company_admin(
    company_id: str,
    payload: AssignAdminRequest,
    force: bool = Query(default=False),
    caller_id: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
    session: Session = Depends(get_db_session),
) -> AssignAdminResponse:
    try:
        result = admin_service.assign_or_invite_company_admin(
            company_id=company_id,
            user_email=payload.user_email,
            invited_by_user_id=caller_id,
            force=force,
        )
    except ConflictError as exc:
        from src.schemas.auth import CompanyResponse as CR
        conflict_detail = {
            "detail": "existing_admin",
            "companies": [
                {
                    "company_id": c.company_id,
                    "company_name": c.company_name,
                    "logo_url": c.logo_url,
                    "status": c.status,
                }
                for c in exc.companies
            ],
        }
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflict_detail,
        ) from exc
    except ValueError as exc:
        msg = str(exc)
        if "already company_admin" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg) from exc

    # If an invitation was created, send the email asynchronously
    if result["status"] == "invited":
        from src.models.invitation import Invitation
        invitation = session.get(Invitation, result["invitation_id"])
        if invitation is not None:
            company = session.get(
                __import__("src.models.company", fromlist=["Company"]).Company,
                company_id,
            )
            company_name = company.company_name if company else company_id
            try:
                await send_company_admin_invitation(
                    email=payload.user_email,
                    company_name=company_name,
                    invitation_token=invitation.token,
                )
            except Exception:
                logger.exception("Failed to send invitation email to %s", payload.user_email)

    http_status = (
        status.HTTP_201_CREATED if result["status"] == "assigned"
        else status.HTTP_202_ACCEPTED
    )
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=http_status,
        content={
            "status": result["status"],
            "user_id": result["user_id"],
            "invitation_id": result["invitation_id"],
        },
    )


@router.delete(
    "/companies/{company_id}/admins/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_company_admin(
    company_id: str,
    user_id: str,
    _: str = Depends(_require_platform_admin),
    admin_service: AdminService = Depends(get_admin_service),
) -> None:
    admin_service.revoke_company_admin(user_id=user_id, company_id=company_id)


# ── Company application review ───────────────────────────────────────────────

@router.get("/applications", response_model=ApplicationListResponse)
def list_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    company_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    _: str = Depends(_require_platform_admin),
    app_service: ApplicationService = Depends(get_application_service),
) -> ApplicationListResponse:
    """List accreditation applications with optional filters."""
    items, total = app_service.list(
        status=status_filter,
        company_type=company_type,
        page=page,
        size=size,
    )
    return ApplicationListResponse(
        items=[ApplicationResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    _: str = Depends(_require_platform_admin),
    app_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Get full detail of an accreditation application."""
    try:
        app = app_service.get(application_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ApplicationResponse.model_validate(app)


@router.post(
    "/applications/{application_id}/approve",
    response_model=ApplicationResponse,
)
async def approve_application(
    application_id: str,
    caller_id: str = Depends(_require_platform_admin),
    app_service: ApplicationService = Depends(get_application_service),
    admin_service: AdminService = Depends(get_admin_service),
    session: Session = Depends(get_db_session),
) -> ApplicationResponse:
    """
    Approve an application: creates the Company and sends a company_admin
    invitation to the applicant's contact_email.
    """
    try:
        app, company, invitation = app_service.approve(application_id, caller_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        await send_company_admin_invitation(
            email=app.contact_email,
            company_name=company.company_name,
            invitation_token=invitation.token,
        )
    except Exception:
        logger.exception(
            "Failed to send approval invitation email to %s for company %s",
            app.contact_email,
            company.company_id,
        )

    return ApplicationResponse.model_validate(app)


@router.post(
    "/applications/{application_id}/reject",
    response_model=ApplicationResponse,
)
async def reject_application(
    application_id: str,
    payload: RejectApplicationRequest,
    caller_id: str = Depends(_require_platform_admin),
    app_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """
    Reject an application with a mandatory reason.
    The applicant can correct data and reopen the same application.
    """
    try:
        app = app_service.reject(application_id, caller_id, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Best-effort rejection email — TODO: add send_application_rejected_email to email service
    # try:
    #     await send_application_rejected_email(app.contact_email, app.company_name, payload.reason)
    # except Exception:
    #     logger.exception("Failed to send rejection email to %s", app.contact_email)

    return ApplicationResponse.model_validate(app)
