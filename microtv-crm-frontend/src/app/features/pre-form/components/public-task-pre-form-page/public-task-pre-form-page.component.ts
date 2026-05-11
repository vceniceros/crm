import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { TaskPreFormField, TaskPreFormFieldType } from '../../../../core/models/task-management.model';
import { TaskManagementService } from '../../../../core/services/task-management.service';

@Component({
  selector: 'app-public-task-pre-form-page',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './public-task-pre-form-page.component.html',
  styleUrl: './public-task-pre-form-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PublicTaskPreFormPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly taskService = inject(TaskManagementService);
  private readonly fb = inject(FormBuilder);

  readonly token = signal('');
  readonly isLoading = signal(true);
  readonly isSubmitting = signal(false);
  readonly isSubmitted = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly formInfo = signal<{
    task_title: string;
    client_name: string | null;
    location_name: string | null;
    title: string | null;
    instructions: string | null;
    fields: TaskPreFormField[];
  } | null>(null);

  readonly preForm = this.fb.group({});

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('token') ?? '';
    this.token.set(token);

    if (!token) {
      this.errorMessage.set('Token inválido o formulario no encontrado.');
      this.isLoading.set(false);
      return;
    }

    this.taskService.getPublicTaskPreForm(token).subscribe({
      next: (info) => {
        this.formInfo.set(info);
        this.buildDynamicForm(info.fields);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('El formulario previo indicado no existe, expiró o ya fue utilizado.');
        this.isLoading.set(false);
      },
    });
  }

  fieldControlName(field: TaskPreFormField): string {
    return field.field_id;
  }

  isCheckboxField(field: TaskPreFormField): boolean {
    return field.field_type === 'CHECKBOX';
  }

  inputType(fieldType: TaskPreFormFieldType): string {
    if (fieldType === 'NUMBER') {
      return 'number';
    }
    if (fieldType === 'DATE') {
      return 'date';
    }
    if (fieldType === 'TEL') {
      return 'tel';
    }
    return 'text';
  }

  onSubmit(): void {
    const info = this.formInfo();
    if (!info) {
      return;
    }

    if (this.preForm.invalid) {
      this.preForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    const values = info.fields.map((field) => {
      const value = this.preForm.get(field.field_id)?.value;
      if (field.field_type === 'CHECKBOX') {
        return {
          field_id: field.field_id,
          text_value: value ? 'true' : 'false',
        };
      }

      return {
        field_id: field.field_id,
        text_value: String(value ?? '').trim() || null,
      };
    });

    this.taskService.submitPublicTaskPreForm(this.token(), { values }).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.isSubmitted.set(true);
      },
      error: (err: Error) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(err.message ?? 'No se pudo enviar el formulario previo.');
      },
    });
  }

  private buildDynamicForm(fields: TaskPreFormField[]): void {
    fields
      .slice()
      .sort((left, right) => left.order_index - right.order_index)
      .forEach((field) => {
        const validators = field.is_required ? [Validators.required] : [];
        if (field.field_type === 'CHECKBOX') {
          this.preForm.addControl(field.field_id, this.fb.control(false, { nonNullable: true, validators }));
          return;
        }

        this.preForm.addControl(field.field_id, this.fb.control<string>('', { nonNullable: true, validators }));
      });
  }
}
