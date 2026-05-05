import { Injectable } from '@angular/core';
import { inject } from '@angular/core';
import { map, shareReplay } from 'rxjs';

import { LoginSuccessResponse } from '../models/crm-auth.model';
import { MockUserProfile, MockUsersData } from '../models/user-profile.model';
import { MockUserRole } from '../models/user-role.model';
import { AuthSessionService } from './auth-session.service';
import usersData from '../../../mocks/users-data.json';

const mockUsers = (usersData as MockUsersData).users;
const defaultUser = mockUsers[0];

@Injectable({ providedIn: 'root' })
export class MockUserContextService {
  private readonly authSessionService = inject(AuthSessionService);

  readonly activeUser$ = this.authSessionService.session$.pipe(
    map((session) => this.mapSessionToUser(session) ?? defaultUser),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly users$ = this.activeUser$.pipe(
    map((activeUser) => [activeUser]),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  getUsers() {
    return this.users$;
  }

  activeUser() {
    return this.activeUser$;
  }

  getActiveUserSnapshot(): MockUserProfile {
    return this.mapSessionToUser(this.authSessionService.sessionSnapshot()) ?? defaultUser;
  }

  setActiveUser(_: number | string): void {}

  private mapSessionToUser(session: LoginSuccessResponse | null): MockUserProfile | null {
    if (!session) {
      return null;
    }

    const role = this.normalizeRole(session.user.primary_role);
    const templateUser = mockUsers.find((user) => user.role === role) ?? defaultUser;
    const displayName = session.user.display_name?.trim() || session.user.email || templateUser.name;

    return {
      id: templateUser.id,
      name: displayName,
      role,
      roleLabel: this.mapRoleLabel(role),
      initials: this.buildInitials(displayName),
      avatarUrl: session.user.avatar_url ?? null
    };
  }

  private normalizeRole(roleKey: string): MockUserRole {
    if (roleKey === 'admin' || roleKey === 'ejecutivo' || roleKey === 'deposito' || roleKey === 'tecnico') {
      return roleKey;
    }

    return defaultUser.role;
  }

  private mapRoleLabel(role: MockUserRole): string {
    switch (role) {
      case 'admin':
        return 'Administrador';
      case 'ejecutivo':
        return 'Ejecutivo';
      case 'deposito':
        return 'Encargado de deposito';
      case 'tecnico':
        return 'Tecnico';
    }
  }

  private buildInitials(displayName: string): string {
    return displayName
      .split(' ')
      .map((segment) => segment.trim())
      .filter(Boolean)
      .slice(0, 2)
      .map((segment) => segment[0]?.toUpperCase() ?? '')
      .join('') || defaultUser.initials;
  }
}

export type { MockUserProfile };