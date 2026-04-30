import { CommonModule, isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnChanges,
  OnDestroy,
  PLATFORM_ID,
  ViewChild,
  computed,
  inject,
  input,
  output,
  signal
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import type { Map as MapLibreMap, MapMouseEvent, Marker as MapLibreMarker } from 'maplibre-gl';

import { crmMapConfig } from '../../../core/config/crm-api.config';

export interface LocationPickerMapCoordinates {
  lat: number;
  lon: number;
}

export interface LocationPickerMapMarker extends LocationPickerMapCoordinates {
  title?: string;
  kind?: 'primary' | 'secondary';
}

@Component({
  selector: 'app-location-picker-map',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './location-picker-map.component.html',
  styleUrl: './location-picker-map.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LocationPickerMapComponent implements AfterViewInit, OnChanges, OnDestroy {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  @ViewChild('mapShell') private mapShell?: ElementRef<HTMLElement>;
  @ViewChild('mapCanvas') private mapCanvas?: ElementRef<HTMLElement>;

  readonly styleUrl = input(crmMapConfig.styleUrl);
  readonly initialCoordinates = input<LocationPickerMapCoordinates | null>(null);
  readonly markers = input<readonly LocationPickerMapMarker[] | null>(null);
  readonly readOnly = input(false);
  readonly title = input('Ubicación');
  readonly zoom = input<number | null>(null);
  readonly showGoogleMapsLink = input(true);
  readonly defaultCenter = input<LocationPickerMapCoordinates | null>({
    lat: crmMapConfig.defaultLat,
    lon: crmMapConfig.defaultLon
  });
  readonly defaultZoom = input(crmMapConfig.defaultZoom);

  readonly onChange = output<LocationPickerMapCoordinates>();

  readonly state = signal<'idle' | 'loading' | 'ready' | 'error'>('idle');
  readonly errorMessage = signal('');
  readonly selectedCoordinates = signal<LocationPickerMapCoordinates | null>(null);
  readonly hasSelection = computed(() => this.isValidCoordinates(this.selectedCoordinates()));
  readonly hasVisibleMarker = computed(() => {
    if (this.readOnly()) {
      return this.normalizedMarkers().length > 0;
    }

    return this.hasSelection();
  });
  readonly coordinatesLabel = computed(() => {
    const coordinates = this.readOnly() ? this.normalizedMarkers()[0] ?? null : this.selectedCoordinates();
    if (!this.isValidCoordinates(coordinates)) {
      return this.readOnly() ? 'Sin coordenadas válidas para mostrar.' : 'Todavía no marcaste un punto en el mapa.';
    }

    return `${coordinates.lat.toFixed(5)}, ${coordinates.lon.toFixed(5)}`;
  });
  readonly googleMapsUrl = computed(() => {
    const coordinates = this.readOnly() ? this.normalizedMarkers()[0] ?? null : this.selectedCoordinates();
    if (!this.isValidCoordinates(coordinates)) {
      return null;
    }

    return `https://www.google.com/maps?q=${coordinates.lat},${coordinates.lon}`;
  });
  readonly normalizedMarkers = computed<readonly LocationPickerMapMarker[]>(() => {
    const providedMarkers = (this.markers() ?? [])
      .map((marker) => this.normalizeMarker(marker))
      .filter((marker): marker is LocationPickerMapMarker => marker !== null);

    if (providedMarkers.length) {
      return providedMarkers;
    }

    const initial = this.normalizeCoordinates(this.initialCoordinates());
    if (initial) {
      return [{ ...initial, title: this.title(), kind: 'primary' }];
    }

    return [];
  });

  private mapInstance: MapLibreMap | null = null;
  private editableMarker: MapLibreMarker | null = null;
  private staticMarkers: MapLibreMarker[] = [];
  private maplibreModule: Pick<typeof import('maplibre-gl'), 'Map' | 'Marker'> | null = null;
  private mapInitializationPromise: Promise<void> | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private resizeFrameId: number | null = null;
  private lastObservedMapSize: { width: number; height: number } | null = null;

  ngAfterViewInit(): void {
    const initialCoordinates = this.normalizeCoordinates(this.initialCoordinates());
    this.selectedCoordinates.set(initialCoordinates);

    queueMicrotask(() => {
      void this.syncMap();
    });
  }

  ngOnChanges(): void {
    const initialCoordinates = this.normalizeCoordinates(this.initialCoordinates());
    if (!this.areCoordinatesEqual(initialCoordinates, this.selectedCoordinates())) {
      this.selectedCoordinates.set(initialCoordinates);
    }

    if (!this.isBrowser) {
      return;
    }

    queueMicrotask(() => {
      void this.syncMap();
    });
  }

  ngOnDestroy(): void {
    this.destroyResizeObserver();
    this.clearMarkers();
    this.mapInstance?.remove();
    this.mapInstance = null;
    this.mapInitializationPromise = null;
    this.maplibreModule = null;
  }

  openInGoogleMaps(): void {
    const url = this.googleMapsUrl();
    if (!url || !this.isBrowser) {
      return;
    }

    globalThis.open(url, '_blank', 'noopener,noreferrer');
  }

  private async syncMap(): Promise<void> {
    if (!this.isBrowser) {
      return;
    }

    if (!this.mapInstance) {
      await this.initializeMap();
      return;
    }

    this.updateMapContents();
  }

  private async initializeMap(): Promise<void> {
    if (this.mapInitializationPromise || this.mapInstance) {
      return;
    }

    const mapElement = this.mapCanvas?.nativeElement;
    if (!mapElement) {
      this.state.set('error');
      this.errorMessage.set('No se pudo preparar el contenedor del mapa.');
      return;
    }

    const styleUrl = this.styleUrl().trim();
    if (!styleUrl) {
      this.state.set('error');
      this.errorMessage.set('Falta NEXT_PUBLIC_MAP_STYLE_URL en la configuración de runtime.');
      return;
    }

    this.state.set('loading');
    this.errorMessage.set('');

    this.mapInitializationPromise = (async () => {
      const imported = await import('maplibre-gl');
      const maplibre = ((imported as { default?: typeof import('maplibre-gl') }).default ?? imported);

      if (typeof maplibre.Map !== 'function' || typeof maplibre.Marker !== 'function') {
        throw new Error('No se pudo inicializar MapLibre: exportaciones Map/Marker no disponibles.');
      }

      this.maplibreModule = maplibre;

      const initialCenter = this.resolveInitialCenter();
      const map = new maplibre.Map({
        container: mapElement,
        style: styleUrl,
        center: [initialCenter.lon, initialCenter.lat],
        zoom: this.resolveInitialZoom()
      });
      map.on('error', (event) => {
        const message = event?.error instanceof Error && event.error.message.trim()
          ? event.error.message
          : 'No se pudo renderizar el mapa con el estilo configurado.';
        this.state.set('error');
        this.errorMessage.set(message);
      });

      if (!this.readOnly()) {
        map.on('click', (event: MapMouseEvent) => {
          this.updateSelection({ lat: event.lngLat.lat, lon: event.lngLat.lng }, true, true);
        });
      }

      map.on('load', () => {
        this.state.set('ready');
        this.updateMapContents(true);
        this.observeMapContainer();
      });

      this.mapInstance = map;
    })()
      .catch((error: unknown) => {
        this.state.set('error');
        this.errorMessage.set(this.resolveMapErrorMessage(error));
      })
      .finally(() => {
        this.mapInitializationPromise = null;
      });

    await this.mapInitializationPromise;
  }

  private updateMapContents(forceRecenter = false): void {
    if (!this.mapInstance || !this.maplibreModule) {
      return;
    }

    if (this.readOnly()) {
      this.renderReadOnlyMarkers(forceRecenter);
      return;
    }

    this.clearStaticMarkers();

    const selected = this.normalizeCoordinates(this.selectedCoordinates())
      ?? this.normalizeCoordinates(this.initialCoordinates());
    if (!selected) {
      this.editableMarker?.remove();
      this.editableMarker = null;
      if (forceRecenter) {
        const fallbackCenter = this.resolveFallbackCenter();
        this.mapInstance.easeTo({ center: [fallbackCenter.lon, fallbackCenter.lat], zoom: this.resolveInitialZoom() });
      }
      return;
    }

    this.ensureEditableMarker(selected);
    if (forceRecenter || !this.mapInstance.getBounds().contains([selected.lon, selected.lat])) {
      this.mapInstance.easeTo({ center: [selected.lon, selected.lat], zoom: this.resolveFocusedZoom() });
    }
  }

  private renderReadOnlyMarkers(forceRecenter: boolean): void {
    if (!this.mapInstance || !this.maplibreModule) {
      return;
    }

    this.editableMarker?.remove();
    this.editableMarker = null;
    this.clearStaticMarkers();

    const markers = this.normalizedMarkers();
    if (!markers.length) {
      if (forceRecenter) {
        const fallbackCenter = this.resolveFallbackCenter();
        this.mapInstance.easeTo({ center: [fallbackCenter.lon, fallbackCenter.lat], zoom: this.resolveInitialZoom() });
      }
      return;
    }

    const maplibre = this.maplibreModule;
    for (const marker of markers) {
      const mapMarker = new maplibre.Marker({
        element: this.createMarkerElement(marker.kind ?? 'primary'),
        anchor: 'bottom'
      }).setLngLat([marker.lon, marker.lat]);

      mapMarker.addTo(this.mapInstance);
      this.staticMarkers.push(mapMarker);
    }

    if (markers.length > 1) {
      const bounds = markers.reduce(
        (accumulator, marker) => {
          return {
            minLat: Math.min(accumulator.minLat, marker.lat),
            maxLat: Math.max(accumulator.maxLat, marker.lat),
            minLon: Math.min(accumulator.minLon, marker.lon),
            maxLon: Math.max(accumulator.maxLon, marker.lon)
          };
        },
        {
          minLat: markers[0].lat,
          maxLat: markers[0].lat,
          minLon: markers[0].lon,
          maxLon: markers[0].lon
        }
      );

      this.mapInstance.fitBounds(
        [
          [bounds.minLon, bounds.minLat],
          [bounds.maxLon, bounds.maxLat]
        ],
        { padding: 48, maxZoom: this.resolveFocusedZoom() }
      );
      return;
    }

    const marker = markers[0];
    if (forceRecenter || !this.mapInstance.getBounds().contains([marker.lon, marker.lat])) {
      this.mapInstance.easeTo({ center: [marker.lon, marker.lat], zoom: this.resolveFocusedZoom() });
    }
  }

  private ensureEditableMarker(coordinates: LocationPickerMapCoordinates): void {
    if (!this.mapInstance || !this.maplibreModule) {
      return;
    }

    if (!this.editableMarker) {
      const maplibre = this.maplibreModule;
      this.editableMarker = new maplibre.Marker({
        element: this.createMarkerElement('primary'),
        anchor: 'bottom',
        draggable: true
      })
        .setLngLat([coordinates.lon, coordinates.lat])
        .addTo(this.mapInstance);

      this.editableMarker.on('dragend', () => {
        const draggedCoordinates = this.editableMarker?.getLngLat();
        if (!draggedCoordinates) {
          return;
        }

        this.updateSelection({ lat: draggedCoordinates.lat, lon: draggedCoordinates.lng }, true, false);
      });
      return;
    }

    this.editableMarker.setLngLat([coordinates.lon, coordinates.lat]);
  }

  private updateSelection(
    coordinates: LocationPickerMapCoordinates,
    emit = false,
    recenter = false
  ): void {
    const normalized = this.normalizeCoordinates(coordinates);
    if (!normalized) {
      return;
    }

    this.selectedCoordinates.set(normalized);
    this.ensureEditableMarker(normalized);

    if (recenter && this.mapInstance) {
      this.mapInstance.easeTo({ center: [normalized.lon, normalized.lat], zoom: this.resolveFocusedZoom() });
    }

    if (emit) {
      this.onChange.emit(normalized);
    }
  }

  private observeMapContainer(): void {
    const observedElement = this.mapShell?.nativeElement ?? this.mapCanvas?.nativeElement;
    if (!this.isBrowser || !this.mapInstance || !observedElement || typeof ResizeObserver === 'undefined') {
      return;
    }

    this.destroyResizeObserver();

    this.resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      const nextSize = {
        width: Math.round(entry.contentRect.width),
        height: Math.round(entry.contentRect.height)
      };

      if (nextSize.width <= 0 || nextSize.height <= 0) {
        return;
      }

      if (
        this.lastObservedMapSize
        && this.lastObservedMapSize.width === nextSize.width
        && this.lastObservedMapSize.height === nextSize.height
      ) {
        return;
      }

      this.lastObservedMapSize = nextSize;
      this.scheduleMapResize();
    });
    this.resizeObserver.observe(observedElement);
  }

  private destroyResizeObserver(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.lastObservedMapSize = null;

    if (this.resizeFrameId !== null) {
      cancelAnimationFrame(this.resizeFrameId);
      this.resizeFrameId = null;
    }
  }

  private scheduleMapResize(): void {
    if (!this.mapInstance || this.resizeFrameId !== null) {
      return;
    }

    this.resizeFrameId = requestAnimationFrame(() => {
      this.resizeFrameId = null;
      this.mapInstance?.resize();
    });
  }

  private clearMarkers(): void {
    this.editableMarker?.remove();
    this.editableMarker = null;
    this.clearStaticMarkers();
  }

  private clearStaticMarkers(): void {
    for (const marker of this.staticMarkers) {
      marker.remove();
    }
    this.staticMarkers = [];
  }

  private normalizeMarker(marker: LocationPickerMapMarker | null | undefined): LocationPickerMapMarker | null {
    const normalizedCoordinates = this.normalizeCoordinates(marker);
    if (!normalizedCoordinates) {
      return null;
    }

    return {
      ...normalizedCoordinates,
      title: marker?.title,
      kind: marker?.kind
    };
  }

  private normalizeCoordinates(coordinates: LocationPickerMapCoordinates | null | undefined): LocationPickerMapCoordinates | null {
    if (!coordinates || !this.isValidCoordinates(coordinates)) {
      return null;
    }

    return {
      lat: coordinates.lat,
      lon: coordinates.lon
    };
  }

  private isValidCoordinates(coordinates: LocationPickerMapCoordinates | null | undefined): coordinates is LocationPickerMapCoordinates {
    return Boolean(
      coordinates
      && Number.isFinite(coordinates.lat)
      && Number.isFinite(coordinates.lon)
      && coordinates.lat >= -90
      && coordinates.lat <= 90
      && coordinates.lon >= -180
      && coordinates.lon <= 180
    );
  }

  private areCoordinatesEqual(
    left: LocationPickerMapCoordinates | null,
    right: LocationPickerMapCoordinates | null
  ): boolean {
    if (!left && !right) {
      return true;
    }

    if (!left || !right) {
      return false;
    }

    return left.lat === right.lat && left.lon === right.lon;
  }

  private resolveInitialCenter(): LocationPickerMapCoordinates {
    const editableCoordinates = this.normalizeCoordinates(this.selectedCoordinates())
      ?? this.normalizeCoordinates(this.initialCoordinates());
    if (editableCoordinates) {
      return editableCoordinates;
    }

    const markerCoordinates = this.normalizedMarkers()[0];
    if (markerCoordinates) {
      return markerCoordinates;
    }

    return this.resolveFallbackCenter();
  }

  private resolveFallbackCenter(): LocationPickerMapCoordinates {
    return this.normalizeCoordinates(this.defaultCenter()) ?? {
      lat: crmMapConfig.defaultLat,
      lon: crmMapConfig.defaultLon
    };
  }

  private resolveInitialZoom(): number {
    if (typeof this.zoom() === 'number' && Number.isFinite(this.zoom())) {
      return this.zoom() as number;
    }

    if (typeof this.defaultZoom() === 'number' && Number.isFinite(this.defaultZoom())) {
      return this.defaultZoom();
    }

    return crmMapConfig.defaultZoom;
  }

  private resolveFocusedZoom(): number {
    return Math.max(12, this.resolveInitialZoom());
  }

  private createMarkerElement(kind: 'primary' | 'secondary'): HTMLElement {
    const element = document.createElement('div');
    element.className = `location-picker-map__marker location-picker-map__marker--${kind}`;

    // Dynamic marker nodes do not get Angular style scoping attributes, so we set core styles inline.
    element.style.width = '18px';
    element.style.height = '18px';
    element.style.borderRadius = '999px';
    element.style.border = '2px solid #ffffff';
    element.style.boxShadow = '0 5px 16px rgba(15, 23, 42, 0.32)';
    element.style.background = kind === 'primary' ? '#d32f2f' : '#1565c0';
    element.style.cursor = 'grab';

    return element;
  }

  private resolveMapErrorMessage(error: unknown): string {
    if (error instanceof Error && error.message.trim()) {
      return error.message;
    }

    return 'No se pudo cargar el mapa en este momento.';
  }
}
