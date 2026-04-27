import { AsyncPipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { map, startWith } from 'rxjs';

import { CreateTaskFormValue } from '../../../../core/models/create-task.model';
import { MockTaskCreationService } from '../../../../core/services/mock-task-creation.service';

@Component({
  selector: 'app-create-task-dialog',
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
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule
  ],
  templateUrl: './create-task-dialog.component.html',
  styleUrl: './create-task-dialog.component.scss'
})
export class CreateTaskDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<CreateTaskDialogComponent, CreateTaskFormValue>);
  private readonly formBuilder = inject(FormBuilder);
  private readonly mockTaskCreationService = inject(MockTaskCreationService);

  readonly taskCreationData$ = this.mockTaskCreationService.taskCreationData$;
  readonly form = this.formBuilder.group({
    title: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    clientId: this.formBuilder.control<number | string | null>(null, Validators.required),
    templateId: this.formBuilder.control<number | string | null>(null, Validators.required)
  });
  readonly selectedTemplateId = toSignal(
    this.form.controls.templateId.valueChanges.pipe(startWith(this.form.controls.templateId.value)),
    { initialValue: this.form.controls.templateId.value }
  );
  readonly creationData = toSignal(this.taskCreationData$, { initialValue: { clients: [], templates: [] } });
  readonly selectedTemplate = computed(
    () => this.creationData().templates.find((template) => template.id === this.selectedTemplateId()) ?? null
  );

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload: CreateTaskFormValue = this.form.getRawValue();

    this.mockTaskCreationService
      .createTask(payload)
      .pipe(map((value) => this.dialogRef.close(value)))
      .subscribe();
  }
}