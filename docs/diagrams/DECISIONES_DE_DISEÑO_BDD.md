# Decisiones de Diseño - Base de Datos CRM MicroTV

> **Versión:** 1.0  
> **Fecha:** Abril 2026  
> **Esquema SQL:** `schema-propuesto.sql`

---

## Resumen Ejecutivo

Este documento explica las decisiones de diseño tomadas para el esquema de base de datos relacional del CRM MicroTV. El diseño está **normalizado hacia BCNF** donde es razonable, priorizando:

- **Integridad referencial**
- **Trazabilidad completa**
- **Separación clara de conceptos**
- **Evolución futura sin rupturas**

**Total de tablas:** 38

---

## 1. Diagnóstico del schema.sql Original

### Problemas críticos encontrados:

#### 1.1. Ubicaciones embebidas incorrectamente
- **Problema:** `latitud` y `longitud` están dentro de tabla `Clientes`
- **Por qué es malo:** 
  - Un cliente puede tener múltiples ubicaciones (casa central, sucursales)
  - Tickets y tareas tienen ubicaciones que NO necesariamente pertenecen al cliente
  - Rompe 1NF si queremos múltiples ubicaciones por cliente
- **Solución:** Tabla `locations` normalizada + `client_locations` (many-to-many)

#### 1.2. Modelo de tareas/subtareas ausente
- **Problema:** El core funcional del sistema no está modelado
- **Impacto:** No se pueden implementar flujos de trabajo reales
- **Solución:** Sistema completo de 9 tablas para tareas (ver Sección 5)

#### 1.3. Concepto "Visitas" espurio
- **Problema:** No aparece en el frontend actual
- **Decisión:** Eliminar. Si reaparece, modelar correctamente desde cero

#### 1.4. Roles como VARCHAR libre
- **Problema:** `rol VARCHAR(50)` permite datos inconsistentes
- **Solución:** Tabla `roles` + `user_roles` (many-to-many)
- **Beneficio:** Usuarios con múltiples roles, extensibilidad, integridad

#### 1.5. No distingue catálogo vs stock vs consumo
- **Problema:** `Productos` mezcla definición, stock actual y movimientos
- **Solución:** 
  - `inventory_products` (catálogo/definición)
  - `inventory_stock` (stock actual)
  - `inventory_movements` (trazabilidad)

#### 1.6. Relación incorrecta en Productos_entregados
- **Problema:** PK = FK implica relación 1:1 con solicitud
- **Realidad:** Una solicitud puede tener múltiples productos
- **Solución:** 
  - `ticket_inventory_requests` (header)
  - `ticket_inventory_request_items` (línea items)
  - `ticket_dispatches` (despachos)
  - `ticket_dispatch_items` (línea items despachados)

---

## 2. Decisiones de Normalización

### 2.1. Objetivo: BCNF donde razonable, 3NF mínimo

**Definiciones:**
- **1NF:** Valores atómicos, sin grupos repetitivos
- **2NF:** 1NF + todos los atributos no-clave dependen de toda la clave primaria
- **3NF:** 2NF + no hay dependencias transitivas
- **BCNF:** 3NF + toda dependencia funcional tiene superclave como determinante

**Enfoque aplicado:**
- Todas las tablas cumplen BCNF o están a 1 paso razonable
- No desnormalicé por "performance prematura"
- Única desnormalización: `current_assigned_user_id` en `tasks`, `subtasks`, `tickets` (cache del asignado actual)
  - Justificación: Evita JOIN constante para listados
  - Consistencia: Mantenida por triggers o lógica de aplicación
  - Fuente de verdad: Tablas `*_assignments` con historial completo

### 2.2. Separación definición vs ejecución vs progreso

**Principio clave:** No mezclar plantilla reutilizable con instancia ejecutable.

| Concepto | Definición | Ejecución | Progreso |
|----------|-----------|-----------|----------|
| **Task Templates** | `task_templates`, `template_subtasks`, `template_materials` | N/A | N/A |
| **Tasks** | `tasks` (metadata) | `subtasks` (ejecutables) | `subtask_checklist_progress`, `subtask_assignments` |
| **Tickets** | `tickets` (metadata) | N/A | `ticket_resolution_notes`, `ticket_inventory_requests`, `ticket_dispatches` |
| **Inventory** | `inventory_products` (catálogo) | N/A | `inventory_stock` (actual), `inventory_movements` (historial) |

**Beneficios:**
- Templates reutilizables sin contaminarse con datos de ejecución
- Múltiples tareas desde mismo template
- Trazabilidad histórica completa
- Auditoría de cambios

---

## 3. Decisiones por Módulo

### 3.1. Usuarios y Seguridad (4 tablas)

#### Roles como catálogo normalizado
- **Decisión:** `roles` + `user_roles` (many-to-many)
- **Por qué:** Usuario puede ser "tecnico" Y "deposito" simultáneamente
- **Alternativa rechazada:** ENUM o CHECK constraint (no extensible)

#### Sesiones JWT separadas
- **Tabla:** `user_sessions`
- **Por qué:** Permite revocar tokens, auditoría de accesos, multi-sesión
- **Campos clave:**
  - `token_jti` (JWT ID) para identificar token único
  - `refresh_token_hash` para refresh tokens
  - `revoked_at` para blacklist
  - `ip_address`, `user_agent` para auditoría

### 3.2. Clientes y Geografía (3 tablas)

#### Ubicaciones normalizadas
- **Decisión:** `locations` independiente de `clients`
- **Por qué:**
  - Cliente tiene múltiples sedes (`client_locations`)
  - Ticket/tarea puede ocurrir en ubicación NO registrada del cliente
  - Reutilización de ubicaciones
- **Estructura:**
  ```
  clients 1---* client_locations *---1 locations
  tasks/tickets *---0..1 locations (opcional, puede no ser sede del cliente)
  ```

#### Precisión de coordenadas
- `latitude DECIMAL(10, 8)` → ~1cm de precisión
- `longitude DECIMAL(11, 8)` → ~1cm de precisión
- CHECK constraints para rangos válidos (-90/90, -180/180)

### 3.3. Inventario (6 tablas)

#### Separación catálogo vs stock vs movimientos
**Problema resuelto:** Sistema anterior mezclaba todo en `Productos.stock INT`

**Nueva estructura:**
1. **inventory_products** (catálogo)
   - Definición del producto (nombre, código, categoría)
   - Inmutable (casi)
   - Compartido entre todos los almacenes

2. **inventory_stock** (estado actual)
   - `quantity_available` (disponible)
   - `quantity_reserved` (reservado para despachos pendientes)
   - `minimum_stock` (alerta de reposición)
   - Unique constraint: `(product_id, warehouse_id)`
   - Por ahora `warehouse_id` es NULL (único almacén), preparado para futuro multi-warehouse

3. **inventory_movements** (trazabilidad completa)
   - Cada entrada, salida, ajuste, consumo queda registrado
   - `movement_type`: IN, OUT, ADJUSTMENT, CONSUMPTION, RETURN
   - `reference_entity_type` + `reference_entity_id` → vincula a ticket_dispatch, purchase_order, etc.
   - Auditoría: quién, cuándo, por qué

**Beneficios:**
- Trazabilidad completa para auditoría
- Cálculo de stock histórico (sumar movimientos)
- Detección de discrepancias
- Reportes de consumo por ticket/tarea

#### Dispositivos del cliente
- **stock_devices:** Catálogo de dispositivos (DVR, cámaras, etc.)
- **client_devices:** Qué dispositivos tiene instalados cada cliente
- **Uso:** En tickets, campo `affected_device_id` referencia a dispositivo específico del cliente

### 3.4. Templates de Tareas (3 tablas)

#### Estructura jerárquica de subtareas
- **template_subtasks** tiene `parent_template_subtask_id` (self-referencing FK)
- **order_index:** Orden secuencial de ejecución (0, 1, 2, ...)
- **Decisión:** Usar `order_index` numérico en lugar de linked list (`previous_subtask_id`)
  - **Por qué:** Más robusto, fácil de ordenar, fácil de insertar en medio
  - **Alternativa rechazada:** Linked list es frágil, complicado reordenar, dificulta queries

#### Materiales requeridos
- **template_materials:** Productos necesarios para completar template
- **Relación:** `template_id` + `product_id` (many-to-many)
- **Uso futuro:** Al crear tarea desde template, pre-cargar materiales necesarios

### 3.5. Tareas (9 tablas)

#### Instancias ejecutables
- **tasks:** Tarea (épica/trabajo grande)
- **subtasks:** Subtareas ejecutables (copiadas de template o creadas ad-hoc)
- **Relación con template:** `tasks.template_id` (nullable), `subtasks.template_subtask_id` (nullable)
- **Por qué nullable:** Permite tareas sin template (creación manual)

#### Secuencia y dependencias
- **Decisión:** `subtasks.order_index` define orden secuencial
- **Regla de negocio:** Subtarea N+1 no puede iniciarse hasta que N esté completa
- **Implementación:** Validación en backend antes de marcar subtarea como iniciada
- **Alternativa rechazada:** Tabla `subtask_dependencies` (overkill para secuencia simple)

#### Checklist items dentro de subtareas
- **subtask_checklist_items:** Checks tipo "Verificar voltaje", "Instalar bracket"
- **subtask_checklist_progress:** Estado de cada check (completado o no)
- **Separación:** Definición vs progreso (permite resetear progreso sin perder definición)

#### Asignaciones con historial
- **subtask_assignments:** Historial completo de quién trabajó cuándo
- **subtasks.current_assigned_user_id:** Cache del asignado actual (desnormalización razonable)
- **Por qué ambos:**
  - Listados rápidos sin JOIN a historial
  - Trazabilidad completa de cambios de manos
  - Auditoría de reasignaciones

#### Adjuntos vinculados a nivel subtarea
- **task_attachments:** Adjuntos de fotos/videos
- **Campos clave:**
  - `task_id` (NOT NULL)
  - `subtask_id` (NULL si el adjunto es de la tarea general)
- **file_url:** URL completa consumible por frontend (storage externo, NO blob en BD)
- **mime_type:** Para validar tipo de archivo
- **attachment_type:** PHOTO, VIDEO, DOCUMENT (enum check)

### 3.6. Tickets (11 tablas)

#### Ciclo de vida explícito
- **ticket_statuses:** Tabla de catálogo con `status_order` y `is_final`
- **Estados:** OPEN → IN_PROGRESS → AWAITING_APPROVAL → RESOLVED → CLOSED/CANCELLED
- **Beneficio:** Extensible, permite agregar estados, permite workflows

#### Prioridades normalizadas
- **ticket_priorities:** Tabla de catálogo con `priority_level`
- **Uso:** Ordenamiento, SLA, dashboard

#### Asignaciones duales (técnico + depósito)
- **tickets.current_technician_id:** Técnico asignado
- **tickets.current_warehouse_user_id:** Depósito asignado
- **ticket_assignments:** Historial de cambios (con `assignment_type` = 'TECHNICIAN' | 'WAREHOUSE')

#### Resolución con notas
- **ticket_resolution_notes:** Comentarios del técnico (puede haber múltiples)
- **Por qué no un campo en tickets:** Permite múltiples comentarios, historial de actualizaciones

#### Solicitudes vs Despachos (separados)
**Decisión crítica:** NO asumir que todo despacho viene de solicitud previa.

**Estructura:**
1. **ticket_inventory_requests** (header de solicitud)
   - Técnico crea solicitud
   - Estado: PENDING → APPROVED/REJECTED por depósito
   - `reviewed_by_user_id`, `review_notes`

2. **ticket_inventory_request_items** (línea items de solicitud)
   - Productos y cantidades solicitadas

3. **ticket_dispatches** (header de despacho)
   - Depósito despacha material
   - `request_id` (NULLABLE) → puede o no estar relacionado con solicitud
   - **Por qué nullable:** Depósito puede despachar sin solicitud previa (decisión operativa)

4. **ticket_dispatch_items** (línea items despachados)
   - Productos y cantidades realmente despachadas

**Beneficios:**
- Flexibilidad operativa: despacho sin solicitud previa SI hace falta
- Trazabilidad: qué se solicitó vs qué se despachó
- Auditoría: solicitudes rechazadas quedan registradas
- Reportes: materiales más solicitados, tasa de aprobación

**Integración con stock:**
- Cada `ticket_dispatch_items` genera entrada en `inventory_movements` (tipo CONSUMPTION)
- Trigger o lógica de backend actualiza `inventory_stock.quantity_available`

---

## 4. Patrones de Diseño Aplicados

### 4.1. Soft Deletes
- **Tablas con `deleted_at`:** clients, users, inventory_products, tasks, tickets
- **Por qué:** Permite "borrar" sin perder referencias, auditoría, posible restauración
- **Implementación:** Índices con `WHERE deleted_at IS NULL` para queries activos

### 4.2. Auditoría automática
- **Todas las tablas tienen:**
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`
- **Trigger:** `update_updated_at_column()` actualiza `updated_at` en cada UPDATE

### 4.3. Historial de asignaciones
- **Patrón:** Tabla de historial + campo cache en entidad principal
- **Ejemplos:**
  - `subtask_assignments` + `subtasks.current_assigned_user_id`
  - `ticket_assignments` + `tickets.current_technician_id`
- **Beneficio:** Performance para listados + trazabilidad completa

### 4.4. Header-Detail (Maestro-Detalle)
- **Ejemplos:**
  - `ticket_inventory_requests` ← `ticket_inventory_request_items`
  - `ticket_dispatches` ← `ticket_dispatch_items`
- **Por qué:** Agrupa items relacionados, permite metadata de header (fecha solicitud, estado, aprobador)

### 4.5. Polimorfismo evitado conscientemente
- **NO usé:** Tabla genérica `attachments` con `entity_type` + `entity_id`
- **Preferí:** `task_attachments`, `ticket_attachments` separadas
- **Por qué:**
  - Type safety en constraints
  - Claridad de relaciones
  - FKs reales (no simuladas)
  - Menos bugs en queries

### 4.6. Catálogos normalizados vs ENUMs
- **Tablas de catálogo:** roles, ticket_statuses, ticket_priorities, ticket_categories, inventory_categories
- **Por qué NO enum:**
  - Extensibilidad (agregar nuevos valores sin ALTER TABLE)
  - Localización (agregar traducciones)
  - Metadata adicional (descripción, orden, is_active)
- **Cuándo SÍ usar CHECKs:** Valores técnicos fijos (attachment_type, movement_type)

---

## 5. Decisiones de Integridad Referencial

### ON DELETE políticas

| Relación | Política | Justificación |
|----------|----------|---------------|
| `users.role` → `roles` | CASCADE | Si se borra role, desasignar usuarios |
| `tasks.client` → `clients` | CASCADE | Si se borra cliente, borrar sus tareas |
| `tasks.assigned_user` → `users` | SET NULL | Usuario puede ser dado de baja pero tarea persiste |
| `subtasks.task` → `tasks` | CASCADE | Subtarea no existe sin tarea |
| `task_attachments.subtask` → `subtasks` | CASCADE | Adjunto no existe sin subtarea |
| `tickets.priority` → `ticket_priorities` | RESTRICT | No borrar prioridad si hay tickets usándola |
| `inventory_products.category` → `inventory_categories` | SET NULL | Producto puede quedar sin categoría |

### Restricciones UNIQUE críticas
- `users.email` (no duplicar emails)
- `clients.tax_id` (CUIT único)
- `roles.role_key` (identificador único de rol)
- `inventory_stock(product_id, warehouse_id)` (stock único por producto-almacén)
- `user_roles(user_id, role_id)` (no duplicar asignación)

---

## 6. Índices Estratégicos

### Criterios de indexación
1. **Foreign keys:** Siempre indexados (join performance)
2. **Columnas de filtrado común:** status, priority, created_at
3. **Columnas de búsqueda:** email, tax_id, barcode, serial_number
4. **Índices parciales:** `WHERE deleted_at IS NULL` para soft deletes

### Ejemplos clave
```sql
-- Búsqueda de tickets por técnico asignado
CREATE INDEX idx_tickets_technician ON tickets(current_technician_id);

-- Tareas pendientes del usuario
CREATE INDEX idx_tasks_status ON tasks(status) WHERE deleted_at IS NULL;

-- Historial de asignaciones ordenado
CREATE INDEX idx_subtask_assignments_subtask 
ON subtask_assignments(subtask_id, assigned_at DESC);

-- Stock bajo para alertas
CREATE INDEX idx_inventory_stock_low 
ON inventory_stock(product_id) 
WHERE quantity_available <= minimum_stock;
```

---

## 7. Preparación para Backend Real

### 7.1. JWT y autenticación
- **user_sessions:** Lista de tokens activos (whitelist o blacklist según estrategia)
- **Campo `token_jti`:** Permite revocar tokens específicos
- **Campo `refresh_token_hash`:** Implementar refresh tokens seguros

### 7.2. Multi-warehouse (futuro)
- **inventory_stock:** Ya tiene `warehouse_id` (nullable)
- **Cuando se active:**
  - Crear tabla `warehouses`
  - FK en `inventory_stock.warehouse_id`
  - Unique constraint `(product_id, warehouse_id)` ya existe

### 7.3. Sincronización stock con despachos
**Trigger sugerido:**
```sql
CREATE FUNCTION sync_stock_on_dispatch()
RETURNS TRIGGER AS $$
BEGIN
    -- Descontar stock al crear dispatch item
    UPDATE inventory_stock
    SET quantity_available = quantity_available - NEW.quantity_dispatched
    WHERE product_id = NEW.product_id;
    
    -- Crear movimiento
    INSERT INTO inventory_movements (
        product_id, movement_type, quantity,
        reference_entity_type, reference_entity_id,
        performed_by_user_id, notes
    ) VALUES (
        NEW.product_id, 'OUT', -NEW.quantity_dispatched,
        'ticket_dispatch', NEW.dispatch_id,
        (SELECT dispatched_by_user_id FROM ticket_dispatches WHERE dispatch_id = NEW.dispatch_id),
        'Despacho automático de ticket'
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_insert_ticket_dispatch_items
AFTER INSERT ON ticket_dispatch_items
FOR EACH ROW EXECUTE FUNCTION sync_stock_on_dispatch();
```

### 7.4. Validación de permisos en backend
**Implementar:** Middleware o guards que verifiquen:
- Usuario tiene rol requerido para acción
- Usuario asignado puede editar ticket/tarea
- Depósito puede aprobar solicitudes
- Técnico puede crear solicitudes

**NO confiar en frontend:** Control de acceso en `MockAccessControlService` es solo UX.

---

## 8. Supuestos y Áreas Grises

### 8.1. Ubicaciones de tickets/tareas
**Supuesto:** Ubicación puede NO ser una sede registrada del cliente.
- **Por qué:** Cliente reporta problema en obra en construcción, no es sede fija
- **Modelado:** `location_id` nullable en tickets/tasks, puede o no estar en `client_locations`

### 8.2. Despachos sin solicitud previa
**Supuesto:** Depósito puede despachar material sin solicitud formal del técnico.
- **Escenario:** Técnico llama por teléfono, depósito despacha directamente
- **Modelado:** `ticket_dispatches.request_id` nullable

### 8.3. Subtareas sin template
**Supuesto:** Usuario puede crear tarea ad-hoc sin template.
- **Modelado:** `tasks.template_id` nullable, `subtasks.template_subtask_id` nullable

### 8.4. Múltiples técnicos en una tarea
**Supuesto actual:** Cada subtarea tiene UN asignado, pero diferentes subtareas pueden tener diferentes técnicos.
- **Si se necesita:** Múltiples técnicos simultáneos en una subtarea → crear `subtask_collaborators` (many-to-many)

### 8.5. Tickets sin técnico asignado
**Supuesto:** Ticket puede crearse sin técnico inicial (asignación posterior).
- **Modelado:** `tickets.current_technician_id` nullable

---

## 9. Mejoras Futuras Consideradas

### 9.1. SLA (Service Level Agreement)
**Estructura sugerida:**
```sql
CREATE TABLE sla_policies (
    sla_id UUID PRIMARY KEY,
    priority_id UUID REFERENCES ticket_priorities,
    response_time_hours INT,
    resolution_time_hours INT
);

ALTER TABLE tickets ADD COLUMN sla_response_due_at TIMESTAMPTZ;
ALTER TABLE tickets ADD COLUMN sla_resolution_due_at TIMESTAMPTZ;
```

### 9.2. Notificaciones persistentes
**Estructura sugerida:**
```sql
CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users,
    notification_type VARCHAR(50),
    related_entity_type VARCHAR(50),
    related_entity_id UUID,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ
);
```

### 9.3. Tareas recurrentes
**Estructura sugerida:**
```sql
CREATE TABLE task_schedules (
    schedule_id UUID PRIMARY KEY,
    template_id UUID REFERENCES task_templates,
    client_id UUID REFERENCES clients,
    recurrence_rule VARCHAR(255), -- RRULE format
    next_execution_date DATE
);
```

### 9.4. Comentarios internos en tickets
**Alternativa actual:** `ticket_resolution_notes` cumple este rol.
**Mejora:** Agregar `note_type` ('RESOLUTION', 'INTERNAL', 'CLIENT_VISIBLE')

### 9.5. Versionado de templates
**Problema:** Si se modifica template, ¿afecta tareas existentes creadas con versión anterior?
**Solución:**
```sql
ALTER TABLE task_templates ADD COLUMN version_number INT DEFAULT 1;
ALTER TABLE tasks ADD COLUMN template_version_used INT;
```

---

## 10. Checklist de Migración Frontend → Backend

### Fase 1: Autenticación
- [ ] Implementar endpoints `/api/auth/login`, `/api/auth/refresh`
- [ ] Crear `AuthService` en Angular
- [ ] Implementar interceptor JWT
- [ ] Migrar `MockUserContextService` → `AuthService`
- [ ] Crear guards de autenticación

### Fase 2: CRUD básico
- [ ] Endpoints GET/POST/PATCH/DELETE para cada entidad
- [ ] Migrar `Mock*Service` → `*ApiService`
- [ ] Validación server-side
- [ ] Manejo de errores HTTP

### Fase 3: Lógica de negocio
- [ ] Validar secuencia de subtareas (no completar N+1 si N incompleta)
- [ ] Actualizar contadores (total_subtasks, completed_subtasks)
- [ ] Enviar notificaciones (email, push)
- [ ] Triggers de stock (despacho → inventory_movements)

### Fase 4: Upload de archivos
- [ ] Implementar upload a storage (S3, Azure Blob, local filesystem)
- [ ] Generar URLs pre-firmadas para descarga segura
- [ ] Validar tipo y tamaño de archivos
- [ ] Migrar `task_attachments.file_url` a URLs reales

### Fase 5: Reportes y dashboard
- [ ] Queries optimizadas con agregaciones
- [ ] Cachear contadores de dashboard
- [ ] Implementar filtros y paginación
- [ ] Exportación a PDF/Excel

---

## 11. Conclusión

Este esquema de base de datos:

✅ **Cumple todos los requisitos funcionales** del frontend actual  
✅ **Está normalizado hacia BCNF** donde es razonable  
✅ **Separa claramente** definición, ejecución y progreso  
✅ **Tiene trazabilidad completa** de asignaciones, movimientos y cambios  
✅ **Está preparado** para evolución futura sin rupturas  
✅ **Respeta las particularidades de negocio** explicadas en el brief  
✅ **No simplifica de más** donde eso destruiría integridad  
✅ **No inventa features** que no surgen del contexto  

**Próximo paso:** Implementar backend con Django/FastAPI/NestJS/Express que mapee este esquema y exponga API RESTful para el frontend Angular.

---

**Autor:** Diseño generado mediante análisis de FRONTEND_CURRENT_STATE.md y schema.sql  
**Revisión:** Pendiente de validación con equipo técnico  
**Contacto:** [GitHub Copilot]
