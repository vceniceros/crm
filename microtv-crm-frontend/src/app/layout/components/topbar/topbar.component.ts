import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, computed, inject, input, OnDestroy, OnInit, output } from '@angular/core';
import { Router } from '@angular/router';
import { map } from 'rxjs';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { Notification, NOTIFICATION_TYPES } from '../../../core/models/notification.model';
import { ContextHelpService } from '../../../core/services/context-help.service';
import { NotificationsService } from '../../../core/services/notifications.service';
import { ThemeService } from '../../../core/services/theme.service';

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
  private readonly themeService = inject(ThemeService);
  private readonly contextHelpService = inject(ContextHelpService);

  readonly unreadCount$ = this.notificationsService.unreadCount$;
  readonly notifications$ = this.notificationsService.notifications$;
  readonly unreadNotifications$ = this.notifications$.pipe(map((items) => items.filter((item) => !item.is_read)));
  readonly currentTheme = this.themeService.theme;
  readonly themeToggleIcon = computed(() => (this.currentTheme() === 'dark' ? 'light_mode' : 'dark_mode'));
  readonly themeToggleLabel = computed(() =>
    this.currentTheme() === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'
  );
  readonly helpButtonLabel = computed(() => 'Mostrar ayudas de esta pantalla');

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

    const typedRoute = this.resolveRouteFromNotificationType(notification);
    if (typedRoute) {
      this.router.navigateByUrl(typedRoute);
      return;
    }

    if (notification.entity_type && notification.entity_id) {
      const routeMap: Record<string, string> = {
        ticket: `/tickets/${notification.entity_id}`,
        task: `/tasks/${notification.entity_id}`,
        deposit_request: `/inventory/requests`,
        stock_product: '/inventory',
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

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  requestContextHelpReveal(): void {
    this.contextHelpService.requestReveal();
  }

  requestContextHelpHide(): void {
    this.contextHelpService.requestHide();
  }

  private resolveRouteFromNotificationType(notification: Notification): string | null {
    const notificationType = notification.notification_type;
    const entityId = notification.entity_id;

    switch (notificationType) {
      case NOTIFICATION_TYPES.TASK_ASSIGNED:
      case NOTIFICATION_TYPES.TASK_PRE_FORM_COMPLETED:
      case NOTIFICATION_TYPES.TASK_SATISFACTION_SUBMITTED:
        return entityId ? `/tasks/${entityId}` : '/tasks';
      case NOTIFICATION_TYPES.TASK_COMMENT_MENTIONED:
        return entityId ? this.withCommentFragment(`/tasks/${entityId}`, notification, 'task-comment') : '/tasks';
      case NOTIFICATION_TYPES.TASK_UNASSIGNED_IN_ROLE:
        return '/tasks';
      case NOTIFICATION_TYPES.TICKET_SATISFACTION_SUBMITTED:
        return entityId ? `/tickets/${entityId}` : '/tickets';
      case NOTIFICATION_TYPES.TICKET_COMMENT_MENTIONED:
        return entityId ? this.withCommentFragment(`/tickets/${entityId}`, notification, 'ticket-comment') : '/tickets';
      case NOTIFICATION_TYPES.TICKET_UNASSIGNED_IN_ROLE:
        return '/tickets';
      case NOTIFICATION_TYPES.STOCK_LOW:
      case NOTIFICATION_TYPES.STOCK_OUT:
        return '/inventory';
      case NOTIFICATION_TYPES.DEPOSIT_PENDING_DISPATCH:
      case NOTIFICATION_TYPES.DEPOSIT_PRODUCTS_INSTALLED:
        return '/inventory/requests';
      default:
        return null;
    }
  }

  private withCommentFragment(route: string, notification: Notification, prefix: string): string {
    const commentId = notification.metadata_json?.['comment_id'];
    return typeof commentId === 'string' && commentId.trim() ? `${route}#${prefix}-${commentId}` : route;
  }
}
