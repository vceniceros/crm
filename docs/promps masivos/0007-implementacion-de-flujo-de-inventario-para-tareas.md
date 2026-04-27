Quiero implementar el **flujo completo real de productos/equipos en tareas y tickets**, cableado de punta a punta:

- frontend real
- backend real
- persistencia real en base de datos
- sin mocks
- respetando la estructura actual del proyecto
- respetando los patrones de diseño ya usados en el módulo
- con cambios mínimos pero completos

## Objetivo

Este flujo debe cubrir:

1. **Productos mínimos requeridos en templates**
2. **Despacho real de productos/equipos a una tarea**
3. **Registro de serial / código de barras por parte de depósito**
4. **Confirmación por parte del técnico de campo**
5. **Solicitud adicional de productos desde una tarea o ticket cuando el técnico ya está en el lugar**
6. **Despacho posterior desde depósito de esa solicitud**
7. **Trazabilidad completa del flujo**

No quiero una implementación decorativa.
No quiero mocks.
Quiero el frontend cableado al backend y el backend hablando con la base real.

---

## Regla de modelado principal

Separar explícitamente estos niveles:

### A. Requerimiento mínimo del template
Qué productos/materiales/equipos exige ese tipo de trabajo para existir como template.

Ejemplo:
- Template “Instalación DVR Vacron” requiere:
  - 1 DVR Vacron
  - 1 kit de cables
  - 1 módulo wifi opcional o requerido según template real

Esto pertenece al template y debe modelarse como requerimiento mínimo.

### B. Despacho/entrega real a una tarea
Qué producto real fue despachado a esa tarea específica.

Ejemplo:
- se despachó un DVR con serial/código de barras concreto
- se despachó un accesorio concreto
- quedó asociado a esa tarea

Esto no es template: es ejecución real.

### C. Solicitud adicional en campo
Qué producto adicional solicita el técnico cuando ya está ejecutando una tarea o ticket.

Ejemplo:
- falta un módulo
- se dañó un cable
- necesita un repuesto no previsto

Esto debe quedar como flujo formal:
- request
- items
- estado
- revisión/atención desde depósito
- despacho posterior

---

## Flujo funcional exacto esperado

# 1. Templates: productos mínimos requeridos

Los usuarios `admin_crm` / `ejecutivo` al crear o editar templates pueden definir:

- productos mínimos requeridos
- cantidad mínima requerida
- nota opcional

Esto debe quedar persistido realmente y visible en:
- create/edit template
- detail template
- create task from template
- task detail

Reutilizar el soporte existente tipo `template_materials` si ya existe.
No crear una segunda solución paralela.

---

# 2. Creación de tarea desde template

Cuando se crea una tarea desde template:
- la tarea debe heredar visual y funcionalmente la lista de productos mínimos requeridos
- no hace falta reservar stock automáticamente en esta etapa, salvo que ya exista soporte claro
- sí debe quedar visible que la tarea requiere esos productos

---

# 3. Depósito: despacho real de productos/equipos a la tarea

En las tareas donde corresponda al rol `encargado_deposito`, el operario de depósito debe poder:

- ver productos mínimos requeridos por el template
- agregar a la tarea productos realmente despachados
- cargar:
  - producto
  - cantidad
  - serial o código de barras si aplica
  - observaciones si corresponde

### Casos importantes
- hay productos genéricos sin serial
- hay equipos concretos que sí requieren serial o barcode obligatorio
- el flujo debe soportar ambos

### Requisito funcional
Para equipos como DVR Vacron, el operario de depósito debe poder registrar:
- serial
- código de barras
- o el identificador real definido por el sistema

Eso debe quedar asociado a la tarea y trazable.

### Regla de diseño
Este comportamiento debe abstraerse como parte del flujo de materiales/equipos.
No quiero lógica dispersa ad hoc en cada componente.

---

# 4. Técnico de campo: recepción / entrega / instalación

El técnico de campo, desde la tarea, debe poder ver claramente:

- qué productos/equipos fueron despachados a esa tarea
- qué seriales/códigos se cargaron
- cuál era el mínimo requerido por template
- qué falta o qué ya fue cubierto

Además, debe poder marcar al menos una confirmación operativa tipo:
- equipo recibido
- equipo entregado
- equipo instalado

No inventar semántica si ya hay una mejor en backend, pero debe existir confirmación real por técnico.

Esa confirmación debe quedar persistida y auditada.

---

# 5. Técnico en campo: solicitud adicional de productos para tarea o ticket

Cuando el técnico ya está en el lugar, debe poder solicitar productos adicionales desde:

- una tarea
- un ticket

### Requisitos funcionales
El técnico debe poder:
- crear una solicitud
- agregar productos requeridos
- indicar cantidad
- agregar observación/motivo
- enviarla a depósito

### El flujo debe soportar:
- request con estado
- items del request
- revisión/atención por depósito
- despacho posterior

### Reglas
No mocks.
No simulaciones.
Quiero flujo real y persistido.

---

# 6. Depósito: atención de solicitudes adicionales

Depósito debe poder:

- ver solicitudes de productos abiertas
- distinguir si vienen de tarea o ticket
- revisar items solicitados
- aprobar/despachar
- registrar qué se despachó realmente
- dejar observación

Si ya existe una estructura en tickets para inventory requests/dispatches, reutilizarla o extenderla con criterio.
No duplicar un flujo paralelo si el dominio ya tiene una base reutilizable.

---

## Requisitos de arquitectura

## A. Patrones de diseño obligatorios

Seguir los patrones ya establecidos en el proyecto donde aplique.

### 1. Facade
Usar fachadas para encapsular subsistemas complejos del flujo de materiales/equipos.

Ejemplos esperados:
- `TaskMaterialFlowFacade`
- `InventoryRequestFacade`
- o nombres equivalentes consistentes con el proyecto

La fachada debe simplificar el uso desde frontend/backend application layer.

### 2. Strategy
Usar `Strategy` para reglas variables, por ejemplo:
- validación de productos que requieren serial vs no requieren serial
- resolución de comportamiento según tipo de flujo:
  - task template required materials
  - task dispatch
  - field request
  - ticket request

Evitar `if/else` repartidos por todo el sistema.

### 3. Template Method
Usar `Template Method` si ya encaja con la lógica de acciones repetidas:
- validar
- persistir
- auditar
- devolver resultado

### 4. State
Si el flujo de requests/despachos usa estados, modelarlo con el mismo criterio ya usado en subtareas/acciones cuando sea razonable.
No meter enums sueltos sin control si ya existe una mecánica mejor.

---

## B. Backend

Quiero implementación real en backend.

### B1. Templates
Conectar realmente:
- productos mínimos requeridos del template
- create/update/get template
- validación
- persistencia

### B2. Tareas
Agregar soporte real para:
- materiales/equipos despachados a una tarea
- serial/barcode
- confirmación técnica de recepción/entrega/instalación

### B3. Requests desde campo
Agregar o reutilizar flujo real para:
- request de producto desde tarea
- request de producto desde ticket
- items del request
- estados
- despacho posterior

### B4. Base de datos
No usar estructuras en memoria.
Persistir en la BDD real.

Si ya existen tablas equivalentes en schema o backend:
- reutilizarlas
- extenderlas
- no duplicarlas

Si falta delta mínimo:
- proponerlo e implementarlo con cambios mínimos y claros

---

## C. Frontend

Quiero vistas reales, conectadas al backend real.

### C1. Templates
En create/edit template agregar sección:
### “Productos mínimos requeridos”

Debe permitir:
- seleccionar producto del catálogo
- indicar cantidad mínima
- agregar varios
- quitar
- evitar duplicados
- persistir realmente

### C2. Task detail / task operational view
Mostrar claramente:
- productos mínimos requeridos por template
- productos realmente despachados a la tarea
- serial/barcode si aplica
- estado de confirmación por técnico

### C3. Depósito en tareas
Vista/acción para que depósito pueda:
- agregar producto despachado a la tarea
- cargar serial/barcode
- dejar observación
- confirmar despacho real

### C4. Técnico en tareas
Vista/acción para que técnico pueda:
- ver productos despachados
- ver seriales/códigos
- marcar confirmación de recepción/entrega/instalación
- solicitar productos adicionales si hace falta

### C5. Técnico en tickets
Vista/acción para solicitar productos adicionales desde ticket también

### C6. Depósito: bandeja de requests
Pantalla para que depósito vea y atienda solicitudes adicionales de:
- tareas
- tickets

---

## D. UX/UI

La UI debe ser operativa, clara y simple.

### Reglas
- no marketinera
- no sobreingeniería
- no modales anidados innecesarios
- no esconder acciones clave
- los seriales/barcodes deben verse claramente
- el técnico debe entender qué recibió y qué falta
- depósito debe entender qué requiere serial y qué no

### Validaciones visibles
- producto faltante
- cantidad inválida
- serial obligatorio faltante si aplica
- duplicado inválido
- error API
- request inválido

---

## E. Requisitos de dominio importantes

### Serial / barcode
No todos los productos lo requieren.

Necesito que el sistema soporte productos/equipos que:
- sí requieren identificación unitaria
- no la requieren

La validación no debe estar hardcodeada en el componente.
Debe estar abstraída y gobernada por backend + estrategia si corresponde.

### Trazabilidad
Todo debe quedar trazable:
- quién agregó producto requerido al template
- quién despachó qué a la tarea
- qué serial/código se cargó
- qué confirmó el técnico
- qué pidió adicionalmente el técnico
- qué atendió depósito

### Coherencia task/ticket
Si ya existe flujo de inventory requests en tickets, reutilizarlo como base conceptual.
No quiero dos dominios inconsistentes para lo mismo.

---

## F. Entregable esperado

Quiero que entregues implementación real y concreta de:

### Backend
1. modelos/entidades/repositories/services/facades necesarios
2. endpoints reales
3. validaciones
4. persistencia en BDD
5. si hace falta, delta SQL mínimo

### Frontend
1. secciones y vistas reales
2. formularios conectados
3. servicios conectados al backend
4. visualización de materiales requeridos
5. flujo de despacho
6. flujo de request adicional
7. flujo de confirmación técnica

### Además
- lista de archivos modificados
- qué reutilizaste
- qué abstrajiste con Facade + Strategy
- qué quedó explícitamente fuera de alcance si algo se deja para después

---

## Restricciones finales

- No tocar frontend fuera de este flujo salvo integración mínima necesaria.
- No rehacer inventario entero.
- No meter mocks.
- No dejar solo frontend preparado.
- No dejar solo backend preparado.
- Quiero flujo real end-to-end.
- Respetar siempre la estructura actual del proyecto.
- Respetar patrones ya usados en el módulo.
- No crear una segunda solución paralela si ya existe una base en tasks/tickets/inventory.

## Nota final importante

Quiero que esto quede cubierto de punta a punta:

- admin define productos mínimos en template
- depósito registra productos/equipos reales despachados a tarea con serial/barcode si aplica
- técnico visualiza y confirma recepción/entrega/instalación
- técnico puede solicitar productos adicionales desde tarea o ticket
- depósito atiende esas solicitudes
- todo queda persistido y trazable