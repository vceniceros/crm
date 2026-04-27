import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogContent,
  MatDialogModule,
  MatDialogRef,
  MatDialogTitle
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { SatisfactionResponseDetailResponse } from '../../../../core/models/ticket-management.model';
import { TicketAttachment } from '../../../../core/models/ticket-attachment.model';
import { TicketAttachmentsSectionComponent } from '../ticket-attachments-section/ticket-attachments-section.component';

export interface SurveyLinkDialogData {
  title: string;
  message: string;
  surveyUrl?: string | null;
  details?: string | null;
  copyEnabled?: boolean;
  surveyResponse?: SatisfactionResponseDetailResponse | null;
}

@Component({
  selector: 'app-survey-link-dialog',
  standalone: true,
  imports: [
    MatButtonModule,
    MatDialogActions,
    MatDialogContent,
    MatDialogModule,
    MatDialogTitle,
    MatIconModule,
    MatSnackBarModule,
    TicketAttachmentsSectionComponent
  ],
  templateUrl: './survey-link-dialog.component.html',
  styleUrl: './survey-link-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SurveyLinkDialogComponent {
  readonly data = inject<SurveyLinkDialogData>(MAT_DIALOG_DATA);
  readonly ratingScale = [1, 2, 3, 4, 5];
  readonly surveyAttachments = this.mapSurveyAttachments(this.data.surveyResponse);

  private readonly snackBar = inject(MatSnackBar);
  private readonly dialogRef = inject(MatDialogRef<SurveyLinkDialogComponent>);

  copyLink(): void {
    const surveyUrl = this.data.surveyUrl?.trim();
    if (!surveyUrl) {
      return;
    }

    navigator.clipboard
      ?.writeText(surveyUrl)
      .then(() => {
        this.snackBar.open('Link copiado al portapapeles.', 'Cerrar', { duration: 3000 });
      })
      .catch(() => {
        this.snackBar.open('No se pudo copiar el link automáticamente.', 'Cerrar', { duration: 4000 });
      });
  }

  close(): void {
    this.dialogRef.close();
  }

  private mapSurveyAttachments(response: SatisfactionResponseDetailResponse | null | undefined): TicketAttachment[] {
    if (!response?.media_files?.length) {
      return [];
    }

    return response.media_files.map((media) => ({
      id: media.id,
      fileName: media.file_name?.trim() || media.id,
      fileType: media.file_type || 'application/octet-stream',
      kind: this.resolveAttachmentKind(media.file_type),
      previewUrl: media.file_path,
      size: media.size_bytes ?? null,
    }));
  }

  private resolveAttachmentKind(fileType: string | null | undefined): TicketAttachment['kind'] {
    const normalized = (fileType || '').toLowerCase();
    if (normalized.startsWith('image/')) {
      return 'image';
    }
    if (normalized.startsWith('video/')) {
      return 'video';
    }
    return 'other';
  }
}
