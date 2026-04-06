import { Component, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';

import { RecentTicketsBlock } from '../../../../core/models/dashboard.model';
import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-recent-tickets-table',
  standalone: true,
  imports: [MatCardModule, MatTableModule, PriorityIndicatorComponent, StatusBadgeComponent, UserAvatarComponent],
  templateUrl: './recent-tickets-table.component.html',
  styleUrl: './recent-tickets-table.component.scss'
})
export class RecentTicketsTableComponent {
  readonly block = input.required<RecentTicketsBlock>();

  readonly displayedColumns: Array<'id' | 'subject' | 'client' | 'priority' | 'status' | 'assignedTo'> = [
    'id',
    'subject',
    'client',
    'priority',
    'status',
    'assignedTo'
  ];

  labelFor(column: (typeof this.displayedColumns)[number]): string {
    return this.block().columns.find((item) => item.key === column)?.label ?? column;
  }
}