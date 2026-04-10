import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { CreateInventoryProductFormValue } from '../../../../core/models/create-product.model';
import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { MockInventoryService } from '../../../../core/services/mock-inventory.service';
import { CreateProductFormGroup, CreateProductFormModel } from '../create-product-form.types';

@Component({
  selector: 'app-create-product-dialog',
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
    ReactiveFormsModule
  ],
  templateUrl: './create-product-dialog.component.html',
  styleUrl: './create-product-dialog.component.scss'
})
export class CreateProductDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<CreateProductDialogComponent, InventoryProduct>);
  private readonly formBuilder = inject(FormBuilder);
  private readonly mockInventoryService = inject(MockInventoryService);

  readonly categories$ = this.mockInventoryService.categories$;
  readonly form: CreateProductFormGroup = this.formBuilder.group<CreateProductFormModel>({
    name: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    categoryId: this.formBuilder.control<number | string | null>(null, Validators.required),
    imageUrl: this.formBuilder.control('', {
      nonNullable: true
    }),
    initialStock: this.formBuilder.control<number | null>(0, [Validators.required, Validators.min(0)])
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload: CreateInventoryProductFormValue = {
      name: this.form.controls.name.getRawValue().trim(),
      categoryId: this.form.controls.categoryId.getRawValue(),
      imageUrl: this.form.controls.imageUrl.getRawValue().trim() || null,
      initialStock: this.form.controls.initialStock.getRawValue()
    };

    this.mockInventoryService
      .createProduct(payload)
      .pipe(map((product) => this.dialogRef.close(product)))
      .subscribe();
  }
}