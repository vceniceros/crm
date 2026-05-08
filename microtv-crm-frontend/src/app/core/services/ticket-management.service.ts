import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, Subject, from, throwError } from 'rxjs';
import { catchError, map, mergeMap, tap } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import {
  ApproveTicketRequest,
  AssignTicketRequest,
  CloseTicketRequest,
  CreateTicketCommentRequest,
  CreateTicketRequest,
  GenerateSatisfactionFormResponse,
  PublicSatisfactionFormInfoResponse,
  RegisterArrivalRequest,
  SatisfactionMediaFile,
  RejectTicketApprovalRequest,
  ReopenTicketRequest,
  SatisfactionFormStatusResponse,
  SatisfactionResponseDetailResponse,
  SubmitSatisfactionFormRequest,
  TicketAttachment,
  TicketClientOption,
  TicketDetail,
  TicketRoleOption,
  TicketSummary,
  UpdateTicketStatusRequest
} from '../models/ticket-management.model';
import { CreateLocationRequest, CrmUserOption, PersistedLocation } from '../models/task-management.model';
import { AppLocation } from '../models/location.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class TicketManagementService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly badgeRefreshSubject = new Subject<void>();

  readonly badgeRefresh$ = this.badgeRefreshSubject.asObservable();

  listAssignableRoles(): Observable<TicketRoleOption[]> {
    return this.request<TicketRoleOption[]>('get', '/tickets/roles');
  }

  listClients(): Observable<TicketClientOption[]> {
    return this.request<TicketClientOption[]>('get', '/clients');
  }

  listCrmUsersByRole(roleKey: string): Observable<CrmUserOption[]> {
    return this.request<CrmUserOption[]>('get', `/crm-users?role_key=${encodeURIComponent(roleKey)}`);
  }

  createLocation(location: AppLocation): Observable<PersistedLocation> {
    const payload: CreateLocationRequest = {
      latitude: location.latitude,
      longitude: location.longitude,
      address_label: location.addressLabel?.trim() || null,
      formatted_address: location.addressLabel?.trim() || null
    };

    return this.request<{
      location_id: string;
      latitude: number;
      longitude: number;
      address_label: string | null;
    }>('post', '/locations', payload).pipe(map((response) => this.mapPersistedLocation(response)));
  }

  createTicket(payload: CreateTicketRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('post', '/tickets', payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  listAssignedTickets(): Observable<TicketSummary[]> {
    return this.request<TicketSummary[]>('get', '/tickets/assigned/me');
  }

  listUnassignedTickets(): Observable<TicketSummary[]> {
    return this.request<TicketSummary[]>('get', '/tickets/unassigned/me');
  }

  listTrackingTickets(): Observable<TicketSummary[]> {
    return this.request<TicketSummary[]>('get', '/tickets/tracking/me');
  }

  listTicketHistory(): Observable<TicketSummary[]> {
    return this.request<TicketSummary[]>('get', '/tickets/history/me');
  }

  getTicketDetail(ticketId: string): Observable<TicketDetail> {
    return this.request<TicketDetail>('get', `/tickets/${ticketId}`).pipe(map((ticket) => this.normalizeTicketDetail(ticket)));
  }

  assignTicket(ticketId: string, payload: AssignTicketRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('patch', `/tickets/${ticketId}/assignment`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  addTicketComment(ticketId: string, payload: CreateTicketCommentRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('post', `/tickets/${ticketId}/comments`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket))
    );
  }

  markCommentAsSolution(ticketId: string, commentId: string): Observable<TicketDetail> {
    return this.request<TicketDetail>('post', `/tickets/${ticketId}/comments/${commentId}/mark-as-solution`).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  updateTicketStatus(ticketId: string, payload: UpdateTicketStatusRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('patch', `/tickets/${ticketId}/status`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  closeTicket(ticketId: string, payload: CloseTicketRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('patch', `/tickets/${ticketId}/close`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  approveTicket(ticketId: string, payload: ApproveTicketRequest = {}): Observable<TicketDetail> {
    return this.request<TicketDetail>('patch', `/tickets/${ticketId}/approve`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  rejectTicketApproval(ticketId: string, payload: RejectTicketApprovalRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('patch', `/tickets/${ticketId}/reject`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  reopenTicket(ticketId: string, payload: ReopenTicketRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('patch', `/tickets/${ticketId}/reopen`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  uploadTicketAttachments(ticketId: string, files: readonly File[]): Observable<TicketAttachment[]> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tickets.'));
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    return this.http
      .post<TicketAttachment[]>(`${crmApiConfig.baseUrl}/tickets/${ticketId}/attachments`, formData, { headers })
      .pipe(
        map((attachments) => attachments.map((attachment) => this.normalizeAttachment(attachment))),
        catchError((error) => this.handleRequestError(error))
      );
  }

  deleteTicketAttachment(attachmentId: string): Observable<void> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tickets.'));
    }

    return this.http
      .delete<void>(`${crmApiConfig.baseUrl}/tickets/attachments/${attachmentId}`, { headers })
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  // -------------------------------------------------------------------------
  // Arrival registration (US-1)
  // -------------------------------------------------------------------------

  registerArrival(ticketId: string, payload: RegisterArrivalRequest): Observable<TicketDetail> {
    return this.request<TicketDetail>('post', `/tickets/${ticketId}/arrival`, payload).pipe(
      map((ticket) => this.normalizeTicketDetail(ticket))
    );
  }

  // -------------------------------------------------------------------------
  // Satisfaction form (US-2)
  // -------------------------------------------------------------------------

  generateTicketSurvey(ticketId: string): Observable<GenerateSatisfactionFormResponse> {
    return this.request<GenerateSatisfactionFormResponse>('post', `/tickets/${ticketId}/generate-survey`);
  }

  generateSatisfactionForm(ticketId: string): Observable<GenerateSatisfactionFormResponse> {
    return this.generateTicketSurvey(ticketId);
  }

  revokeSatisfactionForm(ticketId: string): Observable<SatisfactionFormStatusResponse> {
    return this.request<SatisfactionFormStatusResponse>('post', `/tickets/${ticketId}/satisfaction-form/revoke`);
  }

  getSatisfactionFormStatus(ticketId: string): Observable<SatisfactionFormStatusResponse> {
    return this.request<SatisfactionFormStatusResponse>('get', `/tickets/${ticketId}/satisfaction-form/status`);
  }

  getSatisfactionResponse(ticketId: string): Observable<SatisfactionResponseDetailResponse> {
    return this.request<SatisfactionResponseDetailResponse>('get', `/tickets/${ticketId}/satisfaction-form/response`).pipe(
      map((response) => this.normalizeSatisfactionResponse(response))
    );
  }

  // Public (no auth required)
  getPublicSatisfactionForm(token: string): Observable<PublicSatisfactionFormInfoResponse> {
    return this.http
      .get<PublicSatisfactionFormInfoResponse>(`${crmApiConfig.baseUrl}/public/tickets/satisfaction/${encodeURIComponent(token)}`)
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  submitPublicSatisfactionForm(
    token: string,
    payload: SubmitSatisfactionFormRequest,
    files: readonly File[] = []
  ): Observable<SatisfactionResponseDetailResponse> {
    const endpoint = `${crmApiConfig.baseUrl}/public/tickets/satisfaction/${encodeURIComponent(token)}`;
    if (files.length > 0) {
      const formData = new FormData();
      formData.append('rating', String(payload.rating));
      formData.append('customer_name', payload.customer_name);
      formData.append('customer_company', payload.customer_company);
      if (payload.comment?.trim()) {
        formData.append('comment', payload.comment.trim());
      }
      files.forEach((file) => formData.append('files', file));

      return this.http
        .post<SatisfactionResponseDetailResponse>(endpoint, formData)
        .pipe(
          map((response) => this.normalizeSatisfactionResponse(response)),
          catchError((error) => this.handleRequestError(error))
        );
    }

    return this.http
      .post<SatisfactionResponseDetailResponse>(endpoint, payload)
      .pipe(
        map((response) => this.normalizeSatisfactionResponse(response)),
        catchError((error) => this.handleRequestError(error))
      );
  }

  // -------------------------------------------------------------------------
  // Export development (US-3)
  // -------------------------------------------------------------------------

  exportTicketHistory(ticketId: string): Observable<Blob> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tickets.'));
    }
    return this.http
      .get(`${crmApiConfig.baseUrl}/tickets/${ticketId}/export`, {
        headers,
        responseType: 'blob'
      })
      .pipe(catchError((error) => this.handleBlobRequestError(error, 'No se pudo exportar el historial del ticket.')));
  }

  exportTicketDevelopment(ticketId: string): Observable<Blob> {
    return this.exportTicketHistory(ticketId);
  }

  private request<T>(method: 'get' | 'post' | 'put' | 'patch', path: string, body?: unknown): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tickets.'));
    }

    const url = `${crmApiConfig.baseUrl}${path}`;
    if (method === 'get') {
      return this.http.get<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }

    if (method === 'put') {
      return this.http.put<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }

    if (method === 'patch') {
      return this.http.patch<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }

    return this.http.post<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
  }

  private mapPersistedLocation(location: {
    location_id: string;
    latitude: number;
    longitude: number;
    address_label: string | null;
  }): PersistedLocation {
    return {
      locationId: location.location_id,
      latitude: location.latitude,
      longitude: location.longitude,
      addressLabel: location.address_label?.trim() || undefined
    };
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

    const validationDetail = (error as { error?: { detail?: unknown } })?.error?.detail;
    const validationMessage = this.extractValidationMessage(validationDetail);
    if (validationMessage) {
      return throwError(() => new Error(validationMessage));
    }

    return throwError(() => new Error('No se pudo completar la operación de tickets.'));
  }

  private handleBlobRequestError(error: unknown, fallbackMessage: string): Observable<never> {
    const blobPayload = (error as { error?: unknown })?.error;
    if (!(blobPayload instanceof Blob)) {
      return this.handleRequestError(error);
    }

    return from(blobPayload.text()).pipe(
      map((text) => this.extractApiMessageFromBlobText(text) || this.fallbackMessageByStatus((error as { status?: number })?.status, fallbackMessage)),
      mergeMap((message) => throwError(() => new Error(message)))
    );
  }

  private extractApiMessageFromBlobText(rawText: string): string | null {
    const normalized = rawText?.trim();
    if (!normalized) {
      return null;
    }

    try {
      const parsed = JSON.parse(normalized) as {
        error?: { message?: unknown };
        detail?: unknown;
      };

      const apiMessage = parsed?.error?.message;
      if (typeof apiMessage === 'string' && apiMessage.trim()) {
        return apiMessage.trim();
      }

      return this.extractValidationMessage(parsed?.detail);
    } catch {
      return normalized;
    }
  }

  private fallbackMessageByStatus(status: number | undefined, fallbackMessage: string): string {
    if (status === 403) {
      return 'No tenés permisos para esta acción en el estado actual del ticket.';
    }

    return fallbackMessage;
  }

  private extractValidationMessage(detail: unknown): string | null {
    if (typeof detail === 'string' && detail.trim()) {
      return detail.trim();
    }

    if (!Array.isArray(detail)) {
      return null;
    }

    const messages = detail
      .map((item) => {
        if (!item || typeof item !== 'object') {
          return null;
        }

        const candidate = item as { msg?: unknown; loc?: unknown };
        if (typeof candidate.msg !== 'string' || !candidate.msg.trim()) {
          return null;
        }

        if (!Array.isArray(candidate.loc) || candidate.loc.length === 0) {
          return candidate.msg.trim();
        }

        const loc = candidate.loc
          .map((segment) => (typeof segment === 'string' || typeof segment === 'number' ? String(segment) : ''))
          .filter((segment) => segment.length > 0)
          .join('.');

        return loc ? `${loc}: ${candidate.msg.trim()}` : candidate.msg.trim();
      })
      .filter((item): item is string => Boolean(item));

    if (!messages.length) {
      return null;
    }

    return messages.join(' | ');
  }

  private normalizeTicketDetail(ticket: TicketDetail): TicketDetail {
    return {
      ...ticket,
      comments: (ticket.comments ?? []).map((comment) => ({
        ...comment,
        attachments: (comment.attachments ?? []).map((attachment) => this.normalizeAttachment(attachment))
      }))
    };
  }

  private normalizeAttachment(attachment: TicketAttachment): TicketAttachment {
    const normalizedPreview = this.resolveAttachmentUrl(attachment.previewUrl);
    const normalizedPublic = this.resolveAttachmentUrl(attachment.publicUrl);
    const normalizedStorage = this.resolveAttachmentUrl(attachment.storagePath);

    return {
      ...attachment,
      previewUrl: normalizedPreview ?? normalizedPublic ?? normalizedStorage ?? null,
      publicUrl: normalizedPublic ?? normalizedPreview ?? normalizedStorage ?? null,
      storagePath: attachment.storagePath ?? null
    };
  }

  private normalizeSatisfactionResponse(response: SatisfactionResponseDetailResponse): SatisfactionResponseDetailResponse {
    return {
      ...response,
      media_files: (response.media_files ?? []).map((media) => this.normalizeSatisfactionMedia(media))
    };
  }

  private normalizeSatisfactionMedia(media: SatisfactionMediaFile): SatisfactionMediaFile {
    return {
      ...media,
      file_path: this.resolveAttachmentUrl(media.file_path) ?? media.file_path
    };
  }

  private resolveAttachmentUrl(rawUrl: string | null | undefined): string | null {
    const normalized = rawUrl?.trim();
    if (!normalized) {
      return null;
    }

    if (/^https?:/i.test(normalized)) {
      return this.rewriteAbsoluteMediaUrl(normalized);
    }

    if (/^(blob:|data:)/i.test(normalized)) {
      return normalized;
    }

    const backendOrigin = this.resolveBackendOrigin();
    const slashNormalized = normalized.replace(/\\/g, '/');
    const lowerPath = slashNormalized.toLowerCase();
    const publicMarker = '/public/';
    const publicIndex = lowerPath.lastIndexOf(publicMarker);
    const normalizedPath = this.stripBackendPathPrefix(
      (publicIndex >= 0 ? slashNormalized.slice(publicIndex + publicMarker.length) : slashNormalized)
      .replace(/^\/?public\//i, '')
      .replace(/^\/+/, ''),
      backendOrigin
    );

    if (!normalizedPath || /^[a-z]:\//i.test(normalizedPath)) {
      return null;
    }

    // Avoid treating opaque ids/tokens as direct media URLs.
    if (!normalizedPath.includes('/') && !normalizedPath.includes('.')) {
      return null;
    }

    return `${backendOrigin}/${normalizedPath}`;
  }

  private rewriteAbsoluteMediaUrl(url: string): string {
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';

    try {
      const backend = new URL(this.resolveBackendOrigin(), browserOrigin);
      const absolute = new URL(url);

      if (absolute.origin !== backend.origin) {
        return url;
      }

      const backendPath = backend.pathname.replace(/\/+$/, '');
      if (!backendPath || backendPath === '/') {
        return url;
      }

      if (absolute.pathname.startsWith(`${backendPath}/`)) {
        return url;
      }

      if (absolute.pathname.startsWith('/media/')) {
        absolute.pathname = `${backendPath}${absolute.pathname}`;
        return absolute.toString();
      }

      return url;
    } catch {
      return url;
    }
  }

  private stripBackendPathPrefix(normalizedPath: string, backendOrigin: string): string {
    const backendPathPrefix = this.backendPathPrefix(backendOrigin);
    if (!backendPathPrefix) {
      return normalizedPath;
    }

    const lowerPath = normalizedPath.toLowerCase();
    const lowerPrefix = `${backendPathPrefix.toLowerCase()}/`;
    if (lowerPath === backendPathPrefix.toLowerCase()) {
      return '';
    }

    if (lowerPath.startsWith(lowerPrefix)) {
      return normalizedPath.slice(backendPathPrefix.length + 1);
    }

    return normalizedPath;
  }

  private backendPathPrefix(backendOrigin: string): string {
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';

    try {
      const parsed = new URL(backendOrigin, browserOrigin);
      return parsed.pathname.replace(/^\/+|\/+$/g, '');
    } catch {
      return '';
    }
  }

  private resolveBackendOrigin(): string {
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
    const normalizedBaseUrl = (crmApiConfig.baseUrl || '').trim();

    if (!normalizedBaseUrl) {
      return browserOrigin;
    }

    try {
      const parsed = new URL(normalizedBaseUrl, browserOrigin);
      const normalizedPath = parsed.pathname.replace(/\/+$/, '');
      return normalizedPath ? `${parsed.origin}${normalizedPath}` : parsed.origin;
    } catch {
      return browserOrigin;
    }
  }
}
