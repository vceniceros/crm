import { FormArray, FormControl, FormGroup } from '@angular/forms';

export interface RequiredInventoryItemFormModel {
  itemId: FormControl<number | string>;
  name: FormControl<string>;
  quantity: FormControl<number>;
  unit: FormControl<string>;
}

export type RequiredInventoryItemFormGroup = FormGroup<RequiredInventoryItemFormModel>;

export interface CreateTicketFormModel {
  title: FormControl<string>;
  description: FormControl<string>;
  categoryId: FormControl<number | string | null>;
  affectedDeviceId: FormControl<number | string | null>;
  priority: FormControl<string | null>;
  requiredItems: FormArray<RequiredInventoryItemFormGroup>;
}

export type CreateTicketFormGroup = FormGroup<CreateTicketFormModel>;