import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';

import { AssetSummary } from '../../../../core/models/asset.model';
import { AssetManagementService } from '../../../../core/services/asset-management.service';
import { CreateAssetDialogComponent } from '../create-asset-dialog/create-asset-dialog.component';

@Component({
  selector: 'app-asset-vinculation-section',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatChipsModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatSelectModule],
  templateUrl: './asset-vinculation-section.component.html',
  styleUrl: './asset-vinculation-section.component.scss'
})
export class AssetVinculationSectionComponent implements OnInit {
  private readonly assetService = inject(AssetManagementService);
  private readonly dialog = inject(MatDialog);

  @Input() ticketId: string | null = null;
  @Input() taskId: string | null = null;
  @Input() linkedAssets: AssetSummary[] = [];
  @Input() disabled = false;
  @Input() clientId: string | null = null;
  @Output() assetsChanged = new EventEmitter<void>();

  readonly assetOptions = signal<AssetSummary[]>([]);
  readonly selectedAssetId = new FormControl('', { nonNullable: true });

  ngOnInit(): void {
    this.loadAssets();
  }

  readonly availableAssets = () => {
    const linkedIds = new Set(this.linkedAssets.map((asset) => asset.asset_id));
    return this.assetOptions().filter((asset) => !linkedIds.has(asset.asset_id));
  };

  assetOptionLabel(asset: AssetSummary): string {
    return `${asset.asset_name} - ${asset.client_name}`;
  }

  attachExistingAsset(): void {
    const assetId = this.selectedAssetId.getRawValue();
    if (!assetId) {
      return;
    }
    const request$ = this.ticketId
      ? this.assetService.linkAssetToTicket(this.ticketId, assetId)
      : this.taskId
        ? this.assetService.linkAssetToTask(this.taskId, assetId)
        : null;
    request$?.subscribe(() => {
      this.selectedAssetId.reset('');
      this.assetsChanged.emit();
      this.loadAssets();
    });
  }

  addNewAsset(): void {
    this.dialog.open(CreateAssetDialogComponent, { width: '52rem', maxWidth: 'calc(100vw - 1rem)', data: { clientId: this.clientId } }).afterClosed().subscribe((asset) => {
      if (!asset) {
        return;
      }
      const request$ = this.ticketId
        ? this.assetService.linkAssetToTicket(this.ticketId, asset.asset_id)
        : this.taskId
          ? this.assetService.linkAssetToTask(this.taskId, asset.asset_id)
          : null;
      request$?.subscribe(() => {
        this.assetsChanged.emit();
        this.loadAssets();
      });
    });
  }

  unlink(asset: AssetSummary): void {
    const request$ = this.ticketId
      ? this.assetService.unlinkAssetFromTicket(this.ticketId, asset.asset_id)
      : this.taskId
        ? this.assetService.unlinkAssetFromTask(this.taskId, asset.asset_id)
        : null;
    request$?.subscribe(() => this.assetsChanged.emit());
  }

  private loadAssets(): void {
    this.assetService.listAssets().subscribe({
      next: (assets) => this.assetOptions.set(assets),
      error: () => this.assetOptions.set([])
    });
  }
}
