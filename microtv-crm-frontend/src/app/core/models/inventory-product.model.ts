export interface InventoryPageAction {
  label: string;
  icon: string;
}

export interface InventoryProduct {
  id: number;
  name: string;
  category: string;
  imageUrl?: string | null;
  stock: number;
}

export interface InventoryProductsMockData {
  items: InventoryProduct[];
}

export interface InventoryTableColumn {
  key: 'image' | 'id' | 'name' | 'category' | 'stock' | 'actions';
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