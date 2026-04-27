"""Schemas HTTP del módulo real de depósito."""

from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class StockCategoryResponse(BaseModel):
    """Expone una categoría de depósito al frontend.

    Attributes:
        id: Identificador interno.
        code: Código estable.
        name: Nombre visible.
        is_active: Estado operativo.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    is_active: bool


class StockProductResponse(BaseModel):
    """Expone un producto de depósito al frontend.

    Attributes:
        id: Alias legacy del identificador interno.
        product_id: Identificador interno para requests y relaciones.
        product_code: Código visible del producto.
        name: Alias legacy del nombre del producto.
        product_name: Nombre del producto.
        category_id: Identificador de categoría.
        category_name: Nombre visible de categoría.
        current_stock: Stock actual disponible.
        image_url: Imagen opcional.
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
        is_active: Estado operativo.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_code: str
    name: str
    product_name: str
    category_id: str
    category_name: str
    current_stock: int
    image_url: str | None
    requires_tracking: bool
    created_at: datetime
    updated_at: datetime | None
    is_active: bool


class CreateStockProductRequest(BaseModel):
    """Payload de alta de producto.

    Attributes:
        name: Nombre obligatorio del producto.
        product_code: Código visible obligatorio del producto.
        category_id: Categoría obligatoria.
        initial_stock: Stock inicial.
        image_url: Imagen opcional.
    """

    name: str = Field(..., min_length=1, max_length=160, validation_alias=AliasChoices("name", "product_name"))
    product_code: str = Field(..., min_length=3, max_length=100)
    category_id: str
    initial_stock: int = Field(default=0, ge=0, validation_alias=AliasChoices("initial_stock", "stock_initial"))
    image_url: str | None = Field(default=None, max_length=500)
    requires_tracking: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Normaliza el nombre ingresado.

        Args:
            value: Nombre crudo recibido.

        Returns:
            str: Nombre saneado.
        """

        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre es obligatorio.")
        return normalized

    @field_validator("product_code")
    @classmethod
    def normalize_product_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("El código del producto es obligatorio.")
        return normalized

    @field_validator("image_url")
    @classmethod
    def normalize_image_url(cls, value: str | None) -> str | None:
        """Convierte strings vacíos en nulos.

        Args:
            value: URL cruda.

        Returns:
            str | None: URL saneada.
        """

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class StockAdjustmentRequest(BaseModel):
    """Payload de ajuste simple de stock.

    Attributes:
        quantity: Cantidad positiva a mover.
    """

    quantity: int = Field(..., gt=0)