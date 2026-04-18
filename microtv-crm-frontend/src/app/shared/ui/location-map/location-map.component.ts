import { CommonModule, isPlatformBrowser } from '@angular/common';
import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, PLATFORM_ID, ViewChild, computed, inject, input, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import type { Map as LeafletMap } from 'leaflet';

import { AppLocation } from '../../../core/models/location.model';
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
  readonly title = input('Ubicación');
  readonly zoom = input(15);

  readonly state = signal<'idle' | 'loading' | 'ready' | 'error' | 'invalid'>('idle');
  readonly errorMessage = signal('');
  readonly hasValidLocation = computed(() => this.locationFacade.isValid(this.location()));

  private mapInstance: LeafletMap | null = null;

  ngAfterViewInit(): void {
    queueMicrotask(() => {
      void this.initializeMap();
    });
  }

  ngOnDestroy(): void {
    this.mapInstance?.remove();
    this.mapInstance = null;
  }

  private async initializeMap(): Promise<void> {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const location = this.location();
    if (!this.locationFacade.isValid(location)) {
      this.state.set('invalid');
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
      const coordinates: [number, number] = [location.latitude, location.longitude];

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

      leaflet
        .circleMarker(coordinates, {
          radius: 10,
          weight: 3,
          color: '#b71c1c',
          fillColor: '#ef5350',
          fillOpacity: 0.92
        })
        .addTo(this.mapInstance)
        .bindPopup(this.title())
        .openPopup();

      this.mapInstance.invalidateSize();
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