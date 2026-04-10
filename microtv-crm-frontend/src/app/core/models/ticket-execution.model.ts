import { TicketPriorityTone, TicketStatusTone } from './dashboard.model';
import { TicketAttachment } from './ticket-attachment.model';
import { TicketDispatchItem } from './ticket-dispatch.model';
import { TicketInventoryRequest } from './ticket-inventory-request.model';
import { TicketResolutionNote } from './ticket-resolution-note.model';

export interface TicketExecutionDefinition {
  id: string;
  title: string;
  description: string;
  category: string;
  affectedDevice: string;
  status: string;
  statusTone: TicketStatusTone;
  priority: string;
  priorityTone: TicketPriorityTone;
  createdAt: string;
  technicianAssigneeId: number | string | null;
  technicianAssigneeName?: string | null;
  technicianAssigneeInitials?: string | null;
  depositAssigneeId: number | string | null;
  depositAssigneeName?: string | null;
  depositAssigneeInitials?: string | null;
}

export interface TicketExecutionData {
  tickets: TicketExecutionDefinition[];
}

export interface TicketExecutionState {
  ticketId: string;
  resolutionComment: string;
  resolutionUpdatedAt: string;
  attachments: TicketAttachment[];
  inventoryRequests: TicketInventoryRequest[];
  dispatchedItems: TicketDispatchItem[];
  updatedAt: string;
}

export interface TicketExecutionStateData {
  execution: TicketExecutionState[];
}

export interface TicketExecutionPermissions {
  canEditResolution: boolean;
  canManageAttachments: boolean;
  canCreateInventoryRequests: boolean;
  canReviewInventoryRequests: boolean;
  canManageDispatch: boolean;
  canViewDispatch: boolean;
}

export interface TicketExecutionItem {
  id: string;
  title: string;
  description: string;
  category: string;
  affectedDevice: string;
  status: string;
  statusTone: TicketStatusTone;
  priority: string;
  priorityTone: TicketPriorityTone;
  createdAt: string;
  assigneeId: number | string | null;
  assigneeName?: string | null;
  assigneeInitials?: string | null;
  depositAssigneeId: number | string | null;
  depositAssigneeName?: string | null;
  depositAssigneeInitials?: string | null;
  resolutionNote: TicketResolutionNote;
  attachments: TicketAttachment[];
  inventoryRequests: TicketInventoryRequest[];
  dispatchedItems: TicketDispatchItem[];
  updatedAt: string;
  permissions: TicketExecutionPermissions;
}