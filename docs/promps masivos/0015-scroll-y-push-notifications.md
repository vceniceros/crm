# 0015 — Scroll Contenido en Listas + Notificaciones Push (SwPush + VAPID)

## Contexto

Dos mejoras independientes que se pueden desarrollar en paralelo:

1. **Scroll contenido**: En las páginas de Tickets y Pedidos, cuando la cantidad de items supera la altura de la pantalla, la página crece infinitamente en lugar de mostrar una barra de desplazamiento interna. El fix es una sola modificación CSS en el shell.

2. **Push notifications**: El sistema de notificaciones in-app ya existe y funciona por polling. Ahora se quiere que cuando el usuario inicia sesión, la app pida permiso de notificaciones y, cuando se emita una notificación in-app, también se envíe como push nativo al navegador/teléfono — incluso con la app en segundo plano o cerrada. Al cerrar sesión, la suscripción se elimina.

---

## Feature A — Scroll contenido en listas

### Causa raíz

`.app-shell__content` usa `min-height: 100dvh`, que le permite crecer sin límite. Toda la lógica de scroll ya está planteada: el componente `AppShellComponent` llama a `sidenavContent.scrollTo({ top: 0 })` en cada navegación, indicando que el área de contenido es la que debe scrollear, no la ventana del navegador.

### Paso A1 — Editar `app-shell.component.scss`

**Archivo:** `microtv-crm-frontend/src/app/layout/components/app-shell/app-shell.component.scss`

Cambios:
- `:host` y `.app-shell`: reemplazar `min-height: 100dvh` por `height: 100dvh`
- `.app-shell__content`: reemplazar `min-height: 100dvh` por `height: 100dvh` y agregar `overflow-y: auto`

```scss
:host {
  display: block;
  height: 100dvh;            /* era min-height */
}

.app-shell {
  height: 100dvh;            /* era min-height */
  background: transparent;
}

.app-shell__content {
  height: 100dvh;            /* era min-height */
  min-width: 0;
  overflow-x: clip;
  overflow-y: auto;          /* nuevo */
}
```

> Un único cambio en un único archivo. Todas las rutas se benefician automáticamente.

### Verificación A

- Abrir `/tickets` o `/tasks` con muchos items en el laboratorio
- La barra del navegador **no** se mueve; la barra de scroll aparece dentro del panel de contenido
- Navegar entre rutas → el scroll vuelve a `top: 0` automáticamente (ya funciona gracias a `sidenavContent.scrollTo`)
- Verificar en breakpoint mobile (< 960px) — mismo comportamiento

---

## Feature B — Push notifications nativas (SwPush + VAPID)

### Arquitectura

```
Login → app-shell detecta isAuthenticated$ = true
      → PushNotificationService.requestAndSubscribe()
          → SwPush.requestSubscription({ serverPublicKey })
          → Browser muestra dialog de permisos
          → Si acepta: POST /notifications/push-subscription → DB
          → Si rechaza: no-op silencioso

Backend emite notificación in-app (notify())
      → PushNotificationService.send_to_user()
          → pywebpush envía a cada endpoint del usuario
          → Si endpoint devuelve 410: eliminar suscripción de DB

Logout → app-shell detecta isAuthenticated$ = false
       → PushNotificationService.unsubscribe()
           → SwPush.unsubscribe()
           → DELETE /notifications/push-subscription → DB
```

El service worker ya está registrado (`app.config.ts`) y `ngsw-config.json` ya está configurado — no requieren cambios.

---

## Fase B0 — Generación de VAPID keys (prerequisito)

Ejecutar una sola vez, conservar las claves generadas:

```bash
npx web-push generate-vapid-keys
```

- `VAPID_PRIVATE_KEY` → `.env` del backend
- `VAPID_PUBLIC_KEY` → `.env` del backend **y** runtime config del frontend
- `VAPID_CLAIMS_SUB` → `mailto:admin@microtv.ar` → `.env` del backend

La clave pública se inyecta al frontend via `__CRM_RUNTIME_CONFIG__.vapidPublicKey` en el `index.html` (o en la configuración de nginx), usando el mismo patrón que `crmApiBaseUrl`. Así no es necesario recompilar la app por entorno.

---

## Fase B1 — Backend

### Paso B1 — Agregar dependencia

**Archivo:** `microtv-crm-backend/pyproject.toml`

```toml
dependencies = [
    ...
    "pywebpush>=2.0,<3.0",
]
```

---

### Paso B2 — Configuración VAPID

**Archivo:** `microtv-crm-backend/src/crm_backend/core/config.py`

Agregar a `Settings`:

```python
vapid_private_key: str = Field(default="")
vapid_public_key: str = Field(default="")
vapid_claims_sub: str = Field(default="mailto:admin@microtv.ar")
```

---

### Paso B3 — Migración SQL

**Archivo nuevo:** `microtv-crm-backend/sql/20260512_push_subscriptions.sql`

```sql
-- Push subscriptions para notificaciones nativas (Web Push / VAPID)
-- Fecha: 2026-05-12

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    crm_user_id   UUID         NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
    endpoint      TEXT         NOT NULL UNIQUE,
    p256dh        TEXT         NOT NULL,
    auth          TEXT         NOT NULL,
    user_agent    TEXT         NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user
    ON push_subscriptions(crm_user_id);
```

> `UNIQUE` en `endpoint` permite que un mismo usuario tenga N suscripciones (N dispositivos/navegadores) y que el upsert por endpoint sea idempotente.

---

### Paso B4 — Modelo SQLAlchemy

**Archivo nuevo:** `microtv-crm-backend/src/crm_backend/models/push_subscription.py`

```python
"""Push subscription model para notificaciones nativas Web Push."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from crm_backend.db.base import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id", ondelete="CASCADE"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

---

### Paso B5 — Repositorio

**Archivo nuevo:** `microtv-crm-backend/src/crm_backend/repositories/push_subscription_repository.py`

```python
"""Repositorio para suscripciones push."""

from __future__ import annotations

from sqlalchemy.orm import Session

from crm_backend.models.push_subscription import PushSubscription


class PushSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, crm_user_id: str, endpoint: str, p256dh: str, auth: str, user_agent: str | None = None) -> PushSubscription:
        existing = self._session.query(PushSubscription).filter_by(endpoint=endpoint).first()
        if existing:
            existing.crm_user_id = crm_user_id
            existing.p256dh = p256dh
            existing.auth = auth
            existing.user_agent = user_agent
            self._session.flush()
            return existing
        sub = PushSubscription(
            crm_user_id=crm_user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
        )
        self._session.add(sub)
        self._session.flush()
        return sub

    def delete_by_endpoint(self, endpoint: str) -> None:
        self._session.query(PushSubscription).filter_by(endpoint=endpoint).delete()
        self._session.flush()

    def list_for_user(self, crm_user_id: str) -> list[PushSubscription]:
        return self._session.query(PushSubscription).filter_by(crm_user_id=crm_user_id).all()
```

Registrar en `microtv-crm-backend/src/crm_backend/repositories/__init__.py` si aplica.

---

### Paso B6 — Servicio de push

**Archivo nuevo:** `microtv-crm-backend/src/crm_backend/services/push_notification_service.py`

```python
"""Servicio de envío de push notifications via VAPID/Web Push."""

from __future__ import annotations

import json
import logging

from pywebpush import webpush, WebPushException

from crm_backend.core.config import Settings
from crm_backend.repositories.push_subscription_repository import PushSubscriptionRepository

logger = logging.getLogger(__name__)


class PushNotificationService:
    def __init__(
        self,
        push_subscription_repository: PushSubscriptionRepository,
        settings: Settings,
    ) -> None:
        self._repo = push_subscription_repository
        self._settings = settings

    def send_to_user(self, crm_user_id: str, title: str, body: str, url: str | None = None) -> None:
        """Envía una push notification a todos los dispositivos del usuario.

        Los errores de envío se logean y no se propagan — nunca deben romper
        el flujo de negocio que dispara la notificación in-app.
        """
        subscriptions = self._repo.list_for_user(crm_user_id)
        payload = json.dumps({"title": title, "body": body, "url": url or "/"})

        stale_endpoints: list[str] = []

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=self._settings.vapid_private_key,
                    vapid_claims={"sub": self._settings.vapid_claims_sub},
                )
            except WebPushException as exc:
                response = getattr(exc, "response", None)
                status_code = response.status_code if response is not None else None
                if status_code == 410:
                    # Suscripción expirada o revocada por el navegador
                    stale_endpoints.append(sub.endpoint)
                else:
                    logger.warning("Push send failed for user %s endpoint %s: %s", crm_user_id, sub.endpoint, exc)
            except Exception as exc:
                logger.warning("Push send unexpected error for user %s: %s", crm_user_id, exc)

        for endpoint in stale_endpoints:
            try:
                self._repo.delete_by_endpoint(endpoint)
            except Exception as exc:
                logger.warning("Failed to remove stale push subscription: %s", exc)
```

---

### Paso B7 — Endpoints REST

**Archivo nuevo:** `microtv-crm-backend/src/crm_backend/api/endpoints/push_subscriptions.py`

```python
"""Endpoints REST para gestión de suscripciones push."""

from fastapi import APIRouter, Depends, Request, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_push_subscription_repository
from crm_backend.repositories.push_subscription_repository import PushSubscriptionRepository
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.schemas.common import ErrorResponse
from pydantic import BaseModel

router = APIRouter(prefix="/notifications/push-subscription", tags=["push-notifications"])


class PushSubscriptionBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None


class DeletePushSubscriptionBody(BaseModel):
    endpoint: str


@router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}},
)
def upsert_push_subscription(
    body: PushSubscriptionBody,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    repo: PushSubscriptionRepository = Depends(get_push_subscription_repository),
) -> None:
    repo.upsert(
        crm_user_id=actor.crm_user.crm_user_id,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth,
        user_agent=body.user_agent,
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}},
)
def delete_push_subscription(
    body: DeletePushSubscriptionBody,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    repo: PushSubscriptionRepository = Depends(get_push_subscription_repository),
) -> None:
    repo.delete_by_endpoint(body.endpoint)
```

---

### Paso B8 — Registrar router

**Archivo:** `microtv-crm-backend/src/crm_backend/api/router.py`

```python
from crm_backend.api.endpoints.push_subscriptions import router as push_subscriptions_router

# ... (al final, junto a los otros include_router)
api_router.include_router(push_subscriptions_router)
```

---

### Paso B9 — Providers de DI

**Archivo:** `microtv-crm-backend/src/crm_backend/api/dependencies.py`

```python
from crm_backend.repositories.push_subscription_repository import PushSubscriptionRepository
from crm_backend.services.push_notification_service import PushNotificationService

def get_push_subscription_repository(session: Session = Depends(get_db_session)) -> PushSubscriptionRepository:
    return PushSubscriptionRepository(session)

def get_push_notification_service(
    repo: PushSubscriptionRepository = Depends(get_push_subscription_repository),
    settings: Settings = Depends(get_settings),
) -> PushNotificationService:
    return PushNotificationService(push_subscription_repository=repo, settings=settings)
```

---

### Paso B10 — Hookear push en `NotificationService.notify()`

**Archivo:** `microtv-crm-backend/src/crm_backend/services/notification_service.py`

`PushNotificationService` se inyecta como dependencia opcional (`None` por defecto) para no romper los tests existentes que construyen `NotificationService` directamente.

```python
class NotificationService:
    def __init__(
        self,
        notification_repository: NotificationRepository,
        user_repository: CrmUserRepository,
        push_notification_service: PushNotificationService | None = None,
    ) -> None:
        self._notification_repository = notification_repository
        self._user_repository = user_repository
        self._push_notification_service = push_notification_service
```

En `notify()`, después de `_notification_repository.save(notification)`:

```python
    def notify(self, *, recipient_crm_user_id, notification_type, title, body, ...) -> Notification:
        notification = Notification(...)
        saved = self._notification_repository.save(notification)

        if self._push_notification_service is not None:
            try:
                self._push_notification_service.send_to_user(
                    crm_user_id=recipient_crm_user_id,
                    title=title,
                    body=body,
                )
            except Exception as exc:
                logger.warning("Push dispatch failed for notification %s: %s", saved.notification_id, exc)

        return saved
```

Actualizar el factory `get_notification_service` en `dependencies.py` para pasar `push_notification_service`:

```python
def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repository),
    user_repo: CrmUserRepository = Depends(get_crm_user_repository),
    push_service: PushNotificationService = Depends(get_push_notification_service),
) -> NotificationService:
    return NotificationService(
        notification_repository=notification_repo,
        user_repository=user_repo,
        push_notification_service=push_service,
    )
```

---

## Fase B2 — Frontend

### Paso B11 — Agregar `vapidPublicKey` a la config de runtime

**Archivo:** `microtv-crm-frontend/src/app/core/config/crm-api.config.ts`

Agregar al tipo `CrmRuntimeConfig`:

```typescript
type CrmRuntimeConfig = {
  crmApiBaseUrl?: string;
  vapidPublicKey?: string;
  // ... resto de campos existentes
};
```

Agregar al final del archivo (mismo patrón que `crmApiConfig`):

```typescript
export const crmPushConfig = {
  vapidPublicKey: runtimeConfig?.vapidPublicKey?.trim() ?? '',
};
```

---

### Paso B12 — Nuevo servicio `PushNotificationService`

**Archivo nuevo:** `microtv-crm-frontend/src/app/core/services/push-notification.service.ts`

```typescript
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
      const sub = await this.swPush.requestSubscription({
        serverPublicKey: crmPushConfig.vapidPublicKey,
      });

      const json = sub.toJSON();
      const keys = json.keys as { p256dh: string; auth: string } | undefined;
      if (!json.endpoint || !keys?.p256dh || !keys?.auth) return;

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
      // Permiso denegado o SW no disponible — no-op silencioso
    }
  }

  async unsubscribe(): Promise<void> {
    if (!this.swPush.isEnabled) return;

    try {
      const sub = await firstValueFrom(this.swPush.subscription);
      if (!sub) return;

      const endpoint = sub.endpoint;
      await this.swPush.unsubscribe();

      await firstValueFrom(
        this.http.delete(
          `${crmApiConfig.baseUrl}/notifications/push-subscription`,
          {
            body: { endpoint },
            headers: this.authHeaders,
          }
        )
      ).catch(() => {
        // Si el token ya expiró al momento del logout, ignorar el error de la API
      });
    } catch {
      // SW no disponible o sin suscripción activa
    }
  }

  private get authHeaders(): HttpHeaders {
    const token = this.authSessionService.sessionSnapshot()?.tokens.access_token;
    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : new HttpHeaders();
  }
}
```

---

### Paso B13 — Disparar desde `AppShellComponent`

**Archivo:** `microtv-crm-frontend/src/app/layout/components/app-shell/app-shell.component.ts`

Inyectar `PushNotificationService` y reaccionar a `isAuthenticated$` en el constructor:

```typescript
import { distinctUntilChanged, filter, pairwise, startWith } from 'rxjs';
import { PushNotificationService } from '../../../core/services/push-notification.service';

// En la clase:
private readonly pushNotificationService = inject(PushNotificationService);
private readonly authSessionService = inject(AuthSessionService);

constructor() {
  // ... código existente del constructor ...

  this.authSessionService.isAuthenticated$
    .pipe(
      startWith(false as boolean),
      distinctUntilChanged(),
      pairwise(),
      takeUntilDestroyed(this.destroyRef)
    )
    .subscribe(([prev, curr]) => {
      if (!prev && curr) {
        // Login: solicitar permiso y registrar suscripción
        void this.pushNotificationService.requestAndSubscribe();
      } else if (prev && !curr) {
        // Logout: eliminar suscripción
        void this.pushNotificationService.unsubscribe();
      }
    });
}
```

> `pairwise()` + `startWith(false)` garantiza que sólo se actúa en la **transición** (login o logout), no cada vez que el observable emite el mismo valor.

---

## Archivos modificados y nuevos

### Frontend

| Archivo | Tipo | Cambio |
|---|---|---|
| `app-shell.component.scss` | Editar | `height: 100dvh` + `overflow-y: auto` en content |
| `app-shell.component.ts` | Editar | Inyectar push service, reaccionar a auth transitions |
| `core/config/crm-api.config.ts` | Editar | Agregar `vapidPublicKey` y `crmPushConfig` |
| `core/services/push-notification.service.ts` | **Nuevo** | Wrapper SwPush con `requestAndSubscribe()` y `unsubscribe()` |

### Backend

| Archivo | Tipo | Cambio |
|---|---|---|
| `pyproject.toml` | Editar | Agregar `pywebpush>=2.0,<3.0` |
| `core/config.py` | Editar | Agregar campos VAPID a `Settings` |
| `sql/20260512_push_subscriptions.sql` | **Nuevo** | Tabla `push_subscriptions` |
| `models/push_subscription.py` | **Nuevo** | SQLAlchemy model |
| `repositories/push_subscription_repository.py` | **Nuevo** | `upsert`, `delete_by_endpoint`, `list_for_user` |
| `services/push_notification_service.py` | **Nuevo** | `send_to_user()` vía pywebpush |
| `api/endpoints/push_subscriptions.py` | **Nuevo** | `POST` + `DELETE /notifications/push-subscription` |
| `api/router.py` | Editar | Registrar push router |
| `api/dependencies.py` | Editar | Providers para push repo y push service |
| `services/notification_service.py` | Editar | Inyectar push service; llamar en `notify()` |

---

## Verificación

| # | Escenario | Resultado esperado |
|---|---|---|
| A1 | Abrir `/tickets` con muchos items | Barra de scroll interna; el browser no scrollea |
| A2 | Navegar entre rutas | Scroll vuelve a `top: 0` automáticamente |
| B1 | Login fresco en navegador sin permiso previo | Aparece dialog de permisos del OS/browser, una sola vez |
| B2 | Aceptar permiso | Fila aparece en tabla `push_subscriptions` en DB |
| B3 | Trigger `TICKET_ASSIGNED` en el sistema | Notificación push llega al navegador/teléfono, incluso con la app en segundo plano |
| B4 | Rechazar permiso | Sin errores en consola; app funciona normalmente; sin fila en DB |
| B5 | Logout | `unsubscribe()` se ejecuta; fila eliminada de DB |
| B6 | Mismo usuario, dos navegadores | Dos filas en DB (una por endpoint); ambos reciben el push |
| B7 | Suscripción expirada (410 del browser push service) | Fila eliminada automáticamente de DB; no rompe el flujo |

---

## Decisiones

- **Scroll al nivel del shell** — todas las rutas se benefician de un único cambio CSS. No hay modificaciones en `tickets-page`, `tasks-page` ni sus tablas.
- **VAPID public key via `__CRM_RUNTIME_CONFIG__`** — mismo patrón que `crmApiBaseUrl`; no requiere recompilar la app por entorno.
- **`pywebpush`** — biblioteca Python más establecida para Web Push con VAPID.
- **Push failure no propaga** — `send_to_user()` nunca lanza excepciones al caller; sólo loguea. El flujo de negocio que disparó la notificación in-app no se ve afectado.
- **Logout limpia la suscripción** — el usuario no recibe notificaciones después de cerrar sesión.
- **Múltiples dispositivos** — `UNIQUE` en `endpoint`, no en `crm_user_id`. Un usuario puede tener N suscripciones activas (N dispositivos/navegadores).
- **`ngsw-config.json` y `app.config.ts`** — sin cambios; el service worker ya está configurado y registrado.
