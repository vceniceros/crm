import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';

import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { UI_HELP_TEXTS } from '../../../../core/config/ui-help-texts.config';
import {
  buildInitials,
  countCompletedSubtasks,
  formatRoleKey,
  formatTaskStatus,
  TaskDetail,
  TaskSummary,
  toTaskTone,
  UnassignedSubtaskQueueItem
} from '../../../../core/models/task-management.model';
import { TaskListItem, TasksTableData } from '../../../../core/models/task.model';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { ListingViewMode, ListingViewPreferenceService } from '../../../../shared/services/listing-view-preference.service';
import { ListingControlsComponent, ListingSortDirection, ListingStatusOption } from '../../../../shared/ui/listing-controls/listing-controls.component';
import { ContextHelpCardComponent } from '../../../../shared/ui/context-help-card/context-help-card.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { CreateTaskDialogComponent } from '../create-task-dialog/create-task-dialog.component';
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
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    ContextHelpCardComponent,
    ListingControlsComponent,
    PageTitleComponent,
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
  private readonly dialog = inject(MatDialog);
  private readonly listingViewPreferenceService = inject(ListingViewPreferenceService);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly helpText = UI_HELP_TEXTS.tasks;

  readonly isLoading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly initialTabIndex = signal(0);
  readonly highlightedHistoryTaskId = signal<string | null>(null);
  readonly assignedTasks = signal<TaskDetail[]>([]);
  readonly unassignedSubtasks = signal<UnassignedSubtaskQueueItem[]>([]);
  readonly trackingTasks = signal<TaskDetail[]>([]);
  readonly historyTasks = signal<TaskDetail[]>([]);

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
  readonly assignedTableBlock = computed<TasksTableData>(() => this.buildTaskTableBlock('Pedidos asignados a mi', this.assignedVisibleTasks()));
  readonly trackingTableBlock = computed<TasksTableData>(() => this.buildTaskTableBlock('Seguimiento general', this.trackingVisibleTasks()));
  readonly historyTableBlock = computed<TasksTableData>(() => this.buildTaskTableBlock('Historial de pedidos', this.historyVisibleTasks()));
  readonly unassignedTableBlock = computed<TasksTableData>(() => this.buildUnassignedTableBlock(this.unassignedVisibleSubtasks()));
  readonly isHandset = toSignal(
    this.breakpointObserver.observe([Breakpoints.Handset]).pipe(map((state) => state.matches)),
    { initialValue: false }
  );

  constructor() {
    const queryParams = this.activatedRoute.snapshot.queryParams;
    const preselectedTemplateId = queryParams['templateId'];

    const highlightedTaskId = queryParams['taskId'];
    if (typeof highlightedTaskId === 'string' && highlightedTaskId.trim()) {
      this.highlightedHistoryTaskId.set(highlightedTaskId.trim());
    }

    if (this.router.url.startsWith('/tasks/history')) {
      this.initialTabIndex.set(3);
    }

    this.refresh();

    if (typeof preselectedTemplateId === 'string' && preselectedTemplateId.trim() && this.isAdminOrExecutive()) {
      this.openCreateTaskDialog(preselectedTemplateId.trim());
    }
  }

  refresh(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

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

  openCreateTaskDialog(preselectedTemplateId?: string): void {
    if (!this.isAdminOrExecutive()) {
      return;
    }

    this.dialog
      .open<CreateTaskDialogComponent, { templateId?: string }, TaskDetail>(CreateTaskDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '58rem',
        data: preselectedTemplateId ? { templateId: preselectedTemplateId } : undefined
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((task) => {
        if (task) {
          this.successMessage.set('El pedido se creó y quedó instanciado con el flujo real del template.');
          this.refresh();
          void this.router.navigate(['/tasks', task.task_id]);
        }
      });
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
          this.successMessage.set('El pedido se aprobó y se movió al historial de pedidos.');
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
          this.successMessage.set('El cierre fue rechazado y el pedido volvió al flujo operativo.');
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
        rowActionLabel: canApprove ? 'Aprobar pedido' : undefined,
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