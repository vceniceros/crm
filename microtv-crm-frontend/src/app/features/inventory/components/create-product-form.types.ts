import { FormControl, FormGroup } from '@angular/forms';

export interface CreateProductFormModel {
  name: FormControl<string>;
  productCode: FormControl<string>;
  categoryId: FormControl<string | null>;
  initialStock: FormControl<number | null>;
  minimumStock: FormControl<number>;
  shelfId: FormControl<string | null>;
  shelfHeight: FormControl<number | null>;
  requiresTracking: FormControl<boolean>;
}

export type CreateProductFormGroup = FormGroup<CreateProductFormModel>;
