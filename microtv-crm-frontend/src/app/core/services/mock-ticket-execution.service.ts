import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, combineLatest, map, of, shareReplay } from 'rxjs';

import { InventoryItemOption, InventoryItemsMockData } from '../models/inventory-item.model';
import { TicketAttachment, TicketAttachmentKind } from '../models/ticket-attachment.model';
import { TicketDispatchItem } from '../models/ticket-dispatch.model';
import {
  TicketExecutionData,
  TicketExecutionDefinition,
  TicketExecutionItem,
  TicketExecutionPermissions,
  TicketExecutionState,
  TicketExecutionStateData
} from '../models/ticket-execution.model';
import { TicketInventoryRequest, TicketInventoryRequestItem, TicketInventoryRequestStatus } from '../models/ticket-inventory-request.model';
import { TicketListItem } from '../models/ticket.model';
import { MockUserProfile, MockUserContextService } from './mock-user-context.service';
import { MockAccessControlService } from './mock-access-control.service';
import { MockTicketExecutionStorageService } from './mock-ticket-execution-storage.service';
import inventoryItemsData from '../../../mocks/inventory-items-data.json';
import ticketExecutionData from '../../../mocks/ticket-execution-data.json';
import ticketExecutionStateData from '../../../mocks/ticket-execution-state-data.json';

@Injectable({ providedIn: 'root' })
export class MockTicketExecutionService {
  private readonly mockUserContextService = inject(MockUserContextService);
  private readonly mockAccessControlService = inject(MockAccessControlService);
  private readonly ticketExecutionStorageService = inject(MockTicketExecutionStorageService);
  private readonly ticketDefinitions = (ticketExecutionData as TicketExecutionData).tickets;
  private readonly initialExecutionState = (ticketExecutionStateData as TicketExecutionStateData).execution;
  private readonly executionStateSubject = new BehaviorSubject<Record<string, TicketExecutionState>>({});

  readonly inventoryItems$ = of((inventoryItemsData as InventoryItemsMockData).items).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly ticketSummaries$ = combineLatest([
    of(this.ticketDefinitions),
    this.executionStateSubject.asObservable(),
    this.mockUserContextService.activeUser()
  ]).pipe(
    map(([tickets, executionByTicketId, user]) =>
      tickets
        .filter((ticket) => this.mockAccessControlService.canUserViewTicketExecution(user, ticket.technicianAssigneeId, ticket.depositAssigneeId))
        .map((ticket) => this.buildTicketListItem(ticket, this.getExecutionState(ticket.id, executionByTicketId)))
    ),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  constructor() {
    this.ticketExecutionStorageService.initialize(this.initialExecutionState);
    this.executionStateSubject.next(this.buildExecutionRecord(this.ticketExecutionStorageService.getAllExecutionState()));
  }

  getTicketExecution(ticketId: string) {
    return combineLatest([
      of(this.ticketDefinitions),
      this.executionStateSubject.asObservable(),
      this.mockUserContextService.activeUser()
    ]).pipe(
      map(([tickets, executionByTicketId, user]) => {
        const ticket = tickets.find((item) => item.id === ticketId);

        if (!ticket || !this.mockAccessControlService.canUserViewTicketExecution(user, ticket.technicianAssigneeId, ticket.depositAssigneeId)) {
          return null;
        }

        return this.buildTicketExecutionItem(ticket, this.getExecutionState(ticket.id, executionByTicketId), user);
      })
    );
  }

  updateResolutionComment(ticketId: string, comment: string): boolean {
    const ticket = this.findTicket(ticketId);
    const user = this.currentUser();

    if (!ticket || !this.mockAccessControlService.canUserEditTicketResolution(user, ticket.technicianAssigneeId)) {
      return false;
    }

    const state = this.cloneExecutionState(this.currentExecutionState(ticketId));
    state.resolutionComment = comment;
    state.resolutionUpdatedAt = new Date().toISOString();
    state.updatedAt = state.resolutionUpdatedAt;
    this.persistExecutionState(state);
    return true;
  }

  addAttachments(ticketId: string, files: readonly File[]): boolean {
    const ticket = this.findTicket(ticketId);
    const user = this.currentUser();

    if (!ticket || !files.length || !this.mockAccessControlService.canUserManageTicketAttachments(user, ticket.technicianAssigneeId)) {
      return false;
    }

    const state = this.cloneExecutionState(this.currentExecutionState(ticketId));
    const nextAttachments = files.map((file, index) => this.createAttachmentFromFile(file, ticketId, index));
    state.attachments = [...state.attachments, ...nextAttachments];
    state.updatedAt = new Date().toISOString();
    this.persistExecutionState(state);
    return true;
  }

  removeAttachment(ticketId: string, attachmentId: string): boolean {
    const ticket = this.findTicket(ticketId);
    const user = this.currentUser();

    if (!ticket || !this.mockAccessControlService.canUserManageTicketAttachments(user, ticket.technicianAssigneeId)) {
      return false;
    }

    const state = this.cloneExecutionState(this.currentExecutionState(ticketId));
    const attachment = state.attachments.find((item) => item.id === attachmentId);

    if (!attachment) {
      return false;
    }

    this.revokePreviewUrl(attachment.previewUrl);
    state.attachments = state.attachments.filter((item) => item.id !== attachmentId);
    state.updatedAt = new Date().toISOString();
    this.persistExecutionState(state);
    return true;
  }

  createInventoryRequest(ticketId: string, items: readonly TicketInventoryRequestItem[]): boolean {
    const ticket = this.findTicket(ticketId);
    const user = this.currentUser();

    if (!ticket || !items.length || !this.mockAccessControlService.canUserCreateTicketInventoryRequests(user, ticket.technicianAssigneeId)) {
      return false;
    }

    const state = this.cloneExecutionState(this.currentExecutionState(ticketId));
    const request: TicketInventoryRequest = {
      id: `${ticketId}-req-${Date.now()}`,
      requestedByUserId: user.id,
      requestedByUserName: user.name,
      requestedAt: new Date().toISOString(),
      status: 'pending_deposit_review',
      items: items.map((item) => ({ ...item }))
    };

    state.inventoryRequests = [request, ...state.inventoryRequests];
    state.updatedAt = request.requestedAt;
    this.persistExecutionState(state);
    return true;
  }

  decideInventoryRequest(ticketId: string, requestId: string, status: TicketInventoryRequestStatus, comment: string): boolean {
    const ticket = this.findTicket(ticketId);
    const user = this.currentUser();

    if (
      !ticket ||
      (status !== 'approved_for_dispatch' && status !== 'rejected') ||
      !this.mockAccessControlService.canUserReviewTicketInventoryRequests(user, ticket.depositAssigneeId)
    ) {
      return false;
    }

    const state = this.cloneExecutionState(this.currentExecutionState(ticketId));
    const nextRequests = state.inventoryRequests.map((request) =>
      request.id === requestId && request.status === 'pending_deposit_review'
        ? {
            ...request,
            status,
            depositDecisionComment: comment.trim() || undefined
          }
        : request
    );

    if (nextRequests === state.inventoryRequests) {
      return false;
    }

    state.inventoryRequests = nextRequests;
    state.updatedAt = new Date().toISOString();
    this.persistExecutionState(state);
    return true;
  }

  addDispatchItem(ticketId: string, dispatchItem: TicketDispatchItem): boolean {
    const ticket = this.findTicket(ticketId);
    const user = this.currentUser();

    if (!ticket || !this.mockAccessControlService.canUserManageTicketDispatch(user, ticket.depositAssigneeId)) {
      return false;
    }

    const quantity = Math.max(1, Math.trunc(dispatchItem.quantity));

    if (!dispatchItem.inventoryItemId || !dispatchItem.inventoryItemName || !quantity) {
      return false;
    }

    const state = this.cloneExecutionState(this.currentExecutionState(ticketId));
    state.dispatchedItems = [
      {
        inventoryItemId: dispatchItem.inventoryItemId,
        inventoryItemName: dispatchItem.inventoryItemName,
        quantity
      },
      ...state.dispatchedItems
    ];
    state.updatedAt = new Date().toISOString();
    this.persistExecutionState(state);
    return true;
  }

  private buildTicketExecutionItem(
    ticket: TicketExecutionDefinition,
    state: TicketExecutionState,
    user: MockUserProfile
  ): TicketExecutionItem {
    const permissions = this.resolvePermissions(user, ticket);
    return {
      id: ticket.id,
      title: ticket.title,
      description: ticket.description,
      category: ticket.category,
      affectedDevice: ticket.affectedDevice,
      status: this.resolveStatusLabel(ticket, state),
      statusTone: this.resolveStatusTone(ticket, state),
      priority: ticket.priority,
      priorityTone: ticket.priorityTone,
      createdAt: ticket.createdAt,
      assigneeId: ticket.technicianAssigneeId,
      assigneeName: ticket.technicianAssigneeName,
      assigneeInitials: ticket.technicianAssigneeInitials,
      depositAssigneeId: ticket.depositAssigneeId,
      depositAssigneeName: ticket.depositAssigneeName,
      depositAssigneeInitials: ticket.depositAssigneeInitials,
      resolutionNote: {
        comment: state.resolutionComment,
        updatedAt: state.resolutionUpdatedAt
      },
      attachments: state.attachments.map((attachment) => ({ ...attachment })),
      inventoryRequests: state.inventoryRequests.map((request) => ({
        ...request,
        items: request.items.map((item) => ({ ...item }))
      })),
      dispatchedItems: state.dispatchedItems.map((item) => ({ ...item })),
      updatedAt: state.updatedAt,
      permissions
    };
  }

  private buildTicketListItem(ticket: TicketExecutionDefinition, state: TicketExecutionState): TicketListItem {
    return {
      id: ticket.id,
      title: ticket.title,
      category: ticket.category,
      affectedDevice: ticket.affectedDevice,
      status: this.resolveStatusLabel(ticket, state),
      statusTone: this.resolveStatusTone(ticket, state),
      priority: ticket.priority,
      priorityTone: ticket.priorityTone,
      createdAt: ticket.createdAt,
      assigneeId: ticket.technicianAssigneeId,
      assigneeName: ticket.technicianAssigneeName,
      assigneeInitials: ticket.technicianAssigneeInitials
    };
  }

  private resolveStatusLabel(ticket: TicketExecutionDefinition, state: TicketExecutionState): string {
    if (state.dispatchedItems.length > 0) {
      return 'Despacho registrado';
    }

    if (state.inventoryRequests.some((request) => request.status === 'approved_for_dispatch')) {
      return 'Solicitud autorizada';
    }

    if (state.inventoryRequests.some((request) => request.status === 'pending_deposit_review')) {
      return 'Esperando depósito';
    }

    if (state.resolutionComment.trim() || state.attachments.length > 0) {
      return 'En progreso';
    }

    return ticket.status;
  }

  private resolveStatusTone(ticket: TicketExecutionDefinition, state: TicketExecutionState): TicketListItem['statusTone'] {
    if (state.dispatchedItems.length > 0 || state.inventoryRequests.some((request) => request.status === 'approved_for_dispatch')) {
      return 'success';
    }

    if (state.inventoryRequests.some((request) => request.status === 'pending_deposit_review') || state.resolutionComment.trim() || state.attachments.length > 0) {
      return 'progress';
    }

    return ticket.statusTone;
  }

  private resolvePermissions(user: MockUserProfile, ticket: TicketExecutionDefinition): TicketExecutionPermissions {
    return {
      canEditResolution: this.mockAccessControlService.canUserEditTicketResolution(user, ticket.technicianAssigneeId),
      canManageAttachments: this.mockAccessControlService.canUserManageTicketAttachments(user, ticket.technicianAssigneeId),
      canCreateInventoryRequests: this.mockAccessControlService.canUserCreateTicketInventoryRequests(user, ticket.technicianAssigneeId),
      canReviewInventoryRequests: this.mockAccessControlService.canUserReviewTicketInventoryRequests(user, ticket.depositAssigneeId),
      canManageDispatch: this.mockAccessControlService.canUserManageTicketDispatch(user, ticket.depositAssigneeId),
      canViewDispatch: this.mockAccessControlService.canUserViewTicketDispatch(user, ticket.depositAssigneeId)
    };
  }

  private getExecutionState(ticketId: string, executionByTicketId: Record<string, TicketExecutionState>): TicketExecutionState {
    return executionByTicketId[ticketId] ? this.cloneExecutionState(executionByTicketId[ticketId]) : this.createEmptyExecutionState(ticketId);
  }

  private currentExecutionState(ticketId: string): TicketExecutionState {
    return this.getExecutionState(ticketId, this.executionStateSubject.value);
  }

  private createEmptyExecutionState(ticketId: string): TicketExecutionState {
    return {
      ticketId,
      resolutionComment: '',
      resolutionUpdatedAt: '',
      attachments: [],
      inventoryRequests: [],
      dispatchedItems: [],
      updatedAt: ''
    };
  }

  private persistExecutionState(state: TicketExecutionState): void {
    const nextExecutionByTicketId = {
      ...this.executionStateSubject.value,
      [state.ticketId]: this.cloneExecutionState(state)
    };

    this.executionStateSubject.next(nextExecutionByTicketId);
    this.ticketExecutionStorageService.saveExecutionState(state);
  }

  private createAttachmentFromFile(file: File, ticketId: string, index: number): TicketAttachment {
    const kind = this.resolveAttachmentKind(file.type);
    const previewUrl = kind === 'image' || kind === 'video' ? URL.createObjectURL(file) : null;

    return {
      id: `${ticketId}-${Date.now()}-${index}`,
      fileName: file.name,
      fileType: file.type || 'application/octet-stream',
      kind,
      previewUrl,
      size: file.size
    };
  }

  private resolveAttachmentKind(fileType: string): TicketAttachmentKind {
    if (fileType.startsWith('image/')) {
      return 'image';
    }

    if (fileType.startsWith('video/')) {
      return 'video';
    }

    return 'other';
  }

  private buildExecutionRecord(states: readonly TicketExecutionState[]): Record<string, TicketExecutionState> {
    return states.reduce<Record<string, TicketExecutionState>>((record, state) => {
      record[state.ticketId] = this.cloneExecutionState(state);
      return record;
    }, {});
  }

  private cloneExecutionState(state: TicketExecutionState): TicketExecutionState {
    return {
      ticketId: state.ticketId,
      resolutionComment: state.resolutionComment,
      resolutionUpdatedAt: state.resolutionUpdatedAt,
      attachments: state.attachments.map((attachment) => ({ ...attachment })),
      inventoryRequests: state.inventoryRequests.map((request) => ({
        ...request,
        items: request.items.map((item) => ({ ...item }))
      })),
      dispatchedItems: state.dispatchedItems.map((item) => ({ ...item })),
      updatedAt: state.updatedAt
    };
  }

  private findTicket(ticketId: string): TicketExecutionDefinition | undefined {
    return this.ticketDefinitions.find((ticket) => ticket.id === ticketId);
  }

  private currentUser(): MockUserProfile {
    return this.mockUserContextService.getActiveUserSnapshot();
  }

  private revokePreviewUrl(previewUrl: string | null | undefined): void {
    if (previewUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl);
    }
  }
}