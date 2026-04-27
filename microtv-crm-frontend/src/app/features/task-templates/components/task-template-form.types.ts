import { FormArray, FormControl, FormGroup } from '@angular/forms';

export interface TemplateSubtaskFormModel {
  id: FormControl<string>;
  title: FormControl<string>;
  children: FormArray<TemplateSubtaskFormGroup>;
}

export type TemplateSubtaskFormGroup = FormGroup<TemplateSubtaskFormModel>;

export interface TemplateRequiredMaterialFormModel {
  materialId: FormControl<number | string>;
  name: FormControl<string>;
  quantity: FormControl<number>;
  unit: FormControl<string>;
}

export type TemplateRequiredMaterialFormGroup = FormGroup<TemplateRequiredMaterialFormModel>;

export interface CreateTemplateFormModel {
  title: FormControl<string>;
  description: FormControl<string>;
  subtasks: FormArray<TemplateSubtaskFormGroup>;
  requiredMaterials: FormArray<TemplateRequiredMaterialFormGroup>;
}

export type CreateTemplateFormGroup = FormGroup<CreateTemplateFormModel>;