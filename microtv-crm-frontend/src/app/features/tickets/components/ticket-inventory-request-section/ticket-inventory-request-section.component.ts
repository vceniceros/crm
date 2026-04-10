import { DatePipe } from '@angular/common';
import { Component, inject, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { InventoryItemOption } from '../../../../core/models/inventory-item.model';
import { TicketInventoryRequest, TicketInventoryRequestItem, TicketInventoryRequestStatus } from '../../../../core/models/ticket-inventory-request.model';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';

@Component({
  selector: 'app-ticket-inventory-request-section',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
    StatusBadgeComponent
  ],
  templateUrl: './ticket-inventory-request-section.component.html',
  styleUrl: './ticket-inventory-request-section.component.scss'
})
export class TicketInventoryRequestSectionComponent {
  private readonly formBuilder = inject(FormBuilder);

  readonly inventoryOptions = input.required<readonly InventoryItemOption[]>();
  readonly requests = input.required<readonly TicketInventoryRequest[]>();
  readonly canCreateRequest = input(false);
  readonly canReviewRequests = input(false);
  readonly requestCreated = output<readonly TicketInventoryRequestItem[]>();
  readonly requestDecision = output<{ requestId: string; status: TicketInventoryRequestStatus; comment: string }>();

  readonly itemForm = this.formBuilder.group({
    inventoryItemId: this.formBuilder.control<number | string | null>(null, Validators.required),
    quantity: this.formBuilder.control(1, {
      validators: [Validators.required, Validators.min(1)],
      nonNullable: true
    })
  });

  draftItems: TicketInventoryRequestItem[] = [];
  private readonly decisionCommentByRequestId: Record<string, string> = {};

  addDraftItem(): void {
    if (this.itemForm.invalid) {
      this.itemForm.markAllAsTouched();
      return;
    }

    const inventoryItemId = this.itemForm.controls.inventoryItemId.getRawValue();
    const selectedItem = this.inventoryOptions().find((item) => item.id === inventoryItemId);

    if (!selectedItem || this.isDraftSelected(selectedItem.id)) {
      return;
    }

    this.draftItems = [
      ...this.draftItems,
      {
        inventoryItemId: selectedItem.id,
        inventoryItemName: selectedItem.name,
        quantity: this.itemForm.controls.quantity.getRawValue()
      }
    ];

    this.itemForm.reset({ inventoryItemId: null, quantity: 1 });
  }

  removeDraftItem(inventoryItemId: number | string): void {
    this.draftItems = this.draftItems.filter((item) => item.inventoryItemId !== inventoryItemId);
  }

  submitRequest(): void {
    if (!this.draftItems.length) {
      return;
    }

    this.requestCreated.emit(this.draftItems.map((item) => ({ ...item })));
    this.draftItems = [];
    this.itemForm.reset({ inventoryItemId: null, quantity: 1 });
  }

  updateDecisionComment(requestId: string, event: Event): void {
    const target = event.target;

    if (target instanceof HTMLTextAreaElement) {
      this.decisionCommentByRequestId[requestId] = target.value;
    }
  }

  decideRequest(requestId: string, status: TicketInventoryRequestStatus): void {
    this.requestDecision.emit({
      requestId,
      status,
      comment: this.decisionCommentByRequestId[requestId] ?? ''
    });
  }

  isDraftSelected(inventoryItemId: number | string): boolean {
    return this.draftItems.some((item) => item.inventoryItemId === inventoryItemId);
  }

  trackDraftItem(_: number, item: TicketInventoryRequestItem): number | string {
    return item.inventoryItemId;
  }

  statusTone(status: TicketInventoryRequestStatus): 'neutral' | 'warning' | 'success' {
    if (status === 'approved') {
      return 'success';
    }

    if (status === 'rejected') {
      return 'warning';
    }

    return 'neutral';
  }

  statusLabel(status: TicketInventoryRequestStatus): string {
    if (status === 'approved') {
      return 'Autorizada';
    }

    if (status === 'rejected') {
      return 'Rechazada';
    }

    return 'Pendiente';
  }

  decisionComment(requestId: string): string {
    return this.decisionCommentByRequestId[requestId] ?? '';
  }
}