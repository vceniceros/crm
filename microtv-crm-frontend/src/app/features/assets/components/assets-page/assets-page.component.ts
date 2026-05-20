import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';

import { AssetSummary, AssetCategory } from '../../../../core/models/asset.model';
import { AssetManagementService } from '../../../../core/services/asset-management.service';
import { MockAccessControlService } from '../../../../core/services/mock-access-control.service';
import { CreateAssetCategoryDialogComponent } from '../create-asset-category-dialog/create-asset-category-dialog.component';
import { CreateAssetDialogComponent } from '../create-asset-dialog/create-asset-dialog.component';

@Component({
  selector: 'app-assets-page',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, MatTableModule],
  templateUrl: './assets-page.component.html',
  styleUrl: './assets-page.component.scss'
})
export class AssetsPageComponent {
  private readonly assetService = inject(AssetManagementService);
  private readonly accessControl = inject(MockAccessControlService);
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);

  readonly assets = signal<AssetSummary[]>([]);
  readonly categories = signal<AssetCategory[]>([]);
  readonly isAdmin = signal(false);
  readonly search = signal('');
  readonly categoryId = signal<string | null>(null);
  readonly displayedColumns = ['asset_name', 'category_name', 'client_name', 'parent_asset_name', 'actions'];

  constructor() {
    this.accessControl.isAdmin().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((value) => this.isAdmin.set(value));
    this.assetService.listCategories().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((categories) => this.categories.set(categories));
    this.reload();
  }

  reload(): void {
    this.assetService
      .listAssets({ search: this.search(), categoryId: this.categoryId() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((assets) => this.assets.set(assets));
  }

  openCreateAssetDialog(): void {
    this.dialog.open(CreateAssetDialogComponent, { width: '52rem', maxWidth: 'calc(100vw - 1rem)', data: {} }).afterClosed().subscribe((asset) => {
      if (asset) {
        this.reload();
      }
    });
  }

  openEditAssetDialog(asset: AssetSummary): void {
    this.assetService.getAsset(asset.asset_id).subscribe((detail) => {
      this.dialog.open(CreateAssetDialogComponent, { width: '52rem', maxWidth: 'calc(100vw - 1rem)', data: { existingAsset: detail } }).afterClosed().subscribe((updated) => {
        if (updated) {
          this.reload();
        }
      });
    });
  }

  openCreateCategoryDialog(): void {
    this.dialog.open(CreateAssetCategoryDialogComponent, { width: '48rem', maxWidth: 'calc(100vw - 1rem)' }).afterClosed().subscribe((category) => {
      if (category) {
        this.assetService.listCategories().subscribe((categories) => this.categories.set(categories));
      }
    });
  }

  deleteAsset(asset: AssetSummary): void {
    if (!window.confirm(`Eliminar el activo ${asset.asset_name}?`)) {
      return;
    }
    this.assetService.deleteAsset(asset.asset_id).subscribe(() => this.reload());
  }

  setSearch(value: string): void {
    this.search.set(value);
    this.reload();
  }

  setCategory(value: string): void {
    this.categoryId.set(value || null);
    this.reload();
  }
}
