import { isPlatformBrowser } from '@angular/common';
import { inject, Injectable, PLATFORM_ID } from '@angular/core';

import { AppLocation } from '../../core/models/location.model';

@Injectable({ providedIn: 'root' })
export class LocationFacade {
  private readonly platformId = inject(PLATFORM_ID);

  isValid(location: AppLocation | null | undefined): location is AppLocation {
    return Boolean(
      location
      && Number.isFinite(location.latitude)
      && Number.isFinite(location.longitude)
      && location.latitude >= -90
      && location.latitude <= 90
      && location.longitude >= -180
      && location.longitude <= 180
    );
  }

  createFromMapSelection(latitude: number, longitude: number, addressLabel?: string | null): AppLocation {
    return {
      latitude,
      longitude,
      addressLabel: addressLabel?.trim() || this.buildSelectionLabel(latitude, longitude)
    };
  }

  buildNavigationUrl(location: AppLocation | null | undefined): string | null {
    if (!this.isValid(location)) {
      return null;
    }

    const coordinates = `${location.latitude},${location.longitude}`;
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(coordinates)}`;
  }

  openNavigation(location: AppLocation | null | undefined): boolean {
    const url = this.buildNavigationUrl(location);

    if (!url || !isPlatformBrowser(this.platformId)) {
      return false;
    }

    window.open(url, '_blank', 'noopener,noreferrer');
    return true;
  }

  private buildSelectionLabel(latitude: number, longitude: number): string {
    return `Punto marcado ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
  }
}