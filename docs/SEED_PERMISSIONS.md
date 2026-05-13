# Carga de Permisos por Defecto

## Resumen

El sistema incluye un endpoint idempotente `POST /settings/permissions/seed` que carga automáticamente los permisos por defecto para los roles `admin`, `deposito` y `ejecutivo`.

## Permisos Cargados

### Admin
- `stock.manage` → `TRUE`
- `stock.delete_product` → `TRUE`
- `ticket.reassign` → `TRUE`
- `order.reassign` → `TRUE`
- `comment.delete` → `TRUE`

### Deposito (Warehouse Staff)
- `stock.manage` → `TRUE`
- `stock.delete_product` → `FALSE` (solo lectura)

### Ejecutivo (Executive)
- `ticket.reassign` → `TRUE`
- `order.reassign` → `TRUE`

## Uso

### 1. **Desarrollo (SQLite)**
Al iniciar el backend en modo desarrollo, los permisos se cargan automáticamente mediante el script de bootstrap en `src/crm_backend/db/bootstrap.py`.

**Verificación:**
```bash
# En Python/FastAPI interactive shell
from crm_backend.db.bootstrap import seed_database
seed_database()  # Ya se ejecuta automáticamente
```

### 2. **Producción (PostgreSQL)**

La carga de permisos ocurre en dos momentos:

#### a) Migración automática (recomendado)
Cuando ejecutas `deploy/migrate_prod.sh`, la migración `20260512_permissions_and_activity_log.sql` se aplica automáticamente:

```bash
cd microtv-crm-backend/deploy
bash migrate_prod.sh
```

El script verifica que las tablas `crm_role_permissions` y `crm_user_permissions` existan y están pobladas correctamente.

#### b) Carga manual via API (si las migraciones fallaron)

Si después de ejecutar las migraciones el BD está vacío, puedes recargar los permisos usando el endpoint:

```bash
# 1. Obtén un token JWT como administrador
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin_password"
  }'
# Guarda el token de la respuesta

# 2. Ejecuta el seed via API
curl -X POST http://localhost:8000/settings/permissions/seed \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Respuesta esperada:
# {
#   "message": "Permisos por defecto cargados",
#   "count": 9
# }
```

### 3. **Frontend (Angular)**

Un botón de "Cargar Permisos Predeterminados" en la pestaña de Permisos permite recargar manualmente:

```typescript
// En permissions-tab.component.ts
seedDefaultPermissions() {
  this.settingsManagementService.seedDefaultPermissions().subscribe(
    (response) => {
      console.log('Permisos cargados:', response.count);
      this.load();  // Recargar lista
    }
  );
}
```

## Idempotencia

El endpoint es **idempotente**: puede ejecutarse múltiples veces sin crear duplicados. La BD usa `ON CONFLICT DO NOTHING` a nivel SQL, por lo que:

- Primera ejecución: Inserta 9 registros
- Segunda ejecución: No inserta nada (ya existen)
- Tercera ejecución: No inserta nada (ya existen)

## Verificación

Consulta la BD para confirmar que se cargaron los permisos:

```sql
SELECT role_key, permission_code, is_granted 
FROM crm_role_permissions 
ORDER BY role_key, permission_code;
```

Deberías ver 9 filas (3 roles × 3 permisos promedio).

## Troubleshooting

### "Tabla crm_role_permissions no existe"
- Ejecuta las migraciones: `bash deploy/migrate_prod.sh`
- O aplica manualmente: `psql -f sql/20260512_permissions_and_activity_log.sql`

### Permisos vacíos después de migración
- Ejecuta el endpoint: `POST /settings/permissions/seed` como admin
- O reaplica la migración SQL: `psql -f sql/20260512_permissions_and_activity_log.sql`

### Error 403 al llamar al endpoint
- Verifica que estés logeado como `admin`
- Valida que tu JWT sea válido y no esté expirado

## Detalles Técnicos

- **Endpoint**: `POST /settings/permissions/seed`
- **Autenticación**: Requiere rol `admin`
- **Payload**: Vacío `{}`
- **Response**: `{"message": "...", "count": number}`
- **Status**: `200 OK` (éxito), `403 Forbidden` (no admin), `401 Unauthorized` (no autenticado)
- **Log**: Genera evento `settings.permissions_seeded` en la tabla `activity_log`
