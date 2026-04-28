# MicroTV CRM Backend

Backend inicial del CRM en FastAPI, con foco exclusivo en autenticación delegada hacia `auth.microtv.ar` y persistencia mínima local de contexto operativo.

## Alcance funcional actual

- `POST /auth/login`: recibe credenciales, delega login a `auth.microtv.ar`, valida/decodifica el JWT, persiste usuario/contexto local y devuelve un contrato usable por el frontend.
- `GET /auth/me`: valida un bearer token emitido por `auth.microtv.ar` y reconstruye la sesión local del CRM.
- `GET /stock/categories`: lista categorías reales del módulo inicial de depósito para YCC.
- `GET /stock/products`: lista productos persistidos con stock real.
- `POST /stock/products`: crea un producto real con categoría y stock inicial.
- `POST /stock/products/{id}/increase-stock`: aumenta stock persistido.
- `POST /stock/products/{id}/decrease-stock`: disminuye stock persistido sin permitir negativo.
- `GET /health`: healthcheck básico.

## Arquitectura

- `api`: endpoints y wiring HTTP.
- `services`: orquestación de casos de uso.
- `models`: entidades ORM locales del CRM.
- `repositories`: persistencia encapsulada por agregado principal.
- `adapters`: integración externa con `auth.microtv.ar`.

## Persistencia local mínima

El CRM guarda como fuente local:

- `crm_users.crm_user_id`
- `crm_users.auth_user_id`
- `crm_users.is_active_in_crm`
- asignaciones locales en `crm_user_roles`
- catálogo real en `stock_categories`
- productos reales en `stock_products`
- movimientos simples en `stock_movements`

El CRM guarda como snapshot/cache contextual de auth:

- `email`
- `display_name`
- `last_auth_membership_id`
- `last_auth_tenant_type`
- `last_auth_tenant_id`
- `last_auth_roles_json`
- timestamps de sincronización y último login

## Arranque local

1. Crear `.env` a partir de `.env.example`.
2. Instalar dependencias:

```bash
pip install -e .[test]
```

3. Levantar la API:

```bash
uvicorn crm_backend.main:app --reload --host 0.0.0.0 --port 8010
```

## Multimedia configurable

El backend soporta almacenamiento de archivos multimedia fuera del repo usando `.env`:

- `CRM_MEDIA_ROOT`: carpeta física donde se escriben archivos (por ejemplo `/opt/ycc/crm-media`).
- `CRM_MEDIA_PUBLIC_URL`: prefijo público montado por FastAPI (por ejemplo `/media`).

Subcarpetas usadas por módulo:

- `tasks/images`
- `tasks/videos`
- `products/images`
- `satisfaction/images`
- `satisfaction/videos`

Para compatibilidad legacy, el backend mantiene mounts de `/images` y `/videos` apuntando al directorio histórico `public/` del proyecto.

Ejemplo recomendado en Nginx:

```nginx
location /media/ {
  proxy_pass http://127.0.0.1:8202;
}
```

## Contrato HTTP actual

### `POST /auth/login`

Request:

```json
{
  "email": "admin.crm@microtv.com",
  "password": "Passw0rd!"
}
```

Respuesta autenticada:

```json
{
  "status": "authenticated",
  "tokens": {
    "access_token": "jwt",
    "refresh_token": "jwt",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_expires_in": 604800
  },
  "user": {
    "crm_user_id": "uuid",
    "auth_user_id": "external-user-id",
    "email": "admin.crm@microtv.com",
    "display_name": "Admin Microtv",
    "primary_role": "admin",
    "role_keys": ["admin"],
    "active_membership": {
      "membership_id": "membership-id",
      "tenant_type": "company",
      "tenant_id": "MICROTV",
      "auth_roles": ["platform_admin"]
    }
  }
}
```

Posibles estados alternativos:

- `context_selection_required`
- `access_pending`

Errores estables:

- `401 invalid_credentials`
- `401 unauthenticated`
- `403 crm_role_required`
- `502 invalid_auth_context`
- `503 auth_unavailable`

## Auth local para el CRM

El entorno Docker auxiliar está en `docker-compose.auth-local.yml` y usa un Dockerfile separado, sin tocar el Dockerfile original del proyecto auth.

```bash
docker compose -f docker-compose.auth-local.yml up --build
```

Credenciales seed por defecto:

- `admin.crm@microtv.com` / `Passw0rd!`
- `operador.crm@yccbrothers.com` / `Passw0rd!`
- `deposito.aux@yccbrothers.com` / `Passw0rd!`

## Nota de diseño

La asignación automática inicial de rol local del CRM existe solo como política de bootstrap para que la maqueta actual pueda entrar al sistema. La autorización definitiva del CRM sigue siendo local y debe evolucionar luego mediante administración explícita de `crm_roles` y `crm_user_roles`.
