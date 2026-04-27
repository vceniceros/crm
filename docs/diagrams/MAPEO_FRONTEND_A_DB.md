# Mapeo Frontend → Base de Datos

> **Propósito:** Relacionar los mocks actuales del frontend con las tablas del esquema propuesto  
> **Fecha:** Abril 2026

---

## 📋 Tabla de Contenidos

1. [Archivos Mock → Tablas](#archivos-mock--tablas)
2. [Servicios Mock → Endpoints Futuros](#servicios-mock--endpoints-futuros)
3. [Modelos TypeScript → Tablas SQL](#modelos-typescript--tablas-sql)
4. [Operaciones Clave](#operaciones-clave)

---

## 1. Archivos Mock → Tablas

### Correspondencia directa entre JSONs y tablas SQL

| Archivo Mock | Tabla(s) SQL Principal(es) | Notas |
|--------------|---------------------------|-------|
| **users-data.json** | `users`, `user_roles` | Agregar password_hash, expandir roles |
| **clients-data.json** | `clients`, `client_locations`, `locations` | Separar ubicaciones |
| **inventory-products-data.json** | `inventory_products`, `inventory_stock` | Separar catálogo de stock |
| **inventory-categories-data.json** | `inventory_categories` | Directo |
| **inventory-items-data.json** | `inventory_products` | Mismo que products, consolidar |
| **stock-devices-data.json** | `stock_devices`, `client_devices` | Separar catálogo de asignación |
| **task-templates-data.json** | `task_templates`, `template_subtasks`, `template_materials` | Expandir jerarquía |
| **tasks-data.json** | `tasks` | Metadata de tareas |
| **task-execution-data.json** | `tasks`, `subtasks`, `subtask_checklist_items` | Separar definición de checklist |
| **task-progress-data.json** | `subtask_checklist_progress`, `subtasks.is_completed` | Progreso separado |
| **task-creation-data.json** | N/A | Datos para formularios (catálogos) |
| **tickets-data.json** | `tickets` | Metadata de tickets |
| **ticket-categories-data.json** | `ticket_categories` | Directo |
| **ticket-execution-data.json** | `tickets`, `ticket_resolution_notes` | Separar resolución |
| **ticket-execution-state-data.json** | `ticket_resolution_notes`, `ticket_inventory_requests`, `ticket_dispatches` | Estado operativo |
| **materials-data.json** | `inventory_products` | Mismo que products |
| **layout-data.json** | N/A | Configuración frontend, no persiste en BD |

---

## 2. Servicios Mock → Endpoints Futuros

### Migración de servicios mock a API REST

| Servicio Mock | Endpoints Backend Sugeridos | Tablas Involucradas |
|---------------|----------------------------|---------------------|
| **MockUserContextService** | `GET /api/auth/me`<br>`POST /api/auth/login`<br>`POST /api/auth/logout` | `users`, `user_sessions`, `user_roles` |
| **MockAccessControlService** | `GET /api/auth/permissions`<br>`GET /api/navigation` | `users`, `user_roles`, `roles` |
| **MockClientsService** | `GET /api/clients`<br>`POST /api/clients`<br>`GET /api/clients/:id` | `clients`, `client_locations`, `locations` |
| **MockTasksService** | `GET /api/tasks`<br>`POST /api/tasks`<br>`GET /api/tasks/:id` | `tasks`, `subtasks`, `task_templates` |
| **MockTaskExecutionService** | `GET /api/tasks/:id/execution`<br>`PATCH /api/tasks/:id/subtasks/:subtaskId`<br>`POST /api/tasks/:id/finalize` | `tasks`, `subtasks`, `subtask_checklist_progress`, `task_attachments` |
| **MockTaskProgressStorageService** | (Migrar a backend)<br>`GET /api/tasks/:id/progress`<br>`PATCH /api/tasks/:id/progress` | `subtasks`, `subtask_checklist_progress`, `subtask_assignments` |
| **MockTicketsService** | `GET /api/tickets`<br>`POST /api/tickets`<br>`GET /api/tickets/:id` | `tickets`, `ticket_categories`, `ticket_priorities` |
| **MockTicketExecutionService** | `GET /api/tickets/:id/execution`<br>`PATCH /api/tickets/:id/resolution`<br>`POST /api/tickets/:id/attachments`<br>`POST /api/tickets/:id/inventory-requests`<br>`POST /api/tickets/:id/dispatch` | `tickets`, `ticket_resolution_notes`, `ticket_attachments`, `ticket_inventory_requests`, `ticket_dispatches` |
| **MockTicketExecutionStorageService** | (Migrar a backend)<br>`GET /api/tickets/:id/state` | `ticket_resolution_notes`, `ticket_inventory_requests`, `ticket_dispatches` |
| **MockInventoryService** | `GET /api/inventory/products`<br>`POST /api/inventory/products`<br>`PATCH /api/inventory/products/:id/stock` | `inventory_products`, `inventory_stock`, `inventory_movements` |
| **MockTaskTemplateService** | `GET /api/task-templates`<br>`POST /api/task-templates`<br>`GET /api/task-templates/:id` | `task_templates`, `template_subtasks`, `template_materials` |
| **MockTaskCreationService** | `GET /api/tasks/creation-data` | Agregado de múltiples tablas (clients, templates, users) |
| **MockLayoutDataService** | `GET /api/dashboard`<br>`GET /api/navigation` | Agregado de múltiples tablas (tickets, tasks, users) |

---

## 3. Modelos TypeScript → Tablas SQL

### Mapeo de interfaces TypeScript a estructura SQL

#### 3.1. Usuarios

| Modelo TS | Tabla SQL | Notas de Conversión |
|-----------|-----------|---------------------|
| `MockUserProfile` | `users` + `user_roles` (JOIN) | Agregar `password_hash`, expandir `role` a relación many-to-many |
| `MockUsersData` | `users` (lista) | Mismo mapeo |

**Conversión sugerida:**
```typescript
// Frontend (TypeScript)
interface UserProfile {
  id: number;
  name: string;
  role: 'admin' | 'tecnico' | 'deposito';
  initials: string;
}

// Backend (SQL + TypeScript DTO)
interface UserProfileDTO {
  id: string; // UUID
  fullName: string;
  email: string;
  roles: RoleDTO[]; // Array de roles
  initials: string;
  isActive: boolean;
}
```

---

#### 3.2. Clientes

| Modelo TS | Tabla SQL | Notas de Conversión |
|-----------|-----------|---------------------|
| `ClientItem` | `clients` | Separar ubicación |
| `ClientItem.location` | `locations` + `client_locations` | Extraer a tabla separada |

**Conversión sugerida:**
```typescript
// Frontend (MockClientItem)
interface ClientItem {
  id: number;
  businessName: string;
  taxId: string;
  email: string;
  phone: string;
  location?: { latitude: number; longitude: number; addressLabel?: string };
}

// Backend (ClientDTO)
interface ClientDTO {
  id: string; // UUID
  businessName: string;
  taxId: string;
  email: string;
  phone: string;
  primaryLocation?: LocationDTO; // Separado
  allLocations: LocationDTO[]; // Array de todas las ubicaciones
}

interface LocationDTO {
  id: string;
  latitude: number;
  longitude: number;
  addressLabel?: string;
  formattedAddress?: string;
}
```

---

#### 3.3. Tareas

| Modelo TS | Tabla(s) SQL | Notas de Conversión |
|-----------|-------------|---------------------|
| `TaskListItem` | `tasks` | Metadata de tarea |
| `TaskExecutionDefinition` | `tasks` + `subtasks` + `subtask_checklist_items` | Separar definición de checklist |
| `TaskExecutionSubtaskView` | `subtasks` (JOIN recursivo para jerarquía) | Soporte para árbol jerárquico |
| `TaskProgressState` | `subtask_checklist_progress` + `subtasks.is_completed` | Separar progreso de definición |
| `TaskAttachment` | `task_attachments` | Directo |

**Conversión clave: Subtareas jerárquicas**
```typescript
// Frontend (TaskExecutionSubtaskView)
interface TaskExecutionSubtaskView {
  id: string;
  title: string;
  items: string[]; // Array plano de checks
  isRequired: boolean;
  children?: TaskExecutionSubtaskView[]; // Recursivo
}

// Backend (SubtaskDTO)
interface SubtaskDTO {
  id: string; // UUID
  taskId: string;
  parentSubtaskId?: string;
  title: string;
  orderIndex: number; // Orden secuencial
  checklistItems: ChecklistItemDTO[];
  isRequired: boolean;
  isCompleted: boolean;
  currentAssignedUser?: UserSummaryDTO;
  children?: SubtaskDTO[]; // Recursivo (generado en backend)
}

interface ChecklistItemDTO {
  id: string;
  label: string;
  itemOrder: number;
  isRequired: boolean;
  isChecked: boolean; // De subtask_checklist_progress
  checkedAt?: string;
  checkedByUser?: UserSummaryDTO;
}
```

---

#### 3.4. Tickets

| Modelo TS | Tabla(s) SQL | Notas de Conversión |
|-----------|-------------|---------------------|
| `TicketListItem` | `tickets` + `ticket_categories` + `ticket_priorities` + `ticket_statuses` | JOINs para catálogos |
| `TicketExecutionDefinition` | `tickets` | Metadata |
| `TicketExecutionState` | `ticket_resolution_notes` + `ticket_inventory_requests` + `ticket_dispatches` | Separar componentes del estado |
| `TicketInventoryRequest` | `ticket_inventory_requests` + `ticket_inventory_request_items` | Header-detail |
| `TicketDispatchItem` | `ticket_dispatches` + `ticket_dispatch_items` | Header-detail |
| `TicketAttachment` | `ticket_attachments` | Directo |

**Conversión clave: Solicitudes vs Despachos**
```typescript
// Frontend (TicketInventoryRequest)
interface TicketInventoryRequest {
  id: string;
  items: Array<{
    productId: string;
    productName: string;
    quantityRequested: number;
  }>;
  status: 'pending' | 'approved' | 'rejected';
  requestedByUserId: string;
  requestedAt: string;
  reviewNotes?: string;
}

// Backend (TicketInventoryRequestDTO)
interface TicketInventoryRequestDTO {
  id: string; // UUID
  ticketId: string;
  items: TicketInventoryRequestItemDTO[];
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  requestedBy: UserSummaryDTO;
  requestedAt: string; // ISO 8601
  reviewedBy?: UserSummaryDTO;
  reviewedAt?: string;
  reviewNotes?: string;
}

interface TicketInventoryRequestItemDTO {
  id: string;
  product: ProductSummaryDTO;
  quantityRequested: number;
  notes?: string;
}
```

---

#### 3.5. Inventario

| Modelo TS | Tabla(s) SQL | Notas de Conversión |
|-----------|-------------|---------------------|
| `InventoryProduct` | `inventory_products` + `inventory_stock` | Separar catálogo de stock |
| `InventoryCategory` | `inventory_categories` | Directo |
| `InventoryItemOption` | `inventory_products` | Mismo, consolidar |
| `StockDeviceOption` | `stock_devices` | Directo |

**Conversión clave: Catálogo vs Stock**
```typescript
// Frontend (InventoryProduct)
interface InventoryProduct {
  id: number;
  name: string;
  categoryId: string;
  stock: number; // MEZCLADO
  imageUrl?: string;
}

// Backend (InventoryProductDTO)
interface InventoryProductDTO {
  id: string; // UUID
  productName: string;
  productCode: string;
  barcode?: string;
  category: CategorySummaryDTO;
  unitOfMeasure: string;
  imageUrl?: string;
  stock: StockDTO; // SEPARADO
  isActive: boolean;
}

interface StockDTO {
  quantityAvailable: number;
  quantityReserved: number;
  minimumStock?: number;
  warehouseId?: string; // Futuro multi-warehouse
}
```

---

## 4. Operaciones Clave

### Operaciones complejas que requieren múltiples tablas

#### 4.1. Crear Tarea desde Template

**Frontend (MockTaskCreationService):**
```typescript
createTask(formValue: CreateTaskFormValue): Observable<void> {
  // Solo log en consola
}
```

**Backend (API /api/tasks → SQL):**
```sql
-- 1. Insertar tarea
INSERT INTO tasks (task_title, client_id, template_id, current_assigned_user_id, created_by_user_id)
VALUES ($1, $2, $3, $4, $5) RETURNING task_id;

-- 2. Copiar subtareas del template
INSERT INTO subtasks (task_id, template_subtask_id, subtask_title, order_index, is_required)
SELECT $task_id, ts.template_subtask_id, ts.subtask_title, ts.order_index, ts.is_required
FROM template_subtasks ts
WHERE ts.template_id = $template_id;

-- 3. Copiar checklist items
INSERT INTO subtask_checklist_items (subtask_id, item_label, item_order, is_required)
SELECT s.subtask_id, tci.item_label, tci.item_order, tci.is_required
FROM subtasks s
JOIN template_subtasks ts ON s.template_subtask_id = ts.template_subtask_id
JOIN template_checklist_items tci ON tci.template_subtask_id = ts.template_subtask_id
WHERE s.task_id = $task_id;

-- 4. Crear asignación inicial
INSERT INTO subtask_assignments (subtask_id, assigned_user_id, assigned_by_user_id)
SELECT subtask_id, $assigned_user_id, $created_by_user_id
FROM subtasks WHERE task_id = $task_id;
```

---

#### 4.2. Completar Subtarea

**Frontend (MockTaskExecutionService):**
```typescript
toggleSubtaskCompletion(taskId: string, subtaskId: string): void {
  // Actualiza BehaviorSubject en memoria + localStorage
}
```

**Backend (API PATCH /api/tasks/:id/subtasks/:subtaskId → SQL):**
```sql
-- 1. Validar secuencia (no completar N+1 si N incompleta)
SELECT order_index FROM subtasks WHERE subtask_id = $subtask_id;
-- Verificar que todas las subtareas con order_index < current están completadas

-- 2. Marcar subtarea como completada
UPDATE subtasks 
SET is_completed = TRUE,
    completed_at = CURRENT_TIMESTAMP,
    completion_notes = $notes
WHERE subtask_id = $subtask_id;

-- 3. Actualizar estado de tarea padre si todas las subtareas están completas
UPDATE tasks
SET status = CASE 
    WHEN (SELECT COUNT(*) FROM subtasks WHERE task_id = $task_id AND is_completed = FALSE) = 0 
    THEN 'COMPLETED' 
    ELSE 'IN_PROGRESS' 
END
WHERE task_id = $task_id;
```

---

#### 4.3. Aprobar Solicitud de Inventario

**Frontend (MockTicketExecutionService):**
```typescript
approveInventoryRequest(ticketId: string, requestId: string): void {
  // Actualiza BehaviorSubject + localStorage
}
```

**Backend (API PATCH /api/tickets/:ticketId/inventory-requests/:requestId → SQL):**
```sql
-- 1. Actualizar estado de solicitud
UPDATE ticket_inventory_requests
SET request_status = 'APPROVED',
    reviewed_by_user_id = $reviewer_user_id,
    reviewed_at = CURRENT_TIMESTAMP,
    review_notes = $notes
WHERE request_id = $request_id;

-- 2. (Opcional) Reservar stock automáticamente
UPDATE inventory_stock
SET quantity_reserved = quantity_reserved + 
    (SELECT SUM(quantity_requested) 
     FROM ticket_inventory_request_items 
     WHERE request_id = $request_id AND product_id = inventory_stock.product_id)
WHERE product_id IN (
    SELECT product_id FROM ticket_inventory_request_items WHERE request_id = $request_id
);
```

---

#### 4.4. Despachar Materiales

**Frontend (MockTicketExecutionService):**
```typescript
addDispatchItem(ticketId: string, item: TicketDispatchItem): void {
  // Actualiza BehaviorSubject + localStorage
}
```

**Backend (API POST /api/tickets/:ticketId/dispatch → SQL):**
```sql
BEGIN;

-- 1. Crear header de despacho
INSERT INTO ticket_dispatches (ticket_id, request_id, dispatched_by_user_id, dispatch_notes)
VALUES ($ticket_id, $request_id, $user_id, $notes)
RETURNING dispatch_id;

-- 2. Insertar items despachados
INSERT INTO ticket_dispatch_items (dispatch_id, product_id, quantity_dispatched, notes)
VALUES ($dispatch_id, $product_id, $quantity, $item_notes);

-- 3. Descontar stock (trigger o manual)
UPDATE inventory_stock
SET quantity_available = quantity_available - $quantity
WHERE product_id = $product_id;

-- 4. Registrar movimiento
INSERT INTO inventory_movements (
    product_id, movement_type, quantity, 
    reference_entity_type, reference_entity_id,
    performed_by_user_id
) VALUES (
    $product_id, 'OUT', -$quantity,
    'ticket_dispatch', $dispatch_id,
    $user_id
);

COMMIT;
```

---

#### 4.5. Dashboard Stats

**Frontend (MockLayoutDataService):**
```json
{
  "stats": [
    { "label": "Tickets Abiertos", "value": 12 },
    { "label": "Tareas Activas", "value": 8 },
    { "label": "Pendientes Aprobación", "value": 3 },
    { "label": "Instalaciones del Mes", "value": 24 }
  ]
}
```

**Backend (API GET /api/dashboard → SQL):**
```sql
-- Tickets abiertos
SELECT COUNT(*) FROM tickets 
WHERE status_id IN (SELECT status_id FROM ticket_statuses WHERE is_final = FALSE)
AND deleted_at IS NULL;

-- Tareas activas
SELECT COUNT(*) FROM tasks
WHERE status IN ('PENDING', 'IN_PROGRESS')
AND deleted_at IS NULL;

-- Solicitudes pendientes de aprobación
SELECT COUNT(*) FROM ticket_inventory_requests
WHERE request_status = 'PENDING';

-- Instalaciones del mes (asumiendo que hay tipo de tarea "instalacion")
SELECT COUNT(*) FROM tasks
WHERE task_title ILIKE '%instalación%'
AND created_at >= date_trunc('month', CURRENT_DATE)
AND deleted_at IS NULL;
```

---

## 5. Migraciones de localStorage a Backend

### Qué persiste hoy en localStorage y cómo migrarlo

| localStorage Key | Contenido | Migración Backend |
|------------------|-----------|-------------------|
| `microtv-crm.task-progress` | Progreso de subtareas (completadas, comentarios, adjuntos) | `subtasks.is_completed`, `subtask_checklist_progress`, `task_attachments` |
| `microtv-crm.ticket-execution` | Estado de tickets (resolución, adjuntos, requests, dispatch) | `ticket_resolution_notes`, `ticket_attachments`, `ticket_inventory_requests`, `ticket_dispatches` |

**Estrategia de migración:**
1. Mantener localStorage como "draft" temporal
2. Sincronizar con backend periódicamente (cada acción + cada 30 segundos)
3. Implementar offline-first con SW si hace falta
4. Resolver conflictos con "last-write-wins" o merge inteligente

---

## 6. Validaciones que pasan de Frontend a Backend

### Validaciones que HOY están solo en frontend y DEBEN moverse a backend

| Validación | Frontend Actual | Backend SQL/Logic |
|------------|-----------------|-------------------|
| **Secuencia de subtareas** | No completar N+1 si N incompleta | CHECK en UPDATE + lógica en backend |
| **Finalizar tarea** | Todas las subtareas requeridas completas | Verificar COUNT antes de marcar `is_finalized` |
| **Stock disponible** | No validado (mock) | CHECK en despacho: `quantity_available >= quantity_dispatched` |
| **Permisos de usuario** | Client-side (Mock*AccessControlService) | Middleware/guard en backend por endpoint |
| **Email único** | HTML input type="email" | UNIQUE constraint en `users.email` |
| **CUIT único** | HTML input | UNIQUE constraint en `clients.tax_id` |

---

## 7. Queries Complejas Sugeridas

### Ejemplos de queries útiles para el backend

#### 7.1. Obtener tarea con progreso completo
```sql
SELECT 
    t.task_id,
    t.task_title,
    c.business_name AS client_name,
    u.full_name AS assigned_user,
    COUNT(s.subtask_id) AS total_subtasks,
    COUNT(s.subtask_id) FILTER (WHERE s.is_completed = TRUE) AS completed_subtasks,
    ROUND(
        COUNT(s.subtask_id) FILTER (WHERE s.is_completed = TRUE) * 100.0 / 
        NULLIF(COUNT(s.subtask_id), 0), 
        2
    ) AS completion_percentage
FROM tasks t
LEFT JOIN clients c ON t.client_id = c.client_id
LEFT JOIN users u ON t.current_assigned_user_id = u.user_id
LEFT JOIN subtasks s ON t.task_id = s.task_id
WHERE t.task_id = $1
GROUP BY t.task_id, c.business_name, u.full_name;
```

#### 7.2. Obtener tickets pendientes del técnico con prioridad
```sql
SELECT 
    t.ticket_id,
    t.ticket_title,
    c.business_name AS client_name,
    tp.priority_label,
    tp.priority_level,
    ts.status_label,
    t.created_at,
    COUNT(tir.request_id) FILTER (WHERE tir.request_status = 'PENDING') AS pending_requests
FROM tickets t
JOIN clients c ON t.client_id = c.client_id
JOIN ticket_priorities tp ON t.priority_id = tp.priority_id
JOIN ticket_statuses ts ON t.status_id = ts.status_id
LEFT JOIN ticket_inventory_requests tir ON t.ticket_id = tir.ticket_id
WHERE t.current_technician_id = $user_id
AND t.deleted_at IS NULL
AND ts.is_final = FALSE
GROUP BY t.ticket_id, c.business_name, tp.priority_label, tp.priority_level, ts.status_label
ORDER BY tp.priority_level DESC, t.created_at ASC;
```

#### 7.3. Obtener productos con stock bajo
```sql
SELECT 
    p.product_id,
    p.product_name,
    p.product_code,
    s.quantity_available,
    s.minimum_stock,
    s.minimum_stock - s.quantity_available AS deficit
FROM inventory_products p
JOIN inventory_stock s ON p.product_id = s.product_id
WHERE s.quantity_available <= s.minimum_stock
AND p.is_active = TRUE
ORDER BY deficit DESC;
```

#### 7.4. Historial de asignaciones de una tarea
```sql
SELECT 
    sa.assignment_id,
    s.subtask_title,
    u.full_name AS assigned_user,
    sa.assigned_at,
    sa.unassigned_at,
    ua.full_name AS assigned_by
FROM subtask_assignments sa
JOIN subtasks s ON sa.subtask_id = s.subtask_id
JOIN users u ON sa.assigned_user_id = u.user_id
LEFT JOIN users ua ON sa.assigned_by_user_id = ua.user_id
WHERE s.task_id = $task_id
ORDER BY sa.assigned_at DESC;
```

---

## 8. Resumen de Migración

### Checklist de conversión frontend → backend

- [ ] **Usuarios y Auth**
  - [ ] Migrar `users-data.json` → insertar en `users` + `user_roles`
  - [ ] Implementar hashing de passwords (bcrypt)
  - [ ] Crear endpoint `/api/auth/login` con JWT
  - [ ] Reemplazar `MockUserContextService` → `AuthService`

- [ ] **Clientes**
  - [ ] Migrar `clients-data.json` → insertar en `clients`
  - [ ] Extraer ubicaciones → insertar en `locations` + `client_locations`
  - [ ] Endpoint `POST /api/clients` con validación de CUIT único

- [ ] **Inventario**
  - [ ] Migrar `inventory-products-data.json` → `inventory_products`
  - [ ] Inicializar `inventory_stock` con cantidad actual
  - [ ] Crear movimiento inicial (tipo 'IN') en `inventory_movements`
  - [ ] Endpoint `PATCH /api/inventory/products/:id/stock` con validación

- [ ] **Templates**
  - [ ] Migrar `task-templates-data.json` → `task_templates` + `template_subtasks`
  - [ ] Asociar materiales → `template_materials`

- [ ] **Tareas**
  - [ ] Migrar `tasks-data.json` → `tasks`
  - [ ] Migrar `task-execution-data.json` → `subtasks` + `subtask_checklist_items`
  - [ ] Migrar progreso localStorage → `subtask_checklist_progress`
  - [ ] Endpoint `POST /api/tasks/:id/finalize` con validación de completitud

- [ ] **Tickets**
  - [ ] Migrar `tickets-data.json` → `tickets`
  - [ ] Migrar estado localStorage → `ticket_resolution_notes`, `ticket_inventory_requests`, `ticket_dispatches`
  - [ ] Endpoint `POST /api/tickets/:id/inventory-requests` con validación de stock

- [ ] **Adjuntos**
  - [ ] Implementar upload a storage (S3/Azure/filesystem)
  - [ ] Generar URLs pre-firmadas
  - [ ] Migrar metadata → `task_attachments`, `ticket_attachments`

---

**Conclusión:** Este mapeo asegura que TODA la funcionalidad actual del frontend (aunque mock) tiene su correspondencia en el esquema de base de datos propuesto. La migración será directa y sin pérdida de features.
