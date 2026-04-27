# Resumen Ejecutivo - Esquema de Base de Datos MicroTV CRM

> **Fecha:** Abril 2026  
> **Archivos generados:**  
> - `schema-propuesto.sql` (esquema SQL completo)  
> - `DECISIONES_DE_DISEÑO_BDD.md` (documentación detallada)  
> - `diagrama_de_entidades_propuesto.puml` (diagrama PlantUML)  

---

## ✅ Qué se completó

Se diseñó un esquema de base de datos relacional **completo y normalizado (BCNF)** que:

1. **Corrige todos los problemas del schema.sql original**
2. **Modela correctamente el contexto funcional del frontend**
3. **Separa claramente definición, ejecución y progreso**
4. **Tiene trazabilidad completa de cambios**
5. **Está preparado para evolución futura**

**Total:** 38 tablas organizadas en 7 módulos funcionales

---

## 📊 Estructura del Esquema

### Módulos principales (38 tablas)

| Módulo | Tablas | Propósito |
|--------|--------|-----------|
| **Usuarios y Seguridad** | 4 | `roles`, `users`, `user_roles`, `user_sessions` |
| **Clientes y Geografía** | 3 | `clients`, `locations`, `client_locations` |
| **Inventario** | 6 | Productos, categorías, stock, movimientos, dispositivos |
| **Templates de Tareas** | 3 | `task_templates`, `template_subtasks`, `template_materials` |
| **Tareas** | 9 | Tasks, subtasks, checklist, asignaciones, adjuntos |
| **Tickets** | 11 | Tickets, categorías, estados, resolución, inventario, despachos |
| **Catálogos** | 2 | `ticket_priorities`, `ticket_statuses` |

---

## 🎯 Decisiones Críticas de Diseño

### 1. Ubicaciones como entidad independiente ✅

**Problema original:** `latitud`/`longitud` embebidos en tabla `Clientes`

**Nueva estructura:**
```
clients 1---* client_locations *---1 locations
tasks/tickets *---0..1 locations (pueden tener ubicación NO registrada del cliente)
```

**Por qué:** 
- Cliente tiene múltiples sedes
- Ticket/tarea puede ocurrir en ubicación NO perteneciente al cliente
- Reutilización de ubicaciones

---

### 2. Separación catálogo vs stock vs movimientos ✅

**Problema original:** Todo mezclado en `Productos.stock INT`

**Nueva estructura:**
```
inventory_products (catálogo/definición)
    └── inventory_stock (stock actual por almacén)
    └── inventory_movements (historial completo de movimientos)
```

**Beneficios:**
- Trazabilidad completa para auditoría
- Detección de discrepancias
- Reportes de consumo histórico
- Preparado para multi-warehouse

---

### 3. Secuencia de subtareas con order_index ✅

**Decisión:** `subtasks.order_index INT` define orden secuencial (0, 1, 2, ...)

**Regla de negocio:** Subtarea N+1 no puede iniciarse hasta que N esté completa

**Alternativa rechazada:** Linked list con `previous_subtask_id` (frágil, complicado)

---

### 4. Historial de asignaciones + cache ✅

**Patrón aplicado:**
- Tabla de historial: `subtask_assignments`, `ticket_assignments`
- Campo cache: `subtasks.current_assigned_user_id`, `tickets.current_technician_id`

**Por qué ambos:**
- Cache → performance para listados (evita JOIN)
- Historial → trazabilidad completa de cambios de manos

---

### 5. Solicitudes vs Despachos separados ✅

**Decisión crítica:** NO asumir que todo despacho viene de solicitud previa

**Estructura:**
```
ticket_inventory_requests (solicitud del técnico)
    └── ticket_inventory_request_items (productos solicitados)
    
ticket_dispatches (despacho del depósito)
    └── ticket_dispatch_items (productos despachados)
    └── request_id (NULLABLE - puede despachar sin solicitud)
```

**Beneficio:** Flexibilidad operativa (depósito puede despachar sin solicitud formal si hace falta)

---

### 6. Templates vs Ejecución separados ✅

**Principio:** No mezclar definición reutilizable con instancia ejecutable

| Concepto | Definición | Ejecución |
|----------|-----------|-----------|
| **Templates** | `task_templates`, `template_subtasks` | N/A |
| **Tasks** | `tasks` (metadata) | `subtasks` (ejecutables) |
| **Stock** | `inventory_products` (catálogo) | `inventory_stock` (actual) |

---

### 7. Adjuntos como metadata (NO blobs) ✅

**Decisión:** Solo URLs en base de datos, NO binarios

```sql
CREATE TABLE task_attachments (
    attachment_id UUID PRIMARY KEY,
    task_id UUID FK,
    subtask_id UUID FK (nullable),
    file_url VARCHAR(1000),  -- URL consumible por Angular
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    attachment_type VARCHAR(50) -- 'PHOTO', 'VIDEO', 'DOCUMENT'
);
```

**Storage real:** S3, Azure Blob, o filesystem externo

---

### 8. Roles normalizados (NO enum ni VARCHAR libre) ✅

**Decisión:** Tabla `roles` + `user_roles` (many-to-many)

**Por qué:**
- Usuario puede tener múltiples roles
- Extensibilidad (agregar roles sin ALTER TABLE)
- Metadata adicional (descripción, is_active)

---

## 🔍 Comparación schema.sql original vs propuesto

| Aspecto | Original | Propuesto | Mejora |
|---------|----------|-----------|--------|
| **Ubicaciones** | Embebidas en Clientes | Tabla normalizada + many-to-many | ✅ Múltiples ubicaciones, reutilización |
| **Tareas** | ❌ No existe | 9 tablas con subtareas, checklist, asignaciones | ✅ Core funcional completo |
| **Tickets** | ❌ No existe | 11 tablas con resolución, inventario, despachos | ✅ Flujo operativo completo |
| **Stock** | 1 tabla mezclada | 3 tablas (catálogo, stock, movimientos) | ✅ Trazabilidad completa |
| **Roles** | VARCHAR(50) libre | Tabla normalizada | ✅ Integridad, extensibilidad |
| **Solicitudes** | Relación incorrecta | Header-detail + nullable | ✅ Flexible, correcto |
| **Auditoría** | Parcial | created_at, updated_at, deleted_at en todas | ✅ Auditoría completa |
| **Normalización** | Múltiples violaciones | BCNF donde razonable | ✅ Integridad relacional |

---

## 📋 Checklist de Cumplimiento

### Requisitos funcionales ✅

- [x] Clientes con múltiples ubicaciones
- [x] Ubicaciones independientes para tickets/tareas
- [x] Tareas divididas en subtareas secuenciales
- [x] Subtareas con checklist items
- [x] Subtareas pueden cambiar de asignado
- [x] Templates reutilizables de tareas
- [x] Tickets con resolución y adjuntos
- [x] Solicitudes de materiales con aprobación/rechazo
- [x] Despachos de materiales (vinculados o independientes)
- [x] Stock con trazabilidad completa
- [x] Dispositivos afectados en tickets
- [x] Adjuntos como metadata (URLs)
- [x] Usuarios con roles múltiples

### Requisitos técnicos ✅

- [x] Normalización BCNF/3NF
- [x] Claves primarias UUID
- [x] Foreign keys con políticas ON DELETE correctas
- [x] Unique constraints donde aplica
- [x] Check constraints para validación
- [x] Índices estratégicos
- [x] Soft deletes con deleted_at
- [x] Auditoría con created_at/updated_at
- [x] Triggers para updated_at automático
- [x] Datos semilla (seed data)
- [x] Comentarios COMMENT ON
- [x] Separación definición/ejecución
- [x] Historial de asignaciones
- [x] Preparado para JWT sessions
- [x] Preparado para multi-warehouse

---

## ⚠️ Decisiones donde NO se normalizó (justificadas)

### Cache de asignado actual
- **Campo:** `current_assigned_user_id` en `tasks`, `subtasks`, `tickets`
- **Por qué:** Performance en listados (evita JOIN constante)
- **Consistencia:** Mantenida por triggers o lógica de backend
- **Fuente de verdad:** Tablas `*_assignments` con historial completo

### Estados y prioridades como tablas (no ENUMs)
- **Decisión:** Tablas de catálogo en lugar de ENUMs PostgreSQL
- **Por qué:** Extensibilidad, localización, metadata adicional
- **Trade-off aceptado:** JOIN adicional vs ALTER TYPE en producción

---

## 🚀 Preparación para Backend Real

### JWT y Autenticación
```sql
CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID FK,
    token_jti VARCHAR(255) UNIQUE,  -- JWT ID
    refresh_token_hash VARCHAR(255),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
```

### Sincronización stock con despachos
```sql
-- Trigger sugerido para descontar stock automáticamente
CREATE TRIGGER after_insert_ticket_dispatch_items
AFTER INSERT ON ticket_dispatch_items
FOR EACH ROW EXECUTE FUNCTION sync_stock_on_dispatch();
```

### Multi-warehouse futuro
```sql
-- Ya preparado: inventory_stock tiene warehouse_id (nullable)
ALTER TABLE inventory_stock ADD CONSTRAINT fk_warehouse 
FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id);
```

---

## 📁 Archivos Generados

### 1. schema-propuesto.sql (esquema completo)
- 38 tablas con DDL completo
- Claves primarias, foráneas, unique constraints
- Índices estratégicos
- Triggers para updated_at
- Datos semilla
- Comentarios COMMENT ON

### 2. DECISIONES_DE_DISEÑO_BDD.md (documentación)
- Diagnóstico del schema original
- Decisiones de modelado justificadas
- Patrones aplicados
- Supuestos y áreas grises
- Checklist de migración frontend→backend

### 3. diagrama_de_entidades_propuesto.puml (diagrama)
- Diagrama PlantUML con relaciones visuales
- Organizado por paquetes funcionales
- Colores por tipo de entidad (master, detail, catalog, junction)

---

## 🎓 Lecciones Aprendidas

### Lo que se hizo bien ✅
1. **Análisis profundo del frontend antes de diseñar**
2. **Separación clara de conceptos (definición vs ejecución)**
3. **Trazabilidad priorizad desde el inicio**
4. **Normalización sin fanatismo (cache razonable)**
5. **Preparación para evolución futura**

### Lo que NO se hizo (intencionalmente) ❌
1. **No inventé features que no están en el frontend**
2. **No simplifiqué de más donde destruía trazabilidad**
3. **No usé polimorfismo genérico (tabla attachments única)**
4. **No asumí relaciones 1:1 donde puede haber many**
5. **No ignoré particularidades de negocio mencionadas**

---

## 📞 Próximos Pasos

### Fase 1: Validación (1-2 días)
- [ ] Revisar esquema con equipo técnico
- [ ] Validar reglas de negocio con stakeholders
- [ ] Ajustar si surgen nuevos requisitos

### Fase 2: Implementación DB (1 semana)
- [ ] Crear base de datos PostgreSQL
- [ ] Ejecutar schema-propuesto.sql
- [ ] Insertar datos de prueba
- [ ] Validar integridad referencial

### Fase 3: Backend (2-4 semanas)
- [ ] Elegir stack (Django/FastAPI/NestJS/Express)
- [ ] Implementar modelos ORM
- [ ] Crear endpoints REST
- [ ] Implementar JWT auth
- [ ] Validación server-side
- [ ] Upload de archivos a storage

### Fase 4: Migración Frontend (1-2 semanas)
- [ ] Reemplazar Mock*Service por *ApiService
- [ ] Implementar interceptors JWT
- [ ] Crear guards de autenticación
- [ ] Conectar formularios a API
- [ ] Eliminar localStorage (usar backend)

---

## ✨ Conclusión

Este esquema de base de datos:

✅ **Es completo:** Cubre todos los requisitos funcionales del frontend  
✅ **Es consistente:** Normalizado hacia BCNF con trazabilidad completa  
✅ **Es extensible:** Preparado para evolución sin rupturas  
✅ **Es pragmático:** No se normaliza de más donde no aporta  
✅ **Es auditable:** Historial completo de cambios y asignaciones  
✅ **Es claro:** Separación explícita de conceptos  

**Puede implementarse directamente en producción** una vez validado por el equipo.

---

**Autor:** GitHub Copilot  
**Fuentes:** `FRONTEND_CURRENT_STATE.md` + `schema.sql` original  
**Revisión:** Pendiente de validación técnica  
**Contacto:** Para consultas sobre el diseño, revisar `DECISIONES_DE_DISEÑO_BDD.md`
