import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { forkJoin } from 'rxjs';

import {
  SettingsAuthUser,
  SettingsAuthUserCreateRequest,
  SettingsCategory,
  SettingsCategoryWriteRequest,
  SettingsNotificationRule,
  SettingsNotificationRuleWriteRequest,
  SettingsPriority,
  SettingsPriorityWriteRequest,
  SettingsRole,
  SettingsRoleUpdateRequest,
  SettingsSlaRule,
  SettingsSlaRuleWriteRequest,
  SettingsStatus,
  SettingsStatusWriteRequest,
  SettingsTaskTemplate,
  SettingsTaskTemplateUpdateRequest,
  SettingsUserRoleAssignment,
  SettingsUserRoleAssignmentRequest
} from '../../../../core/models/settings-management.model';
import { UI_HELP_TEXTS } from '../../../../core/config/ui-help-texts.config';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { PermissionService } from '../../../../core/services/permission.service';
import { SettingsManagementService } from '../../../../core/services/settings-management.service';
import { ContextHelpCardComponent } from '../../../../shared/ui/context-help-card/context-help-card.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import {
  SettingsDialogRoleOption,
  SettingsEditDialogComponent
} from '../settings-edit-dialog/settings-edit-dialog.component';
import { PermissionsTabComponent } from '../permissions-tab/permissions-tab.component';
import { ActivityLogTabComponent } from '../activity-log-tab/activity-log-tab.component';

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    ContextHelpCardComponent,
    PageTitleComponent,
    PermissionsTabComponent,
    ActivityLogTabComponent
  ],
  templateUrl: './settings-page.component.html',
  styleUrl: './settings-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SettingsPageComponent {
  private readonly settingsService = inject(SettingsManagementService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly permissionService = inject(PermissionService);
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);
  readonly helpText = UI_HELP_TEXTS.settings;

  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);

  readonly roles = signal<SettingsRole[]>([]);
  readonly userRoles = signal<SettingsUserRoleAssignment[]>([]);
  readonly authUsers = signal<SettingsAuthUser[]>([]);
  readonly categories = signal<SettingsCategory[]>([]);
  readonly priorities = signal<SettingsPriority[]>([]);
  readonly statuses = signal<SettingsStatus[]>([]);
  readonly templates = signal<SettingsTaskTemplate[]>([]);
  readonly slaRules = signal<SettingsSlaRule[]>([]);
  readonly notificationRules = signal<SettingsNotificationRule[]>([]);

  readonly crmOperationalRoles: Array<{ code: string; label: string }> = [
    { code: 'admin', label: 'Administrador' },
    { code: 'ejecutivo', label: 'Ejecutivo' },
    { code: 'tecnico_campo', label: 'Técnico de campo' },
    { code: 'operador_deposito', label: 'Operador depósito' }
  ];

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    if (!this.isAdminOrExecutive() || !this.canCreateAuthUsers()) {
      // Solo admins y ejecutivos con permiso pueden gestionar usuarios
      this.authUsers.set([]);
      this.loading.set(false);
      return;
    }

    forkJoin({
      authUsers: this.settingsService.listAuthUsers()
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.authUsers.set(result.authUsers);
          this.loading.set(false);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.loading.set(false);
        }
      });
  }

  openRoleDialog(role: SettingsRole): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '40rem',
        data: {
          kind: 'role',
          title: `Editar rol ${role.role_label}`,
          submitLabel: 'Guardar',
          value: role
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsRoleUpdateRequest | undefined) => {
        if (!value) {
          return;
        }
        this.settingsService
          .updateRole(role.crm_role_id, value)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: () => this.reload(),
            error: (error: Error) => this.errorMessage.set(error.message)
          });
      });
  }

  openUserRolesDialog(item: SettingsUserRoleAssignment): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '40rem',
        data: {
          kind: 'user-roles',
          title: `Roles de ${item.display_name || item.email || 'usuario'}`,
          submitLabel: 'Guardar',
          value: item,
          roleOptions: this.roleOptions()
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsUserRoleAssignmentRequest | undefined) => {
        if (!value) {
          return;
        }
        this.settingsService
          .setUserRoles(item.crm_user_id, value)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: () => this.reload(),
            error: (error: Error) => this.errorMessage.set(error.message)
          });
      });
  }

  openCategoryDialog(item?: SettingsCategory): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '42rem',
        data: {
          kind: 'category',
          title: item ? 'Editar categoría' : 'Nueva categoría',
          submitLabel: item ? 'Guardar' : 'Crear',
          value: item ?? { name: '', category_type: 'ticket', description: '', is_active: true }
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsCategoryWriteRequest | undefined) => {
        if (!value) {
          return;
        }
        const request$ = item
          ? this.settingsService.updateCategory(item.category_id, value)
          : this.settingsService.createCategory(value);
        request$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => this.reload(),
          error: (error: Error) => this.errorMessage.set(error.message)
        });
      });
  }

  openPriorityDialog(item?: SettingsPriority): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '42rem',
        data: {
          kind: 'priority',
          title: item ? 'Editar prioridad' : 'Nueva prioridad',
          submitLabel: item ? 'Guardar' : 'Crear',
          value: item ?? { code: '', name: '', order_index: 0, color: '', is_active: true }
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsPriorityWriteRequest | undefined) => {
        if (!value) {
          return;
        }
        const request$ = item
          ? this.settingsService.updatePriority(item.priority_id, value)
          : this.settingsService.createPriority(value);
        request$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => this.reload(),
          error: (error: Error) => this.errorMessage.set(error.message)
        });
      });
  }

  openStatusDialog(item?: SettingsStatus): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '42rem',
        data: {
          kind: 'status',
          title: item ? 'Editar estado' : 'Nuevo estado',
          submitLabel: item ? 'Guardar' : 'Crear',
          value: item ?? { code: '', name: '', entity_type: 'ticket', is_final: false, order_index: 0, is_active: true }
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsStatusWriteRequest | undefined) => {
        if (!value) {
          return;
        }
        const request$ = item
          ? this.settingsService.updateStatus(item.status_id, value)
          : this.settingsService.createStatus(value);
        request$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => this.reload(),
          error: (error: Error) => this.errorMessage.set(error.message)
        });
      });
  }

  openTemplateDialog(item: SettingsTaskTemplate): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '42rem',
        data: {
          kind: 'template',
          title: 'Editar template de tarea',
          submitLabel: 'Guardar',
          value: item
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsTaskTemplateUpdateRequest | undefined) => {
        if (!value) {
          return;
        }
        this.settingsService
          .updateTaskTemplate(item.template_id, value)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: () => this.reload(),
            error: (error: Error) => this.errorMessage.set(error.message)
          });
      });
  }

  openSlaDialog(item?: SettingsSlaRule): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '42rem',
        data: {
          kind: 'sla',
          title: item ? 'Editar regla SLA' : 'Nueva regla SLA',
          submitLabel: item ? 'Guardar' : 'Crear',
          value: item ?? {
            entity_type: 'ticket',
            priority_code: this.priorities()[0]?.code ?? 'MEDIUM',
            response_time_minutes: 60,
            resolution_time_minutes: 480,
            is_active: true
          },
          priorityOptions: this.priorities().map((priority) => priority.code)
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsSlaRuleWriteRequest | undefined) => {
        if (!value) {
          return;
        }
        const request$ = item
          ? this.settingsService.updateSlaRule(item.sla_rule_id, value)
          : this.settingsService.createSlaRule(value);
        request$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => this.reload(),
          error: (error: Error) => this.errorMessage.set(error.message)
        });
      });
  }

  openNotificationDialog(item?: SettingsNotificationRule): void {
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '44rem',
        data: {
          kind: 'notification',
          title: item ? 'Editar regla de notificación' : 'Nueva regla de notificación',
          submitLabel: item ? 'Guardar' : 'Crear',
          value: item ?? { event_code: '', label: '', notify_assigned: true, notify_roles_json: [], is_active: true },
          roleOptions: this.roleOptions()
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsNotificationRuleWriteRequest | undefined) => {
        if (!value) {
          return;
        }
        const request$ = item
          ? this.settingsService.updateNotificationRule(item.notification_rule_id, value)
          : this.settingsService.createNotificationRule(value);
        request$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => this.reload(),
          error: (error: Error) => this.errorMessage.set(error.message)
        });
      });
  }

  roleOptions(): SettingsDialogRoleOption[] {
    return this.roles().map((role) => ({ code: role.role_key, label: role.role_label }));
  }

  prettyRoles(roleKeys: string[]): string {
    if (!roleKeys.length) {
      return 'Sin roles';
    }
    const byKey = new Map(this.roles().map((role) => [role.role_key, role.role_label]));
    return roleKeys.map((key) => byKey.get(key) ?? key).join(', ');
  }

  isAdmin(): boolean {
    return this.authSessionService.sessionSnapshot()?.user.role_keys.includes('admin') ?? false;
  }

  isAdminOrExecutive(): boolean {
    const roleKeys = this.authSessionService.sessionSnapshot()?.user.role_keys ?? [];
    return roleKeys.includes('admin') || roleKeys.includes('ejecutivo');
  }

  canCreateAuthUsers(): boolean {
    if (this.isAdmin()) {
      return true;
    }
    return this.permissionService.canCreateNonAdminAuthUser();
  }

  canManageAuthUser(user: SettingsAuthUser): boolean {
    if (this.isAdmin()) {
      return true;
    }
    return this.canCreateAuthUsers() && !this.hasAdminRole(user.roles);
  }

  hasAdminRole(roleKeys: string[]): boolean {
    return roleKeys.some((roleKey) => roleKey === 'admin' || roleKey === 'platform_admin');
  }

  prettyAuthRoles(roleKeys: string[]): string {
    const byKey = new Map(this.crmOperationalRoles.map((role) => [role.code, role.label]));
    if (!roleKeys.length) {
      return 'Sin roles';
    }
    return roleKeys.map((key) => byKey.get(key) ?? key).join(', ');
  }

  createAuthUser(): void {
    const roleOptions = this.availableAuthRoleOptions();
    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '34rem',
        data: {
          kind: 'auth-user',
          authUserMode: 'create',
          title: 'Nuevo usuario',
          submitLabel: 'Crear',
          value: {
            email: '',
            display_name: '',
            password: '',
            roles: [roleOptions[0]?.code ?? 'operador_deposito']
          },
          roleOptions
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: { email: string; display_name: string; password: string; roles: string[] } | undefined) => {
        if (!value) {
          return;
        }

        const payload: SettingsAuthUserCreateRequest = {
          email: value.email,
          display_name: value.display_name,
          password: value.password,
          is_active: true,
          roles: this.filterAssignableRoles(value.roles ?? [])
        };

        this.settingsService
          .createAuthUser(payload)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: () => this.reload(),
            error: (error: Error) => this.errorMessage.set(error.message)
          });
      });
  }

  private availableAuthRoleOptions(): Array<{ code: string; label: string }> {
    if (this.isAdmin()) {
      return this.crmOperationalRoles.map((role) => ({ code: role.code, label: role.label }));
    }
    return this.crmOperationalRoles
      .filter((role) => role.code !== 'admin')
      .map((role) => ({ code: role.code, label: role.label }));
  }

  private filterAssignableRoles(roleKeys: string[]): string[] {
    const allowedRoleKeys = new Set(this.availableAuthRoleOptions().map((role) => role.code));
    return roleKeys.filter((roleKey) => allowedRoleKeys.has(roleKey));
  }

  editAuthUser(user: SettingsAuthUser): void {
    if (!this.canManageAuthUser(user)) {
      this.errorMessage.set('Un ejecutivo no puede editar usuarios con rol administrador.');
      return;
    }

    this.dialog
      .open(SettingsEditDialogComponent, {
        width: '34rem',
        data: {
          kind: 'auth-user',
          authUserMode: 'edit',
          title: `Editar usuario ${user.display_name}`,
          submitLabel: 'Guardar',
          value: {
            email: user.email,
            display_name: user.display_name,
            roles: user.roles
          },
          roleOptions: this.availableAuthRoleOptions()
        }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: { email: string; display_name: string; roles: string[] } | undefined) => {
        if (!value) {
          return;
        }

        forkJoin({
          user: this.settingsService.updateAuthUser(user.user_id, {
            email: value.email,
            display_name: value.display_name
          }),
          roles: this.settingsService.setAuthUserRoles(user.user_id, {
            roles: this.filterAssignableRoles(value.roles ?? [])
          })
        })
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: () => this.reload(),
            error: (error: Error) => this.errorMessage.set(error.message)
          });
      });
  }

  toggleAuthUserStatus(user: SettingsAuthUser): void {
    this.settingsService
      .setAuthUserStatus(user.user_id, { is_active: !user.is_active })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.reload(),
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }

  resetAuthUserPassword(user: SettingsAuthUser): void {
    if (!this.canManageAuthUser(user)) {
      this.errorMessage.set('Un ejecutivo no puede resetear contraseñas de usuarios administradores.');
      return;
    }

    const newPassword = window.prompt(`Nueva contraseña para ${user.display_name} (${user.email}):`, '') ?? '';
    if (newPassword.length < 8) {
      this.errorMessage.set('La nueva contraseña debe tener al menos 8 caracteres.');
      return;
    }
    this.settingsService
      .resetAuthUserPassword(user.user_id, { new_password: newPassword })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.reload(),
        error: (error: Error) => this.errorMessage.set(error.message)
      });
  }
}
