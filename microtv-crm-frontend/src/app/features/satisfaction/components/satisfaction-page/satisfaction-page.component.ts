import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
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
    MatSnackBarModule
  ],
  templateUrl: './satisfaction-page.component.html',
  styleUrl: './satisfaction-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SatisfactionPageComponent implements OnInit {
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

  readonly ratingOptions = [1, 2, 3, 4, 5];

  readonly satisfactionForm = this.fb.group({
    rating: this.fb.control<number>(0, { validators: [Validators.min(1), Validators.required], nonNullable: true }),
    comment: this.fb.control<string>('', { nonNullable: true })
  });

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

  onSubmit(): void {
    if (this.satisfactionForm.invalid || this.isSubmitting()) return;

    const { rating, comment } = this.satisfactionForm.getRawValue();
    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    this.ticketService
      .submitPublicSatisfactionForm(this.token(), {
        rating,
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
  }
}
