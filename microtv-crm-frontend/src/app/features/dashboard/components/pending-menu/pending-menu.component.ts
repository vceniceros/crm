import { Component, computed, inject, input, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { Router } from '@angular/router';

import { PendingMenuBlock, PendingMenuItem, PendingMenuTabKey } from '../../../../core/models/dashboard.model';
import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-pending-menu',
  standalone: true,
  imports: [MatCardModule, PriorityIndicatorComponent, StatusBadgeComponent, UserAvatarComponent],
  templateUrl: './pending-menu.component.html',
  styleUrl: './pending-menu.component.scss'
})
export class PendingMenuComponent {
  private readonly router = inject(Router);

  readonly block = input.required<PendingMenuBlock>();
  readonly selectedTab = signal<PendingMenuTabKey>('all');

  readonly selectedItems = computed(() => {
    const selectedTab = this.selectedTab();
    return this.block().items.filter((item) => item.tabKeys.includes(selectedTab));
  });

  selectTab(tabKey: PendingMenuTabKey): void {
    this.selectedTab.set(tabKey);
  }

  navigateTo(item: PendingMenuItem): void {
    void this.router.navigateByUrl(item.targetRoute);
  }
}
