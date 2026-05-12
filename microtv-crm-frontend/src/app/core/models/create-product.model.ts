export interface CreateInventoryProductFormValue {
  name: string;
  productCode: string;
  categoryId: string | null;
  imageFile?: File | null;
  initialStock: number | null;
  minimumStock: number;
  requiresTracking: boolean;
}