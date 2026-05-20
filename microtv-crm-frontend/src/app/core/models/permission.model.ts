import { MockUserRole } from './user-role.model';

export type MockModuleKey =
  | 'dashboard'
  | 'tickets'
  | 'tasks'
  | 'inventory'
  | 'installations'
  | 'clients'
  | 'assets'
  | 'billing'
  | 'reports'
  | 'settings'
  | 'profile';

export interface MockModuleAccessRule {
  moduleKey: MockModuleKey;
  allowedRoles: MockUserRole[];
}
