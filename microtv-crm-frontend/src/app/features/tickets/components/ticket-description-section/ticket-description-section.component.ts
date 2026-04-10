import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';

import { TicketExecutionItem } from '../../../../core/models/ticket-execution.model';
import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';

@Component({
  selector: 'app-ticket-description-section',
  standalone: true,
  imports: [DatePipe, MatCardModule, PriorityIndicatorComponent, StatusBadgeComponent],
  templateUrl: './ticket-description-section.component.html',
  styleUrl: './ticket-description-section.component.scss'
})
export class TicketDescriptionSectionComponent {
  readonly ticket = input.required<TicketExecutionItem>();
}