import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { BehaviorSubject, Observable, forkJoin, map, shareReplay, tap, catchError, throwError, finalize } from 'rxjs';

import { crmApiConfig } from '../config/crm-api.config';
import { CreateInventoryProductFormValue } from '../models/create-product.model';
import { InventoryCategory } from '../models/inventory-category.model';
import { InventoryPageData, InventoryProduct, InventoryTableColumn, InventoryTableData } from '../models/inventory-product.model';
import { resolveBackendAssetUrl } from '../utils/backend-asset-url.util';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

interface StockCategoryResponseDto {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

interface StockProductResponseDto {
  id: string;
  product_id: string;
  product_code: string;
  name: string;
  product_name: string;
  category_id: string;
  category_name: string;
  current_stock: number;
  image_url: string | null;
  minimum_stock: number;
  shelf_id: string | null;
  shelf_height: number | null;
  requires_tracking: boolean;
  created_at: string;
  updated_at: string | null;
  is_active: boolean;
}

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
export class InventoryService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly productsSubject = new BehaviorSubject<InventoryProduct[]>([]);
  private readonly categoriesSubject = new BehaviorSubject<InventoryCategory[]>([]);
  private readonly isLoadingSubject = new BehaviorSubject(false);
  private readonly errorMessageSubject = new BehaviorSubject<string | null>(null);

  readonly categories$ = this.categoriesSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly products$ = this.productsSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly isLoading$ = this.isLoadingSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly errorMessage$ = this.errorMessageSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
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

  refresh(): Observable<void> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para consultar depósito.');
    }

    this.isLoadingSubject.next(true);
    this.errorMessageSubject.next(null);

    return forkJoin({
      categories: this.http.get<StockCategoryResponseDto[]>(this.buildUrl('/stock/categories'), { headers }),
      products: this.http.get<StockProductResponseDto[]>(this.buildUrl('/stock/products'), { headers })
    }).pipe(
      tap(({ categories, products }) => {
        this.categoriesSubject.next(categories.map((category) => this.mapCategory(category)));
        this.productsSubject.next(products.map((product) => this.mapProduct(product)));
      }),
      map(() => void 0),
      catchError((error) => this.handleRequestError(error, 'No se pudo cargar el módulo real de depósito.')),
      finalize(() => this.isLoadingSubject.next(false))
    );
  }

  createProduct(payload: CreateInventoryProductFormValue): Observable<InventoryProduct> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para crear productos.');
    }

    const formData = new FormData();
    formData.append('product_name', payload.name.trim());
    formData.append('product_code', payload.productCode.trim().toUpperCase());
    formData.append('category_id', payload.categoryId ?? '');
    formData.append('stock_initial', String(Math.max(0, Math.trunc(payload.initialStock ?? 0))));
    formData.append('minimum_stock', String(payload.minimumStock));
    formData.append('requires_tracking', String(payload.requiresTracking));
    if (payload.imageFile) {
      formData.append('image', payload.imageFile);
    }

    return this.http
      .post<StockProductResponseDto>(this.buildUrl('/stock/products'), formData, { headers })
      .pipe(
        map((product) => this.mapProduct(product)),
        tap((product) => {
          this.errorMessageSubject.next(null);
          this.productsSubject.next([product, ...this.productsSubject.getValue()]);
        }),
        catchError((error) => this.handleRequestError(error, 'No se pudo crear el producto.'))
      );
  }

  addStock(productId: string, quantity = 1): Observable<InventoryProduct> {
    return this.adjustStock(productId, quantity, 'increase-stock', 'No se pudo aumentar el stock.');
  }

  removeStock(productId: string, quantity = 1): Observable<InventoryProduct> {
    return this.adjustStock(productId, quantity, 'decrease-stock', 'No se pudo disminuir el stock.');
  }

  setStock(productId: string, quantity: number): Observable<InventoryProduct> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay sesión activa.');
    }

    return this.http
      .patch<StockProductResponseDto>(this.buildUrl(`/stock/products/${productId}/stock`), { quantity }, { headers })
      .pipe(
        tap((dto) => {
          const updated = this.mapProduct(dto);
          this.productsSubject.next(
            this.productsSubject.value.map((product) => (product.productId === updated.productId ? updated : product))
          );
        }),
        map((dto) => this.mapProduct(dto)),
        catchError((error) => this.handleError(error))
      );
  }

  updateProductLocation(productId: string, shelfId: string, shelfHeight: number): Observable<InventoryProduct> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay sesión activa.');
    }

    return this.http
      .patch<StockProductResponseDto>(
        this.buildUrl(`/stock/products/${productId}/location`),
        { shelf_id: shelfId, shelf_height: shelfHeight },
        { headers }
      )
      .pipe(
        tap((dto) => {
          const updated = this.mapProduct(dto);
          this.productsSubject.next(
            this.productsSubject.value.map((product) => (product.productId === updated.productId ? updated : product))
          );
        }),
        map((dto) => this.mapProduct(dto)),
        catchError((error) => this.handleError(error))
      );
  }

  deleteProduct(productId: string): Observable<void> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para eliminar productos.');
    }

    return this.http.delete<void>(this.buildUrl(`/stock/products/${productId}`), { headers }).pipe(
      tap(() => {
        this.errorMessageSubject.next(null);
        this.productsSubject.next(this.productsSubject.getValue().filter((product) => product.productId !== productId));
      }),
      catchError((error) => this.handleRequestError(error, 'No se pudo eliminar el producto.'))
    );
  }

  private adjustStock(
    productId: string,
    quantity: number,
    action: 'increase-stock' | 'decrease-stock',
    fallbackMessage: string
  ): Observable<InventoryProduct> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para ajustar stock.');
    }

    return this.http
      .post<StockProductResponseDto>(this.buildUrl(`/stock/products/${productId}/${action}`), { quantity }, { headers })
      .pipe(
        map((product) => this.mapProduct(product)),
        tap((product) => {
          this.errorMessageSubject.next(null);
          this.productsSubject.next(
            this.productsSubject.getValue().map((currentProduct) =>
              currentProduct.productId === product.productId ? product : currentProduct
            )
          );
        }),
        catchError((error) => this.handleRequestError(error, fallbackMessage))
      );
  }

  private mapCategory(category: StockCategoryResponseDto): InventoryCategory {
    return {
      id: category.id,
      code: category.code,
      name: category.name
    };
  }

  private mapProduct(product: StockProductResponseDto): InventoryProduct {
    return {
      id: product.product_code,
      productId: product.product_id,
      productCode: product.product_code,
      name: product.product_name,
      productName: product.product_name,
      categoryId: product.category_id,
      category: product.category_name,
      imageUrl: this.resolveProductImageUrl(product.image_url),
      stock: product.current_stock,
      minimumStock: product.minimum_stock,
      shelfId: product.shelf_id,
      shelfHeight: product.shelf_height,
      requiresTracking: product.requires_tracking,
      isActive: product.is_active,
      createdAt: product.created_at,
      updatedAt: product.updated_at
    };
  }

  private resolveProductImageUrl(imageUrl: string | null): string | null {
    return resolveBackendAssetUrl(imageUrl, crmApiConfig.baseUrl);
  }

  private buildTable(items: InventoryProduct[]): InventoryTableData {
    return {
      title: 'Productos en deposito',
      columns: tableColumns,
      items
    };
  }

  private buildAuthHeaders(): HttpHeaders | null {
    const session = this.authSessionService.sessionSnapshot();
    const accessToken = session?.tokens.access_token;
    if (!accessToken) {
      return null;
    }

    return new HttpHeaders({
      Authorization: `Bearer ${accessToken}`
    });
  }

  private handleRequestError(error: unknown, fallbackMessage: string): Observable<never> {
    const message = this.resolveErrorMessage(error, fallbackMessage);
    this.errorMessageSubject.next(message);
    return throwError(() => new Error(message));
  }

  private failRequest(message: string): Observable<never> {
    this.errorMessageSubject.next(message);
    return throwError(() => new Error(message));
  }

  private handleError(error: unknown): Observable<never> {
    return this.handleRequestError(error, 'No se pudo completar la operación en depósito.');
  }

  private resolveErrorMessage(error: unknown, fallbackMessage: string): string {
    const apiMessage = (error as { error?: ApiErrorEnvelope })?.error?.error?.message;
    if (typeof apiMessage === 'string' && apiMessage.trim()) {
      return apiMessage;
    }

    return fallbackMessage;
  }

  private buildUrl(path: string): string {
    return `${crmApiConfig.baseUrl}${path}`;
  }
}