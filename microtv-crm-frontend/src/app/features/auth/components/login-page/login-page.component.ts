import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { crmApiConfig, crmRuntimeConfig } from '../../../../core/config/crm-api.config';
import type { CrmRuntimeSeedLoginAccount } from '../../../../core/config/crm-api.config';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './login-page.component.html',
  styleUrl: './login-page.component.scss'
})
export class LoginPageComponent {
  private readonly authSessionService = inject(AuthSessionService);
  private readonly router = inject(Router);
  private readonly activatedRoute = inject(ActivatedRoute);

  readonly showDevSeedAccounts = crmRuntimeConfig.devMode;
  readonly seedAccounts: CrmRuntimeSeedLoginAccount[] = crmRuntimeConfig.devLoginAccounts;
  readonly loginCardSubtitle = this.showDevSeedAccounts
    ? 'Probá con cualquiera de las cuentas seed del auth local.'
    : 'Ingresá con un usuario habilitado en auth.microtv.ar para operar el CRM.';

  readonly isSubmitting = signal(false);
  readonly feedbackMessage = signal<string | null>(null);
  readonly feedbackTone = signal<'error' | 'info'>('error');
  readonly showPassword = signal(false);
  readonly form = new FormGroup({
    email: new FormControl('admin.crm@microtv.com', {
      nonNullable: true,
      validators: [Validators.required, Validators.email]
    }),
    password: new FormControl('Passw0rd!', {
      nonNullable: true,
      validators: [Validators.required]
    })
  });

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.feedbackMessage.set(null);

    try {
      const response = await firstValueFrom(this.authSessionService.login(this.form.getRawValue()));

      if (response.status === 'authenticated') {
        const redirectTo = this.activatedRoute.snapshot.queryParamMap.get('redirectTo') || '/';
        await this.router.navigateByUrl(redirectTo);
        return;
      }

      if (response.status === 'context_selection_required') {
        this.feedbackTone.set('info');
        this.feedbackMessage.set(
          'La cuenta requiere seleccion de contexto antes de entrar al CRM. Por ahora el frontend inicial no resuelve ese paso.'
        );
        return;
      }

      this.feedbackTone.set('info');
      this.feedbackMessage.set(
        'La cuenta existe en auth, pero todavia no tiene acceso operativo confirmado para este flujo inicial del CRM.'
      );
    } catch (error) {
      this.feedbackTone.set('error');
      this.feedbackMessage.set(this.resolveErrorMessage(error));
    } finally {
      this.isSubmitting.set(false);
    }
  }

  togglePasswordVisibility(): void {
    this.showPassword.update((currentValue) => !currentValue);
  }

  useSeedAccount(account: CrmRuntimeSeedLoginAccount): void {
    this.form.setValue({
      email: account.email,
      password: account.password
    });
    this.form.markAsPristine();
    this.form.markAsUntouched();
    this.feedbackMessage.set(null);
  }

  private resolveErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const apiMessage = error.error?.error?.message;
      if (typeof apiMessage === 'string' && apiMessage.trim()) {
        return apiMessage;
      }

      if (error.status === 0) {
        return `No se pudo conectar con el backend del CRM. Verificá la URL configurada en CRM_API_BASE_URL (${crmApiConfig.baseUrl}).`;
      }

      if (error.status === 401) {
        return 'Las credenciales no son validas o el usuario no pudo autenticarse en auth.microtv.ar.';
      }

      if (error.status === 403) {
        return 'El usuario autenticado no tiene un rol local habilitado para entrar al CRM.';
      }

      if (error.status >= 500) {
        return 'El backend del CRM o auth.microtv.ar devolvieron un error interno. Revisá los logs antes de seguir.';
      }
    }

    return 'No se pudo completar el login. Revisá la configuracion local y probá de nuevo.';
  }
}