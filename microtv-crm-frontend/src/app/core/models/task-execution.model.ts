import { TicketStatusTone } from './dashboard.model';
import { TaskAttachment } from './task-attachment.model';

export interface TaskExecutionSubtaskDefinition {
  id: string;
  title: string;
  required?: boolean;
  children: TaskExecutionSubtaskDefinition[];
}

export interface TaskExecutionDefinition {
  id: string;
  title: string;
  client: string;
  summary: string;
  status: string;
  statusTone: TicketStatusTone;
  assigneeId: number | string;
  assigneeName: string;
  assigneeInitials: string;
  subtasks: TaskExecutionSubtaskDefinition[];
}

export interface TaskExecutionData {
  tasks: TaskExecutionDefinition[];
}

export interface TaskExecutionSubtaskView extends TaskExecutionSubtaskDefinition {
  completed: boolean;
  enabled: boolean;
  blocked: boolean;
  children: TaskExecutionSubtaskView[];
}

export interface TaskExecutionItem {
  id: string;
  title: string;
  client: string;
  summary: string;
  status: string;
  statusTone: TicketStatusTone;
  assigneeId: number | string;
  assigneeName: string;
  assigneeInitials: string;
  completedSubtasks: number;
  totalSubtasks: number;
  progressPercent: number;
  comment: string;
  attachments: TaskAttachment[];
  finalized: boolean;
  canFinalize: boolean;
  updatedAt: string;
  subtasks: TaskExecutionSubtaskView[];
}