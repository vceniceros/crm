"""Asset service exceptions."""

from crm_backend.core.exceptions import ApplicationError


class AssetAccessDeniedError(ApplicationError):
    def __init__(self, message: str = "No tenes permisos para operar activos.") -> None:
        super().__init__(code="asset_access_denied", message=message, status_code=403)


class AssetCategoryNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(code="asset_category_not_found", message="La categoria de activo indicada no existe.", status_code=404)


class AssetNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(code="asset_not_found", message="El activo indicado no existe.", status_code=404)


class AssetValidationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(code="asset_validation_error", message=message, status_code=422)
