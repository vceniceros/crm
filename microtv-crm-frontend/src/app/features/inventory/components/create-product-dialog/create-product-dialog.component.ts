import { AsyncPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { CreateInventoryProductFormValue, UpdateInventoryProductFormValue } from '../../../../core/models/create-product.model';
import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { InventoryService } from '../../../../core/services/inventory.service';
import { optimizeImageForUpload } from '../../../../core/utils/media-upload-optimization';
import { CreateProductFormGroup, CreateProductFormModel } from '../create-product-form.types';

export interface ProductDialogData {
  mode: 'create' | 'edit';
  product?: InventoryProduct;
}

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
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    ReactiveFormsModule
  ],
  templateUrl: './create-product-dialog.component.html',
  styleUrl: './create-product-dialog.component.scss'
})
export class CreateProductDialogComponent {
  private static readonly allowedImageTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);

  private readonly dialogRef = inject(MatDialogRef<CreateProductDialogComponent, InventoryProduct>);
  private readonly data = inject<ProductDialogData | null>(MAT_DIALOG_DATA, { optional: true });
  private readonly formBuilder = inject(FormBuilder);
  private readonly inventoryService = inject(InventoryService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly product = this.data?.mode === 'edit' ? this.data.product ?? null : null;

  readonly categories$ = this.inventoryService.categories$;
  readonly isEditMode = this.data?.mode === 'edit' && Boolean(this.product);
  readonly dialogTitle = this.isEditMode ? 'Editar producto' : 'Cargar nuevo producto';
  readonly introTitle = this.isEditMode ? 'Edición de producto' : 'Alta inicial de producto';
  readonly introCopy = this.isEditMode
    ? 'Actualiza los datos del item, su referencia visual, ubicación y stock actual.'
    : 'Registra un nuevo item del deposito con su categoria, referencia visual y stock de arranque para dejarlo disponible en el listado.';
  readonly stockLabel = this.isEditMode ? 'Stock actual' : 'Stock inicial';
  readonly submitLabel = this.isEditMode ? 'Guardar cambios' : 'Cargar producto';
  readonly shelfOptions = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  readonly isSubmitting = signal(false);
  readonly submissionError = signal<string | null>(null);
  readonly selectedFileName = signal<string | null>(null);
  readonly imageError = signal<string | null>(null);
  private selectedFile: File | null = null;
  readonly form: CreateProductFormGroup = this.formBuilder.group<CreateProductFormModel>({
    name: this.formBuilder.control(this.product?.name ?? '', {
      validators: [Validators.required],
      nonNullable: true
    }),
    productCode: this.formBuilder.control(this.product?.productCode ?? '', {
      validators: [Validators.required],
      nonNullable: true
    }),
    categoryId: this.formBuilder.control<string | null>(this.product?.categoryId ?? null, Validators.required),
    initialStock: this.formBuilder.control<number | null>(this.product?.stock ?? 0, [Validators.required, Validators.min(0)]),
    minimumStock: this.formBuilder.control(this.product?.minimumStock ?? 3, {
      validators: [Validators.required, Validators.min(1)],
      nonNullable: true
    }),
    shelfId: this.formBuilder.control<string | null>(this.product?.shelfId ?? null),
    shelfHeight: this.formBuilder.control<number | null>(this.product?.shelfHeight ?? null, Validators.min(1)),
    requiresTracking: this.formBuilder.control(this.product?.requiresTracking ?? false, { nonNullable: true })
  });

  async onFileSelected(event: Event): Promise<void> {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) {
      return;
    }

    const file = input.files?.item(0) ?? null;
    this.selectedFile = null;
    this.selectedFileName.set(null);
    this.imageError.set(null);

    if (!file) {
      return;
    }
    if (!CreateProductDialogComponent.allowedImageTypes.has(file.type)) {
      this.imageError.set('La imagen debe ser JPG, PNG o WEBP.');
      input.value = '';
      return;
    }

    const optimizedFile = await optimizeImageForUpload(file);
    this.selectedFile = optimizedFile;
    this.selectedFileName.set(optimizedFile.name);
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.submissionError.set(null);

    if (this.isEditMode && this.product) {
      await this.submitUpdate(this.product.productId);
      return;
    }

    const payload: CreateInventoryProductFormValue = {
      name: this.form.controls.name.getRawValue().trim(),
      productCode: this.form.controls.productCode.getRawValue().trim().toUpperCase(),
      categoryId: this.form.controls.categoryId.getRawValue(),
      imageFile: this.selectedFile,
      initialStock: this.form.controls.initialStock.getRawValue(),
      minimumStock: this.form.controls.minimumStock.getRawValue(),
      requiresTracking: this.form.controls.requiresTracking.getRawValue()
    };

    try {
      const product = await firstValueFrom(this.inventoryService.createProduct(payload));
      this.snackBar.open('Producto cargado correctamente.', 'Cerrar', { duration: 2500 });
      this.dialogRef.close(product);
    } catch (error) {
      this.submissionError.set(error instanceof Error ? error.message : 'No se pudo crear el producto.');
    } finally {
      this.isSubmitting.set(false);
    }
  }

  private async submitUpdate(productId: string): Promise<void> {
    const payload: UpdateInventoryProductFormValue = {
      name: this.form.controls.name.getRawValue().trim(),
      productCode: this.form.controls.productCode.getRawValue().trim().toUpperCase(),
      categoryId: this.form.controls.categoryId.getRawValue(),
      imageFile: this.selectedFile,
      currentStock: this.form.controls.initialStock.getRawValue(),
      minimumStock: this.form.controls.minimumStock.getRawValue(),
      shelfId: this.form.controls.shelfId.getRawValue() || null,
      shelfHeight: this.form.controls.shelfHeight.getRawValue(),
      requiresTracking: this.form.controls.requiresTracking.getRawValue()
    };

    try {
      const product = await firstValueFrom(this.inventoryService.updateProduct(productId, payload));
      this.snackBar.open('Producto actualizado correctamente.', 'Cerrar', { duration: 2500 });
      this.dialogRef.close(product);
    } catch (error) {
      this.submissionError.set(error instanceof Error ? error.message : 'No se pudo editar el producto.');
    } finally {
      this.isSubmitting.set(false);
    }
  }
}
