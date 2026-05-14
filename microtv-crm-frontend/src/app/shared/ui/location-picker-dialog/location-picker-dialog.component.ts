import { CommonModule, isPlatformBrowser } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnDestroy, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

import { AppLocation, LocationPickerDialogData, LocationSelectionResult } from '../../../core/models/location.model';
import { LocationFacade } from '../../facades/location.facade';
import { LocationPickerMapComponent, LocationPickerMapCoordinates } from '../location-picker-map/location-picker-map.component';

interface NominatimSearchResult {
  display_name: string;
  lat: string;
  lon: string;
}

interface AddressSearchResult {
  label: string;
  latitude: number;
  longitude: number;
}

@Component({
  selector: 'app-location-picker-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    LocationPickerMapComponent
  ],
  templateUrl: './location-picker-dialog.component.html',
  styleUrls: ['./location-picker-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LocationPickerDialogComponent implements OnDestroy {
  private readonly dialogRef = inject(MatDialogRef<LocationPickerDialogComponent, LocationSelectionResult>);
  private readonly locationFacade = inject(LocationFacade);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);
  private searchAbortController: AbortController | null = null;
  readonly data = inject<LocationPickerDialogData | null>(MAT_DIALOG_DATA, { optional: true }) ?? {};

  readonly selectedLocation = signal<AppLocation | null>(this.getInitialLocation());
  readonly addressQuery = signal('');
  readonly addressSearchState = signal<'idle' | 'loading' | 'ready' | 'empty' | 'error'>('idle');
  readonly addressSearchResults = signal<readonly AddressSearchResult[]>([]);
  readonly addressSearchMessage = signal('');
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
  readonly selectedAddressLabel = computed(() => this.selectedLocation()?.addressLabel?.trim() || '');

  ngOnDestroy(): void {
    this.searchAbortController?.abort();
    this.searchAbortController = null;
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

  async searchAddress(event?: Event): Promise<void> {
    event?.preventDefault();

    const query = this.addressQuery().trim();
    if (query.length < 3) {
      this.addressSearchState.set('error');
      this.addressSearchMessage.set('Escribi al menos 3 caracteres para buscar una direccion.');
      this.addressSearchResults.set([]);
      return;
    }

    if (!this.isBrowser) {
      this.addressSearchState.set('error');
      this.addressSearchMessage.set('La busqueda de direcciones solo esta disponible en el navegador.');
      this.addressSearchResults.set([]);
      return;
    }

    this.searchAbortController?.abort();
    const controller = new AbortController();
    this.searchAbortController = controller;
    this.addressSearchState.set('loading');
    this.addressSearchMessage.set('');
    this.addressSearchResults.set([]);

    try {
      const params = new URLSearchParams({
        format: 'json',
        limit: '6',
        q: query
      });
      const response = await fetch(`https://nominatim.openstreetmap.org/search?${params.toString()}`, {
        headers: {
          Accept: 'application/json'
        },
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error('No se pudo consultar el buscador de direcciones.');
      }

      const payload = (await response.json()) as NominatimSearchResult[];
      const results = payload
        .map((item) => this.normalizeSearchResult(item))
        .filter((item): item is AddressSearchResult => item !== null);

      if (!results.length) {
        this.addressSearchState.set('empty');
        this.addressSearchMessage.set('No encontramos resultados para esa direccion.');
        return;
      }

      this.addressSearchResults.set(results);
      this.addressSearchState.set('ready');
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }

      this.addressSearchState.set('error');
      this.addressSearchMessage.set(error instanceof Error ? error.message : 'No se pudo buscar la direccion.');
    } finally {
      if (this.searchAbortController === controller) {
        this.searchAbortController = null;
      }
    }
  }

  selectAddressResult(result: AddressSearchResult): void {
    const nextLocation = this.locationFacade.createFromMapSelection(result.latitude, result.longitude, result.label);
    this.selectedLocation.set(nextLocation);
    this.addressQuery.set(result.label);
    this.addressSearchResults.set([]);
    this.addressSearchState.set('idle');
    this.addressSearchMessage.set('');
  }

  onCoordinatesChanged(coordinates: LocationPickerMapCoordinates): void {
    const nextLocation = this.locationFacade.createFromMapSelection(coordinates.lat, coordinates.lon);
    this.selectedLocation.set(nextLocation);
  }

  private getInitialLocation(): AppLocation | null {
    const candidate = this.data.initialLocation;
    return this.locationFacade.isValid(candidate) ? candidate : null;
  }

  private normalizeSearchResult(result: NominatimSearchResult): AddressSearchResult | null {
    const latitude = Number(result.lat);
    const longitude = Number(result.lon);
    const label = result.display_name?.trim();

    if (!label || !Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      return null;
    }

    return {
      label,
      latitude,
      longitude
    };
  }
}
