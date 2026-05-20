"""Repository exports for the CRM backend."""

from crm_backend.repositories.client_repository import ClientRepository
from crm_backend.repositories.asset_repository import AssetRepository
from crm_backend.repositories.crm_role_repository import CrmRoleRepository
from crm_backend.repositories.crm_user_repository import CrmUserRepository
from crm_backend.repositories.inventory_flow_repository import InventoryFlowRepository
from crm_backend.repositories.location_repository import LocationRepository
from crm_backend.repositories.notification_repository import NotificationRepository
from crm_backend.repositories.push_subscription_repository import PushSubscriptionRepository
from crm_backend.repositories.activity_log_repository import ActivityLogRepository
from crm_backend.repositories.permission_repository import PermissionRepository
from crm_backend.repositories.stock_category_repository import StockCategoryRepository
from crm_backend.repositories.stock_product_repository import StockProductRepository
from crm_backend.repositories.task_repository import TaskRepository
from crm_backend.repositories.task_template_repository import TaskTemplateRepository
from crm_backend.repositories.ticket_repository import TicketRepository

__all__ = [
	"ClientRepository",
	"AssetRepository",
	"CrmRoleRepository",
	"CrmUserRepository",
	"InventoryFlowRepository",
	"LocationRepository",
	"NotificationRepository",
	"PushSubscriptionRepository",
	"ActivityLogRepository",
	"PermissionRepository",
	"StockCategoryRepository",
	"StockProductRepository",
	"TaskRepository",
	"TaskTemplateRepository",
	"TicketRepository",
]
