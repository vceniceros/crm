import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { TicketManagementService } from '../../../../core/services/ticket-management.service';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { isVideoFile, mediaVideoMaxBytes, optimizeImagesForUpload } from '../../../../core/utils/media-upload-optimization';
import {
  PublicSatisfactionFormInfoResponse,
  SatisfactionResponseDetailResponse
} from '../../../../core/models/ticket-management.model';
import {
  PublicTaskSatisfactionFormInfoResponse,
  TaskSatisfactionResponseDetailResponse,
} from '../../../../core/models/task-management.model';
import { TicketAttachment } from '../../../../core/models/ticket-attachment.model';
import { TicketAttachmentsSectionComponent } from '../../../tickets/components/ticket-attachments-section/ticket-attachments-section.component';

interface PendingSurveyMedia {
  id: string;
  file: File;
  previewUrl: string | null;
}

type SurveyMode = 'ticket' | 'task';
type SurveyInfo = PublicSatisfactionFormInfoResponse | PublicTaskSatisfactionFormInfoResponse;
type SurveyResponse = SatisfactionResponseDetailResponse | TaskSatisfactionResponseDetailResponse;

@Component({
  selector: 'app-satisfaction-page',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatSnackBarModule,
    TicketAttachmentsSectionComponent
  ],
  templateUrl: './satisfaction-page.component.html',
  styleUrl: './satisfaction-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SatisfactionPageComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly ticketService = inject(TicketManagementService);
  private readonly taskService = inject(TaskManagementService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly fb = inject(FormBuilder);

  readonly token = signal<string>('');
  readonly mode = signal<SurveyMode>('ticket');
  readonly isLoading = signal(true);
  readonly isSubmitting = signal(false);
  readonly formInfo = signal<SurveyInfo | null>(null);
  readonly response = signal<SurveyResponse | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly hoverRating = signal(0);
  readonly pendingMedia = signal<PendingSurveyMedia[]>([]);

  readonly ratingOptions = [1, 2, 3, 4, 5];

  readonly satisfactionForm = this.fb.group({
    customer_name: this.fb.control('', { validators: [Validators.required, Validators.maxLength(255)], nonNullable: true }),
    customer_company: this.fb.control('', { validators: [Validators.required, Validators.maxLength(255)], nonNullable: true }),
    rating: this.fb.control<number>(0, { validators: [Validators.min(1), Validators.required], nonNullable: true }),
    comment: this.fb.control<string>('', { nonNullable: true })
  });

  ngOnDestroy(): void {
    this.revokePendingMediaUrls();
  }

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('token') ?? '';
    const modeQuery = (this.route.snapshot.queryParamMap.get('mode') ?? '').trim().toLowerCase();
    this.mode.set(modeQuery === 'task' ? 'task' : 'ticket');
    this.token.set(token);

    if (!token) {
      this.errorMessage.set('Token inválido o formulario no encontrado.');
      this.isLoading.set(false);
      return;
    }

    if (this.isTaskMode()) {
      this.taskService.getPublicTaskSatisfactionForm(token).subscribe({
        next: (info) => {
          this.formInfo.set(info);
          this.isLoading.set(false);
        },
        error: () => {
          this.errorMessage.set('El formulario de satisfacción indicado no existe, expiró o ya fue utilizado.');
          this.isLoading.set(false);
        }
      });
      return;
    }

    this.ticketService.getPublicSatisfactionForm(token).subscribe({
      next: (info) => {
        this.formInfo.set(info);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('El formulario de satisfacción indicado no existe, expiró o ya fue utilizado.');
        this.isLoading.set(false);
      }
    });
  }

  isTaskMode(): boolean {
    return this.mode() === 'task';
  }

  setRating(value: number): void {
    this.satisfactionForm.patchValue({ rating: value });
  }

  get selectedRating(): number {
    return this.satisfactionForm.getRawValue().rating;
  }

  pendingAttachments(): TicketAttachment[] {
    return this.pendingMedia().map((item) => ({
      id: item.id,
      fileName: item.file.name,
      fileType: item.file.type || 'application/octet-stream',
      kind: this.resolveAttachmentKind(item.file.type),
      previewUrl: item.previewUrl,
      size: item.file.size,
    }));
  }

  async onSurveyFilesSelected(files: readonly File[]): Promise<void> {
    const validFiles = files.filter((file) => file.type.startsWith('image/') || file.type.startsWith('video/'));
    if (!validFiles.length) {
      this.snackBar.open('Solo se admiten imágenes o videos.', 'Cerrar', { duration: 3500 });
      return;
    }

    const maxVideoBytes = mediaVideoMaxBytes();
    const maxVideoMb = Math.max(1, Math.round(maxVideoBytes / (1024 * 1024)));
    for (const file of validFiles) {
      if (isVideoFile(file) && file.size > maxVideoBytes) {
        this.snackBar.open(`El video ${file.name} supera el límite de ${maxVideoMb} MB.`, 'Cerrar', { duration: 4500 });
        return;
      }
    }

    const preparedFiles = await optimizeImagesForUpload(validFiles);

    const additions = preparedFiles.map((file) => ({
      id: typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
      file,
      previewUrl: URL.createObjectURL(file),
    }));
    this.pendingMedia.update((current) => [...current, ...additions]);
  }

  onSurveyAttachmentRemoved(attachmentId: string): void {
    this.pendingMedia.update((current) => {
      const attachmentToRemove = current.find((item) => item.id === attachmentId);
      if (attachmentToRemove?.previewUrl) {
        URL.revokeObjectURL(attachmentToRemove.previewUrl);
      }
      return current.filter((item) => item.id !== attachmentId);
    });
  }

  onSubmit(): void {
    if (this.satisfactionForm.invalid || this.isSubmitting()) return;

    const { customer_name, customer_company, rating, comment } = this.satisfactionForm.getRawValue();
    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    if (this.isTaskMode()) {
      this.taskService
        .submitPublicTaskSatisfactionForm(this.token(), {
          rating,
          customer_name: customer_name.trim(),
          customer_company: customer_company.trim(),
          comment: comment.trim() || null
        })
        .subscribe({
          next: (resp) => {
            this.response.set(resp);
            this.isSubmitting.set(false);
          },
          error: (err: Error) => {
            this.isSubmitting.set(false);
            this.errorMessage.set(err.message ?? 'Error al enviar la encuesta. Intentá de nuevo.');
          }
        });
      return;
    }

    this.ticketService
      .submitPublicSatisfactionForm(
        this.token(),
        {
          rating,
          customer_name: customer_name.trim(),
          customer_company: customer_company.trim(),
          comment: comment.trim() || null
        },
        this.pendingMedia().map((item) => item.file)
      )
      .subscribe({
        next: (resp) => {
          this.response.set(resp);
          this.isSubmitting.set(false);
          this.revokePendingMediaUrls();
          this.pendingMedia.set([]);
        },
        error: (err: Error) => {
          this.isSubmitting.set(false);
          this.errorMessage.set(err.message ?? 'Error al enviar la encuesta. Intentá de nuevo.');
        }
      });
  }

  formPrimaryLabel(): string {
    const info = this.formInfo();
    if (!info) {
      return '';
    }

    if ('ticket_number' in info) {
      return `Ticket #${info.ticket_number}`;
    }

    return `Pedido: ${info.task_title}`;
  }

  formSecondaryLabel(): string {
    const info = this.formInfo();
    if (!info) {
      return '';
    }

    const parts = [info.client_name, info.location_name].filter((value) => Boolean(value && value.trim()));
    return parts.join(' · ');
  }

  responseMediaCount(): number {
    const response = this.response();
    if (!response) {
      return 0;
    }
    return 'media_count' in response ? response.media_count : 0;
  }

  private resolveAttachmentKind(fileType: string): TicketAttachment['kind'] {
    if (fileType.startsWith('image/')) {
      return 'image';
    }
    if (fileType.startsWith('video/')) {
      return 'video';
    }
    return 'other';
  }

  private revokePendingMediaUrls(): void {
    this.pendingMedia().forEach((item) => {
      if (item.previewUrl) {
        URL.revokeObjectURL(item.previewUrl);
      }
    });
  }
}
