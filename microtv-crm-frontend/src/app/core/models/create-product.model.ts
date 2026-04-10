export interface CreateInventoryProductFormValue {
  name: string;
  categoryId: number | string | null;
  imageUrl?: string | null;
  initialStock: number | null;
}