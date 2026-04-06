# CRM YCC

## Descripción general

CRM interno para YCC orientado a centralizar y simplificar la gestión operativa de la empresa, desde el ingreso de dispositivos al depósito hasta su instalación en cliente y el seguimiento posterior.

El sistema busca cubrir el flujo completo de trabajo de manera clara, intuitiva y eficiente, evitando complejidad innecesaria y priorizando la usabilidad para personal de distintas áreas, incluyendo depósito, administración, soporte y técnicos de instalación.

No se plantea como un CRM genérico ni como una plataforma sobrecargada de funcionalidades. Su objetivo es adaptarse a la operatoria real de YCC.

---

## Objetivo del proyecto

Construir una plataforma interna que permita:

- registrar y seguir el ciclo de vida completo de dispositivos, equipos e insumos
- centralizar la información operativa en un solo sistema
- mejorar la trazabilidad de movimientos, asignaciones e instalaciones
- reducir errores manuales, pérdidas de contexto y uso de planillas dispersas
- facilitar el trabajo diario de usuarios no especializados en sistemas
- servir como base para una futura evolución hacia uso externo o móvil

---

## Problemas que debe resolver

Actualmente, la operación de este tipo de flujo suele presentar uno o más de estos problemas:

- información repartida entre distintas personas, mensajes o planillas
- dificultad para saber dónde está un equipo y en qué estado se encuentra
- poca trazabilidad entre compra, ingreso, stock, asignación, salida e instalación
- procesos dependientes de conocimiento informal
- exceso de carga manual y repetitiva
- dificultad para auditar movimientos o responsables
- herramientas genéricas que no reflejan el flujo real de trabajo
- sistemas con sobreingeniería o funcionalidades irrelevantes para el uso diario
- fallos en entregas debido a la falta de procesos preestablecidos
- repeticion de visitas tecnicas a razon de subsanar fallos durante instalacion

Este CRM debe resolver esos puntos con foco en la operación real de YCC.

---

## Alcance inicial

En su primera etapa, el sistema estará orientado a cubrir principalmente:

- ingreso de mercadería o dispositivos al depósito
- registro de lotes, series o identificadores relevantes
- control de stock y movimientos internos
- reserva o asignación de equipos para clientes, órdenes o instalaciones
- salida de equipos de depósito
- seguimiento de tareas técnicas e instalaciones
- asociación de dispositivos instalados a cliente, unidad o servicio
- historial operativo y trazabilidad de cada equipo
- base inicial para soporte técnico posterior

---

## Fuera de alcance inicial

Para evitar sobreingeniería, en la primera etapa no se priorizarán:

- automatizaciones complejas de workflow tipo BPM
- motor genérico de procesos
- funcionalidades masivas no alineadas con la operación real
- app móvil nativa
- integraciones externas no esenciales
- dashboards avanzados si no aportan valor operativo inmediato
- personalizaciones excesivas por usuario o sector

Estas capacidades podrán evaluarse más adelante, una vez consolidado el núcleo operativo.

---

## Principios del sistema

### 1. Usabilidad por encima de complejidad
El sistema debe poder ser utilizado por personal de depósito, técnicos y administración sin necesidad de conocimientos técnicos avanzados.

### 2. Operación real por encima de abstracción
La plataforma debe modelar el flujo real de trabajo de YCC, no forzar a la empresa a adaptarse a un software genérico.

### 3. Trazabilidad completa
Cada equipo, movimiento, asignación o instalación debe poder seguirse de punta a punta.

### 4. Eficiencia operativa
Cada pantalla y cada acción deben reducir pasos, errores y tiempos innecesarios.

### 5. Sin sobreingeniería
No se agregarán capas, patrones o módulos que no aporten valor concreto al problema actual.

### 6. Base sólida para crecer
La arquitectura debe permitir evolucionar en el futuro sin comprometer la simplicidad inicial.

---

## Usuarios previstos

El sistema deberá contemplar, al menos, los siguientes perfiles:

- personal de depósito
- administración / operaciones
- técnicos instaladores
- soporte técnico
- supervisión / coordinación
- perfiles administradores del sistema

Cada perfil tendrá permisos y vistas acordes a su tarea real.

---

## Responsabilidades del sistema

Entre sus responsabilidades principales se encuentran:

- centralizar la información operativa del circuito interno
- registrar entidades clave del negocio y su historial
- reflejar estados operativos de forma clara y simple
- permitir seguimiento y trazabilidad de equipos y tareas
- servir como fuente confiable de consulta para distintas áreas
- mantener consistencia entre stock, asignaciones, salidas e instalaciones
- reducir dependencia de registros manuales externos
- facilitar auditoría operativa y análisis posterior

---

## Módulos funcionales esperados

La definición final podrá ajustarse durante el diseño, pero inicialmente se proyectan módulos como:

- clientes
- dispositivos / equipos
- depósito / stock
- movimientos de inventario
- compras / ingresos
- asignaciones / reservas
- instalaciones
- soporte / incidencias
- usuarios, roles y permisos
- auditoría / historial

---

## Tecnologías previstas

### Backend
- Python
- FastAPI

### Base de datos
- PostgreSQL

### Frontend
Pendiente de definición final.  
Actualmente se evalúan alternativas como:

- React + TypeScript
- Vue 3 + TypeScript
- Angular

La decisión deberá priorizar:

- simplicidad de desarrollo
- buena experiencia de usuario
- facilidad de mantenimiento
- compatibilidad futura con una webapp móvil

---

## Criterios de éxito

Se considerará que el proyecto cumple su propósito inicial si logra:

- representar correctamente el flujo operativo real de YCC
- ser entendible y usable por usuarios no técnicos
- reducir pasos manuales y errores frecuentes
- mejorar trazabilidad de equipos y tareas
- centralizar la operación sin depender de planillas paralelas
- ofrecer una base clara y mantenible para futuras ampliaciones

---

## Arquitectura base esperada

El sistema estará dividido, en principio, en:

- **frontend web** para operación diaria
- **backend API** para lógica de negocio
- **base de datos relacional** para persistencia y trazabilidad

Lineamientos iniciales:

- frontend desacoplado del backend
- API orientada a dominio y casos reales de uso
- modelo de permisos por roles
- trazabilidad de eventos críticos
- diseño simple y mantenible

---

## Estado del proyecto

Proyecto en etapa inicial de definición funcional y arquitectónica.

Pendientes principales:

- definición del frontend
- diseño de módulos y entidades iniciales
- definición del MVP
- diseño de permisos y roles
- priorización del flujo operativo principal
- estructura base del repositorio

---

## Próximos pasos sugeridos

1. definir el MVP operativo real
2. mapear el flujo completo actual de YCC
3. identificar entidades principales del dominio
4. definir estados operativos clave
5. elegir stack de frontend
6. diseñar arquitectura inicial del backend
7. crear backlog funcional por etapas

---

## Sugerencia de estructura futura del repositorio

```text
/
├─ backend/
├─ frontend/
├─ docs/
├─ scripts/
└─ README.md