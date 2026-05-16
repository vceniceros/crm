import { AsyncPipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { BehaviorSubject, combineLatest, firstValueFrom, map } from 'rxjs';

import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { UI_HELP_TEXTS } from '../../../../core/config/ui-help-texts.config';
import { InventoryService } from '../../../../core/services/inventory.service';
import { PermissionService } from '../../../../core/services/permission.service';
import { ContextHelpCardComponent } from '../../../../shared/ui/context-help-card/context-help-card.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { InventoryTableComponent } from '../inventory-table/inventory-table.component';

@Component({
  selector: 'app-inventory-page',
  standalone: true,
  imports: [
    AsyncPipe,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatSnackBarModule,
    ContextHelpCardComponent,
    PageTitleComponent,
    InventoryTableComponent
  ],
  templateUrl: './inventory-page.component.html',
  styleUrl: './inventory-page.component.scss'
})
export class InventoryPageComponent {
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);
  private readonly permissionService = inject(PermissionService);
  private readonly inventoryService = inject(InventoryService);
  private readonly querySubject = new BehaviorSubject('');
  private readonly categoryIdSubject = new BehaviorSubject('all');
  readonly helpText = UI_HELP_TEXTS.inventory;

  readonly inventoryPage$ = combineLatest({
    inventoryPage: this.inventoryService.inventoryPage$,
    categories: this.inventoryService.categories$,
    query: this.querySubject,
    categoryId: this.categoryIdSubject
  }).pipe(
    map(({ inventoryPage, categories, query, categoryId }) => {
      const normalizedQuery = this.normalizeText(query);
      const selectedCategoryId = categoryId;
      const filteredItems = inventoryPage.productsTable.items.filter((product) =>
        this.matchesCategory(product, selectedCategoryId) && this.matchesQuery(product, normalizedQuery)
      );

      return {
        ...inventoryPage,
        categories,
        filters: {
          query,
          categoryId
        },
        totalItems: inventoryPage.productsTable.items.length,
        filteredItems: filteredItems.length,
        hasActiveFilters: Boolean(normalizedQuery) || selectedCategoryId !== 'all',
        productsTable: {
          ...inventoryPage.productsTable,
          items: filteredItems
        }
      };
    })
  );
  readonly isLoading$ = this.inventoryService.isLoading$;
  readonly errorMessage$ = this.inventoryService.errorMessage$;

  constructor() {
    this.inventoryService
      .refresh()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        error: () => undefined
      });
  }

  async openCreateProductDialog(): Promise<void> {
    if (!this.canCreateProducts()) {
      return;
    }

    const { CreateProductDialogComponent } = await import('../create-product-dialog/create-product-dialog.component');
    this.dialog.open(CreateProductDialogComponent, {
      autoFocus: false,
      maxWidth: 'calc(100vw - 1.5rem)',
      width: '44rem'
    });
  }

  async previewStockImport(event: Event): Promise<void> {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) {
      return;
    }

    const file = input.files?.[0];
    input.value = '';
    if (!file || !this.canCreateProducts()) {
      return;
    }

    try {
      const preview = await firstValueFrom(this.inventoryService.previewStockImport(file));
      const { StockImportPreviewDialogComponent } = await import('../stock-import-preview-dialog/stock-import-preview-dialog.component');
      this.dialog.open(StockImportPreviewDialogComponent, {
        data: preview,
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '72rem'
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo previsualizar la importacion.';
      this.snackBar.open(message, 'Cerrar', { duration: 5000 });
    }
  }

  async rollbackLatestStock(): Promise<void> {
    if (!this.canRollbackStock()) {
      return;
    }

    try {
      const backup = await firstValueFrom(this.inventoryService.getLatestStockBackup());
      if (!backup.hasBackup || !backup.importId) {
        this.snackBar.open('No hay un backup de stock disponible.', 'Cerrar', { duration: 3000 });
        return;
      }

      const confirmed = window.confirm(
        `Se va a volver al stock anterior a la importacion "${backup.filename ?? backup.importId}". Esta accion solo debe usarse si la importacion salio mal. Continuar?`
      );
      if (!confirmed) {
        return;
      }

      const result = await firstValueFrom(this.inventoryService.rollbackStockImport(backup.importId));
      this.snackBar.open(`Stock anterior restaurado. Productos restaurados: ${result.restoredProducts}.`, 'Cerrar', { duration: 4000 });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo volver al stock anterior.';
      this.snackBar.open(message, 'Cerrar', { duration: 5000 });
    }
  }

  clearFilters(): void {
    this.querySubject.next('');
    this.categoryIdSubject.next('all');
  }

  updateQuery(event: Event): void {
    const target = event.target;
    if (target instanceof HTMLInputElement) {
      this.querySubject.next(target.value);
    }
  }

  updateCategory(event: Event): void {
    const target = event.target;
    if (target instanceof HTMLSelectElement) {
      this.categoryIdSubject.next(target.value || 'all');
    }
  }

  canCreateProducts(): boolean {
    return this.permissionService.canManageStock();
  }

  canRollbackStock(): boolean {
    return this.permissionService.canDeleteProduct();
  }

  private matchesCategory(product: InventoryProduct, categoryId: string): boolean {
    return categoryId === 'all' || product.categoryId === categoryId;
  }

  private matchesQuery(product: InventoryProduct, query: string): boolean {
    if (!query) {
      return true;
    }

    const searchableFields = [product.productCode, product.imageUrl, product.name, product.productName];
    return searchableFields.some((value) => this.normalizeText(value).includes(query));
  }

  private normalizeText(value: string | null | undefined): string {
    return (value ?? '').trim().toLocaleLowerCase();
  }
}
