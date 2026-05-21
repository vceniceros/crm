import { CommonModule } from '@angular/common';
import { Component, inject, input, output, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { crmApiConfig } from '../../../../core/config/crm-api.config';
import { TaskAttachment } from '../../../../core/models/task-attachment.model';
import { MediaUploadFacade } from '../../../../shared/facades/media-upload.facade';
import { PhotoCaptureComponent } from '../../../../shared/ui/photo-capture/photo-capture.component';
import { UploadProgressComponent } from '../../../../shared/ui/upload-progress/upload-progress.component';
import { VideoRecorderComponent } from '../../../../shared/ui/video-recorder/video-recorder.component';

@Component({
  selector: 'app-task-attachments-section',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatCardModule, MatIconModule, PhotoCaptureComponent, UploadProgressComponent, VideoRecorderComponent],
  templateUrl: './task-attachments-section.component.html',
  styleUrl: './task-attachments-section.component.scss'
})
export class TaskAttachmentsSectionComponent {
  private readonly mediaUploadFacade = inject(MediaUploadFacade);
  private readonly backendOrigin = this.resolveBackendOrigin();
  readonly failedPreviewAttachmentIds = signal<Set<string>>(new Set());

  readonly taskId = input.required<string>();
  readonly subtaskId = input<string | null>(null);
  readonly attachments = input.required<readonly TaskAttachment[]>();
  readonly disabled = input(false);
  readonly attachmentsSelected = output<readonly TaskAttachment[]>();
  readonly attachmentRemoved = output<string>();
  readonly uploadError = signal<string | null>(null);
  readonly isUploading = signal(false);
  readonly isPhotoCaptureOpen = signal(false);
  readonly isRecorderOpen = signal(false);
  readonly uploadProgress = this.mediaUploadFacade.uploadProgress;
  readonly mediaStatus = this.mediaUploadFacade.mediaStatus;

  readonly acceptAttribute = this.mediaUploadFacade.acceptAttribute('task');

  onFileSelection(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);

    if (files.length) {
      this.uploadFiles(files);
    }

    input.value = '';
  }

  openPhotoCapture(): void {
    this.isRecorderOpen.set(false);
    this.isPhotoCaptureOpen.set(true);
  }

  closePhotoCapture(): void {
    this.isPhotoCaptureOpen.set(false);
  }

  onPhotoCaptured(file: File): void {
    this.isPhotoCaptureOpen.set(false);
    this.uploadFiles([file]);
  }

  openVideoRecorder(): void {
    this.isPhotoCaptureOpen.set(false);
    this.isRecorderOpen.set(true);
  }

  closeVideoRecorder(): void {
    this.isRecorderOpen.set(false);
  }

  onRecordingComplete(blob: Blob): void {
    const mimeType = blob.type.split(';')[0] || 'video/webm';
    const file = new File([blob], `recording-${Date.now()}.webm`, { type: mimeType });
    this.isRecorderOpen.set(false);
    this.uploadFiles([file]);
  }

  openGalleryInput(input: HTMLInputElement): void {
    if (!input) {
      return;
    }

    input.value = '';

    const picker = (input as HTMLInputElement & { showPicker?: () => void }).showPicker;
    if (typeof picker === 'function') {
      try {
        picker.call(input);
        return;
      } catch {
        // Fall back to click below.
      }
    }

    input.click();
  }

  private uploadFiles(files: readonly File[]): void {
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

  removeAttachment(attachmentId: string): void {
    this.attachmentRemoved.emit(attachmentId);
  }

  markPreviewAsFailed(attachmentId: string): void {
    this.failedPreviewAttachmentIds.update((current) => {
      const next = new Set(current);
      next.add(attachmentId);
      return next;
    });
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
    if (this.failedPreviewAttachmentIds().has(attachment.id)) {
      return false;
    }

    return Boolean(this.previewUrl(attachment) && (attachment.kind === 'image' || attachment.kind === 'video'));
  }

  previewUrl(attachment: TaskAttachment): string | null {
    return this.toAbsoluteUrl(attachment.previewUrl) ?? this.toAbsoluteUrl(attachment.publicUrl) ?? this.toAbsoluteUrl(attachment.storagePath);
  }

  downloadUrl(attachment: TaskAttachment): string | null {
    return this.toAbsoluteUrl(attachment.publicUrl) ?? this.previewUrl(attachment);
  }

  private toAbsoluteUrl(rawUrl: string | null | undefined): string | null {
    const normalized = rawUrl?.trim();
    if (!normalized) {
      return null;
    }

    if (/^(https?:|blob:|data:)/i.test(normalized)) {
      return normalized;
    }

    const slashNormalized = normalized.replace(/\\/g, '/');
    const lowerPath = slashNormalized.toLowerCase();
    const publicMarker = '/public/';
    const publicIndex = lowerPath.lastIndexOf(publicMarker);
    const normalizedPath = (publicIndex >= 0 ? slashNormalized.slice(publicIndex + publicMarker.length) : slashNormalized)
      .replace(/^\/?public\//i, '')
      .replace(/^\/+/, '');

    if (!normalizedPath || /^[a-z]:\//i.test(normalizedPath)) {
      return null;
    }

    return `${this.backendOrigin}/${normalizedPath}`;
  }

  private resolveBackendOrigin(): string {
    try {
      return new URL(crmApiConfig.baseUrl).origin;
    } catch {
      return crmApiConfig.baseUrl.replace(/\/$/, '');
    }
  }
}
