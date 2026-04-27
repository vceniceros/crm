import { MockUserRole } from './user-role.model';

export type MockModuleKey =
  | 'dashboard'
  | 'tickets'
  | 'tasks'
  | 'inventory'
  | 'installations'
  | 'clients'
  | 'billing'
  | 'reports'
  | 'settings';

export interface MockModuleAccessRule {
  moduleKey: MockModuleKey;
  allowedRoles: MockUserRole[];
}