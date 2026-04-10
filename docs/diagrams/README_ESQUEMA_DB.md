# Esquema de Base de Datos - MicroTV CRM

> **Fecha:** Abril 2026  
> **Autor:** GitHub Copilot  
> **Versión:** 1.0

---

## 📋 Índice de Documentación

Este directorio contiene el diseño completo de la base de datos relacional para el CRM MicroTV.

### Documentos Principales

1. **[RESUMEN_EJECUTIVO_BDD.md](./RESUMEN_EJECUTIVO_BDD.md)** ⭐  
   **→ EMPEZAR AQUÍ**  
   Resumen ejecutivo con las decisiones más importantes, tabla comparativa y checklist de cumplimiento.

2. **[schema-propuesto.sql](./schema-propuesto.sql)** 🗄️  
   **Esquema SQL completo** con:
   - 38 tablas con DDL completo
   - Claves primarias, foráneas, constraints
   - Índices estratégicos
   - Triggers y funciones
   - Datos semilla
   - Comentarios COMMENT ON

3. **[DECISIONES_DE_DISEÑO_BDD.md](./DECISIONES_DE_DISEÑO_BDD.md)** 📖  
   Documentación técnica detallada:
   - Diagnóstico del schema.sql original
   - Justificación de cada decisión de modelado
   - Patrones aplicados
   - Supuestos y áreas grises
   - Mejoras futuras consideradas

4. **[MAPEO_FRONTEND_A_DB.md](./MAPEO_FRONTEND_A_DB.md)** 🔗  
   Mapeo entre el frontend actual y las tablas SQL:
   - Archivos mock → tablas
   - Servicios mock → endpoints futuros
   - Modelos TypeScript → tablas SQL
   - Operaciones complejas
   - Queries sugeridas

5. **[diagrama_de_entidades_propuesto.puml](./diagrama_de_entidades_propuesto.puml)** 📊  
   Diagrama PlantUML con visualización de todas las relaciones.

---

## ✅ Qué se entrega

### 1. Diagnóstico del schema.sql actual

**Problemas encontrados:**
- ❌ Ubicaciones embebidas incorrectamente en `Clientes`
- ❌ No existe modelo de tareas/subtareas (core funcional ausente)
- ❌ No existe modelo de tickets
- ❌ Roles como VARCHAR libre (no normalizado)
- ❌ No distingue catálogo vs stock vs movimientos
- ❌ Relación incorrecta en `Productos_entregados` (PK=FK implica 1:1)
- ❌ Sin trazabilidad de asignaciones
- ❌ Sin historial de cambios
- ❌ "Visitas" es concepto espurio (no aparece en frontend)

---

### 2. Decisiones de Modelado

#### Normalización: BCNF donde razonable, 3NF mínimo

**Principios aplicados:**
- ✅ Separar definición de ejecución de progreso
- ✅ No mezclar catálogo con stock con consumo
- ✅ Ubicaciones como entidad independiente
- ✅ Historial completo de asignaciones
- ✅ Adjuntos como metadata (no blobs)
- ✅ Roles normalizados (no enum ni VARCHAR)

**Única desnormalización (justificada):**
- Cache de asignado actual (`current_assigned_user_id`) para performance
- Fuente de verdad: tablas `*_assignments` con historial completo

---

### 3. Modelo Conceptual Resumido

#### Entidades principales (38 tablas)

**Usuarios y Seguridad (4):**
- `roles`, `users`, `user_roles`, `user_sessions`

**Clientes y Geografía (3):**
- `clients`, `locations`, `client_locations`

**Inventario (6):**
- `inventory_categories`, `inventory_products`, `inventory_stock`
- `inventory_movements`, `stock_devices`, `client_devices`

**Templates de Tareas (3):**
- `task_templates`, `template_subtasks`, `template_materials`

**Tareas (9):**
- `tasks`, `subtasks`, `subtask_checklist_items`
- `subtask_checklist_progress`, `subtask_assignments`, `task_attachments`

**Tickets (11):**
- `ticket_categories`, `ticket_statuses`, `ticket_priorities`, `tickets`
- `ticket_assignments`, `ticket_resolution_notes`, `ticket_attachments`
- `ticket_inventory_requests`, `ticket_inventory_request_items`
- `ticket_dispatches`, `ticket_dispatch_items`

#### Relaciones clave

```
users 1---* tasks, tickets, subtasks (asignaciones)
clients 1---* tasks, tickets
clients *---* locations (vía client_locations)
locations 0..1---* tasks, tickets (ubicación puede NO ser sede del cliente)

tasks 1---* subtasks (secuencia por order_index)
subtasks 1---* subtask_checklist_items
subtasks 1---* subtask_assignments (historial)

tickets 1---* ticket_inventory_requests 1---* ticket_inventory_request_items
tickets 1---* ticket_dispatches 1---* ticket_dispatch_items
ticket_dispatches *---0..1 ticket_inventory_requests (despacho puede ser sin solicitud)

inventory_products 1---* inventory_stock (stock actual)
inventory_products 1---* inventory_movements (trazabilidad)
```

---

### 4. Esquema SQL Propuesto

**Ver archivo:** [schema-propuesto.sql](./schema-propuesto.sql)

**Highlights:**
- PostgreSQL con extensión `uuid-ossp`
- UUIDs como claves primarias
- TIMESTAMPTZ para auditoría
- Soft deletes con `deleted_at`
- Triggers para `updated_at` automático
- CHECK constraints para validación
- Índices estratégicos
- Datos semilla (roles, prioridades, estados)

**Estructura por sección:**
1. Usuarios y seguridad
2. Clientes y geografía
3. Inventario y productos
4. Templates de tareas
5. Tareas (tasks)
6. Tickets
7. Triggers y funciones
8. Datos semilla

---

### 5. Notas de Diseño

#### Responde al frontend actual ✅

Todas las funcionalidades del frontend mock están cubiertas:
- ✅ Dashboard con estadísticas
- ✅ Listado y creación de tickets
- ✅ Ejecución de tickets (resolución, adjuntos, inventario, despacho)
- ✅ Listado y creación de tareas
- ✅ Ejecución de tareas (checklist, comentarios, adjuntos)
- ✅ Gestión de depósito (productos, stock)
- ✅ Gestión de clientes con ubicación geográfica
- ✅ Plantillas de tareas con subtareas y materiales
- ✅ Sistema de usuarios con roles
- ✅ Control de acceso por roles

#### Preparado para backend real ✅

- ✅ JWT sessions (`user_sessions`)
- ✅ Multi-warehouse futuro (`inventory_stock.warehouse_id`)
- ✅ Sincronización stock con despachos (trigger sugerido)
- ✅ Upload de archivos (solo URLs en BD)
- ✅ Validación de permisos server-side
- ✅ Auditoría completa (created_at, updated_at, deleted_at)

#### Supuestos tomados 📝

1. **Ubicaciones independientes:** Ticket/tarea puede ocurrir en ubicación NO registrada del cliente
2. **Despachos sin solicitud:** Depósito puede despachar sin solicitud formal previa
3. **Subtareas sin template:** Usuario puede crear tarea ad-hoc sin template
4. **Secuencia simple:** Subtarea N bloquea a N+1 (no se necesita grafo complejo de dependencias)
5. **Asignaciones históricas:** Cada cambio de asignado queda registrado para auditoría

---

## 🎯 Decisiones Clave Explicadas

### 1. Ubicaciones normalizadas (no embebidas)

**Era:** `Clientes.latitud/longitud`  
**Es ahora:** `locations` tabla independiente + `client_locations` (many-to-many)

**Por qué:**
- Cliente tiene múltiples sedes/oficinas
- Ticket/tarea puede tener ubicación que NO es sede del cliente
- Reutilización de ubicaciones

---

### 2. Separación catálogo vs stock vs movimientos

**Era:** `Productos.stock INT` (todo mezclado)  
**Es ahora:**
- `inventory_products` (catálogo/definición)
- `inventory_stock` (stock actual)
- `inventory_movements` (trazabilidad completa)

**Beneficios:**
- Trazabilidad histórica
- Detección de discrepancias
- Reportes de consumo
- Preparado para multi-warehouse

---

### 3. Secuencia de subtareas con order_index

**Decisión:** `subtasks.order_index INT` define orden (0, 1, 2, ...)  
**Regla:** Subtarea N+1 no puede iniciarse hasta que N esté completa

**Alternativa rechazada:** Linked list con `previous_subtask_id` (frágil, complicado)

---

### 4. Solicitudes vs Despachos separados

**Decisión:** No asumir que todo despacho viene de solicitud previa

**Estructura:**
```
ticket_inventory_requests (solicitud técnico)
    └── ticket_inventory_request_items

ticket_dispatches (despacho depósito)
    └── ticket_dispatch_items
    └── request_id (NULLABLE - puede despachar sin solicitud)
```

**Beneficio:** Flexibilidad operativa real

---

### 5. Historial de asignaciones + cache

**Patrón:**
- Historial: `subtask_assignments`, `ticket_assignments`
- Cache: `current_assigned_user_id` en `subtasks`, `tickets`

**Por qué ambos:**
- Cache → performance (evita JOIN constante)
- Historial → trazabilidad completa

---

## 📊 Comparativa: Original vs Propuesto

| Aspecto | schema.sql original | schema-propuesto.sql | Mejora |
|---------|---------------------|---------------------|--------|
| **Tablas** | 6 tablas | 38 tablas | ✅ Completo |
| **Ubicaciones** | Embebidas | Normalizadas | ✅ Many-to-many |
| **Tareas** | ❌ No existe | 9 tablas | ✅ Core funcional |
| **Tickets** | ❌ No existe | 11 tablas | ✅ Flujo operativo |
| **Stock** | 1 tabla mezclada | 3 tablas separadas | ✅ Trazabilidad |
| **Roles** | VARCHAR libre | Tabla normalizada | ✅ Integridad |
| **Normalización** | Violaciones | BCNF | ✅ Integridad |
| **Auditoría** | Parcial | Completa | ✅ Timestamps |
| **Soft deletes** | ❌ No | ✅ Sí | ✅ Trazabilidad |

---

## 🚀 Próximos Pasos

### Fase 1: Validación (1-2 días)
- [ ] Revisar esquema con equipo técnico
- [ ] Validar reglas de negocio
- [ ] Ajustar si surgen nuevos requisitos

### Fase 2: Implementación DB (1 semana)
- [ ] Crear base PostgreSQL
- [ ] Ejecutar `schema-propuesto.sql`
- [ ] Insertar datos de prueba
- [ ] Validar integridad referencial

### Fase 3: Backend (2-4 semanas)
- [ ] Elegir stack (Django/FastAPI/NestJS)
- [ ] Implementar modelos ORM
- [ ] Crear endpoints REST
- [ ] Implementar JWT auth
- [ ] Upload de archivos

### Fase 4: Migración Frontend (1-2 semanas)
- [ ] Reemplazar `Mock*Service` por `*ApiService`
- [ ] Interceptors JWT
- [ ] Guards de autenticación
- [ ] Eliminar localStorage

---

## 📖 Cómo Usar Esta Documentación

1. **Para entender rápido:**  
   → Leer [RESUMEN_EJECUTIVO_BDD.md](./RESUMEN_EJECUTIVO_BDD.md)

2. **Para implementar backend:**  
   → Ejecutar [schema-propuesto.sql](./schema-propuesto.sql)  
   → Seguir [MAPEO_FRONTEND_A_DB.md](./MAPEO_FRONTEND_A_DB.md) para endpoints

3. **Para revisar decisiones:**  
   → Leer [DECISIONES_DE_DISEÑO_BDD.md](./DECISIONES_DE_DISEÑO_BDD.md)

4. **Para visualizar relaciones:**  
   → Abrir [diagrama_de_entidades_propuesto.puml](./diagrama_de_entidades_propuesto.puml) en PlantUML viewer

---

## ✨ Conclusión

Este esquema de base de datos:

✅ **Es completo:** Cubre todos los requisitos funcionales  
✅ **Es consistente:** Normalizado hacia BCNF con trazabilidad completa  
✅ **Es extensible:** Preparado para evolución sin rupturas  
✅ **Es pragmático:** No normaliza de más donde no aporta  
✅ **Es auditable:** Historial completo de cambios  
✅ **Es claro:** Separación explícita de conceptos  

**Puede implementarse directamente en producción** una vez validado por el equipo técnico.

---

**Fuentes:**  
- `FRONTEND_CURRENT_STATE.md` (contexto funcional)  
- `schema.sql` (intenciones iniciales)

**Contacto:**  
Para consultas técnicas, revisar la documentación detallada en cada archivo.
