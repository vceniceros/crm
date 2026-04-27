import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import {
  DashboardData,
  DashboardStat,
  DashboardSummaryApiResponse,
  RecentActivityItem,
  RecentTicket
} from '../models/dashboard.model';
import { crmApiConfig } from '../config/crm-api.config';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  getSummary(): Observable<DashboardData> {
    return this.request<DashboardSummaryApiResponse>('get', '/api/dashboard/summary').pipe(
      map((response) => this.mapDashboardSummary(response))
    );
  }

  private request<T>(method: 'get', path: string): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para cargar el dashboard.'));
    }

    const url = `${crmApiConfig.baseUrl}${path}`;
    return this.http.get<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
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

    return throwError(() => new Error('No se pudo cargar el resumen operativo.'));
  }

  private mapDashboardSummary(response: DashboardSummaryApiResponse): DashboardData {
    return {
      pageTitle: response.page_title,
      pageSubtitle: response.page_subtitle,
      stats: response.kpis.map((kpi) => this.mapKpi(kpi)),
      recentTickets: {
        title: 'Tickets Recientes',
        columns: [
          { key: 'id', label: 'ID' },
          { key: 'subject', label: 'Asunto' },
          { key: 'client', label: 'Cliente' },
          { key: 'priority', label: 'Prioridad' },
          { key: 'status', label: 'Estado' },
          { key: 'assignedTo', label: 'Asignado' }
        ],
        items: response.recent_tickets.map((ticket) => this.mapRecentTicket(ticket))
      },
      recentActivity: {
        title: 'Actividad Reciente',
        items: response.recent_activity.map((activity) => this.mapRecentActivity(activity))
      }
    };
  }

  private mapKpi(kpi: DashboardSummaryApiResponse['kpis'][number]): DashboardStat {
    return {
      label: kpi.label,
      value: String(kpi.value),
      sublabel: kpi.secondary,
      variant: kpi.variant
    };
  }

  private mapRecentTicket(ticket: DashboardSummaryApiResponse['recent_tickets'][number]): RecentTicket {
    return {
      id: ticket.ticket_public_id,
      ticketId: ticket.ticket_id,
      subject: ticket.subject,
      client: ticket.client,
      priority: this.normalizePriorityLabel(ticket.priority),
      priorityTone: ticket.priority_tone,
      status: this.normalizeStatusLabel(ticket.status),
      statusTone: ticket.status_tone,
      assignedTo: ticket.assigned_to,
      assignedInitials: ticket.assigned_initials,
      targetRoute: ticket.target_route
    };
  }

  private mapRecentActivity(activity: DashboardSummaryApiResponse['recent_activity'][number]): RecentActivityItem {
    return {
      type: activity.type,
      tone: activity.tone,
      text: activity.text,
      timestamp: this.formatRelativeTime(activity.timestamp),
      actor: activity.actor,
      targetRoute: activity.target_route ?? undefined
    };
  }

  private normalizePriorityLabel(priority: string): string {
    const normalized = priority.toUpperCase();
    if (normalized === 'CRITICAL') {
      return 'Crítica';
    }
    if (normalized === 'HIGH') {
      return 'Alta';
    }
    if (normalized === 'LOW') {
      return 'Baja';
    }
    return 'Media';
  }

  private normalizeStatusLabel(status: string): string {
    const normalized = status.toUpperCase();
    if (normalized === 'OPEN') {
      return 'Abierto';
    }
    if (normalized === 'IN_PROGRESS') {
      return 'En progreso';
    }
    if (normalized === 'ON_HOLD') {
      return 'Bloqueado';
    }
    if (normalized === 'PENDING_APPROVAL') {
      return 'Pendiente';
    }
    if (normalized === 'RESOLVED') {
      return 'Resuelto';
    }
    if (normalized === 'CLOSED') {
      return 'Cerrado';
    }
    return status;
  }

  private formatRelativeTime(isoTimestamp: string): string {
    const parsed = new Date(isoTimestamp);
    const time = parsed.getTime();
    if (Number.isNaN(time)) {
      return isoTimestamp;
    }

    const deltaSeconds = Math.floor((Date.now() - time) / 1000);
    if (deltaSeconds < 60) {
      return 'Hace instantes';
    }

    const deltaMinutes = Math.floor(deltaSeconds / 60);
    if (deltaMinutes < 60) {
      return `Hace ${deltaMinutes} min`;
    }

    const deltaHours = Math.floor(deltaMinutes / 60);
    if (deltaHours < 24) {
      return `Hace ${deltaHours} h`;
    }

    const deltaDays = Math.floor(deltaHours / 24);
    return `Hace ${deltaDays} d`;
  }
}
