"""Repository for CRM roles."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from crm_backend.models import CrmRole


class CrmRoleRepository:
    """Persist and query local CRM roles."""

    def __init__(self, session: Session) -> None:
        """Build a repository bound to a SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """

        self._session = session

    def get_by_key(self, role_key: str) -> CrmRole | None:
        """Return an active CRM role by key.

        Args:
            role_key: Role key to search.

        Returns:
            CrmRole | None: Matching role if found.
        """

        statement = select(CrmRole).where(CrmRole.role_key == role_key, CrmRole.is_active.is_(True))
        return self._session.scalar(statement)

    def get_by_id(self, crm_role_id: str) -> CrmRole | None:
        """Return an active CRM role by internal identifier."""

        statement = select(CrmRole).where(CrmRole.crm_role_id == crm_role_id, CrmRole.is_active.is_(True))
        return self._session.scalar(statement)

    def list_active(self) -> list[CrmRole]:
        """Return all active CRM roles ordered by label."""

        statement = select(CrmRole).where(CrmRole.is_active.is_(True)).order_by(CrmRole.role_label.asc(), CrmRole.role_key.asc())
        return list(self._session.scalars(statement).all())
