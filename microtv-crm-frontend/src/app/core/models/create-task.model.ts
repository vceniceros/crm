import { ClientOption } from './client.model';
import { TaskTemplateOption } from './task-template.model';

export interface CreateTaskFormValue {
  title: string;
  clientId: number | string | null;
  templateId: number | string | null;
}

export interface TaskCreationMockData {
  clients: ClientOption[];
  templates: TaskTemplateOption[];
}