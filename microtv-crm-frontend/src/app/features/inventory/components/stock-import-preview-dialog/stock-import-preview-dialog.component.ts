import { Component, inject, signal } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { StockImportPreview } from '../../../../core/models/inventory-product.model';
import { InventoryService } from '../../../../core/services/inventory.service';

@Component({
  selector: 'app-stock-import-preview-dialog',
  standalone: true,
  imports: [MatButtonModule, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogTitle, MatIconModule, MatSnackBarModule, MatTableModule],
  templateUrl: './stock-import-preview-dialog.component.html',
  styleUrl: './stock-import-preview-dialog.component.scss'
})
export class StockImportPreviewDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<StockImportPreviewDialogComponent, boolean>);
  private readonly inventoryService = inject(InventoryService);
  private readonly snackBar = inject(MatSnackBar);
  readonly preview = inject<StockImportPreview>(MAT_DIALOG_DATA);
  readonly isConfirming = signal(false);
  readonly displayedColumns = ['image', 'code', 'product', 'category', 'location', 'oldStock', 'importedStock', 'newStock', 'status'] as const;

  async confirm(): Promise<void> {
    if (!this.preview.canConfirm || this.isConfirming()) {
      return;
    }

    this.isConfirming.set(true);
    try {
      const result = await firstValueFrom(this.inventoryService.confirmStockImport(this.preview.importId));
      this.snackBar.open(`Importacion aplicada: ${result.updatedCount} actualizados, ${result.createdCount} nuevos.`, 'Cerrar', { duration: 3500 });
      this.dialogRef.close(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo confirmar la importacion.';
      this.snackBar.open(message, 'Cerrar', { duration: 5000 });
    } finally {
      this.isConfirming.set(false);
    }
  }
}
