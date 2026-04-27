import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Observable, Subscription, interval } from 'rxjs';
import { catchError, switchMap, tap } from 'rxjs/operators';
import { of } from 'rxjs';

import { crmApiConfig } from '../config/crm-api.config';
import { Notification, NotificationListResponse, UnreadCountResponse } from '../models/notification.model';
import { AuthSessionService } from './auth-session.service';

const POLL_INTERVAL_MS = 30_000;

@Injectable({ providedIn: 'root' })
export class NotificationsService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  private readonly unreadCountSubject = new BehaviorSubject<number>(0);
  private readonly notificationsSubject = new BehaviorSubject<Notification[]>([]);
  private pollSubscription: Subscription | null = null;

  readonly unreadCount$ = this.unreadCountSubject.asObservable();
  readonly notifications$ = this.notificationsSubject.asObservable();

  private get authHeaders(): HttpHeaders {
    const session = this.authSessionService.sessionSnapshot();
    const token = session?.tokens.access_token;
    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : new HttpHeaders();
  }

  startPolling(): void {
    if (this.pollSubscription) return;
    this.load();
    this.pollSubscription = interval(POLL_INTERVAL_MS)
      .pipe(switchMap(() => this.fetchList()))
      .subscribe((data) => this.applyList(data));
  }

  stopPolling(): void {
    this.pollSubscription?.unsubscribe();
    this.pollSubscription = null;
  }

  load(): void {
    this.fetchList().subscribe((data) => this.applyList(data));
  }

  dismissFromTray(notificationId: string): void {
    const current = this.notificationsSubject.getValue();
    this.notificationsSubject.next(current.filter((n) => n.notification_id !== notificationId));
    this.unreadCountSubject.next(this.notificationsSubject.getValue().filter((n) => !n.is_read).length);
  }

  markRead(notificationId: string): Observable<Notification> {
    this.dismissFromTray(notificationId);
    return this.http
      .patch<Notification>(
        `${crmApiConfig.baseUrl}/notifications/${notificationId}/read`,
        {},
        { headers: this.authHeaders }
      );
  }

  markAllRead(): Observable<void> {
    return this.http
      .post<void>(`${crmApiConfig.baseUrl}/notifications/mark-all-read`, {}, { headers: this.authHeaders })
      .pipe(
        tap(() => {
          this.notificationsSubject.next([]);
          this.unreadCountSubject.next(0);
        })
      );
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  private fetchList(): Observable<NotificationListResponse> {
    return this.http
      .get<NotificationListResponse>(`${crmApiConfig.baseUrl}/notifications`, { headers: this.authHeaders })
      .pipe(
        catchError((error) => {
          console.error('Error loading notifications', error);
          return of({
            notifications: this.notificationsSubject.getValue(),
            unread_count: this.unreadCountSubject.getValue(),
          });
        })
      );
  }

  private applyList(data: NotificationListResponse): void {
    this.notificationsSubject.next(data.notifications);
    this.unreadCountSubject.next(data.unread_count);
  }
}
