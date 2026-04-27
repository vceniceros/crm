"""Repositorio de categorías de depósito."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from crm_backend.models import StockCategory


class StockCategoryRepository:
    """Encapsula el acceso a categorías activas de depósito."""

    def __init__(self, session: Session) -> None:
        """Crea el repositorio.

        Args:
            session: Sesión SQLAlchemy activa.
        """

        self._session = session

    def list_active(self) -> list[StockCategory]:
        """Lista categorías activas ordenadas por nombre.

        Returns:
            list[StockCategory]: Categorías disponibles.
        """

        statement = select(StockCategory).where(StockCategory.is_active.is_(True)).order_by(StockCategory.category_name.asc())
        return list(self._session.scalars(statement).all())

    def get_active_by_id(self, category_id: str) -> StockCategory | None:
        """Obtiene una categoría activa por identificador.

        Args:
            category_id: Identificador de categoría.

        Returns:
            StockCategory | None: Categoría encontrada.
        """

        statement = select(StockCategory).where(
            StockCategory.category_id == category_id,
            StockCategory.is_active.is_(True),
        )
        return self._session.scalar(statement)