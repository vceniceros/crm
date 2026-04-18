import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';

import {
  CreateTaskDispatchRequest,
  InventoryDispatchItem,
  InventoryRequest,
  InventoryRequestItemWriteRequest,
  RequiredMaterial
} from '../../../../core/models/inventory-flow.model';
import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { InventoryFlowService } from '../../../../core/services/inventory-flow.service';
import { InventoryService } from '../../../../core/services/inventory.service';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import {
  buildInitials,
  CrmUserOption,
  formatAssignmentPolicy,
  formatRoleKey,
  formatTaskStatus,
  Subtask,
  TaskAction,
  TaskComment,
  TaskDetail,
  TASK_ACTION_OPTIONS,
  toTaskTone
} from '../../../../core/models/task-management.model';
import { TaskAttachment } from '../../../../core/models/task-attachment.model';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { AppLocation } from '../../../../core/models/location.model';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';
import { TaskAttachmentsSectionComponent } from '../task-attachments-section/task-attachments-section.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-task-execution-page',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    LocationMapComponent,
    PageTitleComponent,
    ReactiveFormsModule,
    RouterLink,
    StatusBadgeComponent,
    TaskAttachmentsSectionComponent,
    UserAvatarComponent
  ],
  templateUrl: './task-execution-page.component.html',
  styleUrl: './task-execution-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TaskExecutionPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly formBuilder = inject(FormBuilder);
  private readonly inventoryFlowService = inject(InventoryFlowService);
  private readonly inventoryService = inject(InventoryService);
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly destroyRef = inject(DestroyRef);

  readonly task = signal<TaskDetail | null>(null);
  readonly isLoading = signal(true);
  readonly isSaving = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly inventoryProducts = signal<InventoryProduct[]>([]);
  readonly requestDraftItems = signal<Array<InventoryRequestItemWriteRequest & { product_name: string }>>([]);
  readonly dispatchDraftItems = signal<Array<CreateTaskDispatchRequest['items'][number] & { product_name: string; requires_tracking: boolean }>>([]);
  readonly selectedSubtaskId = signal<string | null>(null);
  readonly pendingAttachments = signal<TaskAttachment[]>([]);
  readonly nextAssigneeOptions = signal<CrmUserOption[]>([]);
  readonly actionOptions = TASK_ACTION_OPTIONS;
  readonly operationForm = this.formBuilder.group({
    items: this.formBuilder.array([]),
    comment: this.formBuilder.control('', { nonNullable: true, validators: [Validators.required] }),
    next_assigned_crm_user_id: this.formBuilder.control<string | null>(null)
  });
  readonly requestComposerForm = this.formBuilder.group({
    product_id: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    quantity_requested: this.formBuilder.control(1, { validators: [Validators.required, Validators.min(1)], nonNullable: true }),
    notes: this.formBuilder.control<string | null>(null),
    request_reason: this.formBuilder.control<string | null>(null)
  });
  readonly dispatchComposerForm = this.formBuilder.group({
    request_id: this.formBuilder.control<string | null>(null),
    product_id: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    quantity_dispatched: this.formBuilder.control(1, { validators: [Validators.required, Validators.min(1)], nonNullable: true }),
    serial_number: this.formBuilder.control<string | null>(null),
    barcode_value: this.formBuilder.control<string | null>(null),
    notes: this.formBuilder.control<string | null>(null),
    dispatch_notes: this.formBuilder.control<string | null>(null)
  });

  readonly currentUserId = computed(() => this.authSessionService.sessionSnapshot()?.user.crm_user_id ?? null);
  readonly currentRoles = computed(() => this.authSessionService.sessionSnapshot()?.user.role_keys ?? []);
  readonly isDeposito = computed(() => this.currentRoles().includes('deposito') || this.currentRoles().includes('admin'));
  readonly isTecnico = computed(() => this.currentRoles().includes('tecnico') || this.currentRoles().includes('admin'));
  readonly selectedSubtask = computed(() => {
    const currentTask = this.task();
    if (!currentTask) {
      return null;
    }
    const selected = this.selectedSubtaskId();
    return currentTask.subtasks.find((subtask) => subtask.subtask_id === selected) ?? null;
  });
  readonly selectedSubtaskComments = computed(() => {
    const currentTask = this.task();
    const subtaskId = this.selectedSubtaskId();
    if (!currentTask || !subtaskId) {
      return [] as TaskComment[];
    }

    return currentTask.comments.filter((comment) => comment.subtask_id === subtaskId);
  });
  readonly taskLocation = computed<AppLocation | null>(() => {
    const location = this.task()?.location;
    if (!location) {
      return null;
    }

    return {
      latitude: location.latitude,
      longitude: location.longitude,
      addressLabel: location.address_label?.trim() || location.formatted_address?.trim() || undefined
    };
  });
  readonly canOperateTask = computed(() => this.task()?.current_assigned_crm_user_id === this.currentUserId());

  constructor() {
    this.inventoryService.products$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((products) => {
      this.inventoryProducts.set(products);
    });
    this.inventoryService
      .refresh()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ error: () => undefined });

    const taskId = this.activatedRoute.snapshot.paramMap.get('taskId');
    if (!taskId) {
      this.errorMessage.set('No se indicó una tarea válida.');
      this.isLoading.set(false);
      return;
    }
    this.refresh(taskId);
  }

  get itemControls(): FormArray {
    return this.operationForm.controls.items;
  }

  get approvedRequests(): InventoryRequest[] {
    return (this.task()?.inventory_requests ?? []).filter((request) => request.request_status === 'APPROVED');
  }

  totalDispatchedFor(material: RequiredMaterial): number {
    return this.flattenDispatchItems()
      .filter((item) => item.product_id === material.product_id)
      .reduce((total, item) => total + item.quantity_dispatched, 0);
  }

  selectedRequestProduct(): InventoryProduct | null {
    return this.inventoryProducts().find((product) => product.productId === this.requestComposerForm.controls.product_id.getRawValue()) ?? null;
  }

  selectedDispatchProduct(): InventoryProduct | null {
    return this.inventoryProducts().find((product) => product.productId === this.dispatchComposerForm.controls.product_id.getRawValue()) ?? null;
  }

  addRequestDraftItem(): void {
    if (this.requestComposerForm.controls.product_id.invalid || this.requestComposerForm.controls.quantity_requested.invalid) {
      this.requestComposerForm.markAllAsTouched();
      return;
    }
    const product = this.selectedRequestProduct();
    if (!product) {
      return;
    }
    if (this.requestDraftItems().some((item) => item.product_id === product.productId)) {
      this.errorMessage.set('No podés repetir el mismo producto dentro de una misma solicitud adicional.');
      return;
    }
    this.requestDraftItems.update((current) => [
      ...current,
      {
        product_id: product.productId,
        quantity_requested: this.requestComposerForm.controls.quantity_requested.getRawValue(),
        notes: this.requestComposerForm.controls.notes.getRawValue()?.trim() || null,
        product_name: product.productName
      }
    ]);
    this.requestComposerForm.patchValue({ product_id: '', quantity_requested: 1, notes: null });
  }

  removeRequestDraftItem(productId: string): void {
    this.requestDraftItems.update((current) => current.filter((item) => item.product_id !== productId));
  }

  submitInventoryRequest(): void {
    const currentTask = this.task();
    if (!currentTask || !this.requestDraftItems().length) {
      return;
    }
    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.inventoryFlowService
      .createRequest({
        source_type: 'TASK',
        task_id: currentTask.task_id,
        request_reason: this.requestComposerForm.controls.request_reason.getRawValue()?.trim() || null,
        items: this.requestDraftItems().map(({ product_name: _productName, ...item }) => item)
      })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isSaving.set(false))
      )
      .subscribe({
        next: () => {
          this.requestDraftItems.set([]);
          this.requestComposerForm.reset({ product_id: '', quantity_requested: 1, notes: null, request_reason: null });
          this.reloadTask('La solicitud adicional quedó enviada a depósito.');
        },
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  addDispatchDraftItem(): void {
    if (this.dispatchComposerForm.controls.product_id.invalid || this.dispatchComposerForm.controls.quantity_dispatched.invalid) {
      this.dispatchComposerForm.markAllAsTouched();
      return;
    }
    const product = this.selectedDispatchProduct();
    if (!product) {
      return;
    }
    if (this.dispatchDraftItems().some((item) => item.product_id === product.productId)) {
      this.errorMessage.set('No podés repetir el mismo producto dentro del mismo despacho.');
      return;
    }
    this.dispatchDraftItems.update((current) => [
      ...current,
      {
        product_id: product.productId,
        quantity_dispatched: this.dispatchComposerForm.controls.quantity_dispatched.getRawValue(),
        serial_number: this.dispatchComposerForm.controls.serial_number.getRawValue()?.trim() || null,
        barcode_value: this.dispatchComposerForm.controls.barcode_value.getRawValue()?.trim() || null,
        notes: this.dispatchComposerForm.controls.notes.getRawValue()?.trim() || null,
        product_name: product.productName,
        requires_tracking: product.requiresTracking
      }
    ]);
    this.dispatchComposerForm.patchValue({ product_id: '', quantity_dispatched: 1, serial_number: null, barcode_value: null, notes: null });
  }

  removeDispatchDraftItem(productId: string): void {
    this.dispatchDraftItems.update((current) => current.filter((item) => item.product_id !== productId));
  }

  submitDispatch(): void {
    const currentTask = this.task();
    if (!currentTask || !this.dispatchDraftItems().length) {
      return;
    }
    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.inventoryFlowService
      .createTaskDispatch(currentTask.task_id, {
        request_id: this.dispatchComposerForm.controls.request_id.getRawValue()?.trim() || null,
        dispatch_notes: this.dispatchComposerForm.controls.dispatch_notes.getRawValue()?.trim() || null,
        items: this.dispatchDraftItems().map(({ product_name: _productName, requires_tracking: _requiresTracking, ...item }) => item)
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          this.dispatchDraftItems.set([]);
          this.dispatchComposerForm.reset({
            request_id: null,
            product_id: '',
            quantity_dispatched: 1,
            serial_number: null,
            barcode_value: null,
            notes: null,
            dispatch_notes: null
          });
          this.updateTask(task, 'El despacho quedó registrado y trazado contra el stock real.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  reviewInventoryRequest(requestId: string, status: 'APPROVED' | 'REJECTED'): void {
    this.isSaving.set(true);
    this.inventoryFlowService
      .reviewRequest(requestId, { status, review_notes: null })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isSaving.set(false))
      )
      .subscribe({
        next: () => this.reloadTask(status === 'APPROVED' ? 'La solicitud quedó aprobada.' : 'La solicitud quedó rechazada.'),
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  confirmDispatchItem(item: InventoryDispatchItem, confirmationType: 'received' | 'delivered' | 'installed'): void {
    this.isSaving.set(true);
    this.inventoryFlowService
      .confirmDispatchItem(item.inventory_dispatch_item_id, { confirmation_type: confirmationType })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          if ('task_id' in result) {
            this.updateTask(result, 'La confirmación técnica quedó persistida.');
            return;
          }
          this.reloadTask('La confirmación técnica quedó persistida.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  selectSubtask(subtaskId: string): void {
    this.clearPendingAttachments();
    this.selectedSubtaskId.set(subtaskId);
    this.rebuildOperationForm();
  }

  canClaimSubtask(subtask: Subtask): boolean {
    return subtask.status === 'pending_assignment';
  }

  canEditSubtask(subtask: Subtask): boolean {
    return subtask.assigned_crm_user_id === this.currentUserId();
  }

  claimSelectedSubtask(): void {
    const subtask = this.selectedSubtask();
    if (!subtask) {
      return;
    }

    this.isSaving.set(true);
    this.taskManagementService.claimSubtask(subtask.subtask_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (task) => this.updateTask(task, 'La subtarea fue tomada correctamente.'),
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isSaving.set(false);
      }
    });
  }

  saveProgress(): void {
    const subtask = this.selectedSubtask();
    if (!subtask) {
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.taskManagementService
      .saveSubtaskProgress(subtask.subtask_id, {
        items: this.itemControls.controls.map((control) => ({
          item_id: String(control.get('item_id')?.value ?? ''),
          checkbox_value: control.get('item_type')?.value === 'checkbox' ? Boolean(control.get('checkbox_value')?.value) : undefined,
          text_value: control.get('item_type')?.value === 'text' ? (String(control.get('text_value')?.value ?? '').trim() || null) : undefined
        }))
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => this.updateTask(task, 'El progreso de la subtarea se guardó correctamente.'),
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  executeAction(action: TaskAction): void {
    const subtask = this.selectedSubtask();
    if (!subtask) {
      return;
    }

    if (this.operationForm.controls.comment.invalid) {
      this.operationForm.controls.comment.markAsTouched();
      this.errorMessage.set('El comentario es obligatorio para ejecutar la acción final.');
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.taskManagementService
      .executeSubtaskAction(subtask.subtask_id, {
        action,
        comment: this.operationForm.controls.comment.getRawValue().trim(),
        next_assigned_crm_user_id: this.operationForm.controls.next_assigned_crm_user_id.getRawValue()?.trim() || null,
        attachment_ids: this.pendingAttachments().map((attachment) => attachment.id)
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => this.updateTask(task, 'La acción se ejecutó y el flujo quedó actualizado.'),
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  timelineTone(status: string) {
    return toTaskTone(status);
  }

  subtaskCanBeOperated(subtask: Subtask): boolean {
    return this.canEditSubtask(subtask) && ['assigned', 'in_progress'].includes(subtask.status);
  }

  isReadOnlySubtask(subtask: Subtask): boolean {
    return Boolean(subtask.assigned_crm_user_id) && subtask.assigned_crm_user_id !== this.currentUserId();
  }

  readOnlyMessage(subtask: Subtask): string {
    if (this.isReadOnlySubtask(subtask)) {
      return `Solo lectura. La subtarea está asignada a ${subtask.assigned_user_display_name ?? 'otro usuario'}.`;
    }

    if (!this.canOperateTask()) {
      return 'Solo lectura. La tarea está asignada a otro usuario.';
    }

    return 'Solo lectura.';
  }

  canManageDispatch(): boolean {
    return this.canOperateTask() && this.isDeposito();
  }

  canCreateInventoryRequest(): boolean {
    return this.canOperateTask() && this.isTecnico();
  }

  canConfirmDispatchItem(): boolean {
    return this.canOperateTask() && this.isTecnico();
  }

  selectedSubtaskAssignee(): string {
    return this.selectedSubtask()?.assigned_user_display_name ?? 'Sin usuario asignado';
  }

  requestOptionLabel(request: InventoryRequest): string {
    return request.request_reason?.trim() || 'Solicitud adicional aprobada';
  }

  requestCardTitle(request: InventoryRequest): string {
    return request.request_reason?.trim() || 'Solicitud adicional';
  }

  dispatchCardTitle(dispatch: { request_id: string | null }): string {
    return dispatch.request_id ? 'Despacho asociado a solicitud' : 'Despacho directo';
  }

  nextAssigneeLabel(option: CrmUserOption): string {
    return option.display_name?.trim() || option.email || 'Usuario CRM';
  }

  addAttachments(attachments: readonly TaskAttachment[]): void {
    this.pendingAttachments.update((current) => [...current, ...attachments]);
  }

  removeAttachment(attachmentId: string): void {
    this.taskManagementService
      .deleteTaskAttachment(attachmentId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.pendingAttachments.update((current) => current.filter((attachment) => attachment.id !== attachmentId));
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
        }
      });
  }

  readonly buildInitials = buildInitials;
  readonly formatRoleKey = formatRoleKey;
  readonly formatAssignmentPolicy = formatAssignmentPolicy;
  readonly formatTaskStatus = formatTaskStatus;
  readonly toTaskTone = toTaskTone;

  flattenDispatchItems(): InventoryDispatchItem[] {
    return this.task()?.dispatches.flatMap((dispatch) => dispatch.items) ?? [];
  }

  hasTaskLocation(): boolean {
    return this.locationLinkService.isValidLocation(this.taskLocation());
  }

  taskLocationLabel(): string {
    const location = this.taskLocation();
    if (!location) {
      return 'Sin ubicación específica';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  openTaskLocationInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.taskLocation());
  }

  private refresh(taskId: string): void {
    this.isLoading.set(true);
    this.taskManagementService.getTaskDetail(taskId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (task) => {
        this.task.set(task);
        this.selectedSubtaskId.set(task.current_subtask_id ?? task.subtasks[0]?.subtask_id ?? null);
        this.rebuildOperationForm();
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoading.set(false);
      }
    });
  }

  private reloadTask(message: string): void {
    const taskId = this.task()?.task_id;
    if (!taskId) {
      return;
    }
    this.taskManagementService.getTaskDetail(taskId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (task) => {
        this.task.set(task);
        this.successMessage.set(message);
        this.errorMessage.set(null);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
      }
    });
  }

  private rebuildOperationForm(): void {
    const subtask = this.selectedSubtask();
    this.itemControls.clear();
    if (!subtask) {
      return;
    }

    subtask.items
      .sort((left, right) => left.item_order - right.item_order)
      .forEach((item) => {
        this.itemControls.push(
          this.formBuilder.group({
            item_id: this.formBuilder.control(item.subtask_item_value_id, { nonNullable: true }),
            item_type: this.formBuilder.control(item.item_type, { nonNullable: true }),
            item_label: this.formBuilder.control(item.item_label, { nonNullable: true }),
            is_required: this.formBuilder.control(item.is_required, { nonNullable: true }),
            checkbox_value: this.formBuilder.control(item.checkbox_value, { nonNullable: true }),
            text_value: this.formBuilder.control(item.text_value ?? '', { nonNullable: true })
          })
        );
      });

    this.operationForm.controls.comment.setValue('');
    this.operationForm.controls.next_assigned_crm_user_id.setValue(null);
    this.loadNextAssigneeOptions(subtask);
  }

  private updateTask(task: TaskDetail, message: string): void {
    this.task.set(task);
    this.selectedSubtaskId.set(task.current_subtask_id ?? this.selectedSubtaskId());
    this.pendingAttachments.set([]);
    this.rebuildOperationForm();
    this.successMessage.set(message);
    this.errorMessage.set(null);
    this.isSaving.set(false);
  }

  private clearPendingAttachments(): void {
    const attachments = this.pendingAttachments();
    if (!attachments.length) {
      return;
    }

    this.pendingAttachments.set([]);
    attachments.forEach((attachment) => {
      this.taskManagementService.deleteTaskAttachment(attachment.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        error: () => undefined
      });
    });
  }

  private loadNextAssigneeOptions(subtask: Subtask): void {
    const nextSubtask = this.task()?.subtasks.find((candidate) => candidate.order_index === subtask.order_index + 1) ?? null;
    if (subtask.next_assignment_policy !== 'manual_required' || !nextSubtask?.responsible_role_key) {
      this.nextAssigneeOptions.set([]);
      return;
    }

    this.taskManagementService.listCrmUsersByRole(nextSubtask.responsible_role_key).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (options) => this.nextAssigneeOptions.set(options),
      error: () => this.nextAssigneeOptions.set([])
    });
  }
}