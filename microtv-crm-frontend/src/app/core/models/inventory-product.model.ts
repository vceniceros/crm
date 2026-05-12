export interface InventoryPageAction {
  label: string;
  icon: string;
}

export interface InventoryProduct {
  id: string;
  productId: string;
  productCode: string;
  name: string;
  productName: string;
  categoryId: string;
  category: string;
  imageUrl?: string | null;
  stock: number;
  minimumStock: number;
  shelfId: string | null;
  shelfHeight: number | null;
  requiresTracking: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string | null;
}

export interface InventoryTableColumn {
  key: 'image' | 'id' | 'name' | 'category' | 'stock' | 'location' | 'actions';
  label: string;
}

export interface InventoryTableData {
  title: string;
  columns: InventoryTableColumn[];
  items: InventoryProduct[];
}

export interface InventoryPageData {
  pageTitle: string;
  pageSubtitle: string;
  primaryAction: InventoryPageAction;
  productsTable: InventoryTableData;
}

export type InventoryProductsMockData = { items: InventoryProduct[] };