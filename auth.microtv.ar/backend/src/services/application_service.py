from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.company_application import CompanyApplication
from src.models.invitation import Invitation
from src.schemas.application import CreateApplicationRequest, UpdateApplicationRequest

# company_types that require MP Connect before going to under_review
_MP_REQUIRED_TYPES = {"transport_sub", "merchant_solo", "merchant_company"}


def _now() -> datetime:
    return datetime.now(UTC)


def _generate_company_id() -> str:
    """Generate a 20-char hex ID for a new company."""
    return uuid4().hex[:20]


class ApplicationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Queries ─────────────────────────────────────────────────────────────

    def get(self, application_id: str) -> CompanyApplication:
        app = self.session.get(CompanyApplication, application_id)
        if app is None:
            raise ValueError("Application not found.")
        return app

    def list(
        self,
        status: str | None = None,
        company_type: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CompanyApplication], int]:
        query = select(CompanyApplication)
        if status:
            query = query.where(CompanyApplication.status == status)
        if company_type:
            query = query.where(CompanyApplication.company_type == company_type)

        total = self.session.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0

        items = list(
            self.session.scalars(
                query.order_by(CompanyApplication.submitted_at.asc().nulls_last())
                .offset((page - 1) * size)
                .limit(size)
            ).all()
        )
        return items, total

    # ── State transitions ────────────────────────────────────────────────────

    def create(self, data: CreateApplicationRequest) -> CompanyApplication:
        app = CompanyApplication(
            application_id=str(uuid4()),
            company_type=data.company_type,
            company_name=data.company_name,
            cuit=data.cuit,
            contact_email=data.contact_email,
            contact_name=data.contact_name,
            parent_company_id=data.parent_company_id,
            documents=data.documents,
            status="draft",
        )
        self.session.add(app)
        self.session.commit()
        self.session.refresh(app)
        return app

    async def submit(self, application_id: str) -> CompanyApplication:
        """
        draft → fiscal_verified (AFIP OK) or raises ValueError (AFIP rejected).
        AFIP timeout/unreachable raises ValueError so callers can return 503.
        """
        from src.services.afip import verify_cuit

        app = self.get(application_id)
        if app.status != "draft":
            raise ValueError(f"Cannot submit an application in '{app.status}' status.")

        afip_data = await verify_cuit(app.cuit)

        app.fiscal_type = afip_data.get("fiscal_type")
        app.afip_data = afip_data
        app.fiscal_verified = True
        app.fiscal_verified_at = _now()
        app.status = "fiscal_verified"
        app.submitted_at = _now()
        app.updated_at = _now()
        self.session.commit()
        self.session.refresh(app)
        return app

    def mark_mp_verified(self, application_id: str, mp_account_id: str) -> CompanyApplication:
        """
        fiscal_verified → mp_verified → under_review (automatic advance).
        Called by pay.microtv.ar after successful MP OAuth.
        """
        app = self.get(application_id)
        if app.status != "fiscal_verified":
            raise ValueError(
                f"Cannot mark MP verified for an application in '{app.status}' status."
            )

        app.mp_account_id = mp_account_id
        app.mp_verified = True
        app.mp_verified_at = _now()
        # Automatically advance to under_review — no manual step needed
        app.status = "under_review"
        app.updated_at = _now()
        self.session.commit()
        self.session.refresh(app)
        return app

    def update_and_reopen(
        self,
        application_id: str,
        data: UpdateApplicationRequest,
    ) -> CompanyApplication:
        """
        Applies corrections to a rejected application and moves it back to draft.
        """
        app = self.get(application_id)
        if app.status != "rejected":
            raise ValueError("Only rejected applications can be updated and reopened.")

        if data.company_name is not None:
            app.company_name = data.company_name
        if data.cuit is not None:
            app.cuit = data.cuit
            # Reset fiscal verification — new CUIT needs re-validation
            app.fiscal_verified = False
            app.fiscal_verified_at = None
            app.afip_data = None
            app.fiscal_type = None
        if data.contact_email is not None:
            app.contact_email = data.contact_email
        if data.contact_name is not None:
            app.contact_name = data.contact_name
        if data.parent_company_id is not None:
            app.parent_company_id = data.parent_company_id
        if data.documents is not None:
            app.documents = data.documents

        app.status = "draft"
        app.rejection_reason = None
        app.updated_at = _now()
        self.session.commit()
        self.session.refresh(app)
        return app

    def approve(self, application_id: str, reviewer_id: str) -> CompanyApplication:
        """
        under_review → approved.
        Creates the Company and an invitation for contact_email as company_admin.
        """
        app = self.get(application_id)
        if app.status != "under_review":
            raise ValueError(
                f"Cannot approve an application in '{app.status}' status."
            )

        company_id = _generate_company_id()
        company = Company(
            company_id=company_id,
            company_name=app.company_name,
            status="active",
            company_type=app.company_type,
            parent_company_id=app.parent_company_id,
            cuit=app.cuit,
            fiscal_type=app.fiscal_type,
            mp_account_id=app.mp_account_id,
        )
        self.session.add(company)
        self.session.flush()

        # Create a company_admin invitation for the applicant
        invitation = self._create_admin_invitation(
            company_id=company_id,
            contact_email=app.contact_email,
            invited_by_user_id=reviewer_id,
        )

        app.status = "approved"
        app.reviewed_by = reviewer_id
        app.reviewed_at = _now()
        app.updated_at = _now()
        self.session.commit()
        self.session.refresh(app)
        return app, company, invitation

    def reject(
        self,
        application_id: str,
        reviewer_id: str,
        reason: str,
    ) -> CompanyApplication:
        """
        under_review → rejected. Stores the reason so it can be emailed to the applicant.
        """
        app = self.get(application_id)
        if app.status != "under_review":
            raise ValueError(
                f"Cannot reject an application in '{app.status}' status."
            )

        app.status = "rejected"
        app.rejection_reason = reason
        app.reviewed_by = reviewer_id
        app.reviewed_at = _now()
        app.updated_at = _now()
        self.session.commit()
        self.session.refresh(app)
        return app

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _create_admin_invitation(
        self,
        company_id: str,
        contact_email: str,
        invited_by_user_id: str,
    ) -> Invitation:
        """Creates a company_admin invitation token for the approved applicant."""
        from datetime import timedelta
        import secrets

        token = secrets.token_urlsafe(32)
        expires_at = _now() + timedelta(hours=72)

        invitation = Invitation(
            token=token,
            email=contact_email,
            company_id=company_id,
            invited_by=invited_by_user_id,
            status="pending",
            expires_at=expires_at,
        )
        self.session.add(invitation)
        return invitation
