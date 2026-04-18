import { AsyncPipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { BehaviorSubject, combineLatest, map } from 'rxjs';

import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { InventoryService } from '../../../../core/services/inventory.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { CreateProductDialogComponent } from '../create-product-dialog/create-product-dialog.component';
import { InventoryTableComponent } from '../inventory-table/inventory-table.component';

@Component({
  selector: 'app-inventory-page',
  standalone: true,
  imports: [
    AsyncPipe,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    PageTitleComponent,
    InventoryTableComponent
  ],
  templateUrl: './inventory-page.component.html',
  styleUrl: './inventory-page.component.scss'
})
export class InventoryPageComponent {
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly inventoryService = inject(InventoryService);
  private readonly querySubject = new BehaviorSubject('');
  private readonly categoryIdSubject = new BehaviorSubject('all');

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

  openCreateProductDialog(): void {
    if (!this.canCreateProducts()) {
      return;
    }

    this.dialog.open<CreateProductDialogComponent, undefined, InventoryProduct>(CreateProductDialogComponent, {
      autoFocus: false,
      maxWidth: 'calc(100vw - 1.5rem)',
      width: '44rem'
    });
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
    const primaryRole = this.authSessionService.sessionSnapshot()?.user.primary_role;
    return primaryRole === 'admin' || primaryRole === 'deposito';
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