import { Component, inject, input, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';

import { InventoryProduct, InventoryTableData } from '../../../../core/models/inventory-product.model';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { InventoryService } from '../../../../core/services/inventory.service';

@Component({
  selector: 'app-inventory-table',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatSnackBarModule, MatTableModule],
  templateUrl: './inventory-table.component.html',
  styleUrl: './inventory-table.component.scss'
})
export class InventoryTableComponent {
  private readonly inventoryService = inject(InventoryService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly snackBar = inject(MatSnackBar);

  readonly block = input.required<InventoryTableData>();
  readonly pendingProductId = signal<string | null>(null);
  readonly placeholderImageUrl = 'https://placehold.co/96x96/f0f2f4/5c6670?text=YCC';
  readonly displayedColumns: Array<'image' | 'id' | 'name' | 'category' | 'stock' | 'actions'> = [
    'image',
    'id',
    'name',
    'category',
    'stock',
    'actions'
  ];

  async addStock(productId: string): Promise<void> {
    await this.adjustStock(productId, () => this.inventoryService.addStock(productId), 'Stock aumentado correctamente.');
  }

  async removeStock(productId: string): Promise<void> {
    await this.adjustStock(productId, () => this.inventoryService.removeStock(productId), 'Stock disminuido correctamente.');
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

    if (product.stock <= 3) {
      return 'low';
    }

    return 'healthy';
  }

  hasStock(product: InventoryProduct): boolean {
    return product.stock > 0;
  }

  canManageStock(): boolean {
    const primaryRole = this.authSessionService.sessionSnapshot()?.user.primary_role;
    return primaryRole === 'admin' || primaryRole === 'deposito';
  }

  canDeleteProducts(): boolean {
    return this.authSessionService.sessionSnapshot()?.user.primary_role === 'admin';
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