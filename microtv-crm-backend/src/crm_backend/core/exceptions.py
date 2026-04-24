"""Custom application exceptions."""


class ApplicationError(Exception):
    """Base exception for controlled API failures.

    Attributes:
        code: Stable machine-readable error code.
        message: Human-readable error message.
        status_code: HTTP status code to return.
    """

    def __init__(self, code: str, message: str, status_code: int) -> None:
        """Initialize the exception.

        Args:
            code: Stable machine-readable error code.
            message: Human-readable error message.
            status_code: HTTP status code to return.
        """

        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class InvalidCredentialsError(ApplicationError):
    """Signal that external credentials were rejected."""

    def __init__(self) -> None:
        """Initialize the exception."""

        super().__init__(code="invalid_credentials", message="Credenciales inválidas.", status_code=401)


class AuthenticationContextError(ApplicationError):
    """Signal that a JWT or auth response is structurally invalid."""

    def __init__(self, message: str = "La respuesta del servicio auth es inválida.") -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
        """

        super().__init__(code="invalid_auth_context", message=message, status_code=502)


class UpstreamAuthError(ApplicationError):
    """Signal that the external auth service failed or is unavailable."""

    def __init__(self, message: str = "No fue posible contactar al servicio auth.") -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
        """

        super().__init__(code="auth_unavailable", message=message, status_code=503)


class CrmAuthorizationError(ApplicationError):
    """Signal that the user cannot operate inside the CRM."""

    def __init__(self, message: str = "El usuario no tiene un rol local habilitado en el CRM.") -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
        """

        super().__init__(code="crm_role_required", message=message, status_code=403)


class UnauthenticatedError(ApplicationError):
    """Signal that the request lacks a valid bearer token."""

    def __init__(self, message: str = "Se requiere un token Bearer válido.") -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
        """

        super().__init__(code="unauthenticated", message=message, status_code=401)


class InventoryAccessDeniedError(ApplicationError):
    """Señala que el usuario no puede operar sobre el módulo de depósito."""

    def __init__(self, message: str = "El usuario no tiene acceso al módulo de depósito para YCC.") -> None:
        """Inicializa la excepción.

        Args:
            message: Mensaje legible para el cliente.
        """

        super().__init__(code="inventory_access_denied", message=message, status_code=403)


class InventoryAdminRequiredError(ApplicationError):
    """Señala que la operación requiere privilegios de administrador."""

    def __init__(self, message: str = "Solo un administrador puede eliminar productos del depósito.") -> None:
        """Inicializa la excepción.

        Args:
            message: Mensaje legible para el cliente.
        """

        super().__init__(code="inventory_admin_required", message=message, status_code=403)


class ClientAccessDeniedError(ApplicationError):
    """Señala que el usuario no puede administrar clientes."""

    def __init__(self, message: str = "La operación requiere rol administrador o ejecutivo.") -> None:
        super().__init__(code="client_access_denied", message=message, status_code=403)


class ClientNotFoundError(ApplicationError):
    """Señala que el cliente solicitado no existe."""

    def __init__(self) -> None:
        super().__init__(code="client_not_found", message="El cliente indicado no existe.", status_code=404)


class DuplicateClientTaxIdError(ApplicationError):
    """Señala que ya existe un cliente activo con el CUIT indicado."""

    def __init__(self) -> None:
        super().__init__(code="client_tax_id_duplicated", message="Ya existe un cliente activo con ese CUIT.", status_code=409)


class StockCategoryNotFoundError(ApplicationError):
    """Señala que la categoría solicitada no existe o no está activa."""

    def __init__(self) -> None:
        """Inicializa la excepción."""

        super().__init__(
            code="stock_category_not_found",
            message="La categoría indicada no existe o no está activa.",
            status_code=404,
        )


class StockProductNotFoundError(ApplicationError):
    """Señala que el producto solicitado no existe."""

    def __init__(self) -> None:
        """Inicializa la excepción."""

        super().__init__(
            code="stock_product_not_found",
            message="El producto indicado no existe.",
            status_code=404,
        )


class StockProductInactiveError(ApplicationError):
    """Señala que el producto existe pero no admite operaciones."""

    def __init__(self) -> None:
        """Inicializa la excepción."""

        super().__init__(
            code="stock_product_inactive",
            message="El producto indicado está inactivo y no admite operaciones.",
            status_code=409,
        )


class InvalidStockQuantityError(ApplicationError):
    """Señala que la cantidad recibida es inválida."""

    def __init__(self) -> None:
        """Inicializa la excepción."""

        super().__init__(
            code="invalid_stock_quantity",
            message="La cantidad debe ser mayor a cero.",
            status_code=422,
        )


class InsufficientStockError(ApplicationError):
    """Señala que la operación dejaría stock negativo."""

    def __init__(self) -> None:
        """Inicializa la excepción."""

        super().__init__(
            code="insufficient_stock",
            message="La operación no puede dejar stock negativo.",
            status_code=409,
        )


class DuplicateStockProductCodeError(ApplicationError):
    """Señala que el código del producto ya existe."""

    def __init__(self) -> None:
        super().__init__(
            code="stock_product_code_duplicated",
            message="El código del producto ya existe.",
            status_code=409,
        )


class InvalidStockProductImageError(ApplicationError):
    """Señala que la imagen del producto es inválida."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="invalid_stock_product_image",
            message=message,
            status_code=422,
        )


class TaskAccessDeniedError(ApplicationError):
    """Señala que el usuario no puede operar el módulo de tareas."""

    def __init__(self, message: str = "El usuario no tiene permisos para operar el módulo de tareas.") -> None:
        super().__init__(code="task_access_denied", message=message, status_code=403)


class TaskTemplateNotFoundError(ApplicationError):
    """Señala que no existe el template solicitado."""

    def __init__(self) -> None:
        super().__init__(
            code="task_template_not_found",
            message="El template de tarea indicado no existe.",
            status_code=404,
        )


class TaskNotFoundError(ApplicationError):
    """Señala que no existe la tarea solicitada."""

    def __init__(self) -> None:
        super().__init__(
            code="task_not_found",
            message="La tarea indicada no existe.",
            status_code=404,
        )


class SubtaskNotFoundError(ApplicationError):
    """Señala que no existe la subtarea solicitada."""

    def __init__(self) -> None:
        super().__init__(
            code="subtask_not_found",
            message="La subtarea indicada no existe.",
            status_code=404,
        )


class TaskValidationError(ApplicationError):
    """Señala una violación de reglas del dominio de tareas."""

    def __init__(self, message: str) -> None:
        super().__init__(code="task_validation_error", message=message, status_code=422)


class TaskConflictError(ApplicationError):
    """Señala un conflicto de estado dentro del flujo de tareas."""

    def __init__(self, message: str) -> None:
        super().__init__(code="task_conflict", message=message, status_code=409)


class InvalidTaskAttachmentError(ApplicationError):
    """Señala que el adjunto de tarea es inválido."""

    def __init__(self, message: str) -> None:
        super().__init__(code="invalid_task_attachment", message=message, status_code=422)


class TaskAttachmentNotFoundError(ApplicationError):
    """Señala que no existe el adjunto indicado."""

    def __init__(self) -> None:
        super().__init__(
            code="task_attachment_not_found",
            message="El adjunto indicado no existe.",
            status_code=404,
        )


class InventoryFlowValidationError(ApplicationError):
    """Señala una validación inválida en requests o despachos de inventario."""

    def __init__(self, message: str) -> None:
        super().__init__(code="inventory_flow_validation_error", message=message, status_code=422)


class InventoryRequestNotFoundError(ApplicationError):
    """Señala que la solicitud de inventario no existe."""

    def __init__(self) -> None:
        super().__init__(
            code="inventory_request_not_found",
            message="La solicitud de inventario indicada no existe.",
            status_code=404,
        )


class InventoryDispatchItemNotFoundError(ApplicationError):
    """Señala que el item despachado no existe."""

    def __init__(self) -> None:
        super().__init__(
            code="inventory_dispatch_item_not_found",
            message="El item despachado indicado no existe.",
            status_code=404,
        )


class TicketAccessDeniedError(ApplicationError):
    """Señala que el usuario no puede operar el módulo de tickets."""

    def __init__(self, message: str = "El usuario no tiene permisos para operar tickets.") -> None:
        super().__init__(code="ticket_access_denied", message=message, status_code=403)


class TicketNotFoundError(ApplicationError):
    """Señala que no existe el ticket solicitado."""

    def __init__(self) -> None:
        super().__init__(
            code="ticket_not_found",
            message="El ticket indicado no existe.",
            status_code=404,
        )


class TicketValidationError(ApplicationError):
    """Señala una violación de reglas del dominio de tickets."""

    def __init__(self, message: str) -> None:
        super().__init__(code="ticket_validation_error", message=message, status_code=422)


class TicketConflictError(ApplicationError):
    """Señala un conflicto de estado dentro del flujo de tickets."""

    def __init__(self, message: str) -> None:
        super().__init__(code="ticket_conflict", message=message, status_code=409)


class NotificationNotFoundError(ApplicationError):
    """Señala que la notificación indicada no existe."""

    def __init__(self) -> None:
        super().__init__(code="notification_not_found", message="La notificación indicada no existe.", status_code=404)


class NotificationAccessDeniedError(ApplicationError):
    """Señala que el usuario no puede acceder a la notificación indicada."""

    def __init__(self) -> None:
        super().__init__(code="notification_access_denied", message="No tenés acceso a esa notificación.", status_code=403)
