import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Inject, computed, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { ClientItem } from '../../../../core/models/client.model';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';

export interface ClientLocationDialogData {
  client: ClientItem;
}

@Component({
  selector: 'app-client-location-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule
  ],
  templateUrl: './client-location-dialog.component.html',
  styleUrls: ['./client-location-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ClientLocationDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<ClientLocationDialogComponent>);
  private readonly locationLinkService = inject(LocationLinkService);

  readonly locationMapComponent = LocationMapComponent;
  readonly location = computed(() => this.data.client.location);
  readonly hasValidLocation = computed(() => this.locationLinkService.isValidLocation(this.location()));
  readonly locationMapInputs = computed(() => ({
    location: this.data.client.location,
    title: this.data.client.razonSocial
  }));
  readonly coordinatesLabel = computed(() => {
    const location = this.location();
    if (!this.locationLinkService.isValidLocation(location)) {
      return null;
    }

    return `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  });

  constructor(@Inject(MAT_DIALOG_DATA) readonly data: ClientLocationDialogData) {}

  openInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.location());
  }

  close(): void {
    this.dialogRef.close();
  }
}
