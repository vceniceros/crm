export type InventorySourceType = 'TASK' | 'TICKET';
export type InventoryRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
export type DispatchConfirmationType = 'received' | 'delivered' | 'installed';

export interface RequiredMaterialWriteRequest {
  product_id: string;
  quantity_required: number;
  notes: string | null;
}

export interface RequiredMaterial {
  required_material_id: string;
  product_id: string;
  product_code: string;
  product_name: string;
  quantity_required: number;
  notes: string | null;
  requires_tracking: boolean;
}

export interface InventoryRequestItemWriteRequest {
  product_id: string;
  quantity_requested: number;
  notes: string | null;
}

export interface CreateInventoryRequestRequest {
  source_type: InventorySourceType;
  task_id?: string | null;
  external_ticket_id?: string | null;
  request_reason?: string | null;
  items: InventoryRequestItemWriteRequest[];
}

export interface ReviewInventoryRequestRequest {
  status: 'APPROVED' | 'REJECTED';
  review_notes?: string | null;
}

export interface InventoryDispatchItemWriteRequest {
  product_id: string;
  quantity_dispatched: number;
  serial_number?: string | null;
  barcode_value?: string | null;
  notes?: string | null;
}

export interface CreateTaskDispatchRequest {
  request_id?: string | null;
  dispatch_notes?: string | null;
  items: InventoryDispatchItemWriteRequest[];
}

export interface ConfirmDispatchItemRequest {
  confirmation_type: DispatchConfirmationType;
}

export interface InventoryRequestItem {
  inventory_request_item_id: string;
  product_id: string;
  product_code: string;
  product_name: string;
  quantity_requested: number;
  notes: string | null;
  requires_tracking: boolean;
}

export interface InventoryDispatchItem {
  inventory_dispatch_item_id: string;
  product_id: string;
  product_code: string;
  product_name: string;
  quantity_dispatched: number;
  serial_number: string | null;
  barcode_value: string | null;
  notes: string | null;
  requires_tracking: boolean;
  received_confirmed_by_crm_user_id: string | null;
  received_confirmed_by_display_name: string | null;
  received_confirmed_at: string | null;
  delivered_confirmed_by_crm_user_id: string | null;
  delivered_confirmed_by_display_name: string | null;
  delivered_confirmed_at: string | null;
  installed_confirmed_by_crm_user_id: string | null;
  installed_confirmed_by_display_name: string | null;
  installed_confirmed_at: string | null;
}

export interface InventoryDispatch {
  inventory_dispatch_id: string;
  source_type: InventorySourceType;
  source_reference_id: string;
  request_id: string | null;
  dispatched_by_crm_user_id: string;
  dispatched_by_display_name: string | null;
  warehouse_id: string;
  dispatch_notes: string | null;
  created_at: string;
  items: InventoryDispatchItem[];
}

export interface InventoryRequest {
  inventory_request_id: string;
  source_type: InventorySourceType;
  source_reference_id: string;
  task_id: string | null;
  external_ticket_id: string | null;
  request_status: InventoryRequestStatus;
  request_reason: string | null;
  requested_by_crm_user_id: string;
  requested_by_display_name: string | null;
  reviewed_by_crm_user_id: string | null;
  reviewed_by_display_name: string | null;
  requested_at: string;
  reviewed_at: string | null;
  review_notes: string | null;
  items: InventoryRequestItem[];
  dispatches: InventoryDispatch[];
}

export interface InventorySourceFlow {
  source_type: InventorySourceType;
  source_reference_id: string;
  requests: InventoryRequest[];
  dispatches: InventoryDispatch[];
}

export function formatInventoryRequestStatus(status: InventoryRequestStatus): string {
  switch (status) {
    case 'PENDING':
      return 'Pendiente';
    case 'APPROVED':
      return 'Aprobada';
    case 'REJECTED':
      return 'Rechazada';
    case 'CANCELLED':
      return 'Cancelada';
    default:
      return status;
  }
}