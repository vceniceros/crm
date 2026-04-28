import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import { AppLocation, LocationPickerDialogData, LocationSelectionResult } from '../../../core/models/location.model';
import { LocationFacade } from '../../facades/location.facade';
import { LocationPickerMapComponent, LocationPickerMapCoordinates } from '../location-picker-map/location-picker-map.component';

@Component({
  selector: 'app-location-picker-dialog',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule, MatIconModule, LocationPickerMapComponent],
  templateUrl: './location-picker-dialog.component.html',
  styleUrls: ['./location-picker-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LocationPickerDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<LocationPickerDialogComponent, LocationSelectionResult>);
  private readonly locationFacade = inject(LocationFacade);
  readonly data = inject<LocationPickerDialogData | null>(MAT_DIALOG_DATA, { optional: true }) ?? {};

  readonly selectedLocation = signal<AppLocation | null>(this.getInitialLocation());
  readonly initialCoordinates = computed<LocationPickerMapCoordinates | null>(() => {
    const location = this.selectedLocation();
    if (!this.locationFacade.isValid(location)) {
      return null;
    }

    return {
      lat: location.latitude,
      lon: location.longitude
    };
  });
  readonly googleMapsUrl = computed(() => this.locationFacade.buildNavigationUrl(this.selectedLocation()));
  readonly coordinatesLabel = computed(() => {
    const location = this.selectedLocation();
    if (!this.locationFacade.isValid(location)) {
      return 'Todavía no marcaste un punto en el mapa.';
    }

    return `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  });

  close(): void {
    this.dialogRef.close();
  }

  confirmSelection(): void {
    const location = this.selectedLocation();
    const googleMapsUrl = this.googleMapsUrl();

    if (!this.locationFacade.isValid(location) || !googleMapsUrl) {
      return;
    }

    this.dialogRef.close({
      location,
      googleMapsUrl
    });
  }

  openSelectedLocationInMaps(): void {
    this.locationFacade.openNavigation(this.selectedLocation());
  }

  onCoordinatesChanged(coordinates: LocationPickerMapCoordinates): void {
    const nextLocation = this.locationFacade.createFromMapSelection(coordinates.lat, coordinates.lon);
    this.selectedLocation.set(nextLocation);
  }

  private getInitialLocation(): AppLocation | null {
    const candidate = this.data.initialLocation;
    return this.locationFacade.isValid(candidate) ? candidate : null;
  }
}
