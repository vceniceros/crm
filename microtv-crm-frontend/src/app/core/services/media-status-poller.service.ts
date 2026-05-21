import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, interval, startWith, switchMap, takeWhile, throwError } from 'rxjs';

import { crmApiConfig } from '../config/crm-api.config';
import { AuthSessionService } from './auth-session.service';

export interface MediaStatusResponse {
  id: string;
  status: 'uploaded' | 'processing' | 'ready' | 'failed';
  original_url: string;
  optimized_url: string | null;
  thumbnail_url: string | null;
  error: string | null;
}

@Injectable({ providedIn: 'root' })
export class MediaStatusPollerService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  pollUntilDone(mediaId: string, intervalMs = 2000): Observable<MediaStatusResponse> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesion autenticada valida para consultar el estado del video.'));
    }

    return interval(intervalMs).pipe(
      startWith(0),
      switchMap(() => this.http.get<MediaStatusResponse>(`${crmApiConfig.baseUrl}/media/${encodeURIComponent(mediaId)}/status`, { headers })),
      takeWhile((response) => response.status !== 'ready' && response.status !== 'failed', true)
    );
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
}
