export interface TicketDispatchItem {
  inventoryItemId: number | string;
  inventoryItemName: string;
  quantity: number;
  requestId?: string;
  serialNumber?: string;
  barcodeValue?: string;
  notes?: string;
  requiresTracking?: boolean;
  dispatchedAt?: string;
  receivedConfirmedAt?: string;
  deliveredConfirmedAt?: string;
  installedConfirmedAt?: string;
}