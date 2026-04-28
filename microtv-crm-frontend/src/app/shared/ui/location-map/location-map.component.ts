import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import { AppLocation, LocationMapMarker } from '../../../core/models/location.model';
import { LocationFacade } from '../../facades/location.facade';
import { LocationPickerMapComponent } from '../location-picker-map/location-picker-map.component';

@Component({
  selector: 'app-location-map',
  standalone: true,
  imports: [CommonModule, MatIconModule, LocationPickerMapComponent],
  templateUrl: './location-map.component.html',
  styleUrls: ['./location-map.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LocationMapComponent {
  private readonly locationFacade = inject(LocationFacade);

  readonly location = input<AppLocation | null>(null);
  readonly markers = input<readonly LocationMapMarker[] | null>(null);
  readonly title = input('Ubicación');
  readonly zoom = input(15);

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
  readonly normalizedMarkers = computed(() => {
    return this.validMarkers().map((marker, index) => ({
      lat: marker.latitude,
      lon: marker.longitude,
      title: marker.title,
      kind: index === 0 ? 'primary' as const : 'secondary' as const
    }));
  });
}