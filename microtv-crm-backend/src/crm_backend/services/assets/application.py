"""Application service for asset management."""

from __future__ import annotations

from datetime import UTC, datetime

from crm_backend.core.exceptions import ApplicationError, ClientNotFoundError, TaskNotFoundError, TicketNotFoundError
from crm_backend.models import Asset, AssetCategory, AssetCategoryField, AssetFieldValue
from crm_backend.repositories import AssetRepository, ClientRepository, TaskRepository, TicketRepository
from crm_backend.services.activity_log_service import ActivityLogService
from crm_backend.services.assets.builder import AssetBuilder
from crm_backend.services.assets.exceptions import AssetAccessDeniedError, AssetCategoryNotFoundError, AssetNotFoundError, AssetValidationError
from crm_backend.services.assets.strategies import AssetFieldValueStrategyRegistry
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.permission_service import PermissionService


class AssetApplicationService:
    """Coordinate asset use cases."""

    def __init__(
        self,
        asset_repository: AssetRepository,
        client_repository: ClientRepository,
        ticket_repository: TicketRepository,
        task_repository: TaskRepository,
        permission_service: PermissionService,
        activity_log_service: ActivityLogService,
    ) -> None:
        self._asset_repository = asset_repository
        self._client_repository = client_repository
        self._ticket_repository = ticket_repository
        self._task_repository = task_repository
        self._permission_service = permission_service
        self._activity_log_service = activity_log_service
        self._strategy_registry = AssetFieldValueStrategyRegistry()

    def list_categories(self, actor: ResolvedCrmSession) -> list[AssetCategory]:
        self._ensure_authenticated(actor)
        return self._asset_repository.list_categories(is_active=True)

    def create_category(self, actor: ResolvedCrmSession, request) -> AssetCategory:
        self._ensure_permission(actor, "assets.manage_categories")
        category_name = request.category_name.strip()
        if not category_name:
            raise AssetValidationError("El nombre de la categoria es obligatorio.")
        fields = []
        for index, field_payload in enumerate(request.fields):
            if field_payload.field_type not in {"string", "number"}:
                raise AssetValidationError(f"Tipo de campo no soportado: '{field_payload.field_type}'.")
            fields.append(
                AssetCategoryField(
                    field_name=field_payload.field_name.strip(),
                    field_type=field_payload.field_type,
                    is_required=field_payload.is_required,
                    order_index=field_payload.order_index if field_payload.order_index is not None else index,
                )
            )
        category = AssetCategory(
            category_name=category_name,
            description=request.description,
            created_by_crm_user_id=actor.crm_user.crm_user_id,
            fields=fields,
        )
        saved = self._asset_repository.save_category(category)
        self._log(actor, "assets.category.created", saved.asset_category_id, saved.category_name)
        return saved

    def get_category(self, actor: ResolvedCrmSession, category_id: str) -> AssetCategory:
        self._ensure_authenticated(actor)
        category = self._asset_repository.get_category(category_id)
        if category is None or not category.is_active:
            raise AssetCategoryNotFoundError()
        return category

    def list_assets(self, actor: ResolvedCrmSession, client_id: str | None = None, category_id: str | None = None, search: str | None = None) -> list[Asset]:
        self._ensure_authenticated(actor)
        return self._asset_repository.list_assets(client_id=client_id, category_id=category_id, search=search)

    def get_asset(self, actor: ResolvedCrmSession, asset_id: str) -> Asset:
        self._ensure_authenticated(actor)
        asset = self._asset_repository.get_asset(asset_id)
        if asset is None:
            raise AssetNotFoundError()
        return asset

    def create_asset(self, actor: ResolvedCrmSession, request) -> Asset:
        self._ensure_permission(actor, "assets.create")
        category = self.get_category(actor, request.category_id)
        if self._client_repository.get_by_id(request.client_id) is None:
            raise ClientNotFoundError()
        if request.parent_asset_id:
            parent = self.get_asset(actor, request.parent_asset_id)
            if parent.client_id != request.client_id:
                raise AssetValidationError("El activo padre debe pertenecer al mismo cliente.")

        field_by_id = {field.field_id: field for field in category.fields}
        builder = (
            AssetBuilder()
            .with_category(category)
            .with_client(request.client_id)
            .with_parent_asset(request.parent_asset_id)
            .with_name(request.asset_name)
            .with_notes(request.notes)
        )
        for item in request.field_values:
            field = field_by_id.get(item.field_id)
            if field is None:
                raise AssetValidationError("Uno de los campos no pertenece a la categoria seleccionada.")
            builder.with_field_value(field, item.value, self._strategy_registry)

        asset = self._asset_repository.save_asset(builder.build(actor.crm_user.crm_user_id))
        self._log(actor, "assets.created", asset.asset_id, asset.asset_name)
        return asset

    def update_asset(self, actor: ResolvedCrmSession, asset_id: str, request) -> Asset:
        self._ensure_permission(actor, "assets.edit")
        asset = self.get_asset(actor, asset_id)
        if "tecnico" in actor.role_keys and asset.created_by_crm_user_id != actor.crm_user.crm_user_id:
            raise AssetAccessDeniedError("Los tecnicos solo pueden editar activos creados por ellos.")
        if request.asset_name is not None:
            name = request.asset_name.strip()
            if not name:
                raise AssetValidationError("El nombre del activo es obligatorio.")
            asset.asset_name = name
        if request.notes is not None:
            asset.notes = request.notes.strip() if request.notes.strip() else None
        if request.parent_asset_id is not None:
            if request.parent_asset_id == asset.asset_id:
                raise AssetValidationError("Un activo no puede ser su propio padre.")
            if request.parent_asset_id:
                parent = self.get_asset(actor, request.parent_asset_id)
                if parent.client_id != asset.client_id:
                    raise AssetValidationError("El activo padre debe pertenecer al mismo cliente.")
            asset.parent_asset_id = request.parent_asset_id or None
        if request.field_values is not None:
            self._update_field_values(asset, request.field_values)
        asset.updated_at = datetime.now(UTC)
        saved = self._asset_repository.save_asset(asset)
        self._log(actor, "assets.updated", saved.asset_id, saved.asset_name)
        return saved

    def delete_asset(self, actor: ResolvedCrmSession, asset_id: str) -> None:
        self._ensure_permission(actor, "assets.delete")
        asset = self.get_asset(actor, asset_id)
        self._asset_repository.unlink_asset_everywhere(asset.asset_id)
        asset.deleted_at = datetime.now(UTC)
        self._asset_repository.session.add(asset)
        self._asset_repository.session.commit()
        self._log(actor, "assets.deleted", asset.asset_id, asset.asset_name)

    def link_asset_to_ticket(self, actor: ResolvedCrmSession, ticket_id: str, asset_id: str) -> None:
        self._ensure_permission(actor, "assets.link")
        self.get_asset(actor, asset_id)
        if self._ticket_repository.get_ticket_detail(ticket_id) is None:
            raise TicketNotFoundError()
        self._asset_repository.link_to_ticket(ticket_id, asset_id, actor.crm_user.crm_user_id)

    def link_asset_to_task(self, actor: ResolvedCrmSession, task_id: str, asset_id: str) -> None:
        self._ensure_permission(actor, "assets.link")
        self.get_asset(actor, asset_id)
        if self._task_repository.get_task_detail(task_id) is None:
            raise TaskNotFoundError()
        self._asset_repository.link_to_task(task_id, asset_id, actor.crm_user.crm_user_id)

    def unlink_asset_from_ticket(self, actor: ResolvedCrmSession, ticket_id: str, asset_id: str) -> None:
        self._ensure_permission(actor, "assets.link")
        self._asset_repository.unlink_from_ticket(ticket_id, asset_id)

    def unlink_asset_from_task(self, actor: ResolvedCrmSession, task_id: str, asset_id: str) -> None:
        self._ensure_permission(actor, "assets.link")
        self._asset_repository.unlink_from_task(task_id, asset_id)

    def list_assets_for_ticket(self, actor: ResolvedCrmSession, ticket_id: str) -> list[Asset]:
        self._ensure_authenticated(actor)
        return self._asset_repository.list_assets_for_ticket(ticket_id)

    def list_assets_for_task(self, actor: ResolvedCrmSession, task_id: str) -> list[Asset]:
        self._ensure_authenticated(actor)
        return self._asset_repository.list_assets_for_task(task_id)

    def list_tickets_for_asset(self, actor: ResolvedCrmSession, asset_id: str):
        self.get_asset(actor, asset_id)
        return self._asset_repository.list_tickets_for_asset(asset_id)

    def list_tasks_for_asset(self, actor: ResolvedCrmSession, asset_id: str):
        self.get_asset(actor, asset_id)
        return self._asset_repository.list_tasks_for_asset(asset_id)

    def _update_field_values(self, asset: Asset, field_values) -> None:
        field_by_id = {field.field_id: field for field in asset.category.fields}
        value_by_field_id = {value.field_id: value for value in asset.field_values}
        for item in field_values:
            field = field_by_id.get(item.field_id)
            if field is None:
                raise AssetValidationError("Uno de los campos no pertenece a la categoria del activo.")
            raw_value = self._strategy_registry.get(field.field_type).validate(item.value, field)
            current = value_by_field_id.get(field.field_id)
            if current is None:
                asset.field_values.append(AssetFieldValue(field_id=field.field_id, raw_value=raw_value))
            else:
                current.raw_value = raw_value
        for field in asset.category.fields:
            current_value = next((value.raw_value for value in asset.field_values if value.field_id == field.field_id), "")
            if field.is_required and not current_value:
                raise AssetValidationError(f"El campo '{field.field_name}' es obligatorio.")

    def _ensure_permission(self, actor: ResolvedCrmSession, code: str) -> None:
        if not self._permission_service.resolve(actor.role_keys, actor.crm_user.crm_user_id, code):
            raise AssetAccessDeniedError()

    def _ensure_authenticated(self, actor: ResolvedCrmSession) -> None:
        if actor.crm_user is None:
            raise ApplicationError("asset_auth_required", "Debe iniciar sesion para operar activos.", 401)

    def _log(self, actor: ResolvedCrmSession, event_code: str, entity_id: str, label: str) -> None:
        self._activity_log_service.log(event_code, actor, entity_type="asset", entity_id=entity_id, entity_label=label)
