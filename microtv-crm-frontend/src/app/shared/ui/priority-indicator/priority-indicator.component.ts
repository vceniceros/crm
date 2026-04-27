import { Component, input } from '@angular/core';

import { TicketPriorityTone } from '../../../core/models/dashboard.model';

@Component({
  selector: 'app-priority-indicator',
  standalone: true,
  templateUrl: './priority-indicator.component.html',
  styleUrl: './priority-indicator.component.scss'
})
export class PriorityIndicatorComponent {
  readonly label = input.required<string>();
  readonly tone = input.required<TicketPriorityTone>();
}