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
  readonly sectionTitle = input('Adjuntos del ticket');
  readonly editableSubtitle = input('Fotos y videos del diagnóstico técnico persistidos en backend.');
  readonly readonlySubtitle = input('Evidencia visual cargada en el ticket. Visible para seguimiento cruzado entre técnico, depósito y admin.');
  readonly uploadButtonLabel = input('Agregar fotos o videos');
  readonly hintText = input('Los archivos quedan disponibles para comentarios, transiciones y cierre del ticket.');
  readonly emptyMessage = input('No hay adjuntos cargados todavía para este ticket.');
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

  triggerFileInput(input: HTMLInputElement): void {
    if (!input) {
      return;
    }

    // Reset value so the same file can be selected again after retries.
    input.value = '';

    const picker = (input as HTMLInputElement & { showPicker?: () => void }).showPicker;
    if (typeof picker === 'function') {
      picker.call(input);
      return;
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
}