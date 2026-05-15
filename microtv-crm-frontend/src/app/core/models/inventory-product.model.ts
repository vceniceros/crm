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

export interface StockImportRowPreview {
  rowNumber: number;
  imageUrl: string;
  productCode: string;
  productName: string;
  categoryName: string;
  importedStock: number;
  oldStock: number;
  newStock: number;
  ubication: string | null;
  isNewProduct: boolean;
  isValid: boolean;
  errors: string[];
}

export interface StockImportPreview {
  importId: string;
  status: string;
  filename: string;
  totalRows: number;
  validRows: number;
  invalidRows: number;
  createdCount: number;
  updatedCount: number;
  totalImportStock: number;
  canConfirm: boolean;
  rows: StockImportRowPreview[];
}

export interface StockImportConfirmResult {
  importId: string;
  backupId: string;
  status: string;
  createdCount: number;
  updatedCount: number;
  totalImportStock: number;
  products: InventoryProduct[];
}

export interface StockBackupStatus {
  hasBackup: boolean;
  importId: string | null;
  backupId: string | null;
  filename: string | null;
  createdAt: string | null;
  totalRows: number;
  totalImportStock: number;
}

export interface StockRollbackResult {
  importId: string;
  backupId: string;
  restoredProducts: number;
  deactivatedCreatedProducts: number;
  products: InventoryProduct[];
}
