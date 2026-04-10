import { Injectable } from '@angular/core';
import { BehaviorSubject, map, of, shareReplay } from 'rxjs';

import { CreateInventoryProductFormValue } from '../models/create-product.model';
import { InventoryCategoriesMockData, InventoryCategory } from '../models/inventory-category.model';
import { InventoryPageData, InventoryProduct, InventoryProductsMockData, InventoryTableColumn, InventoryTableData } from '../models/inventory-product.model';
import inventoryCategoriesData from '../../../mocks/inventory-categories-data.json';
import inventoryProductsData from '../../../mocks/inventory-products-data.json';

const categories = (inventoryCategoriesData as InventoryCategoriesMockData).categories;
const initialProducts = (inventoryProductsData as InventoryProductsMockData).items;
const tableColumns: InventoryTableColumn[] = [
  { key: 'image', label: 'Imagen' },
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'Producto' },
  { key: 'category', label: 'Categoria' },
  { key: 'stock', label: 'Stock actual' },
  { key: 'actions', label: 'Acciones' }
];

@Injectable({ providedIn: 'root' })
export class MockInventoryService {
  private readonly categoryNameById = new Map(categories.map((category) => [String(category.id), category.name]));
  private readonly productsSubject = new BehaviorSubject<InventoryProduct[]>(initialProducts);
  private nextProductId = initialProducts.reduce((maxId, product) => Math.max(maxId, product.id), 0) + 1;

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
    const product: InventoryProduct = {
      id: this.nextProductId++,
      name: payload.name.trim(),
      category: categoryName,
      imageUrl: this.normalizeImageUrl(payload.imageUrl),
      stock: this.sanitizeStock(payload.initialStock)
    };

    this.productsSubject.next([product, ...this.productsSubject.getValue()]);
    return of(product);
  }

  addStock(productId: number): void {
    this.updateProduct(productId, (product) => ({
      ...product,
      stock: product.stock + 1
    }));
  }

  removeStock(productId: number): void {
    this.updateProduct(productId, (product) => {
      if (product.stock === 0) {
        return product;
      }

      return {
        ...product,
        stock: product.stock - 1
      };
    });
  }

  private buildTable(items: InventoryProduct[]): InventoryTableData {
    return {
      title: 'Productos en deposito',
      columns: tableColumns,
      items
    };
  }

  private normalizeImageUrl(imageUrl?: string | null): string | null {
    const value = imageUrl?.trim();
    return value ? value : null;
  }

  private sanitizeStock(stock: number | null): number {
    return Math.max(0, Math.trunc(stock ?? 0));
  }

  private updateProduct(productId: number, project: (product: InventoryProduct) => InventoryProduct): void {
    const nextProducts = this.productsSubject
      .getValue()
      .map((product) => (product.id === productId ? project(product) : product));

    this.productsSubject.next(nextProducts);
  }
}

export type { CreateInventoryProductFormValue, InventoryCategory, InventoryPageData, InventoryProduct, InventoryTableData };