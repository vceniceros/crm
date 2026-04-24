import { DatePipe } from '@angular/common';
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
import { SettingsManagementService } from '../../../../core/services/settings-management.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import {
  SettingsDialogRoleOption,
  SettingsEditDialogComponent
} from '../settings-edit-dialog/settings-edit-dialog.component';

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    PageTitleComponent
  ],
  templateUrl: './settings-page.component.html',
  styleUrl: './settings-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SettingsPageComponent {
  private readonly settingsService = inject(SettingsManagementService);
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);

  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);

  readonly roles = signal<SettingsRole[]>([]);
  readonly userRoles = signal<SettingsUserRoleAssignment[]>([]);
  readonly categories = signal<SettingsCategory[]>([]);
  readonly priorities = signal<SettingsPriority[]>([]);
  readonly statuses = signal<SettingsStatus[]>([]);
  readonly templates = signal<SettingsTaskTemplate[]>([]);
  readonly slaRules = signal<SettingsSlaRule[]>([]);
  readonly notificationRules = signal<SettingsNotificationRule[]>([]);

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    forkJoin({
      roles: this.settingsService.listRoles(),
      userRoles: this.settingsService.listUserRoles(),
      categories: this.settingsService.listCategories(),
      priorities: this.settingsService.listPriorities(),
      statuses: this.settingsService.listStatuses(),
      templates: this.settingsService.listTaskTemplates(),
      sla: this.settingsService.listSlaRules(),
      notifications: this.settingsService.listNotificationRules()
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.roles.set(result.roles);
          this.userRoles.set(result.userRoles);
          this.categories.set(result.categories);
          this.priorities.set(result.priorities);
          this.statuses.set(result.statuses);
          this.templates.set(result.templates);
          this.slaRules.set(result.sla);
          this.notificationRules.set(result.notifications);
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
}
