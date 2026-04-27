from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models import Invitation, Membership, Role, RoleAssignment, User
from src.models.company import Company
from src.security.passwords import hash_password

_INVITATION_TTL_HOURS = 48


class ConflictError(Exception):
    """Raised when assigning an admin who is already company_admin elsewhere."""

    def __init__(self, companies: list[Company]) -> None:
        self.companies = companies
        super().__init__("existing_admin")


class AdminService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Company management ──────────────────────────────────────────────────────

    def create_company(
        self,
        company_id: str,
        company_name: str,
        logo_url: str | None,
    ) -> Company:
        """Create a new company. Raises ValueError if company_id already exists."""
        existing = self.session.get(Company, company_id)
        if existing is not None:
            raise ValueError(f"Company '{company_id}' already exists.")

        company = Company(
            company_id=company_id,
            company_name=company_name,
            logo_url=logo_url,
            status="active",
        )
        self.session.add(company)
        self.session.commit()
        self.session.refresh(company)
        return company

    def list_companies(self) -> list[Company]:
        """Returns all companies ordered by company_name."""
        return list(
            self.session.scalars(select(Company).order_by(Company.company_name.asc())).all()
        )

    def get_company(self, company_id: str) -> Company:
        """Returns the company or raises 404 HTTPException."""
        company = self.session.get(Company, company_id)
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company '{company_id}' not found.",
            )
        return company

    def update_company(
        self,
        company_id: str,
        company_name: str | None,
        logo_url: str | None,
    ) -> Company:
        company = self.get_company(company_id)
        if company_name is not None:
            company.company_name = company_name
        if logo_url is not None:
            company.logo_url = logo_url
        self.session.commit()
        self.session.refresh(company)
        return company

    def suspend_company(self, company_id: str) -> Company:
        """Sets status='suspended'."""
        company = self.get_company(company_id)
        company.status = "suspended"
        self.session.commit()
        self.session.refresh(company)
        return company

    def reactivate_company(self, company_id: str) -> Company:
        """Sets status='active'."""
        company = self.get_company(company_id)
        company.status = "active"
        self.session.commit()
        self.session.refresh(company)
        return company

    # ── company_admin management ────────────────────────────────────────────────

    def list_company_admins(self, company_id: str) -> list[dict[str, Any]]:
        """
        Returns all users with company_admin role in company_id.
        Each entry: { user_id, email, display_name }.
        """
        self.get_company(company_id)  # 404 if missing

        role = self.session.scalar(select(Role).where(Role.role_name == "company_admin"))
        if role is None:
            return []

        rows = self.session.execute(
            select(User.user_id, User.email, User.display_name)
            .join(Membership, Membership.user_id == User.user_id)
            .join(RoleAssignment, RoleAssignment.membership_id == Membership.membership_id)
            .where(
                Membership.tenant_type == "company",
                Membership.tenant_id == company_id,
                RoleAssignment.role_id == role.role_id,
            )
        ).all()

        return [
            {"user_id": r.user_id, "email": r.email, "display_name": r.display_name}
            for r in rows
        ]

    def assign_or_invite_company_admin(
        self,
        company_id: str,
        user_email: str,
        invited_by_user_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Assign or invite a company_admin for company_id.

        Caso A — email belongs to an existing company_employee:
          - Checks for multi-empresa conflict; raises ConflictError if force=False.
          - Creates or updates membership to include company_admin role.
          - Returns { status: "assigned", user_id: ... }.

        Caso B — email is not registered:
          - Creates an Invitation record (TTL 48 h).
          - Returns { status: "invited", invitation_id: ... }.

        Raises:
          ValueError — email belongs to a customer.
          ValueError — user is already company_admin of this company.
          ConflictError — user is company_admin elsewhere and force=False.
        """
        self.get_company(company_id)  # 404 if missing

        user = self.session.scalar(select(User).where(User.email == user_email))

        if user is None:
            # Caso B — unregistered email
            return self._create_invitation(
                company_id=company_id,
                email=user_email,
                invited_by_user_id=invited_by_user_id,
            )

        # Registered email — validate type
        if user.user_type == "customer":
            raise ValueError(
                "This email belongs to a customer account and cannot be assigned as company_admin."
            )

        # Check if already admin of THIS company
        admin_role = self._get_role("company_admin")
        existing_membership = self.session.scalar(
            select(Membership).where(
                Membership.user_id == user.user_id,
                Membership.tenant_type == "company",
                Membership.tenant_id == company_id,
            )
        )
        if existing_membership is not None:
            already_admin = self.session.scalar(
                select(RoleAssignment).where(
                    RoleAssignment.membership_id == existing_membership.membership_id,
                    RoleAssignment.role_id == admin_role.role_id,
                )
            )
            if already_admin is not None:
                raise ValueError("User is already company_admin of this company.")

        # Check for multi-empresa conflict
        if not force:
            conflict_companies = self._get_admin_companies(user.user_id, exclude_company_id=company_id)
            if conflict_companies:
                raise ConflictError(conflict_companies)

        # Caso A — assign the role
        return self._assign_company_admin(
            user_id=user.user_id,
            company_id=company_id,
            existing_membership=existing_membership,
        )

    def _assign_company_admin(
        self,
        user_id: str,
        company_id: str,
        existing_membership: Membership | None,
    ) -> dict[str, Any]:
        admin_role = self._get_role("company_admin")

        if existing_membership is None:
            membership = Membership(
                user_id=user_id,
                tenant_type="company",
                tenant_id=company_id,
            )
            self.session.add(membership)
            self.session.flush()
        else:
            membership = existing_membership

        self.session.add(
            RoleAssignment(
                membership_id=membership.membership_id,
                role_id=admin_role.role_id,
            )
        )
        self.session.commit()
        return {"status": "assigned", "user_id": user_id, "invitation_id": None}

    def _create_invitation(
        self,
        company_id: str,
        email: str,
        invited_by_user_id: str,
    ) -> dict[str, Any]:
        # Revoke any existing pending invitations for same email+company
        self.session.execute(
            select(Invitation)
            .where(
                Invitation.email == email,
                Invitation.company_id == company_id,
                Invitation.status == "pending",
            )
        )
        pending = self.session.scalars(
            select(Invitation).where(
                Invitation.email == email,
                Invitation.company_id == company_id,
                Invitation.status == "pending",
            )
        ).all()
        for inv in pending:
            inv.status = "revoked"

        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(hours=_INVITATION_TTL_HOURS)
        invitation = Invitation(
            token=token,
            email=email,
            company_id=company_id,
            invited_by=invited_by_user_id,
            status="pending",
            expires_at=expires_at,
        )
        self.session.add(invitation)
        self.session.commit()
        self.session.refresh(invitation)
        return {"status": "invited", "user_id": None, "invitation_id": invitation.invitation_id}

    def revoke_company_admin(self, user_id: str, company_id: str) -> None:
        """
        Removes the company_admin RoleAssignment from the user's membership in company_id.
        If no RoleAssignments remain on the membership, deletes the membership as well.
        Raises 404 HTTPException if user is not company_admin of this company.
        """
        admin_role = self._get_role("company_admin")

        membership = self.session.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.tenant_type == "company",
                Membership.tenant_id == company_id,
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not company_admin of this company.",
            )

        assignment = self.session.scalar(
            select(RoleAssignment).where(
                RoleAssignment.membership_id == membership.membership_id,
                RoleAssignment.role_id == admin_role.role_id,
            )
        )
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not company_admin of this company.",
            )

        self.session.delete(assignment)
        self.session.flush()

        # Remove membership if no other role assignments remain
        remaining = self.session.scalar(
            select(RoleAssignment).where(
                RoleAssignment.membership_id == membership.membership_id
            )
        )
        if remaining is None:
            self.session.delete(membership)

        self.session.commit()

    # ── Invitation acceptance (Caso B) ──────────────────────────────────────────

    def get_invitation_by_token(self, token: str) -> Invitation:
        """
        Returns the Invitation for token.
        Raises 404 if not found.
        Raises 410 (HTTPException) if expired, accepted, or revoked.
        """
        invitation = self.session.scalar(
            select(Invitation).where(Invitation.token == token)
        )
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found.",
            )
        self._assert_invitation_valid(invitation)
        return invitation

    def accept_invitation(
        self,
        token: str,
        display_name: str,
        password: str,
    ) -> dict[str, Any]:
        """
        Accepts an invitation:
        1. Validates token (410 if not valid).
        2. Creates user (company_employee, active, email_verified=True).
        3. Creates membership for company_id.
        4. Assigns company_admin role.
        5. Marks invitation as accepted.
        6. Issues and returns access + refresh tokens.
        """
        invitation = self.session.scalar(
            select(Invitation).where(Invitation.token == token)
        )
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found.",
            )
        self._assert_invitation_valid(invitation)

        # Check email not already registered
        existing_user = self.session.scalar(
            select(User).where(User.email == invitation.email)
        )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        # Create user
        user = User(
            display_name=display_name.strip(),
            email=invitation.email,
            password_hash=hash_password(password),
            status="active",
            email_verified=True,
            user_type="company_employee",
        )
        self.session.add(user)
        self.session.flush()

        # Create membership + assign company_admin role
        company_id = invitation.company_id
        membership = Membership(
            user_id=user.user_id,
            tenant_type="company",
            tenant_id=company_id,
        )
        self.session.add(membership)
        self.session.flush()

        admin_role = self._get_role("company_admin")
        self.session.add(
            RoleAssignment(
                membership_id=membership.membership_id,
                role_id=admin_role.role_id,
            )
        )

        # Mark invitation accepted
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(user)
        self.session.refresh(membership)

        # Issue tokens
        from src.security.jwt import create_access_token, create_refresh_token
        from src.config import settings

        membership_dict = {
            "membership_id": membership.membership_id,
            "tenant_type": membership.tenant_type,
            "tenant_id": membership.tenant_id,
            "roles": ["company_admin"],
        }
        return {
            "access_token": create_access_token(user, membership_dict),
            "refresh_token": create_refresh_token(user, membership_dict),
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "refresh_expires_in": settings.refresh_token_expire_minutes * 60,
            "requires_context_selection": False,
        }

    # ── Private helpers ─────────────────────────────────────────────────────────

    def _get_role(self, role_name: str) -> Role:
        role = self.session.scalar(select(Role).where(Role.role_name == role_name))
        if role is None:
            raise RuntimeError(f"Role '{role_name}' not seeded.")
        return role

    def _get_admin_companies(
        self,
        user_id: str,
        exclude_company_id: str,
    ) -> list[Company]:
        """Returns companies where user is already company_admin (excluding exclude_company_id)."""
        admin_role = self._get_role("company_admin")

        company_ids = [
            row.tenant_id
            for row in self.session.execute(
                select(Membership.tenant_id)
                .join(RoleAssignment, RoleAssignment.membership_id == Membership.membership_id)
                .where(
                    Membership.user_id == user_id,
                    Membership.tenant_type == "company",
                    Membership.tenant_id != exclude_company_id,
                    RoleAssignment.role_id == admin_role.role_id,
                )
            ).all()
        ]
        if not company_ids:
            return []
        return list(
            self.session.scalars(
                select(Company).where(Company.company_id.in_(company_ids))
            ).all()
        )

    def _assert_invitation_valid(self, invitation: Invitation) -> None:
        if invitation.status in ("accepted", "revoked"):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Invitation is {invitation.status}.",
            )
        now = datetime.now(UTC)
        expires = invitation.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < now:
            invitation.status = "expired"
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation has expired.",
            )

    def resend_invitation(
        self,
        company_id: str,
        invitation_id: str,
        invited_by_user_id: str,
    ) -> dict[str, Any]:
        """
        Revokes the existing invitation and creates a new one for the same email.
        Raises 404 if the invitation does not belong to company_id.
        """
        existing = self.session.get(Invitation, invitation_id)
        if existing is None or existing.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found.",
            )
        email = existing.email
        existing.status = "revoked"
        self.session.flush()

        return self._create_invitation(
            company_id=company_id,
            email=email,
            invited_by_user_id=invited_by_user_id,
        )

    def get_pending_invitations(self, company_id: str) -> list[Invitation]:
        """Returns all pending (non-expired) invitations for a company."""
        self.get_company(company_id)
        return list(
            self.session.scalars(
                select(Invitation).where(
                    Invitation.company_id == company_id,
                    Invitation.status == "pending",
                )
            ).all()
        )

    def delete_pending_invitation(self, company_id: str, invitation_id: str) -> None:
        """Revokes a pending invitation. Raises 404 if not found."""
        invitation = self.session.get(Invitation, invitation_id)
        if invitation is None or invitation.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found.",
            )
        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invitation is already {invitation.status}.",
            )
        invitation.status = "revoked"
        self.session.commit()
