"""Service exports for the CRM backend."""

from crm_backend.services.auth_service import AuthApplicationService
from crm_backend.services.client_service import (
	ClientApplicationService,
	ClientLocationCommand,
	CreateClientCommand,
	UpdateClientCommand,
)
from crm_backend.services.dashboard_service import DashboardService
from crm_backend.services.location_service import CreateLocationCommand, LocationApplicationService
from crm_backend.services.material_flow_service import InventoryRequestFacade, TaskMaterialFlowFacade
from crm_backend.services.notification_service import NotificationService
from crm_backend.services.role_resolution_service import RoleResolutionService
from crm_backend.services.reports_service import ReportsService
from crm_backend.services.settings_service import SettingsService
from crm_backend.services.stock_service import CreateStockProductCommand, StockApplicationService
from crm_backend.services.ticket_service import TicketApplicationService
from crm_backend.services.tasks import TaskApplicationService

__all__ = [
	"AuthApplicationService",
	"ClientApplicationService",
	"ClientLocationCommand",
	"CreateClientCommand",
	"UpdateClientCommand",
	"DashboardService",
	"CreateLocationCommand",
	"LocationApplicationService",
	"InventoryRequestFacade",
	"TaskMaterialFlowFacade",
	"NotificationService",
	"RoleResolutionService",
	"ReportsService",
	"SettingsService",
	"CreateStockProductCommand",
	"StockApplicationService",
	"TicketApplicationService",
	"TaskApplicationService",
]
