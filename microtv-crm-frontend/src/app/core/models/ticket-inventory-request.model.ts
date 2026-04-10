export interface TicketInventoryRequestItem {
  inventoryItemId: number | string;
  inventoryItemName: string;
  quantity: number;
}

export type TicketInventoryRequestStatus = 'pending' | 'approved' | 'rejected';

export interface TicketInventoryRequest {
  id: string;
  requestedByUserId: number | string;
  requestedByUserName: string;
  requestedAt: string;
  status: TicketInventoryRequestStatus;
  items: TicketInventoryRequestItem[];
  depositDecisionComment?: string;
}