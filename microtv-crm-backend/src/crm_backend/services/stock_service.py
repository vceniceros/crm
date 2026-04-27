"""Casos de uso del flujo inicial real de depósito."""

from __future__ import annotations

from dataclasses import dataclass

from crm_backend.core.config import Settings
from crm_backend.core.exceptions import (
    DuplicateStockProductCodeError,
    InventoryAdminRequiredError,
    InventoryAccessDeniedError,
    StockCategoryNotFoundError,
    StockProductNotFoundError,
)
from crm_backend.models import StockCategory, StockProduct
from crm_backend.repositories import StockCategoryRepository, StockProductRepository
from crm_backend.services.auth_service import ResolvedCrmSession


@dataclass(slots=True)
class CreateStockProductCommand:
    """Agrupa los datos de alta de producto.

    Attributes:
        name: Nombre del producto.
        product_code: Código visible obligatorio del producto.
        category_id: Categoría elegida.
        initial_stock: Stock inicial.
        image_url: URL opcional de imagen.
    """

    name: str
    product_code: str
    category_id: str
    initial_stock: int
    image_url: str | None
    requires_tracking: bool


class StockApplicationService:
    """Orquesta el módulo inicial real de depósito."""

    def __init__(
        self,
        settings: Settings,
        category_repository: StockCategoryRepository,
        product_repository: StockProductRepository,
    ) -> None:
        """Crea el servicio.

        Args:
            settings: Configuración de la aplicación.
            category_repository: Repositorio de categorías.
            product_repository: Repositorio de productos.
        """

        self._settings = settings
        self._category_repository = category_repository
        self._product_repository = product_repository

    def list_categories(self, actor: ResolvedCrmSession) -> list[StockCategory]:
        """Lista categorías disponibles para el actor autenticado.

        Args:
            actor: Sesión CRM autenticada.

        Returns:
            list[StockCategory]: Categorías activas.
        """

        self._ensure_inventory_read_access(actor)
        return self._category_repository.list_active()

    def list_products(self, actor: ResolvedCrmSession) -> list[StockProduct]:
        """Lista productos activos para el actor autenticado.

        Args:
            actor: Sesión CRM autenticada.

        Returns:
            list[StockProduct]: Productos activos.
        """

        self._ensure_inventory_read_access(actor)
        return self._product_repository.list_active()

    def create_product(self, actor: ResolvedCrmSession, command: CreateStockProductCommand) -> StockProduct:
        """Crea un producto real en depósito.

        Args:
            actor: Sesión CRM autenticada.
            command: Datos del producto.

        Returns:
            StockProduct: Producto persistido.
        """

        self._ensure_inventory_write_access(actor)
        category = self._category_repository.get_active_by_id(command.category_id)
        if category is None:
            raise StockCategoryNotFoundError()
        if self._product_repository.get_by_code(command.product_code) is not None:
            raise DuplicateStockProductCodeError()

        warehouse_id = self._product_repository.get_default_warehouse_id()
        product = StockProduct.create(
            name=command.name,
            product_code=command.product_code,
            stock_category_id=category.stock_category_id,
            initial_stock=command.initial_stock,
            image_url=command.image_url,
            requires_tracking=command.requires_tracking,
            actor_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=warehouse_id,
        )
        return self._product_repository.save(product)

    def increase_stock(self, actor: ResolvedCrmSession, product_id: str, quantity: int) -> StockProduct:
        """Aumenta el stock de un producto existente.

        Args:
            actor: Sesión CRM autenticada.
            product_id: Producto afectado.
            quantity: Cantidad a sumar.

        Returns:
            StockProduct: Producto actualizado.
        """

        self._ensure_inventory_write_access(actor)
        product = self._get_operable_product(product_id)
        product.increase_stock(
            quantity=quantity,
            actor_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=self._product_repository.get_default_warehouse_id(),
        )
        return self._product_repository.save(product)

    def decrease_stock(self, actor: ResolvedCrmSession, product_id: str, quantity: int) -> StockProduct:
        """Disminuye el stock de un producto existente.

        Args:
            actor: Sesión CRM autenticada.
            product_id: Producto afectado.
            quantity: Cantidad a descontar.

        Returns:
            StockProduct: Producto actualizado.
        """

        self._ensure_inventory_write_access(actor)
        product = self._get_operable_product(product_id)
        product.decrease_stock(
            quantity=quantity,
            actor_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=self._product_repository.get_default_warehouse_id(),
        )
        return self._product_repository.save(product)

    def delete_product(self, actor: ResolvedCrmSession, product_id: str) -> StockProduct:
        """Da de baja lógica un producto existente.

        Args:
            actor: Sesión CRM autenticada.
            product_id: Producto a eliminar.

        Returns:
            StockProduct: Producto actualizado tras la baja lógica.
        """

        self._ensure_inventory_admin(actor)
        product = self._get_operable_product(product_id)
        product.deactivate()
        return self._product_repository.save(product)

    def _get_operable_product(self, product_id: str) -> StockProduct:
        """Obtiene un producto existente listo para operar.

        Args:
            product_id: Identificador del producto.

        Returns:
            StockProduct: Producto encontrado.
        """

        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise StockProductNotFoundError()
        product._ensure_active()
        return product

    def _ensure_inventory_read_access(self, actor: ResolvedCrmSession) -> None:
        """Valida que la sesión tenga acceso de lectura al módulo real de depósito.

        Args:
            actor: Sesión CRM autenticada.
        """

        if "admin" in actor.role_keys:
            return

        membership = actor.auth_result.active_membership
        if not {"deposito", "ejecutivo"}.intersection(actor.role_keys):
            raise InventoryAccessDeniedError()
        if membership.tenant_type != "company" or membership.tenant_id != self._settings.deposito_demo_tenant_id:
            raise InventoryAccessDeniedError()

    def _ensure_inventory_write_access(self, actor: ResolvedCrmSession) -> None:
        """Valida que la sesión tenga permisos operativos sobre depósito.

        Args:
            actor: Sesión CRM autenticada.
        """

        self._ensure_inventory_read_access(actor)
        if "deposito" not in actor.role_keys and "admin" not in actor.role_keys:
            raise InventoryAccessDeniedError()

    def _ensure_inventory_admin(self, actor: ResolvedCrmSession) -> None:
        """Valida que la sesión tenga permisos administrativos en el CRM."""

        if "admin" not in actor.role_keys:
            raise InventoryAdminRequiredError()