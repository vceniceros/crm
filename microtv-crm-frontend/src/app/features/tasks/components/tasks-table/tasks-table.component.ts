import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';

import { TasksTableData } from '../../../../core/models/task.model';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-tasks-table',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatTableModule, RouterLink, StatusBadgeComponent, UserAvatarComponent],
  templateUrl: './tasks-table.component.html',
  styleUrl: './tasks-table.component.scss'
})
export class TasksTableComponent {
  readonly block = input.required<TasksTableData>();

  readonly displayedColumns: Array<'id' | 'title' | 'client' | 'subtasks' | 'status' | 'assignedTo'> = [
    'id',
    'title',
    'client',
    'subtasks',
    'status',
    'assignedTo'
  ];

  labelFor(column: (typeof this.displayedColumns)[number]): string {
    return this.block().columns.find((item) => item.key === column)?.label ?? column;
  }

  completionRatio(completed: number, total: number): number {
    if (!total) {
      return 0;
    }

    return Math.round((completed / total) * 100);
  }
}