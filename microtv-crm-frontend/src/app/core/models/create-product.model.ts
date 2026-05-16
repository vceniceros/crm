export interface CreateInventoryProductFormValue {
  name: string;
  productCode: string;
  categoryId: string | null;
  imageFile?: File | null;
  initialStock: number | null;
  minimumStock: number;
  requiresTracking: boolean;
}

export interface UpdateInventoryProductFormValue {
  name: string;
  productCode: string;
  categoryId: string | null;
  imageFile?: File | null;
  currentStock: number | null;
  minimumStock: number;
  shelfId: string | null;
  shelfHeight: number | null;
  requiresTracking: boolean;
}
