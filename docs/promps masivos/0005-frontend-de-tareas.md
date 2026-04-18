Quiero que implementes las **vistas frontend reales del módulo de tareas** del CRM, siguiendo estrictamente la arquitectura ya existente del proyecto y consumiendo el backend real ya implementado.

## Contexto y objetivo

Este módulo debe cubrir dos grandes flujos:

1. **Creación y administración de templates de tareas**
2. **Operación real de tareas/subtareas por roles**

El frontend debe respetar el flujo funcional ya definido y no inventar lógica paralela ni mocks innecesarios.

## Regla principal

No quiero una demo visual aislada.

Quiero vistas reales, conectadas al backend existente, orientadas a uso operativo diario, simples de entender y listas para continuar iterando.

---

## Requisitos funcionales generales

### 1. Templates de tarea
Los usuarios con rol `admin_crm` o `ejecutivo` deben poder:

- crear templates de tarea
- listar templates existentes
- ver detalle de un template
- editar template
- activar/desactivar template si ya existe esa semántica en backend
- definir:
  - nombre del template
  - descripción
  - lista ordenada de subtareas
  - para cada subtarea:
    - título
    - descripción
    - orden
    - rol responsable
    - usuario responsable por defecto si aplica
    - política de asignación siguiente
    - si requiere comentario obligatorio al cerrar
    - lista de ítems
  - para cada ítem:
    - label
    - tipo (`checkbox` o `text`)
    - obligatoriedad
    - orden

### 2. Creación de tarea desde template
Los usuarios `admin_crm` o `ejecutivo` deben poder:

- crear una tarea real a partir de un template
- cargar la información inicial requerida
- asociar cliente
- asociar ubicación si corresponde
- confirmar creación
- ver que la tarea queda instanciada y asignada según reglas del template

### 3. Operación real de subtareas
Los usuarios operativos deben poder:

- ver tareas/subtareas asignadas a ellos
- ver subtareas sin asignar de su rol
- tomar una subtarea sin asignar
- abrir una subtarea y operar sus ítems
- completar checklist de ítems
- completar campos de texto
- guardar progreso
- escribir comentario obligatorio de cierre/observaciones
- ejecutar acción final:
  - cerrar subtarea
  - rechazar
  - poner en pendiente

### 4. Reasignación / avance
Al finalizar una subtarea, el usuario debe poder ver claramente:

- a quién o a qué rol pasa la siguiente etapa
- si la siguiente asignación es automática o manual
- si queda sin asignar para el siguiente rol
- si requiere intervención administrativa

No inventar lógica en frontend: usar la información real del backend y mostrarla correctamente.

---

## Flujo funcional específico que debe reflejar la UI

### Caso ejemplo: instalación de un Vacron

Ejemplo operativo que la UI debe soportar de punta a punta:

- admin/ejecutivo crea una tarea desde un template de instalación Vacron
- la primera subtarea puede ser “despachar en depósito”
- esa subtarea queda para el rol `encargado_deposito`
- si no tiene usuario puntual asignado, debe aparecer en una bandeja de “sin asignar” para ese rol
- alguien de depósito la toma
- entra a la subtarea
- completa ítems de checklist y texto
  - ejemplo texto: código de DVR
  - ejemplo checkbox: tiene módulo wifi
- al final completa comentario obligatorio
- usa botón de acción con opciones:
  - cerrar subtarea
  - rechazar
  - poner en pendiente
- todas esas acciones requieren comentario
- una vez cerrada, la siguiente subtarea pasa al siguiente rol o usuario definido
- si no queda asignada a usuario específico, debe aparecer como sin asignar para el rol siguiente

La UI tiene que hacer esto entendible y usable para usuarios no técnicos.

---

## Alcance exacto del frontend a implementar

## A. Pantallas de templates

### A1. Listado de templates
Crear vista de listado con:
- tabla o lista clara
- nombre
- descripción breve
- estado
- cantidad de subtareas
- acciones: ver, editar, crear tarea desde template

### A2. Formulario de creación/edición de template
Crear una vista robusta para armar un template completo.

Debe permitir:
- datos generales del template
- agregar/eliminar/reordenar subtareas
- dentro de cada subtarea:
  - editar datos base
  - agregar/eliminar/reordenar ítems
- dentro de cada ítem:
  - definir tipo checkbox/text
  - label
  - requerido sí/no

Importante:
- no usar UX confusa
- no hacer un formulario monstruoso ilegible
- preferir bloques o cards por subtarea
- que el orden de subtareas e ítems sea visible y fácil de modificar

### A3. Vista detalle de template
Mostrar template completo en modo lectura:
- encabezado
- subtareas ordenadas
- ítems de cada subtarea
- rol responsable
- reglas de cierre y asignación

---

## B. Pantallas operativas de tareas

### B1. Bandeja de tareas/subtareas
Implementar una vista operativa con pestañas o secciones claras:

- Mis tareas / subtareas asignadas
- Subtareas sin asignar de mi rol
- Tareas creadas por mí o que estoy siguiendo (para admin/ejecutivo)
- Opcional si ya existe backend: filtros por estado

Cada fila/card debe mostrar al menos:
- título de tarea
- subtarea actual
- cliente
- template origen si aplica
- rol responsable
- usuario asignado si existe
- estado
- acciones rápidas: ver detalle / tomar / continuar

### B2. Vista detalle operativo de tarea
Mostrar:
- datos generales de la tarea
- cliente
- ubicación
- template origen
- estado general
- timeline o lista de subtareas

Cada subtarea debe verse con su estado:
- bloqueada
- pendiente de asignación
- asignada
- en progreso
- completada
- rechazada
- en espera

La subtarea activa debe destacarse claramente.

### B3. Vista de ejecución de subtarea
Esta es la vista más importante.

Debe mostrar:
- título de subtarea
- descripción
- tarea padre
- cliente
- responsable actual
- estado
- checklist / formulario dinámico según ítems

Para cada ítem:
- si es `checkbox`, mostrar checkbox claro
- si es `text`, mostrar input o textarea según convenga
- marcar visualmente cuáles son obligatorios

Al final:
- sección visible de comentario obligatorio
- placeholder explícito tipo:
  - “Comentario de cierre y/o observaciones”
- botón principal con menú de acciones
  - cerrar subtarea
  - rechazar
  - poner en pendiente

No permitir UX ambigua:
- si falta comentario obligatorio o ítems requeridos, mostrar validación clara
- no esconder errores
- no permitir que el usuario piense que cerró algo cuando no pasó

### B4. Tomar subtarea sin asignar
Si una subtarea está en bandeja de “sin asignar”:
- mostrar botón “Tomar subtarea”
- luego redirigir a la vista operativa correspondiente

---

## Requisitos de UX/UI

La UI debe seguir estas premisas:

- ultra intuitiva
- operativa
- sin sobreingeniería
- clara para depósito, técnicos y admin
- usable en desktop, pero sin romper en tablet o resoluciones medias
- visualmente consistente con el resto del CRM

### Reglas de diseño
- no hacer una UI “marketinera”
- no usar demasiados modales anidados
- no esconder acciones críticas en lugares raros
- priorizar lectura rápida
- priorizar flujo real sobre estética exagerada
- si una subtarea está bloqueada, debe verse como bloqueada
- si está sin asignar, debe verse como sin asignar
- si está asignada a otro usuario, debe verse claramente

### Validaciones visibles
- ítem obligatorio faltante
- comentario obligatorio faltante
- error del backend
- acción inválida por estado
- problemas de asignación

---

## Requisitos técnicos

### 1. Consumir backend real
No usar mocks permanentes.
Consumir los endpoints reales ya implementados para:
- listar templates
- crear template
- editar template
- crear tarea desde template
- listar tareas/subtareas
- obtener detalle
- tomar subtarea
- guardar progreso
- ejecutar acciones

Si falta algún endpoint o contrato menor, documentarlo de forma puntual y mínima, sin reinventar backend completo.

### 2. Mantener arquitectura frontend existente
Seguir el patrón ya definido en el proyecto:
- módulos
- componentes
- servicios
- modelos/interfaces
- guards/interceptors si ya existen
- routing existente

No reestructurar todo el frontend.

### 3. Formularios
Usar el enfoque ya estándar del proyecto para formularios.
Preferir componentes reutilizables donde tenga sentido, pero sin sobreabstractar.

### 4. Estado
No meter una solución compleja de estado global si no hace falta.
Resolver con servicios/componentes de forma clara y mantenible.

### 5. Tipado
Definir interfaces/types claros para:
- template
- subtask template
- item template
- task
- subtask
- item progress
- comments
- transitions si aplica a la UI

### 6. Errores
Manejar correctamente:
- loading
- empty states
- errores de API
- validaciones

---

## Comportamientos esperados

### Templates
- crear subtarea nueva
- duplicar subtarea si eso simplifica armado
- mover subtarea arriba/abajo
- mover ítem arriba/abajo
- eliminar subtarea/ítem con confirmación simple

### Operación
- guardar progreso sin cerrar
- ejecutar acción final con comentario
- refrescar estado real luego de la acción
- mostrar feedback claro de éxito/error
- si una acción cierra y avanza flujo, reflejarlo en pantalla

---

## Roles y visibilidad

La UI debe contemplar al menos estos comportamientos:

### admin_crm / ejecutivo
- crear y editar templates
- crear tareas desde template
- ver seguimiento completo
- consultar tareas de otros

### encargado_deposito
- ver subtareas de depósito
- ver subtareas sin asignar de su rol
- tomar y ejecutar subtareas

### tecnico_campo
- ver subtareas técnicas
- tomar si aplica
- ejecutar checklist y cierre

No inventar permisos en frontend: usar el contexto ya disponible y ocultar o deshabilitar acciones según corresponda.

---

## Entregable esperado

Quiero que implementes el frontend de este módulo con cambios concretos y mínimos, entregando:

1. componentes creados/modificados
2. servicios creados/modificados
3. rutas agregadas
4. modelos/interfaces
5. pantallas funcionales conectadas al backend
6. validaciones principales
7. breve nota final indicando:
   - qué quedó funcional
   - qué dependencias menores del backend aparecieron si las hubo
   - qué mejoras futuras podrían venir después, sin implementarlas ahora

---

## Prioridad de implementación

Implementar en este orden:

### Fase 1
- listado de templates
- formulario de template
- detalle de template

### Fase 2
- crear tarea desde template
- bandeja de tareas/subtareas
- tomar subtarea sin asignar

### Fase 3
- detalle operativo de tarea
- ejecución real de subtarea con checklist/text/comment/action menu

### Fase 4
- pulido visual mínimo
- mensajes de error/empty/loading
- revisión de consistencia UX

---

## Restricciones finales

- No tocar frontend fuera de este módulo salvo integración mínima necesaria.
- No rehacer diseño general del CRM.
- No crear componentes genéricos abstractos de más.
- No usar datos mock como solución final.
- No simplificar el flujo funcional.
- No ignorar el caso de subtareas sin asignar por rol.
- No ignorar comentario obligatorio.
- No ignorar ítems tipo texto.

Quiero implementación real, concreta y mantenible.


Importante: no me entregues solo una UI linda. Quiero vistas operativas reales, conectadas al backend actual, respetando exactamente el flujo de templates → creación de task → asignación por rol/usuario → toma de subtarea → ejecución checklist/texto → comentario obligatorio → acción final → avance al siguiente responsable.