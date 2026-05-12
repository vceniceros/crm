import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { crmApiConfig } from '../config/crm-api.config';
import {
  ActivityLogFilters,
  ActivityLogPage,
  SettingsEffectivePermissions,
  SettingsAuthUser,
  SettingsAuthUserCreateRequest,
  SettingsAuthUserResetPasswordRequest,
  SettingsAuthUserRolesRequest,
  SettingsAuthUserStatusRequest,
  SettingsAuthUserUpdateRequest,
  SettingsCategory,
  SettingsCategoryWriteRequest,
  SettingsNotificationRule,
  SettingsNotificationRuleWriteRequest,
  SettingsPriority,
  SettingsPriorityWriteRequest,
  SettingsRole,
  SettingsRolePermission,
  SettingsRoleUpdateRequest,
  SettingsSlaRule,
  SettingsSlaRuleWriteRequest,
  SettingsStatus,
  SettingsStatusWriteRequest,
  SettingsTaskTemplate,
  SettingsTaskTemplateUpdateRequest,
  SettingsUserPermissionOverride,
  SettingsUserRoleAssignment,
  SettingsUserRoleAssignmentRequest
} from '../models/settings-management.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class SettingsManagementService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  listRoles(): Observable<SettingsRole[]> {
    return this.request<SettingsRole[]>('get', '/settings/roles');
  }

  updateRole(roleId: string, payload: SettingsRoleUpdateRequest): Observable<SettingsRole> {
    return this.request<SettingsRole>('put', `/settings/roles/${roleId}`, payload);
  }

  listUserRoles(): Observable<SettingsUserRoleAssignment[]> {
    return this.request<SettingsUserRoleAssignment[]>('get', '/settings/user-roles');
  }

  setUserRoles(userId: string, payload: SettingsUserRoleAssignmentRequest): Observable<SettingsUserRoleAssignment> {
    return this.request<SettingsUserRoleAssignment>('put', `/settings/user-roles/${userId}`, payload);
  }

  listAuthUsers(): Observable<SettingsAuthUser[]> {
    return this.request<SettingsAuthUser[]>('get', '/settings/auth-users');
  }

  createAuthUser(payload: SettingsAuthUserCreateRequest): Observable<SettingsAuthUser> {
    return this.request<SettingsAuthUser>('post', '/settings/auth-users', payload);
  }

  updateAuthUser(userId: string, payload: SettingsAuthUserUpdateRequest): Observable<SettingsAuthUser> {
    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}`, payload);
  }

  setAuthUserStatus(userId: string, payload: SettingsAuthUserStatusRequest): Observable<SettingsAuthUser> {
    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}/status`, payload);
  }

  setAuthUserRoles(userId: string, payload: SettingsAuthUserRolesRequest): Observable<SettingsAuthUser> {
    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}/roles`, payload);
  }

  resetAuthUserPassword(userId: string, payload: SettingsAuthUserResetPasswordRequest): Observable<SettingsAuthUser> {
    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}/reset-password`, payload);
  }

  listCategories(type?: string): Observable<SettingsCategory[]> {
    const query = type ? `?type=${encodeURIComponent(type)}` : '';
    return this.request<SettingsCategory[]>('get', `/settings/categories${query}`);
  }

  createCategory(payload: SettingsCategoryWriteRequest): Observable<SettingsCategory> {
    return this.request<SettingsCategory>('post', '/settings/categories', payload);
  }

  updateCategory(categoryId: string, payload: SettingsCategoryWriteRequest): Observable<SettingsCategory> {
    return this.request<SettingsCategory>('put', `/settings/categories/${categoryId}`, payload);
  }

  listPriorities(): Observable<SettingsPriority[]> {
    return this.request<SettingsPriority[]>('get', '/settings/priorities');
  }

  createPriority(payload: SettingsPriorityWriteRequest): Observable<SettingsPriority> {
    return this.request<SettingsPriority>('post', '/settings/priorities', payload);
  }

  updatePriority(priorityId: string, payload: SettingsPriorityWriteRequest): Observable<SettingsPriority> {
    return this.request<SettingsPriority>('put', `/settings/priorities/${priorityId}`, payload);
  }

  listStatuses(entityType?: string): Observable<SettingsStatus[]> {
    const query = entityType ? `?entity_type=${encodeURIComponent(entityType)}` : '';
    return this.request<SettingsStatus[]>('get', `/settings/statuses${query}`);
  }

  createStatus(payload: SettingsStatusWriteRequest): Observable<SettingsStatus> {
    return this.request<SettingsStatus>('post', '/settings/statuses', payload);
  }

  updateStatus(statusId: string, payload: SettingsStatusWriteRequest): Observable<SettingsStatus> {
    return this.request<SettingsStatus>('put', `/settings/statuses/${statusId}`, payload);
  }

  listTaskTemplates(): Observable<SettingsTaskTemplate[]> {
    return this.request<SettingsTaskTemplate[]>('get', '/settings/task-templates');
  }

  updateTaskTemplate(templateId: string, payload: SettingsTaskTemplateUpdateRequest): Observable<SettingsTaskTemplate> {
    return this.request<SettingsTaskTemplate>('put', `/settings/task-templates/${templateId}`, payload);
  }

  listSlaRules(): Observable<SettingsSlaRule[]> {
    return this.request<SettingsSlaRule[]>('get', '/settings/sla');
  }

  createSlaRule(payload: SettingsSlaRuleWriteRequest): Observable<SettingsSlaRule> {
    return this.request<SettingsSlaRule>('post', '/settings/sla', payload);
  }

  updateSlaRule(ruleId: string, payload: SettingsSlaRuleWriteRequest): Observable<SettingsSlaRule> {
    return this.request<SettingsSlaRule>('put', `/settings/sla/${ruleId}`, payload);
  }

  listNotificationRules(): Observable<SettingsNotificationRule[]> {
    return this.request<SettingsNotificationRule[]>('get', '/settings/notification-rules');
  }

  createNotificationRule(payload: SettingsNotificationRuleWriteRequest): Observable<SettingsNotificationRule> {
    return this.request<SettingsNotificationRule>('post', '/settings/notification-rules', payload);
  }

  updateNotificationRule(ruleId: string, payload: SettingsNotificationRuleWriteRequest): Observable<SettingsNotificationRule> {
    return this.request<SettingsNotificationRule>('put', `/settings/notification-rules/${ruleId}`, payload);
  }

  listRolePermissions(): Observable<SettingsRolePermission[]> {
    return this.request<SettingsRolePermission[]>('get', '/settings/permissions/roles');
  }

  updateRolePermission(roleKey: string, code: string, isGranted: boolean): Observable<SettingsRolePermission> {
    return this.request<SettingsRolePermission>('put', `/settings/permissions/roles/${encodeURIComponent(roleKey)}/${encodeURIComponent(code)}`, {
      is_granted: isGranted
    });
  }

  listUserPermissionOverrides(): Observable<SettingsUserPermissionOverride[]> {
    return this.request<SettingsUserPermissionOverride[]>('get', '/settings/permissions/users');
  }

  updateUserPermission(userId: string, code: string, isGranted: boolean): Observable<void> {
    return this.request<void>('put', `/settings/permissions/users/${encodeURIComponent(userId)}/${encodeURIComponent(code)}`, {
      is_granted: isGranted
    });
  }

  deleteUserPermission(userId: string, code: string): Observable<void> {
    return this.request<void>('delete', `/settings/permissions/users/${encodeURIComponent(userId)}/${encodeURIComponent(code)}`);
  }

  getMyEffectivePermissions(): Observable<SettingsEffectivePermissions> {
    return this.request<{ permissions: SettingsEffectivePermissions }>('get', '/settings/permissions/me').pipe(
      map((response) => response.permissions ?? {})
    );
  }

  listActivityLog(filters: ActivityLogFilters): Observable<ActivityLogPage> {
    const params = new URLSearchParams();
    if (filters.userId) params.set('user_id', filters.userId);
    if (filters.eventCode) params.set('event_code', filters.eventCode);
    if (filters.entityType) params.set('entity_type', filters.entityType);
    if (filters.dateFrom) params.set('date_from', filters.dateFrom);
    if (filters.dateTo) params.set('date_to', filters.dateTo);
    params.set('page', String(filters.page));
    params.set('per_page', String(filters.perPage));
    return this.request<ActivityLogPage>('get', `/activity-log?${params.toString()}`);
  }

  private request<T>(method: 'get' | 'post' | 'put' | 'delete', path: string, body?: unknown): Observable<T> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return throwError(() => new Error('No hay una sesión autenticada válida para operar configuración.'));
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

    return throwError(() => new Error('No se pudo completar la operación de configuración.'));
  }
}
