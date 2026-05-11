import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { crmApiConfig } from '../../../../core/config/crm-api.config';
import { MeResponse } from '../../../../core/models/profile.model';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { ProfileService } from '../../../../core/services/profile.service';
import { resolveBackendAssetUrl } from '../../../../core/utils/backend-asset-url.util';
import { optimizeImageForUpload } from '../../../../core/utils/media-upload-optimization';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    PageTitleComponent,
    UserAvatarComponent
  ],
  templateUrl: './profile-page.component.html',
  styleUrl: './profile-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ProfilePageComponent {
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);
  private readonly profileService = inject(ProfileService);
  private readonly authSessionService = inject(AuthSessionService);

  readonly me = signal<MeResponse | null>(null);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly uploadingAvatar = signal(false);
  readonly requestingPasswordReset = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    display_name: ['', [Validators.maxLength(120)]],
    email: ['', [Validators.email, Validators.maxLength(255)]]
  });

  readonly avatarUrl = computed(() => resolveBackendAssetUrl(this.me()?.avatar_url ?? null, crmApiConfig.baseUrl));
  readonly initials = computed(() => {
    const displayName = this.form.controls.display_name.value.trim() || this.me()?.display_name || this.me()?.email || 'Usuario';
    return displayName
      .split(/\s+/)
      .slice(0, 2)
      .map((segment) => segment[0]?.toUpperCase() ?? '')
      .join('')
      .slice(0, 2);
  });

  constructor() {
    this.loadProfile();
  }

  saveProfile(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }

    const payload = {
      display_name: this.form.controls.display_name.value.trim(),
      email: this.form.controls.email.value.trim()
    };

    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.profileService
      .patchMe(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (me) => {
          this.me.set(me);
          this.applyProfileToForm(me);
          this.syncSessionFromMe(me);
          this.successMessage.set('Perfil actualizado correctamente.');
          this.saving.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.saving.set(false);
        }
      });
  }

  async uploadAvatar(input: HTMLInputElement): Promise<void> {
    const file = input.files?.[0];
    input.value = '';
    if (!file || this.uploadingAvatar()) {
      return;
    }

    if (!file.type.startsWith('image/')) {
      this.errorMessage.set('Seleccioná una imagen válida para continuar.');
      this.successMessage.set(null);
      return;
    }

    const optimizedFile = await optimizeImageForUpload(file);

    this.uploadingAvatar.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.profileService
      .uploadAvatar(optimizedFile)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (me) => {
          this.me.set(me);
          this.syncSessionFromMe(me);
          this.successMessage.set('Avatar actualizado correctamente.');
          this.uploadingAvatar.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.uploadingAvatar.set(false);
        }
      });
  }

  requestPasswordReset(): void {
    if (this.requestingPasswordReset()) {
      return;
    }

    this.requestingPasswordReset.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.profileService
      .requestPasswordReset()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.successMessage.set('Se envió el email para restablecer tu contraseña.');
          this.requestingPasswordReset.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.requestingPasswordReset.set(false);
        }
      });
  }

  private loadProfile(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.profileService
      .getMe()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (me) => {
          this.me.set(me);
          this.applyProfileToForm(me);
          this.syncSessionFromMe(me);
          this.loading.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.loading.set(false);
        }
      });
  }

  private applyProfileToForm(me: MeResponse): void {
    this.form.patchValue(
      {
        display_name: me.display_name ?? '',
        email: me.email ?? ''
      },
      { emitEvent: false }
    );
  }

  private syncSessionFromMe(me: MeResponse): void {
    this.authSessionService.updateSessionUser({
      display_name: me.display_name,
      email: me.email,
      avatar_url: me.avatar_url
    });
  }
}
