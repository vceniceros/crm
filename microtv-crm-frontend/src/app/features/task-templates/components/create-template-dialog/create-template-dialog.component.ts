import { AsyncPipe } from '@angular/common';
import { AbstractControl, FormArray, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { MaterialOption, TemplateRequiredMaterial } from '../../../../core/models/material.model';
import { TaskTemplateDraft, TaskTemplateRecord } from '../../../../core/models/task-template.model';
import { TemplateSubtask } from '../../../../core/models/template-subtask.model';
import { MockTaskTemplateService } from '../../../../core/services/mock-task-template.service';
import {
  CreateTemplateFormGroup,
  CreateTemplateFormModel,
  TemplateRequiredMaterialFormGroup,
  TemplateSubtaskFormGroup
} from '../task-template-form.types';
import { TemplateMaterialsEditorComponent } from '../template-materials-editor/template-materials-editor.component';
import { TemplateSubtasksEditorComponent } from '../template-subtasks-editor/template-subtasks-editor.component';

@Component({
  selector: 'app-create-template-dialog',
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
    ReactiveFormsModule,
    TemplateMaterialsEditorComponent,
    TemplateSubtasksEditorComponent
  ],
  templateUrl: './create-template-dialog.component.html',
  styleUrl: './create-template-dialog.component.scss'
})
export class CreateTemplateDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<CreateTemplateDialogComponent, TaskTemplateRecord>);
  private readonly formBuilder = inject(FormBuilder);
  private readonly mockTaskTemplateService = inject(MockTaskTemplateService);

  readonly materials$ = this.mockTaskTemplateService.materials$;
  readonly form: CreateTemplateFormGroup = this.formBuilder.group<CreateTemplateFormModel>({
    title: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    description: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    subtasks: this.formBuilder.array<TemplateSubtaskFormGroup>([this.createSubtaskGroup()], {
      validators: [this.minSubtasksValidator]
    }),
    requiredMaterials: this.formBuilder.array<TemplateRequiredMaterialFormGroup>([])
  });

  readonly subtasks = this.form.controls.subtasks;
  readonly requiredMaterials = this.form.controls.requiredMaterials;
  readonly subtaskFactory = (subtask?: Partial<TemplateSubtask>) => this.createSubtaskGroup(subtask);

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload: TaskTemplateDraft = {
      title: this.form.controls.title.getRawValue().trim(),
      description: this.form.controls.description.getRawValue().trim(),
      subtasks: this.serializeSubtasks(this.subtasks),
      requiredMaterials: this.serializeMaterials(this.requiredMaterials)
    };

    this.mockTaskTemplateService
      .createTemplate(payload)
      .pipe(map((value) => this.dialogRef.close(value)))
      .subscribe();
  }

  private createSubtaskGroup(subtask?: Partial<TemplateSubtask>): TemplateSubtaskFormGroup {
    return this.formBuilder.group({
      id: this.formBuilder.control(subtask?.id ?? this.generateSubtaskId(), {
        validators: [Validators.required],
        nonNullable: true
      }),
      title: this.formBuilder.control(subtask?.title ?? '', {
        validators: [Validators.required],
        nonNullable: true
      }),
      children: this.formBuilder.array<TemplateSubtaskFormGroup>(
        (subtask?.children ?? []).map((child) => this.createSubtaskGroup(child))
      )
    });
  }

  private minSubtasksValidator(control: AbstractControl): ValidationErrors | null {
    const subtasks = control as FormArray<TemplateSubtaskFormGroup>;
    return subtasks.length > 0 ? null : { required: true };
  }

  private serializeSubtasks(subtasks: FormArray<TemplateSubtaskFormGroup>): TemplateSubtask[] {
    return subtasks.controls.map((subtask) => ({
      id: subtask.controls.id.getRawValue(),
      title: subtask.controls.title.getRawValue().trim(),
      children: this.serializeSubtasks(subtask.controls.children)
    }));
  }

  private serializeMaterials(materials: FormArray<TemplateRequiredMaterialFormGroup>): TemplateRequiredMaterial[] {
    return materials.controls.map((material) => ({
      materialId: material.controls.materialId.getRawValue(),
      name: material.controls.name.getRawValue(),
      quantity: material.controls.quantity.getRawValue(),
      unit: material.controls.unit.getRawValue() || undefined
    }));
  }

  private generateSubtaskId(): string {
    return `sub-${Math.random().toString(36).slice(2, 10)}`;
  }
}