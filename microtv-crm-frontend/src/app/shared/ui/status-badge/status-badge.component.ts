import { Component, input } from '@angular/core';

import { TicketStatusTone } from '../../../core/models/dashboard.model';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  templateUrl: './status-badge.component.html',
  styleUrl: './status-badge.component.scss'
})
export class StatusBadgeComponent {
  readonly label = input.required<string>();
  readonly tone = input.required<TicketStatusTone>();
}