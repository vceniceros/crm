import { DatePipe } from '@angular/common';
import { Component, computed, inject, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { formatTicketPriority, formatTicketStatus, TicketDetail } from '../../../../core/models/ticket-management.model';
import { AppLocation, LocationMapMarker } from '../../../../core/models/location.model';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';
import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';

@Component({
  selector: 'app-ticket-description-section',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule, MatIconModule, LocationMapComponent, PriorityIndicatorComponent, StatusBadgeComponent],
  templateUrl: './ticket-description-section.component.html',
  styleUrl: './ticket-description-section.component.scss'
})
export class TicketDescriptionSectionComponent {
  private readonly locationLinkService = inject(LocationLinkService);

  readonly ticket = input.required<TicketDetail>();

  readonly formatTicketStatus = formatTicketStatus;
  readonly formatTicketPriority = formatTicketPriority;

  readonly ticketLocation = computed<AppLocation | null>(() => {
    const location = this.ticket().location;
    if (!location) {
      return null;
    }

    return {
      latitude: location.latitude,
      longitude: location.longitude,
      addressLabel: location.address_label?.trim() || location.formatted_address?.trim() || undefined
    };
  });

  readonly locationMarkers = computed<LocationMapMarker[]>(() => {
    const markers: LocationMapMarker[] = [];
    const primaryLocation = this.ticketLocation();
    if (primaryLocation) {
      markers.push({
        ...primaryLocation,
        title: primaryLocation.addressLabel?.trim() || 'Ubicación principal del ticket'
      });
    }

    let visitIndex = 0;
    for (const comment of this.ticket().comments ?? []) {
      const location = comment.location;
      if (!location) {
        continue;
      }

      visitIndex += 1;
      markers.push({
        latitude: location.latitude,
        longitude: location.longitude,
        addressLabel: location.address_label?.trim() || location.formatted_address?.trim() || undefined,
        title: location.address_label?.trim() || location.formatted_address?.trim() || `Visita ${visitIndex}`
      });
    }

    return markers;
  });

  readonly additionalVisitLocations = computed<LocationMapMarker[]>(() => this.locationMarkers().slice(1));

  readonly hasTicketLocation = computed<boolean>(() => this.locationLinkService.isValidLocation(this.ticketLocation()));

  openTicketLocationInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.ticketLocation());
  }
}