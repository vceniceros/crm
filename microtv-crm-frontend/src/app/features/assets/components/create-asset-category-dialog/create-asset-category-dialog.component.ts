import { Component, inject } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { AssetCategory } from '../../../../core/models/asset.model';
import { AssetManagementService } from '../../../../core/services/asset-management.service';

@Component({
  selector: 'app-create-asset-category-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatCheckboxModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  templateUrl: './create-asset-category-dialog.component.html',
  styleUrl: './create-asset-category-dialog.component.scss'
})
export class CreateAssetCategoryDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<CreateAssetCategoryDialogComponent, AssetCategory>);
  private readonly assetService = inject(AssetManagementService);

  readonly form = this.fb.group({
    category_name: ['', [Validators.required, Validators.maxLength(120)]],
    description: [''],
    fields: this.fb.array([this.createFieldGroup()])
  });

  readonly fieldTypes = [
    { value: 'string', label: 'Texto' },
    { value: 'number', label: 'Numero' }
  ] as const;

  get fields(): FormArray {
    return this.form.controls.fields;
  }

  addField(): void {
    this.fields.push(this.createFieldGroup());
  }

  removeField(index: number): void {
    this.fields.removeAt(index);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.assetService
      .createCategory({
        category_name: value.category_name || '',
        description: value.description?.trim() || null,
        fields: value.fields.map((field, index) => ({
          field_name: field.field_name || '',
          field_type: field.field_type as 'string' | 'number',
          is_required: Boolean(field.is_required),
          order_index: index
        }))
      })
      .subscribe((category) => this.dialogRef.close(category));
  }

  private createFieldGroup() {
    return this.fb.group({
      field_name: ['', Validators.required],
      field_type: ['string', Validators.required],
      is_required: [false]
    });
  }
}
