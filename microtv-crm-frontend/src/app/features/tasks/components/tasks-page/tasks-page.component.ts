import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';

import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { AppLocation } from '../../../../core/models/location.model';
import {
  ClientSummary,
  countCompletedSubtasks,
  formatRoleKey,
  formatTaskStatus,
  TaskDetail,
  TaskSummary,
  TaskTemplate,
  toTaskTone,
  UnassignedSubtaskQueueItem
} from '../../../../core/models/task-management.model';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';

@Component({
  selector: 'app-tasks-page',
  standalone: true,
  imports: [
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTabsModule,
    LocationMapComponent,
    PageTitleComponent,
    ReactiveFormsModule,
    RouterLink,
    StatusBadgeComponent
  ],
  templateUrl: './tasks-page.component.html',
  styleUrl: './tasks-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TasksPageComponent {
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly isLoading = signal(true);
  readonly isCreatingTask = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly templates = signal<TaskTemplate[]>([]);
  readonly clients = signal<ClientSummary[]>([]);
  readonly assignedTasks = signal<TaskDetail[]>([]);
  readonly unassignedSubtasks = signal<UnassignedSubtaskQueueItem[]>([]);
  readonly trackingTasks = signal<TaskDetail[]>([]);
  readonly selectedLocation = signal<AppLocation | null>(null);
  readonly taskCreationForm = this.formBuilder.group({
    template_id: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    client_id: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    task_title: this.formBuilder.control<string | null>(null),
    task_description: this.formBuilder.control<string | null>(null)
  });

  readonly currentSession = computed(() => this.authSessionService.sessionSnapshot());
  readonly currentUserId = computed(() => this.currentSession()?.user.crm_user_id ?? null);
  readonly currentRoles = computed(() => this.currentSession()?.user.role_keys ?? []);
  readonly isAdminOrExecutive = computed(() => {
    const roles = this.currentRoles();
    return roles.includes('admin') || roles.includes('ejecutivo');
  });
  readonly canTrackGeneral = computed(() => this.currentRoles().some((role) => ['admin', 'ejecutivo', 'deposito', 'tecnico'].includes(role)));
  readonly selectedTemplate = computed(
    () => this.templates().find((template) => template.template_id === this.taskCreationForm.controls.template_id.getRawValue()) ?? null
  );

  constructor() {
    const preselectedTemplateId = this.router.parseUrl(this.router.url).queryParams['templateId'];
    if (typeof preselectedTemplateId === 'string' && preselectedTemplateId.trim()) {
      this.taskCreationForm.controls.template_id.setValue(preselectedTemplateId);
    }

    this.refresh();
  }

  refresh(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.taskManagementService.listTemplates().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (templates) => this.templates.set(templates),
      error: (error: Error) => this.errorMessage.set(error.message)
    });

    this.taskManagementService.listClients().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (clients) => this.clients.set(clients),
      error: (error: Error) => this.errorMessage.set(error.message)
    });

    this.taskManagementService.listAssignedTasks().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (summaries) => this.loadAssignedTaskDetails(summaries),
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoading.set(false);
      }
    });

    this.taskManagementService.listTrackingTasks().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (summaries) => this.loadTrackingTaskDetails(summaries),
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoading.set(false);
      }
    });

    this.taskManagementService.listUnassignedSubtasks().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (queue) => this.unassignedSubtasks.set(queue),
      error: (error: Error) => this.errorMessage.set(error.message)
    });
  }

  createTask(): void {
    if (this.taskCreationForm.invalid) {
      this.taskCreationForm.markAllAsTouched();
      this.errorMessage.set('Completá template y cliente para crear la tarea.');
      return;
    }

    this.isCreatingTask.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    if (this.hasValidSelectedLocation()) {
      this.taskManagementService
        .createLocation(this.selectedLocation() as AppLocation)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (persistedLocation) => {
            this.submitTaskCreation(persistedLocation.locationId);
          },
          error: (error: Error) => {
            this.errorMessage.set(error.message);
            this.isCreatingTask.set(false);
          }
        });
      return;
    }

    this.submitTaskCreation(null);
  }

  openLocationPicker(): void {
    this.locationPickerService
      .open({
        title: 'Seleccionar ubicación operativa de la tarea',
        initialLocation: this.selectedLocation()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result) => {
        if (!result) {
          return;
        }

        this.selectedLocation.set(result.location);
      });
  }

  clearSelectedLocation(): void {
    this.selectedLocation.set(null);
  }

  openSelectedLocationInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.selectedLocation());
  }

  hasValidSelectedLocation(): boolean {
    return this.locationLinkService.isValidLocation(this.selectedLocation());
  }

  selectedLocationLabel(): string {
    const location = this.selectedLocation();
    if (!location) {
      return 'Sin ubicación cargada';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  claimSubtask(subtaskId: string): void {
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.taskManagementService
      .claimSubtask(subtaskId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          this.successMessage.set('La subtarea fue tomada y quedó asignada a tu usuario.');
          this.refresh();
          void this.router.navigate(['/tasks', task.task_id]);
        },
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  completedSubtasks(task: TaskDetail): number {
    return countCompletedSubtasks(task.subtasks);
  }

  currentSubtask(task: TaskDetail) {
    return task.subtasks.find((subtask) => subtask.subtask_id === task.current_subtask_id) ?? null;
  }

  assigneeLabel(task: TaskDetail): string {
    return task.current_assigned_user_display_name ?? 'Sin usuario asignado';
  }

  isReadOnly(task: TaskSummary | TaskDetail): boolean {
    return Boolean(task.current_assigned_crm_user_id) && task.current_assigned_crm_user_id !== this.currentUserId();
  }

  readonly formatTaskStatus = formatTaskStatus;
  readonly formatRoleKey = formatRoleKey;
  readonly toTaskTone = toTaskTone;

  private submitTaskCreation(locationId: string | null): void {
    this.taskManagementService
      .createTaskFromTemplate({
        template_id: this.taskCreationForm.controls.template_id.getRawValue(),
        client_id: this.taskCreationForm.controls.client_id.getRawValue(),
        location_id: locationId,
        task_title: this.taskCreationForm.controls.task_title.getRawValue()?.trim() || null,
        task_description: this.taskCreationForm.controls.task_description.getRawValue()?.trim() || null
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task: TaskDetail) => {
          this.successMessage.set('La tarea se creó y quedó instanciada con el flujo real del template.');
          this.isCreatingTask.set(false);
          void this.router.navigate(['/tasks', task.task_id]);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isCreatingTask.set(false);
        }
      });
  }

  private loadAssignedTaskDetails(summaries: TaskSummary[]): void {
    if (!summaries.length) {
      this.assignedTasks.set([]);
      this.isLoading.set(false);
      return;
    }

    this.resolveTaskDetails(summaries, (ordered) => {
      this.assignedTasks.set(ordered);
      this.isLoading.set(false);
    });
  }

  private loadTrackingTaskDetails(summaries: TaskSummary[]): void {
    if (!summaries.length) {
      this.trackingTasks.set([]);
      this.isLoading.set(false);
      return;
    }

    this.resolveTaskDetails(summaries, (ordered) => {
      this.trackingTasks.set(ordered);
      this.isLoading.set(false);
    });
  }

  private resolveTaskDetails(summaries: TaskSummary[], onCompleted: (ordered: TaskDetail[]) => void): void {
    if (!summaries.length) {
      onCompleted([]);
      return;
    }

    const details: TaskDetail[] = [];
    let completedRequests = 0;
    summaries.forEach((summary) => {
      this.taskManagementService.getTaskDetail(summary.task_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (detail) => {
          details.push(detail);
          completedRequests += 1;
          if (completedRequests === summaries.length) {
            const ordered = [...details].sort((left, right) => right.created_at.localeCompare(left.created_at));
            onCompleted(ordered);
          }
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isLoading.set(false);
        }
      });
    });
  }
}