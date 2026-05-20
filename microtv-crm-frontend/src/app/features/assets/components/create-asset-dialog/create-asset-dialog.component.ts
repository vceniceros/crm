import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { Asset, AssetCategory, AssetSummary } from '../../../../core/models/asset.model';
import { ClientItem } from '../../../../core/models/client.model';
import { AssetManagementService } from '../../../../core/services/asset-management.service';
import { ClientsService } from '../../../../core/services/clients.service';

export interface AssetDialogData {
  existingAsset?: Asset | null;
  clientId?: string | null;
}

@Component({
  selector: 'app-create-asset-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  templateUrl: './create-asset-dialog.component.html',
  styleUrl: './create-asset-dialog.component.scss'
})
export class CreateAssetDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<CreateAssetDialogComponent, Asset>);
  private readonly assetService = inject(AssetManagementService);
  private readonly clientsService = inject(ClientsService);
  private readonly data = inject<AssetDialogData>(MAT_DIALOG_DATA);

  readonly categories = signal<AssetCategory[]>([]);
  readonly clients = signal<ClientItem[]>([]);
  readonly parentAssetOptions = signal<AssetSummary[]>([]);
  readonly selectedCategory = signal<AssetCategory | null>(null);
  readonly existingAsset = this.data.existingAsset ?? null;
  readonly isEdit = Boolean(this.existingAsset);
  readonly selectedClientId = signal<string>(this.existingAsset?.client_id ?? this.data.clientId ?? '');

  readonly form = this.fb.group({
    category_id: [{ value: this.existingAsset?.category_id ?? '', disabled: this.isEdit }, Validators.required],
    client_id: [{ value: this.existingAsset?.client_id ?? this.data.clientId ?? '', disabled: this.isEdit }, Validators.required],
    asset_name: [this.existingAsset?.asset_name ?? '', Validators.required],
    parent_asset_id: [this.existingAsset?.parent_asset_id ?? ''],
    notes: [this.existingAsset?.notes ?? '']
  });

  readonly fieldValues = this.fb.group<Record<string, ReturnType<FormBuilder['control']>>>({});

  constructor() {
    this.clientsService.clients$.subscribe((clients) => this.clients.set(clients));
    this.clientsService.refresh().subscribe({ error: () => undefined });
    this.assetService.listAssets().subscribe((assets) => this.parentAssetOptions.set(assets));
    this.assetService.listCategories().subscribe((categories) => {
      this.categories.set(categories);
      const categoryId = this.existingAsset?.category_id || this.form.controls.category_id.value;
      const selected = categories.find((category) => category.asset_category_id === categoryId) ?? null;
      if (selected) {
        this.selectCategory(selected.asset_category_id);
      }
    });
    this.form.controls.category_id.valueChanges.subscribe((categoryId) => {
      if (categoryId) {
        this.selectCategory(categoryId);
      }
    });
    this.form.controls.client_id.valueChanges.subscribe((clientId) => this.selectedClientId.set(clientId || ''));
  }

  readonly availableParentAssets = () => {
    return this.parentAssetOptions().filter((asset) => {
      if (this.existingAsset?.asset_id === asset.asset_id) {
        return false;
      }
      return true;
    });
  };

  clientNameForId(clientId: string | null | undefined): string {
    if (!clientId) {
      return '';
    }
    return this.clients().find((client) => String(client.id) === clientId)?.razonSocial ?? clientId;
  }

  assetOptionLabel(asset: AssetSummary): string {
    return `${asset.asset_name} - ${asset.client_name}`;
  }

  save(): void {
    if (this.form.invalid || !this.selectedCategory()) {
      this.form.markAllAsTouched();
      return;
    }
    const formValue = this.form.getRawValue();
    const field_values = this.selectedCategory()!.fields.map((field) => ({
      field_id: field.field_id,
      value: String(this.fieldValues.controls[field.field_id]?.value ?? '')
    }));

    const payload = {
      asset_name: formValue.asset_name || '',
      notes: formValue.notes?.trim() || null,
      parent_asset_id: formValue.parent_asset_id || null,
      field_values
    };

    const request$ = this.existingAsset
      ? this.assetService.updateAsset(this.existingAsset.asset_id, payload)
      : this.assetService.createAsset({
          ...payload,
          category_id: formValue.category_id || '',
          client_id: formValue.client_id || ''
        });

    request$.subscribe((asset) => this.dialogRef.close(asset));
  }

  private selectCategory(categoryId: string): void {
    const category = this.categories().find((item) => item.asset_category_id === categoryId) ?? null;
    this.selectedCategory.set(category);
    if (!category) {
      return;
    }
    for (const field of category.fields) {
      if (!this.fieldValues.controls[field.field_id]) {
        const existingValue = this.existingAsset?.field_values.find((value) => value.field_id === field.field_id)?.raw_value ?? '';
        this.fieldValues.addControl(field.field_id, this.fb.control(existingValue, field.is_required ? Validators.required : null));
      }
    }
  }
}
