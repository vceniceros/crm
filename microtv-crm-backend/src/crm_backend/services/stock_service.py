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
from crm_backend.models.notification import NotificationEntityType, NotificationType
from crm_backend.repositories import CrmUserRepository, StockCategoryRepository, StockProductRepository
from crm_backend.services.activity_log_service import ActivityLogService
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.notification_service import NotificationService
from crm_backend.services.permission_service import (
    PERMISSION_STOCK_DELETE_PRODUCT,
    PERMISSION_STOCK_MANAGE,
    PermissionService,
)


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
    minimum_stock: int = 3


class StockApplicationService:
    """Orquesta el módulo inicial real de depósito."""

    def __init__(
        self,
        settings: Settings,
        category_repository: StockCategoryRepository,
        product_repository: StockProductRepository,
        notification_service: NotificationService | None = None,
        user_repository: CrmUserRepository | None = None,
        permission_service: PermissionService | None = None,
        activity_log_service: ActivityLogService | None = None,
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
        self._notification_service = notification_service
        self._user_repository = user_repository
        self._permission_service = permission_service
        self._activity_log_service = activity_log_service

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
            minimum_stock=command.minimum_stock,
            actor_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=warehouse_id,
        )
        saved = self._product_repository.save(product)
        self._log_event(
            "stock.product_created",
            actor,
            saved.product_id,
            saved.product_name,
            {"product_code": saved.visible_product_code, "stock": saved.current_stock},
        )
        return saved

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
        saved = self._product_repository.save(product)
        self._log_event(
            "stock.movement",
            actor,
            saved.product_id,
            saved.product_name,
            {"kind": "increase", "quantity": quantity, "stock": saved.current_stock},
        )
        return saved

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
        saved_product = self._product_repository.save(product)
        self._log_event(
            "stock.movement",
            actor,
            saved_product.product_id,
            saved_product.product_name,
            {"kind": "decrease", "quantity": quantity, "stock": saved_product.current_stock},
        )

        if self._notification_service is not None and self._user_repository is not None:
            stock_now = saved_product.current_stock
            if stock_now == 0:
                notification_type = NotificationType.STOCK_OUT
                title = f"Sin stock: {saved_product.visible_product_code}"
                body = f"El producto '{saved_product.product_name}' llegó a 0 unidades."
            elif stock_now < saved_product.minimum_stock:
                notification_type = NotificationType.STOCK_LOW
                title = f"Stock bajo: {saved_product.visible_product_code} ({stock_now} unidades)"
                body = f"El producto '{saved_product.product_name}' tiene menos de {saved_product.minimum_stock} unidades disponibles."
            else:
                notification_type = None

            if notification_type is not None:
                deposito_ids = [user.crm_user_id for user in self._user_repository.list_active_by_role_key("deposito")]
                ejecutivo_ids = [user.crm_user_id for user in self._user_repository.list_active_by_role_key("ejecutivo")]
                recipient_ids = list({*deposito_ids, *ejecutivo_ids})
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=recipient_ids,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    entity_type=NotificationEntityType.STOCK_PRODUCT,
                    entity_id=saved_product.product_id,
                )

        return saved_product

    def update_product_location(
        self,
        actor: ResolvedCrmSession,
        product_id: str,
        shelf_id: str,
        shelf_height: int,
    ) -> StockProduct:
        self._ensure_inventory_write_access(actor)
        product = self._get_operable_product(product_id)
        product.shelf_id = shelf_id
        product.shelf_height = shelf_height
        saved = self._product_repository.save(product)
        self._log_event(
            "stock.product_updated",
            actor,
            saved.product_id,
            saved.product_name,
            {"shelf_id": shelf_id, "shelf_height": shelf_height},
        )
        return saved

    def set_stock(
        self,
        actor: ResolvedCrmSession,
        product_id: str,
        quantity: int,
    ) -> StockProduct:
        self._ensure_inventory_write_access(actor)
        product = self._get_operable_product(product_id)

        current = product.current_stock
        if quantity > current:
            product.increase_stock(
                quantity=quantity - current,
                actor_crm_user_id=actor.crm_user.crm_user_id,
                warehouse_id=self._product_repository.get_default_warehouse_id(),
            )
        elif quantity < current:
            product.decrease_stock(
                quantity=current - quantity,
                actor_crm_user_id=actor.crm_user.crm_user_id,
                warehouse_id=self._product_repository.get_default_warehouse_id(),
            )

        saved_product = self._product_repository.save(product)
        self._log_event(
            "stock.movement",
            actor,
            saved_product.product_id,
            saved_product.product_name,
            {"kind": "set", "quantity": quantity, "stock": saved_product.current_stock},
        )

        if self._notification_service is not None and self._user_repository is not None:
            stock_now = saved_product.current_stock
            if stock_now == 0:
                notification_type = NotificationType.STOCK_OUT
                title = f"Sin stock: {saved_product.visible_product_code}"
                body = f"El producto '{saved_product.product_name}' llegó a 0 unidades."
            elif stock_now < saved_product.minimum_stock:
                notification_type = NotificationType.STOCK_LOW
                title = f"Stock bajo: {saved_product.visible_product_code} ({stock_now} unidades)"
                body = f"El producto '{saved_product.product_name}' tiene menos de {saved_product.minimum_stock} unidades disponibles."
            else:
                notification_type = None

            if notification_type is not None:
                deposito_ids = [user.crm_user_id for user in self._user_repository.list_active_by_role_key("deposito")]
                ejecutivo_ids = [user.crm_user_id for user in self._user_repository.list_active_by_role_key("ejecutivo")]
                recipient_ids = list({*deposito_ids, *ejecutivo_ids})
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=recipient_ids,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    entity_type=NotificationEntityType.STOCK_PRODUCT,
                    entity_id=saved_product.product_id,
                )

        return saved_product

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
        saved = self._product_repository.save(product)
        self._log_event("stock.product_deleted", actor, saved.product_id, saved.product_name, {})
        return saved

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
        if self._permission_service is None:
            if "deposito" in actor.role_keys or "admin" in actor.role_keys:
                return
            raise InventoryAccessDeniedError()
        if not self._permission_service.resolve(actor.role_keys, actor.crm_user.crm_user_id, PERMISSION_STOCK_MANAGE):
            raise InventoryAccessDeniedError()

    def _ensure_inventory_admin(self, actor: ResolvedCrmSession) -> None:
        """Valida que la sesión tenga permisos administrativos en el CRM."""

        if self._permission_service is None:
            if "admin" in actor.role_keys:
                return
            raise InventoryAdminRequiredError()
        if not self._permission_service.resolve(actor.role_keys, actor.crm_user.crm_user_id, PERMISSION_STOCK_DELETE_PRODUCT):
            raise InventoryAdminRequiredError()

    def _log_event(
        self,
        event_code: str,
        actor: ResolvedCrmSession,
        entity_id: str,
        entity_label: str,
        extra: dict[str, object],
    ) -> None:
        if self._activity_log_service is None:
            return
        self._activity_log_service.log(
            event_code,
            actor,
            entity_type="stock_product",
            entity_id=entity_id,
            entity_label=entity_label,
            summary=event_code,
            extra=extra,
        )