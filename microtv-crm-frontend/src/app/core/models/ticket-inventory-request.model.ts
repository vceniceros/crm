export interface TicketInventoryRequestItem {
  inventoryItemId: number | string;
  inventoryItemName: string;
  quantity: number;
  notes?: string;
  requiresTracking?: boolean;
}

export type TicketInventoryRequestStatus =
  | 'pending_deposit_review'
  | 'approved_for_dispatch'
  | 'pending_receipt'
  | 'dispatched'
  | 'rejected'
  | 'cancelled';

export interface TicketInventoryRequest {
  id: string;
  requestedByUserId: number | string;
  requestedByUserName: string;
  requestedAt: string;
  status: TicketInventoryRequestStatus;
  requestReason?: string;
  items: TicketInventoryRequestItem[];
  depositDecisionComment?: string;
}