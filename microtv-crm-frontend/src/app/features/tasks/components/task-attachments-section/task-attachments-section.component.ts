import { Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { TaskAttachment } from '../../../../core/models/task-attachment.model';

@Component({
  selector: 'app-task-attachments-section',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule],
  templateUrl: './task-attachments-section.component.html',
  styleUrl: './task-attachments-section.component.scss'
})
export class TaskAttachmentsSectionComponent {
  readonly attachments = input.required<readonly TaskAttachment[]>();
  readonly disabled = input(false);
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

  trackByAttachmentId(_: number, attachment: TaskAttachment): string {
    return attachment.id;
  }

  iconFor(attachment: TaskAttachment): string {
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

  canPreview(attachment: TaskAttachment): boolean {
    return Boolean(attachment.previewUrl && (attachment.kind === 'image' || attachment.kind === 'video'));
  }
}