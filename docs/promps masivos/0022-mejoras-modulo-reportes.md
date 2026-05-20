# 0022 — Mejoras al Módulo de Reportes

## Objetivo

Extender el módulo de reportes existente con dos mejoras principales:

1. **"Mis Reportes" mejorado** — cada usuario puede generar reportes sobre sus propios tickets y tareas con métricas estadísticas (promedio, mínimo, máximo), gráficos apropiados por tipo de dato, y exportación a PDF.
2. **"Reportes Ejecutivos"** — nueva tab restringida a administradores y ejecutivos con performance gráfica y concisa de cada empleado/rol, orientada a evaluación de desempeño.

---

## Decisiones de diseño

| Decisión | Valor |
|---|---|
| Scope "Mis Tickets" | Tickets donde el usuario es creador **O** está asignado |
| Scope "Mis Tareas" | Tareas donde `current_assigned_crm_user_id = usuario actual` |
| Contenido del PDF exportado | KPIs + gráfico + tabla de datos (todo lo visible en pantalla) |
| Acceso a "Reportes Ejecutivos" | Solo administradores y ejecutivos |
| Definición de "rechazo de solución" | Ticket que volvió de `PENDING_APPROVAL` a `IN_PROGRESS` u `OPEN` (vía `TicketAuditEvent`) |

---

## Fase 1 — Backend: Endpoints de Mis Reportes

> Puede implementarse en paralelo con la Fase 2.

### 1.1 `reports_service.py` — método `my_tickets_report(current_user_id, filters)`

- **Query:** `Ticket WHERE (assigned_user_id = X OR created_by_crm_user_id = X) AND created_at BETWEEN date_from AND date_to`
- **Filtros adicionales:** `category_id`, `priority`, `client_id`, `location_id`, `group_by`
- **KPIs:** total, resueltos, cerrados, abiertos, avg/min/max `resolution_hours` (`resolved_at - created_at`), `resolution_rate %`
- **Series:** según `group_by` — `status | priority | category | client | location | time-series diario`
- **Rows:** nº ticket, título, estado, prioridad, categoría, cliente, fecha creación, horas de resolución

### 1.2 `reports_service.py` — método `my_tasks_report(current_user_id, filters)`

- **Query:** `Task WHERE current_assigned_crm_user_id = X AND created_at BETWEEN date_from AND date_to`
- **Filtros:** `category_id`, `priority`, `client_id`, `group_by`
- **KPIs:** total, completadas, pendientes, bloqueadas, avg/min/max `completion_hours` (`finalized_at - created_at`), `completion_rate %`
- **Series:** `status | category | client`
- **Rows:** tarea, estado, prioridad, categoría, cliente, fecha inicio, horas hasta cierre

### 1.3 Nuevos endpoints en `api/endpoints/reports.py`

| Método | Path | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/reports/my-tickets` | cualquier rol autenticado | Reportes de tickets propios del usuario |
| `GET` | `/api/reports/my-tasks` | cualquier rol autenticado | Reportes de tareas propias del usuario |
| `GET` | `/api/reports/options/locations` | cualquier rol autenticado | Lista de ubicaciones para filtro dropdown |

El `current_user_id` se extrae automáticamente del token JWT, sin parámetro explícito.

### 1.4 Nuevos schemas en `schemas/reports.py`

- `MyTicketReportParams` — query params: `date_from`, `date_to`, `category_id`, `priority`, `client_id`, `location_id`, `group_by`
- `MyTaskReportParams` — similar sin `location_id`
- `MyTicketReportResponse` — `kpis`, `series`, `rows`, `chart_kind`, `report_kind`
- `MyTaskReportResponse` — ídem

---

## Fase 2 — Backend: Reportes Ejecutivos

> Puede implementarse en paralelo con la Fase 1.

### 2.1 `reports_service.py` — método `executive_performance_report(filters)`

- **Query principal:** tickets con JOIN a `CrmUser` (asignado), sub-query `COUNT(TicketComment)` por ticket, sub-query de rechazos desde `TicketAuditEvent` (transición `PENDING_APPROVAL → IN_PROGRESS/OPEN`)
- **Filtros:** `date_from`, `date_to`, `group_by` (user | role), `category_id`, `priority`, `client_id`
- **Por usuario/rol:**
  - `display_name`, rol principal
  - `total_assigned`, `closed_count`, `rejected_count`
  - `avg_close_hours`, `min_close_hours`, `max_close_hours` (desde `closed_at - created_at`)
  - `total_comments`, `avg_comments_per_ticket`
- **KPIs globales:** `overall_avg_close_hours`, mejor desempeño (min avg), peor desempeño (max avg), total empleados analizados
- **Series:** `horizontal_bar` de usuarios rankeados por `avg_close_hours`

### 2.2 Nuevo endpoint

| Método | Path | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/reports/executive/performance` | solo admin/ejecutivo | Performance de empleados por período y filtros |

### 2.3 Nuevos schemas

- `ExecutivePerformanceParams`
- `ExecutivePerformanceRow`
- `ExecutivePerformanceResponse` — `kpis`, `series` (horizontal_bar), `rows`, `chart_kind="horizontal_bar"`

---

## Fase 3 — Frontend: "Mis Reportes" mejorado

> Depende de que la Fase 1 esté implementada.

### 3.1 `report.types.ts`

- Agregar `location_id?: string` a la interfaz `ReportRequestFilters`
- Agregar `locations: ReportOption[]` a `ReportFilterCatalogs`
- Habilitar las siguientes cards en la categoría `mis-reportes` de `REPORT_CARDS`:
  - `my-tickets` — "Mis Tickets" — chart: `bar` para distribución de estados, `donut` para prioridades
  - `my-tasks` — "Mis Tareas" — chart: `bar` para estados, `area` para evolución temporal

### 3.2 Quick-date presets — `report-detail.component.ts`

Agregar dos presets nuevos:

| Preset | Rango |
|---|---|
| **Hoy** | Solo el día actual (00:00 → 23:59) |
| **Este año** | 1 de enero → 31 de diciembre del año en curso |

Orden final: **Hoy** · Esta semana · Este mes · Último mes · Este año · Personalizado

### 3.3 `report-detail.component.ts` — `buildFilters()`

- Mapear `my-tickets` → endpoint `/api/reports/my-tickets`
- Mapear `my-tasks` → endpoint `/api/reports/my-tasks`
- Mostrar dropdown `location_id` **solo** para el reporte `my-tickets`
- Mostrar KPIs de avg/min/max como tarjetas comparativas side-by-side

### 3.4 `reports.service.ts`

- En `loadFilterCatalogs()`: agregar llamada a `GET /api/reports/options/locations` para los reports que usen `location_id`
- Agregar mapeos de endpoint base para `my-tickets` y `my-tasks`

---

## Fase 4 — Frontend: Tab "Reportes Ejecutivos"

> Depende de que la Fase 2 esté implementada.

### 4.1 `report.types.ts` — nueva tab y cards

Agregar tab:

```ts
{ key: 'ejecutivos', label: 'Reportes Ejecutivos', roles: ['admin', 'ejecutivo'] }
```

Agregar cards en categoría `ejecutivos`:

| `reportId` | Label | Chart |
|---|---|---|
| `executive-performance` | Desempeño por empleado | `horizontal_bar` |
| `executive-by-category` | Resolución por categoría | `bar` |
| `executive-by-priority` | Resolución por criticidad | `bar` |
| `executive-by-client` | Análisis por cliente | `bar` |

### 4.2 `reports.component.ts` — visibilidad de tabs por rol

- Filtrar `REPORT_TABS` según el rol del usuario actual (leer del perfil/auth service)
- Ocultar completamente la tab `ejecutivos` para usuarios sin roles `admin` o `ejecutivo`
- No solo ocultar en UI: el guard de ruta también debe rechazar el acceso directo por URL

### 4.3 `report-detail.component.ts` — `buildFilters()` extendido

| `reportId` | Endpoint | `group_by` implícito |
|---|---|---|
| `executive-performance` | `/api/reports/executive/performance` | `user` (seleccionable en filtro) |
| `executive-by-category` | `/api/reports/executive/performance` | forzado a `category` |
| `executive-by-priority` | `/api/reports/executive/performance` | forzado a `priority` |
| `executive-by-client` | `/api/reports/executive/performance` | forzado a `client` |

### 4.4 `reports.service.ts`

- Los filtros de usuario (`/api/reports/options/users`) ya existen; reutilizar para el dropdown de filtro ejecutivo
- Agregar opción de filtro por rol (`/api/reports/options/roles`) si no existe

---

## Fase 5 — Frontend: Exportación a PDF

> Independiente de las Fases 3 y 4; puede implementarse en paralelo.

### 5.1 Instalar dependencias

```bash
npm install jspdf html2canvas
```

### 5.2 `report-detail.component.ts` — lógica de exportación

1. Al presionar "Exportar PDF", capturar por secciones vía `html2canvas`:
   - **Header**: nombre del reporte, usuario que generó, timestamp de generación, filtros aplicados
   - **Bloque KPIs**: tarjetas de métricas principales
   - **Bloque Chart**: el gráfico Recharts renderizado
   - **Bloque Tabla**: la tabla de datos con paginación desactivada temporalmente
2. Componer las imágenes en un documento `jsPDF` en orientación **landscape**
3. Insertar saltos de página entre secciones si el contenido excede el alto de la página
4. Disparar la descarga del archivo

Nombre del archivo: `{reportId}_{YYYY-MM-DD}.pdf`

### 5.3 `report-detail.component.html`

Agregar botón "Exportar PDF" junto al botón CSV existente:

```html
<!-- junto al botón de exportar CSV -->
<button (click)="exportPdf()" [disabled]="exportingPdf">
  <span *ngIf="!exportingPdf">Exportar PDF</span>
  <span *ngIf="exportingPdf">Generando...</span>
</button>
```

---

## Resumen de archivos a modificar

### Backend

| Archivo | Cambios |
|---|---|
| `src/crm_backend/services/reports_service.py` | 3 nuevos métodos: `my_tickets_report`, `my_tasks_report`, `executive_performance_report` |
| `src/crm_backend/api/endpoints/reports.py` | 4 nuevos endpoints + 1 endpoint de opciones (`/options/locations`) |
| `src/crm_backend/schemas/reports.py` | `MyTicketReportParams`, `MyTaskReportParams`, `MyTicketReportResponse`, `MyTaskReportResponse`, `ExecutivePerformanceParams`, `ExecutivePerformanceRow`, `ExecutivePerformanceResponse` |

### Frontend

| Archivo | Cambios |
|---|---|
| `src/app/features/reports/report.types.ts` | REPORT_TABS con roles, REPORT_CARDS nuevas, `ReportRequestFilters` extendida, `ReportFilterCatalogs` extendida |
| `src/app/features/reports/reports.component.ts/.html` | Filtrado de tabs visible por rol del usuario |
| `src/app/features/reports/report-detail.component.ts/.html` | Nuevos quick-dates, dropdown `location_id`, PDF export, `buildFilters()` extendido |
| `src/app/features/reports/reports.service.ts` | Nuevos mapeos de endpoint, catálogo de locations |
| `package.json` | Agregar `jspdf` y `html2canvas` |

---

## Checklist de verificación

- [ ] `npm run build` sin errores tras los cambios en el frontend
- [ ] `GET /api/reports/my-tickets` devuelve KPIs con avg/min/max para el usuario autenticado, filtrados correctamente
- [ ] `GET /api/reports/my-tasks` devuelve stats de completion correctos para el usuario autenticado
- [ ] `GET /api/reports/executive/performance` retorna `403` para usuarios con rol técnico
- [ ] Tab "Reportes Ejecutivos" no aparece en la UI para técnicos/operadores
- [ ] Acceso directo por URL a `/reports/ejecutivos` queda bloqueado por guard para no-admin/ejecutivo
- [ ] El preset "Hoy" filtra solo el día actual; "Este año" filtra desde el 1 de enero
- [ ] El filtro `location_id` aparece únicamente en el reporte `my-tickets`
- [ ] El botón "Exportar PDF" genera un archivo con KPIs + gráfico + tabla
- [ ] El PDF incluye header con nombre del reporte, usuario, timestamp y filtros aplicados
- [ ] Las métricas de rechazo en reportes ejecutivos corresponden a transiciones `PENDING_APPROVAL → IN_PROGRESS/OPEN`
