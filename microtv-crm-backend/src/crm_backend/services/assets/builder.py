"""Builder for asset aggregates."""

from crm_backend.models import Asset, AssetCategory, AssetCategoryField, AssetFieldValue
from crm_backend.services.assets.exceptions import AssetValidationError
from crm_backend.services.assets.strategies import AssetFieldValueStrategyRegistry


class AssetBuilder:
    """Build an Asset with validated field values."""

    def __init__(self) -> None:
        self._category: AssetCategory | None = None
        self._client_id: str | None = None
        self._parent_asset_id: str | None = None
        self._name: str | None = None
        self._notes: str | None = None
        self._field_values: dict[str, str] = {}

    def with_category(self, category: AssetCategory) -> "AssetBuilder":
        self._category = category
        return self

    def with_client(self, client_id: str) -> "AssetBuilder":
        self._client_id = client_id
        return self

    def with_parent_asset(self, asset_id: str | None) -> "AssetBuilder":
        self._parent_asset_id = asset_id
        return self

    def with_name(self, name: str) -> "AssetBuilder":
        self._name = name.strip()
        return self

    def with_notes(self, notes: str | None) -> "AssetBuilder":
        self._notes = notes.strip() if isinstance(notes, str) and notes.strip() else None
        return self

    def with_field_value(
        self,
        field: AssetCategoryField,
        raw_value: str,
        strategy_registry: AssetFieldValueStrategyRegistry,
    ) -> "AssetBuilder":
        strategy = strategy_registry.get(field.field_type)
        self._field_values[field.field_id] = strategy.validate(raw_value, field)
        return self

    def build(self, actor_crm_user_id: str) -> Asset:
        if self._category is None:
            raise AssetValidationError("La categoria es obligatoria.")
        if not self._client_id:
            raise AssetValidationError("El cliente es obligatorio.")
        if not self._name:
            raise AssetValidationError("El nombre del activo es obligatorio.")
        for field in self._category.fields:
            if field.is_required and not self._field_values.get(field.field_id):
                raise AssetValidationError(f"El campo '{field.field_name}' es obligatorio.")
        asset = Asset(
            category_id=self._category.asset_category_id,
            client_id=self._client_id,
            parent_asset_id=self._parent_asset_id,
            asset_name=self._name,
            notes=self._notes,
            created_by_crm_user_id=actor_crm_user_id,
        )
        asset.field_values = [AssetFieldValue(field_id=field_id, raw_value=value) for field_id, value in self._field_values.items()]
        return asset
