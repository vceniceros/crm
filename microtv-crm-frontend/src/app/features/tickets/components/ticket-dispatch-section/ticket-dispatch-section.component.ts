import { Component, inject, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { InventoryItemOption } from '../../../../core/models/inventory-item.model';
import { TicketDispatchItem } from '../../../../core/models/ticket-dispatch.model';
import { TicketInventoryRequest } from '../../../../core/models/ticket-inventory-request.model';

@Component({
  selector: 'app-ticket-dispatch-section',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, ReactiveFormsModule],
  templateUrl: './ticket-dispatch-section.component.html',
  styleUrl: './ticket-dispatch-section.component.scss'
})
export class TicketDispatchSectionComponent {
  private readonly formBuilder = inject(FormBuilder);

  readonly inventoryOptions = input.required<readonly InventoryItemOption[]>();
  readonly requests = input.required<readonly TicketInventoryRequest[]>();
  readonly dispatchedItems = input.required<readonly TicketDispatchItem[]>();
  readonly canManageDispatch = input(false);
  readonly dispatchCreated = output<TicketDispatchItem>();

  readonly dispatchForm = this.formBuilder.group({
    inventoryItemId: this.formBuilder.control<number | string | null>(null, Validators.required),
    quantity: this.formBuilder.control(1, {
      validators: [Validators.required, Validators.min(1)],
      nonNullable: true
    })
  });

  approvedRequestCount(): number {
    return this.requests().filter((request) => request.status === 'approved').length;
  }

  createDispatch(): void {
    if (this.dispatchForm.invalid) {
      this.dispatchForm.markAllAsTouched();
      return;
    }

    const inventoryItemId = this.dispatchForm.controls.inventoryItemId.getRawValue();
    const selectedItem = this.inventoryOptions().find((item) => item.id === inventoryItemId);

    if (!selectedItem) {
      return;
    }

    this.dispatchCreated.emit({
      inventoryItemId: selectedItem.id,
      inventoryItemName: selectedItem.name,
      quantity: this.dispatchForm.controls.quantity.getRawValue()
    });

    this.dispatchForm.reset({ inventoryItemId: null, quantity: 1 });
  }
}