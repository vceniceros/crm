import { FormControl, FormGroup } from '@angular/forms';

export interface CreateProductFormModel {
  name: FormControl<string>;
  productCode: FormControl<string>;
  categoryId: FormControl<string | null>;
  initialStock: FormControl<number | null>;
  minimumStock: FormControl<number>;
  requiresTracking: FormControl<boolean>;
}

export type CreateProductFormGroup = FormGroup<CreateProductFormModel>;