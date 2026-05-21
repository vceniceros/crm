import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, interval, startWith, switchMap, takeWhile } from 'rxjs';

import { crmApiConfig } from '../config/crm-api.config';

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

  pollUntilDone(mediaId: string, intervalMs = 2000): Observable<MediaStatusResponse> {
    return interval(intervalMs).pipe(
      startWith(0),
      switchMap(() => this.http.get<MediaStatusResponse>(`${crmApiConfig.baseUrl}/media/${encodeURIComponent(mediaId)}/status`)),
      takeWhile((response) => response.status !== 'ready' && response.status !== 'failed', true)
    );
  }
}
