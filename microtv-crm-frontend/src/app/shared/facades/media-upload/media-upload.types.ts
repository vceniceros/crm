import { Observable } from 'rxjs';

import { TaskAttachment, TaskAttachmentKind } from '../../../core/models/task-attachment.model';

export interface MediaUploadContext {
  kind: 'task';
  taskId: string;
  subtaskId?: string | null;
}

export interface MediaUploadStrategy {
  readonly kind: TaskAttachmentKind;
  readonly acceptPattern: string;

  supports(file: File): boolean;
  validate(file: File): void;
}

export interface MediaUploadPort {
  upload(files: readonly File[], context: MediaUploadContext): Observable<TaskAttachment[]>;
  delete(attachmentId: string): Observable<void>;
}