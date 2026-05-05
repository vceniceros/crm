import { MockUserRole } from './user-role.model';

export interface MockUserProfile {
  id: number | string;
  name: string;
  role: MockUserRole;
  roleLabel: string;
  initials: string;
  avatarUrl?: string | null;
}

export interface MockUsersData {
  users: MockUserProfile[];
}