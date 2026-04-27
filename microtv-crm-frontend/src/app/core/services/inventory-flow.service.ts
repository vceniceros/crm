import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import {
  ConfirmDispatchItemRequest,
  CreateInventoryRequestRequest,
  CreateTaskDispatchRequest,
  InventoryDispatch,
  InventoryRequest,
  InventorySourceFlow,
  ReviewInventoryRequestRequest
} from '../models/inventory-flow.model';
import { TaskDetail } from '../models/task-management.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class InventoryFlowService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  createRequest(payload: CreateInventoryRequestRequest): Observable<InventoryRequest> {
    return this.request<InventoryRequest>('post', '/inventory-flow/requests', payload);
  }

  reviewRequest(requestId: string, payload: ReviewInventoryRequestRequest): Observable<InventoryRequest> {
    return this.request<InventoryRequest>('post', `/inventory-flow/requests/${requestId}/review`, payload);
  }

  dispatchRequest(requestId: string, payload: CreateTaskDispatchRequest): Observable<TaskDetail | InventoryDispatch> {
    return this.request<TaskDetail | InventoryDispatch>('post', `/inventory-flow/requests/${requestId}/dispatches`, payload);
  }

  getSourceFlow(sourceType: 'TASK' | 'TICKET', sourceReferenceId: string): Observable<InventorySourceFlow> {
    return this.request<InventorySourceFlow>('get', `/inventory-flow/sources/${sourceType}/${encodeURIComponent(sourceReferenceId)}`);
  }

  listOpenRequests(): Observable<InventoryRequest[]> {
    return this.request<InventoryRequest[]>('get', '/inventory-flow/requests/open');
  }

  createTaskDispatch(taskId: string, payload: CreateTaskDispatchRequest): Observable<TaskDetail> {
    return this.request<TaskDetail>('post', `/inventory-flow/tasks/${taskId}/dispatches`, payload);
  }

  confirmDispatchItem(dispatchItemId: string, payload: ConfirmDispatchItemRequest): Observable<TaskDetail | InventoryDispatch> {
    return this.request<TaskDetail | InventoryDispatch>('post', `/inventory-flow/dispatch-items/${dispatchItemId}/confirmations`, payload);
  }

  private request<T>(method: 'get' | 'post', path: string, body?: unknown): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar materiales y solicitudes.'));
    }

    const url = `${crmApiConfig.baseUrl}${path}`;
    if (method === 'get') {
      return this.http.get<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }

    return this.http.post<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
  }

  private buildAuthHeaders(): HttpHeaders | null {
    const accessToken = this.authSessionService.sessionSnapshot()?.tokens.access_token;
    if (!accessToken) {
      return null;
    }

    return new HttpHeaders({ Authorization: `Bearer ${accessToken}` });
  }

  private handleRequestError(error: unknown): Observable<never> {
    const apiMessage = (error as { error?: ApiErrorEnvelope })?.error?.error?.message;
    if (typeof apiMessage === 'string' && apiMessage.trim()) {
      return throwError(() => new Error(apiMessage));
    }

    return throwError(() => new Error('No se pudo completar la operación de materiales y solicitudes.'));
  }
}