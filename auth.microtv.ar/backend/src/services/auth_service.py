from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from src.config import settings
from src.models import LoginTicket, Membership, Role, RoleAssignment, User
from src.models.company import Company
from src.security.jwt import (
    create_access_token,
    create_login_ticket,
    create_refresh_token,
    validate_login_ticket,
)
from src.security.passwords import hash_password, verify_password


def get_user_memberships(session: Session, user_id: str) -> list[dict[str, Any]]:
    memberships = session.scalars(
        select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at.asc())
    ).all()

    if not memberships:
        return []

    membership_ids = [membership.membership_id for membership in memberships]
    role_rows: Sequence[tuple[str, str]] = session.execute(
        select(RoleAssignment.membership_id, Role.role_name)
        .join(Role, Role.role_id == RoleAssignment.role_id)
        .where(RoleAssignment.membership_id.in_(membership_ids))
        .order_by(Role.role_name.asc())
    ).all()

    roles_by_membership: dict[str, list[str]] = {membership_id: [] for membership_id in membership_ids}
    for membership_id, role_name in role_rows:
        roles_by_membership.setdefault(membership_id, []).append(role_name)

    memberships_with_roles = [
        {
            "membership_id": membership.membership_id,
            "tenant_type": membership.tenant_type,
            "tenant_id": membership.tenant_id,
            "roles": roles_by_membership.get(membership.membership_id, []),
        }
        for membership in memberships
    ]
    active = [m for m in memberships_with_roles if m["roles"]]

    # Enrich company memberships with name / logo from the companies table
    company_ids = [m["tenant_id"] for m in active if m["tenant_type"] == "company"]
    company_map: dict[str, Company] = {}
    if company_ids:
        rows = session.scalars(select(Company).where(Company.company_id.in_(company_ids))).all()
        company_map = {c.company_id: c for c in rows}

    for m in active:
        if m["tenant_type"] == "company":
            company = company_map.get(m["tenant_id"])
            m["company_name"] = company.company_name if company else None
            m["company_logo_url"] = company.logo_url if company else None

    return active


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def authenticate(self, email: str, password: str) -> User:
        user = self.session.scalar(select(User).where(User.email == email))
        if user is None or user.password_hash is None:
            raise ValueError("Invalid credentials.")
        if user.status == "pending_verification":
            raise ValueError("Please verify your email before logging in.")
        if user.status != "active":
            raise ValueError("User is not active.")
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials.")
        return user

    def get_user_memberships(self, user_id: str) -> list[dict[str, object]]:
        return get_user_memberships(self.session, user_id)

    def get_user_by_id(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise ValueError("User not found.")
        if user.status != "active":
            raise ValueError("User is not active.")
        return user

    def get_membership_context(self, user_id: str, membership_id: str) -> dict[str, Any]:
        memberships = self.get_user_memberships(user_id)
        for membership in memberships:
            if membership["membership_id"] == membership_id:
                return membership
        raise ValueError("Selected membership is not valid for the user.")

    def cleanup_expired_login_tickets(self) -> None:
        self.session.execute(delete(LoginTicket).where(LoginTicket.expires_at <= func.now()))

    def issue_login_ticket(self, user: User) -> str:
        self.cleanup_expired_login_tickets()

        token = create_login_ticket(user)
        claims = validate_login_ticket(token)
        expires_at = datetime.fromtimestamp(claims["exp"], tz=UTC)

        self.session.add(
            LoginTicket(
                ticket_id=claims["jti"],
                user_id=user.user_id,
                expires_at=expires_at,
            )
        )
        self.session.commit()
        return token

    def get_login_ticket(self, ticket_claims: dict[str, Any]) -> LoginTicket:
        self.cleanup_expired_login_tickets()

        ticket_id = ticket_claims.get("jti")
        if not ticket_id:
            raise ValueError("Invalid login ticket.")

        ticket = self.session.get(LoginTicket, ticket_id)
        if ticket is None:
            self.session.commit()
            raise ValueError("Invalid login ticket.")
        if ticket.user_id != ticket_claims["sub"]:
            raise ValueError("Invalid login ticket.")
        if ticket.consumed_at is not None:
            raise ValueError("Invalid login ticket.")
        return ticket

    def consume_login_ticket(self, ticket_claims: dict[str, Any]) -> None:
        ticket_id = ticket_claims.get("jti")
        user_id = ticket_claims.get("sub")
        if not ticket_id or not user_id:
            raise ValueError("Invalid login ticket.")

        result = self.session.execute(
            update(LoginTicket)
            .where(
                LoginTicket.ticket_id == ticket_id,
                LoginTicket.user_id == user_id,
                LoginTicket.consumed_at.is_(None),
                LoginTicket.expires_at > func.now(),
            )
            .values(consumed_at=func.now())
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise ValueError("Invalid login ticket.")
        self.session.commit()

    def issue_tokens(self, user: User, membership: dict[str, Any]) -> dict[str, object]:
        return {
            "access_token": create_access_token(user, membership),
            "refresh_token": create_refresh_token(user, membership),
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "refresh_expires_in": settings.refresh_token_expire_minutes * 60,
            "requires_context_selection": False,
        }

    # ── Registration flow ───────────────────────────────────────────────────────────

    def register_user(self, display_name: str, email: str, password: str, user_type: str = "customer") -> User:
        """Create a new user with status=pending_verification. Raises ValueError if email is taken."""
        if user_type not in {"customer", "company_employee"}:
            raise ValueError("user_type must be 'customer' or 'company_employee'.")

        existing = self.session.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise ValueError("Email already registered.")

        token = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        user = User(
            display_name=display_name,
            email=email,
            password_hash=hash_password(password),
            status="pending_verification",
            email_verified=False,
            verification_token=token,
            verification_token_expires_at=expires_at,
            user_type=user_type,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def verify_email_token(self, token: str) -> User:
        """Validate verification token, mark user as active, auto-assign membership for customers."""
        user = self.session.scalar(select(User).where(User.verification_token == token))
        if user is None:
            raise ValueError("Invalid or expired verification token.")

        expires = user.verification_token_expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires is None or expires < datetime.now(UTC):
            raise ValueError("Invalid or expired verification token.")

        if user.status != "pending_verification":
            raise ValueError("Invalid or expired verification token.")

        user.email_verified = True
        user.status = "active"
        user.verification_token = None
        user.verification_token_expires_at = None

        if user.user_type == "customer":
            role = self.session.scalar(select(Role).where(Role.role_name == "passenger_user"))
            if role is None:
                raise RuntimeError("Role 'passenger_user' not seeded.")
            membership = Membership(
                user_id=user.user_id,
                tenant_type="customer",
                tenant_id="platform",
            )
            self.session.add(membership)
            self.session.flush()
            self.session.add(RoleAssignment(
                membership_id=membership.membership_id,
                role_id=role.role_id,
            ))

        self.session.commit()
        self.session.refresh(user)
        return user

    def resend_verification(self, email: str) -> User:
        """Regenerate verification token for a pending user. Raises ValueError if not applicable."""
        user = self.session.scalar(select(User).where(User.email == email))
        if user is None or user.status != "pending_verification":
            raise ValueError("No pending account found for this email.")

        user.verification_token = str(uuid4())
        user.verification_token_expires_at = datetime.now(UTC) + timedelta(hours=24)
        self.session.commit()
        self.session.refresh(user)
        return user

    def request_password_reset(self, email: str, expires_minutes: int = 60) -> User | None:
        """
        Create a password reset token for an active local-password account.

        Returns None when the email should not receive a reset link. Callers
        must still respond with a generic success message to avoid enumeration.
        """
        user = self.session.scalar(select(User).where(User.email == email))
        if user is None:
            return None
        if user.status != "active" or not user.email_verified or user.password_hash is None:
            return None

        user.password_reset_token = str(uuid4())
        user.password_reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
        self.session.commit()
        self.session.refresh(user)
        return user

    def reset_password(self, token: str, new_password: str) -> None:
        """Consume a password reset token and update the local password."""
        user = self.session.scalar(select(User).where(User.password_reset_token == token))
        if user is None:
            raise ValueError("Invalid or expired password reset token.")

        expires = user.password_reset_token_expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires is None or expires < datetime.now(UTC):
            raise ValueError("Invalid or expired password reset token.")
        if user.status != "active":
            raise ValueError("Invalid or expired password reset token.")

        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires_at = None
        self.session.commit()

    # ── Login response helper ───────────────────────────────────────────────────

    def get_login_response(self, user: User, login_mode: str | None = None) -> dict[str, Any]:
        """
        Returns the appropriate login payload dict for a user.
        Possible shapes:
          - TokenResponse dict (single membership)
          - LoginTicketResponse dict (multiple memberships)
          - {"access_pending": True, "user_type": user.user_type} (0 memberships, company_employee)
        Raises ValueError if a customer has 0 memberships (data integrity error).
        If login_mode is provided, memberships are filtered to the matching tenant types.
        A 403-worthy ValueError is raised if the user has no memberships of the requested type.
        """
        memberships = get_user_memberships(self.session, user.user_id)

        if login_mode == "cliente":
            filtered = [m for m in memberships if m["tenant_type"] == "customer"]
            if not filtered and any(m["tenant_type"] in ("company", "seller") for m in memberships):
                raise ValueError("Esta cuenta es empresarial. Iniciá sesión con el acceso Empresa.")
            memberships = filtered
        elif login_mode == "empresa":
            filtered = [m for m in memberships if m["tenant_type"] in ("company", "seller")]
            if not filtered and any(m["tenant_type"] == "customer" for m in memberships):
                raise ValueError("Esta cuenta es de cliente. Iniciá sesión con el acceso Cliente.")
            memberships = filtered

        if len(memberships) == 0:
            if user.user_type == "company_employee":
                return {"access_pending": True, "user_type": "company_employee"}
            raise ValueError("User has no valid memberships.")

        if len(memberships) == 1:
            return self.issue_tokens(user, memberships[0])

        return {
            "login_ticket": self.issue_login_ticket(user),
            "memberships": memberships,
            "requires_context_selection": True,
        }

    # ── Company access management ───────────────────────────────────────────────

    def _verify_company_admin(self, user_id: str, company_id: str) -> None:
        """Raise ValueError unless user_id has company_admin role in company_id."""
        memberships = get_user_memberships(self.session, user_id)
        for m in memberships:
            if m["tenant_type"] == "company" and m["tenant_id"] == company_id and "company_admin" in m["roles"]:
                return
        raise ValueError("Caller does not have company_admin role in this company.")

    def grant_company_access(
        self,
        granting_admin_user_id: str,
        target_user_id: str,
        company_id: str,
    ) -> Membership:
        """
        Grants company_operator access for target_user in company_id.
        Raises ValueError on any violation.
        """
        # 1. Verify company exists and is active
        company = self.session.get(Company, company_id)
        if company is None or company.status != "active":
            raise ValueError("Company not found or not active.")

        # 2. Verify caller has company_admin in that company
        self._verify_company_admin(granting_admin_user_id, company_id)

        # 3. Verify target user exists and is company_employee
        target = self.session.get(User, target_user_id)
        if target is None:
            raise ValueError("Target user not found.")
        if target.user_type != "company_employee":
            raise ValueError("Target user is not a company employee.")

        # 4. Check no existing membership for target in that company (idempotency check)
        existing = self.session.scalar(
            select(Membership).where(
                Membership.user_id == target_user_id,
                Membership.tenant_type == "company",
                Membership.tenant_id == company_id,
            )
        )
        if existing is not None:
            raise ValueError("User already has access to this company.")

        # 5. Create membership
        membership = Membership(
            user_id=target_user_id,
            tenant_type="company",
            tenant_id=company_id,
        )
        self.session.add(membership)
        self.session.flush()

        # 6. Assign company_operator role
        role = self.session.scalar(select(Role).where(Role.role_name == "company_operator"))
        if role is None:
            raise RuntimeError("Role 'company_operator' not seeded.")
        self.session.add(RoleAssignment(
            membership_id=membership.membership_id,
            role_id=role.role_id,
        ))

        self.session.commit()
        self.session.refresh(membership)
        return membership

    def revoke_company_access(
        self,
        granting_admin_user_id: str,
        target_user_id: str,
        company_id: str,
    ) -> None:
        """
        Revokes company access for target_user in company_id.
        Raises ValueError on any violation.
        """
        # 1. Verify caller has company_admin in that company
        self._verify_company_admin(granting_admin_user_id, company_id)

        # 2. Find the membership
        membership = self.session.scalar(
            select(Membership).where(
                Membership.user_id == target_user_id,
                Membership.tenant_type == "company",
                Membership.tenant_id == company_id,
            )
        )
        if membership is None:
            raise ValueError("User does not have access to this company.")

        # 3. Delete role assignments
        self.session.execute(
            delete(RoleAssignment).where(RoleAssignment.membership_id == membership.membership_id)
        )

        # 4. Delete membership
        self.session.delete(membership)
        self.session.commit()
