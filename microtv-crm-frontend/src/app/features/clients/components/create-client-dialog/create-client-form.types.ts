import { FormControl, FormGroup } from '@angular/forms';

export interface CreateClientFormModel {
  razonSocial: FormControl<string>;
  cuit: FormControl<string>;
  email: FormControl<string>;
  telefono: FormControl<string>;
  isActive: FormControl<boolean>;
}

export type CreateClientFormGroup = FormGroup<CreateClientFormModel>;