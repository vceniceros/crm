import { CommonModule } from '@angular/common';
import { Component, inject, input, output, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { TaskAttachment } from '../../../../core/models/task-attachment.model';
import { MediaUploadFacade } from '../../../../shared/facades/media-upload.facade';

@Component({
  selector: 'app-task-attachments-section',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatCardModule, MatIconModule],
  templateUrl: './task-attachments-section.component.html',
  styleUrl: './task-attachments-section.component.scss'
})
export class TaskAttachmentsSectionComponent {
  private readonly mediaUploadFacade = inject(MediaUploadFacade);

  readonly taskId = input.required<string>();
  readonly subtaskId = input<string | null>(null);
  readonly attachments = input.required<readonly TaskAttachment[]>();
  readonly disabled = input(false);
  readonly attachmentsSelected = output<readonly TaskAttachment[]>();
  readonly attachmentRemoved = output<string>();
  readonly uploadError = signal<string | null>(null);
  readonly isUploading = signal(false);

  readonly acceptAttribute = this.mediaUploadFacade.acceptAttribute('task');

  onFileSelection(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);

    if (files.length) {
      try {
        this.uploadError.set(null);
        this.isUploading.set(true);
        this.mediaUploadFacade
          .upload(files, {
            kind: 'task',
            taskId: this.taskId(),
            subtaskId: this.subtaskId()
          })
          .pipe(finalize(() => this.isUploading.set(false)))
          .subscribe({
            next: (attachments) => this.attachmentsSelected.emit(attachments),
            error: (error: Error) => {
              this.uploadError.set(error instanceof Error ? error.message : 'No se pudo subir la multimedia seleccionada.');
            }
          });
      } catch (error) {
        this.uploadError.set(error instanceof Error ? error.message : 'No se pudo preparar la multimedia seleccionada.');
        this.isUploading.set(false);
      }
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