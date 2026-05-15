"""Repositorio de productos de depósito."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from crm_backend.core.exceptions import DuplicateStockProductCodeError
from crm_backend.models import StockProduct, Warehouse


class StockProductRepository:
    """Encapsula consultas y persistencia de productos de depósito."""

    def __init__(self, session: Session) -> None:
        """Crea el repositorio.

        Args:
            session: Sesión SQLAlchemy activa.
        """

        self._session = session

    def list_active(self) -> list[StockProduct]:
        """Lista productos activos ordenados por creación descendente.

        Returns:
            list[StockProduct]: Productos activos.
        """

        statement = (
            select(StockProduct)
            .options(
                joinedload(StockProduct.category),
                selectinload(StockProduct.movements),
                selectinload(StockProduct.stock_entries),
            )
            .where(StockProduct.is_active.is_(True))
            .order_by(StockProduct.created_at.desc())
        )
        return list(self._session.scalars(statement).unique().all())

    def list_all(self) -> list[StockProduct]:
        """Lista todos los productos, activos e inactivos."""

        statement = (
            select(StockProduct)
            .options(
                joinedload(StockProduct.category),
                selectinload(StockProduct.movements),
                selectinload(StockProduct.stock_entries),
            )
            .order_by(StockProduct.created_at.asc())
        )
        return list(self._session.scalars(statement).unique().all())

    def get_by_id(self, product_id: str) -> StockProduct | None:
        """Obtiene un producto por identificador.

        Args:
            product_id: Identificador de producto.

        Returns:
            StockProduct | None: Producto encontrado.
        """

        statement = (
            select(StockProduct)
            .options(
                joinedload(StockProduct.category),
                selectinload(StockProduct.movements),
                selectinload(StockProduct.stock_entries),
            )
            .where(StockProduct.product_id == product_id)
        )
        return self._session.scalar(statement)

    def get_by_code(self, product_code: str) -> StockProduct | None:
        """Obtiene un producto por código visible."""

        statement = (
            select(StockProduct)
            .options(joinedload(StockProduct.category), selectinload(StockProduct.stock_entries))
            .where(StockProduct.product_code == product_code)
        )
        return self._session.scalar(statement)

    @property
    def session(self) -> Session:
        """Expone la sesion para operaciones transaccionales de inventario."""

        return self._session

    def get_default_warehouse_id(self) -> str:
        """Devuelve el depósito por defecto del módulo de inventario."""

        statement = select(Warehouse).order_by(Warehouse.created_at.asc())
        warehouse = self._session.scalar(statement)
        if warehouse is None:
            raise RuntimeError("No existe ningun deposito en la base del CRM. Verifica el bootstrap del schema v4.")
        return warehouse.warehouse_id

    def save(self, product: StockProduct) -> StockProduct:
        """Persiste y refresca un producto.

        Args:
            product: Producto a guardar.

        Returns:
            StockProduct: Producto persistido.
        """

        self._session.add(product)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if "inventory_products_product_code_key" in str(exc):
                raise DuplicateStockProductCodeError() from exc
            raise
        self._session.refresh(product)
        return self.get_by_id(product.product_id) or product
