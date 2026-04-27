import { TemplateRequiredMaterial } from './material.model';
import { TemplateSubtask } from './template-subtask.model';

export interface TaskTemplateDraft {
  title: string;
  description: string;
  subtasks: TemplateSubtask[];
  requiredMaterials: TemplateRequiredMaterial[];
}

export interface TaskTemplateRecord extends TaskTemplateDraft {
  id: string;
}

export interface TaskTemplatesMockData {
  templates: TaskTemplateRecord[];
}