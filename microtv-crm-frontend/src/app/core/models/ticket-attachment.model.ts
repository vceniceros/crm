export type TicketAttachmentKind = 'image' | 'video' | 'other';

export interface TicketAttachment {
  id: string;
  fileName: string;
  fileType: string;
  kind: TicketAttachmentKind;
  previewUrl?: string | null;
  size?: number | null;
}