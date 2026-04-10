import { FormControl, FormGroup } from '@angular/forms';

export interface CreateProductFormModel {
  name: FormControl<string>;
  categoryId: FormControl<number | string | null>;
  imageUrl: FormControl<string>;
  initialStock: FormControl<number | null>;
}

export type CreateProductFormGroup = FormGroup<CreateProductFormModel>;