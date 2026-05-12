"""Repository for permissions."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from crm_backend.models import RolePermission, UserPermission


class PermissionRepository:
    """Persistence helpers for role defaults and user overrides."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_all_role_permissions(self) -> list[RolePermission]:
        statement = select(RolePermission).order_by(RolePermission.role_key.asc(), RolePermission.permission_code.asc())
        return list(self._session.scalars(statement).all())

    def get_role_permissions(self, role_key: str) -> list[RolePermission]:
        statement = (
            select(RolePermission)
            .where(RolePermission.role_key == role_key)
            .order_by(RolePermission.permission_code.asc())
        )
        return list(self._session.scalars(statement).all())

    def get_user_overrides(self, crm_user_id: str) -> list[UserPermission]:
        statement = (
            select(UserPermission)
            .where(UserPermission.crm_user_id == crm_user_id)
            .order_by(UserPermission.permission_code.asc())
        )
        return list(self._session.scalars(statement).all())

    def list_user_overrides(self) -> list[UserPermission]:
        statement = select(UserPermission).order_by(UserPermission.crm_user_id.asc(), UserPermission.permission_code.asc())
        return list(self._session.scalars(statement).all())

    def set_role_permission(self, role_key: str, permission_code: str, is_granted: bool, *, actor_id: str) -> RolePermission:
        existing = self._session.scalar(
            select(RolePermission).where(RolePermission.role_key == role_key, RolePermission.permission_code == permission_code)
        )
        if existing is None:
            existing = RolePermission(role_key=role_key, permission_code=permission_code, is_granted=is_granted)
            self._session.add(existing)
        else:
            existing.is_granted = is_granted
        self._session.flush()
        return existing

    def set_user_permission(
        self,
        crm_user_id: str,
        permission_code: str,
        is_granted: bool,
        *,
        granted_by: str,
    ) -> UserPermission:
        existing = self._session.scalar(
            select(UserPermission).where(UserPermission.crm_user_id == crm_user_id, UserPermission.permission_code == permission_code)
        )
        if existing is None:
            existing = UserPermission(
                crm_user_id=crm_user_id,
                permission_code=permission_code,
                is_granted=is_granted,
                granted_by_crm_user_id=granted_by,
            )
            self._session.add(existing)
        else:
            existing.is_granted = is_granted
            existing.granted_by_crm_user_id = granted_by
        self._session.flush()
        return existing

    def delete_user_permission(self, crm_user_id: str, permission_code: str) -> None:
        self._session.execute(
            delete(UserPermission).where(UserPermission.crm_user_id == crm_user_id, UserPermission.permission_code == permission_code)
        )
        self._session.flush()
