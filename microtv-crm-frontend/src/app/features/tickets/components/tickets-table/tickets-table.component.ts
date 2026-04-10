import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';

import { TicketsTableData } from '../../../../core/models/ticket.model';
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
  readonly block = input.required<TicketsTableData>();

  readonly displayedColumns: Array<'id' | 'title' | 'category' | 'affectedDevice' | 'status' | 'priority' | 'createdAt' | 'assignee'> = [
    'id',
    'title',
    'category',
    'affectedDevice',
    'status',
    'priority',
    'createdAt',
    'assignee'
  ];

  labelFor(column: (typeof this.displayedColumns)[number]): string {
    return this.block().columns.find((item) => item.key === column)?.label ?? column;
  }

  hasAssignee(assigneeName?: string | null): boolean {
    return Boolean(assigneeName);
  }
}