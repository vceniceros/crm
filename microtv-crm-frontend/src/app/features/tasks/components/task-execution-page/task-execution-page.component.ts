import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { map, switchMap } from 'rxjs';

import { MockTaskExecutionService } from '../../../../core/services/mock-task-execution.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';
import { TaskAttachmentsSectionComponent } from '../task-attachments-section/task-attachments-section.component';
import { TaskChecklistTreeComponent } from '../task-checklist-tree/task-checklist-tree.component';
import { TaskCommentSectionComponent } from '../task-comment-section/task-comment-section.component';

@Component({
  selector: 'app-task-execution-page',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    PageTitleComponent,
    RouterLink,
    StatusBadgeComponent,
    TaskAttachmentsSectionComponent,
    TaskChecklistTreeComponent,
    TaskCommentSectionComponent,
    UserAvatarComponent
  ],
  templateUrl: './task-execution-page.component.html',
  styleUrl: './task-execution-page.component.scss'
})
export class TaskExecutionPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly mockTaskExecutionService = inject(MockTaskExecutionService);

  readonly task$ = this.activatedRoute.paramMap.pipe(
    map((params) => params.get('taskId') ?? ''),
    switchMap((taskId) => this.mockTaskExecutionService.getTaskExecution(taskId))
  );

  toggleSubtask(subtaskId: string, completed: boolean): void {
    const taskId = this.taskId();

    if (taskId) {
      this.mockTaskExecutionService.updateSubtask(taskId, subtaskId, completed);
    }
  }

  updateComment(comment: string): void {
    const taskId = this.taskId();

    if (taskId) {
      this.mockTaskExecutionService.updateComment(taskId, comment);
    }
  }

  addAttachments(files: readonly File[]): void {
    const taskId = this.taskId();

    if (taskId) {
      this.mockTaskExecutionService.addAttachments(taskId, files);
    }
  }

  removeAttachment(attachmentId: string): void {
    const taskId = this.taskId();

    if (taskId) {
      this.mockTaskExecutionService.removeAttachment(taskId, attachmentId);
    }
  }

  finalizeTask(): void {
    const taskId = this.taskId();

    if (taskId) {
      this.mockTaskExecutionService.finalizeTask(taskId);
    }
  }

  private taskId(): string {
    return this.activatedRoute.snapshot.paramMap.get('taskId') ?? '';
  }
}