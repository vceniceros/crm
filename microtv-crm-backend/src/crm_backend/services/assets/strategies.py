"""Validation strategies for typed asset field values."""

from crm_backend.models import AssetCategoryField
from crm_backend.services.assets.exceptions import AssetValidationError


class AssetFieldValueStrategy:
    """Base strategy for validating an asset field value."""

    def validate(self, value: str, field: AssetCategoryField) -> str:
        raise NotImplementedError


class StringFieldValueStrategy(AssetFieldValueStrategy):
    def validate(self, value: str, field: AssetCategoryField) -> str:
        cleaned = (value or "").strip()
        if field.is_required and not cleaned:
            raise AssetValidationError(f"El campo '{field.field_name}' es obligatorio.")
        return cleaned


class NumberFieldValueStrategy(AssetFieldValueStrategy):
    def validate(self, value: str, field: AssetCategoryField) -> str:
        stripped = (value or "").strip()
        if field.is_required and not stripped:
            raise AssetValidationError(f"El campo '{field.field_name}' es obligatorio.")
        if stripped:
            try:
                float(stripped)
            except ValueError as exc:
                raise AssetValidationError(f"El campo '{field.field_name}' debe ser un numero. Valor recibido: '{stripped}'.") from exc
        return stripped


class AssetFieldValueStrategyRegistry:
    """Registry for asset field value strategies."""

    def __init__(self) -> None:
        self._strategies = {
            "string": StringFieldValueStrategy(),
            "number": NumberFieldValueStrategy(),
        }

    def get(self, field_type: str) -> AssetFieldValueStrategy:
        strategy = self._strategies.get(field_type)
        if strategy is None:
            raise AssetValidationError(f"Tipo de campo no soportado: '{field_type}'.")
        return strategy
