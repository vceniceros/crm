import { isPlatformBrowser } from '@angular/common';
import { inject, Injectable, PLATFORM_ID } from '@angular/core';

import { AppLocation } from '../../core/models/location.model';
import { LocationFacade } from '../facades/location.facade';

@Injectable({ providedIn: 'root' })
export class LocationLinkService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly locationFacade = inject(LocationFacade);

  isValidLocation(location: AppLocation | null | undefined): location is AppLocation {
    return this.locationFacade.isValid(location);
  }

  buildGoogleMapsUrl(location: AppLocation | null | undefined): string | null {
    return this.locationFacade.buildNavigationUrl(location);
  }

  openInGoogleMaps(location: AppLocation | null | undefined): boolean {
    if (!isPlatformBrowser(this.platformId)) {
      return false;
    }

    return this.locationFacade.openNavigation(location);
  }
}