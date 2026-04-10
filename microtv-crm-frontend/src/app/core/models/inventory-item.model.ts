export interface InventoryItemOption {
  id: number | string;
  name: string;
  unit?: string;
}

export interface RequiredInventoryItem {
  itemId: number | string;
  name: string;
  quantity: number;
  unit?: string;
}

export interface InventoryItemsMockData {
  items: InventoryItemOption[];
}