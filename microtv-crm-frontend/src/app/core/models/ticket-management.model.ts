import { TicketPriorityTone, TicketStatusTone } from './dashboard.model';
import { InventoryDispatch, InventoryRequest } from './inventory-flow.model';
import { AppLocation } from './location.model';

export type TicketStatus = 'OPEN' | 'IN_PROGRESS' | 'ON_HOLD' | 'RESOLVED' | 'PENDING_APPROVAL' | 'CLOSED';
export type TicketPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface TicketRoleOption {
  crm_role_id: string;
  role_key: string;
  role_label: string;
}

export interface TicketClientLocation {
  location_id: string;
  latitude: number;
  longitude: number;
  address_label: string | null;
  formatted_address: string | null;
}

export interface TicketClientOption {
  client_id: string;
  business_name: string;
  tax_id: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
  location: TicketClientLocation | null;
}

export interface TicketAttachment {
  id: string;
  fileName: string;
  fileType: string;
  kind: 'image' | 'video' | 'other';
  context?: string | null;
  publicUrl?: string | null;
  storagePath?: string | null;
  previewUrl?: string | null;
  size?: number | null;
}

export interface TicketComment {
  ticket_comment_id: string;
  author_crm_user_id: string;
  author_display_name: string | null;
  comment_type: 'general' | 'system' | 'closure' | string;
  body: string;
  created_at: string;
  location: TicketLocation | null;
  attachments: TicketAttachment[];
}

export interface TicketStatusTransition {
  ticket_status_transition_id: string;
  from_status: TicketStatus | string;
  to_status: TicketStatus | string;
  action: string;
  performed_by_crm_user_id: string;
  performed_by_display_name: string | null;
  ticket_comment_id: string | null;
  created_at: string;
}

export interface TicketAssignmentHistory {
  ticket_assignment_id: string;
  previous_role_id: string | null;
  previous_role_key: string | null;
  previous_user_id: string | null;
  previous_user_display_name: string | null;
  assigned_role_id: string | null;
  assigned_role_key: string | null;
  assigned_user_id: string | null;
  assigned_user_display_name: string | null;
  assigned_by_crm_user_id: string;
  assigned_by_display_name: string | null;
  notes: string | null;
  created_at: string;
}

export interface TicketAuditEvent {
  ticket_audit_event_id: string;
  event_type: string;
  actor_crm_user_id: string;
  payload_json: Record<string, unknown>;
  created_at: string;
}

export interface TicketLocation {
  location_id: string;
  latitude: number;
  longitude: number;
  address_label: string | null;
  formatted_address: string | null;
}

export interface TicketSummary {
  ticket_id: string;
  ticket_number: string;
  title: string;
  description: string;
  client_id: string;
  client_name: string;
  location_id: string;
  location: TicketLocation | null;
  status: TicketStatus;
  priority: TicketPriority;
  assigned_role_id: string | null;
  assigned_role_key: string | null;
  assigned_role_label: string | null;
  assigned_user_id: string | null;
  assigned_user_display_name: string | null;
  created_by_crm_user_id: string;
  created_by_display_name: string | null;
  resolved_by_crm_user_id: string | null;
  resolved_by_display_name: string | null;
  resolved_at: string | null;
  closed_by_crm_user_id: string | null;
  closed_by_display_name: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketDetail extends TicketSummary {
  comments: TicketComment[];
  status_history: TicketStatusTransition[];
  assignment_history: TicketAssignmentHistory[];
  audit_events: TicketAuditEvent[];
  inventory_requests: InventoryRequest[];
  dispatches: InventoryDispatch[];
}

export interface CreateTicketRequest {
  title: string;
  client_id: string;
  location_id: string | null;
  description: string;
  priority: TicketPriority;
  assigned_role_id: string | null;
  assigned_user_id: string | null;
}

export interface AssignTicketRequest {
  assigned_role_id: string | null;
  assigned_user_id: string | null;
  notes?: string | null;
}

export interface CreateTicketCommentRequest {
  body: string;
  location_id?: string | null;
  attachment_ids?: string[];
}

export interface UpdateTicketStatusRequest {
  to_status: 'OPEN' | 'IN_PROGRESS' | 'ON_HOLD' | 'RESOLVED';
  comment?: string | null;
  attachment_ids?: string[];
}

export interface TicketStatusTransitionOption {
  toStatus: UpdateTicketStatusRequest['to_status'];
  label: string;
}

export interface CloseTicketRequest {
  comment: string;
  attachment_ids?: string[];
}

export interface ApproveTicketRequest {
  comment?: string | null;
}

export interface RejectTicketApprovalRequest {
  comment: string;
}

export interface ReopenTicketRequest {
  comment: string;
}

export interface TicketTableItem {
  ticketId: string;
  ticketNumber: string;
  title: string;
  client: string;
  location: string;
  mapsUrl: string | null;
  statusKey: string;
  status: string;
  statusTone: TicketStatusTone;
  priority: string;
  priorityTone: TicketPriorityTone;
  assignedTo: string;
  assignedUserId: string | null;
  assignedRoleId: string | null;
  assignedRoleKey: string | null;
  selfAssignable?: boolean;
  createdAtRaw: string;
  createdAt: string;
  updatedAtRaw: string;
  updatedAt: string;
}

export function formatTicketStatus(status: TicketStatus | string): string {
  switch (status) {
    case 'OPEN':
      return 'Abierto';
    case 'IN_PROGRESS':
      return 'En gestión';
    case 'ON_HOLD':
      return 'En espera';
    case 'RESOLVED':
      return 'Resuelto';
    case 'PENDING_APPROVAL':
      return 'Pendiente de aprobación';
    case 'CLOSED':
      return 'Cerrado';
    default:
      return status;
  }
}

export function formatTicketPriority(priority: TicketPriority | string): string {
  switch (priority) {
    case 'LOW':
      return 'Baja';
    case 'MEDIUM':
      return 'Media';
    case 'HIGH':
      return 'Alta';
    case 'CRITICAL':
      return 'Crítica';
    default:
      return priority;
  }
}

export function toTicketStatusTone(status: TicketStatus | string): TicketStatusTone {
  switch (status) {
    case 'IN_PROGRESS':
      return 'progress';
    case 'ON_HOLD':
      return 'warning';
    case 'PENDING_APPROVAL':
      return 'warning';
    case 'RESOLVED':
    case 'CLOSED':
      return 'success';
    default:
      return 'neutral';
  }
}

export function toTicketPriorityTone(priority: TicketPriority | string): TicketPriorityTone {
  switch (priority) {
    case 'CRITICAL':
      return 'critical';
    case 'HIGH':
      return 'high';
    case 'LOW':
      return 'low';
    default:
      return 'medium';
  }
}

export function buildTicketStatusTransitions(status: TicketStatus | string): TicketStatusTransitionOption[] {
  switch (status) {
    case 'OPEN':
      return [
        { toStatus: 'IN_PROGRESS', label: 'Pasar a En gestión' },
        { toStatus: 'ON_HOLD', label: 'Pasar a En espera' },
        { toStatus: 'RESOLVED', label: 'Marcar como Resuelto' }
      ];
    case 'IN_PROGRESS':
      return [
        { toStatus: 'ON_HOLD', label: 'Pasar a En espera' },
        { toStatus: 'RESOLVED', label: 'Marcar como Resuelto' }
      ];
    case 'ON_HOLD':
      return [
        { toStatus: 'IN_PROGRESS', label: 'Retomar (En gestión)' },
        { toStatus: 'RESOLVED', label: 'Marcar como Resuelto' }
      ];
    case 'RESOLVED':
      return [
        { toStatus: 'IN_PROGRESS', label: 'Reabrir a En gestión' },
        { toStatus: 'ON_HOLD', label: 'Reabrir a En espera' },
        { toStatus: 'OPEN', label: 'Reabrir a Abierto' }
      ];
    case 'PENDING_APPROVAL':
      return [
        { toStatus: 'OPEN', label: 'Rechazar y reabrir' },
        { toStatus: 'IN_PROGRESS', label: 'Rechazar y devolver a gestión' },
        { toStatus: 'ON_HOLD', label: 'Rechazar y poner en espera' },
        { toStatus: 'RESOLVED', label: 'Mantener resuelto sin cerrar' }
      ];
    default:
      return [];
  }
}

export function toLocationLabel(location: TicketLocation | TicketClientLocation | AppLocation | null | undefined): string {
  if (!location) {
    return 'Sin ubicación';
  }

  const addressLabel = 'address_label' in location ? location.address_label : location.addressLabel;
  if (addressLabel && String(addressLabel).trim()) {
    return String(addressLabel).trim();
  }

  return `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
}

export function buildGoogleMapsUrlFromTicketLocation(location: TicketLocation | TicketClientLocation | AppLocation | null | undefined): string | null {
  if (!location) {
    return null;
  }

  const latitude = Number(location.latitude);
  const longitude = Number(location.longitude);
  const hasValidCoordinates = Number.isFinite(latitude) && Number.isFinite(longitude);
  if (hasValidCoordinates) {
    return `https://www.google.com/maps?q=${latitude},${longitude}`;
  }

  const addressLabel = 'address_label' in location ? location.address_label : location.addressLabel;
  const formattedAddress = 'formatted_address' in location ? location.formatted_address : undefined;
  const query = String(addressLabel || formattedAddress || '').trim();
  if (!query) {
    return null;
  }

  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}
