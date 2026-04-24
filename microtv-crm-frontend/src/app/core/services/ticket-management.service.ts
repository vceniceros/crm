import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, Subject, throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import {
  ApproveTicketRequest,
  AssignTicketRequest,
  CloseTicketRequest,
  CreateTicketCommentRequest,
  CreateTicketRequest,
  RejectTicketApprovalRequest,
  ReopenTicketRequest,
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

    return throwError(() => new Error('No se pudo completar la operación de tickets.'));
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

  private resolveAttachmentUrl(rawUrl: string | null | undefined): string | null {
    const normalized = rawUrl?.trim();
    if (!normalized) {
      return null;
    }

    if (/^(https?:|blob:|data:)/i.test(normalized)) {
      return normalized;
    }

    const backendOrigin = this.resolveBackendOrigin();
    const normalizedPath = normalized.replace(/^\/?public\//i, '').replace(/^\/+/, '');
    return `${backendOrigin}/${normalizedPath}`;
  }

  private resolveBackendOrigin(): string {
    try {
      return new URL(crmApiConfig.baseUrl).origin;
    } catch {
      return crmApiConfig.baseUrl.replace(/\/$/, '');
    }
  }
}
