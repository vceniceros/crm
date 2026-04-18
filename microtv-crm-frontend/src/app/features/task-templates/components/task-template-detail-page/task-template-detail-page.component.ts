import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { formatAssignmentPolicy, formatRoleKey, TaskTemplate } from '../../../../core/models/task-management.model';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { toTaskTone } from '../../../../core/models/task-management.model';

@Component({
  selector: 'app-task-template-detail-page',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule, PageTitleComponent, RouterLink, StatusBadgeComponent],
  templateUrl: './task-template-detail-page.component.html',
  styleUrl: './task-template-detail-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TaskTemplateDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly destroyRef = inject(DestroyRef);

  readonly template = signal<TaskTemplate | null>(null);
  readonly isLoading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = computed(() => {
    const roles = this.authSessionService.sessionSnapshot()?.user.role_keys ?? [];
    return roles.includes('admin') || roles.includes('ejecutivo');
  });

  constructor() {
    const templateId = this.route.snapshot.paramMap.get('templateId');
    if (!templateId) {
      this.errorMessage.set('No se indicó un template válido.');
      this.isLoading.set(false);
      return;
    }

    this.taskManagementService
      .getTemplate(templateId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (template) => {
          this.template.set(template);
          this.isLoading.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isLoading.set(false);
        }
      });
  }

  readonly formatRoleKey = formatRoleKey;
  readonly formatAssignmentPolicy = formatAssignmentPolicy;
  readonly toTaskTone = toTaskTone;
}