import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import { CreateTaskFormValue } from '../../../../core/models/create-task.model';
import { TaskTemplateRecord } from '../../../../core/models/task-template.model';
import { MockTasksService } from '../../../../core/services/mock-tasks.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { CreateTemplateDialogComponent } from '../../../task-templates/components/create-template-dialog/create-template-dialog.component';
import { CreateTaskDialogComponent } from '../create-task-dialog/create-task-dialog.component';
import { TasksTableComponent } from '../tasks-table/tasks-table.component';

@Component({
  selector: 'app-tasks-page',
  standalone: true,
  imports: [AsyncPipe, MatButtonModule, MatDialogModule, MatIconModule, PageTitleComponent, TasksTableComponent],
  templateUrl: './tasks-page.component.html',
  styleUrl: './tasks-page.component.scss'
})
export class TasksPageComponent {
  private readonly dialog = inject(MatDialog);
  private readonly mockTasksService = inject(MockTasksService);

  readonly tasksPage$ = this.mockTasksService.tasksPage$;

  openCreateTemplateDialog(): void {
    this.dialog
      .open<CreateTemplateDialogComponent, undefined, TaskTemplateRecord>(CreateTemplateDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '68rem'
      })
      .afterClosed()
      .subscribe((payload) => {
        if (payload) {
          console.log('Create template dialog result', payload);
        }
      });
  }

  openCreateTaskDialog(): void {
    this.dialog
      .open<CreateTaskDialogComponent, undefined, CreateTaskFormValue>(CreateTaskDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '40rem'
      })
      .afterClosed()
      .subscribe((payload) => {
        if (payload) {
          console.log('Create task dialog result', payload);
        }
      });
  }
}