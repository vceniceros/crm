export type TaskAttachmentKind = 'image' | 'video' | 'other';

export interface TaskAttachment {
  id: string;
  fileName: string;
  fileType: string;
  kind: TaskAttachmentKind;
  previewUrl?: string | null;
  size?: number | null;
}