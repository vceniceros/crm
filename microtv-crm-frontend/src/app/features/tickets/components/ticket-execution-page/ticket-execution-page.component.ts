import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { combineLatest, map, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

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
  private readonly mockTicketExecutionService = inject(MockTicketExecutionService);

  readonly viewModel$ = this.activatedRoute.paramMap.pipe(
    map((params) => params.get('ticketId') ?? ''),
    switchMap((ticketId) =>
      combineLatest({
        ticket: this.mockTicketExecutionService.getTicketExecution(ticketId),
        inventoryItems: this.mockTicketExecutionService.inventoryItems$
      })
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
      this.mockTicketExecutionService.createInventoryRequest(ticketId, items);
    }
  }

  decideInventoryRequest(requestId: string, status: TicketInventoryRequestStatus, comment: string): void {
    const ticketId = this.ticketId();

    if (ticketId) {
      this.mockTicketExecutionService.decideInventoryRequest(ticketId, requestId, status, comment);
    }
  }

  registerDispatch(item: TicketDispatchItem): void {
    const ticketId = this.ticketId();

    if (ticketId) {
      this.mockTicketExecutionService.addDispatchItem(ticketId, item);
    }
  }

  private ticketId(): string {
    return this.activatedRoute.snapshot.paramMap.get('ticketId') ?? '';
  }
}