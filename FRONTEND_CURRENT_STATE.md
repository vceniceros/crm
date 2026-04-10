# Frontend Current State - MicroTV CRM

> **Última actualización:** Abril 2026  
> **Objetivo de este documento:** Proveer contexto fiel y preciso del estado actual del frontend Angular para compartir con otros LLMs y desarrolladores.

---

## 1. Overview

### 1.1. Objetivo actual del frontend

El frontend actual es un **prototipo funcional mock** de un sistema CRM interno para gestión de tickets, tareas, depósito y clientes. Permite simular flujos de trabajo operativos completos sin backend real, utilizando datos JSON mockeados y servicios en memoria.

### 1.2. Estado general del proyecto

- **Estado:** Funcionando como SPA con SSR
- **Alcance:** Módulos principales implementados con datos mock
- **Persistencia:** Parcial (solo task-progress y ticket-execution en localStorage)
- **Backend:** No existe. Todo es mock.
- **Autenticación:** Mock (sin JWT, sin guards, sin seguridad real)
- **Build:** Configurado y funcional (`npm run build`)

### 1.3. Alcance funcional implementado hoy

**Implementado:**
- Dashboard con estadísticas y actividad reciente
- Listado y creación de tickets
- Ejecución de tickets con resolución, adjuntos, pedidos de inventario y despacho
- Listado y creación de tareas
- Ejecución de tareas con checklist, comentarios y adjuntos
- Gestión de depósito (productos, categorías, stock)
- Gestión de clientes con ubicación geográfica
- Plantillas de tareas (task templates) con subtareas y materiales
- Sistema de usuario activo mock con cambio de usuario
- Control de acceso básico por roles (admin, deposito, tecnico)
- Sidebar con navegación filtrada por rol
- Mapas interactivos con Leaflet

**Mock/No real:**
- Autenticación
- Backend/API
- Persistencia de base de datos

**No implementado:**
- Instalaciones (solo aparece en sidebar)
- Facturación (solo aparece en sidebar)
- Reportes (solo aparece en sidebar)
- Configuración (solo aparece en sidebar)

---

## 2. Tech Stack

### 2.1. Dependencias principales

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Angular** | 21.2.0 | Framework principal (standalone components) |
| **Angular Material** | 21.2.5 | UI components (dialogs, cards, sidenav, etc.) |
| **Angular CDK** | 21.2.5 | Layout utilities (BreakpointObserver) |
| **RxJS** | 7.8.0 | Programación reactiva (BehaviorSubject, observables) |
| **Leaflet** | 1.9.4 | Mapas interactivos (visualización y picker de ubicación) |
| **Tailwind CSS** | 4.1.12 | Utilities CSS |
| **TypeScript** | 5.9.2 | Lenguaje |
| **@angular/ssr** | 21.2.6 | Server-Side Rendering |
| **Express** | 5.1.0 | Servidor SSR |

### 2.2. Herramientas de desarrollo

- **Angular CLI** 21.2.6
- **Prettier** 3.8.1
- **jsdom** 28.0.0

### 2.3. Patrones relevantes

- **Standalone components** (no NgModules)
- **Signals** en algunos componentes UI
- **BehaviorSubject** para state reactivo en servicios
- **Dependency injection** con `inject()` function
- **RxJS shareReplay** para cacheo de streams
- **Programación declarativa** (streams reactivos)

---

## 3. Arquitectura general

### 3.1. Organización del proyecto

```
src/app/
├── core/                    # Modelos, servicios mock, tokens
│   ├── models/              # Interfaces y tipos (31 archivos .model.ts)
│   ├── services/            # Servicios mock (13 servicios)
│   └── tokens/              # Injection tokens (si existen)
├── features/                # Módulos funcionales por dominio
│   ├── dashboard/
│   ├── tickets/
│   ├── tasks/
│   ├── inventory/
│   ├── clients/
│   └── task-templates/
├── layout/                  # Shell, sidebar, topbar
│   └── components/
│       ├── app-shell/
│       ├── sidebar/
│       ├── sidebar-user-switcher/
│       └── topbar/
└── shared/                  # Componentes y servicios compartidos
    ├── services/            # LocationLinkService, LocationPickerService
    └── ui/                  # Componentes reutilizables (6 componentes)

src/mocks/                   # JSON mock data (17 archivos)
src/environments/            # Vacío (no hay configuración de entornos)
```

### 3.2. Core services (todos mock)

| Servicio | Responsabilidad |
|----------|-----------------|
| `MockUserContextService` | Usuario activo, lista de usuarios mock |
| `MockAccessControlService` | Filtro de navegación y datos por rol |
| `MockLayoutDataService` | Datos de sidebar, topbar, dashboard |
| `MockTasksService` | Listado de tareas |
| `MockTaskExecutionService` | Ejecución de tareas (checklist, adjuntos, comentarios) |
| `MockTaskProgressStorageService` | Persistencia localStorage del progreso de tareas |
| `MockTicketsService` | Listado de tickets, categorías, prioridades |
| `MockTicketExecutionService` | Ejecución de tickets (resolución, adjuntos, inventario, despacho) |
| `MockTicketExecutionStorageService` | Persistencia localStorage del estado de tickets |
| `MockInventoryService` | Productos, categorías, stock (BehaviorSubject en memoria) |
| `MockClientsService` | Clientes (BehaviorSubject en memoria) |
| `MockTaskTemplateService` | Templates de tareas con subtareas y materiales |
| `MockTaskCreationService` | Datos para formulario de creación de tareas |

### 3.3. Estrategia actual de mocks

**Origen de datos:**
1. Archivos JSON en `src/mocks/` importados directamente en servicios TypeScript
2. No se hacen llamadas HTTP ni fetch (requisito SSR)
3. Datos transformados y servidos vía observables

**State management:**
1. BehaviorSubject para datos mutables (inventory, clients)
2. `of()` + `shareReplay()` para datos inmutables
3. localStorage para persistencia parcial (tasks progress, ticket execution)
4. Todo lo demás vive en memoria (se pierde al refrescar)

**Reactividad:**
1. Servicios exponen observables (`clients$`, `tasks$`, etc.)
2. Componentes consumen con `AsyncPipe` o `toSignal()`
3. Cambios de usuario activo reactualizan datos filtrados

---

## 4. Estructura de carpetas

### 4.1. Core

- **core/models/**: 31 interfaces TypeScript que definen contratos de datos (task, ticket, client, inventory, user, execution, etc.)
- **core/services/**: 13 servicios mock que proveen datos y lógica de negocio
- **core/tokens/**: Tokens de inyección (si los hay)

### 4.2. Features

Cada feature contiene:
- `components/`: Componentes standalone organizados en subcarpetas
- Archivos `.types.ts` cuando hay tipos específicos de formularios

**Features existentes:**
- `dashboard`: página principal, timeline, stats cards
- `tickets`: página listado, creación, ejecución
- `tasks`: página listado, creación, ejecución
- `inventory`: página depósito, tabla de productos
- `clients`: página listado, creación, card de cliente, diálogo de ubicación
- `task-templates`: creación de templates (no tiene página propia, se integra en tasks)

### 4.3. Layout

- `app-shell`: contenedor con sidebar y topbar (MatSidenav)
- `sidebar`: navegación lateral con filtrado por rol
- `sidebar-user-switcher`: dropdown para cambiar usuario activo mock
- `topbar`: barra superior con título dinámico

### 4.4. Shared

**UI Components (6 componentes):**
- `location-map`: Visualización de ubicación con Leaflet
- `location-picker-dialog`: Diálogo para seleccionar ubicación en mapa
- `page-title`: Título de página estandarizado
- `priority-indicator`: Badge de prioridad
- `status-badge`: Badge de estado
- `user-avatar`: Avatar circular con iniciales

**Services:**
- `LocationLinkService`: Genera URLs de Google Maps, abre ubicaciones
- `LocationPickerService`: Abre diálogo de selección de ubicación

### 4.5. Mocks

17 archivos JSON:
- `clients-data.json`
- `inventory-categories-data.json`
- `inventory-items-data.json`
- `inventory-products-data.json`
- `layout-data.json`
- `materials-data.json`
- `stock-devices-data.json`
- `task-creation-data.json`
- `task-execution-data.json`
- `task-progress-data.json`
- `task-templates-data.json`
- `tasks-data.json`
- `ticket-categories-data.json`
- `ticket-execution-data.json`
- `ticket-execution-state-data.json`
- `tickets-data.json`
- `users-data.json`

---

## 5. Estado funcional por módulo

### 5.1. Dashboard

**Ruta:** `/`

**Componentes:**
- `DashboardPageComponent` (página principal)
- `StatsCardsComponent` (4 tarjetas de estadísticas)
- `RecentTicketsTableComponent` (tabla de tickets recientes)
- `RecentActivityTimelineComponent` (timeline de actividad)

**Datos:**
- Provienen de `MockLayoutDataService.dashboard$`
- Source: `layout-data.json`
- Todo estático, no se actualiza con cambios en otros módulos

**Funcionalidad:**
- Visualización read-only
- No hay acciones disponibles
- No depende del rol (todos lo ven igual)

**Limitaciones:**
- Datos hardcoded, no reflejan estado real de tickets/tareas
- No hay gráficos ni drill-down

---

### 5.2. Tareas (Tasks)

**Ruta:** `/tasks`

**Componentes principales:**
- `TasksPageComponent`: Listado de tareas
- `TasksTableComponent`: Tabla con tareas
- `CreateTaskDialogComponent`: Diálogo para crear tarea

**Datos:**
- `MockTasksService.tasksPage$`
- Source: `tasks-data.json` + `MockTaskExecutionService.taskSummaries$`
- **Filtrado reactivo por usuario activo:**
  - Admin ve todas las tareas
  - Técnico/depósito ven solo las asignadas a ellos

**Acciones:**
- Crear nueva tarea
- Click en tarea → navega a `/tasks/:taskId`
- Creación desde template (botón visible, funcionalidad limitada)

**Estado de creación:**
- Diálogo implementado
- Formulario completo (título, cliente, template, técnico asignado, ubicación)
- Al confirmar: solo log en consola (no persiste)

**Limitaciones:**
- Creación no persiste (no hay backend)
- Templates están listados pero crear tarea desde template no integra subtareas automáticamente
- No se pueden editar tareas existentes
- No se pueden eliminar tareas

---

### 5.3. Ejecución de tareas (Task Execution)

**Ruta:** `/tasks/:taskId`

**Componentes principales:**
- `TaskExecutionPageComponent`: Página de ejecución
- `TaskChecklistTreeComponent`: Árbol de subtareas con checkboxes
- `TaskCommentSectionComponent`: Editor de comentario
- `TaskAttachmentsSectionComponent`: Carga y gestión de adjuntos

**Funcionalidad implementada:**
1. **Checklist de subtareas:**
   - Árbol jerárquico con checkboxes
   - Toggle individual de subtareas
   - Dependencias: no se puede marcar padre si hijos incompletos
   - Estado persiste en localStorage

2. **Comentarios:**
   - Campo de texto para notas del técnico
   - Se guarda en localStorage al escribir
   - Visible solo para usuario asignado

3. **Adjuntos:**
   - Carga de archivos (File input)
   - Preview de imágenes con Object URLs
   - Eliminar adjuntos
   - Persisten en localStorage (como metadata, no el archivo real)

4. **Finalización:**
   - Botón "Finalizar tarea"
   - Valida que todas las subtareas obligatorias estén completas
   - Marca tarea como finalizada (persiste en localStorage)
   - Una vez finalizada, no se puede editar más

**Datos:**
- Definition: `task-execution-data.json` (subtareas jerárquicas, materiales)
- Progress: `task-progress-data.json` (estado inicial)
- Persistencia: `MockTaskProgressStorageService` → localStorage key `microtv-crm.task-progress`

**Control de acceso:**
- Usuario ve solo tareas donde esté asignado (o si es admin)
- Si no tiene acceso, componente recibe `null` y no renderiza (no hay guard)

**Limitaciones:**
- Adjuntos no se suben a servidor, solo simulación con Object URLs
- localStorage puede llenarse si se adjuntan muchos archivos
- No hay sincronización con backend
- Finalizar no notifica a nadie ni actualiza métricas del dashboard

---

### 5.4. Tickets

**Ruta:** `/tickets`

**Componentes:**
- `TicketsPageComponent`: Listado
- `TicketsTableComponent`: Tabla
- `CreateTicketDialogComponent`: Creación

**Datos:**
- `MockTicketsService.ticketsPage$`
- Source: `tickets-data.json` + `MockTicketExecutionService.ticketSummaries$`
- **Filtrado reactivo:**
  - Admin ve todos
  - Técnico ve solo donde sea técnico asignado
  - Depósito ve solo donde sea depósito asignado

**Creación de ticket:**
- Formulario completo:
  - Título
  - Descripción
  - Cliente (select)
  - Categoría (select de `ticket-categories-data.json`)
  - Prioridad (Baja/Media/Alta/Crítica)
  - Dispositivo afectado (select de `stock-devices-data.json`)
  - Técnico asignado (select de usuarios rol tecnico)
  - Depósito asignado (select de usuarios rol deposito)
- Al confirmar: solo log en consola

**Limitaciones:**
- Creación no persiste
- No se pueden editar ni eliminar tickets

---

### 5.5. Ejecución de tickets (Ticket Execution)

**Ruta:** `/tickets/:ticketId`

**Componentes principales:**
- `TicketExecutionPageComponent`
- `TicketDescriptionSectionComponent`: Info del ticket
- `TicketResolutionSectionComponent`: Nota de resolución del técnico
- `TicketAttachmentsSectionComponent`: Adjuntos
- `TicketInventoryRequestSectionComponent`: Pedidos de material
- `TicketDispatchSectionComponent`: Despacho de materiales

**Funcionalidad implementada:**

**1. Descripción del ticket:**
- Read-only: título, categoría, prioridad, descripción, dispositivo afectado, cliente
- Técnico asignado, depósito asignado

**2. Resolución (solo técnico asignado):**
- Campo de texto para nota de resolución
- Persiste en localStorage
- Solo editable por técnico asignado

**3. Adjuntos (solo técnico asignado):**
- Carga de archivos
- Preview de imágenes
- Eliminar adjuntos
- Mock (Object URLs, persisten metadata en localStorage)

**4. Pedidos de inventario (solo técnico asignado puede crear):**
- Técnico crea solicitud con ítems:
  - Selecciona producto de `inventory-items-data.json`
  - Indica cantidad
  - Agrega múltiples ítems
- Pedido queda pendiente
- Depósito asignado ve pedidos y puede:
  - Aprobar
  - Rechazar (con comentario)
- Estado: pending → approved / rejected
- Persiste en localStorage

**5. Despacho (solo depósito asignado):**
- Depósito registra materiales enviados al técnico
- Formulario:
  - Producto (select)
  - Cantidad
  - Notas opcionales
- Se agregan ítems despachados
- Persiste en localStorage

**Datos:**
- Definition: `ticket-execution-data.json`
- State: `ticket-execution-state-data.json`
- Persistencia: `MockTicketExecutionStorageService` → localStorage key `microtv-crm.ticket-execution`

**Control de acceso granular:**
| Sección | Admin | Técnico asignado | Depósito asignado | Otros |
|---------|-------|------------------|-------------------|-------|
| Ver ticket | ✅ | ✅ | ✅ | ❌ |
| Editar resolución | ❌ | ✅ | ❌ | ❌ |
| Adjuntos | ✅ readonly | ✅ | ❌ | ❌ |
| Crear pedido inventario | ❌ | ✅ | ❌ | ❌ |
| Aprobar/rechazar pedido | ✅ | ❌ | ✅ | ❌ |
| Despachar materiales | ✅ | ❌ | ✅ | ❌ |

**Limitaciones:**
- Sin backend, pedidos y despachos no afectan stock real de depósito
- Sin notificaciones cuando se aprueba/rechaza pedido
- Sin historial de cambios

---

### 5.6. Depósito (Inventory)

**Ruta:** `/inventory`

**Componentes:**
- `InventoryPageComponent`
- `InventoryTableComponent`: Tabla de productos
- `CreateProductDialogComponent`: Creación de producto

**Datos:**
- `MockInventoryService.inventoryPage$`
- Source inicial: `inventory-products-data.json`, `inventory-categories-data.json`
- **BehaviorSubject en memoria** (cambios persisten solo en sesión)

**Funcionalidad:**
1. **Listado de productos:**
   - Columnas: Imagen, ID, Nombre, Categoría, Stock, Acciones
   - Todos los productos visibles

2. **Crear producto:**
   - Nombre
   - Categoría (select)
   - URL de imagen (opcional)
   - Stock inicial
   - Al confirmar: se agrega al BehaviorSubject (visible de inmediato)
   - **Persiste solo en memoria** (refresh los elimina)

3. **Ajustar stock:**
   - Botones +/- en cada fila
   - Incrementa/decrementa de a 1
   - No puede bajar de 0
   - Cambios en memoria

**Control de acceso:**
- Solo admin y deposito ven este módulo
- Técnico no puede acceder (sidebar no muestra el link)

**Limitaciones:**
- Productos creados se pierden al refrescar
- Stock no se sincroniza con despachos de tickets
- No hay stock mínimo, alertas ni reposición
- No se pueden eliminar productos
- No se pueden editar detalles de producto existente

---

### 5.7. Clientes

**Ruta:** `/clients`

**Componentes:**
- `ClientsPageComponent`
- `ClientsGridComponent`: Grid de tarjetas de clientes
- `ClientCardComponent`: Tarjeta individual
- `CreateClientDialogComponent`: Creación con ubicación
- `ClientLocationDialogComponent`: Visualización de ubicación en mapa

**Datos:**
- `MockClientsService.clientsPage$`
- Source inicial: `clients-data.json`
- **BehaviorSubject en memoria**

**Funcionalidad:**
1. **Listado:**
   - Grid responsive de tarjetas
   - Muestra: Razón social, CUIT, Email, Teléfono
   - Icono de ubicación si tiene coordenadas
   - Click en ubicación: abre diálogo con mapa Leaflet

2. **Crear cliente (solo admin):**
   - Razón social
   - CUIT
   - Email
   - Teléfono
   - Ubicación (opcional):
     - Botón "Marcar en mapa"
     - Abre diálogo con Leaflet picker interactivo
     - Click en mapa guarda coordenadas
     - Muestra coordenadas seleccionadas
     - Botón "Abrir en Google Maps" (external link)
   - Al confirmar: se agrega al BehaviorSubject

3. **Visualización de ubicación:**
   - Diálogo con mapa Leaflet
   - Marker en ubicación del cliente
   - Botón para abrir en Google Maps (external)

**Integración de mapas:**
- Librería: **Leaflet 1.9.4**
- Tiles: OpenStreetMap
- No requiere API key
- Lazy loading: `await import('leaflet')` en componentes
- SSR-safe: verifica `isPlatformBrowser` antes de inicializar

**Control de acceso:**
- Todos los roles ven clientes
- Solo admin puede crear clientes

**Limitaciones:**
- Clientes creados se pierden al refrescar
- No hay edición de clientes
- No hay eliminación
- No hay búsqueda/filtro
- Ubicación es opcional, no validada

---

### 5.8. Templates (Task Templates)

**Ubicación:** Integrado en crear tarea, no tiene página propia

**Componentes:**
- `CreateTemplateDialogComponent`: Crear template
- `TemplateSubtasksEditorComponent`: Editor de árbol de subtareas
- `TemplateMaterialsEditorComponent`: Editor de materiales requeridos

**Datos:**
- `MockTaskTemplateService.templates$`
- Source: `task-templates-data.json`
- Materials: `materials-data.json`

**Funcionalidad:**
1. **Crear template:**
   - Título
   - Descripción
   - Subtareas (árbol jerárquico con botones add/remove)
   - Materiales requeridos (producto, cantidad, unidad)
   - Al confirmar: solo log en consola

2. **Templates existentes:**
   - 2 templates predefinidos en JSON:
     - "Instalación estándar de monitoreo"
     - "Mantenimiento preventivo técnico"
   - Se listan en select de crear tarea
   - **No hay integración automática**: seleccionar template no pre-llena subtareas

**Limitaciones:**
- Crear template no persiste
- No hay listado de templates
- No hay edición de templates existentes
- No hay preview de template
- Integración con creación de tareas incompleta

---

### 5.9. Usuarios mock / Cambio de usuario activo

**Ubicación:** Footer del sidebar

**Componente:**
- `SidebarUserSwitcherComponent`: Dropdown con mat-menu

**Usuarios mock actuales:**

| ID | Nombre | Rol | Initials |
|----|--------|-----|----------|
| 1 | Sergio M. | admin | SM |
| 2 | Marcelo D. | deposito | MD |
| 3 | Luis F. | tecnico | LF |

**Funcionalidad:**
- Click en avatar abre menú con lista de usuarios
- Seleccionar usuario cambia contexto global
- **Reactivo:** sidebar, tickets, tareas se actualizan automáticamente
- Sin contraseña, sin login, sin logout

**Persistencia:**
- No persiste en localStorage
- Refresh vuelve al usuario por defecto (Sergio M.)

**Limitaciones:**
- No hay autenticación real
- No hay guards de ruta
- Cualquiera puede cambiar de usuario
- No hay audit trail ni logs
- Cambio de usuario no requiere confirmación

---

### 5.10. Control de acceso mock por rol

**Servicio:** `MockAccessControlService`

**Reglas de módulos:**

| Módulo | admin | deposito | tecnico |
|--------|-------|----------|---------|
| dashboard | ✅ | ✅ | ✅ |
| tickets | ✅ | ✅ | ✅ |
| tasks | ✅ | ✅ | ✅ |
| inventory | ✅ | ✅ | ❌ |
| installations | ✅ | ❌ | ❌ |
| clients | ✅ | ✅ | ✅ |
| billing | ✅ | ❌ | ❌ |
| reports | ✅ | ❌ | ❌ |
| settings | ✅ | ❌ | ❌ |

**Implementación:**
- `MockLayoutDataService` filtra navigation items del sidebar según rol
- Items sin acceso no aparecen en sidebar
- **NO hay guards de ruta**: se puede navegar directamente a URL
- Componentes verifican acceso y muestran `null` si no autorizado

**Filtrado de datos:**
1. **Tasks:**
   - Admin ve todas
   - Técnico/depósito ven solo donde `assignedToUserId === activeUser.id`

2. **Tickets:**
   - Admin ve todos
   - Técnico ve donde `technicianAssigneeId === activeUser.id`
   - Depósito ve donde `depositAssigneeId === activeUser.id`

3. **Clients:**
   - Todos ven todos
   - Solo admin puede crear

4. **Inventory:**
   - No filtrado
   - Solo admin/deposito acceden

**Métodos de control:**
- `canViewModule(moduleKey)`
- `canViewAllTickets()`
- `canCreateClients()`
- `canUserViewTicketExecution(...)`
- `canUserEditTicketResolution(...)`
- `canUserManageTicketAttachments(...)`
- etc.

**Limitaciones:**
- Sin guards de ruta (URLs directas no protegidas)
- Sin guards de HTTP (no existen HTTP calls)
- Lógica client-side fácilmente bypasseable
- **NO es seguridad real**, solo UX

---

### 5.11. Mapas / Ubicaciones

**Integración:** Solo en módulo de Clientes

**Librería:** Leaflet 1.9.4

**Componentes:**
1. `LocationMapComponent` (visualización read-only)
2. `LocationPickerDialogComponent` (selector interactivo)

**Funcionalidad:**

**Visualización:**
- Mapa con marker circular rojo
- Tiles de OpenStreetMap (gratuito, sin API key)
- Popup con título
- Zoom configurable

**Selección (picker):**
- Mapa interactivo centrado en Buenos Aires por defecto
- Click en mapa coloca marker
- Muestra coordenadas seleccionadas
- Botón "Abrir en Google Maps" genera URL y abre en nueva pestaña
- Confirmar devuelve `{ location: AppLocation, googleMapsUrl: string }`

**Modelo:**
```typescript
interface AppLocation {
  latitude: number;
  longitude: number;
  addressLabel?: string;
}
```

**SSR Safety:**
- Leaflet se importa dinámicamente: `await import('leaflet')`
- Verifica `isPlatformBrowser(PLATFORM_ID)` antes de inicializar
- No rompe SSR

**Servicios de soporte:**
- `LocationLinkService`:
  - Genera URLs de Google Maps
  - Abre ubicación en Google Maps (window.open)
  - Valida coordenadas

**URL de Google Maps:**
- Formato: `https://www.google.com/maps/search/?api=1&query=lat,lng`
- No requiere API key para links externos

**Limitaciones:**
- Solo en clientes (no en tickets ni tareas aún)
- No hay geocoding (no convierte direcciones a coordenadas)
- No hay reverse geocoding (coordenadas a dirección)
- `addressLabel` es campo manual, no automático
- No hay validación de coordenadas válidas más allá de tipo numérico

---

## 6. Modelos y contratos principales

Total de modelos: **31 archivos .model.ts** en `core/models/`

### 6.1. Usuarios y permisos

- `user-profile.model.ts`: `MockUserProfile`, `MockUsersData`
- `user-role.model.ts`: `MockUserRole = 'admin' | 'deposito' | 'tecnico'`
- `permission.model.ts`: `MockModuleKey`, `MockModuleAccessRule`

### 6.2. Navegación y layout

- `navigation.model.ts`: `NavigationSection`, `NavigationItem`
- `layout.model.ts`: Si existe (no confirmado en este relevamiento)
- `dashboard.model.ts`: Stats, tickets recientes, activity timeline

### 6.3. Tareas (Tasks)

- `task.model.ts`: `TaskListItem`, `TasksPageData`, `TasksTableData`
- `task-execution.model.ts`: `TaskExecutionDefinition`, `TaskExecutionItem`, `TaskExecutionSubtaskView`
- `task-progress.model.ts`: `TaskProgressState`, `TaskProgressData`
- `task-attachment.model.ts`: `TaskAttachment`, `TaskAttachmentKind`
- `create-task.model.ts`: `CreateTaskFormValue`

### 6.4. Templates de tareas

- `task-template.model.ts`: `TaskTemplateRecord`, `TaskTemplateDraft`
- `task-template-option.model.ts`: `TaskTemplateOption`
- `template-subtask.model.ts`: `TemplateSubtask`
- `material.model.ts`: `MaterialOption`

### 6.5. Tickets

- `ticket.model.ts`: `TicketListItem`, `TicketsPageData`, `TicketPriorityOption`
- `ticket-execution.model.ts`: `TicketExecutionDefinition`, `TicketExecutionItem`, `TicketExecutionState`, `TicketExecutionPermissions`
- `ticket-category.model.ts`: `TicketCategory`
- `ticket-attachment.model.ts`: `TicketAttachment`, `TicketAttachmentKind`
- `ticket-dispatch.model.ts`: `TicketDispatchItem`
- `ticket-inventory-request.model.ts`: `TicketInventoryRequest`, `TicketInventoryRequestItem`, `TicketInventoryRequestStatus`
- `ticket-resolution-note.model.ts`: Si existe
- `create-ticket.model.ts`: `CreateTicketFormValue`

### 6.6. Depósito / Inventario

- `inventory-product.model.ts`: `InventoryProduct`, `InventoryPageData`, `InventoryTableData`
- `inventory-category.model.ts`: `InventoryCategory`
- `inventory-item.model.ts`: `InventoryItemOption` (para pedidos de tickets)
- `stock-device.model.ts`: `StockDeviceOption` (dispositivos afectados en tickets)
- `create-product.model.ts`: `CreateInventoryProductFormValue`

### 6.7. Clientes

- `client.model.ts`: `ClientItem`, `ClientsPageData`, `ClientOption`
- `create-client.model.ts`: `CreateClientFormValue`
- `location.model.ts`: `AppLocation`, `LocationPickerDialogData`, `LocationSelectionResult`

### 6.8. Relaciones entre modelos

**Tasks → Task Execution:**
- `TaskListItem` (summary) ← generado desde `TaskExecutionDefinition` + `TaskProgressState`
- Progreso separado de definición

**Tickets → Ticket Execution:**
- `TicketListItem` (summary) ← generado desde `TicketExecutionDefinition` + `TicketExecutionState`
- Execution state incluye: resolución, adjuntos, inventory requests, dispatch items

**Templates → Tasks:**
- `TaskTemplateRecord` define estructura reutilizable
- Al crear task desde template: aún no integrado automáticamente

**Inventory → Tickets:**
- `InventoryItemOption` usada en `TicketInventoryRequestItem`
- **No hay sincronización real** entre despachos y stock

---

## 7. Flujo de datos actual

### 7.1. Origen de datos

**Todo desde JSON estático:**
- 17 archivos en `src/mocks/`
- Importados directamente: `import data from '../../../mocks/file.json'`
- Tipados con `as MyDataType`

### 7.2. Services mock

**Patrón de servicio típico:**

```typescript
@Injectable({ providedIn: 'root' })
export class MockExampleService {
  private readonly dataSubject = new BehaviorSubject<Item[]>(initialData);
  
  readonly items$ = this.dataSubject.asObservable();
  readonly page$ = this.items$.pipe(
    map(items => ({ pageTitle: '...', items })),
    shareReplay({ bufferSize: 1, refCount: true })
  );
}
```

**Servicios con BehaviorSubject (mutable):**
- `MockInventoryService` (productos)
- `MockClientsService` (clientes)
- `MockTaskExecutionService` (progress via storage service)
- `MockTicketExecutionService` (state via storage service)
- `MockUserContextService` (activeUserId)

**Servicios read-only (inmutable):**
- `MockLayoutDataService`
- `MockTaskTemplateService`
- `MockTaskCreationService`

### 7.3. Reactividad

**Observable chains:**
1. Servicio publica `items$`
2. Componente suscribe con `AsyncPipe` o `toSignal()`
3. Cambios en BehaviorSubject emiten nuevo valor
4. Template se actualiza automáticamente

**Filtrado por usuario:**
```typescript
readonly filteredTickets$ = combineLatest([
  this.ticketsService.tickets$,
  this.userContextService.activeUser$
]).pipe(
  map(([tickets, user]) => this.filterForUser(tickets, user))
);
```

**Cascada de observables:**
- `activeUserId$` cambia
- `activeUser$` emite nuevo user
- `filteredTickets$` recalcula
- UI se actualiza

### 7.4. Signals vs Observables

**Signals (Angular 21 feature):**
- Usado en algunos componentes UI:
  - `LocationMapComponent`
  - `LocationPickerDialogComponent`
  - `CreateClientDialogComponent`
- Para state local del componente
- Computed signals para lógica derivada

**Observables (RxJS):**
- Dominante en servicios
- Para data streams
- Integración con AsyncPipe

---

## 8. Persistencia actual

### 8.1. localStorage (persistencia entre refreshes)

**2 storages implementados:**

**1. Task Progress:**
- Key: `microtv-crm.task-progress`
- Servicio: `MockTaskProgressStorageService`
- Inicializa con: `task-progress-data.json`
- Persiste:
  ```typescript
  {
    taskId: string,
    completedSubtaskIds: string[],
    comment: string,
    attachments: TaskAttachment[],  // metadata, no archivos reales
    finalized: boolean,
    createdAt: string,
    updatedAt: string
  }
  ```
- **SSR-safe:** verifica `isPlatformBrowser` antes de acceder a localStorage

**2. Ticket Execution State:**
- Key: `microtv-crm.ticket-execution`
- Servicio: `MockTicketExecutionStorageService`
- Inicializa con: `ticket-execution-state-data.json`
- Persiste:
  ```typescript
  {
    ticketId: string,
    resolutionComment: string,
    resolutionUpdatedAt: string,
    attachments: TicketAttachment[],
    inventoryRequests: TicketInventoryRequest[],
    dispatchedItems: TicketDispatchItem[],
    updatedAt: string
  }
  ```

**Limitaciones de localStorage:**
- Adjuntos: solo metadata (id, name, size, type, previewUrl)
- `previewUrl` es Object URL (`blob:...`), se pierde al refrescar
- No hay upload real de archivos
- No hay límite de tamaño implementado (puede llenar localStorage)

### 8.2. En memoria (BehaviorSubject, se pierde al refresh)

**Servicios con state en memoria:**
- `MockInventoryService`: productos creados
- `MockClientsService`: clientes creados
- `MockUserContextService`: usuario activo actual

**Consecuencia:**
- Crear producto → visible de inmediato
- Refresh → producto desaparece, vuelve a JSON inicial

### 8.3. Lo que NO persiste

- Tickets creados
- Tareas creadas
- Templates de tareas creadas
- Usuario activo seleccionado
- Sidebar colapsado/expandido
- Productos de inventario creados/modificados
- Clientes creados
- Todo lo que no esté en localStorage

---

## 9. Usuarios, roles y acceso mock

### 9.1. Usuarios mock

**Archivo:** `users-data.json`

```json
{
  "users": [
    { "id": 1, "name": "Sergio M.", "role": "admin", "roleLabel": "Administrador", "initials": "SM" },
    { "id": 2, "name": "Marcelo D.", "role": "deposito", "roleLabel": "Encargado de deposito", "initials": "MD" },
    { "id": 3, "name": "Luis F.", "role": "tecnico", "roleLabel": "Tecnico", "initials": "LF" }
  ]
}
```

**Usuario por defecto:** Sergio M. (admin)

### 9.2. Roles y capacidades

**Admin (Sergio M.):**
- Ve todos los módulos del sidebar
- Ve todos los tickets y tareas
- Puede crear clientes
- Puede aprobar/rechazar pedidos de inventario en tickets
- Puede despachar materiales
- No puede editar resolución de tickets (solo técnico)

**Depósito (Marcelo D.):**
- Ve: dashboard, tickets, tasks, inventory, clients
- No ve: installations, billing, reports, settings
- Ve solo tickets donde sea depósito asignado
- Ve solo tareas donde sea asignado (raro, depósito no suele tener tareas)
- Puede aprobar/rechazar pedidos de inventario
- Puede despachar materiales

**Técnico (Luis F.):**
- Ve: dashboard, tickets, tasks, clients
- No ve: inventory, installations, billing, reports, settings
- Ve solo tickets donde sea técnico asignado
- Ve solo tareas donde sea técnico asignado
- Puede editar resolución de ticket
- Puede agregar adjuntos a ticket
- Puede crear pedidos de inventario
- NO puede aprobar pedidos ni despachar

### 9.3. Aplicación de lógica

**Sidebar filtering:**
```typescript
MockLayoutDataService.filteredNavigation$ = 
  MockAccessControlService.filterNavigationForActiveUser(navigation$)
```
- Items filtrados por `moduleKey` vs rol
- Usuario no ve links sin acceso

**Data filtering:**
```typescript
MockAccessControlService.filterTicketsForActiveUser(tickets$)
```
- Filtra por `technicianAssigneeId` o `depositAssigneeId`

**Component-level permissions:**
```typescript
canEdit$ = this.mockAccessControlService.canUserEditTicketResolution(user, technicianId);
```
- Computed observable que habilita/deshabilita controles

### 9.4. Migración futura a JWT/backend real

**Qué cambiar:**
1. Reemplazar `MockUserContextService` con `AuthService` real
2. Agregar guards de ruta (`CanActivate`)
3. Interceptor HTTP para agregar JWT en headers
4. Login/logout real
5. Persistir token en localStorage (o httpOnly cookie)
6. Validación server-side de permisos
7. Refresh token mechanism

**Qué aprovechar:**
- Abstracciones de `MockAccessControlService` pueden migrar a `PermissionsService`
- Observables de usuario y rol ya están reactivos
- Componentes ya consumen permisos vía observables

**IMPORTANTE:** 
- Hoy **no hay seguridad real**
- Todo es client-side y bypasseable
- No hay autenticación ni autorización backend
- Usuario activo es solo simulación UX

---

## 10. Endpoints e integraciones

### 10.1. Resumen ejecutivo

**NO HAY BACKEND REAL HOY.**

### 10.2. HTTP Clients

**Búsqueda de HttpClient en servicios:**
```bash
grep -r "HttpClient" src/app/core/services/*.ts
# Resultado: 0 matches
```

**NO se usa HttpClient en ningún servicio.**

### 10.3. Estrategia actual

**Datos:**
- JSON estáticos en `src/mocks/`
- Importados directamente con `import`
- Servidos vía observables `of()` + `shareReplay()`

**Persistencia:**
- localStorage para task progress y ticket execution
- BehaviorSubject en memoria para inventory y clients
- Sin comunicación con servidor

**SSR:**
- `@angular/ssr` configurado
- Estado inicial rendereado server-side
- Hydration con `withEventReplay()`
- Mock data importado en TypeScript (no fetch HTTP) para evitar errores SSR

### 10.4. Integraciones externas

**Google Maps:**
- No se usa Google Maps JavaScript API
- Solo URLs de links: `https://www.google.com/maps/search/?api=1&query=lat,lng`
- No requiere API key
- Solo para abrir ubicación en nueva pestaña

**Leaflet:**
- Librería client-side
- Tiles de OpenStreetMap (gratuitos)
- Sin backend propio

**Archivos/Media:**
- Adjuntos simulados con File API
- `URL.createObjectURL()` para preview de imágenes
- No hay upload real
- No hay almacenamiento en servidor

### 10.5. Preparación para backend real

**Estructura preparada:**
- Servicios bien separados (mock*Service)
- Interfaces de datos definidas
- Observables ya implementados

**Migración sugerida:**
1. Crear servicios paralelos (ej. `TasksApiService`)
2. Implementar llamadas HTTP con HttpClient
3. Reemplazar `Mock*Service` por `*ApiService` en providers
4. Mantener mocks para tests

**Endpoints sugeridos (futuro):**
```
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/:id
PATCH  /api/tasks/:id/subtasks/:subtaskId
POST   /api/tasks/:id/attachments
POST   /api/tasks/:id/finalize

GET    /api/tickets
POST   /api/tickets
GET    /api/tickets/:id
PATCH  /api/tickets/:id/resolution
POST   /api/tickets/:id/inventory-requests
PATCH  /api/tickets/:id/inventory-requests/:requestId
POST   /api/tickets/:id/dispatch

GET    /api/inventory/products
POST   /api/inventory/products
PATCH  /api/inventory/products/:id

GET    /api/clients
POST   /api/clients

POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout
```

---

## 11. Decisiones de diseño actuales

### 11.1. Separación Task Template vs Task Execution

**Template:**
- Definición reutilizable de proceso
- Subtareas jerárquicas
- Materiales requeridos
- Inmutable (no se modifica al ejecutar)

**Execution:**
- Instancia de ejecución de una tarea
- Referencia a template (o no)
- Progress state mutable (completedSubtaskIds, comment, attachments)
- Lifecicle: created → in-progress → finalized

**Beneficios:**
- Templates reutilizables sin contaminar con datos de ejecución
- Progreso separado de definición
- Múltiples ejecuciones de mismo template

**Implementación actual:**
- `task-execution-data.json`: definiciones de tareas con subtareas
- `task-progress-data.json`: estado inicial de progress
- `MockTaskProgressStorageService`: persiste progress
- `MockTaskExecutionService`: combina definition + progress

### 11.2. Separación Ticket vs Ticket Execution

**Similar a tasks:**
- `ticket-execution-data.json`: definición (cliente, técnico, descripción)
- `ticket-execution-state-data.json`: estado mutable (resolución, adjuntos, requests, dispatch)
- Storage service para estado
- Servicio combina definition + state

### 11.3. Inventory Requests vs Dispatch

**Inventory Request:**
- Técnico solicita materiales
- Status: pending → approved/rejected
- Aprobado por depósito
- **No afecta stock automáticamente**

**Dispatch:**
- Acción independiente de depósito
- Registra materiales enviados
- **No relacionado directamente con requests** (puede despachar sin request)
- **No descuenta stock de inventory**

**Decisión pendiente:**
- ¿Dispatch debería descontar stock?
- ¿Request aprobado debería generar dispatch automático?
- Hoy ambos son registros independientes

### 11.4. Persistencia selectiva

**localStorage:**
- Solo task progress y ticket execution state
- Lo mínimo para simular continuidad de trabajo

**En memoria:**
- Inventory y clients
- Permite crear/modificar sin backend
- Acepta pérdida al refresh (es prototipo)

**Decisión:**
- No intentar persistir todo en localStorage
- Priorizar realismo de flujo de ejecución
- Aceptar que creación de entidades no persiste

### 11.5. Usuario activo vs Autenticación

**Decisión:**
- Mock user context sin autenticación
- Cambio de usuario sin contraseña
- NO es login real

**Objetivo:**
- Simular multi-usuario para probar filtrado
- Validar lógica de acceso sin backend
- **NO es feature de producción**

**Futuro:**
- Reemplazar por login real
- Guards de autenticación
- Token JWT
- Sesión server-side

### 11.6. SSR y estrategia de mocks

**Decisión:**
- Datos JSON importados en TypeScript (no fetch HTTP)
- Evita problemas de fetch en SSR
- Estado inicial rendereado server-side

**Beneficio:**
- Build de producción funcional
- SSR sin errores
- Lighthouse score optimizado

**Limitación:**
- No simula latencia de network
- No permite hot-reload de datos JSON sin rebuild

---

## 12. Limitaciones actuales

### 12.1. Sin backend

- **No hay servidor real**
- No hay base de datos
- No hay autenticación real
- No hay autorización server-side
- No hay validación server-side
- No hay auditoría de cambios
- No hay transacciones
- No hay rollback

### 12.2. Persistencia limitada

- Solo task progress y ticket execution en localStorage
- Inventory y clients en memoria (se pierden al refresh)
- Tickets y tasks creados no persisten
- Templates creados no persisten
- Adjuntos son mock (Object URLs, no archivos reales)

### 12.3. Seguridad inexistente

- No hay autenticación
- No hay JWT
- No hay CSRF protection
- No hay rate limiting
- No hay validación de input server-side
- Control de acceso client-side es bypasseable
- Cualquiera puede cambiar de usuario
- URLs directas no protegidas por guards

### 12.4. Sincronización de datos

- Despacho de materiales no descuenta stock de inventory
- Pedidos aprobados no quedan registrados en inventory
- Dashboard no refleja estado real de tickets/tareas
- Contadores estáticos (no calculados)

### 12.5. Funcionalidad incompleta

- Templates: crear no persiste, integración con tasks parcial
- Tickets/Tasks: crear no persiste
- Inventory: editar/eliminar productos no implementado
- Clients: editar/eliminar no implementado
- Sin búsqueda/filtros en listados
- Sin paginación
- Sin ordenamiento
- Sin exportación de datos

### 12.6. UX

- Sin notificaciones
- Sin confirmaciones de acciones destructivas
- Sin loading states en la mayoría de acciones
- Sin manejo de errores (todo es éxito)
- Sin validación de formularios exhaustiva
- Sin tooltips/ayuda contextual

### 12.7. Producción

**Bloqueantes para producción:**
- Sin backend
- Sin autenticación
- Sin persistencia real
- Sin seguridad
- Sin manejo de errores
- Sin logging
- Sin monitoreo
- Sin backup
- Sin recuperación ante fallos
- Sin tests unitarios/e2e
- Sin CI/CD configurado

---

## 13. Ready for next step

### 13.1. Estructura sólida

**✅ Listo para evolucionar:**

1. **Arquitectura modular:**
   - Servicios bien separados
   - Features independientes
   - Core compartido
   - Standalone components

2. **Contratos de datos definidos:**
   - 31 modelos TypeScript
   - Interfaces para requests/responses
   - Tipos para formularios

3. **Servicios abstraídos:**
   - Mock services fácilmente reemplazables
   - Interfaces claras
   - Inyección de dependencias

4. **Reactividad:**
   - Observables en servicios
   - AsyncPipe en templates
   - Cascadas reactivas funcionando

5. **Control de acceso:**
   - Lógica de permisos centralizada
   - Filtrado por rol implementado
   - Fácil migrar a guards + backend

### 13.2. Próximos pasos técnicos

**Para JWT real:**
1. Crear `AuthService` con login/logout
2. Interceptor HTTP para agregar token
3. Guards de autenticación (`AuthGuard`)
4. Guards de autorización (`RoleGuard`)
5. Almacenar token en localStorage o httpOnly cookie
6. Refresh token mechanism
7. Logout automático en 401

**Para backend real:**
1. Crear servicios API paralelos:
   - `TasksApiService`
   - `TicketsApiService`
   - `InventoryApiService`
   - `ClientsApiService`
2. Implementar llamadas HTTP con HttpClient
3. Proveer `HttpClient` en app.config.ts
4. Reemplazar mock services en DI
5. Configurar CORS en backend
6. Configurar base URL en environment

**Para endpoints reales:**
1. Diseñar API RESTful
2. Implementar endpoints en backend
3. Agregar validación server-side
4. Agregar manejo de errores
5. Agregar logging
6. Agregar rate limiting
7. Documentar API (Swagger/OpenAPI)

**Para control de acceso real:**
1. Backend valida permisos en cada endpoint
2. JWT contiene roles/permisos
3. Frontend consulta permisos al backend
4. Guards utilizan permisos en token
5. UI se habilita/deshabilita según permisos del token

**Para persistencia real:**
1. Backend con base de datos
2. Upload de archivos a storage (S3, Azure Blob, etc.)
3. Eliminar localStorage de task/ticket
4. Estado en backend + cache client-side
5. Optimistic updates

### 13.3. Componentes preparados

**✅ Estos componentes ya funcionan bien y solo necesitan datos reales:**

- Dashboard (solo cambiar source de datos)
- Listados de tickets/tasks (solo conectar a API)
- Ejecución de tickets/tasks (cambiar storage service por API calls)
- Inventory table (conectar a API)
- Clients grid (conectar a API)
- Location picker (ya funciona, no depende de backend)
- Sidebar (solo actualizar source de navigation)
- User switcher (reemplazar por login real)

**⚠️ Estos necesitan ajustes:**

- Task templates: completar integración con task creation
- Create ticket/task dialogs: conectar a API y manejar errores
- Attachment sections: implementar upload real
- Inventory requests/dispatch: sincronizar con stock

### 13.4. Configuración necesaria

**Environments (crear archivos):**
```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:3000/api'
};

// src/environments/environment.production.ts
export const environment = {
  production: true,
  apiUrl: 'https://api.microtv-crm.com'
};
```

**App config (agregar HttpClient):**
```typescript
// app.config.ts
import { provideHttpClient, withFetch } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    // ... existing providers
    provideHttpClient(withFetch())
  ]
};
```

**Interceptors necesarios:**
- `AuthInterceptor`: agrega JWT a headers
- `ErrorInterceptor`: maneja errores HTTP globalmente
- `LoadingInterceptor`: muestra spinner global (opcional)

---

## 14. Resumen para LLMs

### Estado actual (abril 2026)

Este frontend Angular 21 es un **prototipo funcional mock** sin backend real.

**✅ Implementado:**
- Dashboard, tickets, tareas, depósito, clientes, templates
- Ejecución de tickets y tareas con checklist, adjuntos, comentarios
- Pedidos de inventario y despacho (mock)
- Control de acceso mock por 3 roles (admin, deposito, tecnico)
- Cambio de usuario mock sin autenticación
- Mapas con Leaflet (solo en clientes)
- Persistencia parcial en localStorage (task progress, ticket execution)
- SSR configurado

**❌ No existe:**
- Backend
- API HTTP
- Autenticación JWT
- Guards de autenticación
- Persistencia real
- Sincronización con base de datos

**🗂️ Datos:**
- 17 archivos JSON en `src/mocks/`
- Importados en servicios TypeScript
- Servidos vía observables
- localStorage para progreso de ejecución

**👤 Usuarios mock:**
- Sergio M. (admin)
- Marcelo D. (deposito)
- Luis F. (tecnico)

**🔐 Control de acceso:**
- Client-side only (no seguro)
- Filtrado de sidebar por rol
- Filtrado de tickets/tareas por asignación
- Solo admin crea clientes
- Técnico edita resolución de tickets
- Depósito aprueba pedidos y despacha

**📦 Persistencia:**
- localStorage: task progress, ticket execution state
- Memoria: inventory productos, clients
- Todo lo demás se pierde al refresh

**🚫 Seguridad:**
- **NO HAY SEGURIDAD REAL**
- No usar en producción sin backend + JWT
- Todo es simulación UX

**✨ Preparado para:**
- Conectar a backend real
- Agregar JWT y AuthGuard
- Reemplazar mock services por API services
- Agregar upload real de archivos
- Migrar localStorage a backend

**⚠️ Decisiones importantes que respetar:**

1. **Separación template/execution:** No mezclar definición con progreso
2. **Servicios mock independientes:** Facilita reemplazo por API
3. **Observables reactivos:** Mantener programación reactiva
4. **Control de acceso centralizado:** Un servicio para todas las reglas
5. **SSR-safe:** No romper server-side rendering
6. **Standalone components:** No crear NgModules

---

**Fin del documento**

---

## Archivos relevados principales

Durante este relevamiento se analizaron:

### Configuración
- `package.json`
- `angular.json`
- `tsconfig.json`
- `app.config.ts`
- `app.routes.ts`

### Core (13 servicios)
- `MockUserContextService`
- `MockAccessControlService`
- `MockLayoutDataService`
- `MockTasksService`
- `MockTaskExecutionService`
- `MockTaskProgressStorageService`
- `MockTaskCreationService`
- `MockTaskTemplateService`
- `MockTicketsService`
- `MockTicketExecutionService`
- `MockTicketExecutionStorageService`
- `MockInventoryService`
- `MockClientsService`

### Models (31 archivos)
- Todo el directorio `core/models/`

### Components principales
- `AppShellComponent`
- `SidebarComponent`
- `SidebarUserSwitcherComponent`
- `DashboardPageComponent`
- `TasksPageComponent`
- `TaskExecutionPageComponent`
- `TicketsPageComponent`
- `TicketExecutionPageComponent`
- `InventoryPageComponent`
- `ClientsPageComponent`
- `LocationMapComponent`
- `LocationPickerDialogComponent`

### Mocks (17 archivos JSON)
- Todos los archivos en `src/mocks/`

### Features detectadas
✅ Dashboard  
✅ Tickets (listado + ejecución)  
✅ Tareas (listado + ejecución)  
✅ Depósito/Inventory  
✅ Clientes con ubicación  
✅ Templates de tareas  
✅ Usuario activo mock  
✅ Control de acceso mock  
⚠️ Instalaciones (solo en navegación)  
⚠️ Facturación (solo en navegación)  
⚠️ Reportes (solo en navegación)  
⚠️ Configuración (solo en navegación)

### Mocks detectados
✅ Todos los datos vienen de JSON  
✅ Usuarios mock (3 usuarios)  
✅ Roles mock (admin/deposito/tecnico)  
✅ Control de acceso mock (client-side)  
✅ Task progress en localStorage  
✅ Ticket execution state en localStorage  
✅ Adjuntos simulados (Object URLs)  
✅ Creación de entidades (no persiste salvo storage)

### Integraciones reales detectadas
✅ Leaflet para mapas (client-side only)  
✅ OpenStreetMap tiles (gratuito)  
✅ Google Maps URLs (solo links externos)  
❌ NO hay Google Maps JavaScript API  
❌ NO hay HttpClient  
❌ NO hay fetch HTTP  
❌ NO hay backend  
❌ NO hay autenticación real

### Dudas o zonas grises
- **Integración task templates → task creation:** Existe UI pero no integración automática de subtareas
- **Sincronización inventory:** Despacho no descuenta stock, pedidos aprobados no reflejan en inventory
- **Environments:** Carpeta vacía, no hay configuración de entornos
- **Tests:** No se relevaron archivos de test (fuera del alcance)
- **Guards de ruta:** No existen, URLs directas no protegidas
