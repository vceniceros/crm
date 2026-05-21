import { HttpClient, HttpEvent, HttpEventType, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, Subject, throwError } from 'rxjs';
import { catchError, filter, map, tap } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import {
  ApproveTaskRequest,
  AssignSubtaskRequest,
  ClientSummary,
  CreateTaskCommentRequest,
  CreateLocationRequest,
  CrmUserOption,
  CreateTaskFromTemplateRequest,
  GenerateTaskSatisfactionFormResponse,
  PublicTaskPreFormInfoResponse,
  PublicTaskSatisfactionFormInfoResponse,
  PersistedLocation,
  CreateTaskTemplateRequest,
  ExecuteSubtaskActionRequest,
  RejectTaskApprovalRequest,
  SetTaskTemplateActivationRequest,
  TaskDetail,
  TaskPreFormStatusResponse,
  TaskSatisfactionFormStatusResponse,
  TaskSatisfactionResponseDetailResponse,
  TaskSummary,
  TaskTemplate,
  SubmitTaskPreFormRequest,
  SubmitTaskSatisfactionFormRequest,
  UnassignedSubtaskQueueItem,
  UpdateSubtaskProgressRequest,
  UpdateTaskTemplateRequest
} from '../models/task-management.model';
import { TaskAttachment } from '../models/task-attachment.model';
import { AppLocation } from '../models/location.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class TaskManagementService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly badgeRefreshSubject = new Subject<void>();

  readonly badgeRefresh$ = this.badgeRefreshSubject.asObservable();

  listTemplates(): Observable<TaskTemplate[]> {
    return this.request<TaskTemplate[]>('get', '/tasks/templates');
  }

  getTemplate(templateId: string): Observable<TaskTemplate> {
    return this.request<TaskTemplate>('get', `/tasks/templates/${templateId}`);
  }

  createTemplate(payload: CreateTaskTemplateRequest): Observable<TaskTemplate> {
    return this.request<TaskTemplate>('post', '/tasks/templates', payload);
  }

  updateTemplate(templateId: string, payload: UpdateTaskTemplateRequest): Observable<TaskTemplate> {
    return this.request<TaskTemplate>('put', `/tasks/templates/${templateId}`, payload);
  }

  setTemplateActivation(templateId: string, payload: SetTaskTemplateActivationRequest): Observable<TaskTemplate> {
    return this.request<TaskTemplate>('patch', `/tasks/templates/${templateId}/activation`, payload);
  }

  listClients(): Observable<ClientSummary[]> {
    return this.request<ClientSummary[]>('get', '/clients');
  }

  listCrmUsersByRole(roleKey: string): Observable<CrmUserOption[]> {
    return this.request<CrmUserOption[]>('get', `/crm-users?role_key=${encodeURIComponent(roleKey)}`);
  }

  createTaskFromTemplate(payload: CreateTaskFromTemplateRequest): Observable<TaskDetail> {
    return this.request<TaskDetail>('post', '/tasks', payload).pipe(
      map((task) => this.normalizeTaskDetail(task)),
      tap(() => this.badgeRefreshSubject.next())
    );
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
      formatted_address: string | null;
    }>('post', '/locations', payload).pipe(map((response) => this.mapPersistedLocation(response)));
  }

  listAssignedTasks(): Observable<TaskSummary[]> {
    return this.request<TaskSummary[]>('get', '/tasks/assigned/me');
  }

  listTrackingTasks(): Observable<TaskSummary[]> {
    return this.request<TaskSummary[]>('get', '/tasks/tracking/me');
  }

  listTaskHistory(): Observable<TaskSummary[]> {
    return this.request<TaskSummary[]>('get', '/tasks/history/me');
  }

  listUnassignedSubtasks(): Observable<UnassignedSubtaskQueueItem[]> {
    return this.request<UnassignedSubtaskQueueItem[]>('get', '/tasks/unassigned/me');
  }

  getTaskDetail(taskId: string): Observable<TaskDetail> {
    return this.request<TaskDetail>('get', `/tasks/${taskId}`).pipe(map((task) => this.normalizeTaskDetail(task)));
  }

  claimSubtask(subtaskId: string): Observable<TaskDetail> {
    return this.request<TaskDetail>('post', `/tasks/subtasks/${subtaskId}/claim`, {}).pipe(
      map((task) => this.normalizeTaskDetail(task)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  saveSubtaskProgress(subtaskId: string, payload: UpdateSubtaskProgressRequest): Observable<TaskDetail> {
    return this.request<TaskDetail>('put', `/tasks/subtasks/${subtaskId}/items`, payload).pipe(
      map((task) => this.normalizeTaskDetail(task))
    );
  }

  executeSubtaskAction(subtaskId: string, payload: ExecuteSubtaskActionRequest): Observable<TaskDetail> {
    return this.request<TaskDetail>('post', `/tasks/subtasks/${subtaskId}/actions`, payload).pipe(
      map((task) => this.normalizeTaskDetail(task)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  assignSubtask(subtaskId: string, payload: AssignSubtaskRequest): Observable<TaskDetail> {
    return this.request<TaskDetail>('patch', `/tasks/subtasks/${subtaskId}/assignment`, payload).pipe(
      map((task) => this.normalizeTaskDetail(task)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  approveTask(taskId: string, payload: ApproveTaskRequest = {}): Observable<TaskDetail> {
    return this.request<TaskDetail>('patch', `/tasks/${taskId}/approve`, payload).pipe(
      map((task) => this.normalizeTaskDetail(task)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  rejectTaskApproval(taskId: string, payload: RejectTaskApprovalRequest): Observable<TaskDetail> {
    return this.request<TaskDetail>('patch', `/tasks/${taskId}/reject`, payload).pipe(
      map((task) => this.normalizeTaskDetail(task)),
      tap(() => this.badgeRefreshSubject.next())
    );
  }

  uploadTaskAttachments(taskId: string, files: readonly File[], subtaskId?: string | null): Observable<TaskAttachment[]> {
    return this.uploadTaskAttachmentsWithProgress(taskId, files, subtaskId).pipe(
      filter((event) => event.type === HttpEventType.Response),
      map((event) => event.body ?? [])
    );
  }

  uploadTaskAttachmentsWithProgress(taskId: string, files: readonly File[], subtaskId?: string | null): Observable<HttpEvent<TaskAttachment[]>> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tareas.'));
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    if (subtaskId) {
      formData.append('subtask_id', subtaskId);
    }

    return this.http
      .post<TaskAttachment[]>(`${crmApiConfig.baseUrl}/tasks/${taskId}/attachments`, formData, {
        headers,
        observe: 'events',
        reportProgress: true
      })
      .pipe(
        map((event) => event.type === HttpEventType.Response
          ? event.clone({ body: (event.body ?? []).map((attachment) => this.normalizeAttachment(attachment)) })
          : event),
        catchError((error) => this.handleRequestError(error))
      );
  }

  deleteTaskAttachment(attachmentId: string): Observable<void> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tareas.'));
    }

    return this.http
      .delete<void>(`${crmApiConfig.baseUrl}/tasks/attachments/${attachmentId}`, { headers })
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  addTaskComment(taskId: string, payload: CreateTaskCommentRequest): Observable<TaskDetail> {
    return this.request<TaskDetail>('post', `/tasks/${taskId}/comments`, payload).pipe(
      map((task) => this.normalizeTaskDetail(task))
    );
  }

  exportTaskHistory(taskId: string): Observable<Blob> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tareas.'));
    }

    return this.http
      .get(`${crmApiConfig.baseUrl}/tasks/${taskId}/export`, {
        headers,
        responseType: 'blob'
      })
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  generateTaskSatisfactionForm(taskId: string): Observable<GenerateTaskSatisfactionFormResponse> {
    return this.request<GenerateTaskSatisfactionFormResponse>('post', `/tasks/${taskId}/satisfaction-form`);
  }

  getTaskSatisfactionFormStatus(taskId: string): Observable<TaskSatisfactionFormStatusResponse> {
    return this.request<TaskSatisfactionFormStatusResponse>('get', `/tasks/${taskId}/satisfaction-form/status`);
  }

  getTaskSatisfactionResponse(taskId: string): Observable<TaskSatisfactionResponseDetailResponse> {
    return this.request<TaskSatisfactionResponseDetailResponse>('get', `/tasks/${taskId}/satisfaction-response`);
  }

  generateTaskPreFormLink(taskId: string): Observable<TaskPreFormStatusResponse> {
    return this.request<TaskPreFormStatusResponse>('post', `/tasks/${taskId}/pre-form/generate`);
  }

  getTaskPreFormStatus(taskId: string): Observable<TaskPreFormStatusResponse> {
    return this.request<TaskPreFormStatusResponse>('get', `/tasks/${taskId}/pre-form/status`);
  }

  getPublicTaskSatisfactionForm(token: string): Observable<PublicTaskSatisfactionFormInfoResponse> {
    return this.http
      .get<PublicTaskSatisfactionFormInfoResponse>(`${crmApiConfig.baseUrl}/public/tasks/satisfaction/${encodeURIComponent(token)}`)
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  submitPublicTaskSatisfactionForm(
    token: string,
    payload: SubmitTaskSatisfactionFormRequest
  ): Observable<TaskSatisfactionResponseDetailResponse> {
    return this.http
      .post<TaskSatisfactionResponseDetailResponse>(`${crmApiConfig.baseUrl}/public/tasks/satisfaction/${encodeURIComponent(token)}`, payload)
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  getPublicTaskPreForm(token: string): Observable<PublicTaskPreFormInfoResponse> {
    return this.http
      .get<PublicTaskPreFormInfoResponse>(`${crmApiConfig.baseUrl}/pre-form/${encodeURIComponent(token)}`)
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  submitPublicTaskPreForm(token: string, payload: SubmitTaskPreFormRequest): Observable<{ status: string }> {
    return this.http
      .post<{ status: string }>(`${crmApiConfig.baseUrl}/pre-form/${encodeURIComponent(token)}`, payload)
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  private request<T>(method: 'get' | 'post' | 'put' | 'patch', path: string, body?: unknown): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar tareas.'));
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

    return throwError(() => new Error('No se pudo completar la operación de tareas.'));
  }

  private normalizeTaskDetail(task: TaskDetail): TaskDetail {
    return {
      ...task,
      comments: (task.comments ?? []).map((comment) => ({
        ...comment,
        attachments: (comment.attachments ?? []).map((attachment) => this.normalizeAttachment(attachment))
      }))
    };
  }

  private normalizeAttachment(attachment: TaskAttachment): TaskAttachment {
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
    const slashNormalized = normalized.replace(/\\/g, '/');
    const lowerPath = slashNormalized.toLowerCase();
    const publicMarker = '/public/';
    const publicIndex = lowerPath.lastIndexOf(publicMarker);
    const normalizedPath = (publicIndex >= 0 ? slashNormalized.slice(publicIndex + publicMarker.length) : slashNormalized)
      .replace(/^\/?public\//i, '')
      .replace(/^\/+/, '');

    if (!normalizedPath || /^[a-z]:\//i.test(normalizedPath)) {
      return null;
    }

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
