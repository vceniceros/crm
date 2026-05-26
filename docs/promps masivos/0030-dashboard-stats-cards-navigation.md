# 0030 — Dashboard: Stats Cards accionables con navegación filtrada

## Contexto

Las cards de estadísticas del dashboard principal son puramente decorativas: muestran un valor numérico pero no llevan a ningún lado. El objetivo es que cada card relevante navegue directamente a la vista filtrada correspondiente del usuario actual, reutilizando las rutas y tabs que ya existen.

---

## Mapeo de KPIs a rutas

El backend ya devuelve un campo `key` por cada KPI en `GET /api/dashboard/summary`. El frontend lo recibe pero actualmente lo descarta.

| `kpi.key` | Card label | Ruta destino | Lógica |
|---|---|---|---|
| `open_tickets` | Tickets Abiertos | `/tickets` | Tab 0 = "Asignados a mí" es el default |
| `pending_external` | Pendientes externos | `/tasks?status=PENDING_APPROVAL` | Tab 0 = "Asignados a mí" + filtro de status pre-seteado |
| `closed_this_month` | Cerradas (mes) | `/tasks/history` | Ruta existente que activa el tab 3 historial |
| `tasks_in_progress` | Tareas en Progreso | *(sin navegación)* | No solicitado |

---

## Cambios

### 1. `microtv-crm-frontend/src/app/core/models/dashboard.model.ts`

Agregar `route?: string` a la interfaz `DashboardStat`:

```ts
export interface DashboardStat {
  label: string;
  value: string;
  sublabel: string;
  variant: DashboardStatVariant;
  route?: string;
}
```

---

### 2. `microtv-crm-frontend/src/app/core/services/dashboard.service.ts`

En `mapKpi()`, leer `kpi.key` y mapear a `route`:

```ts
private readonly KPI_ROUTES: Record<string, string> = {
  open_tickets: '/tickets',
  pending_external: '/tasks?status=PENDING_APPROVAL',
  closed_this_month: '/tasks/history',
};

private mapKpi(kpi: DashboardSummaryApiResponse['kpis'][number]): DashboardStat {
  return {
    label: kpi.label,
    value: String(kpi.value),
    sublabel: kpi.secondary,
    variant: kpi.variant,
    route: this.KPI_ROUTES[kpi.key],
  };
}
```

---

### 3. `microtv-crm-frontend/src/app/features/dashboard/components/stats-cards/stats-cards.component.ts`

- Inyectar `Router`.
- Agregar método `onCardClick(stat: DashboardStat)` que llama `router.navigateByUrl(stat.route)` solo si `stat.route` está definido.

```ts
import { Component, inject, input } from '@angular/core';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { DashboardStat } from '../../../../core/models/dashboard.model';

@Component({
  selector: 'app-stats-cards',
  standalone: true,
  imports: [MatCardModule],
  templateUrl: './stats-cards.component.html',
  styleUrl: './stats-cards.component.scss'
})
export class StatsCardsComponent {
  private readonly router = inject(Router);
  readonly stats = input.required<DashboardStat[]>();

  onCardClick(stat: DashboardStat): void {
    if (stat.route) {
      this.router.navigateByUrl(stat.route);
    }
  }
}
```

---

### 4. `microtv-crm-frontend/src/app/features/dashboard/components/stats-cards/stats-cards.component.html`

Agregar `(click)` y clase condicional `--clickable`:

```html
<section class="stats-cards">
  @for (stat of stats(); track stat.label) {
    <mat-card
      class="stats-cards__card"
      [class]="'stats-cards__card stats-cards__card--' + stat.variant + (stat.route ? ' stats-cards__card--clickable' : '')"
      (click)="onCardClick(stat)"
    >
      <mat-card-content>
        <p class="stats-cards__label">{{ stat.label }}</p>
        <p class="stats-cards__value">{{ stat.value }}</p>
        <p class="stats-cards__sublabel">{{ stat.sublabel }}</p>
      </mat-card-content>
    </mat-card>
  }
</section>
```

---

### 5. `microtv-crm-frontend/src/app/features/dashboard/components/stats-cards/stats-cards.component.scss`

Agregar estilos para cards clicables:

```scss
.stats-cards__card--clickable {
  cursor: pointer;
  transition: box-shadow 0.15s ease, transform 0.1s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
    transform: translateY(-2px);
  }

  &:active {
    transform: translateY(0);
  }
}
```

---

### 6. `microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.ts`

En el `constructor()`, después de la lectura de `queryParams['taskId']`, leer `queryParams['status']` y pre-setear el filtro del tab "assigned":

```ts
const presetStatus = queryParams['status'];
if (typeof presetStatus === 'string' && presetStatus.trim()) {
  this.listUiState.update((state) => ({
    ...state,
    assigned: { ...state.assigned, status: presetStatus.trim() }
  }));
}
```

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `microtv-crm-frontend/src/app/core/models/dashboard.model.ts` | Agregar `route?: string` a `DashboardStat` |
| `microtv-crm-frontend/src/app/core/services/dashboard.service.ts` | `mapKpi()` mapea `kpi.key` a `route` |
| `stats-cards.component.ts` | Inyectar `Router`, agregar `onCardClick()` |
| `stats-cards.component.html` | Agregar `(click)` y clase `--clickable` |
| `stats-cards.component.scss` | Agregar estilos hover/cursor para `--clickable` |
| `tasks-page.component.ts` | Leer `?status` queryParam en constructor |

## Sin cambios de backend

El campo `key` ya es emitido por el backend en `DashboardKpiResponse`. No se requiere ninguna modificación del backend.

## Notas

- La ruta `/tasks/history` tiene guard `adminOrExecutive`. Si un usuario sin ese rol hace click en "Cerradas", el guard lo redirige — comportamiento correcto por diseño.
- "Tareas en Progreso" queda sin navegación intencionalmente (no solicitado).
- La pre-selección de status vía `?status=PENDING_APPROVAL` funciona sobre el tab 0 (assigned to me) que es el default al cargar `/tasks`.
