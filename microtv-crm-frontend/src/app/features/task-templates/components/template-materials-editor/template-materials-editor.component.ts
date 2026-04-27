import { Component, inject, input } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { MaterialOption } from '../../../../core/models/material.model';
import { TemplateRequiredMaterialFormGroup } from '../task-template-form.types';

@Component({
  selector: 'app-template-materials-editor',
  standalone: true,
  imports: [
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule
  ],
  templateUrl: './template-materials-editor.component.html',
  styleUrl: './template-materials-editor.component.scss'
})
export class TemplateMaterialsEditorComponent {
  private readonly formBuilder = inject(FormBuilder);

  readonly requiredMaterials = input.required<FormArray<TemplateRequiredMaterialFormGroup>>();
  readonly materials = input.required<MaterialOption[]>();

  readonly addMaterialForm = this.formBuilder.group({
    materialId: this.formBuilder.control<number | string | null>(null, Validators.required),
    quantity: this.formBuilder.control(1, {
      validators: [Validators.required, Validators.min(1)],
      nonNullable: true
    })
  });

  addMaterial(): void {
    if (this.addMaterialForm.invalid) {
      this.addMaterialForm.markAllAsTouched();
      return;
    }

    const materialId = this.addMaterialForm.controls.materialId.value;
    const quantity = this.addMaterialForm.controls.quantity.getRawValue();
    const selectedMaterial = this.materials().find((material) => material.id === materialId);

    if (!selectedMaterial) {
      return;
    }

    if (this.isSelected(selectedMaterial.id)) {
      this.addMaterialForm.controls.materialId.setErrors({ duplicate: true });
      this.addMaterialForm.controls.materialId.markAsTouched();
      return;
    }

    this.requiredMaterials().push(
      this.formBuilder.group({
        materialId: this.formBuilder.control(selectedMaterial.id, {
          validators: [Validators.required],
          nonNullable: true
        }),
        name: this.formBuilder.control(selectedMaterial.name, {
          validators: [Validators.required],
          nonNullable: true
        }),
        quantity: this.formBuilder.control(quantity, {
          validators: [Validators.required, Validators.min(1)],
          nonNullable: true
        }),
        unit: this.formBuilder.control(selectedMaterial.unit ?? '', {
          nonNullable: true
        })
      })
    );

    this.addMaterialForm.reset({ materialId: null, quantity: 1 });
  }

  removeMaterial(index: number): void {
    this.requiredMaterials().removeAt(index);
    this.requiredMaterials().markAsDirty();
  }

  isSelected(materialId: number | string): boolean {
    return this.requiredMaterials().controls.some((control) => control.controls.materialId.value === materialId);
  }

  trackMaterial(material: TemplateRequiredMaterialFormGroup): number | string {
    return material.controls.materialId.value;
  }
}