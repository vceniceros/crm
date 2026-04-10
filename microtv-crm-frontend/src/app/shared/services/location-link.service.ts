import { isPlatformBrowser } from '@angular/common';
import { inject, Injectable, PLATFORM_ID } from '@angular/core';

import { AppLocation } from '../../core/models/location.model';

@Injectable({ providedIn: 'root' })
export class LocationLinkService {
  private readonly platformId = inject(PLATFORM_ID);

  isValidLocation(location: AppLocation | null | undefined): location is AppLocation {
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

  buildGoogleMapsUrl(location: AppLocation | null | undefined): string | null {
    if (!this.isValidLocation(location)) {
      return null;
    }

    const coordinates = `${location.latitude},${location.longitude}`;
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(coordinates)}`;
  }

  openInGoogleMaps(location: AppLocation | null | undefined): boolean {
    const url = this.buildGoogleMapsUrl(location);

    if (!url || !isPlatformBrowser(this.platformId)) {
      return false;
    }

    window.open(url, '_blank', 'noopener,noreferrer');
    return true;
  }
}