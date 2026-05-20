import { Component, Inject, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { SettingsCategory, SettingsCategoryWriteRequest, SettingsRole } from '../../../../core/models/settings-management.model';

export interface CategoryEditDialogData {
  item?: SettingsCategory;
  roles: SettingsRole[];
}

@Component({
  selector: 'app-category-edit-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatDialogClose,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule
  ],
  templateUrl: './category-edit-dialog.component.html',
  styleUrl: './category-edit-dialog.component.scss'
})
export class CategoryEditDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<CategoryEditDialogComponent, SettingsCategoryWriteRequest>);
  private readonly fb = inject(FormBuilder);

  readonly form: FormGroup;
  readonly isEdit: boolean;

  readonly periodOptions = [
    { value: 'daily', label: 'Diario' },
    { value: 'weekly', label: 'Semanal' },
    { value: 'biweekly', label: 'Quincenal' },
    { value: 'monthly', label: 'Mensual' },
    { value: 'custom', label: 'Personalizado (semanas)' }
  ];

  readonly weekdayOptions = [
    { value: 1, label: 'Lunes' },
    { value: 2, label: 'Martes' },
    { value: 3, label: 'Miercoles' },
    { value: 4, label: 'Jueves' },
    { value: 5, label: 'Viernes' },
    { value: 6, label: 'Sabado' },
    { value: 7, label: 'Domingo' }
  ];

  constructor(@Inject(MAT_DIALOG_DATA) readonly data: CategoryEditDialogData) {
    const item = data.item;
    this.isEdit = !!item;
    this.form = this.fb.group({
      name: [item?.name ?? '', [Validators.required, Validators.maxLength(120)]],
      description: [item?.description ?? ''],
      is_active: [item?.is_active ?? true],
      default_role_id: [item?.default_role_id ?? null],
      allows_scheduling: [item?.allows_scheduling ?? false],
      schedule_period_type: [item?.schedule_period_type ?? null],
      schedule_interval_weeks: [item?.schedule_interval_weeks ?? null],
      schedule_weekdays_json: [item?.schedule_weekdays_json ?? []],
      schedule_start_date: [item?.schedule_start_date ?? null],
      schedule_end_date: [item?.schedule_end_date ?? null]
    });
  }

  get allowsScheduling(): boolean {
    return this.form.get('allows_scheduling')?.value === true;
  }

  get isCustomPeriod(): boolean {
    return this.form.get('schedule_period_type')?.value === 'custom';
  }

  get usesWeekdays(): boolean {
    return ['daily', 'weekly', 'biweekly', 'custom'].includes(this.form.get('schedule_period_type')?.value);
  }

  submit(): void {
    if (this.form.invalid) return;
    const raw = this.form.getRawValue();
    const payload: SettingsCategoryWriteRequest = {
      name: raw['name'],
      category_type: 'operational',
      description: raw['description'] || null,
      is_active: raw['is_active'],
      default_role_id: raw['default_role_id'] || null,
      allows_scheduling: raw['allows_scheduling'],
      schedule_period_type: raw['allows_scheduling'] ? (raw['schedule_period_type'] || null) : null,
      schedule_interval_weeks: raw['allows_scheduling'] && raw['schedule_period_type'] === 'custom'
        ? (Number(raw['schedule_interval_weeks']) || null) : null,
      schedule_weekdays_json: raw['allows_scheduling'] && this.usesWeekdays
        ? [...(raw['schedule_weekdays_json'] ?? [])].map(Number).sort((left, right) => left - right) : [],
      schedule_start_date: raw['allows_scheduling'] ? (raw['schedule_start_date'] || null) : null,
      schedule_end_date: raw['allows_scheduling'] ? (raw['schedule_end_date'] || null) : null
    };
    this.dialogRef.close(payload);
  }
}
