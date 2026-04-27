"""CLI commands for auth.microtv.ar backend administration.

Usage:
    python -m src.cli create_admin --email=admin@microtv.ar --display-name="MicroTV Admin"
"""
from __future__ import annotations

import argparse
import secrets
import string
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.db.session import SessionLocal
from src.models import Membership, Role, RoleAssignment, User
from src.security.passwords import hash_password
from src.services.crm_identity_service import CrmIdentityService


def _generate_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_admin(email: str, display_name: str, password: str | None = None) -> None:
    session: Session = SessionLocal()
    try:
        # Check for duplicate
        existing = session.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"Error: A user with email '{email}' already exists.", file=sys.stderr)
            sys.exit(1)

        # Resolve platform_admin role
        role = session.scalar(select(Role).where(Role.role_name == "platform_admin"))
        if role is None:
            print("Error: Role 'platform_admin' not found. Run the seed migration first.", file=sys.stderr)
            sys.exit(1)

        password = password or _generate_password()

        user = User(
            display_name=display_name,
            email=email,
            password_hash=hash_password(password),
            status="active",
            email_verified=True,
            verification_token=None,
            verification_token_expires_at=None,
            user_type="platform_admin",
        )
        session.add(user)
        session.flush()

        membership = Membership(
            user_id=user.user_id,
            tenant_type="platform",
            tenant_id="platform",
        )
        session.add(membership)
        session.flush()

        session.add(RoleAssignment(
            membership_id=membership.membership_id,
            role_id=role.role_id,
        ))

        session.commit()

        print(f"Platform admin created successfully.")
        print(f"  user_id:      {user.user_id}")
        print(f"  email:        {user.email}")
        print(f"  display_name: {user.display_name}")
        print(f"  password:     {password}")
        print("Keep this password safe — it will not be shown again.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="auth.microtv.ar CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    admin_parser = subparsers.add_parser("create_admin", help="Create a platform admin user")
    admin_parser.add_argument("--email", required=True, help="Admin email address")
    admin_parser.add_argument("--display-name", required=True, dest="display_name", help="Admin display name")
    admin_parser.add_argument("--password", required=False, help="Optional explicit password for local bootstrap")

    subparsers.add_parser(
        "ensure_crm_bootstrap",
        help="Ensure CRM operational roles and bootstrap admin user from env (idempotent)",
    )

    args = parser.parse_args()

    if args.command == "create_admin":
        create_admin(email=args.email, display_name=args.display_name, password=args.password)
        return

    if args.command == "ensure_crm_bootstrap":
        session: Session = SessionLocal()
        try:
            service = CrmIdentityService(session)
            admin = service.ensure_bootstrap_admin_from_env()
            print("CRM auth bootstrap applied successfully.")
            print(f"  admin_email: {admin.email}")
            print(f"  tenant:      {settings.crm_auth_tenant_type}:{settings.crm_auth_tenant_id}")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    main()
