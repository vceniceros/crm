import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, forkJoin, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule, MatMenuTrigger } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import {
  InventoryDispatchItemWriteRequest,
  InventoryDispatchItem,
  formatInventoryRequestStatus,
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
  TaskPreFormStatusValue,
  formatTaskStatus,
  Subtask,
  TaskAction,
  TaskComment,
  TaskDetail,
  TaskPreFormStatusResponse,
  TaskSatisfactionFormStatusResponse,
  TASK_ACTION_OPTIONS,
  toTaskTone
} from '../../../../core/models/task-management.model';
import { TaskAttachment } from '../../../../core/models/task-attachment.model';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { AppLocation } from '../../../../core/models/location.model';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';
import { TaskAttachmentsSectionComponent } from '../task-attachments-section/task-attachments-section.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';

type DispatchIdentifierType = 'none' | 'serial' | 'barcode';
type TaskCommentPrimaryAction = 'comment' | TaskAction;
type TaskExecutionSectionId =
  | 'subtasks_flow'
  | 'required_materials'
  | 'dispatches'
  | 'requests'
  | 'subtask_operation'
  | 'subtask_transitions'
  | 'subtask_comments';

type DispatchDraftItem = InventoryDispatchItemWriteRequest & {
  draft_id: string;
  product_name: string;
  requires_tracking: boolean;
  identifier_type: DispatchIdentifierType;
  identifier_value: string | null;
};

@Component({
  selector: 'app-task-execution-page',
  standalone: true,
  imports: [
    DatePipe,
    NgTemplateOutlet,
    MatButtonModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
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
  private readonly router = inject(Router);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  readonly task = signal<TaskDetail | null>(null);
  readonly pageError = signal<string | null>(null);
  readonly isLoading = signal(true);
  readonly isSaving = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly inventoryProducts = signal<InventoryProduct[]>([]);
  readonly requestDraftItems = signal<Array<InventoryRequestItemWriteRequest & { product_name: string }>>([]);
  readonly dispatchDraftItems = signal<DispatchDraftItem[]>([]);
  readonly selectedSubtaskId = signal<string | null>(null);
  readonly pendingAttachments = signal<TaskAttachment[]>([]);
  readonly nextAssigneeOptions = signal<CrmUserOption[]>([]);
  readonly subtaskAssigneeOptions = signal<CrmUserOption[]>([]);
  readonly taskSatisfactionStatus = signal<TaskSatisfactionFormStatusResponse | null>(null);
  readonly taskPreFormStatus = signal<TaskPreFormStatusResponse | null>(null);
  readonly isPreFormResponseVisible = signal(false);
  readonly isAndroidCompact = signal(this.detectAndroidCompactLayout());
  readonly nonSubtaskSectionsExpanded = signal(!this.detectAndroidCompactLayout());
  readonly sectionCollapseState = signal<Record<TaskExecutionSectionId, boolean>>({
    subtasks_flow: false,
    required_materials: false,
    dispatches: false,
    requests: false,
    subtask_operation: false,
    subtask_transitions: false,
    subtask_comments: false,
  });
  readonly selectedPrimaryCommentAction = signal<TaskCommentPrimaryAction>('comment');
  readonly selectedCommentLocation = signal<AppLocation | null>(null);
  readonly actionOptions = TASK_ACTION_OPTIONS;
  readonly operationForm = this.formBuilder.group({
    items: this.formBuilder.array([]),
    comment: this.formBuilder.control('', { nonNullable: true, validators: [Validators.required] }),
    next_assigned_crm_user_id: this.formBuilder.control<string | null>(null)
  });
  readonly adminAssignmentForm = this.formBuilder.group({
    assigned_crm_user_id: this.formBuilder.control<string | null>(null, { validators: [Validators.required] }),
    notes: this.formBuilder.control<string | null>(null)
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
    identifier_type: this.formBuilder.control<DispatchIdentifierType>('none', { nonNullable: true }),
    identifier_value: this.formBuilder.control<string | null>(null),
    notes: this.formBuilder.control<string | null>(null),
    dispatch_notes: this.formBuilder.control<string | null>(null)
  });
  readonly rejectTaskApprovalForm = this.formBuilder.group({
    comment: this.formBuilder.control('', { nonNullable: true, validators: [Validators.required] })
  });

  readonly currentUserId = computed(() => this.authSessionService.sessionSnapshot()?.user.crm_user_id ?? null);
  readonly currentRoles = computed(() => this.authSessionService.sessionSnapshot()?.user.role_keys ?? []);
  readonly isAdmin = computed(() => this.currentRoles().includes('admin'));
  readonly isExecutive = computed(() => this.currentRoles().includes('ejecutivo'));
  readonly isDeposito = computed(() => this.currentRoles().includes('deposito'));
  readonly isTecnico = computed(() => this.currentRoles().includes('tecnico'));
  readonly isFieldTechnician = computed(() => this.isTecnico() && !this.isAdmin() && !this.isExecutive() && !this.isDeposito());
  readonly hasSubmittedPreForm = computed(() => Boolean(this.taskPreFormStatus()?.submitted_at));
  readonly canViewDispatchSection = computed(() => this.isDeposito() || this.isAdmin());
  readonly canViewRequestsSection = computed(() => this.isTecnico() || this.isAdmin());
  readonly currentAssignableSubtask = computed(() => {
    const currentTask = this.task();
    if (!currentTask?.current_subtask_id) {
      return null;
    }

    return currentTask.subtasks.find((subtask) => subtask.subtask_id === currentTask.current_subtask_id) ?? null;
  });
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
  readonly selectedSubtaskAttachments = computed<readonly TaskAttachment[]>(() => {
    const comments = this.selectedSubtaskComments();
    if (!comments.length) {
      return [];
    }

    const deduplicatedAttachments = new Map<string, TaskAttachment>();
    comments.forEach((comment) => {
      comment.attachments.forEach((attachment) => {
        deduplicatedAttachments.set(attachment.id, attachment);
      });
    });

    return Array.from(deduplicatedAttachments.values());
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
  readonly canManageTaskLinks = computed(() => this.isAdmin() || this.isExecutive());
  readonly isSelectedSubtaskFinal = computed(() => {
    const subtask = this.selectedSubtask();
    const allSubtasks = this.task()?.subtasks ?? [];
    if (!subtask || !allSubtasks.length) {
      return false;
    }

    const maxOrder = Math.max(...allSubtasks.map((item) => item.order_index));
    return subtask.order_index === maxOrder;
  });
  readonly requiresArrivalRegistration = computed(() => {
    const currentTask = this.task();
    return Boolean(currentTask?.requires_arrival_comment && !currentTask.arrival_registered_at);
  });
  readonly requiresVideoEvidenceForCurrentClose = computed(() => {
    const currentTask = this.task();
    return Boolean(currentTask?.requires_video_evidence && this.isSelectedSubtaskFinal());
  });
  readonly isCloseBlockedByVideoRequirement = computed(() => {
    return this.requiresVideoEvidenceForCurrentClose() && !this.pendingAttachments().some((attachment) => attachment.kind === 'video');
  });

  constructor() {
    if (typeof globalThis.addEventListener === 'function') {
      const resizeListener = () => {
        const compactLayout = this.detectAndroidCompactLayout();
        if (compactLayout !== this.isAndroidCompact()) {
          this.isAndroidCompact.set(compactLayout);
          this.nonSubtaskSectionsExpanded.set(!compactLayout);
        }
      };
      globalThis.addEventListener('resize', resizeListener);
      this.destroyRef.onDestroy(() => {
        globalThis.removeEventListener('resize', resizeListener);
      });
    }

    this.inventoryService.products$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((products) => {
      this.inventoryProducts.set(products);
    });
    this.inventoryService
      .refresh()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ error: () => undefined });

    const taskId = this.activatedRoute.snapshot.paramMap.get('taskId');
    if (!taskId) {
      this.pageError.set('No se indicó una tarea válida.');
      this.isLoading.set(false);
      return;
    }
    this.refresh(taskId);
  }

  get itemControls(): FormArray {
    return this.operationForm.controls.items;
  }

  get approvedRequests(): InventoryRequest[] {
    return (this.task()?.inventory_requests ?? []).filter((request) => ['APPROVED', 'PENDING_DISPATCH'].includes(request.request_status));
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
        error: (error: Error) => this.showOperationError(error.message)
      });
  }

  addDispatchDraftItem(): void {
    if (this.dispatchComposerForm.controls.product_id.invalid) {
      this.dispatchComposerForm.markAllAsTouched();
      return;
    }
    const product = this.selectedDispatchProduct();
    if (!product) {
      return;
    }
    const identifierType = this.dispatchComposerForm.controls.identifier_type.getRawValue();
    const identifierValue = this.dispatchComposerForm.controls.identifier_value.getRawValue()?.trim() || null;
    if (product.requiresTracking) {
      if (identifierType === 'none' || !identifierValue) {
        this.showOperationError('Para productos con tracking unitario debés elegir Serial o Código de barras y cargar su valor.');
        return;
      }
    }
    if ((identifierType === 'serial' || identifierType === 'barcode') && !identifierValue) {
      this.showOperationError('Completá el valor del identificador seleccionado.');
      return;
    }

    const serialNumber = identifierType === 'serial' ? identifierValue : null;
    const barcodeValue = identifierType === 'barcode' ? identifierValue : null;
    if (product.requiresTracking) {
      const duplicateTrackedItem = this.dispatchDraftItems().some(
        (item) =>
          item.product_id === product.productId &&
          ((serialNumber && item.serial_number === serialNumber) || (barcodeValue && item.barcode_value === barcodeValue))
      );
      if (duplicateTrackedItem) {
        this.showOperationError('Ese identificador ya fue agregado para este producto en el despacho actual.');
        return;
      }
    }

    this.dispatchDraftItems.update((current) => [
      ...current,
      {
        draft_id: this.createDraftItemId(),
        product_id: product.productId,
        quantity_dispatched: 1,
        serial_number: serialNumber,
        barcode_value: barcodeValue,
        identifier_type: identifierType,
        identifier_value: identifierValue,
        notes: this.dispatchComposerForm.controls.notes.getRawValue()?.trim() || null,
        product_name: product.productName,
        requires_tracking: product.requiresTracking
      }
    ]);
    this.errorMessage.set(null);
    this.dispatchComposerForm.patchValue({ product_id: '', identifier_type: 'none', identifier_value: null, notes: null });
  }

  removeDispatchDraftItem(draftId: string): void {
    this.dispatchDraftItems.update((current) => current.filter((item) => item.draft_id !== draftId));
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
        items: this.dispatchDraftItems().map(
          ({ draft_id: _draftId, product_name: _productName, requires_tracking: _requiresTracking, identifier_type: _identifierType, identifier_value: _identifierValue, ...item }) => item
        )
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          this.dispatchDraftItems.set([]);
          this.dispatchComposerForm.reset({
            request_id: null,
            product_id: '',
            identifier_type: 'none',
            identifier_value: null,
            notes: null,
            dispatch_notes: null
          });
          this.task.set(task);
          this.reloadTask('El despacho quedó registrado y trazado contra el stock real.');
        },
        error: (error: Error) => {
          this.showOperationError(error.message);
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
        next: () => this.reloadTask(status === 'APPROVED' ? 'La solicitud quedó en pendiente de despacho.' : 'La solicitud quedó rechazada.'),
        error: (error: Error) => this.showOperationError(error.message)
      });
  }

  prepareDispatchForRequest(request: InventoryRequest): void {
    if (!this.canDispatchRequestedMaterial(request)) {
      return;
    }

    this.dispatchComposerForm.controls.request_id.setValue(request.inventory_request_id);
    this.successMessage.set('Solicitud seleccionada para despacho. Cargá los items y confirmá el despacho.');
    this.errorMessage.set(null);
  }

  canDispatchRequestedMaterial(request: InventoryRequest): boolean {
    return this.canManageDispatch() && ['APPROVED', 'PENDING_DISPATCH'].includes(request.request_status);
  }

  canConfirmRequestReceipt(request: InventoryRequest): boolean {
    const actorId = this.currentUserId();
    if (!actorId || request.request_status !== 'PENDING_RECEIPT') {
      return false;
    }

    const canConfirm = this.isAdmin() || request.requested_by_crm_user_id === actorId;
    return canConfirm && this.pendingRequestReceiptItems(request).length > 0;
  }

  confirmRequestReceipt(request: InventoryRequest): void {
    const pendingItems = this.pendingRequestReceiptItems(request);
    if (!pendingItems.length || !this.canConfirmRequestReceipt(request)) {
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    forkJoin(
      pendingItems.map((item) =>
        this.inventoryFlowService.confirmDispatchItem(item.inventory_dispatch_item_id, {
          confirmation_type: 'received'
        })
      )
    )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.reloadTask('Recibimiento confirmado. Ya podés continuar con la tarea.'),
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
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
          this.showOperationError(error.message);
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

  canAdminAssignSubtask(subtask: Subtask): boolean {
    if (!['pending_assignment', 'assigned', 'in_progress'].includes(subtask.status)) {
      return false;
    }

    if (this.isAdmin() || this.isExecutive()) {
      return true;
    }

    return this.currentRoles().includes(subtask.responsible_role_key);
  }

  adminAssignActionLabel(subtask: Subtask): string {
    return subtask.assigned_crm_user_id ? 'Reasignar subtarea' : 'Asignar subtarea';
  }

  canOpenHeaderAssigneeMenu(): boolean {
    const subtask = this.currentAssignableSubtask();
    return Boolean(subtask && this.canAdminAssignSubtask(subtask));
  }

  prepareHeaderAssigneeMenu(): void {
    const subtask = this.currentAssignableSubtask();
    if (!subtask || !this.canAdminAssignSubtask(subtask)) {
      this.subtaskAssigneeOptions.set([]);
      this.adminAssignmentForm.reset({ assigned_crm_user_id: null, notes: null });
      return;
    }

    this.adminAssignmentForm.reset({
      assigned_crm_user_id: subtask.assigned_crm_user_id,
      notes: null
    });
    this.loadSubtaskAssigneeOptions(subtask);
  }

  assignFromHeaderAssigneeMenu(menuTrigger: MatMenuTrigger): void {
    const subtask = this.currentAssignableSubtask();
    if (!subtask || !this.canAdminAssignSubtask(subtask)) {
      return;
    }

    if (this.adminAssignmentForm.invalid) {
      this.adminAssignmentForm.markAllAsTouched();
      return;
    }

    const assignedCrmUserId = this.adminAssignmentForm.controls.assigned_crm_user_id.getRawValue()?.trim() || null;
    if (!assignedCrmUserId) {
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.taskManagementService
      .assignSubtask(subtask.subtask_id, {
        assigned_crm_user_id: assignedCrmUserId,
        notes: this.adminAssignmentForm.controls.notes.getRawValue()?.trim() || null
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          this.updateTask(task, 'La asignación manual quedó guardada correctamente.');
          menuTrigger.closeMenu();
        },
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
      });
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
        this.showOperationError(error.message);
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
        items: this.buildSubtaskProgressItemsPayload()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => this.updateTask(task, 'El progreso de la subtarea se guardó correctamente.'),
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
      });
  }

  saveProgressSilently(): void {
    const subtask = this.selectedSubtask();
    if (!subtask || !this.subtaskCanBeOperated(subtask) || this.isSaving()) {
      return;
    }

    const currentComment = this.operationForm.controls.comment.getRawValue();
    const currentNextAssignee = this.operationForm.controls.next_assigned_crm_user_id.getRawValue();

    this.isSaving.set(true);
    this.taskManagementService
      .saveSubtaskProgress(subtask.subtask_id, {
        items: this.buildSubtaskProgressItemsPayload()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          this.task.set(task);
          this.selectedSubtaskId.set(task.current_subtask_id ?? this.selectedSubtaskId());
          this.rebuildOperationForm();
          this.operationForm.controls.comment.setValue(currentComment);
          this.operationForm.controls.next_assigned_crm_user_id.setValue(currentNextAssignee);
          this.errorMessage.set(null);
          this.isSaving.set(false);
        },
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
      });
  }

  hasPendingRequiredItems(): boolean {
    const subtask = this.selectedSubtask();
    if (!subtask) {
      return false;
    }

    return subtask.items.some((item) => {
      if (!item.is_required) {
        return false;
      }

      const itemType = String(item.item_type ?? '').toLowerCase();
      if (itemType === 'checkbox') {
        return !Boolean(item.checkbox_value);
      }

      return !String(item.text_value ?? '').trim();
    });
  }

  canExecuteFinalAction(subtask: Subtask): boolean {
    return this.subtaskCanBeOperated(subtask) && !this.isSaving() && this.operationForm.controls.comment.valid && !this.hasBlockingInventoryRequestsForCurrentUser();
  }

  executeAction(action: TaskAction): void {
    const subtask = this.selectedSubtask();
    if (!subtask) {
      return;
    }

    if (this.operationForm.controls.comment.invalid) {
      this.operationForm.controls.comment.markAsTouched();
      this.showOperationError('El comentario es obligatorio para ejecutar la acción final.');
      return;
    }

    if (this.hasBlockingInventoryRequestsForCurrentUser()) {
      this.showOperationError(this.blockingInventoryRequestMessage());
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.taskManagementService
      .saveSubtaskProgress(subtask.subtask_id, {
        items: this.buildSubtaskProgressItemsPayload()
      })
      .pipe(
        switchMap(() =>
          this.taskManagementService.executeSubtaskAction(subtask.subtask_id, {
            action,
            comment: this.operationForm.controls.comment.getRawValue().trim(),
            next_assigned_crm_user_id: this.operationForm.controls.next_assigned_crm_user_id.getRawValue()?.trim() || null,
            attachment_ids: this.pendingAttachments().map((attachment) => attachment.id)
          })
        ),
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          if (action === 'close_subtask') {
            this.handleSubtaskClosed(task);
            return;
          }
          this.updateTask(task, 'La acción se ejecutó y el flujo quedó actualizado.');
        },
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
      });
  }

  onChecklistCheckboxChanged(itemIndex: number, event: Event): void {
    const target = event.target as HTMLInputElement | null;
    const control = this.itemControls.at(itemIndex)?.get('checkbox_value');
    if (!target || !control) {
      return;
    }

    control.setValue(Boolean(target.checked));
    control.markAsDirty();
  }

  onChecklistTextChanged(itemIndex: number, event: Event): void {
    const target = event.target as HTMLTextAreaElement | null;
    const control = this.itemControls.at(itemIndex)?.get('text_value');
    if (!target || !control) {
      return;
    }

    control.setValue(target.value);
    control.markAsDirty();
  }

  timelineTone(status: string) {
    return toTaskTone(status);
  }

  taskExecutionStatusLabel(task: TaskDetail): string {
    if (this.isPendingExecutiveApproval(task)) {
      return 'Pendiente de aprobacion ejecutiva';
    }

    return formatTaskStatus(task.status);
  }

  canApproveCurrentTask(): boolean {
    const currentTask = this.task();
    if (!currentTask) {
      return false;
    }

    return (this.isAdmin() || this.isExecutive()) && this.isPendingExecutiveApproval(currentTask);
  }

  approveCurrentTask(): void {
    const currentTask = this.task();
    if (!currentTask || !this.canApproveCurrentTask()) {
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.taskManagementService
      .approveTask(currentTask.task_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (approvedTask) => {
          this.task.set(approvedTask);
          this.pendingAttachments.set([]);
          this.rejectTaskApprovalForm.reset({ comment: '' });
          this.errorMessage.set(null);
          this.successMessage.set(`Tarea cerrada exitosamente. Archivada en historial con ID: ${approvedTask.task_id}.`);
          this.isSaving.set(false);

          this.snackBar.open(
            `Tarea cerrada exitosamente. Archivada en historial con ID: ${approvedTask.task_id}.`,
            'Cerrar',
            { duration: 6500 }
          );
          void this.router.navigate(['/tasks/history'], { queryParams: { taskId: approvedTask.task_id } });
        },
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
      });
  }

  rejectCurrentTaskApproval(): void {
    const currentTask = this.task();
    if (!currentTask || !this.canApproveCurrentTask()) {
      return;
    }

    const comment = this.rejectTaskApprovalForm.controls.comment.getRawValue().trim();
    if (!comment) {
      this.rejectTaskApprovalForm.markAllAsTouched();
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.taskManagementService
      .rejectTaskApproval(currentTask.task_id, { comment })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (rejectedTask) => {
          this.task.set(rejectedTask);
          this.rejectTaskApprovalForm.reset({ comment: '' });
          this.pendingAttachments.set([]);
          this.errorMessage.set(null);
          this.successMessage.set('El cierre fue rechazado. La tarea volvió al flujo operativo y el comentario quedó trazado.');
          this.isSaving.set(false);
        },
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
      });
  }

  exportCurrentTask(): void {
    const currentTask = this.task();
    if (!currentTask || !this.canManageTaskLinks()) {
      return;
    }

    this.taskManagementService.exportTaskHistory(currentTask.task_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (blob) => {
        const objectUrl = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = objectUrl;
        anchor.download = `pedido_${currentTask.task_id}.zip`;
        anchor.click();
        URL.revokeObjectURL(objectUrl);
        this.snackBar.open('Exportación de pedido generada.', 'Cerrar', { duration: 3000 });
      },
      error: (error: Error) => this.showOperationError(error.message),
    });
  }

  generateTaskSatisfactionLink(): void {
    const currentTask = this.task();
    if (!currentTask || !this.canManageTaskLinks()) {
      return;
    }

    this.taskManagementService.generateTaskSatisfactionForm(currentTask.task_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: async (response) => {
        const absoluteLink = `${window.location.origin}${response.survey_path}`;
        try {
          await navigator.clipboard.writeText(absoluteLink);
          this.snackBar.open('Link de encuesta copiado al portapapeles.', 'Cerrar', { duration: 3500 });
        } catch {
          window.prompt('Link de encuesta generado. Copialo:', absoluteLink);
        }
        this.loadTaskSatisfactionStatus(currentTask.task_id);
      },
      error: (error: Error) => this.showOperationError(error.message),
    });
  }

  generateTaskPreFormLink(): void {
    const currentTask = this.task();
    if (!currentTask || !this.canManageTaskLinks()) {
      return;
    }

    this.taskManagementService.generateTaskPreFormLink(currentTask.task_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: async (response) => {
        const relativePath = response.form_link_path ?? '';
        const absoluteLink = `${window.location.origin}${relativePath}`;
        try {
          await navigator.clipboard.writeText(absoluteLink);
          this.snackBar.open('Link de formulario previo copiado al portapapeles.', 'Cerrar', { duration: 3500 });
        } catch {
          window.prompt('Link de formulario previo generado. Copialo:', absoluteLink);
        }
        this.isPreFormResponseVisible.set(false);
        this.loadTaskPreFormStatus(currentTask.task_id);
      },
      error: (error: Error) => this.showOperationError(error.message),
    });
  }

  resendTaskPreFormLink(): void {
    this.generateTaskPreFormLink();
  }

  toggleTaskPreFormView(): void {
    const status = this.taskPreFormStatus();
    if (!status?.submitted_at) {
      this.snackBar.open('Todavía no hay respuestas enviadas del formulario previo.', 'Cerrar', { duration: 3000 });
      return;
    }

    this.isPreFormResponseVisible.update((visible) => !visible);
  }

  preFormFieldValueLabel(value: TaskPreFormStatusValue): string {
    const fieldType = String(value.field_type ?? '').trim().toUpperCase();
    const rawValue = (value.text_value ?? '').trim();

    if (fieldType === 'CHECKBOX') {
      const normalized = rawValue.toLowerCase();
      if (['true', '1', 'si', 'sí', 'yes', 'on'].includes(normalized)) {
        return 'Sí';
      }
      if (['false', '0', 'no', 'off'].includes(normalized)) {
        return 'No';
      }
    }

    if (rawValue) {
      return rawValue;
    }

    if (value.file_attachment_id) {
      return `Adjunto ${value.file_attachment_id}`;
    }

    return 'Sin respuesta';
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
    return this.isDeposito() || this.isAdmin();
  }

  canCreateInventoryRequest(): boolean {
    return this.canOperateTask() && (this.isTecnico() || this.isAdmin());
  }

  canConfirmDispatchItem(): boolean {
    return this.canOperateTask() && (this.isTecnico() || this.isAdmin());
  }

  selectedSubtaskAssignee(): string {
    const subtask = this.selectedSubtask();
    if (!subtask) {
      return 'Sin usuario asignado';
    }

    return subtask.assigned_user_display_name ?? subtask.default_assigned_user_display_name ?? 'Sin usuario asignado';
  }

  requestOptionLabel(request: InventoryRequest): string {
    return request.request_reason?.trim() || 'Solicitud adicional aprobada';
  }

  requestCardTitle(request: InventoryRequest): string {
    return request.request_reason?.trim() || 'Solicitud adicional';
  }

  blockingInventoryRequestMessage(): string {
    const blockingRequest = this.blockingRequestsForCurrentUser()[0];
    if (!blockingRequest) {
      return 'No podés cerrar la subtarea mientras exista una solicitud adicional pendiente.';
    }

    if (blockingRequest.request_status === 'PENDING') {
      return 'No podés cerrar la subtarea porque hay una solicitud de materiales pendiente de aprobación por depósito.';
    }
    if (blockingRequest.request_status === 'PENDING_DISPATCH' || blockingRequest.request_status === 'APPROVED') {
      return 'No podés cerrar la subtarea porque hay una solicitud de materiales pendiente de despacho.';
    }
    return 'No podés cerrar la subtarea porque falta confirmar el recibimiento de materiales solicitados.';
  }

  hasBlockingInventoryRequests(): boolean {
    return this.hasBlockingInventoryRequestsForCurrentUser();
  }

  dispatchCardTitle(dispatch: { request_id: string | null }): string {
    return dispatch.request_id ? 'Despacho asociado a solicitud' : 'Despacho directo';
  }

  dispatchDraftTrackingLabel(item: {
    requires_tracking: boolean;
    identifier_type: DispatchIdentifierType;
    identifier_value: string | null;
    serial_number?: string | null;
    barcode_value?: string | null;
  }): string {
    const identifierText = item.identifier_value || item.serial_number || item.barcode_value || null;
    if (!identifierText) {
      return item.requires_tracking ? 'Falta identificador' : 'Sin serial/barcode';
    }

    if (item.identifier_type === 'none') {
      return identifierText;
    }

    return `${this.identifierTypeLabel(item.identifier_type)}: ${identifierText}`;
  }

  identifierTypeLabel(type: DispatchIdentifierType): string {
    if (type === 'serial') {
      return 'Serial';
    }
    if (type === 'barcode') {
      return 'Codigo de barras';
    }
    return 'Sin identificador';
  }

  onDispatchProductChanged(): void {
    const product = this.selectedDispatchProduct();
    if (!product) {
      return;
    }

    this.dispatchComposerForm.controls.identifier_type.setValue(product.requiresTracking ? 'serial' : 'none');
    this.dispatchComposerForm.controls.identifier_value.setValue(null);
  }

  nextAssigneeLabel(option: CrmUserOption): string {
    return option.display_name?.trim() || option.email || 'Usuario CRM';
  }

  shouldCollapseNonSubtaskSections(): boolean {
    return this.isAndroidCompact();
  }

  onNonSubtaskSectionsToggled(isOpen: boolean): void {
    this.nonSubtaskSectionsExpanded.set(isOpen);
  }

  addAttachments(attachments: readonly TaskAttachment[]): void {
    this.pendingAttachments.update((current) => [...current, ...attachments]);
  }

  selectPrimaryCommentAction(action: TaskCommentPrimaryAction): void {
    this.selectedPrimaryCommentAction.set(action);
  }

  primaryCommentActionLabel(): string {
    const action = this.selectedPrimaryCommentAction();
    if (action === 'comment') {
      return 'Publicar comentario';
    }

    return this.actionOptions.find((option) => option.value === action)?.label ?? 'Ejecutar acción';
  }

  commentFieldLabel(): string {
    const action = this.selectedPrimaryCommentAction();
    if (action === 'comment') {
      return 'Comentario operativo';
    }
    if (action === 'close_subtask') {
      return 'Comentario obligatorio de cierre';
    }

    return 'Comentario de acción';
  }

  commentFieldPlaceholder(): string {
    const action = this.selectedPrimaryCommentAction();
    if (action === 'comment') {
      return 'Describe diagnóstico, avance, llegada o bloqueo';
    }
    if (action === 'close_subtask') {
      return 'Describe validación y evidencia del cierre';
    }

    return 'Describe el motivo de esta acción';
  }

  canExecutePrimaryCommentAction(subtask: Subtask): boolean {
    if (this.isSaving() || !this.subtaskCanBeOperated(subtask)) {
      return false;
    }

    if (!this.operationForm.controls.comment.valid) {
      return false;
    }

    const action = this.selectedPrimaryCommentAction();
    if (action === 'comment') {
      if (this.requiresArrivalRegistration()) {
        const hasLocation = this.locationLinkService.isValidLocation(this.selectedCommentLocation());
        return hasLocation && this.pendingAttachments().length > 0;
      }
      return true;
    }

    if (action === 'close_subtask' && this.isCloseBlockedByVideoRequirement()) {
      return false;
    }

    return this.canExecuteFinalAction(subtask);
  }

  executePrimaryCommentAction(subtask: Subtask): void {
    const action = this.selectedPrimaryCommentAction();
    if (action === 'comment') {
      this.submitTaskComment();
      return;
    }

    this.executeAction(action);
  }

  openCommentLocationPicker(): void {
    this.locationPickerService
      .open({
        title: 'Ubicación del comentario operativo',
        initialLocation: this.selectedCommentLocation() ?? this.taskLocation()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result) => {
        if (!result) {
          return;
        }

        this.selectedCommentLocation.set(result.location);
      });
  }

  useTaskLocationForComment(): void {
    this.selectedCommentLocation.set(this.taskLocation());
  }

  clearCommentLocation(): void {
    this.selectedCommentLocation.set(null);
  }

  selectedCommentLocationLabel(): string {
    const location = this.selectedCommentLocation();
    if (!location) {
      return 'Sin ubicación para comentario';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  canOpenCommentLocationInMaps(): boolean {
    return this.locationLinkService.isValidLocation(this.selectedCommentLocation());
  }

  openCommentLocationInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.selectedCommentLocation());
  }

  isSectionCollapsed(section: TaskExecutionSectionId): boolean {
    return this.sectionCollapseState()[section];
  }

  toggleSection(section: TaskExecutionSectionId): void {
    this.sectionCollapseState.update((state) => ({
      ...state,
      [section]: !state[section],
    }));
  }

  submitTaskComment(): void {
    const currentTask = this.task();
    const subtask = this.selectedSubtask();
    if (!currentTask || !subtask || !this.subtaskCanBeOperated(subtask) || this.isSaving()) {
      return;
    }

    const body = this.operationForm.controls.comment.getRawValue().trim();
    if (!body) {
      this.operationForm.controls.comment.markAsTouched();
      this.showOperationError('Escribí un comentario antes de publicarlo.');
      return;
    }

    const selectedLocation = this.selectedCommentLocation();
    const hasSelectedLocation = this.locationLinkService.isValidLocation(selectedLocation);

    if (this.requiresArrivalRegistration()) {
      if (!hasSelectedLocation) {
        this.showOperationError('Para registrar llegada, seleccioná una ubicación del comentario.');
        return;
      }
      if (!this.pendingAttachments().length) {
        this.showOperationError('Para registrar llegada, agregá al menos un adjunto (foto o video).');
        return;
      }
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    if (hasSelectedLocation) {
      this.taskManagementService
        .createLocation(selectedLocation as AppLocation)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (location) => {
            this.submitTaskCommentWithLocationId(currentTask.task_id, body, location.locationId);
          },
          error: (error: Error) => {
            this.showOperationError(error.message);
            this.isSaving.set(false);
          }
        });
      return;
    }

    this.submitTaskCommentWithLocationId(currentTask.task_id, body, null);
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
          this.showOperationError(error.message);
        }
      });
  }

  readonly buildInitials = buildInitials;
  readonly formatInventoryRequestStatus = formatInventoryRequestStatus;
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

  private hasBlockingInventoryRequestsForCurrentUser(): boolean {
    return this.blockingRequestsForCurrentUser().length > 0;
  }

  private isPendingExecutiveApproval(task: TaskDetail): boolean {
    const allSubtasksCompleted = task.subtasks.every((subtask) => String(subtask.status).trim().toUpperCase() === 'COMPLETED');
    return task.status === 'BLOCKED' && !task.finalized_at && allSubtasksCompleted;
  }

  private blockingRequestsForCurrentUser(): InventoryRequest[] {
    const actorId = this.currentUserId();
    if (!actorId) {
      return [];
    }

    const blockingStatuses = new Set(['PENDING', 'PENDING_DISPATCH', 'PENDING_RECEIPT', 'APPROVED']);
    return (this.task()?.inventory_requests ?? []).filter(
      (request) => request.requested_by_crm_user_id === actorId && blockingStatuses.has(request.request_status)
    );
  }

  private pendingRequestReceiptItems(request: InventoryRequest): InventoryDispatchItem[] {
    return request.dispatches.flatMap((dispatch) => dispatch.items).filter((item) => !item.received_confirmed_at);
  }

  private refresh(taskId: string): void {
    this.isLoading.set(true);
    this.pageError.set(null);
    this.taskManagementService.getTaskDetail(taskId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (task) => {
        this.task.set(task);
        this.selectedCommentLocation.set(this.taskLocation());
        this.pageError.set(null);
        this.selectedSubtaskId.set(task.current_subtask_id ?? task.subtasks[0]?.subtask_id ?? null);
        this.rebuildOperationForm();
        this.loadTaskSatisfactionStatus(task.task_id);
        this.loadTaskPreFormStatus(task.task_id);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.pageError.set(error.message);
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
        this.selectedCommentLocation.set(this.taskLocation());
        this.successMessage.set(message);
        this.errorMessage.set(null);
        this.loadTaskSatisfactionStatus(task.task_id);
        this.loadTaskPreFormStatus(task.task_id);
        this.isSaving.set(false);
      },
      error: (error: Error) => {
        this.showOperationError(error.message);
        this.isSaving.set(false);
      }
    });
  }

  private rebuildOperationForm(): void {
    const subtask = this.selectedSubtask();
    this.itemControls.clear();
    if (!subtask) {
      this.subtaskAssigneeOptions.set([]);
      this.adminAssignmentForm.reset({ assigned_crm_user_id: null, notes: null });
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
    this.selectedPrimaryCommentAction.set('comment');
    this.adminAssignmentForm.reset({
      assigned_crm_user_id: subtask.assigned_crm_user_id,
      notes: null
    });
    this.loadNextAssigneeOptions(subtask);
  }

  private updateTask(task: TaskDetail, message: string): void {
    this.task.set(task);
    this.selectedCommentLocation.set(this.taskLocation());
    this.selectedSubtaskId.set(task.current_subtask_id ?? this.selectedSubtaskId());
    this.pendingAttachments.set([]);
    this.rebuildOperationForm();
    this.successMessage.set(message);
    this.errorMessage.set(null);
    this.isSaving.set(false);
  }

  private submitTaskCommentWithLocationId(taskId: string, body: string, locationId: string | null): void {
    this.taskManagementService
      .addTaskComment(taskId, {
        body,
        location_id: locationId,
        attachment_ids: this.pendingAttachments().map((attachment) => attachment.id)
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          this.operationForm.controls.comment.setValue('');
          const infoSuffix = this.requiresArrivalRegistration()
            ? ' Si este pedido requería llegada, quedó registrada automáticamente.'
            : '';
          this.updateTask(task, `Comentario guardado.${infoSuffix}`);
        },
        error: (error: Error) => {
          this.showOperationError(error.message);
          this.isSaving.set(false);
        }
      });
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

  private loadSubtaskAssigneeOptions(subtask: Subtask): void {
    if (!this.canAdminAssignSubtask(subtask) || !subtask.responsible_role_key) {
      this.subtaskAssigneeOptions.set([]);
      return;
    }

    this.taskManagementService.listCrmUsersByRole(subtask.responsible_role_key).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (options) => this.subtaskAssigneeOptions.set(options),
      error: () => this.subtaskAssigneeOptions.set([])
    });
  }

  private detectAndroidCompactLayout(): boolean {
    const userAgent = globalThis.navigator?.userAgent?.toLowerCase?.() ?? '';
    const isAndroidUa = userAgent.includes('android');
    const isNarrowViewport = typeof globalThis.innerWidth === 'number' ? globalThis.innerWidth <= 920 : false;
    return isAndroidUa || isNarrowViewport;
  }

  private createDraftItemId(): string {
    return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  private buildSubtaskProgressItemsPayload(): Array<{ item_id: string; checkbox_value?: boolean; text_value?: string | null }> {
    this.itemControls.updateValueAndValidity({ emitEvent: false });

    return this.itemControls.controls.map((control) => {
      const itemType = String(control.get('item_type')?.value ?? '').trim().toLowerCase();
      return {
        item_id: String(control.get('item_id')?.value ?? ''),
        checkbox_value: itemType === 'checkbox' ? Boolean(control.get('checkbox_value')?.value) : undefined,
        text_value: itemType === 'text' ? (String(control.get('text_value')?.value ?? '').trim() || null) : undefined
      };
    });
  }

  private loadTaskSatisfactionStatus(taskId: string): void {
    this.taskManagementService.getTaskSatisfactionFormStatus(taskId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (status) => this.taskSatisfactionStatus.set(status),
      error: () => this.taskSatisfactionStatus.set(null),
    });
  }

  private loadTaskPreFormStatus(taskId: string): void {
    this.taskManagementService.getTaskPreFormStatus(taskId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (status) => {
        this.taskPreFormStatus.set(status);
        if (!status.submitted_at) {
          this.isPreFormResponseVisible.set(false);
        }
      },
      error: () => {
        this.taskPreFormStatus.set(null);
        this.isPreFormResponseVisible.set(false);
      },
    });
  }

  private handleSubtaskClosed(task: TaskDetail): void {
    const closedSubtaskTitle = this.selectedSubtask()?.subtask_title ?? null;
    this.task.set(task);
    this.isSaving.set(false);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.router.navigate(['/tasks/subtask-success'], {
      queryParams: {
        subtask: closedSubtaskTitle,
      },
    });
  }

  private showOperationError(message: string): void {
    this.pageError.set(null);
    this.errorMessage.set(message);
    this.snackBar.open(message, 'Cerrar', { duration: 4500 });
  }
}