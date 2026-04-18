"""Service exports for the CRM backend."""

from crm_backend.services.auth_service import AuthApplicationService
from crm_backend.services.client_service import (
	ClientApplicationService,
	ClientLocationCommand,
	CreateClientCommand,
	UpdateClientCommand,
)
from crm_backend.services.location_service import CreateLocationCommand, LocationApplicationService
from crm_backend.services.material_flow_service import InventoryRequestFacade, TaskMaterialFlowFacade
from crm_backend.services.role_resolution_service import RoleResolutionService
from crm_backend.services.stock_service import CreateStockProductCommand, StockApplicationService
from crm_backend.services.tasks import TaskApplicationService

__all__ = [
	"AuthApplicationService",
	"ClientApplicationService",
	"ClientLocationCommand",
	"CreateClientCommand",
	"UpdateClientCommand",
	"CreateLocationCommand",
	"LocationApplicationService",
	"InventoryRequestFacade",
	"TaskMaterialFlowFacade",
	"RoleResolutionService",
	"CreateStockProductCommand",
	"StockApplicationService",
	"TaskApplicationService",
]
