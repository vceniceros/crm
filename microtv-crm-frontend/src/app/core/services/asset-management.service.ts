import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import {
  Asset,
  AssetCategory,
  AssetLinkedTask,
  AssetLinkedTicket,
  AssetSummary,
  CreateAssetCategoryPayload,
  CreateAssetPayload,
  UpdateAssetPayload
} from '../models/asset.model';
import { AuthSessionService } from './auth-session.service';

@Injectable({ providedIn: 'root' })
export class AssetManagementService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  listCategories(): Observable<AssetCategory[]> {
    return this.request<AssetCategory[]>('get', '/asset-categories');
  }

  createCategory(payload: CreateAssetCategoryPayload): Observable<AssetCategory> {
    return this.request<AssetCategory>('post', '/asset-categories', payload);
  }

  listAssets(filters: { clientId?: string | null; categoryId?: string | null; search?: string | null } = {}): Observable<AssetSummary[]> {
    const params = new URLSearchParams();
    if (filters.clientId) {
      params.set('client_id', filters.clientId);
    }
    if (filters.categoryId) {
      params.set('category_id', filters.categoryId);
    }
    if (filters.search) {
      params.set('search', filters.search);
    }
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return this.request<AssetSummary[]>('get', `/assets${suffix}`);
  }

  getAsset(assetId: string): Observable<Asset> {
    return this.request<Asset>('get', `/assets/${assetId}`);
  }

  createAsset(payload: CreateAssetPayload): Observable<Asset> {
    return this.request<Asset>('post', '/assets', payload);
  }

  updateAsset(assetId: string, payload: UpdateAssetPayload): Observable<Asset> {
    return this.request<Asset>('patch', `/assets/${assetId}`, payload);
  }

  deleteAsset(assetId: string): Observable<void> {
    return this.request<void>('delete', `/assets/${assetId}`);
  }

  getTicketAssets(ticketId: string): Observable<AssetSummary[]> {
    return this.request<AssetSummary[]>('get', `/tickets/${ticketId}/assets`);
  }

  linkAssetToTicket(ticketId: string, assetId: string): Observable<void> {
    return this.request<void>('post', `/tickets/${ticketId}/assets`, { asset_id: assetId });
  }

  unlinkAssetFromTicket(ticketId: string, assetId: string): Observable<void> {
    return this.request<void>('delete', `/tickets/${ticketId}/assets/${assetId}`);
  }

  getTaskAssets(taskId: string): Observable<AssetSummary[]> {
    return this.request<AssetSummary[]>('get', `/tasks/${taskId}/assets`);
  }

  linkAssetToTask(taskId: string, assetId: string): Observable<void> {
    return this.request<void>('post', `/tasks/${taskId}/assets`, { asset_id: assetId });
  }

  unlinkAssetFromTask(taskId: string, assetId: string): Observable<void> {
    return this.request<void>('delete', `/tasks/${taskId}/assets/${assetId}`);
  }

  getLinkedTicketsForAsset(assetId: string): Observable<AssetLinkedTicket[]> {
    return this.request<AssetLinkedTicket[]>('get', `/assets/${assetId}/tickets`);
  }

  getLinkedTasksForAsset(assetId: string): Observable<AssetLinkedTask[]> {
    return this.request<AssetLinkedTask[]>('get', `/assets/${assetId}/tasks`);
  }

  private request<T>(method: 'get' | 'post' | 'patch' | 'delete', path: string, body?: unknown): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesion autenticada valida para operar activos.'));
    }
    const url = `${crmApiConfig.baseUrl}${path}`;
    if (method === 'get') {
      return this.http.get<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }
    if (method === 'patch') {
      return this.http.patch<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }
    if (method === 'delete') {
      return this.http.delete<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }
    return this.http.post<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
  }

  private buildAuthHeaders(): HttpHeaders | null {
    const accessToken = this.authSessionService.sessionSnapshot()?.tokens.access_token;
    return accessToken ? new HttpHeaders({ Authorization: `Bearer ${accessToken}` }) : null;
  }

  private handleRequestError(error: unknown): Observable<never> {
    const apiMessage = (error as { error?: { error?: { message?: string } } })?.error?.error?.message;
    return throwError(() => new Error(apiMessage || 'No fue posible completar la operacion de activos.'));
  }
}
