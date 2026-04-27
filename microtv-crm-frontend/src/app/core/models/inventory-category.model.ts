export interface InventoryCategory {
  id: string;
  code?: string;
  name: string;
}

export type InventoryCategoriesMockData = { categories: { id: string; name: string }[] };
