import { Component, inject, input, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';

import { InventoryProduct, InventoryTableData } from '../../../../core/models/inventory-product.model';
import { InventoryService } from '../../../../core/services/inventory.service';
import { PermissionService } from '../../../../core/services/permission.service';
import { ImageViewerDialogComponent } from '../../../../shared/ui/image-viewer-dialog/image-viewer-dialog.component';

@Component({
  selector: 'app-inventory-table',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatDialogModule, MatIconModule, MatSnackBarModule, MatTableModule],
  templateUrl: './inventory-table.component.html',
  styleUrl: './inventory-table.component.scss'
})
export class InventoryTableComponent {
  private readonly inventoryService = inject(InventoryService);
  private readonly permissionService = inject(PermissionService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  readonly block = input.required<InventoryTableData>();
  readonly pendingProductId = signal<string | null>(null);
  readonly placeholderImageUrl = 'https://placehold.co/96x96/f0f2f4/5c6670?text=YCC';
  readonly displayedColumns = ['image', 'id', 'name', 'category', 'stock', 'location', 'actions'] as const;
  readonly editingLocationId = signal<string | null>(null);
  readonly locationEditShelfId = signal<string>('');
  readonly locationEditHeight = signal<number | null>(null);
  readonly shelfOptions = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  readonly editingStockId = signal<string | null>(null);
  readonly stockEditValue = signal<number | null>(null);

  async addStock(productId: string): Promise<void> {
    await this.adjustStock(productId, () => this.inventoryService.addStock(productId), 'Stock aumentado correctamente.');
  }

  async removeStock(productId: string): Promise<void> {
    await this.adjustStock(productId, () => this.inventoryService.removeStock(productId), 'Stock disminuido correctamente.');
  }

  openImage(product: InventoryProduct): void {
    if (!product.imageUrl) {
      return;
    }

    this.dialog.open(ImageViewerDialogComponent, {
      data: { mediaUrl: product.imageUrl, altText: product.name, mediaType: 'image' },
      maxWidth: '95vw',
      maxHeight: '95vh',
      panelClass: 'image-viewer-panel'
    });
  }

  startEditLocation(product: InventoryProduct): void {
    this.editingLocationId.set(product.productId);
    this.locationEditShelfId.set(product.shelfId ?? '');
    this.locationEditHeight.set(product.shelfHeight ?? null);
  }

  cancelEditLocation(): void {
    this.editingLocationId.set(null);
  }

  async confirmEditLocation(productId: string): Promise<void> {
    const shelfId = this.locationEditShelfId();
    const height = this.locationEditHeight();
    if (!shelfId || !height || height < 1 || !this.canManageStock()) {
      return;
    }

    this.pendingProductId.set(productId);
    try {
      await firstValueFrom(this.inventoryService.updateProductLocation(productId, shelfId, height));
      this.snackBar.open('Ubicación actualizada.', 'Cerrar', { duration: 2500 });
      this.editingLocationId.set(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo actualizar la ubicación.';
      this.snackBar.open(message, 'Cerrar', { duration: 4500 });
    } finally {
      this.pendingProductId.set(null);
    }
  }

  startEditStock(product: InventoryProduct): void {
    this.editingStockId.set(product.productId);
    this.stockEditValue.set(product.stock);
  }

  cancelEditStock(): void {
    this.editingStockId.set(null);
    this.stockEditValue.set(null);
  }

  async confirmEditStock(productId: string): Promise<void> {
    const value = this.stockEditValue();
    if (value === null || value < 0 || !this.canManageStock()) {
      return;
    }

    this.pendingProductId.set(productId);
    try {
      await firstValueFrom(this.inventoryService.setStock(productId, value));
      this.snackBar.open('Stock actualizado.', 'Cerrar', { duration: 2500 });
      this.editingStockId.set(null);
      this.stockEditValue.set(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo actualizar el stock.';
      this.snackBar.open(message, 'Cerrar', { duration: 4500 });
    } finally {
      this.pendingProductId.set(null);
    }
  }

  async deleteProduct(product: InventoryProduct): Promise<void> {
    if (!this.canDeleteProducts() || this.pendingProductId() !== null) {
      return;
    }

    const confirmed = window.confirm(`Se va a eliminar ${product.name} (${product.productCode}). Esta acción lo oculta del depósito. ¿Continuar?`);
    if (!confirmed) {
      return;
    }

    this.pendingProductId.set(product.productId);
    try {
      await firstValueFrom(this.inventoryService.deleteProduct(product.productId));
      this.snackBar.open('Producto eliminado correctamente.', 'Cerrar', { duration: 2500 });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo eliminar el producto.';
      this.snackBar.open(message, 'Cerrar', { duration: 4500 });
    } finally {
      this.pendingProductId.set(null);
    }
  }

  async openEditProductDialog(product: InventoryProduct): Promise<void> {
    if (!this.canManageStock() || this.pendingProductId() !== null) {
      return;
    }

    const { CreateProductDialogComponent } = await import('../create-product-dialog/create-product-dialog.component');
    this.dialog.open(CreateProductDialogComponent, {
      data: { mode: 'edit', product },
      autoFocus: false,
      maxWidth: 'calc(100vw - 1.5rem)',
      width: '44rem'
    });
  }

  labelFor(column: (typeof this.displayedColumns)[number]): string {
    return this.block().columns.find((item) => item.key === column)?.label ?? column;
  }

  imageFor(product: InventoryProduct): string {
    return product.imageUrl || this.placeholderImageUrl;
  }

  stockLabel(product: InventoryProduct): string {
    return product.stock === 0 ? 'Sin stock' : String(product.stock);
  }

  stockTone(product: InventoryProduct): 'empty' | 'low' | 'healthy' {
    if (product.stock === 0) {
      return 'empty';
    }

    if (product.stock < product.minimumStock) {
      return 'low';
    }

    return 'healthy';
  }

  hasStock(product: InventoryProduct): boolean {
    return product.stock > 0;
  }

  canManageStock(): boolean {
    return this.permissionService.canManageStock();
  }

  canDeleteProducts(): boolean {
    return this.permissionService.canDeleteProduct();
  }

  isPending(productId: string): boolean {
    return this.pendingProductId() === productId;
  }

  onImageError(event: Event): void {
    const element = event.target;

    if (element instanceof HTMLImageElement && element.src !== this.placeholderImageUrl) {
      element.src = this.placeholderImageUrl;
    }
  }

  private async adjustStock(
    productId: string,
    action: () => ReturnType<InventoryService['addStock']>,
    successMessage: string
  ): Promise<void> {
    if (!this.canManageStock() || this.pendingProductId() !== null) {
      return;
    }

    this.pendingProductId.set(productId);
    try {
      await firstValueFrom(action());
      this.snackBar.open(successMessage, 'Cerrar', { duration: 2500 });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo actualizar el stock.';
      this.snackBar.open(message, 'Cerrar', { duration: 4500 });
    } finally {
      this.pendingProductId.set(null);
    }
  }
}
