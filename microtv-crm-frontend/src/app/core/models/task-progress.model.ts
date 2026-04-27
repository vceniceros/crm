import { TaskAttachment } from './task-attachment.model';

export interface TaskProgressState {
  taskId: string;
  completedSubtaskIds: string[];
  comment: string;
  attachments: TaskAttachment[];
  finalized: boolean;
  updatedAt: string;
}

export interface TaskProgressData {
  progress: TaskProgressState[];
}