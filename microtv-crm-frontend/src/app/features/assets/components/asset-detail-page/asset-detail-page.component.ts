import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';

import { Asset, AssetLinkedTask, AssetLinkedTicket } from '../../../../core/models/asset.model';
import { AssetManagementService } from '../../../../core/services/asset-management.service';

@Component({
  selector: 'app-asset-detail-page',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatIconModule, MatTabsModule],
  templateUrl: './asset-detail-page.component.html',
  styleUrl: './asset-detail-page.component.scss'
})
export class AssetDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly assetService = inject(AssetManagementService);
  private readonly destroyRef = inject(DestroyRef);

  readonly asset = signal<Asset | null>(null);
  readonly tickets = signal<AssetLinkedTicket[]>([]);
  readonly tasks = signal<AssetLinkedTask[]>([]);

  constructor() {
    const assetId = this.route.snapshot.paramMap.get('assetId');
    if (!assetId) {
      return;
    }
    this.assetService.getAsset(assetId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((asset) => this.asset.set(asset));
    this.assetService.getLinkedTicketsForAsset(assetId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((tickets) => this.tickets.set(tickets));
    this.assetService.getLinkedTasksForAsset(assetId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((tasks) => this.tasks.set(tasks));
  }
}
