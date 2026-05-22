import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import {
  CreateKnowledgeArticleRequest,
  KnowledgeArticleDetail,
  KnowledgeArticleListItem,
  KnowledgeAttachment,
  KnowledgeCategory,
  UpdateKnowledgeArticleRequest
} from '../models/knowledge.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: { message?: string };
  detail?: unknown;
}

@Injectable({ providedIn: 'root' })
export class KnowledgeBaseService {
  private readonly http = inject(HttpClient);
  private readonly authSession = inject(AuthSessionService);

  listCategories(): Observable<KnowledgeCategory[]> {
    return this.request<KnowledgeCategory[]>('get', '/knowledge-base/categories');
  }

  listArticles(filters: { search?: string; categoryId?: string | null; status?: 'draft' | 'published' | null } = {}): Observable<KnowledgeArticleListItem[]> {
    const params = new URLSearchParams();
    if (filters.search?.trim()) {
      params.set('search', filters.search.trim());
    }
    if (filters.categoryId) {
      params.set('category_id', filters.categoryId);
    }
    if (filters.status !== undefined) {
      params.set('status', filters.status ?? '');
    }
    const query = params.toString();
    return this.request<KnowledgeArticleListItem[]>('get', `/knowledge-base/articles${query ? `?${query}` : ''}`);
  }

  getArticle(articleId: string): Observable<KnowledgeArticleDetail> {
    return this.request<KnowledgeArticleDetail>('get', `/knowledge-base/articles/${encodeURIComponent(articleId)}`).pipe(
      map((article) => this.normalizeArticle(article))
    );
  }

  createArticle(payload: CreateKnowledgeArticleRequest): Observable<KnowledgeArticleDetail> {
    return this.request<KnowledgeArticleDetail>('post', '/knowledge-base/articles', payload).pipe(map((article) => this.normalizeArticle(article)));
  }

  updateArticle(articleId: string, payload: UpdateKnowledgeArticleRequest): Observable<KnowledgeArticleDetail> {
    return this.request<KnowledgeArticleDetail>('put', `/knowledge-base/articles/${encodeURIComponent(articleId)}`, payload).pipe(
      map((article) => this.normalizeArticle(article))
    );
  }

  deleteArticle(articleId: string): Observable<void> {
    return this.request<void>('delete', `/knowledge-base/articles/${encodeURIComponent(articleId)}`);
  }

  uploadAttachment(articleId: string, file: File): Observable<KnowledgeAttachment> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesion autenticada valida.'));
    }
    const formData = new FormData();
    formData.append('file', file);
    return this.http
      .post<KnowledgeAttachment>(`${crmApiConfig.baseUrl}/knowledge-base/articles/${encodeURIComponent(articleId)}/attachments`, formData, { headers })
      .pipe(map((attachment) => this.normalizeAttachment(attachment)), catchError((error) => this.handleRequestError(error)));
  }

  deleteAttachment(articleId: string, attachmentId: string): Observable<void> {
    return this.request<void>('delete', `/knowledge-base/articles/${encodeURIComponent(articleId)}/attachments/${encodeURIComponent(attachmentId)}`);
  }

  private request<T>(method: 'get' | 'post' | 'put' | 'delete', path: string, body?: unknown): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesion autenticada valida.'));
    }
    const url = `${crmApiConfig.baseUrl}${path}`;
    if (method === 'get') {
      return this.http.get<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }
    if (method === 'put') {
      return this.http.put<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }
    if (method === 'delete') {
      return this.http.delete<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
    }
    return this.http.post<T>(url, body ?? {}, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
  }

  private buildAuthHeaders(): HttpHeaders | null {
    const accessToken = this.authSession.sessionSnapshot()?.tokens.access_token;
    return accessToken ? new HttpHeaders({ Authorization: `Bearer ${accessToken}` }) : null;
  }

  private normalizeArticle(article: KnowledgeArticleDetail): KnowledgeArticleDetail {
    return { ...article, attachments: (article.attachments ?? []).map((attachment) => this.normalizeAttachment(attachment)) };
  }

  private normalizeAttachment(attachment: KnowledgeAttachment): KnowledgeAttachment {
    const rawUrl = attachment.file_url || '';
    if (/^(https?:|blob:|data:)/i.test(rawUrl)) {
      return attachment;
    }
    const backendOrigin = this.resolveBackendOrigin();
    const path = rawUrl.replace(/^\/+/, '');
    return { ...attachment, file_url: `${backendOrigin}/${path}` };
  }

  private resolveBackendOrigin(): string {
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
    try {
      const parsed = new URL(crmApiConfig.baseUrl, browserOrigin);
      return parsed.pathname.replace(/\/+$/, '') ? `${parsed.origin}${parsed.pathname.replace(/\/+$/, '')}` : parsed.origin;
    } catch {
      return browserOrigin;
    }
  }

  private handleRequestError(error: unknown): Observable<never> {
    const payload = (error as { error?: ApiErrorEnvelope })?.error;
    const apiMessage = payload?.error?.message;
    if (apiMessage?.trim()) {
      return throwError(() => new Error(apiMessage.trim()));
    }
    if (Array.isArray(payload?.detail)) {
      const messages = payload.detail
        .map((item) => (item && typeof item === 'object' && 'msg' in item ? String((item as { msg: unknown }).msg) : ''))
        .filter(Boolean);
      if (messages.length) {
        return throwError(() => new Error(messages.join(' | ')));
      }
    }
    return throwError(() => new Error('No se pudo completar la operacion de base de conocimientos.'));
  }
}
