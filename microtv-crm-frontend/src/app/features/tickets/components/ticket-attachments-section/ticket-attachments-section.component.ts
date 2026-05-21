import { Component, HostListener, inject, input, output, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { TicketAttachment } from '../../../../core/models/ticket-attachment.model';
import { ImageViewerDialogComponent } from '../../../../shared/ui/image-viewer-dialog/image-viewer-dialog.component';
import { PhotoCaptureComponent } from '../../../../shared/ui/photo-capture/photo-capture.component';
import { VideoRecorderComponent } from '../../../../shared/ui/video-recorder/video-recorder.component';

@Component({
  selector: 'app-ticket-attachments-section',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatDialogModule, MatIconModule, MatProgressBarModule, PhotoCaptureComponent, VideoRecorderComponent],
  templateUrl: './ticket-attachments-section.component.html',
  styleUrl: './ticket-attachments-section.component.scss'
})
export class TicketAttachmentsSectionComponent {
  private readonly dialog = inject(MatDialog);

  readonly attachments = input.required<readonly TicketAttachment[]>();
  readonly canEdit = input(false);
  readonly sectionTitle = input('Adjuntos del ticket');
  readonly editableSubtitle = input('Fotos y videos del diagnóstico técnico persistidos en backend.');
  readonly readonlySubtitle = input('Evidencia visual cargada en el ticket. Visible para seguimiento cruzado entre técnico, depósito y admin.');
  readonly uploadButtonLabel = input('Agregar fotos o videos');
  readonly hintText = input('Los archivos quedan disponibles para comentarios, transiciones y cierre del ticket.');
  readonly emptyMessage = input('No hay adjuntos cargados todavía para este ticket.');
  readonly isSaving = input(false);
  readonly attachmentsSelected = output<readonly File[]>();
  readonly attachmentRemoved = output<string>();
  readonly isPhotoCaptureOpen = signal(false);
  readonly isRecorderOpen = signal(false);

  onFileSelection(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);

    if (files.length) {
      this.attachmentsSelected.emit(files);
    }

    input.value = '';
  }

  @HostListener('document:paste', ['$event'])
  onClipboardPaste(event: ClipboardEvent): void {
    if (!this.canEdit()) {
      return;
    }

    const mediaFiles = this.getMediaFilesFromClipboard(event);
    if (!mediaFiles.length) {
      return;
    }

    event.preventDefault();
    this.attachmentsSelected.emit(mediaFiles);
  }

  removeAttachment(attachmentId: string): void {
    this.attachmentRemoved.emit(attachmentId);
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
    this.attachmentsSelected.emit([file]);
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
    this.isRecorderOpen.set(false);
    this.attachmentsSelected.emit([
      new File([blob], `recording-${Date.now()}.webm`, { type: mimeType })
    ]);
  }

  trackByAttachmentId(_: number, attachment: TicketAttachment): string {
    return attachment.id;
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

  openPreview(attachment: TicketAttachment): void {
    if (!this.canPreview(attachment) || !attachment.previewUrl) {
      return;
    }

    this.dialog.open(ImageViewerDialogComponent, {
      data: {
        mediaUrl: attachment.previewUrl,
        altText: attachment.fileName,
        mediaType: attachment.kind === 'video' ? 'video' : 'image',
        mimeType: attachment.fileType
      },
      maxWidth: '95vw',
      maxHeight: '95vh',
      panelClass: 'image-viewer-panel'
    });
  }

  private getMediaFilesFromClipboard(event: ClipboardEvent): File[] {
    const clipboardData = event.clipboardData;
    if (!clipboardData) {
      return [];
    }

    const filesFromItems = Array.from(clipboardData.items ?? [])
      .filter((item) => item.kind === 'file' && this.isSupportedMediaType(item.type))
      .map((item) => item.getAsFile())
      .filter((file): file is File => Boolean(file));

    if (filesFromItems.length) {
      return filesFromItems;
    }

    return Array.from(clipboardData.files ?? []).filter((file) => this.isSupportedMediaType(file.type));
  }

  private isSupportedMediaType(type: string | null | undefined): boolean {
    return Boolean(type?.startsWith('image/') || type?.startsWith('video/'));
  }
}
