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

type FileUploadState = 'idle' | 'uploading' | 'uploaded' | 'error';

interface FieldUploadState {
  state: FileUploadState;
  attachmentId: string | null;
  fileName: string | null;
  errorMessage: string | null;
}

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
  readonly fileStates = signal<Record<string, FieldUploadState>>({});
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

  fileState(field: TaskPreFormField): FieldUploadState {
    return this.fileStates()[field.field_id] ?? this.defaultFileState();
  }

  hasPendingUpload(): boolean {
    return Object.values(this.fileStates()).some((state) => state.state === 'uploading');
  }

  onFileSelected(event: Event, field: TaskPreFormField): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    if (!file) {
      return;
    }

    const validationError = this.validateSelectedFile(file);
    if (validationError) {
      this.setFileState(field.field_id, {
        state: 'error',
        attachmentId: null,
        fileName: file.name,
        errorMessage: validationError,
      });
      input.value = '';
      return;
    }

    this.setFileState(field.field_id, {
      state: 'uploading',
      attachmentId: null,
      fileName: file.name,
      errorMessage: null,
    });

    this.taskService.uploadPreFormAttachment(this.token(), field.field_id, file).subscribe({
      next: (attachment) => {
        this.setFileState(field.field_id, {
          state: 'uploaded',
          attachmentId: attachment.attachment_id,
          fileName: file.name,
          errorMessage: null,
        });
      },
      error: (err: Error) => {
        this.setFileState(field.field_id, {
          state: 'error',
          attachmentId: null,
          fileName: file.name,
          errorMessage: err.message ?? 'No se pudo subir la imagen.',
        });
        input.value = '';
      },
    });
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

    const missingRequiredFile = info.fields.find((field) => {
      const state = this.fileState(field);
      return field.field_type === 'FILE' && field.is_required && !state.attachmentId;
    });
    if (missingRequiredFile) {
      this.errorMessage.set(`El campo obligatorio "${missingRequiredFile.label}" requiere una imagen.`);
      return;
    }

    if (this.hasPendingUpload()) {
      this.errorMessage.set('Esperá a que termine la subida de la imagen antes de enviar.');
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    const values = info.fields.map((field) => {
      const value = this.preForm.get(field.field_id)?.value;
      if (field.field_type === 'FILE') {
        return {
          field_id: field.field_id,
          text_value: null,
          file_attachment_id: this.fileState(field).attachmentId,
        };
      }

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
        if (field.field_type === 'FILE') {
          this.preForm.addControl(field.field_id, this.fb.control<string>('', { nonNullable: true }));
          this.setFileState(field.field_id, this.defaultFileState());
          return;
        }
        if (field.field_type === 'CHECKBOX') {
          this.preForm.addControl(field.field_id, this.fb.control(false, { nonNullable: true, validators }));
          return;
        }

        this.preForm.addControl(field.field_id, this.fb.control<string>('', { nonNullable: true, validators }));
      });
  }

  private defaultFileState(): FieldUploadState {
    return {
      state: 'idle',
      attachmentId: null,
      fileName: null,
      errorMessage: null,
    };
  }

  private setFileState(fieldId: string, state: FieldUploadState): void {
    this.fileStates.update((current) => ({
      ...current,
      [fieldId]: state,
    }));
  }

  private validateSelectedFile(file: File): string | null {
    const allowedTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.webp'];
    const hasAllowedExtension = allowedExtensions.some((extension) => file.name.toLowerCase().endsWith(extension));
    if (!allowedTypes.has(file.type) && !hasAllowedExtension) {
      return 'Solo se admiten imágenes JPEG, PNG o WEBP.';
    }
    if (file.size > 8 * 1024 * 1024) {
      return 'La imagen supera el límite permitido de 8 MB.';
    }
    return null;
  }
}
