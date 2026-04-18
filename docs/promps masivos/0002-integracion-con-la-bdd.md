Actúa como un software engineer senior y auditor técnico dentro de este repositorio.

## Objetivo

Necesito que reemplaces el uso de SQLite en el backend del CRM por una base PostgreSQL en contenedor Docker para laboratorio local, con el menor impacto posible y respetando la arquitectura existente.

Debes:

1. crear un Dockerfile o estructura Docker mínima para levantar PostgreSQL para el backend del CRM
2. modificar `lab_start.bat` para que:
   - levante dicho contenedor
   - espere a que PostgreSQL esté disponible
   - ejecute las migraciones necesarias para levantar el **schema v4**
   - conecte el backend existente del CRM a dicha base
3. dejar todo consistente con el flujo de laboratorio ya existente

---

## Contexto técnico obligatorio

- SQLite NO fue una decisión de diseño formal del CRM
- PostgreSQL es el motor objetivo real para este proyecto
- El schema objetivo es **schema-propuesto-v4.sql**
- Ese schema usa características propias de PostgreSQL, por ejemplo:
  - `uuid-ossp`
  - `TIMESTAMPTZ`
  - triggers
  - `ON CONFLICT`
- Por lo tanto, SQLite no es válido ni siquiera como entorno de prueba para este flujo
- Quiero que el backend del CRM quede conectado a PostgreSQL de laboratorio

---

## Restricciones importantes

### 1. Cambios mínimos
No rehagas el proyecto.
No reestructures carpetas sin necesidad.
No cambies el backend más de lo estrictamente necesario para apuntar a PostgreSQL.

### 2. Respetar arquitectura existente
Debes inspeccionar el repo y reutilizar:
- variables de entorno existentes
- convención actual de arranque
- scripts existentes
- mecanismo actual de startup del backend
- estructura actual de laboratorio

### 3. No inventar de más
No inventes:
- rutas
- nombres de módulos
- comandos
- puertos
- migraciones
- nombres de servicio
- nombres de contenedor
si ya existen convenciones en el repo

### 4. No romper el backend actual
El backend del CRM ya existe.
Debes conectarlo a PostgreSQL, no reescribirlo.

### 5. Sin soluciones “mock”
No quiero un parche de laboratorio que simule la base.
Quiero una base PostgreSQL real, usable y consistente con el schema v4.

---

## Trabajo requerido

## A. PostgreSQL para CRM

Crea lo mínimo necesario para levantar un contenedor PostgreSQL para el CRM.

Debes evaluar qué conviene según el repo actual:

- `Dockerfile`
- `docker-compose`
- o script auxiliar con `docker run`

Pero debes priorizar:
- simplicidad
- reproducibilidad
- bajo impacto
- mantenimiento claro

### Requisitos del contenedor
- PostgreSQL real
- base dedicada al CRM
- usuario y contraseña configurables por variables de entorno o valores de laboratorio bien documentados
- persistencia razonable si ya hay una convención para ello
- puerto publicado si hace falta para inspección local

### Requisitos de inicialización
Debes revisar cómo levantar el schema v4 de forma correcta.

Opciones aceptables, según lo que exista en el repo:
1. migraciones Alembic reales
2. ejecución de `schema-propuesto-v4.sql`
3. script de bootstrap controlado

Pero debes elegir la opción **más consistente con el estado real del proyecto**.

### Regla de decisión
- Si ya existen migraciones propias del CRM para ese schema, úsalas
- Si NO existen migraciones propias suficientes, entonces usa el SQL del `schema-propuesto-v4.sql` como bootstrap explícito
- No inventes migraciones incompletas solo para “cumplir”

---

## B. Modificación de `lab_start.bat`

Debes modificar `lab_start.bat` para que haga, en orden:

1. levantar el contenedor PostgreSQL del CRM
2. esperar a que PostgreSQL acepte conexiones
3. ejecutar las migraciones o bootstrap necesarios para dejar levantado el **schema v4**
4. configurar el entorno para que el backend CRM use esa base PostgreSQL
5. levantar el backend del CRM ya existente contra esa base

### Requisitos del `.bat`
- sintaxis correcta para Windows `.bat`
- usar `call` donde corresponda
- mensajes claros por etapa
- no ocultar errores
- validar fallos básicos
- no asumir Bash ni utilidades Unix
- no hardcodear rutas absolutas de una máquina específica
- no dejar pasos manuales implícitos

### Debe quedar claro en el script
- qué variables usa
- cómo detecta disponibilidad de PostgreSQL
- cómo aplica schema/migraciones
- cómo arranca el backend

---

## C. Conexión del backend a PostgreSQL

Debes adaptar la configuración existente del backend para que use PostgreSQL en laboratorio.

Esto puede implicar, solo si realmente hace falta:
- ajustar `.env`
- ajustar `.env.example`
- ajustar lectura de `DATABASE_URL`
- ajustar config del backend

Pero siempre con cambios mínimos.

### Requisitos
- el backend debe apuntar a PostgreSQL y no a SQLite
- no quiero fallback silencioso a SQLite
- si falta configuración, el error debe ser claro
- la cadena de conexión debe seguir la convención real del proyecto

---

## D. Documentación mínima

Además del cambio de código/script, debes documentar brevemente:
- qué archivos fueron creados o modificados
- cómo se levanta PostgreSQL del CRM
- cómo se aplica el schema v4
- qué comando usa el backend para conectarse
- qué supuesto hiciste si faltaban migraciones reales

Puedes documentarlo en el archivo existente de laboratorio si ya existe, o agregar una sección breve relacionada.

---

## Criterios técnicos obligatorios

### Sobre schema v4
Debes revisar el archivo `schema-propuesto-v4.sql` real del repositorio y asegurar compatibilidad con PostgreSQL.
Si necesita extensiones como `uuid-ossp`, debes contemplarlo en el bootstrap.

### Sobre readiness de PostgreSQL
No lances migraciones apenas levantás el contenedor.
Primero espera a que la base esté disponible.
Hazlo de forma entendible y mantenible.

### Sobre backend
No toques lógica de negocio innecesariamente.
Solo ajusta lo necesario para que conecte correctamente a PostgreSQL.

### Sobre naming
Usa nombres claros y consistentes con el repo.
Evita nombres genéricos o temporales si ya hay una convención.

---

## Entregables exactos

Quiero que dejes listos:

1. archivos Docker necesarios para PostgreSQL del CRM
2. `lab_start.bat` modificado
3. configuración del backend apuntando a PostgreSQL
4. mecanismo real para aplicar `schema-propuesto-v4.sql` o migraciones equivalentes
5. breve documentación del flujo

---

## Forma de trabajo obligatoria

Antes de modificar nada:

1. inspecciona cómo arranca hoy el backend del CRM
2. inspecciona cómo se configura hoy la base de datos
3. inspecciona si ya existen Dockerfiles, compose, scripts o migraciones útiles
4. inspecciona el archivo `schema-propuesto-v4.sql`
5. decide el punto mínimo de intervención

Luego implementa.

---

## Formato de respuesta esperado

Responde exactamente en este orden:

1. **Estado actual detectado**
2. **Decisión técnica mínima aplicada**
3. **Archivos creados/modificados**
4. **Diff o contenido completo de cada archivo**
5. **Cómo funciona ahora `lab_start.bat`**
6. **Cómo se aplica el schema v4**
7. **Riesgos, supuestos y edge cases**
8. **Checklist de validación**

---

## Regla final

Está prohibido dejar al backend del CRM apuntando a SQLite en este flujo de laboratorio.
Está prohibido inventar una solución “parecida”.
Quiero una integración real con PostgreSQL, mínima, reproducible y alineada con el schema v4.