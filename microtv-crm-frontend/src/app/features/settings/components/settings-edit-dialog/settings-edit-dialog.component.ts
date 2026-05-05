import { CommonModule } from '@angular/common';
import { Component, Inject, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

export type SettingsDialogKind =
  | 'auth-user'
  | 'role'
  | 'user-roles'
  | 'category'
  | 'priority'
  | 'status'
  | 'template'
  | 'sla'
  | 'notification';

export interface SettingsDialogRoleOption {
  code: string;
  label: string;
}

export interface SettingsEditDialogData {
  kind: SettingsDialogKind;
  title: string;
  submitLabel: string;
  value: Record<string, unknown>;
  authUserMode?: 'create' | 'edit';
  roleOptions?: SettingsDialogRoleOption[];
  priorityOptions?: string[];
}

@Component({
  selector: 'app-settings-edit-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule
  ],
  templateUrl: './settings-edit-dialog.component.html',
  styleUrl: './settings-edit-dialog.component.scss'
})
export class SettingsEditDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<SettingsEditDialogComponent, Record<string, unknown>>);
  private readonly fb = inject(FormBuilder);

  readonly form: FormGroup;

  constructor(@Inject(MAT_DIALOG_DATA) readonly data: SettingsEditDialogData) {
    this.form = this.buildForm(data);
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.dialogRef.close(this.form.getRawValue());
  }

  isAuthUserCreateMode(): boolean {
    return this.data.kind === 'auth-user' && this.data.authUserMode === 'create';
  }

  private buildForm(data: SettingsEditDialogData): FormGroup {
    switch (data.kind) {
      case 'auth-user': {
        const isCreateMode = data.authUserMode === 'create';
        return this.fb.group({
          email: [data.value['email'] ?? '', [Validators.required, Validators.email, Validators.maxLength(255)]],
          display_name: [data.value['display_name'] ?? '', [Validators.required, Validators.maxLength(120)]],
          password: [
            data.value['password'] ?? '',
            isCreateMode ? [Validators.required, Validators.minLength(8)] : []
          ],
          roles: [Array.isArray(data.value['roles']) ? data.value['roles'] : []]
        });
      }
      case 'role':
        return this.fb.group({
          role_label: [data.value['role_label'] ?? '', [Validators.required, Validators.maxLength(100)]],
          description: [data.value['description'] ?? ''],
          is_active: [Boolean(data.value['is_active'] ?? true)]
        });
      case 'user-roles':
        return this.fb.group({
          role_keys: [Array.isArray(data.value['role_keys']) ? data.value['role_keys'] : []]
        });
      case 'category':
        return this.fb.group({
          name: [data.value['name'] ?? '', [Validators.required, Validators.maxLength(120)]],
          category_type: [data.value['category_type'] ?? '', [Validators.required, Validators.maxLength(50)]],
          description: [data.value['description'] ?? ''],
          is_active: [Boolean(data.value['is_active'] ?? true)]
        });
      case 'priority':
        return this.fb.group({
          code: [data.value['code'] ?? '', [Validators.required, Validators.maxLength(40)]],
          name: [data.value['name'] ?? '', [Validators.required, Validators.maxLength(80)]],
          order_index: [Number(data.value['order_index'] ?? 0), [Validators.required, Validators.min(0)]],
          color: [data.value['color'] ?? ''],
          is_active: [Boolean(data.value['is_active'] ?? true)]
        });
      case 'status':
        return this.fb.group({
          code: [data.value['code'] ?? '', [Validators.required, Validators.maxLength(40)]],
          name: [data.value['name'] ?? '', [Validators.required, Validators.maxLength(100)]],
          entity_type: [data.value['entity_type'] ?? 'ticket', [Validators.required, Validators.maxLength(30)]],
          is_final: [Boolean(data.value['is_final'] ?? false)],
          order_index: [Number(data.value['order_index'] ?? 0), [Validators.required, Validators.min(0)]],
          is_active: [Boolean(data.value['is_active'] ?? true)]
        });
      case 'template':
        return this.fb.group({
          template_name: [data.value['template_name'] ?? '', [Validators.required, Validators.maxLength(255)]],
          description: [data.value['description'] ?? ''],
          is_active: [Boolean(data.value['is_active'] ?? true)]
        });
      case 'sla':
        return this.fb.group({
          entity_type: [data.value['entity_type'] ?? 'ticket', [Validators.required, Validators.maxLength(30)]],
          priority_code: [data.value['priority_code'] ?? '', [Validators.required, Validators.maxLength(40)]],
          response_time_minutes: [Number(data.value['response_time_minutes'] ?? 60), [Validators.required, Validators.min(1)]],
          resolution_time_minutes: [Number(data.value['resolution_time_minutes'] ?? 480), [Validators.required, Validators.min(1)]],
          is_active: [Boolean(data.value['is_active'] ?? true)]
        });
      case 'notification':
      default:
        return this.fb.group({
          event_code: [data.value['event_code'] ?? '', [Validators.required, Validators.maxLength(100)]],
          label: [data.value['label'] ?? '', [Validators.required, Validators.maxLength(180)]],
          notify_assigned: [Boolean(data.value['notify_assigned'] ?? true)],
          notify_roles_json: [Array.isArray(data.value['notify_roles_json']) ? data.value['notify_roles_json'] : []],
          is_active: [Boolean(data.value['is_active'] ?? true)]
        });
    }
  }
}
