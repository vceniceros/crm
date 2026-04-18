import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
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
  selector: 'app-task-templates-page',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule, PageTitleComponent, RouterLink, StatusBadgeComponent],
  templateUrl: './task-templates-page.component.html',
  styleUrl: './task-templates-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TaskTemplatesPageComponent {
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly isLoading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly templates = signal<TaskTemplate[]>([]);
  readonly canManage = computed(() => {
    const roles = this.authSessionService.sessionSnapshot()?.user.role_keys ?? [];
    return roles.includes('admin') || roles.includes('ejecutivo');
  });

  constructor() {
    this.refresh();
  }

  refresh(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.taskManagementService
      .listTemplates()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (templates) => {
          this.templates.set(templates);
          this.isLoading.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isLoading.set(false);
        }
      });
  }

  goToCreateTask(templateId: string): void {
    void this.router.navigate(['/tasks'], { queryParams: { templateId } });
  }

  toggleActivation(template: TaskTemplate): void {
    this.taskManagementService
      .setTemplateActivation(template.template_id, { is_active: !template.is_active })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated) => {
          this.templates.update((current) => current.map((item) => (item.template_id === updated.template_id ? updated : item)));
        },
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  readonly formatRoleKey = formatRoleKey;
  readonly formatAssignmentPolicy = formatAssignmentPolicy;
  readonly toTaskTone = toTaskTone;
}