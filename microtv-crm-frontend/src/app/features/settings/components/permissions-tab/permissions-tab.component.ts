import { ChangeDetectionStrategy, Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { SettingsRolePermission, SettingsUserPermissionOverride } from '../../../../core/models/settings-management.model';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { PermissionService } from '../../../../core/services/permission.service';
import { SettingsManagementService } from '../../../../core/services/settings-management.service';

@Component({
  selector: 'app-permissions-tab',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatSnackBarModule],
  templateUrl: './permissions-tab.component.html',
  styleUrl: './permissions-tab.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PermissionsTabComponent implements OnInit {
  private readonly settingsManagementService = inject(SettingsManagementService);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly permissionService = inject(PermissionService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly rolePermissions = signal<SettingsRolePermission[]>([]);
  readonly userOverrides = signal<SettingsUserPermissionOverride[]>([]);
  readonly isExecutiveMode = signal(false);

  ngOnInit(): void {
    const roleKeys = this.authSessionService.sessionSnapshot()?.user.role_keys ?? [];
    const isExecutive = !roleKeys.includes('admin');
    this.load(isExecutive);
  }
  readonly groupedRolePermissions = computed(() => {
    const grouped = new Map<string, SettingsRolePermission[]>();
    for (const row of this.rolePermissions()) {
      const current = grouped.get(row.permission_code) ?? [];
      current.push(row);
      grouped.set(row.permission_code, current);
    }
    return Array.from(grouped.entries()).map(([permissionCode, values]) => ({ permissionCode, values }));
  });

  load(isExecutiveMode: boolean): void {
    this.isExecutiveMode.set(isExecutiveMode);
    this.loading.set(true);
    this.error.set(null);

    this.settingsManagementService
      .listRolePermissions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (roles) => {
          this.rolePermissions.set(roles);
          this.settingsManagementService
            .listUserPermissionOverrides()
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe({
              next: (overrides) => {
                this.userOverrides.set(overrides);
                this.loading.set(false);
              },
              error: (error: Error) => {
                this.error.set(error.message);
                this.loading.set(false);
              }
            });
        },
        error: (error: Error) => {
          this.error.set(error.message);
          this.loading.set(false);
        }
      });
  }

  toggleRolePermission(permission: SettingsRolePermission): void {
    if (this.isExecutiveMode() || permission.role_key === 'admin') {
      return;
    }

    this.settingsManagementService
      .updateRolePermission(permission.role_key, permission.permission_code, !permission.is_granted)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated) => {
          this.rolePermissions.update((current) =>
            current.map((row) =>
              row.role_key === updated.role_key && row.permission_code === updated.permission_code ? updated : row
            )
          );
          this.permissionService.refresh();
        },
        error: (error: Error) => this.error.set(error.message)
      });
  }

  refreshPermissions(): void {
    this.permissionService.refresh();
    this.snackBar.open('Permisos recargados.', 'Cerrar', { duration: 3000 });
  }
}
