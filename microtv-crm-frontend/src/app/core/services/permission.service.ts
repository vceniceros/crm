import { inject, Injectable, signal } from '@angular/core';

import { SettingsManagementService } from './settings-management.service';

@Injectable({ providedIn: 'root' })
export class PermissionService {
  private readonly settingsManagementService = inject(SettingsManagementService);

  readonly canManageStock = signal(false);
  readonly canDeleteProduct = signal(false);
  readonly canReassignTickets = signal(false);
  readonly canReassignOrders = signal(false);
  readonly canDeleteComment = signal(false);

  refresh(): void {
    this.settingsManagementService.getMyEffectivePermissions().subscribe({
      next: (permissions) => {
        this.canManageStock.set(Boolean(permissions['stock.manage']));
        this.canDeleteProduct.set(Boolean(permissions['stock.delete_product']));
        this.canReassignTickets.set(Boolean(permissions['ticket.reassign']));
        this.canReassignOrders.set(Boolean(permissions['order.reassign']));
        this.canDeleteComment.set(Boolean(permissions['comment.delete']));
      },
      error: () => this.clear()
    });
  }

  clear(): void {
    this.canManageStock.set(false);
    this.canDeleteProduct.set(false);
    this.canReassignTickets.set(false);
    this.canReassignOrders.set(false);
    this.canDeleteComment.set(false);
  }
}
