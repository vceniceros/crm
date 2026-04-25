# Historial de Cambios de Código (Últimos 21 días)

> Este documento contiene los diffs de código para análisis técnico.

## Commit: fd65bd9
**Autor:** Valentino_Colella
**Fecha:** Fri Apr 24 16:19:33 2026 -0300
**Mensaje:**  feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo

### Cambios por archivo:
#### 📄 `DEPLOY.md`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
--- /dev/null
+++ b/DEPLOY.md
@@ -0,0 +1,1432 @@
+# DEPLOY.md — Producción CRM MicroTV
+
+**Versión:** 1.0  
+**Fecha:** 2026-04-24  
+**Audiencia:** Sudoers en `/opt/ycc`  
+**Entorno:** Ubuntu Server / Debian compatible  
+
+---
+
+## 📋 Tabla de contenidos
+
+1. [Supuestos del entorno](#supuestos-del-entorno)
+2. [Estructura de directorios](#estructura-de-directorios-en-servidor)
+3. [Pre-deploy: Preparación del servidor](#pre-deploy-preparación-del-servidor)
+4. [PostgreSQL: Base de datos](#postgresql-base-de-datos)
+5. [Backend: FastAPI](#backend-fastapi)
+6. [Frontend: Angular](#frontend-angular)
+7. [Nginx: Reverse proxy](#nginx-reverse-proxy)
+8. [Systemd: Proceso backend](#systemd-proceso-backend)
+9. [HTTPS/SSL](#httpsssl-certbot)
+10. [Verificación post-deploy](#verificación-post-deploy)
+11. [Backups](#backups)
+12. [Actualización de versión](#actualización-de-versión)
+13. [Rollback](#rollback)
+14. [Troubleshooting](#troubleshooting)
+
+---
+
+## Supuestos del entorno
+
+```
+Usuario deploy:        sudoer (capaz de ejecutar sudo sin contraseña)
+Home deploy:           /opt/ycc
+Sistema operativo:     Ubuntu Server 20.04 LTS o superior / Debian 11+
+Backend:               FastAPI (uvicorn ASGI)
+Frontend:              Angular 21.2
+Base de datos:         PostgreSQL 16
+Reverse proxy:         Nginx
+Proceso backend:       systemd (ycc-crm-backend)
+Frontend estático:     Nginx (SPA con service worker)
+Dominio producción:    crm.microtv.ar (REEMPLAZAR CON DOMINIO REAL)
+Auth externo:          https://auth.microtv.ar
+```
+
+**⚠️ Si alguno de estos supuestos es incorrecto, ajustar ahora antes de continuar.**
+
+---
+
+## Estructura de directorios en servidor
+
+```
+/opt/ycc/
+├── crm/
+│   ├── backend/
+│   │   ├── .env                    # Variables de entorno (NO COMMITEAR)
+│   │   ├── .git/
+│   │   ├── venv/                   # Python virtualenv
+│   │   ├── src/crm_backend/
+│   │   ├── public/                 # Imágenes y videos
+│   │   │   ├── images/
+│   │   │   └── videos/
+│   │   ├── pyproject.toml
+│   │   └── [otros archivos del repo]
+│   │
+
... (código truncado por longitud) ...
```

#### 📄 `export_git__md.py`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
--- /dev/null
+++ b/export_git__md.py
@@ -0,0 +1,75 @@
+import subprocess
+import os
+
+# Configuración
+OUTPUT_FILE = "historial_completo_para_gpt_crm.md"
+DIAS_ATRAS = 21  # Cuántos días de historial quieres
+EXCLUDE_EXTENSIONS = ['.json', '.lock', '.png', '.jpg', '.svg', '.map'] # Ignorar archivos ruidosos
+
+def run_git_command(command):
+    try:
+        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
+        return result.decode('utf-8', errors='ignore').strip()
+    except subprocess.CalledProcessError as e:
+        return ""
+
+def generate_markdown():
+    # 1. Obtener los hashes de los commits de los últimos X días
+    print(f"Obteniendo commits de los últimos {DIAS_ATRAS} días...")
+    hashes = run_git_command(f'git log --since="{DIAS_ATRAS} days ago" --format="%H"').split('\n')
+    
+    if not hashes or hashes == ['']:
+        print("No se encontraron commits en ese rango.")
+        return
+
+    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
+        f.write(f"# Historial de Cambios de Código (Últimos {DIAS_ATRAS} días)\n\n")
+        f.write("> Este documento contiene los diffs de código para análisis técnico.\n\n")
+
+        for commit_hash in hashes:
+            # Metadatos del commit
+            info = run_git_command(f'git show -s --format="## Commit: %h%n**Autor:** %an%n**Fecha:** %ad%n**Mensaje:** %s" {commit_hash}')
+            f.write(info + "\n\n")
+            
+            # Obtener archivos modificados
+            files_changed = run_git_command(f'git show --name-only --format="" {commit_hash}').split('\n')
+            
+            f.write("### Cambios por archivo:\n")
+            
+            for file_path in files_changed:
+                if not file_path: continue
+                
+                # Filtrar archivos basura (logs, lockfiles, assets)
+                _, ext = os.path.splitext(file_path)
+                if ext in EXCLUDE_EXTENSIONS:
+                    f.write(f"- *{file_path} (Omitido por extensión)*\n")
+                    continue
+                
+                
... (código truncado por longitud) ...
```

#### 📄 `historial_completo_para_gpt_crm.md`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
--- /dev/null
+++ b/historial_completo_para_gpt_crm.md
@@ -0,0 +1,29524 @@
+# Historial de Cambios de Código (Últimos 21 días)
+
+> Este documento contiene los diffs de código para análisis técnico.
+
+## Commit: a13ef83
+**Autor:** Valentino_Colella
+**Fecha:** Sat Apr 18 11:40:02 2026 -0300
+**Mensaje:** se avanza en la implementacion de backend y bdd integrando el modulo de tareas
+
+### Cambios por archivo:
+- *.vscode/settings.json (Omitido por extensión)*
+#### 📄 `ENTORNO_DE_DEV.md`
+```diff
+commit a13ef83257a56970f36eb8355eb19e286fa3d1f9
+Author: Valentino_Colella <valentinocolella@microtv.com.ar>
+Date:   Sat Apr 18 11:40:02 2026 -0300
+
+    se avanza en la implementacion de backend y bdd integrando el modulo de tareas
+
+new file mode 100644
+--- /dev/null
++++ b/ENTORNO_DE_DEV.md
+@@ -0,0 +1,269 @@
++# Entorno de desarrollo
++
++Este documento deja cerrado el flujo inicial de login para probarlo localmente en Windows con PowerShell.
++
++## 1. Requisitos previos
++
++- Docker Desktop levantado.
++- Python 3.12 disponible en `PATH`.
++- Node.js 20+ y `npm`.
++- Puertos libres: `4200`, `8001`, `8010`.
++
++## 2. Levantar auth.microtv.ar local con seed
++
++Parate en la raíz del workspace `microtv-crm-ycc`:
++
++```powershell
++Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
++docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build
++```
++
++Qué hace este compose:
++
++- levanta PostgreSQL local de auth sólo para la red interna de Docker
++- construye un contenedor específico para CRM usando `microtv-crm-backend/docker/auth-local/Dockerfile`
++- corre migraciones de auth
++- ejecuta el seed del CRM
++- expone auth en `http://localhost:8001`
++
++## 3. Usuarios seed creados en la base local de auth
++
++Estos usuarios quedan creados automáticamente en `auth_microtv`:
++
++### Admin MicroTV
++
++- Email: `admin.crm@microtv.com`
++- Password: `Passw0rd!`
++- Display name: `Admin MicroTV`
++- Tenant: `MICROTV`
++- Rol en auth: `platform_admin`
++- Bootstrap de rol local CRM esperado: `admin`
++
++### Operador YCC Brothers
++

... (código truncado por longitud) ...
```

- *microtv-crm-backend/public/images/products/e649efa4-816b-487c-a29a-c139aefed294.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/02117f2bbc8e443694b5c2238c8db8ce.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/12613159e5364c55985d0c9f1f869756.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/1453925e5830430dbb9016fc6c6b6de0.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/2878b3394fda4bd5b8f4f468857f8165.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/63a11c9d7cb2413cb84964609b9bcd9f.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/882695967bd940b1b7a0a371ca2408eb.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/8e83d9e589004fc1bcb9f268b5567e9a.jpg (Omitido por extensión)*
#### 📄 `microtv-crm-backend/public/images/task/b98fdcc3147e4069929fe1a134803e47.jpeg`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/public/images/task/b98fdcc3147e4069929fe1a134803e47.jpeg differ
```

- *microtv-crm-backend/public/images/task/f265cba050ed4dd89fac5a7846f34ef5.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/f448f780233f480aa5bc7704aa2de4e4.jpg (Omitido por extensión)*
#### 📄 `microtv-crm-backend/sql/20260422_ticket_module.sql`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
--- /dev/null
+++ b/microtv-crm-backend/sql/20260422_ticket_module.sql
@@ -0,0 +1,90 @@
+-- Ticket module schema extension
+-- Compatible with PostgreSQL schema used by microtv-crm-backend.
+
+CREATE TABLE IF NOT EXISTS tickets (
+    ticket_id UUID PRIMARY KEY,
+    ticket_number VARCHAR(30) NOT NULL UNIQUE,
+    title VARCHAR(255) NOT NULL,
+    description TEXT NOT NULL,
+    client_id UUID NOT NULL REFERENCES clients(client_id),
+    location_id UUID NOT NULL REFERENCES locations(location_id),
+    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
+    priority VARCHAR(30) NOT NULL DEFAULT 'MEDIUM',
+    assigned_role_id UUID NULL REFERENCES crm_roles(crm_role_id),
+    assigned_user_id UUID NULL REFERENCES crm_users(crm_user_id),
+    created_by_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
+    resolved_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
+    resolved_at TIMESTAMPTZ NULL,
+    closed_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
+    closed_at TIMESTAMPTZ NULL,
+    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
+    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
+    deleted_at TIMESTAMPTZ NULL
+);
+
+CREATE TABLE IF NOT EXISTS ticket_comments (
+    ticket_comment_id UUID PRIMARY KEY,
+    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
+    author_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id),
+    comment_type VARCHAR(30) NOT NULL DEFAULT 'general',
+    body TEXT NOT NULL,
+    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
+);
+
+CREATE TABLE IF NOT EXISTS ticket_attachments (
+    attachment_id UUID PRIMARY KEY,
+    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
+    ticket_comment_id UUID NULL REFERENCES ticket_comments(ticket_comment_id) ON DELETE SET NULL,
+    file_name VARCHAR(500) NOT NULL,
+    file_url VARCHAR(1000) NOT NULL,
+    file_size_bytes INTEGER NULL,
+    mime_type VARCHAR(100) NULL,
+    attachment_type VARCHAR(50) NOT NULL DEFAULT 'PHOTO',
+    uploaded_by_crm_user_id UUID NULL REFERENCES crm_users(crm_user_id),
+    uploaded_
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/sql/20260423_crm_notifications.sql`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
--- /dev/null
+++ b/microtv-crm-backend/sql/20260423_crm_notifications.sql
@@ -0,0 +1,23 @@
+-- In-app notifications schema extension
+-- Date: 2026-04-23
+
+CREATE TABLE IF NOT EXISTS crm_notifications (
+    notification_id UUID PRIMARY KEY,
+    recipient_crm_user_id UUID NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE CASCADE,
+    notification_type VARCHAR(80) NOT NULL,
+    title VARCHAR(255) NOT NULL,
+    body TEXT NOT NULL,
+    entity_type VARCHAR(40) NULL,
+    entity_id VARCHAR(36) NULL,
+    is_read BOOLEAN NOT NULL DEFAULT FALSE,
+    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
+    read_at TIMESTAMPTZ NULL,
+    metadata JSONB NULL
+);
+
+CREATE INDEX IF NOT EXISTS idx_crm_notifications_recipient ON crm_notifications(recipient_crm_user_id);
+CREATE INDEX IF NOT EXISTS idx_crm_notifications_type ON crm_notifications(notification_type);
+CREATE INDEX IF NOT EXISTS idx_crm_notifications_is_read ON crm_notifications(is_read);
+CREATE INDEX IF NOT EXISTS idx_crm_notifications_created_at ON crm_notifications(created_at);
+CREATE INDEX IF NOT EXISTS idx_crm_notifications_recipient_unread_created
+    ON crm_notifications(recipient_crm_user_id, is_read, created_at DESC);
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/__pycache__/dependencies.cpython-313.pyc`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

Binary files a/microtv-crm-backend/src/crm_backend/api/__pycache__/dependencies.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/api/__pycache__/dependencies.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/__pycache__/router.cpython-313.pyc`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

Binary files a/microtv-crm-backend/src/crm_backend/api/__pycache__/router.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/api/__pycache__/router.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/dependencies.py`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

--- a/microtv-crm-backend/src/crm_backend/api/dependencies.py
+++ b/microtv-crm-backend/src/crm_backend/api/dependencies.py
@@ -15,22 +15,29 @@ from crm_backend.repositories import (
     CrmUserRepository,
     InventoryFlowRepository,
     LocationRepository,
+    NotificationRepository,
     StockCategoryRepository,
     StockProductRepository,
     TaskRepository,
     TaskTemplateRepository,
+    TicketRepository,
 )
 from crm_backend.services import (
     AuthApplicationService,
     ClientApplicationService,
     InventoryRequestFacade,
     LocationApplicationService,
+    NotificationService,
     RoleResolutionService,
     StockApplicationService,
     TaskApplicationService,
     TaskMaterialFlowFacade,
+    TicketApplicationService,
 )
 from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.dashboard_service import DashboardService
+from crm_backend.services.reports_service import ReportsService
+from crm_backend.services.settings_service import SettingsService
 
 
 def get_auth_service_adapter(settings: Settings = Depends(get_settings)) -> AuthServiceAdapter:
@@ -194,6 +201,27 @@ def get_task_repository(session: Session = Depends(get_db_session)) -> TaskRepos
     return TaskRepository(session)
 
 
+def get_ticket_repository(session: Session = Depends(get_db_session)) -> TicketRepository:
+    """Provide the ticket repository."""
+
+    return TicketRepository(session)
+
+
+def get_notification_repository(session: Session = Depends(get_db_session)) -> NotificationRepository:
+    """Provide the notification repository."""
+
+    return NotificationRepository(session)
+
+
+def get_notification_service(
+    notification_repository: NotificationRepository = Depends(get_notification_repository),
+    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
+) -> NotificationService:
+    """Provide the in-app notification service."""
+
+    return NotificationService(notification_repository, user_repository)
+
+
 def extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
     """Extract the bearer token f
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/dashboard.cpython-313.pyc`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/dashboard.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/notifications.cpython-313.pyc`
```diff
commit fd65bd9b0b2f9206b0aef950688557430603e313
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Fri Apr 24 16:19:33 2026 -0300

     feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
    
    backend: agrega módulos de tickets, dashboard, reportes, settings y notificaciones (api, servicios, repos, esquemas, modelos y tests)
    backend: actualiza tareas/material-flow, bootstrap y validaciones de acceso/errores
    db: incorpora scripts SQL de ticket module y notificaciones
    frontend: implementa módulos de reports y settings y amplía flujos de tickets/tasks/dashboard
    frontend: habilita PWA (manifest, service worker, iconos y update service)
    docs: agrega guía DEPLOY.md para producción en servidor central
    chore: incluye assets y artefactos de soporte utilizados durante la integración

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/notifications.cpython-313.pyc differ
```

