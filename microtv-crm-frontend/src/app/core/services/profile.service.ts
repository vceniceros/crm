import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import { MePatchRequest, MeResponse } from '../models/profile.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  getMe(): Observable<MeResponse> {
    return this.request<MeResponse>('get', '/me');
  }

  patchMe(payload: MePatchRequest): Observable<MeResponse> {
    return this.request<MeResponse>('patch', '/me', payload);
  }

  uploadAvatar(file: File): Observable<MeResponse> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar el perfil.'));
    }

    const formData = new FormData();
    formData.append('file', file);
    return this.http
      .post<MeResponse>(`${crmApiConfig.baseUrl}/me/avatar`, formData, { headers })
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  requestPasswordReset(): Observable<void> {
    return this.request<void>('post', '/me/request-password-reset', {});
  }

  private request<T>(method: 'get' | 'patch' | 'post', path: string, body?: unknown): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar el perfil.'));
    }

    const url = `${crmApiConfig.baseUrl}${path}`;
    if (method === 'get') {
      return this.http.get<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }
    if (method === 'patch') {
      return this.http.patch<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }

    return this.http.post<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
  }

  private buildAuthHeaders(): HttpHeaders | null {
    const session = this.authSessionService.sessionSnapshot();
    const accessToken = session?.tokens.access_token;
    if (!accessToken) {
      return null;
    }

    return new HttpHeaders({
      Authorization: `Bearer ${accessToken}`
    });
  }

  private handleRequestError(error: unknown): Observable<never> {
    const apiMessage = (error as { error?: ApiErrorEnvelope })?.error?.error?.message;
    if (typeof apiMessage === 'string' && apiMessage.trim()) {
      return throwError(() => new Error(apiMessage));
    }

    return throwError(() => new Error('No se pudo completar la operación de perfil.'));
  }
}
