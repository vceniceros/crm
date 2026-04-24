import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject, input, OnDestroy, OnInit, output } from '@angular/core';
import { Router } from '@angular/router';
import { map } from 'rxjs';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { Notification } from '../../../core/models/notification.model';
import { NotificationsService } from '../../../core/services/notifications.service';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [AsyncPipe, DatePipe, MatBadgeModule, MatButtonModule, MatIconModule, MatMenuModule, MatToolbarModule, MatTooltipModule],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss'
})
export class TopbarComponent implements OnInit, OnDestroy {
  readonly title = input.required<string>();
  readonly showMenuButton = input(false);
  readonly menuToggle = output<void>();

  private readonly notificationsService = inject(NotificationsService);
  private readonly router = inject(Router);

  readonly unreadCount$ = this.notificationsService.unreadCount$;
  readonly notifications$ = this.notificationsService.notifications$;
  readonly unreadNotifications$ = this.notifications$.pipe(map((items) => items.filter((item) => !item.is_read)));

  ngOnInit(): void {
    this.notificationsService.startPolling();
  }

  ngOnDestroy(): void {
    this.notificationsService.stopPolling();
  }

  openNotification(notification: Notification): void {
    this.notificationsService.dismissFromTray(notification.notification_id);
    if (!notification.is_read) {
      this.notificationsService.markRead(notification.notification_id).subscribe({ error: () => {} });
    }
    if (notification.entity_type && notification.entity_id) {
      const routeMap: Record<string, string> = {
        ticket: `/tickets/${notification.entity_id}`,
        task: `/tasks/${notification.entity_id}`,
        deposit_request: `/inventory/requests`,
      };
      const route = routeMap[notification.entity_type];
      if (route) {
        this.router.navigateByUrl(route);
      }
    }
  }

  markAllRead(): void {
    this.notificationsService.markAllRead().subscribe();
  }
}
