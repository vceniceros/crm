# Auditoría: Integración del CRM con auth.microtv.ar

**Fecha:** 9 de Abril de 2026 (Revisión 2)  
**Auditor:** Software Engineer Senior + Auditor de Arquitectura  
**Alcance:** Rediseño de esquema del CRM para eliminar duplicaciones de autenticación mientras mantiene persistencia local de usuarios y roles funcionales del CRM

---

## Resumen Ejecutivo

El esquema propuesto del CRM (`schema-propuesto.sql`) contiene duplicaciones críticas de responsabilidades de **autenticación/autorización centralizada** que ya están implementadas en `auth.microtv.ar`. 

Sin embargo, el CRM **SÍ necesita**:
- **Persistencia local de usuarios** (perfil operativo con datos del dominio CRM)
- **Roles propios** (permisos funcionales del dominio CRM)

Esta auditoría corregida distingue claramente entre:
- **Identidad centralizada** (auth.microtv.ar) → autenticación, credenciales, sesiones, contexto organizacional
- **Operación local** (CRM) → perfil operativo del usuario + roles funcionales + datos de negocio

**Hallazgos clave:**
- ❌ `password_hash` y lógica de autenticación duplican auth
- ❌ `user_sessions` duplica gestión de JWT de auth
- ✅ Tabla `users` debe **transformarse** en `crm_users` (entidad local del CRM con `auth_user_id` como FK externa)
- ✅ Tabla `roles` debe **renombrarse** a `crm_roles` (roles funcionales del dominio CRM)
- ✅ Tabla `user_roles` debe **renombrarse** a `crm_user_roles` (asignación de capacidades operativas)
- ✅ Diseño final: `crm_users` + `crm_roles` + `crm_user_roles` con separación semántica clara

---

## A. Corrección de Criterio

### Reglas de Arquitectura (Fijas)

1. ✅ **El CRM SÍ debe tener persistencia local del usuario** — para datos operativos del dominio CRM
2. ✅ **El CRM SÍ debe tener roles propios** — para permisos funcionales dentro del CRM
3. ❌ **El CRM NO debe duplicar autenticación ni sesiones** — auth.microtv.ar es autoritativo
4. ✅ **Naming explícito** — usar `crm_users`, `crm_roles`, `crm_user_roles` para evitar ambigüedad

### Qué Cambia Respecto a la Propuesta Anterior

#### 1. Persistencia Local de Usuarios

**Propuesta anterior (incorrecta):**
- Propuse eliminar completamente tabla `users`
- Reemplazar por `crm_user_profiles` como "cache/proyección" de auth
- PK = `auth_user_id` directamente

**Problema:**
- No dejaba claro que era una entidad local del CRM con datos operativos propios
- PK externa no permite integridad referencial robusta
- Semántica confusa: ¿es cache o entidad?

**Propuesta corregida (correcta):**
- Mantener tabla de usuarios del CRM, pero **renombrar a `crm_users`**
- PK local: `crm_user_id UUID` (generado por el CRM)
- FK externa: `auth_user_id VARCHAR(36) UNIQUE` (referencia a auth.microtv.ar)
- Incluir datos operativos del CRM: phone, initials, is_active_in_crm, last_seen_at, etc.
- Incluir cache opcional: email, display_name (para UI, actualizable desde JWT)
- NO incluir: password_hash, tokens, verificación

**Justificación:**
- Es una **entidad propia del dominio CRM**, no un mero cache
- Los usuarios tienen datos operativos locales (teléfono, iniciales, última actividad)
- PK local permite FKs robustas en resto del esquema
- `auth_user_id` UNIQUE garantiza 1:1 con auth

#### 2. Roles Locales del CRM

**Propuesta anterior (incorrecta):**
- Propuse eliminar `roles` por completo
- Alternativa A: flags booleanos (`can_execute_field_work`, etc.)
- Alternativa B: tabla `crm_functional_roles` solo si RBAC complejo

**Problema:**
- Flags booleanos no escalan si hay más de 3-4 permisos
- No dejaba claro que los roles son parte del core del CRM

**Propuesta corregida (correcta):**
- Mantener tabla de roles, pero **renombrar a `crm_roles`**
- Son roles **funcionales del dominio CRM**, NO roles de identidad
- Ejemplos: `admin_crm`, `tecnico_campo`, `encargado_deposito`, `dispatcher`
- Tabla de asignación: `crm_user_roles` (M2M entre `crm_users` y `crm_roles`)

**Justificación:**
- Los roles del CRM representan **capacidades operativas** dentro del sistema
- Son diferentes a los roles del auth (que son de identidad/contexto organizacional)
- Naming explícito (`crm_roles`) evita confusión con roles de auth
- Permite escalar permisos sin modificar esquema (agregar rol nuevo = INSERT)

#### 3. Qué SÍ Se Elimina

Estas partes **SÍ duplican auth** y deben eliminarse:

| Elemento | Motivo de Eliminación |
|----------|----------------------|
| `password_hash` | Auth gestiona credenciales con Argon2 |
| `user_sessions` + `token_jti` + `refresh_token_hash` | Auth gestiona JWT stateless, solo persiste login_tickets para flujo multi-tenant |
| `last_login_at` | Auth gestiona sesiones implícitamente via login_tickets |
| Verificación de email | Auth gestiona `verification_token`, `email_verified` |
| Recuperación de contraseña | Auth gestiona `password_reset_token` |

---

## B. Modelo Conceptual Correcto

### Arquitectura de Integración

```
┌─────────────────────────────────────────────────────────────┐
│                    auth.microtv.ar                          │
│                   (Identidad Centralizada)                  │
├─────────────────────────────────────────────────────────────┤
│ • users (user_id, email, password_hash, status)             │
│ • memberships (tenant_type, tenant_id)                      │
│ • roles (platform_admin, company_admin, company_operator)   │
│ • role_assignments (membership_id, role_id)                 │
│ • login_tickets (jti, user_id, consumed_at)                 │
│ • JWT stateless (access_token, refresh_token)               │
│                                                              │
│ Responsabilidades:                                           │
│  - Autenticación (email+password, OAuth)                    │
│  - Gestión de contraseñas (hash, reset)                     │
│  - Verificación de email                                     │
│  - Sesiones JWT (+revocación futura)                        │
│  - Contexto multi-tenant (selección de membership)          │
│  - Roles de identidad/organización                          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ JWT (claims: sub, email, active_membership)
                            │
┌─────────────────────────────────────────────────────────────┐
│                     microtv-crm-ycc                         │
│                   (Operación Local)                         │
├─────────────────────────────────────────────────────────────┤
│ • crm_users (crm_user_id PK, auth_user_id FK externe UNIQUE)│
│   - phone, initials, is_active_in_crm                       │
│   - cache: email, display_name (de JWT)                     │
│                                                              │
│ • crm_roles (crm_role_id, role_key, role_label)            │
│   - admin_crm, tecnico_campo, encargado_deposito            │
│                                                              │
│ • crm_user_roles (crm_user_id, crm_role_id)                │
│   - M2M asignación de capacidades operativas                │
│                                                              │
│ • tasks, tickets, inventory, locations, clients...          │
│   - FKs a crm_users.crm_user_id                             │
│                                                              │
│ Responsabilidades:                                           │
│  - Perfil operativo del usuario en el CRM                   │
│  - Permisos funcionales (qué puede hacer en CRM)            │
│  - Datos de negocio (tareas, tickets, inventario)           │
│  - Auditoría de acciones operativas                         │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Autenticación y Autorización

1. **Login (en auth.microtv.ar):**
   - Usuario se autentica con email+password
   - Auth valida credenciales, genera JWT
   - JWT incluye: `sub` (user_id), `email`, `active_membership` (tenant_type, tenant_id, roles)

2. **Acceso al CRM:**
   - Usuario presenta JWT en header `Authorization: Bearer <token>`
   - Backend del CRM valida firma del JWT con clave pública de auth
   - Backend extrae `sub` (= auth_user_id) del claim

3. **Sincronización/Upsert de perfil local:**
   ```sql
   -- Backend busca o crea usuario local
   INSERT INTO crm_users (auth_user_id, email, display_name, cached_at)
   VALUES ($1, $2, $3, NOW())
   ON CONFLICT (auth_user_id) 
   DO UPDATE SET 
     email = EXCLUDED.email,
     display_name = EXCLUDED.display_name,
     cached_at = NOW();
   ```

4. **Autorización combinada:**
   ```typescript
   // Pseudocódigo
   function checkPermission(jwtClaims, crmUserId, action) {
     // Paso 1: Validar acceso base desde JWT
     const { active_membership } = jwtClaims;
     
     // Solo company/platform pueden acceder al CRM
     if (!['company', 'platform'].includes(active_membership.tenant_type)) {
       throw new ForbiddenError('Contexto inválido para CRM');
     }
     
     // Paso 2: Validar permisos funcionales del CRM
     const crmRoles = await db.getCrmRoles(crmUserId);
     
     switch (action) {
       case 'execute_field_tasks':
         return (
           active_membership.roles.includes('platform_admin') ||
           crmRoles.includes('tecnico_campo') ||
           crmRoles.includes('admin_crm')
         );
       
       case 'manage_inventory':
         return (
           active_membership.roles.includes('platform_admin') ||
           crmRoles.includes('encargado_deposito') ||
           crmRoles.includes('admin_crm')
         );
       
       case 'approve_requests':
         return (
           active_membership.roles.includes('platform_admin') ||
           active_membership.roles.includes('company_admin') ||
           crmRoles.includes('admin_crm')
         );
       
       default:
         return false;
     }
   }
   ```

### Separación de Responsabilidades

| Responsabilidad | Dueño | Justificación |
|----------------|-------|---------------|
| Autenticación (login) | auth.microtv.ar | Centralizada, evita duplicación, permite SSO futuro |
| Contraseñas (hash, reset) | auth.microtv.ar | Seguridad crítica, una fuente de verdad |
| Verificación de email | auth.microtv.ar | Parte del flujo de registro centralizado |
| Sesiones JWT | auth.microtv.ar | Stateless, auth emite y firma tokens |
| Contexto multi-tenant | auth.microtv.ar | Memberships y selección de contexto |
| Roles de identidad | auth.microtv.ar | platform_admin, company_admin, company_operator |
| **Perfil operativo** | **CRM** | Datos específicos del dominio (teléfono, iniciales, actividad) |
| **Roles funcionales** | **CRM** | Capacidades dentro del CRM (técnico, depósito, dispatcher) |
| **Datos de negocio** | **CRM** | Tasks, tickets, inventario, clientes |

---

## C. Decisión de Naming

### Tablas Renombradas

| Tabla Original | Tabla Nueva | Justificación |
|----------------|-------------|---------------|
| `users` | **`crm_users`** | Evita confusión con `auth.users`. Deja claro que son usuarios locales del CRM con perfil operativo. |
| `roles` | **`crm_roles`** | Evita confusión con `auth.roles`. Deja claro que son roles funcionales del CRM, no roles de identidad. |
| `user_roles` | **`crm_user_roles`** | Consistencia con `crm_users` y `crm_roles`. Asignación de capacidades operativas. |
| `user_sessions` | **ELIMINADA** | Auth gestiona sesiones JWT stateless. |

### Columnas Clave

| Columna | Tipo | Propósito |
|---------|------|-----------|
| `crm_user_id` | UUID PK | Identificador local del CRM (generado por el CRM) |
| `auth_user_id` | VARCHAR(36) UNIQUE NOT NULL | Identificador externo de auth.microtv.ar (claim `sub` del JWT) |
| `email` | VARCHAR(255) | Cache de auth (actualizable desde JWT, no autoritativo) |
| `display_name` | VARCHAR(255) | Cache de auth (actualizable desde JWT, no autoritativo) |
| `phone` | VARCHAR(50) | Dato operativo local del CRM |
| `initials` | VARCHAR(10) | Dato operativo local del CRM (avatares) |
| `is_active_in_crm` | BOOLEAN | Actividad LOCAL en el CRM (independiente de auth.users.status) |
| `last_seen_in_crm_at` | TIMESTAMPTZ | Última actividad en el CRM |
| `cached_at` | TIMESTAMPTZ | Última actualización del cache desde JWT |

### Convenciones

1. **Prefijo `crm_`** en tablas de usuarios/roles para:
   - Evitar naming genérico que se confunde con auth
   - Dejar explícito que son entidades del dominio CRM
   - Facilitar búsquedas en código (grep `crm_` → encuentra todas las entidades locales)

2. **Sufijo `_in_crm`** en flags booleanos para:
   - Diferenciar de flags de auth (`is_active` vs `is_active_in_crm`)
   - Dejar claro que es estado local del CRM

3. **`auth_user_id`** (no `external_user_id`)para:
   - Dejar explícito que apunta a auth.microtv.ar
   - Evitar nombres genéricos que no indican origen

---

## D. Nuevo SQL Completo

Ver archivo adjunto: `schema-propuesto-v2.sql` completo en la siguiente sección.

---

## Resumen de Decisiones Finales

### 1. Separación de Responsabilidades

**auth.microtv.ar (Identidad Centralizada):**
- ✅ Autenticación (login con email+password, OAuth futuro)
- ✅ Gestión de contraseñas (Argon2 hash, reset, verificación)
- ✅ Sesiones JWT stateless (access_token, refresh_token, login_tickets)
- ✅ Contexto multi-tenant (memberships, selección de tenant)
- ✅ Roles de identidad/organización (platform_admin, company_admin, company_operator, passenger_user)
- ✅ Verificación de email, invitaciones, reCAPTCHA

**microtv-crm-ycc (Operación Local):**
- ✅ Perfil operativo de usuarios (phone, initials, is_active_in_crm, last_seen_in_crm_at)
- ✅ Cache de datos de auth (email, display_name) actualizable desde JWT
- ✅ Roles funcionales del CRM (admin_crm, tecnico_campo, encargado_deposito, dispatcher)
- ✅ Datos de negocio (tasks, tickets, inventory, clients, locations)
- ✅ Auditoría de acciones operativas (opcional: crm_audit_log)

### 2. Naming Definitivo

| Concepto | Tabla | PK | FK Externa |
|----------|-------|----|------------|
| Usuarios del CRM | `crm_users` | `crm_user_id` UUID | `auth_user_id` VARCHAR(36) → auth.users.user_id |
| Roles funcionales del CRM | `crm_roles` | `crm_role_id` UUID | - |
| Asignación de roles | `crm_user_roles` | `crm_user_role_id` UUID | `crm_user_id`, `crm_role_id` |

**Convenciones:**
- Prefijo `crm_` en tablas de usuarios/roles → evita confusión con auth
- Sufijo `_in_crm` en flags booleanos → diferencia estado local vs auth
- `auth_user_id` explícito → deja claro que apunta a auth.microtv.ar
- Columnas FK: `*_crm_user_id` → consistencia en todo el esquema

### 3. Cambios Respecto a Schema Original

| Tabla Original | Acción | Tabla Nueva | Cambios |
|----------------|--------|-------------|---------|
| `users` | **Transformada** | `crm_users` | Eliminado `password_hash`, agregado `auth_user_id` UNIQUE, renombrado PK a `crm_user_id` |
| `roles` | **Renombrada** | `crm_roles` | Renombrado PK a `crm_role_id`, seed data actualizado (admin_crm, tecnico_campo, etc.) |
| `user_roles` | **Renombrada** | `crm_user_roles` | Renombrado PK a `crm_user_role_id`, FKs actualizadas |
| `user_sessions` | **ELIMINADA** | - | Auth gestiona JWT stateless |
| Resto (+30 tablas) | **Actualizadas FKs** | Sin cambios | Todas las columnas `*_user_id` ahora son `*_crm_user_id` y apuntan a `crm_users.crm_user_id` |

### 4. Flujo de Integración

1. **Autenticación:** Usuario se loguea en auth.microtv.ar → recibe JWT
2. **Validación:** Backend del CRM valida firma del JWT con clave pública de auth
3. **Sincronización:** Backend extrae `sub` del JWT y hace upsert en `crm_users`:
   ```sql
   INSERT INTO crm_users (auth_user_id, email, display_name, cached_at)
   VALUES ($1, $2, $3, NOW())
   ON CONFLICT (auth_user_id) DO UPDATE SET
     email = EXCLUDED.email,
     display_name = EXCLUDED.display_name,
     cached_at = NOW()
   RETURNING crm_user_id;
   ```
4. **Autorización:** Backend combina roles de auth (JWT claims) + roles del CRM (crm_user_roles)
5. **Operación:** Usuario trabaja en CRM con perfil local (`crm_user_id`) + datos operativos

### 5. Lo Que NO Está en el CRM

- ❌ `password_hash` — auth gestiona credenciales
- ❌ `user_sessions`, `token_jti`, `refresh_token_hash` — auth gestiona JWT
- ❌ `last_login_at` — auth gestiona sesiones
- ❌ `verification_token`, `email_verified` — auth gestiona verificación
- ❌ `password_reset_token` — auth gestiona recuperación
- ❌ `status` (pending_verification, active, suspended) — auth gestiona activación de cuentas

---

**Próximos pasos:**
1. Aplicar schema completo en ambiente de desarrollo
2. Implementar middleware JWT en backend del CRM (validación de firma + upsert automático de `crm_users`)
3. Definir políticas de autorización combinando roles de auth + roles del CRM
4. Documentar contrato de integración auth↔CRM

---

**Fin de auditoría.**
