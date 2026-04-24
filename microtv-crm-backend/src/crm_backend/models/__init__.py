"""ORM models for the CRM backend."""

from crm_backend.models.crm_role import CrmRole
from crm_backend.models.crm_user import CrmUser
from crm_backend.models.crm_user_role import CrmUserRole
from crm_backend.models.stock_category import StockCategory
from crm_backend.models.stock_level import StockLevel
from crm_backend.models.stock_movement import StockMovement, StockMovementType
from crm_backend.models.stock_product import StockProduct
from crm_backend.models.material_flow import (
	InventoryDispatch,
	InventoryDispatchItem,
	InventoryRequest,
	InventoryRequestItem,
	InventoryRequestStatus,
	InventorySourceType,
	TaskRequiredMaterial,
	TemplateMaterial,
)
from crm_backend.models.task_reference import Client, ClientLocation, Location
from crm_backend.models.task_execution import (
	Subtask,
	SubtaskAssignment,
	TaskAttachment,
	TaskAttachmentType,
	SubtaskChecklistProgress,
	SubtaskItemValue,
	SubtaskStatus,
	SubtaskTransition,
	Task,
	TaskAuditEvent,
	TaskComment,
	TaskCommentType,
	TaskStatus,
	TransitionAction,
)
from crm_backend.models.ticket import (
	Ticket,
	TicketAssignmentHistory,
	TicketAttachment,
	TicketAttachmentType,
	TicketAuditEvent,
	TicketComment,
	TicketCommentType,
	TicketPriority,
	TicketStatus,
	TicketStatusTransition,
	TicketTransitionAction,
)
from crm_backend.models.task_template import NextAssignmentPolicy, TaskTemplate, TaskTemplateItem, TaskTemplateSubtask, TemplateItemType
from crm_backend.models.warehouse import Warehouse
from crm_backend.models.notification import Notification, NotificationEntityType, NotificationType
from crm_backend.models.settings import CrmCategory, CrmPriority, CrmStatus, NotificationRule, SlaRule

__all__ = [
	"CrmRole",
	"CrmUser",
	"CrmUserRole",
	"StockCategory",
	"StockLevel",
	"StockMovement",
	"StockMovementType",
	"StockProduct",
	"InventoryDispatch",
	"InventoryDispatchItem",
	"InventoryRequest",
	"InventoryRequestItem",
	"InventoryRequestStatus",
	"InventorySourceType",
	"TaskRequiredMaterial",
	"TemplateMaterial",
	"Client",
	"ClientLocation",
	"Location",
	"Subtask",
	"SubtaskAssignment",
	"TaskAttachment",
	"TaskAttachmentType",
	"SubtaskChecklistProgress",
	"SubtaskItemValue",
	"SubtaskStatus",
	"SubtaskTransition",
	"Task",
	"TaskAuditEvent",
	"TaskComment",
	"TaskCommentType",
	"TaskStatus",
	"TaskTemplate",
	"TaskTemplateItem",
	"TaskTemplateSubtask",
	"TemplateItemType",
	"NextAssignmentPolicy",
	"TransitionAction",
	"Ticket",
	"TicketAssignmentHistory",
	"TicketAttachment",
	"TicketAttachmentType",
	"TicketAuditEvent",
	"TicketComment",
	"TicketCommentType",
	"TicketPriority",
	"TicketStatus",
	"TicketStatusTransition",
	"TicketTransitionAction",
	"Warehouse",
	"Notification",
	"NotificationEntityType",
	"NotificationType",
	"CrmCategory",
	"CrmPriority",
	"CrmStatus",
	"SlaRule",
	"NotificationRule",
]
