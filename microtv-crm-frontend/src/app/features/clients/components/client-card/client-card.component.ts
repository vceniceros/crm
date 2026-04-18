import { Component, inject, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { ClientItem } from '../../../../core/models/client.model';
import { LocationLinkService } from '../../../../shared/services/location-link.service';

@Component({
  selector: 'app-client-card',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule],
  templateUrl: './client-card.component.html',
  styleUrl: './client-card.component.scss'
})
export class ClientCardComponent {
  private readonly locationLinkService = inject(LocationLinkService);

  readonly client = input.required<ClientItem>();
  readonly canEdit = input(false);
  readonly canDelete = input(false);
  readonly editClient = output<ClientItem>();
  readonly deleteClient = output<ClientItem>();
  readonly openLocation = output<ClientItem>();
  readonly openExternalMaps = output<ClientItem>();

  initials(): string {
    return this.client()
      .razonSocial
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('');
  }

  hasLocation(): boolean {
    return this.locationLinkService.isValidLocation(this.client().location);
  }

  locationLabel(): string {
    const location = this.client().location;
    if (!this.locationLinkService.isValidLocation(location)) {
      return 'Sin ubicación cargada';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`;
  }

  emitEdit(): void {
    this.editClient.emit(this.client());
  }

  emitOpenLocation(): void {
    if (!this.hasLocation()) {
      return;
    }

    this.openLocation.emit(this.client());
  }

  emitOpenExternalMaps(): void {
    if (!this.hasLocation()) {
      return;
    }

    this.openExternalMaps.emit(this.client());
  }

  emitDelete(): void {
    this.deleteClient.emit(this.client());
  }
}