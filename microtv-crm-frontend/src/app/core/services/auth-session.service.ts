import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable, Injector, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, distinctUntilChanged, map, shareReplay, tap } from 'rxjs';

import { crmApiConfig } from '../config/crm-api.config';
import { CurrentUser } from '../models/layout.model';
import { AuthenticatedUserResponse, CrmLoginResponse, LoginRequest, LoginSuccessResponse } from '../models/crm-auth.model';
import { PermissionService } from './permission.service';
import { resolveBackendAssetUrl } from '../utils/backend-asset-url.util';

type AuthStatus = 'checking' | 'authenticated' | 'anonymous';

interface AuthState {
  status: AuthStatus;
  session: LoginSuccessResponse | null;
}

const STORAGE_KEY = 'microtv.crm.session';

@Injectable({ providedIn: 'root' })
export class AuthSessionService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly injector = inject(Injector);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);
  private readonly stateSubject = new BehaviorSubject<AuthState>({
    status: 'checking',
    session: null
  });

  readonly state$ = this.stateSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly session$ = this.state$.pipe(
    map((state) => state.session),
    distinctUntilChanged(),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly currentUser$ = this.session$.pipe(
    map((session) => (session ? this.mapSessionToCurrentUser(session) : null)),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly isAuthenticated$ = this.state$.pipe(
    map((state) => state.status === 'authenticated'),
    distinctUntilChanged(),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  bootstrap(): void {
    if (!this.isBrowser) {
      this.stateSubject.next({ status: 'anonymous', session: null });
      return;
    }

    const storedSession = this.readStoredSession();
    if (!storedSession) {
      this.stateSubject.next({ status: 'anonymous', session: null });
      return;
    }

    this.stateSubject.next({ status: 'checking', session: storedSession });
    this.http
      .get<LoginSuccessResponse>(this.buildUrl('/auth/me'), {
        headers: new HttpHeaders({
          Authorization: `Bearer ${storedSession.tokens.access_token}`
        })
      })
      .subscribe({
        next: (session) => this.setAuthenticatedSession(session),
        error: () => {
          const returnUrl = this.router.url;
          this.logout({ navigate: false });
          void this.router.navigate(['/login'], {
            queryParams: returnUrl && returnUrl !== '/' ? { redirectTo: returnUrl } : {}
          });
        }
      });
  }

  login(payload: LoginRequest): Observable<CrmLoginResponse> {
    return this.http.post<CrmLoginResponse>(this.buildUrl('/auth/login'), payload).pipe(
      tap((response) => {
        if (response.status === 'authenticated') {
          this.setAuthenticatedSession(response);
        }
      })
    );
  }

  logout(options: { navigate?: boolean } = {}): void {
    if (this.isBrowser) {
      window.localStorage.removeItem(STORAGE_KEY);
    }

    this.stateSubject.next({ status: 'anonymous', session: null });
    this.permissionService().clear();

    if (options.navigate !== false) {
      void this.router.navigate(['/login']);
    }
  }

  isAuthenticatedSnapshot(): boolean {
    const state = this.stateSubject.value;
    return state.status === 'authenticated' || (state.status === 'checking' && state.session !== null);
  }

  sessionSnapshot(): LoginSuccessResponse | null {
    return this.stateSubject.value.session;
  }

  updateSessionUser(patch: Partial<AuthenticatedUserResponse>): void {
    const session = this.sessionSnapshot();
    if (!session) {
      return;
    }

    this.setAuthenticatedSession({
      ...session,
      user: {
        ...session.user,
        ...patch
      }
    });
  }

  private setAuthenticatedSession(session: LoginSuccessResponse): void {
    if (this.isBrowser) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    }

    this.stateSubject.next({ status: 'authenticated', session });
    this.permissionService().refresh();
  }

  private permissionService(): PermissionService {
    return this.injector.get(PermissionService);
  }

  private readStoredSession(): LoginSuccessResponse | null {
    if (!this.isBrowser) {
      return null;
    }

    const rawValue = window.localStorage.getItem(STORAGE_KEY);
    if (!rawValue) {
      return null;
    }

    try {
      return JSON.parse(rawValue) as LoginSuccessResponse;
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  }

  private mapSessionToCurrentUser(session: LoginSuccessResponse): CurrentUser {
    const displayName = session.user.display_name?.trim() || session.user.email || 'Usuario CRM';
    const initials = this.buildInitials(displayName);

    return {
      initials,
      name: displayName,
      role: this.mapRoleLabel(session.user.primary_role),
      avatarUrl: resolveBackendAssetUrl(session.user.avatar_url, crmApiConfig.baseUrl)
    };
  }

  private buildInitials(name: string): string {
    const normalized = name
      .split(' ')
      .map((segment) => segment.trim())
      .filter(Boolean)
      .slice(0, 2)
      .map((segment) => segment[0]?.toUpperCase() ?? '');

    return normalized.join('') || 'CRM';
  }

  private mapRoleLabel(roleKey: string): string {
    switch (roleKey) {
      case 'admin':
        return 'Administrador';
      case 'ejecutivo':
        return 'Ejecutivo';
      case 'deposito':
        return 'Encargado de deposito';
      case 'tecnico':
        return 'Tecnico';
      default:
        return roleKey;
    }
  }

  private buildUrl(path: string): string {
    return `${crmApiConfig.baseUrl}${path}`;
  }
}