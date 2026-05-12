import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { SwPush } from '@angular/service-worker';
import { firstValueFrom } from 'rxjs';

import { crmApiConfig, crmPushConfig } from '../config/crm-api.config';
import { AuthSessionService } from './auth-session.service';

@Injectable({ providedIn: 'root' })
export class PushNotificationService {
  private readonly swPush = inject(SwPush);
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  async requestAndSubscribe(): Promise<void> {
    if (!this.swPush.isEnabled || !crmPushConfig.vapidPublicKey) {
      return;
    }

    try {
      const subscription = await this.swPush.requestSubscription({
        serverPublicKey: crmPushConfig.vapidPublicKey,
      });

      const json = subscription.toJSON();
      const keys = json.keys as { p256dh: string; auth: string } | undefined;
      if (!json.endpoint || !keys?.p256dh || !keys?.auth) {
        return;
      }

      await firstValueFrom(
        this.http.post(
          `${crmApiConfig.baseUrl}/notifications/push-subscription`,
          {
            endpoint: json.endpoint,
            p256dh: keys.p256dh,
            auth: keys.auth,
            user_agent: navigator.userAgent,
          },
          { headers: this.authHeaders }
        )
      );
    } catch {
      // Permiso denegado o service worker no disponible.
    }
  }

  async unsubscribe(): Promise<void> {
    if (!this.swPush.isEnabled) {
      return;
    }

    try {
      const subscription = await firstValueFrom(this.swPush.subscription);
      if (!subscription) {
        return;
      }

      const endpoint = subscription.endpoint;
      await this.swPush.unsubscribe();

      await firstValueFrom(
        this.http.delete(`${crmApiConfig.baseUrl}/notifications/push-subscription`, {
          body: { endpoint },
          headers: this.authHeaders,
        })
      ).catch(() => {
        // Si el token expiro durante el logout, ignoramos el error.
      });
    } catch {
      // Service worker no disponible o sin suscripcion activa.
    }
  }

  private get authHeaders(): HttpHeaders {
    const token = this.authSessionService.sessionSnapshot()?.tokens.access_token;
    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : new HttpHeaders();
  }
}
