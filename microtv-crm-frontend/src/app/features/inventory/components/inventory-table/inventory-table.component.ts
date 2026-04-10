import { Component, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';

import { InventoryProduct, InventoryTableData } from '../../../../core/models/inventory-product.model';
import { MockInventoryService } from '../../../../core/services/mock-inventory.service';

@Component({
  selector: 'app-inventory-table',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatTableModule],
  templateUrl: './inventory-table.component.html',
  styleUrl: './inventory-table.component.scss'
})
export class InventoryTableComponent {
  private readonly mockInventoryService = inject(MockInventoryService);

  readonly block = input.required<InventoryTableData>();
  readonly placeholderImageUrl = 'https://placehold.co/96x96/f0f2f4/5c6670?text=YCC';
  readonly displayedColumns: Array<'image' | 'id' | 'name' | 'category' | 'stock' | 'actions'> = [
    'image',
    'id',
    'name',
    'category',
    'stock',
    'actions'
  ];

  addStock(productId: number): void {
    this.mockInventoryService.addStock(productId);
  }

  removeStock(productId: number): void {
    this.mockInventoryService.removeStock(productId);
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

  onImageError(event: Event): void {
    const element = event.target;

    if (element instanceof HTMLImageElement && element.src !== this.placeholderImageUrl) {
      element.src = this.placeholderImageUrl;
    }
  }
}