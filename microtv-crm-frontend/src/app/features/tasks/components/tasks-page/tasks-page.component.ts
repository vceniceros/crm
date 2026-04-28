import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';

import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { UI_HELP_TEXTS } from '../../../../core/config/ui-help-texts.config';
import { AppLocation } from '../../../../core/models/location.model';
import {
  buildInitials,
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
import { TaskListItem, TasksTableData } from '../../../../core/models/task.model';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { ListingViewMode, ListingViewPreferenceService } from '../../../../shared/services/listing-view-preference.service';
import { ListingControlsComponent, ListingSortDirection, ListingStatusOption } from '../../../../shared/ui/listing-controls/listing-controls.component';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';
import { ContextHelpCardComponent } from '../../../../shared/ui/context-help-card/context-help-card.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { TasksTableComponent } from '../tasks-table/tasks-table.component';

type TaskListContextId = 'assigned' | 'unassigned' | 'tracking' | 'history';

interface TaskListUiState {
  search: string;
  status: string;
  sortDirection: ListingSortDirection;
  viewMode: ListingViewMode;
}

@Component({
  selector: 'app-tasks-page',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTabsModule,
    ContextHelpCardComponent,
    ListingControlsComponent,
    LocationMapComponent,
    PageTitleComponent,
    ReactiveFormsModule,
    RouterLink,
    StatusBadgeComponent,
    TasksTableComponent
  ],
  templateUrl: './tasks-page.component.html',
  styleUrl: './tasks-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TasksPageComponent {
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly listingViewPreferenceService = inject(ListingViewPreferenceService);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly helpText = UI_HELP_TEXTS.tasks;

  readonly isLoading = signal(true);
  readonly isCreatingTask = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly initialTabIndex = signal(0);
  readonly highlightedHistoryTaskId = signal<string | null>(null);
  readonly templates = signal<TaskTemplate[]>([]);
  readonly clients = signal<ClientSummary[]>([]);
  readonly assignedTasks = signal<TaskDetail[]>([]);
  readonly unassignedSubtasks = signal<UnassignedSubtaskQueueItem[]>([]);
  readonly trackingTasks = signal<TaskDetail[]>([]);
  readonly historyTasks = signal<TaskDetail[]>([]);
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
  readonly isAdmin = computed(() => this.currentRoles().includes('admin'));
  readonly isAdminOrExecutive = computed(() => {
    const roles = this.currentRoles();
    return roles.includes('admin') || roles.includes('ejecutivo');
  });
  readonly canTrackGeneral = computed(() => this.currentRoles().some((role) => ['admin', 'ejecutivo', 'deposito', 'tecnico'].includes(role)));
  readonly taskStatusOptions: readonly ListingStatusOption[] = [
    { value: 'all', label: 'Todos los estados' },
    { value: 'PENDING', label: 'Pendiente' },
    { value: 'IN_PROGRESS', label: 'En progreso' },
    { value: 'BLOCKED', label: 'Bloqueada' },
    { value: 'PENDING_APPROVAL', label: 'Pendiente aprobacion ejecutiva' },
    { value: 'COMPLETED', label: 'Completada' },
    { value: 'pending_assignment', label: 'Pendiente de asignacion' },
    { value: 'assigned', label: 'Asignada' },
    { value: 'in_progress', label: 'En progreso (subtarea)' },
    { value: 'completed', label: 'Completada (subtarea)' },
    { value: 'rejected', label: 'Rechazada' },
    { value: 'on_hold', label: 'En espera' }
  ];
  readonly listUiState = signal<Record<TaskListContextId, TaskListUiState>>({
    assigned: this.buildInitialListUiState('assigned'),
    unassigned: this.buildInitialListUiState('unassigned'),
    tracking: this.buildInitialListUiState('tracking'),
    history: this.buildInitialListUiState('history')
  });
  readonly assignedVisibleTasks = computed(() => this.applyTaskFilters(this.assignedTasks(), 'assigned'));
  readonly trackingVisibleTasks = computed(() => this.applyTaskFilters(this.trackingTasks(), 'tracking'));
  readonly historyVisibleTasks = computed(() => this.applyTaskFilters(this.historyTasks(), 'history'));
  readonly unassignedVisibleSubtasks = computed(() => this.applySubtaskFilters(this.unassignedSubtasks(), 'unassigned'));
  readonly assignedTableBlock = computed<TasksTableData>(() => this.buildTaskTableBlock('Tareas asignadas a mi', this.assignedVisibleTasks()));
  readonly trackingTableBlock = computed<TasksTableData>(() => this.buildTaskTableBlock('Seguimiento general', this.trackingVisibleTasks()));
  readonly historyTableBlock = computed<TasksTableData>(() => this.buildTaskTableBlock('Historial de tareas', this.historyVisibleTasks()));
  readonly unassignedTableBlock = computed<TasksTableData>(() => this.buildUnassignedTableBlock(this.unassignedVisibleSubtasks()));
  readonly isHandset = toSignal(
    this.breakpointObserver.observe([Breakpoints.Handset]).pipe(map((state) => state.matches)),
    { initialValue: false }
  );
  readonly selectedTemplate = computed(
    () => this.templates().find((template) => template.template_id === this.taskCreationForm.controls.template_id.getRawValue()) ?? null
  );

  constructor() {
    const queryParams = this.activatedRoute.snapshot.queryParams;
    const preselectedTemplateId = queryParams['templateId'];
    if (typeof preselectedTemplateId === 'string' && preselectedTemplateId.trim()) {
      this.taskCreationForm.controls.template_id.setValue(preselectedTemplateId);
    }

    const highlightedTaskId = queryParams['taskId'];
    if (typeof highlightedTaskId === 'string' && highlightedTaskId.trim()) {
      this.highlightedHistoryTaskId.set(highlightedTaskId.trim());
    }

    if (this.router.url.startsWith('/tasks/history')) {
      this.initialTabIndex.set(3);
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

    if (this.isAdminOrExecutive()) {
      this.taskManagementService.listTaskHistory().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (summaries) => this.loadHistoryTaskDetails(summaries),
        error: (error: Error) => this.errorMessage.set(error.message)
      });
    } else {
      this.historyTasks.set([]);
    }

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

  approveTask(taskId: string): void {
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.taskManagementService
      .approveTask(taskId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.successMessage.set('La tarea se aprobó y se movió al historial de tareas.');
          this.refresh();
        },
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  rejectTask(taskId: string): void {
    const comment = globalThis.prompt('Motivo obligatorio del rechazo de cierre:')?.trim() ?? '';
    if (!comment) {
      this.errorMessage.set('El rechazo requiere un comentario obligatorio.');
      return;
    }

    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.taskManagementService
      .rejectTaskApproval(taskId, { comment })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.successMessage.set('El cierre fue rechazado y la tarea volvió al flujo operativo.');
          this.refresh();
        },
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  canApproveTask(task: TaskDetail): boolean {
    return this.isAdminOrExecutive() && this.isPendingExecutiveApproval(task);
  }

  taskStatusLabel(task: TaskDetail): string {
    if (this.isPendingExecutiveApproval(task)) {
      return 'Pendiente de aprobacion ejecutiva';
    }

    return formatTaskStatus(task.status);
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

  listState(context: TaskListContextId): TaskListUiState {
    return this.listUiState()[context];
  }

  onListSearchChanged(context: TaskListContextId, value: string): void {
    this.updateListState(context, { search: value });
  }

  onListStatusChanged(context: TaskListContextId, value: string): void {
    this.updateListState(context, { status: value });
  }

  onListSortDirectionChanged(context: TaskListContextId, value: ListingSortDirection): void {
    this.updateListState(context, { sortDirection: value });
  }

  onListViewModeChanged(context: TaskListContextId, value: ListingViewMode): void {
    this.listingViewPreferenceService.setView(this.buildViewPreferenceKey(context), value);
    this.updateListState(context, { viewMode: value });
  }

  claimSubtaskFromRow(subtaskId: string): void {
    this.claimSubtask(subtaskId);
  }

  readonly formatTaskStatus = formatTaskStatus;
  readonly formatRoleKey = formatRoleKey;
  readonly toTaskTone = toTaskTone;

  private isPendingExecutiveApproval(task: TaskDetail): boolean {
    const allSubtasksCompleted = task.subtasks.every((subtask) => this.isCompletedSubtaskStatus(subtask.status));
    return task.status === 'BLOCKED' && !task.finalized_at && allSubtasksCompleted;
  }

  private isCompletedSubtaskStatus(status: string): boolean {
    return String(status).trim().toUpperCase() === 'COMPLETED';
  }

  private updateListState(context: TaskListContextId, partial: Partial<TaskListUiState>): void {
    this.listUiState.update((state) => ({
      ...state,
      [context]: {
        ...state[context],
        ...partial
      }
    }));
  }

  private applyTaskFilters(tasks: readonly TaskDetail[], context: TaskListContextId): TaskDetail[] {
    const state = this.listUiState()[context];
    const searchTerm = state.search.trim().toLowerCase();

    const filtered = tasks.filter((task) => {
      const statusMatches = state.status === 'all' || task.status === state.status;
      if (!statusMatches) {
        return false;
      }

      if (!searchTerm) {
        return true;
      }

      return [task.task_id, task.client_name, task.task_title].some((value) => value.toLowerCase().includes(searchTerm));
    });

    const direction = state.sortDirection === 'asc' ? 1 : -1;
    return [...filtered].sort((left, right) => left.created_at.localeCompare(right.created_at) * direction);
  }

  private applySubtaskFilters(queue: readonly UnassignedSubtaskQueueItem[], context: TaskListContextId): UnassignedSubtaskQueueItem[] {
    const state = this.listUiState()[context];
    const searchTerm = state.search.trim().toLowerCase();

    const filtered = queue.filter((item) => {
      const statusMatches = state.status === 'all' || item.status === state.status;
      if (!statusMatches) {
        return false;
      }

      if (!searchTerm) {
        return true;
      }

      return [item.subtask_id, item.client_name, item.subtask_title, item.task_title].some((value) => value.toLowerCase().includes(searchTerm));
    });

    const direction = state.sortDirection === 'asc' ? 1 : -1;
    return [...filtered].sort((left, right) => (left.order_index - right.order_index) * direction);
  }

  private buildTaskTableBlock(title: string, tasks: readonly TaskDetail[]): TasksTableData {
    const items: TaskListItem[] = tasks.map((task) => {
      const canApprove = this.canApproveTask(task);
      return {
        id: task.task_id,
        title: task.task_title,
        client: task.client_name,
        completedSubtasks: this.completedSubtasks(task),
        totalSubtasks: task.subtasks.length,
        status: this.taskStatusLabel(task),
        statusTone: toTaskTone(task.status),
        assignedToUserId: task.current_assigned_crm_user_id,
        assignedTo: this.assigneeLabel(task),
        assignedInitials: buildInitials(this.assigneeLabel(task), 'SA'),
        routeTaskId: task.task_id,
        rowActionLabel: canApprove ? 'Aprobar tarea' : undefined,
        rowActionId: canApprove ? task.task_id : undefined
      };
    });

    return {
      title,
      columns: [
        { key: 'id', label: 'ID' },
        { key: 'title', label: 'Titulo' },
        { key: 'client', label: 'Cliente' },
        { key: 'subtasks', label: 'Subtareas' },
        { key: 'status', label: 'Estado' },
        { key: 'assignedTo', label: 'Asignado' }
      ],
      items
    };
  }

  private buildUnassignedTableBlock(queue: readonly UnassignedSubtaskQueueItem[]): TasksTableData {
    const items: TaskListItem[] = queue.map((item) => ({
      id: item.subtask_id,
      title: item.subtask_title,
      client: item.client_name,
      completedSubtasks: 0,
      totalSubtasks: 1,
      status: formatTaskStatus(item.status),
      statusTone: toTaskTone(item.status),
      assignedToUserId: null,
      assignedTo: formatRoleKey(item.responsible_role_key),
      assignedInitials: buildInitials(formatRoleKey(item.responsible_role_key), 'RL'),
      routeTaskId: item.task_id,
      rowActionLabel: 'Tomar subtarea',
      rowActionId: item.subtask_id
    }));

    return {
      title: 'Subtareas sin asignar de mi rol',
      columns: [
        { key: 'id', label: 'Subtarea' },
        { key: 'title', label: 'Titulo' },
        { key: 'client', label: 'Cliente' },
        { key: 'subtasks', label: 'Progreso' },
        { key: 'status', label: 'Estado' },
        { key: 'assignedTo', label: 'Rol' }
      ],
      items
    };
  }

  private buildInitialListUiState(context: TaskListContextId): TaskListUiState {
    return {
      search: '',
      status: 'all',
      sortDirection: 'desc',
      viewMode: this.listingViewPreferenceService.getView(this.buildViewPreferenceKey(context), 'cards')
    };
  }

  private buildViewPreferenceKey(context: TaskListContextId): string {
    return `tasks.${context}`;
  }

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

  private loadHistoryTaskDetails(summaries: TaskSummary[]): void {
    if (!summaries.length) {
      this.historyTasks.set([]);
      return;
    }

    this.resolveTaskDetails(summaries, (ordered) => {
      this.historyTasks.set(ordered);
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