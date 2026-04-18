import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { BehaviorSubject, catchError, combineLatest, map, of, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { InventorySourceFlow } from '../../../../core/models/inventory-flow.model';
import { InventoryService } from '../../../../core/services/inventory.service';
import { InventoryFlowService } from '../../../../core/services/inventory-flow.service';
import { TicketDispatchItem } from '../../../../core/models/ticket-dispatch.model';
import { TicketInventoryRequestItem, TicketInventoryRequestStatus } from '../../../../core/models/ticket-inventory-request.model';
import { MockTicketExecutionService } from '../../../../core/services/mock-ticket-execution.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';
import { TicketAttachmentsSectionComponent } from '../ticket-attachments-section/ticket-attachments-section.component';
import { TicketDescriptionSectionComponent } from '../ticket-description-section/ticket-description-section.component';
import { TicketDispatchSectionComponent } from '../ticket-dispatch-section/ticket-dispatch-section.component';
import { TicketInventoryRequestSectionComponent } from '../ticket-inventory-request-section/ticket-inventory-request-section.component';
import { TicketResolutionSectionComponent } from '../ticket-resolution-section/ticket-resolution-section.component';

@Component({
  selector: 'app-ticket-execution-page',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    PageTitleComponent,
    PriorityIndicatorComponent,
    RouterLink,
    StatusBadgeComponent,
    TicketAttachmentsSectionComponent,
    TicketDescriptionSectionComponent,
    TicketDispatchSectionComponent,
    TicketInventoryRequestSectionComponent,
    TicketResolutionSectionComponent,
    UserAvatarComponent
  ],
  templateUrl: './ticket-execution-page.component.html',
  styleUrl: './ticket-execution-page.component.scss'
})
export class TicketExecutionPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly inventoryService = inject(InventoryService);
  private readonly inventoryFlowService = inject(InventoryFlowService);
  private readonly mockTicketExecutionService = inject(MockTicketExecutionService);
  private readonly refreshSourceFlow$ = new BehaviorSubject(0);

  constructor() {
    this.inventoryService.refresh().subscribe({ error: () => undefined });
  }

  readonly viewModel$ = this.activatedRoute.paramMap.pipe(
    map((params) => params.get('ticketId') ?? ''),
    switchMap((ticketId) =>
      combineLatest({
        ticket: this.mockTicketExecutionService.getTicketExecution(ticketId),
        inventoryItems: this.inventoryService.products$.pipe(
          map((products) => products.map((product) => ({ id: product.productId, name: product.productName, unit: 'unidad' })))
        ),
        sourceFlow: this.refreshSourceFlow$.pipe(
          switchMap(() =>
            this.inventoryFlowService.getSourceFlow('TICKET', ticketId).pipe(
              catchError(() =>
                of<InventorySourceFlow>({
                  source_type: 'TICKET',
                  source_reference_id: ticketId,
                  requests: [],
                  dispatches: []
                })
              )
            )
          )
        )
      }).pipe(
        map(({ ticket, inventoryItems, sourceFlow }) => ({
          ticket: ticket
            ? {
                ...ticket,
                inventoryRequests: sourceFlow.requests
                  .map((request) => ({
                    id: request.inventory_request_id,
                    requestedByUserId: request.requested_by_crm_user_id,
                    requestedByUserName: request.requested_by_crm_user_id,
                    requestedAt: request.requested_at,
                    status: this.toTicketRequestStatus(request.request_status),
                    requestReason: request.request_reason ?? undefined,
                    items: request.items.map((item) => ({
                      inventoryItemId: item.product_id,
                      inventoryItemName: item.product_name,
                      quantity: item.quantity_requested,
                      notes: item.notes ?? undefined,
                      requiresTracking: item.requires_tracking
                    })),
                    depositDecisionComment: request.review_notes ?? undefined
                  }))
                  .sort((left, right) => right.requestedAt.localeCompare(left.requestedAt)),
                dispatchedItems: sourceFlow.dispatches.flatMap((dispatch) =>
                  dispatch.items.map((item) => ({
                    inventoryItemId: item.product_id,
                    inventoryItemName: item.product_name,
                    quantity: item.quantity_dispatched,
                    serialNumber: item.serial_number ?? undefined,
                    barcodeValue: item.barcode_value ?? undefined,
                    notes: item.notes ?? undefined,
                    requestId: dispatch.request_id ?? undefined,
                    dispatchedAt: dispatch.created_at,
                    requiresTracking: item.requires_tracking,
                    receivedConfirmedAt: item.received_confirmed_at ?? undefined,
                    deliveredConfirmedAt: item.delivered_confirmed_at ?? undefined,
                    installedConfirmedAt: item.installed_confirmed_at ?? undefined
                  }))
                )
              }
            : null,
          inventoryItems
        }))
      )
    )
  );

  updateResolutionComment(comment: string): void {
    const ticketId = this.ticketId();

    if (ticketId) {
      this.mockTicketExecutionService.updateResolutionComment(ticketId, comment);
    }
  }

  addAttachments(files: readonly File[]): void {
    const ticketId = this.ticketId();

    if (ticketId) {
      this.mockTicketExecutionService.addAttachments(ticketId, files);
    }
  }

  removeAttachment(attachmentId: string): void {
    const ticketId = this.ticketId();

    if (ticketId) {
      this.mockTicketExecutionService.removeAttachment(ticketId, attachmentId);
    }
  }

  createInventoryRequest(items: readonly TicketInventoryRequestItem[]): void {
    const ticketId = this.ticketId();

    if (ticketId) {
      this.inventoryFlowService
        .createRequest({
          source_type: 'TICKET',
          external_ticket_id: ticketId,
          request_reason: null,
          items: items.map((item) => ({
            product_id: String(item.inventoryItemId),
            quantity_requested: item.quantity,
            notes: item.notes ?? null
          }))
        })
        .subscribe({ next: () => this.refreshSourceFlow$.next(this.refreshSourceFlow$.value + 1), error: () => undefined });
    }
  }

  decideInventoryRequest(requestId: string, status: TicketInventoryRequestStatus, comment: string): void {
    const ticketId = this.ticketId();

    if (ticketId) {
      this.inventoryFlowService
        .reviewRequest(requestId, {
          status: status === 'approved' ? 'APPROVED' : 'REJECTED',
          review_notes: comment || null
        })
        .subscribe({ next: () => this.refreshSourceFlow$.next(this.refreshSourceFlow$.value + 1), error: () => undefined });
    }
  }

  registerDispatch(item: TicketDispatchItem): void {
    const ticketId = this.ticketId();

    if (ticketId && item.requestId) {
      this.inventoryFlowService
        .dispatchRequest(item.requestId, {
          dispatch_notes: item.notes ?? null,
          items: [
            {
              product_id: String(item.inventoryItemId),
              quantity_dispatched: item.quantity,
              serial_number: item.serialNumber ?? null,
              barcode_value: item.barcodeValue ?? null,
              notes: item.notes ?? null
            }
          ]
        })
        .subscribe({ next: () => this.refreshSourceFlow$.next(this.refreshSourceFlow$.value + 1), error: () => undefined });
    }
  }

  private toTicketRequestStatus(status: string): TicketInventoryRequestStatus {
    switch (status) {
      case 'APPROVED':
        return 'approved';
      case 'REJECTED':
        return 'rejected';
      case 'CANCELLED':
        return 'cancelled';
      default:
        return 'pending';
    }
  }

  private ticketId(): string {
    return this.activatedRoute.snapshot.paramMap.get('ticketId') ?? '';
  }
}