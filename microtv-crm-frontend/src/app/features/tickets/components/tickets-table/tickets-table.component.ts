import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';

import { TicketTableItem } from '../../../../core/models/ticket-management.model';
import { ListingViewMode } from '../../../../shared/services/listing-view-preference.service';
import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-tickets-table',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatTableModule, RouterLink, PriorityIndicatorComponent, StatusBadgeComponent, UserAvatarComponent],
  templateUrl: './tickets-table.component.html',
  styleUrl: './tickets-table.component.scss'
})
export class TicketsTableComponent {
  readonly title = input.required<string>();
  readonly items = input.required<readonly TicketTableItem[]>();
  readonly canSelfAssign = input(false);
  readonly isAssigning = input(false);
  readonly assigningTicketId = input<string | null>(null);
  readonly viewMode = input<ListingViewMode>('table');
  readonly selfAssignRequested = output<string>();

  readonly displayedColumns: Array<'ticketNumber' | 'title' | 'client' | 'location' | 'status' | 'priority' | 'updatedAt' | 'assignedTo'> = [
    'ticketNumber',
    'title',
    'client',
    'location',
    'status',
    'priority',
    'updatedAt',
    'assignedTo'
  ];

  readonly labels: Record<(typeof this.displayedColumns)[number], string> = {
    ticketNumber: 'Ticket',
    title: 'Título',
    client: 'Cliente',
    location: 'Ubicación',
    status: 'Estado',
    priority: 'Prioridad',
    updatedAt: 'Actualizado',
    assignedTo: 'Asignado'
  };

  labelFor(column: (typeof this.displayedColumns)[number]): string {
    return this.labels[column] ?? column;
  }

  initialsFor(value: string): string {
    return value
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((segment) => segment[0]?.toUpperCase() ?? '')
      .join('') || 'SA';
  }

  requestSelfAssign(ticketId: string): void {
    this.selfAssignRequested.emit(ticketId);
  }
}