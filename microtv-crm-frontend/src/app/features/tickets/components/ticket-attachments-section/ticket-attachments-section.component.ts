import { Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { TicketAttachment } from '../../../../core/models/ticket-attachment.model';

@Component({
  selector: 'app-ticket-attachments-section',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule],
  templateUrl: './ticket-attachments-section.component.html',
  styleUrl: './ticket-attachments-section.component.scss'
})
export class TicketAttachmentsSectionComponent {
  readonly attachments = input.required<readonly TicketAttachment[]>();
  readonly canEdit = input(false);
  readonly attachmentsSelected = output<readonly File[]>();
  readonly attachmentRemoved = output<string>();

  onFileSelection(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);

    if (files.length) {
      this.attachmentsSelected.emit(files);
    }

    input.value = '';
  }

  removeAttachment(attachmentId: string): void {
    this.attachmentRemoved.emit(attachmentId);
  }

  trackByAttachmentId(_: number, attachment: TicketAttachment): string {
    return attachment.id;
  }

  iconFor(attachment: TicketAttachment): string {
    if (attachment.kind === 'image') {
      return 'image';
    }

    if (attachment.kind === 'video') {
      return 'videocam';
    }

    return 'attach_file';
  }

  formatSize(size: number | null | undefined): string {
    if (!size || size <= 0) {
      return 'Tamaño no disponible';
    }

    if (size >= 1024 * 1024) {
      return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    }

    if (size >= 1024) {
      return `${Math.round(size / 1024)} KB`;
    }

    return `${size} B`;
  }

  canPreview(attachment: TicketAttachment): boolean {
    return Boolean(attachment.previewUrl && (attachment.kind === 'image' || attachment.kind === 'video'));
  }
}