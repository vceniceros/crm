import { Component, inject, input } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { InventoryItemOption } from '../../../../core/models/inventory-item.model';
import { RequiredInventoryItemFormGroup } from '../create-ticket-form.types';

@Component({
  selector: 'app-required-items-editor',
  standalone: true,
  imports: [
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule
  ],
  templateUrl: './required-items-editor.component.html',
  styleUrl: './required-items-editor.component.scss'
})
export class RequiredItemsEditorComponent {
  private readonly formBuilder = inject(FormBuilder);

  readonly requiredItems = input.required<FormArray<RequiredInventoryItemFormGroup>>();
  readonly items = input.required<InventoryItemOption[]>();

  readonly addItemForm = this.formBuilder.group({
    itemId: this.formBuilder.control<number | string | null>(null, Validators.required),
    quantity: this.formBuilder.control(1, {
      validators: [Validators.required, Validators.min(1)],
      nonNullable: true
    })
  });

  addItem(): void {
    if (this.addItemForm.invalid) {
      this.addItemForm.markAllAsTouched();
      return;
    }

    const itemId = this.addItemForm.controls.itemId.value;
    const quantity = this.addItemForm.controls.quantity.getRawValue();
    const selectedItem = this.items().find((item) => item.id === itemId);

    if (!selectedItem) {
      return;
    }

    if (this.isSelected(selectedItem.id)) {
      this.addItemForm.controls.itemId.setErrors({ duplicate: true });
      this.addItemForm.controls.itemId.markAsTouched();
      return;
    }

    this.requiredItems().push(
      this.formBuilder.group({
        itemId: this.formBuilder.control(selectedItem.id, {
          validators: [Validators.required],
          nonNullable: true
        }),
        name: this.formBuilder.control(selectedItem.name, {
          validators: [Validators.required],
          nonNullable: true
        }),
        quantity: this.formBuilder.control(quantity, {
          validators: [Validators.required, Validators.min(1)],
          nonNullable: true
        }),
        unit: this.formBuilder.control(selectedItem.unit ?? '', {
          nonNullable: true
        })
      })
    );

    this.addItemForm.reset({ itemId: null, quantity: 1 });
  }

  removeItem(index: number): void {
    this.requiredItems().removeAt(index);
    this.requiredItems().markAsDirty();
  }

  isSelected(itemId: number | string): boolean {
    return this.requiredItems().controls.some((control) => control.controls.itemId.value === itemId);
  }

  trackItem(item: RequiredInventoryItemFormGroup): number | string {
    return item.controls.itemId.value;
  }
}