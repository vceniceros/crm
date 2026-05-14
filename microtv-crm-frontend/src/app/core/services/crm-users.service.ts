import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import { CrmUserOption } from '../models/task-management.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class CrmUsersService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  searchMentionableUsers(query: string, limit = 10): Observable<CrmUserOption[]> {
    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
      return of([]);
    }

    return this.request<CrmUserOption[]>(
      `/crm-users/mentions?q=${encodeURIComponent(normalizedQuery)}&limit=${encodeURIComponent(String(limit))}`
    );
  }

  private request<T>(path: string): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para buscar usuarios.'));
    }

    return this.http.get<T>(`${crmApiConfig.baseUrl}${path}`, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
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

    return throwError(() => new Error('No se pudo buscar usuarios para mencionar.'));
  }
}
