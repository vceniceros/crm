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
import {
  PublicSatisfactionFormInfoResponse,
  SatisfactionResponseDetailResponse
} from '../../../../core/models/ticket-management.model';
import { TicketAttachment } from '../../../../core/models/ticket-attachment.model';
import { TicketAttachmentsSectionComponent } from '../../../tickets/components/ticket-attachments-section/ticket-attachments-section.component';

interface PendingSurveyMedia {
  id: string;
  file: File;
  previewUrl: string | null;
}

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
  private readonly snackBar = inject(MatSnackBar);
  private readonly fb = inject(FormBuilder);

  readonly token = signal<string>('');
  readonly isLoading = signal(true);
  readonly isSubmitting = signal(false);
  readonly formInfo = signal<PublicSatisfactionFormInfoResponse | null>(null);
  readonly response = signal<SatisfactionResponseDetailResponse | null>(null);
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
    this.token.set(token);

    if (!token) {
      this.errorMessage.set('Token inválido o formulario no encontrado.');
      this.isLoading.set(false);
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

  onSurveyFilesSelected(files: readonly File[]): void {
    const validFiles = files.filter((file) => file.type.startsWith('image/') || file.type.startsWith('video/'));
    if (!validFiles.length) {
      this.snackBar.open('Solo se admiten imágenes o videos.', 'Cerrar', { duration: 3500 });
      return;
    }

    const additions = validFiles.map((file) => ({
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

    this.ticketService
      .submitPublicSatisfactionForm(this.token(), {
        rating,
        customer_name: customer_name.trim(),
        customer_company: customer_company.trim(),
        comment: comment.trim() || null
      }, this.pendingMedia().map((item) => item.file))
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
