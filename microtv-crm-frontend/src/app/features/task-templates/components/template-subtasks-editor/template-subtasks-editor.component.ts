import { NgTemplateOutlet } from '@angular/common';
import { Component, input } from '@angular/core';
import { FormArray, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

import { TemplateSubtask } from '../../../../core/models/template-subtask.model';
import { TemplateSubtaskFormGroup } from '../task-template-form.types';

@Component({
  selector: 'app-template-subtasks-editor',
  standalone: true,
  imports: [
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    NgTemplateOutlet,
    ReactiveFormsModule
  ],
  templateUrl: './template-subtasks-editor.component.html',
  styleUrl: './template-subtasks-editor.component.scss'
})
export class TemplateSubtasksEditorComponent {
  readonly subtasks = input.required<FormArray<TemplateSubtaskFormGroup>>();
  readonly buildSubtask = input.required<(subtask?: Partial<TemplateSubtask>) => TemplateSubtaskFormGroup>();

  addRootSubtask(): void {
    this.subtasks().push(this.buildSubtask()());
  }

  addChildSubtask(parent: TemplateSubtaskFormGroup): void {
    parent.controls.children.push(this.buildSubtask()());
  }

  removeSubtask(container: FormArray<TemplateSubtaskFormGroup>, index: number): void {
    container.removeAt(index);
    container.markAsDirty();
    container.markAsTouched();
  }

  childrenOf(subtask: TemplateSubtaskFormGroup): FormArray<TemplateSubtaskFormGroup> {
    return subtask.controls.children;
  }

  trackSubtask(subtask: TemplateSubtaskFormGroup): string {
    return subtask.controls.id.value;
  }
}