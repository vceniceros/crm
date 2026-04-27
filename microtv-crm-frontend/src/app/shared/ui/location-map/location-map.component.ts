import { CommonModule, isPlatformBrowser } from '@angular/common';
import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnChanges, OnDestroy, PLATFORM_ID, ViewChild, computed, inject, input, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import type { Map as LeafletMap } from 'leaflet';

import { AppLocation, LocationMapMarker } from '../../../core/models/location.model';
import { LocationFacade } from '../../facades/location.facade';

@Component({
  selector: 'app-location-map',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './location-map.component.html',
  styleUrls: ['./location-map.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LocationMapComponent implements AfterViewInit, OnDestroy {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly locationFacade = inject(LocationFacade);

  @ViewChild('mapCanvas') private mapCanvas?: ElementRef<HTMLElement>;

  readonly location = input<AppLocation | null>(null);
  readonly markers = input<readonly LocationMapMarker[] | null>(null);
  readonly title = input('Ubicación');
  readonly zoom = input(15);

  readonly state = signal<'idle' | 'loading' | 'ready' | 'error' | 'invalid'>('idle');
  readonly errorMessage = signal('');
  readonly validMarkers = computed<readonly LocationMapMarker[]>(() => {
    const providedMarkers = (this.markers() ?? []).filter((marker) => this.locationFacade.isValid(marker));
    if (providedMarkers.length) {
      return providedMarkers;
    }

    const singleLocation = this.location();
    if (!this.locationFacade.isValid(singleLocation)) {
      return [];
    }

    return [{ ...singleLocation, title: this.title() }];
  });
  readonly hasValidLocation = computed(() => this.validMarkers().length > 0);

  private mapInstance: LeafletMap | null = null;
  private lastRenderSignature = '';

  ngAfterViewInit(): void {
    queueMicrotask(() => {
      void this.renderMap();
    });
  }

  ngOnChanges(): void {
    if (!this.mapCanvas?.nativeElement) {
      return;
    }

    queueMicrotask(() => {
      void this.renderMap();
    });
  }

  ngOnDestroy(): void {
    this.mapInstance?.remove();
    this.mapInstance = null;
  }

  private async renderMap(): Promise<void> {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const markers = this.validMarkers();
    if (!markers.length) {
      this.mapInstance?.remove();
      this.mapInstance = null;
      this.lastRenderSignature = '';
      this.state.set('invalid');
      return;
    }

    const signature = [this.zoom(), this.title(), ...markers.map((marker, index) => `${index}:${marker.latitude}:${marker.longitude}:${marker.title ?? ''}`)].join('|');
    if (signature === this.lastRenderSignature && this.mapInstance) {
      return;
    }

    this.mapInstance?.remove();
    this.mapInstance = null;

    const mapElement = this.mapCanvas?.nativeElement;
    if (!mapElement) {
      this.state.set('error');
      this.errorMessage.set('No se pudo preparar el contenedor del mapa.');
      return;
    }

    this.state.set('loading');

    try {
      const leaflet = await import('leaflet');
      const firstMarker = markers[0];
      const coordinates: [number, number] = [firstMarker.latitude, firstMarker.longitude];

      this.mapInstance = leaflet.map(mapElement, {
        center: coordinates,
        zoom: this.zoom(),
        zoomControl: true
      });

      leaflet
        .tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap contributors'
        })
        .addTo(this.mapInstance);

      const bounds = leaflet.latLngBounds([]);
      markers.forEach((marker, index) => {
        const markerCoordinates: [number, number] = [marker.latitude, marker.longitude];
        bounds.extend(markerCoordinates);

        const circleMarker = leaflet
          .circleMarker(markerCoordinates, {
            radius: index === 0 ? 10 : 8,
            weight: 3,
            color: index === 0 ? '#b71c1c' : '#0d47a1',
            fillColor: index === 0 ? '#ef5350' : '#42a5f5',
            fillOpacity: 0.92
          })
          .addTo(this.mapInstance as LeafletMap);

        const popupLabel = marker.title?.trim() || (index === 0 ? this.title() : `Visita ${index}`);
        circleMarker.bindPopup(popupLabel);
        if (index === 0) {
          circleMarker.openPopup();
        }
      });

      if (markers.length > 1) {
        this.mapInstance.fitBounds(bounds.pad(0.18));
      }

      this.mapInstance.invalidateSize();
      this.lastRenderSignature = signature;
      this.state.set('ready');
    } catch (error) {
      this.state.set('error');
      this.errorMessage.set(resolveMapErrorMessage(error));
    }
  }
}

function resolveMapErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return 'No se pudo renderizar el mapa en este momento.';
}