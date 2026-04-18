export type TaskAttachmentKind = 'image' | 'video' | 'other';

export interface TaskAttachment {
  id: string;
  fileName: string;
  fileType: string;
  kind: TaskAttachmentKind;
  context?: 'task';
  previewUrl?: string | null;
  publicUrl?: string | null;
  storagePath?: string | null;
  size?: number | null;
}