# 0010 — Fix Production: 500s en Tasks/Tickets, Roles Dropdown Vacío, Dark Theme Blancos, Marcador Leaflet

## Problema

En producción (`crm.ycc.group`) se reportan cuatro issues simultáneos:

**1. 500s masivos en consola**
```
api/tasks/assigned/me          → 500
api/tasks/unassigned/me        → 500
api/tasks/tracking/me          → 500
api/tasks/history/me           → 500
api/tasks/templates            → 500
api/tickets/assigned/me        → 500
api/tickets/unassigned/me      → 500
api/tickets/tracking/me        → 500
api/tickets/history/me         → 500
api/tickets/roles              → 500
```

**2. Dropdown de asignación de ticket vacío**  
Al seleccionar "Asignar ticket a usuario" o "Asignar ticket a rol" en el diálogo de creación de ticket, los `mat-select` no muestran ninguna opción. La DB sí tiene roles y usuarios asignados (`crm_user_role_assignments` poblado correctamente).

**3. Espacios blancos en dark theme**  
En modo oscuro, los paneles de `mat-select`, `mat-autocomplete`, `mat-option` y el diálogo `mat-dialog` muestran fondo blanco en lugar del color de superficie dark (`--surface-panel: #151b26`). El problema afecta a los overlays renderizados dentro de `.cdk-overlay-container` que está fuera del árbol DOM principal y no hereda los overrides de `html.theme-dark`.

**4. Marcador Leaflet no aparece en fallback**  
Cuando el mapa MapLibre falla (CORS/PNA/504), el fallback Leaflet carga los tiles de OSM pero el pin/marcador de ubicación no se renderiza. Esto sucede porque Webpack/esbuild elimina las referencias a los assets de imágenes del icono por defecto de Leaflet durante el build.

---

## Causa raíz

### 500s (issues 1 y 2)

Las 9 migraciones SQL del directorio `microtv-crm-backend/sql/` **no están aplicadas en la base de datos de producción**. Esto causa un `ProgrammingError: column "X" does not exist` en cada query que toca `tickets`, `tasks`, o tablas relacionadas.

- Para **tickets**: el `try/except` en `ticket_service.py` traga la excepción y retorna `[]` silenciosamente → los endpoints retornan `200 []` en lugar de 500, pero los datos no aparecen.
- Para **tasks**: no hay `try/except` en `tasks/application.py` → el error SQL se propaga → **500**.
- Para **`/tickets/roles`**: el error en el query de `crm_roles` (FK referenciada desde la migración del módulo tickets) propaga el 500 → el frontend recibe error en `listAssignableRoles()` → `roles()` signal queda vacío → dropdown vacío.

### Dark theme (issue 3)

`.cdk-overlay-container` es montado directamente sobre `<body>` por Angular CDK, fuera del host element. Los selectores `html.theme-dark .mat-mdc-select-panel` existen en `styles.css` pero **no están calificados con `.cdk-overlay-container`**, por lo que el overlay de Material renderizado en el CDK portal no recibe el `background` correcto. El `mat-mdc-option` tampoco tiene override explícito.

### Marcador Leaflet (issue 4)

`L.Icon.Default` resuelve las rutas de los iconos con rutas relativas a `leaflet/dist/images/` que el bundler no incluye en el output porque no son importaciones explícitas. Sin las imágenes, el `<img>` del marcador devuelve 404 y el ícono no se renderiza.

---

## Arquitectura

- No se cambia ningún modelo de datos ni ningún contrato de API.
- No se agregan features nuevas.
- Las migraciones SQL son **idempotentes** (todas usan `IF NOT EXISTS` o `ON CONFLICT DO NOTHING`), seguras de re-ejecutar.
- El fix de dark theme es CSS puro, sin tocar lógica de componentes.
- El fix de Leaflet agrega 3 líneas en el método `initLeafletFallback()` existente.

---

## Fase 1 — Base de datos: aplicar migraciones pendientes en producción

> **Bloqueante**: las Fases 2, 3 y 4 tienen efecto visible sólo después de completar ésta.

### 1.1 Verificar estado actual del schema

Conectarse a la DB de producción:

```bash
psql -U ycc -h 127.0.0.1 -p 5432 -d crm
```

Luego ejecutar:

```sql
-- Verificar columnas presentes en tickets
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'tickets'
ORDER BY column_name;

-- Verificar si existe la tabla crm_notifications
SELECT to_regclass('public.crm_notifications');

-- Verificar roles existentes
SELECT role_key, role_label, is_active FROM crm_roles ORDER BY role_key;
```

Columnas esperadas en `tickets` tras aplicar todas las migraciones:
- `requires_arrival_comment`, `arrival_registered_at`, `arrival_comment_id` (20260427)
- `requires_video_evidence`, `solution_comment_id` (20260430)

### 1.2 Script de migraciones: `migrate_prod.sh`

Crear el archivo `microtv-crm-backend/sql/migrate_prod.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PSQL="psql -U ycc -h 127.0.0.1 -p 5432 -d crm"

echo "=== Iniciando migraciones de producción ==="

run_migration() {
  local file="$1"
  echo "--- Aplicando: $file"
  $PSQL -f "$file"
  echo "    OK: $file"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_migration "$SCRIPT_DIR/20260414_task_schema_v4_delta.sql"
run_migration "$SCRIPT_DIR/20260414_task_schema_v4_1_hardening.sql"
run_migration "$SCRIPT_DIR/20260414_task_schema_v4_1_post_validation.sql"
run_migration "$SCRIPT_DIR/20260414_task_media_comment_link.sql"
run_migration "$SCRIPT_DIR/20260422_ticket_module.sql"
run_migration "$SCRIPT_DIR/20260423_crm_notifications.sql"
run_migration "$SCRIPT_DIR/20260427_ticket_arrival_comment.sql"
run_migration "$SCRIPT_DIR/20260428_notifications_seed.sql"
run_migration "$SCRIPT_DIR/20260430_ticket_profile_enhancements.sql"

echo ""
echo "=== Verificando estado final del schema ==="
$PSQL -c "
SELECT
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='requires_video_evidence') AS col_video_evidence,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='arrival_comment_id')      AS col_arrival_comment,
  EXISTS(SELECT 1 FROM information_schema.tables   WHERE table_name='crm_notifications')                               AS table_notifications,
  (SELECT count(*) FROM crm_roles WHERE is_active = TRUE)                                                              AS active_roles_count;
"

echo "=== Migraciones completadas ==="
```

Ejecutar desde el servidor de producción dentro del directorio `microtv-crm-backend/`:

```bash
chmod +x sql/migrate_prod.sh
./sql/migrate_prod.sh
```

El script usa `set -euo pipefail`: si cualquier migración falla se detiene inmediatamente e indica el archivo fallido. Como todas las migraciones son idempotentes, es seguro re-ejecutarlo.

### 1.3 Verificar seed de `crm_roles`

Si `SELECT * FROM crm_roles;` retorna 0 filas, ejecutar el seed del schema propuesto:

```sql
INSERT INTO crm_roles (role_key, role_label, description) VALUES
  ('admin_crm',          'Administrador del CRM',   'Acceso total al sistema CRM'),
  ('ejecutivo',          'Ejecutivo',               'Visualiza todos los módulos para seguimiento operativo'),
  ('tecnico_campo',      'Técnico de Campo',         'Ejecuta tareas y tickets en ubicaciones del cliente'),
  ('encargado_deposito', 'Encargado de Depósito',    'Gestiona inventario, despachos y recepciones'),
  ('dispatcher',         'Despachador/Coordinador',  'Asigna tareas, coordina logística, aprueba solicitudes')
ON CONFLICT (role_key) DO NOTHING;
```

---

## Fase 2 — Backend: resilencia de errores en task service

**Archivo:** `microtv-crm-backend/src/crm_backend/services/tasks/application.py`

El `ticket_service.py` ya tiene el patrón correcto: `try/except Exception → _logger.exception(...) → return []`. Replicarlo en todos los métodos de listado del task service para que un error de DB (sea por schema drift o cualquier otra causa) degrade a lista vacía en lugar de 500.

### Métodos a envolver

| Método | Línea aprox. | Retorno en error |
|---|---|---|
| `list_templates` | 195 | `[]` |
| `list_tasks_assigned_to_actor` | 250 | `[]` |
| `list_tracking_tasks_for_actor` | 254 | `[]` |
| `list_task_history_for_actor` | 264 | `[]` |
| `list_unassigned_subtasks_for_actor` | 268 | `[]` |

### Patrón a aplicar (replicar exactamente lo que hace ticket_service.py)

```python
def list_tasks_assigned_to_actor(self, actor: ResolvedCrmSession) -> list[Task]:
    self._ensure_read_access(actor)
    try:
        return self._task_repository.list_tasks_assigned_to_user(actor.crm_user.crm_user_id)
    except Exception:
        _logger.exception(
            "Failed to list assigned tasks for actor %s",
            getattr(actor.crm_user, "crm_user_id", "unknown"),
        )
        return []
```

Aplicar el mismo wrapper a los otros 4 métodos de listado. `_ensure_read_access` y `_ensure_admin_or_executive` quedan **fuera** del try/except (deben propagar 403 correctamente).

### Deploy

Rebuild y reiniciar el contenedor/servicio de backend en producción.

---

## Fase 3 — Frontend: dark theme — overlays de Angular CDK

**Archivo:** `microtv-crm-frontend/src/styles.css`

Agregar los overrides que le faltan al bloque de dark theme existente. El problema es que `.cdk-overlay-container` vive fuera del `<html>` subtree de los componentes; sus elementos hijo deben ser seleccionados explícitamente desde el root.

### CSS a agregar

Agregar inmediatamente después del bloque existente `html.theme-dark .mat-mdc-select-panel { ... }`:

```css
/* CDK overlay — select panel, autocomplete y opciones en dark mode */
html.theme-dark .cdk-overlay-container .mat-mdc-select-panel,
html.theme-dark .cdk-overlay-container .mat-mdc-autocomplete-panel {
  background: var(--surface-panel);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
}

html.theme-dark .cdk-overlay-container .mat-mdc-option {
  background: var(--surface-panel);
  color: var(--text-primary);
}

html.theme-dark .cdk-overlay-container .mat-mdc-option:hover:not(.mdc-list-item--disabled),
html.theme-dark .cdk-overlay-container .mat-mdc-option.mat-mdc-option-active {
  background: color-mix(in srgb, var(--surface-panel) 80%, white 20%);
}

html.theme-dark .cdk-overlay-container .mat-mdc-option .mdc-list-item__primary-text {
  color: var(--text-primary);
}
```

---

## Fase 4 — Frontend: dark theme — fondo de mapa Leaflet en modo oscuro

**Archivo:** `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.scss`

El selector `:host-context()` no está soportado en todos los browsers en modo `ViewEncapsulation.Emulated`. Usar `::ng-deep` en combinación con el selector de host para sobrescribir los estilos del shell y del container de Leaflet en dark mode.

### CSS a agregar

Agregar al final del archivo:

```scss
/* Dark mode: shell background y Leaflet container */
:host-context(html.theme-dark) .location-picker-map__shell {
  background: var(--surface-container, #1a1f2e);
}

:host-context(html.theme-dark) ::ng-deep .leaflet-container {
  background: #1a1f2e;
}
```

---

## Fase 5 — Frontend: marcador Leaflet en fallback

**Archivo:** `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.ts`

Dentro del método `initLeafletFallback()`, después de importar Leaflet dinámicamente y antes de crear el mapa, agregar el fix canónico para los assets del icono por defecto:

```typescript
// Fix Leaflet default marker icon assets (stripped by bundler)
const iconDefault = L.icon({
  iconUrl: 'assets/leaflet/marker-icon.png',
  iconRetinaUrl: 'assets/leaflet/marker-icon-2x.png',
  shadowUrl: 'assets/leaflet/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = iconDefault;
```

### Assets a copiar

Copiar los archivos desde `node_modules/leaflet/dist/images/` a `microtv-crm-frontend/public/assets/leaflet/`:

- `marker-icon.png`
- `marker-icon-2x.png`
- `marker-shadow.png`

```bash
mkdir -p microtv-crm-frontend/public/assets/leaflet
cp node_modules/leaflet/dist/images/marker-icon.png microtv-crm-frontend/public/assets/leaflet/
cp node_modules/leaflet/dist/images/marker-icon-2x.png microtv-crm-frontend/public/assets/leaflet/
cp node_modules/leaflet/dist/images/marker-shadow.png microtv-crm-frontend/public/assets/leaflet/
```

Como están en `public/`, Angular los servirá en `/assets/leaflet/` sin configuración adicional en `angular.json`.

---

## Verificación

### DB (post Fase 1)

```sql
-- Todas deben retornar TRUE
SELECT
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='requires_video_evidence') AS col_video_evidence,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='arrival_comment_id') AS col_arrival_comment,
  EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='crm_notifications') AS table_notifications,
  (SELECT count(*) FROM crm_roles WHERE is_active = TRUE) AS active_roles_count;
```

### Backend (post Fase 2)

```
GET /api/tasks/assigned/me       → 200 (no 500)
GET /api/tasks/templates         → 200 (no 500)
GET /api/tickets/roles           → 200 con array de roles (ej. [{role_key: "admin_crm", ...}, ...])
```

### Frontend (post Fases 3–5)

1. Abrir diálogo "Crear ticket" → seleccionar un rol en "Asignar a rol" → el segundo dropdown "Asignar a usuario" debe popularse con usuarios del rol.
2. En modo oscuro, abrir cualquier `mat-select` → el panel desplegable debe ser `#151b26`, no blanco.
3. Forzar fallo del mapa MapLibre (desconectar red o bloquear `map.microtv.ar`) → el mapa Leaflet debe renderizar tiles OSM + un pin en las coordenadas configuradas, con fondo oscuro en dark mode.

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `microtv-crm-backend/sql/migrate_prod.sh` | Crear script de migraciones (nuevo archivo) |
| `microtv-crm-backend/src/crm_backend/services/tasks/application.py` | Agregar try/except a 5 métodos de listado |
| `microtv-crm-frontend/src/styles.css` | Agregar overrides CDK overlay dark mode |
| `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.scss` | Agregar overrides dark mode shell + leaflet-container |
| `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.ts` | Fix icono Leaflet en `initLeafletFallback()` |
| `microtv-crm-frontend/public/assets/leaflet/` | Agregar 3 archivos de imagen copiados desde node_modules |
