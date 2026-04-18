Actuá como un senior backend engineer y auditor de arquitectura.

Tu tarea es CONSTRUIR la base inicial de un backend funcional para un CRM en FastAPI, partiendo de que EL BACKEND TODAVÍA NO EXISTE.

## Objetivo

Crear la primera versión funcional del backend del CRM, con foco exclusivo en el flujo de autenticación y acceso inicial al sistema.

El flujo mínimo que debe quedar resuelto es:

1. El usuario ve una pantalla de login con usuario y contraseña.
2. El frontend envía esas credenciales a nuestro backend CRM.
3. El backend CRM reenvía esas credenciales al servicio auth.
4. Auth valida las credenciales.
5. Si auth responde 200 con JWT:
   - el backend CRM valida/decodifica el JWT
   - extrae `user_id`
   - extrae `rol` o `roles`
6. El backend CRM persiste en su propia base de datos los datos mínimos necesarios del usuario/contexto autenticado.
7. El backend CRM devuelve una respuesta usable por el frontend para permitir el acceso.
8. El usuario puede entrar a la maqueta actual del frontend.

## Restricciones de implementación

- No improvises una arquitectura distinta.
- No mezcles responsabilidades entre capas.
- No pongas lógica de negocio en endpoints.
- No pongas acceso directo a base de datos fuera de repositories.
- No dejes dependencias circulares.
- No dejes duplicación evitable.
- No dejes atajos “temporales” sin marcar.
- No generes una solución monolítica desordenada.
- Programación orientada a objetos.
- Toda clase y todo método debe tener docstring/comentario en formato Google.
- El código debe quedar prolijo, separable y extensible.
- Debe quedar preparado para crecer después en módulos como tickets, tareas, stock, etc.
- Queda prohibido romper la arquitectura definida.
- Queda prohibido dejar code smells notorios.

## Arquitectura obligatoria

Debés respetar esta estructura de capas:

- `api`: endpoints/controllers
- `services`: lógica de aplicación y orquestación de casos de uso
- `models`: entidades/clases de dominio y lógica de negocio de dominio
- `repositories`: acceso puro a persistencia, un repository por agregado/entidad principal

Reglas:

- `api` solo recibe request, valida superficialmente, llama services y devuelve response
- `services` orquestan casos de uso
- `models` representan entidades y reglas de dominio
- `repositories` encapsulan acceso a base de datos
- los endpoints NO deben hablar directo con la base
- los repositories NO deben conocer HTTP
- auth externo debe entrar mediante un adapter/wrapper

## Patrones obligatorios

### 1. Adapter
Implementá un adapter para encapsular la integración con auth.

Ese adapter debe ser el único punto del backend CRM que conoce:
- URL/base URL de auth
- endpoint de login de auth
- formato de request/response de auth
- manejo de errores de auth
- parsing del JWT proveniente de auth

Objetivo:
evitar acoplar el CRM al detalle del servicio auth.

### 2. Recomendar patrones adicionales útiles
Podés usar otros patrones solo si aportan valor claro y sin sobreingeniería.
Evaluá especialmente estos:

- Service Layer
- Repository
- DTO / Mapper
- Factory para construcción de clientes/config
- Strategy solo si realmente aparece una variación real
- Unit of Work solo si la persistencia lo justifica

No metas patrones por decoración.
Si agregás otro patrón, justificá concretamente para qué se usa.

## Alcance concreto de esta primera entrega

Quiero que generes la base funcional para:

### A. Estructura inicial del backend FastAPI
Crear el esqueleto del proyecto backend con:
- app principal
- configuración
- dependencias base
- estructura de carpetas
- routers iniciales
- manejo básico de errores
- conexión a base de datos
- modelos mínimos
- repositories mínimos
- services mínimos

### B. Módulo de autenticación del CRM
Crear el módulo inicial de autenticación con:

- endpoint propio del CRM para login, por ejemplo `/auth/login`
- request model con usuario/email y contraseña
- service que delega al adapter de auth
- adapter que llama al auth externo
- decodificación/lectura del JWT devuelto por auth
- extracción de:
  - `user_id`
  - `rol` o `roles`
  - contexto/membership si estuviera disponible
- persistencia mínima en DB CRM de los datos necesarios del usuario autenticado

### C. Persistencia mínima en CRM
Definí lo mínimo necesario para guardar localmente:
- usuario autenticado
- referencia externa al user_id del auth
- email si viene disponible
- rol o snapshot de roles/contexto si corresponde
- timestamps mínimos útiles

No inventes un mega modelo de usuarios.
Hacé una persistencia mínima, limpia y coherente con un CRM que depende de auth externo.

Importante:
aclará qué se guarda como fuente local del CRM y qué queda como snapshot/cache contextual de auth.

### D. Autorización mínima
Dejá lista la base para poder:
- reconocer usuario autenticado
- reconocer rol/roles
- proteger endpoints después

No hace falta construir todo el sistema de permisos ahora, pero sí dejar la base correcta.

### E. Pantalla/login flow
Si el frontend ya tiene maqueta visual, el backend debe exponer el contrato necesario para que esa pantalla pueda funcionar.

No diseñes un frontend entero nuevo.
Solo definí claramente:
- request esperado
- response esperada
- códigos de error
- formato consistente para que el frontend pueda consumirlo

## Requisito de Docker para auth

Existe un servicio auth ya hecho en otro proyecto.

Necesito que generes un Dockerfile NUEVO y específico para el uso de auth dentro de este proyecto CRM.

Condiciones:
- no modificar ni romper el Dockerfile original del otro proyecto
- crear un Dockerfile separado para este contexto
- dejar documentado cómo levantar auth para entorno local del CRM
- incluir estrategia de seed de datos de prueba

Ese entorno de auth para pruebas debe incluir al menos:
- un usuario admin perteneciente a MicroTV
- un usuario perteneciente a YCC Brothers

Necesito que el entorno ya quede preparado para probar login real contra auth.

Si para eso hace falta:
- script de seed
- migration seed
- fixture inicial
- docker compose auxiliar

podés crearlos, pero sin sobreingeniería.

## Qué espero como salida

Quiero que trabajes en este orden:

### 1. Análisis inicial
Describí de forma breve:
- estructura propuesta del backend
- módulos iniciales
- decisiones arquitectónicas
- qué parte corresponde a auth adapter
- qué parte corresponde a persistencia local del CRM

### 2. Árbol de carpetas propuesto
Mostrá el árbol inicial del backend.

### 3. Lista exacta de archivos a crear
Archivo por archivo, con su responsabilidad.

### 4. Implementación inicial
Generá el código inicial necesario, completo y consistente, para que el backend arranque y el flujo básico de login quede encaminado.

### 5. Docker para auth
Generá:
- nuevo Dockerfile para auth en este proyecto
- estrategia de seed
- archivos auxiliares mínimos necesarios

### 6. Notas técnicas
Indicá:
- qué quedó funcional ya
- qué quedó preparado
- qué faltaría después

## Reglas de calidad

- No hardcodees cosas evitables si deben salir de config.
- No metas secretos reales.
- Usá variables de entorno.
- No supongas claims de JWT si no están confirmados: dejá el código preparado para claims esperadas, pero marcá claramente qué depende del contrato real de auth.
- Si el JWT ya fue auditado y se sabe que trae `sub` y `active_membership.roles`, usá eso como contrato actual.
- Mantené separación estricta entre autenticación externa y autorización local del CRM.
- Evitá sobreingeniería.
- Evitá magia.
- Evitá helpers genéricos inútiles.
- Evitá archivos gigantes.
- Evitá meter toda la lógica en `main.py`.

## Decisión de diseño importante

El CRM depende de auth externo para autenticar.
El CRM no debe transformarse en otro proveedor de identidad.
Debe consumir auth, extraer identidad/contexto, persistir lo mínimo necesario y continuar.

## Entregable esperado

No me des solo ideas.
Quiero propuesta + estructura + archivos + código inicial.

Si detectás una mejor forma de organizar internamente sin romper estas reglas, podés proponerla, pero siempre manteniendo:

- FastAPI
- Adapter para auth
- capas `api / services / models / repositories`
- POO
- docstrings Google
- código limpio
- sin smells notorios