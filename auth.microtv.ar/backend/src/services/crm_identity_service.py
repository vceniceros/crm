from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models import Membership, Role, RoleAssignment, User
from src.security.passwords import hash_password


CRM_OPERATIONAL_ROLES = ("admin", "ejecutivo", "tecnico_campo", "operador_deposito")
LEGACY_COMPAT_ROLES = ("platform_admin", "company_admin", "company_operator", "passenger_user")


class CrmIdentityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_operational_roles(self) -> None:
        for role_name in (*CRM_OPERATIONAL_ROLES, *LEGACY_COMPAT_ROLES):
            existing = self._session.scalar(select(Role).where(Role.role_name == role_name))
            if existing is None:
                self._session.add(Role(role_name=role_name))
        self._session.flush()

    def ensure_bootstrap_admin_from_env(self) -> User:
        self.ensure_operational_roles()
        admin = self._session.scalar(select(User).where(User.email == settings.crm_auth_admin_email.lower().strip()))
        if admin is None:
            admin = User(
                email=settings.crm_auth_admin_email.lower().strip(),
                display_name=settings.crm_auth_admin_name.strip(),
                password_hash=hash_password(settings.crm_auth_admin_password),
                status="active",
                email_verified=True,
                user_type="company_employee",
            )
            self._session.add(admin)
            self._session.flush()
        else:
            admin.display_name = settings.crm_auth_admin_name.strip() or admin.display_name
            admin.status = "active"
            admin.email_verified = True

        membership = self._get_or_create_membership(admin.user_id)
        self._set_membership_roles(membership.membership_id, ["admin"])
        self._session.commit()
        self._session.refresh(admin)
        return admin

    def list_crm_users(self) -> list[dict[str, object]]:
        users = self._session.scalars(select(User).order_by(User.display_name.asc(), User.email.asc())).all()
        result: list[dict[str, object]] = []
        for user in users:
            membership = self._get_membership(user.user_id)
            roles = self._get_membership_roles(membership.membership_id) if membership else []
            result.append(
                {
                    "user_id": user.user_id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "is_active": user.status == "active",
                    "roles": roles,
                }
            )
        return result

    def get_crm_user(self, *, user_id: str) -> dict[str, object]:
        user = self._session.get(User, user_id)
        if user is None:
            raise ValueError("User not found.")
        return self.render_user(user)

    def create_crm_user(self, *, email: str, display_name: str, password: str, is_active: bool, roles: list[str]) -> User:
        normalized_email = email.lower().strip()
        if self._session.scalar(select(User).where(User.email == normalized_email)) is not None:
            raise ValueError("Email already registered.")

        user = User(
            email=normalized_email,
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            status="active" if is_active else "inactive",
            email_verified=True,
            verification_token=None,
            verification_token_expires_at=None,
            user_type="company_employee",
        )
        self._session.add(user)
        self._session.flush()

        membership = self._get_or_create_membership(user.user_id)
        self._set_membership_roles(membership.membership_id, roles)
        self._session.commit()
        self._session.refresh(user)
        return user

    def update_crm_user(self, *, user_id: str, email: str, display_name: str) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise ValueError("User not found.")

        normalized_email = email.lower().strip()
        duplicated = self._session.scalar(select(User).where(User.email == normalized_email, User.user_id != user_id))
        if duplicated is not None:
            raise ValueError("Email already registered.")

        user.email = normalized_email
        user.display_name = display_name.strip()
        self._session.commit()
        self._session.refresh(user)
        return user

    def set_user_active(self, *, user_id: str, is_active: bool) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise ValueError("User not found.")
        user.status = "active" if is_active else "inactive"
        user.email_verified = True
        self._session.commit()
        self._session.refresh(user)
        return user

    def set_user_roles(self, *, user_id: str, roles: list[str]) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise ValueError("User not found.")

        membership = self._get_or_create_membership(user.user_id)
        self._set_membership_roles(membership.membership_id, roles)
        self._session.commit()
        self._session.refresh(user)
        return user

    def reset_user_password(self, *, user_id: str, new_password: str) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise ValueError("User not found.")
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires_at = None
        self._session.commit()
        self._session.refresh(user)
        return user

    def render_user(self, user: User) -> dict[str, object]:
        membership = self._get_membership(user.user_id)
        roles = self._get_membership_roles(membership.membership_id) if membership else []
        return {
            "user_id": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.status == "active",
            "roles": roles,
        }

    def _get_membership(self, user_id: str) -> Membership | None:
        return self._session.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.tenant_type == settings.crm_auth_tenant_type,
                Membership.tenant_id == settings.crm_auth_tenant_id,
            )
        )

    def _get_or_create_membership(self, user_id: str) -> Membership:
        membership = self._get_membership(user_id)
        if membership is not None:
            return membership
        membership = Membership(
            user_id=user_id,
            tenant_type=settings.crm_auth_tenant_type,
            tenant_id=settings.crm_auth_tenant_id,
        )
        self._session.add(membership)
        self._session.flush()
        return membership

    def _get_membership_roles(self, membership_id: str) -> list[str]:
        rows = self._session.execute(
            select(Role.role_name)
            .join(RoleAssignment, RoleAssignment.role_id == Role.role_id)
            .where(RoleAssignment.membership_id == membership_id)
            .order_by(Role.role_name.asc())
        ).all()
        return [str(name) for (name,) in rows]

    def _set_membership_roles(self, membership_id: str, roles: list[str]) -> None:
        self.ensure_operational_roles()
        normalized = sorted({role.strip() for role in roles if role.strip()})
        invalid = [role for role in normalized if role not in CRM_OPERATIONAL_ROLES]
        if invalid:
            raise ValueError(f"Invalid roles: {', '.join(invalid)}")

        existing_assignments = self._session.scalars(
            select(RoleAssignment).where(RoleAssignment.membership_id == membership_id)
        ).all()
        for assignment in existing_assignments:
            self._session.delete(assignment)
        self._session.flush()

        if not normalized:
            return

        role_rows = self._session.scalars(select(Role).where(Role.role_name.in_(normalized))).all()
        role_map = {role.role_name: role for role in role_rows}
        for role_name in normalized:
            role = role_map.get(role_name)
            if role is None:
                raise RuntimeError(f"Role '{role_name}' not seeded.")
            self._session.add(RoleAssignment(membership_id=membership_id, role_id=role.role_id))
