import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, forkJoin, of, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { crmApiConfig } from '../../core/config/crm-api.config';
import { AuthSessionService } from '../../core/services/auth-session.service';
import { ReportFilterCatalogs, ReportId, ReportOption, ReportPayload, ReportRequestFilters } from './report.types';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class ReportsService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  loadFilterCatalogs(reportId: ReportId): Observable<ReportFilterCatalogs> {
    return forkJoin({
      users: this.requiresUserOptions(reportId) ? this.loadOptions('/api/reports/options/users') : of([]),
      clients: this.requiresClientOptions(reportId) ? this.loadOptions('/api/reports/options/clients') : of([]),
      categories: this.requiresCategoryOptions(reportId)
        ? this.loadOptions(this.usesOperationalCategories(reportId) ? '/api/reports/options/operational-categories' : '/api/reports/options/categories')
        : of([]),
      locations: reportId === 'my-tickets' ? this.loadOptions('/api/reports/options/locations') : of([]),
      roles: this.requiresRoleOptions(reportId) ? this.loadOptions('/api/reports/options/roles') : of([]),
      warehouses: reportId === 'stock-critical' ? this.loadOptions('/api/reports/options/warehouses') : of([]),
      technicians: reportId === 'tasks-by-status' || reportId === 'tasks-by-technician' ? this.loadOptions('/api/reports/options/technicians') : of([]),
      actionTypes: reportId === 'activity-by-user' ? this.loadOptions('/api/reports/options/action-types') : of([])
    });
  }

  loadReport(reportId: ReportId, filters: ReportRequestFilters): Observable<ReportPayload> {
    const endpoint = this.resolveEndpoint(reportId);
    if (!endpoint) {
      return throwError(() => new Error('Este reporte está marcado como próximamente.'));
    }

    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para consultar reportes.'));
    }

    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        return;
      }
      params = params.set(key, String(value));
    });

    return this.http
      .get<ReportPayload>(`${crmApiConfig.baseUrl}${endpoint}`, { headers, params })
      .pipe(catchError((error) => this.handleRequestError(error)));
  }

  private resolveEndpoint(reportId: ReportId): string | null {
    switch (reportId) {
      case 'my-tickets':
        return '/api/reports/my-tickets';
      case 'my-tasks':
        return '/api/reports/my-tasks';
      case 'tickets-by-status':
      case 'tickets-by-priority':
      case 'tickets-by-client':
        return '/api/reports/tickets';
      case 'tickets-by-category':
        return '/api/reports/category-resolution';
      case 'tasks-by-status':
      case 'tasks-by-technician':
        return '/api/reports/tasks';
      case 'stock-critical':
        return '/api/reports/stock-critical';
      case 'deposit-requests-status':
        return '/api/reports/deposit-requests';
      case 'activity-by-user':
        return '/api/reports/user-activity';
      case 'executive-performance':
      case 'executive-by-category':
      case 'executive-by-priority':
      case 'executive-by-client':
        return '/api/reports/executive/performance';
      default:
        return null;
    }
  }

  private requiresUserOptions(reportId: ReportId): boolean {
    return reportId === 'activity-by-user'
      || reportId === 'deposit-requests-status'
      || reportId === 'executive-performance'
      || reportId === 'executive-by-category'
      || reportId === 'executive-by-priority'
      || reportId === 'executive-by-client';
  }

  private requiresClientOptions(reportId: ReportId): boolean {
    return reportId === 'tickets-by-client'
      || reportId === 'my-tickets'
      || reportId === 'my-tasks'
      || reportId === 'executive-performance'
      || reportId === 'executive-by-category'
      || reportId === 'executive-by-priority'
      || reportId === 'executive-by-client';
  }

  private requiresCategoryOptions(reportId: ReportId): boolean {
    return reportId === 'stock-critical'
      || reportId === 'tickets-by-category'
      || reportId === 'my-tickets'
      || reportId === 'my-tasks'
      || reportId === 'executive-performance'
      || reportId === 'executive-by-category'
      || reportId === 'executive-by-priority'
      || reportId === 'executive-by-client';
  }

  private requiresRoleOptions(reportId: ReportId): boolean {
    return reportId === 'executive-performance'
      || reportId === 'executive-by-category'
      || reportId === 'executive-by-priority'
      || reportId === 'executive-by-client';
  }

  private usesOperationalCategories(reportId: ReportId): boolean {
    return reportId === 'tickets-by-category'
      || reportId === 'my-tickets'
      || reportId === 'my-tasks'
      || reportId === 'executive-performance'
      || reportId === 'executive-by-category'
      || reportId === 'executive-by-priority'
      || reportId === 'executive-by-client';
  }

  private loadOptions(path: string): Observable<ReportOption[]> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para consultar opciones de reportes.'));
    }

    return this.http
      .get<ReportOption[]>(`${crmApiConfig.baseUrl}${path}`, { headers })
      .pipe(catchError((error) => this.handleRequestError(error, 'No se pudieron cargar las opciones del filtro.')));
  }

  private buildAuthHeaders(): HttpHeaders | null {
    const accessToken = this.authSessionService.sessionSnapshot()?.tokens.access_token;
    if (!accessToken) {
      return null;
    }

    return new HttpHeaders({
      Authorization: `Bearer ${accessToken}`
    });
  }

  private handleRequestError(error: unknown, fallbackMessage = 'No se pudo cargar el reporte solicitado.'): Observable<never> {
    const apiMessage = (error as { error?: ApiErrorEnvelope })?.error?.error?.message;
    if (typeof apiMessage === 'string' && apiMessage.trim()) {
      return throwError(() => new Error(apiMessage));
    }

    return throwError(() => new Error(fallbackMessage));
  }
}
