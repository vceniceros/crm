"""FastAPI dependencies for the CRM backend."""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from crm_backend.adapters import AuthServiceAdapter
from crm_backend.core.config import Settings, get_settings
from crm_backend.core.exceptions import UnauthenticatedError
from crm_backend.db import get_db_session
from crm_backend.infrastructure.product_image_storage import ProductImageStorage
from crm_backend.infrastructure.task_media_storage import TaskMediaStorageFacade
from crm_backend.repositories import (
    ActivityLogRepository,
    ClientRepository,
    CrmRoleRepository,
    CrmUserRepository,
    InventoryFlowRepository,
    LocationRepository,
    NotificationRepository,
    PermissionRepository,
    PushSubscriptionRepository,
    StockCategoryRepository,
    StockProductRepository,
    TaskRepository,
    TaskTemplateRepository,
    TicketRepository,
)
from crm_backend.services import (
    ActivityLogService,
    AuthApplicationService,
    ClientApplicationService,
    InventoryRequestFacade,
    LocationApplicationService,
    NotificationService,
    PermissionService,
    RoleResolutionService,
    StockApplicationService,
    TaskApplicationService,
    TaskMaterialFlowFacade,
    TicketApplicationService,
    TaskExportService,
    TaskPreFormService,
    TaskSatisfactionFormService,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.dashboard_service import DashboardService
from crm_backend.services.reports_service import ReportsService
from crm_backend.services.settings_service import SettingsService
from crm_backend.services.push_notification_service import PushNotificationService


def get_auth_service_adapter(settings: Settings = Depends(get_settings)) -> AuthServiceAdapter:
    """Provide the external auth adapter.

    Args:
        settings: Application settings.

    Returns:
        AuthServiceAdapter: Adapter bound to current settings.
    """

    return AuthServiceAdapter(settings)


def get_crm_user_repository(session: Session = Depends(get_db_session)) -> CrmUserRepository:
    """Provide the CRM user repository.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        CrmUserRepository: Repository bound to the current session.
    """

    return CrmUserRepository(session)


def get_crm_role_repository(session: Session = Depends(get_db_session)) -> CrmRoleRepository:
    """Provide the CRM role repository.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        CrmRoleRepository: Repository bound to the current session.
    """

    return CrmRoleRepository(session)


def get_activity_log_repository(session: Session = Depends(get_db_session)) -> ActivityLogRepository:
    """Provide the activity log repository."""

    return ActivityLogRepository(session)


def get_activity_log_service(
    activity_log_repository: ActivityLogRepository = Depends(get_activity_log_repository),
) -> ActivityLogService:
    """Provide the activity log service."""

    return ActivityLogService(activity_log_repository)


def get_client_repository(session: Session = Depends(get_db_session)) -> ClientRepository:
    """Provide the client repository."""

    return ClientRepository(session)


def get_client_application_service(
    repository: ClientRepository = Depends(get_client_repository),
) -> ClientApplicationService:
    """Provide the client application service."""

    return ClientApplicationService(repository)


def get_location_repository(session: Session = Depends(get_db_session)) -> LocationRepository:
    """Provide the reusable location repository."""

    return LocationRepository(session)


def get_location_application_service(
    repository: LocationRepository = Depends(get_location_repository),
) -> LocationApplicationService:
    """Provide the reusable location application service."""

    return LocationApplicationService(repository)


def get_role_resolution_service(
    settings: Settings = Depends(get_settings),
    role_repository: CrmRoleRepository = Depends(get_crm_role_repository),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> RoleResolutionService:
    """Provide the local role resolution service.

    Args:
        settings: Application settings.
        role_repository: CRM role repository.
        user_repository: CRM user repository.

    Returns:
        RoleResolutionService: Configured local role resolution service.
    """

    return RoleResolutionService(settings, role_repository, user_repository)


def get_auth_application_service(
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
    role_resolution_service: RoleResolutionService = Depends(get_role_resolution_service),
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
) -> AuthApplicationService:
    """Provide the CRM authentication application service.

    Args:
        auth_adapter: External auth adapter.
        user_repository: CRM user repository.
        role_resolution_service: Local role resolution service.

    Returns:
        AuthApplicationService: Configured authentication service.
    """

    return AuthApplicationService(
        auth_adapter,
        user_repository,
        role_resolution_service,
        activity_log_service=activity_log_service,
    )


def get_stock_category_repository(session: Session = Depends(get_db_session)) -> StockCategoryRepository:
    """Provide the stock category repository.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        StockCategoryRepository: Repository bound to the current session.
    """

    return StockCategoryRepository(session)


def get_stock_product_repository(session: Session = Depends(get_db_session)) -> StockProductRepository:
    """Provide the stock product repository.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        StockProductRepository: Repository bound to the current session.
    """

    return StockProductRepository(session)


def get_inventory_flow_repository(session: Session = Depends(get_db_session)) -> InventoryFlowRepository:
    """Provide the generic inventory flow repository."""

    return InventoryFlowRepository(session)


def get_product_image_storage(settings: Settings = Depends(get_settings)) -> ProductImageStorage:
    """Provide the local product image storage service."""

    return ProductImageStorage(settings)


def get_task_media_storage(settings: Settings = Depends(get_settings)) -> TaskMediaStorageFacade:
    """Provide the local task media storage facade."""

    return TaskMediaStorageFacade(settings)


def get_task_template_repository(session: Session = Depends(get_db_session)) -> TaskTemplateRepository:
    """Provide the task template repository."""

    return TaskTemplateRepository(session)


def get_task_repository(session: Session = Depends(get_db_session)) -> TaskRepository:
    """Provide the task repository."""

    return TaskRepository(session)


def get_ticket_repository(session: Session = Depends(get_db_session)) -> TicketRepository:
    """Provide the ticket repository."""

    return TicketRepository(session)


def get_notification_repository(session: Session = Depends(get_db_session)) -> NotificationRepository:
    """Provide the notification repository."""

    return NotificationRepository(session)


def get_push_subscription_repository(session: Session = Depends(get_db_session)) -> PushSubscriptionRepository:
    """Provide the push subscription repository."""

    return PushSubscriptionRepository(session)


def get_permission_repository(session: Session = Depends(get_db_session)) -> PermissionRepository:
    """Provide the permission repository."""

    return PermissionRepository(session)


def get_push_notification_service(
    push_subscription_repository: PushSubscriptionRepository = Depends(get_push_subscription_repository),
    settings: Settings = Depends(get_settings),
) -> PushNotificationService:
    """Provide the Web Push notification service."""

    return PushNotificationService(push_subscription_repository=push_subscription_repository, settings=settings)


def get_notification_service(
    notification_repository: NotificationRepository = Depends(get_notification_repository),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
    push_notification_service: PushNotificationService = Depends(get_push_notification_service),
) -> NotificationService:
    """Provide the in-app notification service."""

    return NotificationService(notification_repository, user_repository, push_notification_service=push_notification_service)


def get_permission_service(
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> PermissionService:
    """Provide the permission service."""

    return PermissionService(permission_repository, user_repository)


def extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    """Extract the bearer token from the Authorization header.

    Args:
        authorization: Raw Authorization header.

    Returns:
        str: Bearer token value.
    """

    if authorization is None:
        raise UnauthenticatedError()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthenticatedError()
    return token


def get_authenticated_crm_session(
    access_token: str = Depends(extract_bearer_token),
    auth_service: AuthApplicationService = Depends(get_auth_application_service),
) -> ResolvedCrmSession:
    """Resolve a bearer token into a CRM session.

    Args:
        access_token: Bearer token extracted from the header.
        auth_service: Authentication application service.

    Returns:
        ResolvedCrmSession: Authenticated CRM session.
    """

    return auth_service.resolve_session_from_token(access_token)


def get_stock_application_service(
    settings: Settings = Depends(get_settings),
    category_repository: StockCategoryRepository = Depends(get_stock_category_repository),
    product_repository: StockProductRepository = Depends(get_stock_product_repository),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
) -> StockApplicationService:
    """Provide the stock application service.

    Args:
        settings: Application settings.
        category_repository: Stock category repository.
        product_repository: Stock product repository.

    Returns:
        StockApplicationService: Configured stock application service.
    """

    return StockApplicationService(
        settings,
        category_repository,
        product_repository,
        notification_service=notification_service,
        user_repository=user_repository,
        permission_service=permission_service,
        activity_log_service=activity_log_service,
    )


def get_task_material_flow_facade(
    task_repository: TaskRepository = Depends(get_task_repository),
    product_repository: StockProductRepository = Depends(get_stock_product_repository),
    inventory_flow_repository: InventoryFlowRepository = Depends(get_inventory_flow_repository),
    ticket_repository: TicketRepository = Depends(get_ticket_repository),
    notification_service: NotificationService = Depends(get_notification_service),
) -> TaskMaterialFlowFacade:
    """Provide the task material flow facade."""

    return TaskMaterialFlowFacade(task_repository, product_repository, inventory_flow_repository, ticket_repository, notification_service)


def get_inventory_request_facade(
    task_repository: TaskRepository = Depends(get_task_repository),
    product_repository: StockProductRepository = Depends(get_stock_product_repository),
    inventory_flow_repository: InventoryFlowRepository = Depends(get_inventory_flow_repository),
    task_material_flow: TaskMaterialFlowFacade = Depends(get_task_material_flow_facade),
    ticket_repository: TicketRepository = Depends(get_ticket_repository),
    role_repository: CrmRoleRepository = Depends(get_crm_role_repository),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
    notification_service: NotificationService = Depends(get_notification_service),
) -> InventoryRequestFacade:
    """Provide the inventory request facade."""

    return InventoryRequestFacade(
        task_repository,
        product_repository,
        inventory_flow_repository,
        task_material_flow,
        ticket_repository,
        role_repository,
        user_repository,
        notification_service,
    )


def get_task_application_service(
    template_repository: TaskTemplateRepository = Depends(get_task_template_repository),
    task_repository: TaskRepository = Depends(get_task_repository),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
    task_media_storage: TaskMediaStorageFacade = Depends(get_task_media_storage),
    task_material_flow: TaskMaterialFlowFacade = Depends(get_task_material_flow_facade),
    notification_service: NotificationService = Depends(get_notification_service),
) -> TaskApplicationService:
    """Provide the task application service."""

    return TaskApplicationService(
        template_repository=template_repository,
        task_repository=task_repository,
        user_repository=user_repository,
        task_media_storage=task_media_storage,
        task_material_flow=task_material_flow,
        notification_service=notification_service,
    )


def get_ticket_application_service(
    ticket_repository: TicketRepository = Depends(get_ticket_repository),
    client_repository: ClientRepository = Depends(get_client_repository),
    location_repository: LocationRepository = Depends(get_location_repository),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
    role_repository: CrmRoleRepository = Depends(get_crm_role_repository),
    task_media_storage: TaskMediaStorageFacade = Depends(get_task_media_storage),
    notification_service: NotificationService = Depends(get_notification_service),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
) -> TicketApplicationService:
    """Provide the ticket application service."""

    return TicketApplicationService(
        ticket_repository=ticket_repository,
        client_repository=client_repository,
        location_repository=location_repository,
        user_repository=user_repository,
        role_repository=role_repository,
        media_storage=task_media_storage,
        notification_service=notification_service,
        permission_service=permission_service,
        activity_log_service=activity_log_service,
    )


def get_dashboard_service(session: Session = Depends(get_db_session)) -> DashboardService:
    """Provide the dashboard service."""

    return DashboardService(session)


def get_reports_service(session: Session = Depends(get_db_session)) -> ReportsService:
    """Provide the reports service."""

    return ReportsService(session)


def get_settings_service(
    session: Session = Depends(get_db_session),
    permission_service: PermissionService = Depends(get_permission_service),
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
) -> SettingsService:
    """Provide the settings service."""

    return SettingsService(
        session,
        permission_service=permission_service,
        activity_log_service=activity_log_service,
    )


def get_satisfaction_form_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> "PublicSatisfactionFormService":
    """Provide the satisfaction form service."""
    from crm_backend.services.satisfaction_form_service import PublicSatisfactionFormService  # noqa: PLC0415
    return PublicSatisfactionFormService(
        session=session,
        satisfaction_images_dir=settings.satisfaction_images_dir,
        satisfaction_videos_dir=settings.satisfaction_videos_dir,
        expiry_hours=settings.satisfaction_form_expiry_hours,
        satisfaction_images_max_bytes=settings.satisfaction_images_max_bytes,
        satisfaction_videos_max_bytes=settings.satisfaction_videos_max_bytes,
        satisfaction_images_public_prefix=settings.satisfaction_images_public_prefix,
        satisfaction_videos_public_prefix=settings.satisfaction_videos_public_prefix,
        notification_service=notification_service,
        user_repository=user_repository,
    )


def get_ticket_export_service(
    settings: Settings = Depends(get_settings),
) -> "TicketExportService":
    """Provide the ticket export service."""
    from crm_backend.services.ticket_export_service import TicketExportService  # noqa: PLC0415
    return TicketExportService(
        media_root_dir=settings.crm_media_root_path,
        media_public_url=settings.crm_media_public_url,
        legacy_public_dir=settings.public_dir,
    )


def get_task_export_service(
    settings: Settings = Depends(get_settings),
) -> TaskExportService:
    """Provide the task export service."""
    return TaskExportService(
        media_root_dir=settings.crm_media_root_path,
        media_public_url=settings.crm_media_public_url,
        legacy_public_dir=settings.public_dir,
    )


def get_task_satisfaction_form_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> TaskSatisfactionFormService:
    """Provide task satisfaction form service."""
    return TaskSatisfactionFormService(
        session=session,
        expiry_hours=settings.satisfaction_form_expiry_hours,
        notification_service=notification_service,
        user_repository=user_repository,
    )


def get_task_pre_form_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> TaskPreFormService:
    """Provide task pre-form service."""
    return TaskPreFormService(
        session=session,
        expiry_hours=settings.satisfaction_form_expiry_hours,
        notification_service=notification_service,
        user_repository=user_repository,
    )
