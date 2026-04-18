"""Repository for CRM users."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from crm_backend.models import CrmRole, CrmUser, CrmUserRole, Subtask, Task, TaskTemplateSubtask


class CrmUserRepository:
    """Persist and query local CRM users and their role assignments."""

    ROLE_KEY_ALIASES = {
        "admin": "admin_crm",
        "deposito": "encargado_deposito",
        "tecnico": "tecnico_campo",
    }

    def __init__(self, session: Session) -> None:
        """Build a repository bound to a SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """

        self._session = session

    def get_by_auth_user_id(self, auth_user_id: str) -> CrmUser | None:
        """Return a CRM user by external auth identifier.

        Args:
            auth_user_id: External auth user identifier.

        Returns:
            CrmUser | None: Matching user when present.
        """

        statement = (
            select(CrmUser)
            .options(selectinload(CrmUser.assigned_roles).selectinload(CrmUserRole.role))
            .where(CrmUser.auth_user_id == auth_user_id)
        )
        return self._session.scalar(statement)

    def get_by_email(self, email: str) -> CrmUser | None:
        """Return the oldest active CRM user matching the email address."""

        candidates = self.list_by_email(email)
        return candidates[0] if candidates else None

    def list_by_email(self, email: str) -> list[CrmUser]:
        """Return active CRM users matching the email address."""

        normalized_email = email.strip().lower()
        statement = (
            select(CrmUser)
            .options(selectinload(CrmUser.assigned_roles).selectinload(CrmUserRole.role))
            .where(CrmUser.deleted_at.is_(None))
            .where(func.lower(CrmUser.email) == normalized_email)
            .order_by(CrmUser.created_at.asc(), CrmUser.crm_user_id.asc())
        )
        return list(self._session.scalars(statement).all())

    def count_operational_references(self, crm_user_id: str) -> int:
        """Count operational references that indicate the user is already in active use."""

        task_count = self._session.query(Task).filter(Task.current_assigned_crm_user_id == crm_user_id).count()
        subtask_count = self._session.query(Subtask).filter(Subtask.current_assigned_crm_user_id == crm_user_id).count()
        template_count = self._session.query(TaskTemplateSubtask).filter(TaskTemplateSubtask.default_responsible_crm_user_id == crm_user_id).count()
        return task_count + subtask_count + template_count

    def get_by_id(self, crm_user_id: str) -> CrmUser | None:
        """Return a CRM user by internal identifier."""

        statement = (
            select(CrmUser)
            .options(selectinload(CrmUser.assigned_roles).selectinload(CrmUserRole.role))
            .where(CrmUser.crm_user_id == crm_user_id)
        )
        return self._session.scalar(statement)

    def create(self, auth_user_id: str) -> CrmUser:
        """Create a new CRM user shell.

        Args:
            auth_user_id: External auth user identifier.

        Returns:
            CrmUser: Newly created user entity.
        """

        crm_user = CrmUser(auth_user_id=auth_user_id)
        self._session.add(crm_user)
        self._session.flush()
        return crm_user

    def assign_role_if_missing(self, crm_user: CrmUser, crm_role: CrmRole) -> None:
        """Assign a local CRM role when it is not already linked.

        Args:
            crm_user: CRM user entity.
            crm_role: CRM role entity.
        """

        role_ids = {assignment.crm_role_id for assignment in crm_user.assigned_roles}
        if crm_role.crm_role_id in role_ids:
            return
        crm_user.assigned_roles.append(
            CrmUserRole(
                crm_user_id=crm_user.crm_user_id,
                crm_role_id=crm_role.crm_role_id,
                role=crm_role,
            )
        )

    def save(self, crm_user: CrmUser) -> CrmUser:
        """Commit current CRM user changes.

        Args:
            crm_user: CRM user entity to persist.

        Returns:
            CrmUser: Persisted and refreshed user.
        """

        self._session.add(crm_user)
        self._session.commit()
        self._session.refresh(crm_user)
        return self.get_by_auth_user_id(crm_user.auth_user_id) or crm_user

    def reconcile_duplicate_identity(self, canonical_user: CrmUser, duplicate_user: CrmUser, auth_user_id: str) -> CrmUser:
        """Merge a duplicate CRM user into the canonical operational record.

        The duplicate row is soft-deleted and its auth identifier is released so
        the canonical row can keep serving future logins.
        """

        canonical_role_ids = {assignment.crm_role_id for assignment in canonical_user.assigned_roles}
        for assignment in duplicate_user.assigned_roles:
            if assignment.crm_role_id in canonical_role_ids:
                continue
            canonical_user.assigned_roles.append(
                CrmUserRole(
                    crm_user_id=canonical_user.crm_user_id,
                    crm_role_id=assignment.crm_role_id,
                    role=assignment.role,
                )
            )

        duplicate_user.auth_user_id = duplicate_user.crm_user_id
        duplicate_user.deleted_at = datetime.now(UTC)
        duplicate_user.is_active_in_crm = False

        self._session.add(duplicate_user)
        self._session.flush()

        canonical_user.auth_user_id = auth_user_id
        self._session.add(canonical_user)
        self._session.commit()
        self._session.refresh(canonical_user)
        return self.get_by_id(canonical_user.crm_user_id) or canonical_user

    def list_active_by_role_key(self, role_key: str) -> list[CrmUser]:
        """Return active CRM users matching the requested role key or alias."""

        resolved_role_key = self.ROLE_KEY_ALIASES.get(role_key, role_key)
        statement = (
            select(CrmUser)
            .join(CrmUser.assigned_roles)
            .join(CrmUserRole.role)
            .options(selectinload(CrmUser.assigned_roles).selectinload(CrmUserRole.role))
            .where(CrmUser.deleted_at.is_(None))
            .where(CrmUser.is_active_in_crm.is_(True))
            .where(CrmRole.is_active.is_(True))
            .where(CrmRole.role_key == resolved_role_key)
            .order_by(CrmUser.display_name.asc(), CrmUser.email.asc(), CrmUser.crm_user_id.asc())
        )
        return list(self._session.scalars(statement).unique().all())
