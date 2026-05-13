import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatDialog } from '@angular/material/dialog';
import { MatMenuModule, MatMenuTrigger } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { forkJoin, from, switchMap } from 'rxjs';

import { crmApiConfig } from '../../../../core/config/crm-api.config';
import { CrmUserOption } from '../../../../core/models/task-management.model';
import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { AppLocation } from '../../../../core/models/location.model';
import {
  AssignTicketRequest,
  buildTicketStatusTransitions,
  formatTicketPriority,
  formatTicketStatus,
  TicketAttachment,
  TicketDetail,
  TicketStatusTransitionOption,
  toTicketStatusTone,
  UpdateTicketStatusRequest
} from '../../../../core/models/ticket-management.model';
import { InventoryService } from '../../../../core/services/inventory.service';
import { InventoryFlowService } from '../../../../core/services/inventory-flow.service';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { TicketManagementService } from '../../../../core/services/ticket-management.service';
import { PermissionService } from '../../../../core/services/permission.service';
import { TicketInventoryRequest, TicketInventoryRequestItem, TicketInventoryRequestStatus } from '../../../../core/models/ticket-inventory-request.model';
import { isVideoFile, optimizeImagesForUpload } from '../../../../core/utils/media-upload-optimization';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';
import { SurveyLinkDialogComponent } from '../survey-link-dialog/survey-link-dialog.component';
import { MarkSolutionConfirmDialogComponent } from '../mark-solution-confirm-dialog/mark-solution-confirm-dialog.component';
import { TicketAttachmentsSectionComponent } from '../ticket-attachments-section/ticket-attachments-section.component';
import { TicketDescriptionSectionComponent } from '../ticket-description-section/ticket-description-section.component';


const TICKET_ALLOWED_IMAGE_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const TICKET_ALLOWED_VIDEO_MIME_TYPES = new Set(['video/mp4', 'video/webm', 'video/quicktime']);
const TICKET_ALLOWED_IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp']);
const TICKET_ALLOWED_VIDEO_EXTENSIONS = new Set(['mp4', 'webm', 'mov']);

type TicketPrimaryAction = 'comment' | 'transition' | 'close';
type DispatchIdentifierType = 'none' | 'serial' | 'barcode';

type TicketDispatchDraftItem = {
  draft_id: string;
  product_id: string;
  quantity_dispatched: number;
  serial_number: string | null;
  barcode_value: string | null;
  notes: string | null;
  product_name: string;
  requires_tracking: boolean;
  identifier_type: DispatchIdentifierType;
  identifier_value: string | null;
};

interface TicketTimelineEvent {
  id: string;
  anchorId?: string;
  commentId?: string;
  commentType?: string;
  occurredAt: string;
  title: string;
  subtitle: string;
  body: string;
  kind: 'comment' | 'status' | 'assignment' | 'request' | 'dispatch' | 'receipt';
  isArrivalComment?: boolean;
  isSolutionComment?: boolean;
  attachments: TicketAttachment[];
  location?: AppLocation; // Location attached to comment
}

@Component({
  selector: 'app-ticket-execution-page',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTooltipModule,
    PageTitleComponent,
    ReactiveFormsModule,
    RouterLink,
    StatusBadgeComponent,
    TicketAttachmentsSectionComponent,
    TicketDescriptionSectionComponent,
    UserAvatarComponent
  ],
  templateUrl: './ticket-execution-page.component.html',
  styleUrl: './ticket-execution-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TicketExecutionPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly formBuilder = inject(FormBuilder);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly permissionService = inject(PermissionService);
  private readonly inventoryService = inject(InventoryService);
  private readonly inventoryFlowService = inject(InventoryFlowService);
  private readonly ticketManagementService = inject(TicketManagementService);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly backendOrigin = this.resolveBackendOrigin();
  private activeCommentLocationRequest = 0;
  private commentLocationWatchdogId: ReturnType<typeof setTimeout> | null = null;

  readonly ticket = signal<TicketDetail | null>(null);
  readonly isLoading = signal(true);
  readonly isSaving = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly inventoryProducts = signal<InventoryProduct[]>([]);
  readonly inventoryOptions = signal<Array<{ id: string; name: string; unit: string }>>([]);
  readonly assignableUsers = signal<CrmUserOption[]>([]);
  readonly pendingAttachments = signal<TicketAttachment[]>([]);
  readonly availableTransitions = signal<TicketStatusTransitionOption[]>([]);
  readonly selectedPrimaryAction = signal<TicketPrimaryAction>('comment');
  readonly showInventoryRequestDrawer = signal(false);
  readonly showDispatchComposer = signal(false);
  readonly dispatchDraftItems = signal<TicketDispatchDraftItem[]>([]);
  readonly selectedCommentLocation = signal<AppLocation | null>(null);
  readonly isResolvingCommentLocation = signal(false);
  readonly pendingRejectRequestId = signal<string | null>(null);
  readonly exportingHistory = signal(false);
  readonly generatingSurvey = signal(false);
  readonly loadingSurveyStatus = signal(false);

  readonly commentForm = this.formBuilder.group({
    body: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true })
  });
  readonly assignmentForm = this.formBuilder.group({
    assigned_role_id: this.formBuilder.control<string | null>(null),
    assigned_user_id: this.formBuilder.control<string | null>(null),
    notes: this.formBuilder.control<string | null>(null)
  });
  readonly statusForm = this.formBuilder.group({
    to_status: this.formBuilder.control<UpdateTicketStatusRequest['to_status'] | null>(null)
  });
  readonly inventoryRequestForm = this.formBuilder.group({
    inventoryItemId: this.formBuilder.control<string | null>(null, Validators.required),
    quantity: this.formBuilder.control(1, { validators: [Validators.required, Validators.min(1)], nonNullable: true }),
    notes: this.formBuilder.control<string | null>(null)
  });
  readonly dispatchComposerForm = this.formBuilder.group({
    request_id: this.formBuilder.control<string | null>(null),
    product_id: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    identifier_type: this.formBuilder.control<DispatchIdentifierType>('none', { nonNullable: true }),
    identifier_value: this.formBuilder.control<string | null>(null),
    notes: this.formBuilder.control<string | null>(null),
    dispatch_notes: this.formBuilder.control<string | null>(null)
  });
  readonly receiptConfirmationForm = this.formBuilder.group({
    comment: this.formBuilder.control<string | null>(null)
  });
  readonly rejectRequestForm = this.formBuilder.group({
    comment: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true })
  });
  readonly rejectTicketApprovalForm = this.formBuilder.group({
    comment: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true })
  });
  readonly reopenForm = this.formBuilder.group({
    comment: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true })
  });

  readonly currentRoles = computed(() => this.authSessionService.sessionSnapshot()?.user.role_keys ?? []);
  readonly currentUserId = computed(() => this.authSessionService.sessionSnapshot()?.user.crm_user_id ?? null);
  readonly actorRoleIds = computed(() => this.resolveActorRoleIds());
  readonly isDeposito = computed(() => this.hasRole('deposito'));
  readonly isTecnico = computed(() => this.hasRole('tecnico'));
  readonly isAdmin = computed(() => this.hasRole('admin'));
  readonly isExecutive = computed(() => this.hasRole('ejecutivo'));
  readonly canManageDispatch = computed(() => {
    return this.isDeposito();
  });
  readonly canCreateInventoryRequest = computed(() => this.canOperateTicket());
  readonly canViewDispatchedHistory = computed(() => this.isDeposito() || this.isTecnico() || this.isAdmin() || this.isExecutive());
  readonly canReviewRequests = computed(() => this.canManageDispatch());
  readonly canOperateTicket = computed(() => {
    const ticket = this.ticket();
    if (!ticket) {
      return false;
    }

    const roles = this.currentRoles();
    if (roles.includes('admin') || roles.includes('ejecutivo')) {
      return true;
    }

    if (ticket.assigned_user_id && ticket.assigned_user_id === this.currentUserId()) {
      return true;
    }

    if (!ticket.assigned_user_id && ticket.assigned_role_id) {
      const roleIds = this.actorRoleIds();
      return roleIds.includes(ticket.assigned_role_id);
    }

    return false;
  });
  readonly canReassign = computed(() => {
    if (this.permissionService.canReassignTickets()) {
      return true;
    }
    const ticket = this.ticket();
    if (!ticket) {
      return false;
    }

    const roles = this.currentRoles();
    if (roles.includes('admin') || roles.includes('ejecutivo')) {
      return true;
    }

    if (ticket.assigned_role_id) {
      const roleIds = this.actorRoleIds();
      return roleIds.includes(ticket.assigned_role_id);
    }

    return ticket.assigned_user_id === this.currentUserId();
  });
  readonly canCloseOrTransition = computed(() => {
    const ticket = this.ticket();
    return Boolean(ticket && ticket.status !== 'CLOSED' && this.canOperateTicket() && !this.pendingReceiptRequestForCurrentUser());
  });
  readonly hasArrivalRegistered = computed(() => {
    const ticket = this.ticket();
    if (!ticket) {
      return false;
    }
    if (ticket.arrival_registered_at) {
      return true;
    }
    if (ticket.arrival_comment_id) {
      return true;
    }
    if (typeof ticket.has_arrival_registered === 'boolean') {
      return ticket.has_arrival_registered;
    }
    return false;
  });
  readonly isArrivalRequired = computed(() => Boolean(this.ticket()?.requires_arrival_comment));
  readonly arrivalCommentAnchor = computed(() => {
    const commentId = this.ticket()?.arrival_comment_id;
    return commentId ? `#ticket-comment-${commentId}` : null;
  });
  readonly canCloseTicket = computed(() => {
    return this.canCloseOrTransition() && (!this.isArrivalRequired() || this.hasArrivalRegistered());
  });
  readonly isCloseBlockedByArrivalRequirement = computed(() => {
    return this.isArrivalRequired() && !this.hasArrivalRegistered() && this.canCloseOrTransition();
  });
  readonly isCloseBlockedByVideoRequirement = computed(() => {
    return Boolean(this.ticket()?.requires_video_evidence && !this.hasPendingCloseVideoEvidence() && this.canCloseOrTransition());
  });
  readonly canApproveExecutiveClosure = computed(() => {
    const ticket = this.ticket();
    return Boolean(ticket && ticket.status === 'PENDING_APPROVAL' && (this.isAdmin() || this.isExecutive()));
  });
  readonly canReopenClosedTicket = computed(() => {
    const ticket = this.ticket();
    if (!ticket || ticket.status !== 'CLOSED') {
      return false;
    }

    const currentUserId = this.currentUserId();
    return Boolean(this.isAdmin() || this.isExecutive() || (currentUserId && ticket.closed_by_crm_user_id === currentUserId));
  });
  readonly canAccessPostClosureActions = computed(() => {
    const ticket = this.ticket();
    if (!ticket) {
      return false;
    }
    return ticket.status === 'CLOSED' && (this.isAdmin() || this.isExecutive());
  });
  readonly hasGeneratedSurvey = computed(() => Boolean(this.ticket()?.survey_generated_at));
  readonly ticketRoles = signal<Array<{ crm_role_id: string; role_key: string; role_label: string }>>([]);
  readonly inventoryRequestsVm = computed<readonly TicketInventoryRequest[]>(() => {
    const ticket = this.ticket();
    if (!ticket) {
      return [];
    }

    return ticket.inventory_requests
      .map((request) => ({
        id: request.inventory_request_id,
        requestedByUserId: request.requested_by_crm_user_id,
        requestedByUserName: request.requested_by_display_name || request.requested_by_crm_user_id,
        requestedAt: request.requested_at,
        status: this.toTicketRequestStatus(request.request_status),
        requestReason: request.request_reason || undefined,
        items: request.items.map((item) => ({
          inventoryItemId: item.product_id,
          inventoryItemName: item.product_name,
          quantity: item.quantity_requested,
          notes: item.notes || undefined,
          requiresTracking: item.requires_tracking
        })),
        depositDecisionComment: request.review_notes || undefined
      }))
      .sort((left, right) => right.requestedAt.localeCompare(left.requestedAt));
  });
  readonly dispatchedItemsVm = computed<
    ReadonlyArray<{
      inventoryDispatchItemId: string;
      inventoryItemId: string;
      inventoryItemName: string;
      quantity: number;
      requestId?: string;
      serialNumber?: string;
      barcodeValue?: string;
      notes?: string;
      requiresTracking?: boolean;
      dispatchedAt: string;
      receivedConfirmedAt?: string;
      deliveredConfirmedAt?: string;
      installedConfirmedAt?: string;
    }>
  >(() => {
    const ticket = this.ticket();
    if (!ticket) {
      return [];
    }

    return ticket.dispatches.flatMap((dispatch) =>
      dispatch.items.map((item) => ({
        inventoryDispatchItemId: item.inventory_dispatch_item_id,
        inventoryItemId: item.product_id,
        inventoryItemName: item.product_name,
        quantity: item.quantity_dispatched,
        requestId: dispatch.request_id || undefined,
        serialNumber: item.serial_number || undefined,
        barcodeValue: item.barcode_value || undefined,
        notes: item.notes || undefined,
        requiresTracking: item.requires_tracking,
        dispatchedAt: dispatch.created_at,
        receivedConfirmedAt: item.received_confirmed_at || undefined,
        deliveredConfirmedAt: item.delivered_confirmed_at || undefined,
        installedConfirmedAt: item.installed_confirmed_at || undefined
      }))
    );
  });
  readonly dispatchableRequests = computed(() => this.inventoryRequestsVm().filter((request) => request.status === 'approved_for_dispatch'));
  readonly pendingReceiptRequestForCurrentUser = computed(() => {
    return this.inventoryRequestsVm().find((request) => request.status === 'pending_receipt') ?? null;
  });
  readonly pendingReceiptDispatchItems = computed(() => {
    const pendingRequest = this.pendingReceiptRequestForCurrentUser();
    if (!pendingRequest) {
      return [];
    }

    return this.dispatchedItemsVm().filter((item) => item.requestId === pendingRequest.id && !item.receivedConfirmedAt);
  });
  readonly blockingRequestForCurrentUser = computed(() => {
    const currentUserId = this.currentUserId();
    if (!currentUserId) {
      return null;
    }

    return (
      this.inventoryRequestsVm().find(
        (request) =>
          String(request.requestedByUserId) === currentUserId &&
          (request.status === 'pending_deposit_review' || request.status === 'approved_for_dispatch')
      ) ?? null
    );
  });
  readonly timelineEvents = computed<readonly TicketTimelineEvent[]>(() => {
    const ticket = this.ticket();
    if (!ticket) {
      return [];
    }

    const commentEvents: TicketTimelineEvent[] = ticket.comments.map((comment) => {
      const isArrivalComment = Boolean(ticket.arrival_comment_id && ticket.arrival_comment_id === comment.ticket_comment_id);
      const isSolutionComment = Boolean(ticket.solution_comment_id && ticket.solution_comment_id === comment.ticket_comment_id);
      return {
        id: `comment-${comment.ticket_comment_id}`,
        anchorId: `ticket-comment-${comment.ticket_comment_id}`,
        commentId: comment.ticket_comment_id,
        commentType: comment.comment_type,
        occurredAt: comment.created_at,
        title: comment.author_display_name || 'Usuario CRM',
        subtitle: this.timelineLabelByCommentType(comment.comment_type),
        body: comment.body,
        kind: 'comment',
        isArrivalComment,
        isSolutionComment,
        attachments: comment.attachments,
        location: comment.location || undefined
      };
    });

    const statusEvents: TicketTimelineEvent[] = ticket.status_history.map((statusEvent) => ({
      id: `status-${statusEvent.ticket_status_transition_id}`,
      occurredAt: statusEvent.created_at,
      title: statusEvent.performed_by_display_name || 'Sistema',
      subtitle: 'Cambio de estado',
      body: `${statusEvent.from_status} -> ${statusEvent.to_status}`,
      kind: 'status',
      attachments: []
    }));

    const assignmentEvents: TicketTimelineEvent[] = ticket.assignment_history.map((assignment) => ({
      id: `assignment-${assignment.ticket_assignment_id}`,
      occurredAt: assignment.created_at,
      title: assignment.assigned_by_display_name || 'Sistema',
      subtitle: 'Reasignación',
      body: assignment.notes || `Asignado a ${assignment.assigned_user_display_name || assignment.assigned_role_key || 'Sin asignación específica'}`,
      kind: 'assignment',
      attachments: []
    }));

    const requestEvents: TicketTimelineEvent[] = ticket.inventory_requests.map((request) => ({
      id: `request-${request.inventory_request_id}`,
      occurredAt: request.requested_at,
      title: request.requested_by_display_name || 'Técnico',
      subtitle: 'Solicitud a depósito',
      body: `${request.items.length} item(s) · ${this.inventoryRequestStatusLabel(this.toTicketRequestStatus(request.request_status))}`,
      kind: 'request',
      attachments: []
    }));

    const dispatchEvents: TicketTimelineEvent[] = ticket.dispatches.map((dispatch) => ({
      id: `dispatch-${dispatch.inventory_dispatch_id}`,
      occurredAt: dispatch.created_at,
      title: dispatch.dispatched_by_display_name || 'Depósito',
      subtitle: 'Despacho registrado',
      body: `${dispatch.items.length} item(s) despachados`,
      kind: 'dispatch',
      attachments: []
    }));

    const receiptEvents: TicketTimelineEvent[] = ticket.audit_events
      .filter((auditEvent) => auditEvent.event_type === 'ticket.dispatch_received_confirmed')
      .map((auditEvent) => {
        const payload = (auditEvent.payload_json || {}) as Record<string, unknown>;
        const receptionComment = typeof payload['reception_comment'] === 'string' ? payload['reception_comment'].trim() : '';

        return {
          id: `receipt-${auditEvent.ticket_audit_event_id}`,
          occurredAt: auditEvent.created_at,
          title: 'Técnico',
          subtitle: 'Recepción confirmada',
          body: receptionComment ? `Recepción confirmada. Comentario: ${receptionComment}` : 'Recepción confirmada por técnico.',
          kind: 'receipt',
          attachments: []
        };
      });

    return [...commentEvents, ...statusEvents, ...assignmentEvents, ...requestEvents, ...dispatchEvents, ...receiptEvents].sort((left, right) =>
      right.occurredAt.localeCompare(left.occurredAt)
    );
  });

  constructor() {
    this.inventoryService.products$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((products) => {
      this.inventoryProducts.set(products);
      this.inventoryOptions.set(products.map((product) => ({ id: product.productId, name: product.productName, unit: 'unidad' })));
    });
    this.inventoryService
      .refresh()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ error: () => undefined });

    this.ticketManagementService
      .listAssignableRoles()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (roles) => this.ticketRoles.set(roles),
        error: (error: Error) => this.errorMessage.set(error.message)
      });

    this.assignmentForm.controls.assigned_role_id.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((roleId) => {
      this.loadAssignees(roleId);
    });

    this.refreshTicket();
  }

  addAttachments(files: readonly File[]): void {
    const ticket = this.ticket();
    if (!ticket || !files.length) {
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    from(this.prepareTicketFilesForUpload(files))
      .pipe(switchMap((preparedFiles) => this.ticketManagementService.uploadTicketAttachments(ticket.ticket_id, preparedFiles)))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (attachments) => {
          this.pendingAttachments.update((current) => [...current, ...attachments]);
          this.successMessage.set('Adjuntos cargados correctamente.');
          this.isSaving.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  private async prepareTicketFilesForUpload(files: readonly File[]): Promise<File[]> {
    const preparedFiles = await optimizeImagesForUpload(files);

    for (const file of preparedFiles) {
      if (!this.isSupportedTicketMediaFile(file)) {
        throw new Error(`El archivo ${file.name} no tiene un formato soportado. Permitidos: JPG, PNG, WEBP, MP4, WEBM o MOV.`);
      }
    }

    return preparedFiles;
  }

  private isSupportedTicketMediaFile(file: File): boolean {
    const mimeType = file.type.toLowerCase();
    const extension = this.getFileExtension(file.name);

    if (!mimeType) {
      return TICKET_ALLOWED_IMAGE_EXTENSIONS.has(extension) || TICKET_ALLOWED_VIDEO_EXTENSIONS.has(extension);
    }

    if (mimeType.startsWith('image/')) {
      return TICKET_ALLOWED_IMAGE_MIME_TYPES.has(mimeType) || TICKET_ALLOWED_IMAGE_EXTENSIONS.has(extension);
    }

    if (mimeType.startsWith('video/')) {
      return TICKET_ALLOWED_VIDEO_MIME_TYPES.has(mimeType) || TICKET_ALLOWED_VIDEO_EXTENSIONS.has(extension);
    }

    return false;
  }

  private isLikelyVideoFile(file: File): boolean {
    if (isVideoFile(file)) {
      return true;
    }
    return TICKET_ALLOWED_VIDEO_EXTENSIONS.has(this.getFileExtension(file.name));
  }

  private getFileExtension(fileName: string): string {
    const extensionIndex = fileName.lastIndexOf('.');
    if (extensionIndex < 0 || extensionIndex === fileName.length - 1) {
      return '';
    }
    return fileName.slice(extensionIndex + 1).toLowerCase();
  }

  removeAttachment(attachmentId: string): void {
    if (!attachmentId) {
      return;
    }

    this.ticketManagementService
      .deleteTicketAttachment(attachmentId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.pendingAttachments.update((current) => current.filter((attachment) => attachment.id !== attachmentId));
        },
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  submitComment(): void {
    const ticket = this.ticket();
    const comment = this.primaryCommentValue();
    if (!ticket || !comment) {
      this.commentForm.markAllAsTouched();
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    const selectedLocation = this.selectedCommentLocation();
    if (this.locationLinkService.isValidLocation(selectedLocation)) {
      this.ticketManagementService
        .createLocation(selectedLocation)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (location) => {
            this.submitCommentWithLocationId(ticket.ticket_id, location.locationId);
          },
          error: (error: Error) => {
            this.errorMessage.set(error.message);
            this.isSaving.set(false);
          }
        });
      return;
    }

    this.submitCommentWithLocationId(ticket.ticket_id, null);
  }

  openCommentLocationPicker(): void {
    this.locationPickerService
      .open({
        title: 'Marcar ubicación adicional de la visita',
        initialLocation: this.selectedCommentLocation()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result) => {
        if (!result) {
          return;
        }

        this.selectedCommentLocation.set(result.location);
      });
  }

  captureCurrentCommentLocation(): void {
    if (this.isResolvingCommentLocation()) {
      return;
    }

    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      this.errorMessage.set('Este navegador no permite usar GPS directo. Usá "Elegir en mapa" para marcar la ubicación.');
      this.snackBar.open('Este navegador no soporta GPS automático.', 'Cerrar', { duration: 4500 });
      return;
    }

    if (typeof window !== 'undefined' && !window.isSecureContext) {
      this.errorMessage.set('El GPS automático requiere un contexto seguro (HTTPS o localhost). Usá "Elegir en mapa" o abrí la app en HTTPS.');
      this.snackBar.open('GPS bloqueado: abrí la app en HTTPS o usá Elegir en mapa.', 'Cerrar', { duration: 6000 });
      return;
    }

    const requestId = this.activeCommentLocationRequest + 1;
    this.activeCommentLocationRequest = requestId;
    this.isResolvingCommentLocation.set(true);
    this.errorMessage.set(null);
    this.snackBar.open('Solicitando ubicación al dispositivo...', 'Cerrar', { duration: 3000 });

    this.clearCommentLocationWatchdog();
    this.commentLocationWatchdogId = setTimeout(() => {
      if (this.activeCommentLocationRequest !== requestId) {
        return;
      }

      this.isResolvingCommentLocation.set(false);
      this.errorMessage.set('No llegó respuesta de ubicación del dispositivo. Revisá permiso GPS y reintentá, o usá "Elegir en mapa".');
      this.snackBar.open('Sin respuesta de GPS. Revisá permisos de ubicación.', 'Cerrar', { duration: 6000 });
    }, 12000);

    try {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (this.activeCommentLocationRequest !== requestId) {
            return;
          }

          this.clearCommentLocationWatchdog();
          this.selectedCommentLocation.set({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            addressLabel: `Ubicación actual ${position.coords.latitude.toFixed(5)}, ${position.coords.longitude.toFixed(5)}`
          });
          this.isResolvingCommentLocation.set(false);
          this.snackBar.open('Ubicación actual capturada.', 'Cerrar', { duration: 2500 });
        },
        (error) => {
          if (this.activeCommentLocationRequest !== requestId) {
            return;
          }

          this.clearCommentLocationWatchdog();
          this.errorMessage.set(this.resolveCommentLocationError(error));
          this.isResolvingCommentLocation.set(false);
        },
        { enableHighAccuracy: true, maximumAge: 10000, timeout: 10000 }
      );
    } catch {
      this.clearCommentLocationWatchdog();
      this.isResolvingCommentLocation.set(false);
      this.errorMessage.set('No se pudo iniciar la solicitud de ubicación. Probá con "Elegir en mapa".');
    }
  }

  clearCommentLocation(): void {
    this.selectedCommentLocation.set(null);
  }

  selectedCommentLocationLabel(): string {
    const location = this.selectedCommentLocation();
    if (!location) {
      return 'Sin ubicación adicional';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  canOpenCommentLocationInMaps(): boolean {
    return this.locationLinkService.isValidLocation(this.selectedCommentLocation());
  }

  openCommentLocationInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.selectedCommentLocation());
  }

  submitAssignment(): void {
    const ticket = this.ticket();
    if (!ticket || !this.canReassign()) {
      return;
    }

    const payload: AssignTicketRequest = {
      assigned_role_id: this.assignmentForm.controls.assigned_role_id.getRawValue(),
      assigned_user_id: this.assignmentForm.controls.assigned_user_id.getRawValue(),
      notes: this.assignmentForm.controls.notes.getRawValue()?.trim() || null
    };

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.ticketManagementService
      .assignTicket(ticket.ticket_id, payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.assignmentForm.patchValue({ notes: null }, { emitEvent: false });
          this.showInventoryRequestDrawer.set(false);
          this.finishCriticalAction('Asignación actualizada correctamente.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  submitStatusTransition(): void {
    const ticket = this.ticket();
    const toStatus = this.statusForm.controls.to_status.getRawValue();
    if (!ticket || !toStatus || !this.canCloseOrTransition()) {
      return;
    }

    const payload: UpdateTicketStatusRequest = {
      to_status: toStatus,
      comment: this.primaryCommentValue() || null,
      attachment_ids: this.pendingAttachments().map((attachment) => attachment.id)
    };

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.ticketManagementService
      .updateTicketStatus(ticket.ticket_id, payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.statusForm.reset({ to_status: null });
          this.finishCriticalAction('Estado del ticket actualizado.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  closeTicket(): void {
    const ticket = this.ticket();
    const comment = this.primaryCommentValue();
    if (!ticket || !comment) {
      this.commentForm.markAllAsTouched();
      return;
    }

    if (ticket.requires_video_evidence && !this.hasPendingCloseVideoEvidence()) {
      this.errorMessage.set('El cierre del ticket requiere adjuntar al menos un video de evidencia.');
      return;
    }

    if (!this.canCloseTicket()) {
      if (this.isCloseBlockedByArrivalRequirement()) {
        this.errorMessage.set(
          'Este ticket requiere registrar llegada antes de poder cerrarse. Agregá un comentario con multimedia y ubicación asociada.'
        );
      }
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.ticketManagementService
      .closeTicket(ticket.ticket_id, {
        comment,
        attachment_ids: this.pendingAttachments().map((attachment) => attachment.id)
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updatedTicket) => {
          this.selectedPrimaryAction.set('comment');
          this.finishCriticalAction(
            updatedTicket.status === 'PENDING_APPROVAL'
              ? 'Ticket enviado a aprobación ejecutiva.'
              : 'Ticket cerrado correctamente.'
          );
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  approveTicket(): void {
    const ticket = this.ticket();
    if (!ticket || !this.canApproveExecutiveClosure()) {
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.ticketManagementService
      .approveTicket(ticket.ticket_id, { comment: this.primaryCommentValue() || null })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.rejectTicketApprovalForm.reset({ comment: '' });
          this.finishCriticalAction('Ticket aprobado y archivado en historial.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  rejectTicketApproval(): void {
    const ticket = this.ticket();
    if (!ticket || !this.canApproveExecutiveClosure()) {
      return;
    }

    const comment = this.rejectTicketApprovalForm.controls.comment.getRawValue().trim();
    if (!comment) {
      this.rejectTicketApprovalForm.markAllAsTouched();
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.ticketManagementService
      .rejectTicketApproval(ticket.ticket_id, { comment })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.rejectTicketApprovalForm.reset({ comment: '' });
          this.finishCriticalAction('Cierre rechazado. El ticket volvió al flujo operativo con trazabilidad.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  createInventoryRequest(items: readonly TicketInventoryRequestItem[]): void {
    const ticket = this.ticket();
    if (!ticket || !items.length) {
      return;
    }

    this.isSaving.set(true);
    this.inventoryFlowService
      .createRequest({
        source_type: 'TICKET',
        external_ticket_id: ticket.ticket_id,
        request_reason: null,
        items: items.map((item) => ({
          product_id: String(item.inventoryItemId),
          quantity_requested: item.quantity,
          notes: item.notes ?? null
        }))
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.inventoryRequestForm.reset({ inventoryItemId: null, quantity: 1, notes: null });
          this.showInventoryRequestDrawer.set(false);
          this.showDispatchComposer.set(false);
          this.finishCriticalAction('Solicitud enviada a depósito.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  submitInventoryRequestFromDrawer(): void {
    if (this.inventoryRequestForm.invalid) {
      this.inventoryRequestForm.markAllAsTouched();
      return;
    }

    const selectedItemId = this.inventoryRequestForm.controls.inventoryItemId.getRawValue();
    const selectedItem = this.inventoryOptions().find((option) => option.id === selectedItemId);
    if (!selectedItem) {
      return;
    }

    this.createInventoryRequest([
      {
        inventoryItemId: selectedItem.id,
        inventoryItemName: selectedItem.name,
        quantity: this.inventoryRequestForm.controls.quantity.getRawValue(),
        notes: this.inventoryRequestForm.controls.notes.getRawValue()?.trim() || undefined
      }
    ]);
  }

  decideInventoryRequest(requestId: string, status: TicketInventoryRequestStatus, comment: string): void {
    if (!requestId) {
      return;
    }

    if (status === 'rejected' && !comment.trim()) {
      this.errorMessage.set('El rechazo requiere un comentario obligatorio con el motivo.');
      return;
    }

    this.isSaving.set(true);
    this.inventoryFlowService
      .reviewRequest(requestId, {
        status: status === 'approved_for_dispatch' ? 'APPROVED' : 'REJECTED',
        review_notes: comment || null
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.pendingRejectRequestId.set(null);
          this.rejectRequestForm.reset({ comment: '' });
          this.finishCriticalAction('Decisión de depósito registrada.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  openRejectInventoryRequest(requestId: string): void {
    this.pendingRejectRequestId.set(requestId);
    this.rejectRequestForm.reset({ comment: '' });
    this.errorMessage.set(null);
  }

  cancelRejectInventoryRequest(): void {
    this.pendingRejectRequestId.set(null);
    this.rejectRequestForm.reset({ comment: '' });
  }

  confirmRejectInventoryRequest(requestId: string): void {
    if (this.rejectRequestForm.invalid) {
      this.rejectRequestForm.markAllAsTouched();
      return;
    }

    const comment = this.rejectRequestForm.controls.comment.getRawValue().trim();
    this.decideInventoryRequest(requestId, 'rejected', comment);
  }

  reopenTicket(): void {
    const ticket = this.ticket();
    if (!ticket || !this.canReopenClosedTicket()) {
      return;
    }

    const comment = this.reopenForm.controls.comment.getRawValue().trim();
    if (!comment) {
      this.reopenForm.markAllAsTouched();
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.ticketManagementService
      .reopenTicket(ticket.ticket_id, { comment })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.reopenForm.reset({ comment: '' });
          this.finishCriticalAction('Ticket reabierto correctamente y devuelto al flujo operativo.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  exportTicketHistory(): void {
    const ticket = this.ticket();
    if (!ticket || !this.canAccessPostClosureActions() || this.exportingHistory()) {
      return;
    }

    this.exportingHistory.set(true);
    this.errorMessage.set(null);
    this.ticketManagementService
      .exportTicketHistory(ticket.ticket_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          this.exportingHistory.set(false);
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          const dateSuffix = new Date().toISOString().slice(0, 10).replace(/-/g, '');
          a.download = `ticket_${ticket.ticket_number}_${dateSuffix}.zip`;
          a.click();
          URL.revokeObjectURL(url);
          this.successMessage.set('Historial exportado correctamente.');
        },
        error: (error: Error) => {
          this.exportingHistory.set(false);
          this.errorMessage.set(error.message);
        }
      });
  }

  generateTicketSurvey(): void {
    const ticket = this.ticket();
    if (!ticket || !this.canAccessPostClosureActions() || this.generatingSurvey()) {
      return;
    }

    this.generatingSurvey.set(true);
    this.errorMessage.set(null);
    this.ticketManagementService
      .generateTicketSurvey(ticket.ticket_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.generatingSurvey.set(false);
          const link = this.buildSurveyLink(response.survey_path, response.public_link_token);
          this.dialog.open(SurveyLinkDialogComponent, {
            autoFocus: false,
            maxWidth: 'calc(100vw - 1.5rem)',
            width: '34rem',
            data: {
              title: 'Encuesta generada correctamente',
              message: 'Compartí este link seguro con el cliente.',
              surveyUrl: link,
              details: 'El link expira y no requiere login del cliente.',
              copyEnabled: true
            }
          });
          this.successMessage.set('Encuesta de satisfacción generada.');
          this.refreshTicket();
        },
        error: (error: Error) => {
          this.generatingSurvey.set(false);
          this.errorMessage.set(error.message);
        }
      });
  }

  viewSurveyStatus(): void {
    const ticket = this.ticket();
    if (!ticket || !this.canAccessPostClosureActions() || this.loadingSurveyStatus()) {
      return;
    }

    this.loadingSurveyStatus.set(true);
    this.errorMessage.set(null);
    this.ticketManagementService
      .getSatisfactionFormStatus(ticket.ticket_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (status) => {
          if (status.has_response) {
            this.ticketManagementService
              .getSatisfactionResponse(ticket.ticket_id)
              .pipe(takeUntilDestroyed(this.destroyRef))
              .subscribe({
                next: (response) => {
                  this.loadingSurveyStatus.set(false);
                  this.dialog.open(SurveyLinkDialogComponent, {
                    autoFocus: false,
                    maxWidth: 'calc(100vw - 1.5rem)',
                    width: '42rem',
                    data: {
                      title: 'Respuesta de encuesta',
                      message: 'Esta encuesta ya fue respondida por el cliente.',
                      details: `Enviada: ${this.formatDate(response.submitted_at)}.`,
                      surveyResponse: response,
                      copyEnabled: false
                    }
                  });
                },
                error: (error: Error) => {
                  this.loadingSurveyStatus.set(false);
                  this.errorMessage.set(error.message);
                }
              });
            return;
          }

          this.loadingSurveyStatus.set(false);
          const statusLabel = status.status_label || 'desconocido';
          const details = `Estado: ${statusLabel}. Expira: ${this.formatDate(status.expires_at)}.`;
          this.dialog.open(SurveyLinkDialogComponent, {
            autoFocus: false,
            maxWidth: 'calc(100vw - 1.5rem)',
            width: '34rem',
            data: {
              title: 'Estado de encuesta',
              message: 'Esta encuesta ya fue generada para el ticket.',
              details,
              copyEnabled: false
            }
          });
        },
        error: (error: Error) => {
          this.loadingSurveyStatus.set(false);
          this.errorMessage.set(error.message);
        }
      });
  }

  prepareDispatchForRequest(request: TicketInventoryRequest): void {
    if (!request.id || request.status !== 'approved_for_dispatch' || !this.canManageDispatch()) {
      return;
    }

    this.dispatchComposerForm.controls.request_id.setValue(request.id);
    this.showDispatchComposer.set(true);
    this.successMessage.set('Solicitud seleccionada para despacho. Cargá los items y confirmá el despacho.');
    this.errorMessage.set(null);
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
        this.errorMessage.set('Para productos con tracking unitario debés elegir Serial o Código de barras y cargar su valor.');
        return;
      }
    }
    if ((identifierType === 'serial' || identifierType === 'barcode') && !identifierValue) {
      this.errorMessage.set('Completá el valor del identificador seleccionado.');
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
        this.errorMessage.set('Ese identificador ya fue agregado para este producto en el despacho actual.');
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
    const requestId = this.dispatchComposerForm.controls.request_id.getRawValue()?.trim() || null;
    if (!requestId || !this.dispatchDraftItems().length) {
      return;
    }

    this.isSaving.set(true);
    this.inventoryFlowService
      .dispatchRequest(requestId, {
        request_id: requestId,
        dispatch_notes: this.dispatchComposerForm.controls.dispatch_notes.getRawValue()?.trim() || null,
        items: this.dispatchDraftItems().map(
          ({ draft_id: _draftId, product_name: _productName, requires_tracking: _requiresTracking, identifier_type: _identifierType, identifier_value: _identifierValue, ...item }) => item
        )
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.dispatchDraftItems.set([]);
          this.dispatchComposerForm.reset({
            request_id: null,
            product_id: '',
            identifier_type: 'none',
            identifier_value: null,
            notes: null,
            dispatch_notes: null
          });
          this.showDispatchComposer.set(false);
          this.finishCriticalAction('Despacho registrado y ticket devuelto al técnico solicitante.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  confirmPendingReceipt(): void {
    const pendingRequest = this.pendingReceiptRequestForCurrentUser();
    const pendingItems = this.pendingReceiptDispatchItems();
    if (!pendingRequest || !pendingItems.length || !this.canOperateTicket()) {
      return;
    }

    const receptionComment = this.receiptConfirmationForm.controls.comment.getRawValue()?.trim() || null;

    this.isSaving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    forkJoin(
      pendingItems.map((item, index) =>
        this.inventoryFlowService.confirmDispatchItem(item.inventoryDispatchItemId, {
          confirmation_type: 'received',
          reception_comment: index === 0 ? receptionComment : null
        })
      )
    )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.receiptConfirmationForm.reset({ comment: null });
          this.finishCriticalAction('Recepción del despacho confirmada.');
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  executePrimaryAction(): void {
    if (this.selectedPrimaryAction() === 'transition') {
      this.submitStatusTransition();
      return;
    }

    if (this.selectedPrimaryAction() === 'close') {
      this.closeTicket();
      return;
    }

    this.submitComment();
  }

  primaryActionLabel(): string {
    if (this.selectedPrimaryAction() === 'transition') {
      return 'Cambiar estado';
    }
    if (this.selectedPrimaryAction() === 'close') {
      return 'Cerrar ticket';
    }
    return 'Publicar comentario';
  }

  selectPrimaryAction(action: TicketPrimaryAction): void {
    this.selectedPrimaryAction.set(action);
  }

  canExecutePrimaryAction(): boolean {
    if (this.isSaving() || !this.canOperateTicket()) {
      return false;
    }

    if (this.selectedPrimaryAction() === 'transition') {
      return this.canCloseOrTransition() && Boolean(this.statusForm.controls.to_status.getRawValue());
    }

    if (this.selectedPrimaryAction() === 'close') {
      const videoRequirementMet = !this.ticket()?.requires_video_evidence || this.hasPendingCloseVideoEvidence();
      return this.canCloseTicket() && Boolean(this.primaryCommentValue()) && videoRequirementMet;
    }

    return Boolean(this.primaryCommentValue());
  }

  commentFieldLabel(): string {
    if (this.selectedPrimaryAction() === 'close') {
      return 'Comentario obligatorio de cierre';
    }
    if (this.selectedPrimaryAction() === 'transition') {
      return 'Comentario para cambio de estado (opcional)';
    }
    return 'Comentario operativo';
  }

  commentFieldPlaceholder(): string {
    if (this.selectedPrimaryAction() === 'close') {
      return 'Describe motivo y validación del cierre';
    }
    if (this.selectedPrimaryAction() === 'transition') {
      return 'Detalle opcional del cambio de estado';
    }
    return 'Describe diagnóstico, avance o bloqueo';
  }

  canMarkCommentAsSolution(event: TicketTimelineEvent): boolean {
    return this.canCloseTicket() && event.kind === 'comment' && event.commentType === 'general';
  }

  markCommentAsSolution(commentId: string): void {
    const ticket = this.ticket();
    if (!ticket || !commentId || !this.canCloseTicket()) {
      return;
    }

    this.dialog
      .open(MarkSolutionConfirmDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '30rem'
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((confirmed: boolean | undefined) => {
        if (!confirmed) {
          return;
        }

        this.isSaving.set(true);
        this.errorMessage.set(null);
        this.successMessage.set(null);
        this.ticketManagementService
          .markCommentAsSolution(ticket.ticket_id, commentId)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: (updatedTicket) => {
              this.selectedPrimaryAction.set('comment');
              this.finishCriticalAction(
                updatedTicket.status === 'PENDING_APPROVAL'
                  ? 'Ticket enviado a aprobación ejecutiva usando comentario como solución.'
                  : 'Ticket cerrado usando comentario marcado como solución.'
              );
            },
            error: (error: Error) => {
              this.errorMessage.set(error.message);
              this.isSaving.set(false);
            }
          });
      });
  }

  toggleInventoryRequestDrawer(): void {
    this.showInventoryRequestDrawer.update((value) => !value);
  }

  closeDispatchComposer(): void {
    this.showDispatchComposer.set(false);
    this.dispatchDraftItems.set([]);
    this.dispatchComposerForm.reset({
      request_id: null,
      product_id: '',
      identifier_type: 'none',
      identifier_value: null,
      notes: null,
      dispatch_notes: null
    });
  }

  canOpenAssigneeMenu(): boolean {
    return this.canReassign();
  }

  prepareAssigneeMenu(): void {
    const ticket = this.ticket();
    if (!ticket) {
      return;
    }

    this.assignmentForm.patchValue(
      {
        assigned_role_id: ticket.assigned_role_id,
        assigned_user_id: ticket.assigned_user_id,
        notes: null
      },
      { emitEvent: false }
    );
    this.loadAssignees(ticket.assigned_role_id);
  }

  assignFromAssigneeMenu(menuTrigger: MatMenuTrigger): void {
    this.submitAssignment();
    menuTrigger.closeMenu();
  }

  timelineTrackBy(_: number, event: TicketTimelineEvent): string {
    return event.id;
  }

  requestCardTitle(request: TicketInventoryRequest): string {
    return request.requestReason?.trim() || 'Solicitud a depósito';
  }

  inventoryRequestStatusLabel(status: TicketInventoryRequestStatus): string {
    if (status === 'pending_deposit_review') {
      return 'Pendiente de depósito';
    }
    if (status === 'approved_for_dispatch') {
      return 'Aprobada para despacho';
    }
    if (status === 'pending_receipt') {
      return 'Pendiente de recepción técnica';
    }
    if (status === 'dispatched') {
      return 'Despachada';
    }
    if (status === 'rejected') {
      return 'Rechazada';
    }
    return 'Cancelada';
  }

  inventoryRequestStatusTone(status: TicketInventoryRequestStatus): 'neutral' | 'warning' | 'success' | 'progress' {
    if (status === 'pending_deposit_review') {
      return 'warning';
    }
    if (status === 'approved_for_dispatch') {
      return 'progress';
    }
    if (status === 'pending_receipt') {
      return 'warning';
    }
    if (status === 'dispatched') {
      return 'success';
    }
    if (status === 'rejected') {
      return 'warning';
    }
    return 'neutral';
  }

  blockingInventoryRequestMessage(): string {
    const blockingRequest = this.blockingRequestForCurrentUser();
    if (!blockingRequest) {
      return 'El ticket está esperando gestión de depósito.';
    }

    if (blockingRequest.status === 'pending_deposit_review') {
      return 'Esperando autorización de depósito. Mientras tanto podés ver el ticket, pero no operarlo.';
    }

    return 'Esperando despacho de depósito. Las acciones operativas se habilitan cuando el ticket vuelva automáticamente al técnico solicitante.';
  }

  selectedDispatchProduct(): InventoryProduct | null {
    return this.inventoryProducts().find((product) => product.productId === this.dispatchComposerForm.controls.product_id.getRawValue()) ?? null;
  }

  requestOptionLabel(request: TicketInventoryRequest): string {
    return request.requestReason?.trim() || 'Solicitud aprobada';
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

  timelineTone(event: TicketTimelineEvent): 'neutral' | 'progress' | 'warning' | 'success' {
    if (event.kind === 'status') {
      return 'progress';
    }
    if (event.kind === 'dispatch') {
      return 'success';
    }
    if (event.kind === 'receipt') {
      return 'success';
    }
    if (event.kind === 'request') {
      return 'warning';
    }
    return 'neutral';
  }

  timelineAttachmentUrl(attachment: TicketAttachment): string | null {
    return this.toAbsoluteMediaUrl(attachment.publicUrl) ?? this.toAbsoluteMediaUrl(attachment.previewUrl) ?? this.toAbsoluteMediaUrl(attachment.storagePath);
  }

  openAttachmentInNewTab(url: string): void {
    if (!url) {
      return;
    }

    window.open(url, '_blank', 'noopener,noreferrer');
  }

  trackByCommentId(_: number, comment: TicketDetail['comments'][number]): string {
    return comment.ticket_comment_id;
  }

  readonly formatTicketStatus = formatTicketStatus;
  readonly toTicketStatusTone = toTicketStatusTone;
  readonly formatTicketPriority = formatTicketPriority;

  private refreshTicket(): void {
    const ticketId = this.ticketId();
    if (!ticketId) {
      this.errorMessage.set('No se indicó un ticket válido.');
      this.isLoading.set(false);
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.ticketManagementService
      .getTicketDetail(ticketId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (ticket) => {
          this.ticket.set(ticket);
          this.availableTransitions.set(buildTicketStatusTransitions(ticket.status));
          this.syncAssignmentForm(ticket);
          this.isLoading.set(false);
          this.isSaving.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isLoading.set(false);
          this.isSaving.set(false);
        }
      });
  }

  private reloadTicket(successMessage: string): void {
    this.successMessage.set(successMessage);
    this.refreshTicket();
  }

  private finishCriticalAction(message: string): void {
    this.successMessage.set(message);
    this.errorMessage.set(null);
    this.isSaving.set(false);
    this.snackBar.open(message, 'Cerrar', { duration: 5000 });
    void this.router.navigate(['/tickets']);
  }

  private submitCommentWithLocationId(ticketId: string, locationId: string | null): void {
    this.ticketManagementService
      .addTicketComment(ticketId, {
        body: this.primaryCommentValue(),
        location_id: locationId,
        attachment_ids: this.pendingAttachments().map((attachment) => attachment.id)
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updatedTicket) => {
          this.updateTicket(updatedTicket, 'Comentario agregado al ticket.');
          this.commentForm.reset({ body: '' });
          this.selectedCommentLocation.set(null);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  private syncAssignmentForm(ticket: TicketDetail): void {
    this.assignmentForm.patchValue(
      {
        assigned_role_id: ticket.assigned_role_id,
        assigned_user_id: ticket.assigned_user_id,
        notes: null
      },
      { emitEvent: false }
    );
    this.loadAssignees(ticket.assigned_role_id);
  }

  private loadAssignees(roleId: string | null): void {
    if (!roleId) {
      this.assignableUsers.set([]);
      this.assignmentForm.controls.assigned_user_id.setValue(null, { emitEvent: false });
      return;
    }

    const role = this.ticketRoles().find((item) => item.crm_role_id === roleId);
    if (!role) {
      this.assignableUsers.set([]);
      this.assignmentForm.controls.assigned_user_id.setValue(null, { emitEvent: false });
      return;
    }

    this.ticketManagementService
      .listCrmUsersByRole(role.role_key)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (users) => {
          this.assignableUsers.set(users);
          const currentUserId = this.assignmentForm.controls.assigned_user_id.getRawValue();
          if (currentUserId && !users.some((user) => user.crm_user_id === currentUserId)) {
            this.assignmentForm.controls.assigned_user_id.setValue(null, { emitEvent: false });
          }
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.assignableUsers.set([]);
          this.assignmentForm.controls.assigned_user_id.setValue(null, { emitEvent: false });
        }
      });
  }

  private updateTicket(ticket: TicketDetail, message: string): void {
    this.ticket.set(ticket);
    this.availableTransitions.set(buildTicketStatusTransitions(ticket.status));
    this.pendingAttachments.set([]);
    this.selectedCommentLocation.set(null);
    this.commentForm.reset({ body: '' });
    this.successMessage.set(message);
    this.isSaving.set(false);
    this.syncAssignmentForm(ticket);
  }

  private primaryCommentValue(): string {
    return this.commentForm.controls.body.getRawValue().trim();
  }

  private hasPendingCloseVideoEvidence(): boolean {
    return this.pendingAttachments().some((attachment) => {
      if (attachment.kind?.toLowerCase() === 'video') {
        return true;
      }
      return attachment.fileType?.toLowerCase().startsWith('video/') ?? false;
    });
  }

  private toTicketRequestStatus(status: string): TicketInventoryRequestStatus {
    switch (status) {
      case 'PENDING_DISPATCH':
      case 'APPROVED':
        return 'approved_for_dispatch';
      case 'PENDING_RECEIPT':
        return 'pending_receipt';
      case 'COMPLETED':
        return 'dispatched';
      case 'REJECTED':
        return 'rejected';
      case 'CANCELLED':
        return 'cancelled';
      default:
        return 'pending_deposit_review';
    }
  }

  private createDraftItemId(): string {
    return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  private clearCommentLocationWatchdog(): void {
    if (this.commentLocationWatchdogId !== null) {
      clearTimeout(this.commentLocationWatchdogId);
      this.commentLocationWatchdogId = null;
    }
  }

  private resolveCommentLocationError(error: GeolocationPositionError): string {
    if (error.code === error.PERMISSION_DENIED) {
      return 'No se concedió permiso de ubicación en el navegador. Habilitalo y reintentá, o usá "Elegir en mapa".';
    }

    if (error.code === error.POSITION_UNAVAILABLE) {
      return 'El dispositivo no pudo obtener una ubicación GPS válida. Podés marcarla manualmente con "Elegir en mapa".';
    }

    if (error.code === error.TIMEOUT) {
      return 'La ubicación tardó demasiado en responder. Reintentá o usá "Elegir en mapa".';
    }

    return 'No se pudo obtener la ubicación actual del dispositivo. Podés usar "Elegir en mapa".';
  }

  private timelineLabelByCommentType(commentType: string): string {
    if (commentType === 'closure') {
      return 'Cierre';
    }
    if (commentType === 'closure_evidence') {
      return 'Evidencia de cierre';
    }
    if (commentType === 'arrival_registration') {
      return 'Llegada al sitio';
    }
    if (commentType === 'system') {
      return 'Sistema';
    }
    return 'Comentario';
  }

  private hasRole(roleKey: string): boolean {
    return this.currentRoles().includes(roleKey);
  }

  private resolveActorRoleIds(): string[] {
    const actorRoles = new Set(this.currentRoles());
    return this.ticketRoles()
      .filter((role) => {
        const normalizedRole = this.normalizeRoleKey(role.role_key);
        return normalizedRole !== null && actorRoles.has(normalizedRole);
      })
      .map((role) => role.crm_role_id);
  }

  private normalizeRoleKey(roleKey: string | null | undefined): string | null {
    if (typeof roleKey !== 'string') {
      return null;
    }

    if (roleKey === 'admin_crm') {
      return 'admin';
    }
    if (roleKey === 'tecnico_campo') {
      return 'tecnico';
    }
    if (roleKey === 'encargado_deposito') {
      return 'deposito';
    }
    return roleKey;
  }

  private formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  private buildSurveyLink(surveyPath: string | null | undefined, token: string): string {
    const normalizedPath = (surveyPath || '').trim();
    if (normalizedPath) {
      const path = normalizedPath.startsWith('/') ? normalizedPath : `/${normalizedPath}`;
      return `${window.location.origin}${path}`;
    }
    return `${window.location.origin}/survey/${token}`;
  }

  private toAbsoluteMediaUrl(path: string | null | undefined): string | null {
    const normalized = path?.trim();
    if (!normalized) {
      return null;
    }

    if (/^https?:/i.test(normalized)) {
      return this.rewriteAbsoluteMediaUrl(normalized);
    }

    if (/^(blob:|data:)/i.test(normalized)) {
      return normalized;
    }

    const slashNormalized = normalized.replace(/\\/g, '/');
    const lowerPath = slashNormalized.toLowerCase();
    const publicMarker = '/public/';
    const publicIndex = lowerPath.lastIndexOf(publicMarker);
    const normalizedPath = this.stripBackendPathPrefix(
      (publicIndex >= 0 ? slashNormalized.slice(publicIndex + publicMarker.length) : slashNormalized)
      .replace(/^\/?public\//i, '')
      .replace(/^\/+/, '')
    );

    if (!normalizedPath || /^[a-z]:\//i.test(normalizedPath)) {
      return null;
    }

    // Ignore opaque ids without path/extension and let caller fall back to other URL fields.
    if (!normalizedPath.includes('/') && !normalizedPath.includes('.')) {
      return null;
    }

    return `${this.backendOrigin}/${normalizedPath}`;
  }

  private rewriteAbsoluteMediaUrl(url: string): string {
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';

    try {
      const backend = new URL(this.backendOrigin, browserOrigin);
      const absolute = new URL(url);

      if (absolute.origin !== backend.origin) {
        return url;
      }

      const backendPath = backend.pathname.replace(/\/+$/, '');
      if (!backendPath || backendPath === '/') {
        return url;
      }

      if (absolute.pathname.startsWith(`${backendPath}/`)) {
        return url;
      }

      if (absolute.pathname.startsWith('/media/')) {
        absolute.pathname = `${backendPath}${absolute.pathname}`;
        return absolute.toString();
      }

      return url;
    } catch {
      return url;
    }
  }

  private stripBackendPathPrefix(normalizedPath: string): string {
    const backendPathPrefix = this.backendPathPrefix();
    if (!backendPathPrefix) {
      return normalizedPath;
    }

    const lowerPath = normalizedPath.toLowerCase();
    const lowerPrefix = `${backendPathPrefix.toLowerCase()}/`;
    if (lowerPath === backendPathPrefix.toLowerCase()) {
      return '';
    }

    if (lowerPath.startsWith(lowerPrefix)) {
      return normalizedPath.slice(backendPathPrefix.length + 1);
    }

    return normalizedPath;
  }

  private backendPathPrefix(): string {
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';

    try {
      const parsed = new URL(this.backendOrigin, browserOrigin);
      return parsed.pathname.replace(/^\/+|\/+$/g, '');
    } catch {
      return '';
    }
  }

  private resolveBackendOrigin(): string {
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
    const normalizedBaseUrl = (crmApiConfig.baseUrl || '').trim();

    if (!normalizedBaseUrl) {
      return browserOrigin;
    }

    try {
      const parsed = new URL(normalizedBaseUrl, browserOrigin);
      const normalizedPath = parsed.pathname.replace(/\/+$/, '');
      return normalizedPath ? `${parsed.origin}${normalizedPath}` : parsed.origin;
    } catch {
      return browserOrigin;
    }
  }

  private ticketId(): string {
    return this.activatedRoute.snapshot.paramMap.get('ticketId') ?? '';
  }
}