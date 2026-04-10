import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { combineLatest, map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { CreateTicketFormValue } from '../../../../core/models/create-ticket.model';
import { RequiredInventoryItem } from '../../../../core/models/inventory-item.model';
import { MockTicketsService } from '../../../../core/services/mock-tickets.service';
import { CreateTicketFormGroup, CreateTicketFormModel, RequiredInventoryItemFormGroup } from '../create-ticket-form.types';
import { RequiredItemsEditorComponent } from '../required-items-editor/required-items-editor.component';

@Component({
  selector: 'app-create-ticket-dialog',
  standalone: true,
  imports: [
    AsyncPipe,
    MatButtonModule,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogModule,
    MatDialogTitle,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
    RequiredItemsEditorComponent
  ],
  templateUrl: './create-ticket-dialog.component.html',
  styleUrl: './create-ticket-dialog.component.scss'
})
export class CreateTicketDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<CreateTicketDialogComponent, CreateTicketFormValue>);
  private readonly formBuilder = inject(FormBuilder);
  private readonly mockTicketsService = inject(MockTicketsService);

  readonly viewModel$ = combineLatest({
    categories: this.mockTicketsService.categories$,
    priorities: this.mockTicketsService.ticketPriorities$,
    stockDevices: this.mockTicketsService.stockDevices$,
    inventoryItems: this.mockTicketsService.inventoryItems$
  });
  readonly form: CreateTicketFormGroup = this.formBuilder.group<CreateTicketFormModel>({
    title: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    description: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    categoryId: this.formBuilder.control<number | string | null>(null, Validators.required),
    affectedDeviceId: this.formBuilder.control<number | string | null>(null, Validators.required),
    priority: this.formBuilder.control<string | null>(null, Validators.required),
    requiredItems: this.formBuilder.array<RequiredInventoryItemFormGroup>([])
  });

  readonly requiredItems = this.form.controls.requiredItems;

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload: CreateTicketFormValue = {
      title: this.form.controls.title.getRawValue().trim(),
      description: this.form.controls.description.getRawValue().trim(),
      categoryId: this.form.controls.categoryId.getRawValue(),
      affectedDeviceId: this.form.controls.affectedDeviceId.getRawValue(),
      priority: this.form.controls.priority.getRawValue(),
      requiredItems: this.serializeRequiredItems(this.requiredItems)
    };

    this.mockTicketsService
      .createTicket(payload)
      .pipe(map((value) => this.dialogRef.close(value)))
      .subscribe();
  }

  private serializeRequiredItems(items: typeof this.requiredItems): RequiredInventoryItem[] {
    return items.controls.map((item) => ({
      itemId: item.controls.itemId.getRawValue(),
      name: item.controls.name.getRawValue(),
      quantity: item.controls.quantity.getRawValue(),
      unit: item.controls.unit.getRawValue() || undefined
    }));
  }
}