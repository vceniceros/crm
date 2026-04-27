import { NgTemplateOutlet } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { MatCheckboxChange, MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';

import { TaskExecutionSubtaskView } from '../../../../core/models/task-execution.model';

@Component({
  selector: 'app-task-checklist-tree',
  standalone: true,
  imports: [NgTemplateOutlet, MatCheckboxModule, MatIconModule],
  templateUrl: './task-checklist-tree.component.html',
  styleUrl: './task-checklist-tree.component.scss'
})
export class TaskChecklistTreeComponent {
  readonly subtasks = input.required<readonly TaskExecutionSubtaskView[]>();
  readonly disabled = input(false);
  readonly subtaskToggled = output<{ subtaskId: string; completed: boolean }>();

  onToggle(subtaskId: string, event: MatCheckboxChange): void {
    this.subtaskToggled.emit({ subtaskId, completed: event.checked });
  }

  stateLabel(subtask: TaskExecutionSubtaskView): string {
    if (subtask.completed) {
      return 'Completada';
    }

    if (subtask.blocked) {
      return 'Bloqueada';
    }

    return 'Disponible';
  }
}