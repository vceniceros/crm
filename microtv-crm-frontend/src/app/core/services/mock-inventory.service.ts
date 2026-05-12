import { Injectable } from '@angular/core';
import { BehaviorSubject, map, of, shareReplay } from 'rxjs';

import { CreateInventoryProductFormValue } from '../models/create-product.model';
import { InventoryCategoriesMockData, InventoryCategory } from '../models/inventory-category.model';
import { InventoryPageData, InventoryProduct, InventoryProductsMockData, InventoryTableColumn, InventoryTableData } from '../models/inventory-product.model';
import inventoryCategoriesData from '../../../mocks/inventory-categories-data.json';
import inventoryProductsData from '../../../mocks/inventory-products-data.json';

type RawInventoryCategory = { id: number | string; name: string };
type RawInventoryProduct = {
  id: number | string;
  name: string;
  category: string;
  imageUrl?: string | null;
  stock: number;
  minimumStock?: number;
  shelfId?: string | null;
  shelfHeight?: number | null;
};

const rawCategories = inventoryCategoriesData as { categories: RawInventoryCategory[] };
const categories: InventoryCategory[] = rawCategories.categories.map((category) => ({
  id: String(category.id),
  name: category.name
}));

const categoryIdByName = new Map(categories.map((category) => [category.name, category.id]));
const rawProducts = inventoryProductsData as { items: RawInventoryProduct[] };
const initialProducts: InventoryProduct[] = rawProducts.items.map((product) => ({
  id: `PRD-${String(product.id)}`,
  productId: crypto.randomUUID(),
  productCode: `PRD-${String(product.id)}`,
  name: product.name,
  productName: product.name,
  categoryId: categoryIdByName.get(product.category) ?? crypto.randomUUID(),
  category: product.category,
  imageUrl: product.imageUrl ?? null,
  stock: product.stock,
  minimumStock: Math.max(1, Math.trunc(product.minimumStock ?? 3)),
  shelfId: product.shelfId ?? null,
  shelfHeight: product.shelfHeight ?? null,
  requiresTracking: false,
  isActive: true,
  createdAt: new Date().toISOString(),
  updatedAt: null
}));

const tableColumns: InventoryTableColumn[] = [
  { key: 'image', label: 'Imagen' },
  { key: 'id', label: 'Codigo' },
  { key: 'name', label: 'Producto' },
  { key: 'category', label: 'Categoria' },
  { key: 'stock', label: 'Stock actual' },
  { key: 'location', label: 'Ubicacion' },
  { key: 'actions', label: 'Acciones' }
];

@Injectable({ providedIn: 'root' })
export class MockInventoryService {
  private readonly categoryNameById = new Map(categories.map((category) => [String(category.id), category.name]));
  private readonly productsSubject = new BehaviorSubject<InventoryProduct[]>(initialProducts);

  readonly categories$ = of<InventoryCategory[]>(categories).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly products$ = this.productsSubject.asObservable();
  readonly inventoryPage$ = this.products$.pipe(
    map((products): InventoryPageData => ({
      pageTitle: 'Deposito',
      pageSubtitle:
        'Base operativa para registrar productos, revisar disponibilidad y ajustar stock de forma directa dentro del listado.',
      primaryAction: {
        label: 'Cargar nuevo producto',
        icon: 'add_box'
      },
      productsTable: this.buildTable(products)
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly inventoryTable$ = this.inventoryPage$.pipe(
    map((page) => page.productsTable)
  );

  createProduct(payload: CreateInventoryProductFormValue) {
    const categoryName = this.categoryNameById.get(String(payload.categoryId ?? '')) ?? 'Varios';
    const productCode = payload.productCode.trim().toUpperCase();
    const product: InventoryProduct = {
      id: productCode,
      productId: crypto.randomUUID(),
      productCode,
      name: payload.name.trim(),
      productName: payload.name.trim(),
      categoryId: payload.categoryId ?? '',
      category: categoryName,
      imageUrl: this.resolveImageUrl(payload.imageFile),
      stock: this.sanitizeStock(payload.initialStock),
      minimumStock: Math.max(1, Math.trunc(payload.minimumStock ?? 3)),
      shelfId: null,
      shelfHeight: null,
      requiresTracking: payload.requiresTracking,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: null,
    };

    this.productsSubject.next([product, ...this.productsSubject.getValue()]);
    return of(product);
  }

  addStock(productId: string) {
    return this.updateProduct(productId, (product) => ({
      ...product,
      stock: product.stock + 1
    }));
  }

  removeStock(productId: string) {
    return this.updateProduct(productId, (product) => {
      if (product.stock === 0) {
        return product;
      }

      return {
        ...product,
        stock: product.stock - 1
      };
    });
  }

  deleteProduct(productId: string) {
    const currentProduct = this.productsSubject.getValue().find((product) => product.productId === productId) ?? null;
    if (currentProduct?.imageUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(currentProduct.imageUrl);
    }

    this.productsSubject.next(this.productsSubject.getValue().filter((product) => product.productId !== productId));
    return of(void 0);
  }

  private buildTable(items: InventoryProduct[]): InventoryTableData {
    return {
      title: 'Productos en deposito',
      columns: tableColumns,
      items
    };
  }

  private resolveImageUrl(imageFile?: File | null): string | null {
    if (!imageFile) {
      return null;
    }
    return URL.createObjectURL(imageFile);
  }

  private sanitizeStock(stock: number | null): number {
    return Math.max(0, Math.trunc(stock ?? 0));
  }

  private updateProduct(productId: string, project: (product: InventoryProduct) => InventoryProduct) {
    let updatedProduct: InventoryProduct | null = null;
    const nextProducts = this.productsSubject.getValue().map((product) => {
      if (product.productId !== productId) {
        return product;
      }

      updatedProduct = project({
        ...product,
        updatedAt: new Date().toISOString()
      });
      return updatedProduct;
    });

    this.productsSubject.next(nextProducts);
    return of(updatedProduct ?? nextProducts.find((product) => product.productId === productId) ?? nextProducts[0]);
  }
}

export type { CreateInventoryProductFormValue, InventoryCategory, InventoryPageData, InventoryProduct, InventoryTableData };