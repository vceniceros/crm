Quiero que implementes el flujo real de tareas y subtareas del CRM siguiendo la arquitectura backend ya existente, manteniendo separación de responsabilidades, buenas prácticas, código claro y sin reescribir innecesariamente partes ajenas al dominio de tareas.

## Objetivo funcional

Implementar el módulo de templates de tareas y la operación real de tareas instanciadas.

### Flujo funcional esperado

1. Un usuario con rol administrador/ejecutivo puede crear un `TaskTemplate`.
2. Un template define:
   - datos base de la tarea
   - lista ordenada de subtareas
   - rol responsable de cada subtarea
   - opcionalmente usuario responsable por defecto
   - ítems de cada subtarea
   - tipo de cada ítem (`checkbox`, `text`, y dejar diseño preparado para tipos futuros)
   - obligatoriedad de cada ítem
   - obligatoriedad de comentario de cierre
   - política de asignación siguiente:
     - automática al siguiente rol
     - automática a usuario por defecto
     - manual obligatoria al cerrar
3. Cuando un admin/ejecutivo crea una `Task` desde un template:
   - se instancia toda la estructura del template
   - se generan sus subtareas e ítems reales
   - se activa la primera subtarea
   - si el template define usuario responsable concreto, asignar a ese usuario
   - si solo define rol y no usuario, dejar la subtarea como "sin asignar" para ese rol
4. Los usuarios del rol correspondiente pueden:
   - ver tareas asignadas a ellos
   - ver tareas sin asignar de su rol
   - tomar una tarea sin asignar
5. Cada subtarea se opera como checklist:
   - los ítems checkbox se marcan/desmarcan
   - los ítems texto aceptan valor textual
   - no se puede cerrar una subtarea si faltan ítems obligatorios
6. Al final de la subtarea debe existir:
   - campo obligatorio de comentario de cierre / observaciones
   - acción elegible desde botón con opciones:
     - `close_subtask`
     - `reject_subtask`
     - `put_on_hold`
7. Todas las acciones anteriores requieren comentario obligatorio explicando motivo.
8. Al cerrar una subtarea correctamente:
   - registrar transición
   - cerrar subtarea actual
   - desbloquear siguiente subtarea
   - asignarla según reglas del template
9. Si la siguiente subtarea tiene solo rol y no usuario:
   - debe quedar visible en bandeja de "sin asignar" de ese rol
10. Debe quedar trazabilidad/auditoría de:
    - quién tomó una tarea
    - quién completó ítems
    - quién cerró/rechazó/puso en pendiente
    - comentario obligatorio asociado a cada transición

---

## Decisiones de diseño obligatorias

### 1. Estructura del dominio
Mantener separación entre:
- template de tarea
- instancia real de tarea
- subtarea instanciada
- ítems instanciados
- asignaciones
- comentarios
- historial de transiciones / auditoría

No mezclar plantilla con ejecución operativa.

### 2. Patrones de diseño a aplicar

#### Patrón principal: State
Usar `State` para modelar el ciclo de vida de una subtarea.

Estados mínimos sugeridos:
- `pending_assignment`
- `assigned`
- `in_progress`
- `completed`
- `rejected`
- `on_hold`

Cada estado debe definir qué acciones están permitidas y cómo transicionar.

Evitar resolver el flujo con grandes `if/else` o `switch` dispersos.

#### Validaciones: Chain of Responsibility
Implementar validaciones encadenables para acciones de subtarea, por ejemplo:
- permisos del usuario
- estado actual válido
- ítems obligatorios completos
- comentario obligatorio presente
- reglas de asignación siguiente
- integridad de transición

Cada validador debe ser reutilizable y desacoplado.

#### Reglas variables: Strategy
Usar `Strategy` para encapsular reglas variables, por ejemplo:
- validación por tipo de ítem
- política de asignación siguiente
- resolución automática de responsable
- reglas específicas por tipo de subtarea

No hardcodear estas variantes dentro del service principal.

#### Flujo común de acciones: Template Method
Modelar el algoritmo común de acciones operativas (`close`, `reject`, `on_hold`) con un esqueleto compartido:
- validar permisos
- validar estado
- validar payload
- aplicar regla específica
- persistir comentario
- persistir transición
- auditar
- reasignar / desbloquear siguiente

Evitar duplicación entre acciones.

### 3. Composite y Builder
- Mantener idea de `Composite` para `Task -> Subtasks -> Items`
- Mantener idea de `Builder` o ensamblador para crear una `Task` real a partir de un `TaskTemplate`

---

## Requisitos técnicos

- Seguir la arquitectura existente del backend
- No romper contratos existentes si ya hay endpoints o modelos parciales
- Agregar solo lo necesario
- Mantener nombres claros y consistentes
- No meter lógica de negocio compleja en controllers
- Services deben orquestar
- Reglas de dominio deben quedar encapsuladas
- Preparar base para futuras extensiones:
  - nuevos tipos de ítem
  - nuevas acciones
  - nuevos estados
  - nuevas políticas de asignación

---

## Entidades / componentes esperados

Proponer e implementar, ajustando a la arquitectura real existente:

- `TaskTemplate`
- `TaskTemplateSubtask`
- `TaskTemplateItem`
- `Task`
- `Subtask`
- `SubtaskItemValue`
- `SubtaskAssignment`
- `SubtaskTransition`
- `TaskComment`
- `TaskAuditEvent`

Y servicios similares a:
- `CreateTaskFromTemplateService`
- `ClaimUnassignedSubtaskService`
- `ExecuteSubtaskActionService`
- `AdvanceTaskFlowService`

---

## API esperada

Diseñar endpoints coherentes con la arquitectura actual para:

- crear template
- listar templates
- crear tarea desde template
- listar tareas asignadas al usuario
- listar tareas sin asignar por rol del usuario
- tomar tarea/subtarea sin asignar
- obtener detalle operativo de tarea/subtarea
- guardar progreso de ítems
- ejecutar acción sobre subtarea (`close`, `reject`, `on_hold`)

No inventar endpoints innecesarios fuera de este alcance.

---

## Reglas operativas importantes

- No se puede cerrar subtarea si faltan ítems obligatorios
- `reject` y `on_hold` también exigen comentario obligatorio
- La transición debe quedar auditada siempre
- La siguiente subtarea no debe activarse si la actual no quedó correctamente cerrada
- Si una subtarea está "sin asignar", solo usuarios del rol correcto deben poder tomarla
- Administradores pueden consultar todo el flujo
- Preparar el diseño para que más adelante existan permisos finos por rol

---

## Entregable esperado

1. Explicar brevemente el diseño elegido y cómo aplicaste:
   - State
   - Chain of Responsibility
   - Strategy
   - Template Method
2. Mostrar estructura de modelos/entidades
3. Implementar services y endpoints mínimos funcionales
4. Incluir validaciones y transiciones reales
5. Dejar comentarios breves donde la intención no sea obvia
6. No reescribir módulos no relacionados
7. Respetar arquitectura existente
8. Indicar riesgos, TODOs y extensiones futuras solo si son realmente relevantes