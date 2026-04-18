import { CommonModule, isPlatformBrowser } from '@angular/common';
import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, PLATFORM_ID, ViewChild, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import type { CircleMarker, Map as LeafletMap } from 'leaflet';

import { AppLocation, LocationPickerDialogData, LocationSelectionResult } from '../../../core/models/location.model';
import { LocationFacade } from '../../facades/location.facade';

const DEFAULT_CENTER: AppLocation = {
  latitude: -34.6037,
  longitude: -58.3816,
  addressLabel: 'Buenos Aires, Argentina'
};

@Component({
  selector: 'app-location-picker-dialog',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './location-picker-dialog.component.html',
  styleUrls: ['./location-picker-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LocationPickerDialogComponent implements AfterViewInit, OnDestroy {
  private readonly dialogRef = inject(MatDialogRef<LocationPickerDialogComponent, LocationSelectionResult>);
  private readonly locationFacade = inject(LocationFacade);
  private readonly platformId = inject(PLATFORM_ID);
  readonly data = inject<LocationPickerDialogData | null>(MAT_DIALOG_DATA, { optional: true }) ?? {};

  @ViewChild('mapCanvas') private mapCanvas?: ElementRef<HTMLElement>;

  readonly state = signal<'idle' | 'loading' | 'ready' | 'error'>('idle');
  readonly errorMessage = signal('');
  readonly selectedLocation = signal<AppLocation | null>(this.getInitialLocation());
  readonly googleMapsUrl = computed(() => this.locationFacade.buildNavigationUrl(this.selectedLocation()));
  readonly coordinatesLabel = computed(() => {
    const location = this.selectedLocation();
    if (!this.locationFacade.isValid(location)) {
      return 'Todavía no marcaste un punto en el mapa.';
    }

    return `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  });

  private mapInstance: LeafletMap | null = null;
  private markerInstance: CircleMarker | null = null;

  ngAfterViewInit(): void {
    queueMicrotask(() => {
      void this.initializeMap();
    });
  }

  ngOnDestroy(): void {
    this.mapInstance?.remove();
    this.mapInstance = null;
    this.markerInstance = null;
  }

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

  private async initializeMap(): Promise<void> {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const mapElement = this.mapCanvas?.nativeElement;
    if (!mapElement) {
      this.state.set('error');
      this.errorMessage.set('No se pudo preparar el contenedor del mapa.');
      return;
    }

    this.state.set('loading');

    try {
      const leaflet = await import('leaflet');
      const initialLocation = this.selectedLocation() ?? DEFAULT_CENTER;
      const center: [number, number] = [initialLocation.latitude, initialLocation.longitude];

      this.mapInstance = leaflet.map(mapElement, {
        center,
        zoom: this.locationFacade.isValid(this.selectedLocation()) ? 15 : 12,
        zoomControl: true
      });

      leaflet
        .tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap contributors'
        })
        .addTo(this.mapInstance);

      if (this.locationFacade.isValid(this.selectedLocation())) {
        this.renderMarker(this.selectedLocation() as AppLocation, this.data.title ?? 'Ubicación seleccionada');
      }

      this.mapInstance.on('click', (event) => {
        const nextLocation = this.locationFacade.createFromMapSelection(event.latlng.lat, event.latlng.lng);

        this.selectedLocation.set(nextLocation);
        this.renderMarker(nextLocation, this.data.title ?? 'Ubicación seleccionada');
      });

      this.mapInstance.invalidateSize();
      this.state.set('ready');
    } catch (error) {
      this.state.set('error');
      this.errorMessage.set(resolvePickerErrorMessage(error));
    }
  }

  private renderMarker(location: AppLocation, title: string): void {
    if (!this.mapInstance) {
      return;
    }

    const coordinates: [number, number] = [location.latitude, location.longitude];

    this.markerInstance?.remove();

    import('leaflet').then((leaflet) => {
      if (!this.mapInstance) {
        return;
      }

      this.markerInstance = leaflet
        .circleMarker(coordinates, {
          radius: 10,
          weight: 3,
          color: '#b71c1c',
          fillColor: '#ef5350',
          fillOpacity: 0.92
        })
        .addTo(this.mapInstance)
        .bindPopup(title)
        .openPopup();

      this.mapInstance.setView(coordinates, Math.max(this.mapInstance.getZoom(), 15));
    });
  }

  private getInitialLocation(): AppLocation | null {
    const candidate = this.data.initialLocation;
    return this.locationFacade.isValid(candidate) ? candidate : null;
  }
}

function resolvePickerErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return 'No se pudo cargar el selector de ubicación.';
}