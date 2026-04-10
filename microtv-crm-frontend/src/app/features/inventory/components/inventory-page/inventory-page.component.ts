import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { MockInventoryService } from '../../../../core/services/mock-inventory.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { CreateProductDialogComponent } from '../create-product-dialog/create-product-dialog.component';
import { InventoryTableComponent } from '../inventory-table/inventory-table.component';

@Component({
  selector: 'app-inventory-page',
  standalone: true,
  imports: [AsyncPipe, MatButtonModule, MatDialogModule, MatIconModule, PageTitleComponent, InventoryTableComponent],
  templateUrl: './inventory-page.component.html',
  styleUrl: './inventory-page.component.scss'
})
export class InventoryPageComponent {
  private readonly dialog = inject(MatDialog);
  private readonly mockInventoryService = inject(MockInventoryService);

  readonly inventoryPage$ = this.mockInventoryService.inventoryPage$;

  openCreateProductDialog(): void {
    this.dialog.open<CreateProductDialogComponent, undefined, InventoryProduct>(CreateProductDialogComponent, {
      autoFocus: false,
      maxWidth: 'calc(100vw - 1.5rem)',
      width: '44rem'
    });
  }
}