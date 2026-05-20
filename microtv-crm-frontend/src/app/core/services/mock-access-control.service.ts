import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { NavigationSection } from '../models/navigation.model';
import { MockModuleAccessRule, MockModuleKey } from '../models/permission.model';
import { TaskListItem } from '../models/task.model';
import { TicketListItem } from '../models/ticket.model';
import { MockUserProfile } from '../models/user-profile.model';
import { MockUserRole } from '../models/user-role.model';
import { MockUserContextService } from './mock-user-context.service';

const moduleRules: MockModuleAccessRule[] = [
  { moduleKey: 'dashboard', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] },
  { moduleKey: 'tickets', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] },
  { moduleKey: 'tasks', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] },
  { moduleKey: 'inventory', allowedRoles: ['admin', 'ejecutivo', 'deposito'] },
  { moduleKey: 'installations', allowedRoles: ['admin', 'ejecutivo'] },
  { moduleKey: 'clients', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] },
  { moduleKey: 'assets', allowedRoles: ['admin', 'ejecutivo', 'tecnico'] },
  { moduleKey: 'billing', allowedRoles: ['admin', 'ejecutivo'] },
  { moduleKey: 'reports', allowedRoles: ['admin', 'ejecutivo'] },
  { moduleKey: 'settings', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] },
  { moduleKey: 'profile', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] }
];

const adminOnlyNavigationItemIds = new Set(['task-templates']);
const adminOrExecutiveNavigationItemIds = new Set(['tasks-history']);

@Injectable({ providedIn: 'root' })
export class MockAccessControlService {
  private readonly mockUserContextService = inject(MockUserContextService);
  private readonly rulesByModule = new Map(moduleRules.map((rule) => [rule.moduleKey, rule.allowedRoles]));

  readonly activeUser$ = this.mockUserContextService.activeUser();
  readonly activeRole$ = this.activeUser$.pipe(map((user) => user.role));

  isAdmin() {
    return this.activeRole$.pipe(map((role) => role === 'admin'));
  }

  canViewInventory() {
    return this.canViewModule('inventory');
  }

  canViewModule(moduleKey: MockModuleKey) {
    return this.activeRole$.pipe(map((role) => this.canRoleViewModule(role, moduleKey)));
  }

  canViewAllTickets() {
    return this.activeRole$.pipe(map((role) => role === 'admin'));
  }

  canViewAllTasks() {
    return this.activeRole$.pipe(map((role) => role === 'admin'));
  }

  canCreateClients() {
    return this.activeRole$.pipe(map((role) => role === 'admin' || role === 'ejecutivo'));
  }

  canEditClients() {
    return this.canCreateClients();
  }

  canDeleteClients() {
    return this.canCreateClients();
  }

  canUserViewTicketExecution(user: MockUserProfile, technicianAssigneeId: number | string | null, depositAssigneeId: number | string | null): boolean {
    return user.role === 'admin' || user.id === technicianAssigneeId || user.id === depositAssigneeId;
  }

  canUserEditTicketResolution(user: MockUserProfile, technicianAssigneeId: number | string | null): boolean {
    return user.role === 'tecnico' && user.id === technicianAssigneeId;
  }

  canUserManageTicketAttachments(user: MockUserProfile, technicianAssigneeId: number | string | null): boolean {
    return this.canUserEditTicketResolution(user, technicianAssigneeId);
  }

  canUserCreateTicketInventoryRequests(user: MockUserProfile, technicianAssigneeId: number | string | null): boolean {
    return this.canUserEditTicketResolution(user, technicianAssigneeId);
  }

  canUserReviewTicketInventoryRequests(user: MockUserProfile, depositAssigneeId: number | string | null): boolean {
    return user.role === 'admin' || (user.role === 'deposito' && user.id === depositAssigneeId);
  }

  canUserManageTicketDispatch(user: MockUserProfile, depositAssigneeId: number | string | null): boolean {
    return this.canUserReviewTicketInventoryRequests(user, depositAssigneeId);
  }

  canUserViewTicketDispatch(user: MockUserProfile, depositAssigneeId: number | string | null): boolean {
    return user.role === 'admin' || (user.role === 'deposito' && user.id === depositAssigneeId);
  }

  filterNavigationForActiveUser(sections: NavigationSection[]) {
    return this.activeRole$.pipe(map((role) => this.filterNavigationForRole(sections, role)));
  }

  filterTasksForActiveUser(tasks: TaskListItem[]) {
    return this.activeUser$.pipe(map((user) => this.filterTasksForUser(tasks, user)));
  }

  filterTicketsForActiveUser(tickets: TicketListItem[]) {
    return this.activeUser$.pipe(map((user) => this.filterTicketsForUser(tickets, user)));
  }

  private canRoleViewModule(role: MockUserRole, moduleKey: MockModuleKey): boolean {
    const allowedRoles = this.rulesByModule.get(moduleKey);
    return allowedRoles ? allowedRoles.includes(role) : role === 'admin';
  }

  private filterNavigationForRole(sections: NavigationSection[], role: MockUserRole): NavigationSection[] {
    return sections
      .map((section) => ({
        ...section,
        items: section.items.filter(
          (item) =>
            this.canRoleViewModule(role, item.moduleKey ?? item.id as MockModuleKey)
            && (!adminOnlyNavigationItemIds.has(item.id) || role === 'admin')
            && (!adminOrExecutiveNavigationItemIds.has(item.id) || role === 'admin' || role === 'ejecutivo')
        )
      }))
      .filter((section) => section.items.length > 0);
  }

  private filterTasksForUser(tasks: TaskListItem[], user: MockUserProfile): TaskListItem[] {
    if (user.role === 'admin') {
      return tasks;
    }

    return tasks.filter((task) => task.assignedToUserId === user.id);
  }

  private filterTicketsForUser(tickets: TicketListItem[], user: MockUserProfile): TicketListItem[] {
    if (user.role === 'admin') {
      return tickets;
    }

    return tickets.filter((ticket) => ticket.assigneeId === user.id);
  }
}

export type { MockModuleKey, MockUserRole };
