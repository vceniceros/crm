# Historial de Cambios de Código (Últimos 7 días)

> Este documento contiene los diffs de código para análisis técnico.

## Commit: ce43f62
**Autor:** Valentino_Colella
**Fecha:** Sat Apr 25 11:36:43 2026 -0300
**Mensaje:** subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

### Cambios por archivo:
#### 📄 `DEPLOY.md`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/DEPLOY.md
+++ b/DEPLOY.md
@@ -1,1432 +1,331 @@
-# DEPLOY.md — Producción CRM MicroTV
+﻿# DEPLOY.md — Producción CRM YCC con Auth Interno
 
-**Versión:** 1.0  
-**Fecha:** 2026-04-24  
-**Audiencia:** Sudoers en `/opt/ycc`  
-**Entorno:** Ubuntu Server / Debian compatible  
+## 1) Objetivo y alcance
+Este deploy levanta una instancia **independiente** de autenticación para CRM YCC.
 
----
+- No reemplaza ni modifica auth operativo de MicroTV/Starlink.
+- Puede convivir en el mismo servidor con otros auth, en puertos/procesos distintos.
+- Mantiene separación de dominios:
+  - Auth interno CRM: identidad, login, usuarios, roles base, JWT.
+  - Backend CRM: permisos funcionales CRM, tickets, tareas, stock, clientes.
 
-## 📋 Tabla de contenidos
-
-1. [Supuestos del entorno](#supuestos-del-entorno)
-2. [Estructura de directorios](#estructura-de-directorios-en-servidor)
-3. [Pre-deploy: Preparación del servidor](#pre-deploy-preparación-del-servidor)
-4. [PostgreSQL: Base de datos](#postgresql-base-de-datos)
-5. [Backend: FastAPI](#backend-fastapi)
-6. [Frontend: Angular](#frontend-angular)
-7. [Nginx: Reverse proxy](#nginx-reverse-proxy)
-8. [Systemd: Proceso backend](#systemd-proceso-backend)
-9. [HTTPS/SSL](#httpsssl-certbot)
-10. [Verificación post-deploy](#verificación-post-deploy)
-11. [Backups](#backups)
-12. [Actualización de versión](#actualización-de-versión)
-13. [Rollback](#rollback)
-14. [Troubleshooting](#troubleshooting)
-
----
-
-## Supuestos del entorno
-
-```
-Usuario deploy:        sudoer (capaz de ejecutar sudo sin contraseña)
-Home deploy:           /opt/ycc
-Sistema operativo:     Ubuntu Server 20.04 LTS o superior / Debian 11+
-Backend:               FastAPI (uvicorn ASGI)
-Frontend:              Angular 21.2
-Base de datos:         PostgreSQL 16
-Reverse proxy:         Nginx
-Proceso backend:       systemd (ycc-crm-backend)
-Frontend estático:     Nginx (SPA con service worker)
-Dominio producción:    crm.microtv.ar (REEMPLAZAR CON DOMINIO REAL)
-Auth externo:          https://auth.microtv.ar
-```
-
-**⚠️ Si alguno de estos supuestos es incorrecto, ajustar ahora antes de continuar.**
-
----
-
-## Estructura de directorios en servidor
+## 2) Layout recomendado
 
+```text
+/opt/ycc/crm/
+  microtv-crm-ycc/
+    auth.microtv.ar/
+      backend/
+    microtv-crm-backend/
+    microtv-crm-frontend/
+    lab/
+  logs/
+    crm-backend/
+    crm-auth/
+    nginx/
 ```
-/opt/ycc/
-├── crm/
-│   ├── backend/
-│   │   ├── .env                    # Variables de entorno (NO COMMITEAR)
-│   │   ├── .git/
-│   │   ├── venv/                   # Python virtualenv
-│   │   ├── src/crm
... (código truncado por longitud) ...
```

#### 📄 `auth.microtv.ar`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 160000
--- /dev/null
+++ b/auth.microtv.ar
@@ -0,0 +1 @@
+Subproject commit 946d8b5cd54e702275161590187a5fa747198cd4
```

#### 📄 `historial_completo_para_gpt_crm.md`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/historial_completo_para_gpt_crm.md
+++ b/historial_completo_para_gpt_crm.md
@@ -2,29523 +2,556 @@
 
 > Este documento contiene los diffs de código para análisis técnico.
 
-## Commit: a13ef83
+## Commit: fd65bd9
 **Autor:** Valentino_Colella
-**Fecha:** Sat Apr 18 11:40:02 2026 -0300
-**Mensaje:** se avanza en la implementacion de backend y bdd integrando el modulo de tareas
+**Fecha:** Fri Apr 24 16:19:33 2026 -0300
+**Mensaje:**  feat(crm): integrar tickets end-to-end, reportes, settings, notificaciones y deploy productivo
 
 ### Cambios por archivo:
-- *.vscode/settings.json (Omitido por extensión)*
-#### 📄 `ENTORNO_DE_DEV.md`
+#### 📄 `DEPLOY.md`
 ```diff
-commit a13ef83257a56970f36eb8355eb19e286fa3d1f9
+commit fd65bd9b0b2f9206b0aef950688557430603e313
 Author: Valentino_Colella <valentinocolella@microtv.com.ar>
-Date:   Sat Apr 18 11:40:02 2026 -0300
+Date:   Fri Apr 24 16:19:33 2026 -0300
 
-    se avanza en la implementacion de backend y bdd integrando el modulo de tareas
-
-new file mode 100644
---- /dev/null
-+++ b/ENTORNO_DE_DEV.md
-@@ -0,0 +1,269 @@
-+# Entorno de desarrollo
-+
-+Este documento deja cerrado el flujo inicial de login para probarlo localmente en Windows con PowerShell.
-+
-+## 1. Requisitos previos
-+
-+- Docker Desktop levantado.
-+- Python 3.12 disponible en `PATH`.
-+- Node.js 20+ y `npm`.
-+- Puertos libres: `4200`, `8001`, `8010`.
-+
-+## 2. Levantar auth.microtv.ar local con seed
-+
-+Parate en la raíz del workspace `microtv-crm-ycc`:
-+
-+```powershell
-+Set-Location "e:\Documentos SYNC\gitlab clones\microtv-crm-ycc"
-+docker compose -f microtv-crm-backend\docker-compose.auth-local.yml up --build
-+```
-+
-+Qué hace este compose:
-+
-+- levanta PostgreSQL local de auth sólo para la red interna de Docker
-+- construye un contenedor específico para CRM usando `microtv-crm-backend/docker/auth-local/Dockerfile`
-+- corre migraciones de auth
-+- ejecuta el seed del CRM
-+- expone auth en `http://localhost:8001`
-+
-+## 3. Usuarios seed creados en la base local de auth
-+
-+Estos usuarios quedan creados automáticamente en `auth_microtv`:
-+
-+### Admin MicroTV
-+
-+- Email: `admin.crm@microtv.com`
-+- Password: `Passw0rd!`
-+- Display name: `Admin MicroTV`
-+- Tenant: `MICROTV`
-+- Rol en auth: `platform_admin`
-+- Bootstrap de rol local CRM esperado: `admin`
-+
-+### Operador YCC Brothers
-+
-+- Email: `operador.crm@yccbrothers.com`
-+- Password: `Passw0rd!`
-+- Display name: `Operador YCC Brothers`
-+- Tenant: `YCC`
-+- Rol en auth: `company_operator`
-+- Bootstrap de rol local CRM esperado: `deposito`
-+
-+### Auxiliar Depósito YCC Brothers
-+
-+- Email: `d
... (código truncado por longitud) ...
```

#### 📄 `lab/crm_backend.bat`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/lab/crm_backend.bat
+++ b/lab/crm_backend.bat
@@ -50,6 +50,24 @@ if not exist ".env" (
     echo   [*] .env existente encontrado, no se sobreescribe.
 )
 
+:: -- Forzar variables de auth internas para el lab
+set "AUTH_BASE_URL=http://localhost:8001"
+set "AUTH_LOGIN_PATH=/v1/auth/login"
+set "AUTH_TIMEOUT_SECONDS=10"
+set "AUTH_JWT_SECRET=change-me"
+set "AUTH_JWT_ALGORITHM=HS256"
+set "AUTH_JWT_ISSUER=auth.crm.ycc.internal"
+set "AUTH_JWT_AUDIENCE=microtv-platform"
+set "AUTO_PROVISION_CRM_ROLE=true"
+set "DEFAULT_ADMIN_AUTH_ROLES=admin,platform_admin,company_admin"
+set "DEFAULT_DEPOSITO_AUTH_ROLES=operador_deposito,company_operator"
+set "DEFAULT_TECH_AUTH_ROLES=tecnico_campo"
+
+echo   [*] Auth lab interno forzado por entorno:
+echo       AUTH_BASE_URL=%AUTH_BASE_URL%
+echo       AUTH_JWT_ISSUER=%AUTH_JWT_ISSUER%
+echo       DEFAULT_ADMIN_AUTH_ROLES=%DEFAULT_ADMIN_AUTH_ROLES%
+
 :: -- Instalar dependencias
 echo.
 echo   [*] Instalando / verificando dependencias (pip install -e .[test])...
```

#### 📄 `lab/verify_internal_auth.ps1`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/lab/verify_internal_auth.ps1
@@ -0,0 +1,55 @@
+param(
+    [string]$AdminEmail = "admin@ycc.local",
+    [string]$AdminPassword = "changeme-secure-password",
+    [string]$BaseAuthUrl = "http://localhost:8001",
+    [string]$BaseCrmUrl = "http://localhost:8010"
+)
+
+$ErrorActionPreference = "Stop"
+
+Write-Host "[1/7] Healthcheck auth interno..."
+$authHealth = Invoke-RestMethod -Uri "$BaseAuthUrl/health" -Method Get
+if ($authHealth.status -ne "ok") { throw "Auth healthcheck failed" }
+
+Write-Host "[2/7] Login vía CRM backend..."
+$loginBody = @{ email = $AdminEmail; password = $AdminPassword } | ConvertTo-Json
+$loginResponse = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
+if ($loginResponse.status -ne "authenticated") { throw "CRM login failed" }
+
+$token = $loginResponse.tokens.access_token
+if (-not $token) { throw "No access token received" }
+
+$headers = @{ Authorization = "Bearer $token" }
+
+Write-Host "[3/7] Token aceptado por backend CRM (/auth/me)..."
+$me = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/me" -Method Get -Headers $headers
+if ($me.status -ne "authenticated") { throw "CRM /auth/me rejected token" }
+
+Write-Host "[4/7] Menú de gestión de usuarios (API settings/auth-users)..."
+$users = Invoke-RestMethod -Uri "$BaseCrmUrl/settings/auth-users" -Method Get -Headers $headers
+if ($null -eq $users) { throw "Auth users endpoint failed" }
+
+Write-Host "[5/7] Crear usuario operativo de prueba..."
+$timestamp = Get-Date -Format "yyyyMMddHHmmss"
+$newEmail = "qa.user.$timestamp@ycc.local"
+$newUserBody = @{
+    email = $newEmail
+    display_name = "QA User $timestamp"
+    password = "Passw0rd!qa"
+    is_active = $true
+    roles = @("operador_deposito")
+} | ConvertTo-Json
+$newUser = Invoke-RestMethod -Uri "$BaseCrmUrl/settings/auth-users" -Method Post -Headers $headers -ContentType "application/json" -Body $newUserBody
+if ($newUser.email -ne $newEmail) { throw "User create failed" }
+
+Write-Host "[6/7] Login del usuario creado en auth interno..."
+$newLoginBody = @{ email = $newEmail; password = "Passw0rd!qa" } | ConvertTo-Json
+$newLogin = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/login" -Method Post -ContentType "application/json" -Body $newLoginBody
+if ($newLogin.status -ne "authenticated") { throw "New user login failed" }
+
+Write-Host "[7/7] Re-ejecutar bootstrap idempotente dentro del contenedor auth..."
+$bootstrapResult = docker exec crm-auth-local python -m src.cli ensure_crm_bootstrap
+if ($LASTEXITCODE -ne 0) { throw "Bootstrap command failed" }
+
+Wr
... (código truncado por longitud) ...
```

#### 📄 `lab_deploy.md`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/lab_deploy.md
+++ b/lab_deploy.md
@@ -2,7 +2,7 @@
 
 ## 1. Propósito
 
-Este documento describe el entorno de laboratorio local que permite probar el stack completo del CRM contra un servicio de autenticación real y una base de datos de prueba, sin depender de entornos externos.
+Este documento describe el entorno de laboratorio local que permite probar el stack completo del CRM contra una instancia interna de autenticación y una base de datos de prueba, sin depender de repositorios externos.
 
 El laboratorio replica el flujo de producción completo:
 - auth.microtv (servicio de identidad y JWT)
@@ -36,17 +36,9 @@ El laboratorio replica el flujo de producción completo:
 
 > `curl` ya viene incluido en Windows 10 versión 1803 en adelante. No requiere instalación adicional.
 
-### Repositorios requeridos
+### Repositorio requerido
 
-Ambos repositorios deben estar clonados **en el mismo directorio padre**:
-
-```
-[raiz_comun]\
-    auth.microtv.ar\      <- repo separado
-    microtv-crm-ycc\      <- este repo
-```
-
-El Docker Compose de auth usa `context: ../..` (relativo al archivo compose dentro de `microtv-crm-ycc/microtv-crm-backend/`), lo que resuelve a `[raiz_comun]\`. El Dockerfile dentro de ese contexto copia desde `auth.microtv.ar/backend/`.
+Solo se requiere este repositorio (`microtv-crm-ycc`), que ya contiene la copia interna de `auth.microtv.ar` en la subcarpeta local.
 
 ### Variables de entorno
 
@@ -57,11 +49,11 @@ DATABASE_URL=postgresql+psycopg://crmmicrotv:crmmicrotv@localhost:5433/crm_micro
 AUTH_BASE_URL=http://localhost:8001
 AUTH_JWT_SECRET=change-me
 AUTH_JWT_ALGORITHM=HS256
-AUTH_JWT_ISSUER=auth.microtv.ar
+AUTH_JWT_ISSUER=auth.crm.ycc.internal
 AUTH_JWT_AUDIENCE=microtv-platform
 ```
 
-> `AUTH_JWT_SECRET=change-me` debe coincidir con el `JWT_SECRET` del contenedor auth
+> `AUTH_JWT_SECRET=change-me` debe coincidir con el `JWT_SECRET` del contenedor auth interno
 > (definido en `docker-compose.auth-local.yml`, valor: `change-me`).
 > No cambies uno sin cambiar el otro.
 
@@ -162,17 +154,20 @@ Abierto automáticamente por `lab_start.bat`.
 Define tres servicios:
 - `auth-db`: PostgreSQL 16 Alpine, datos en volumen `crm-auth-db-data`, healthcheck cada 5s.
 - `crm-backend-db`: PostgreSQL 16 Alpine, datos en volumen `crm-backend-db-data`, expuesto en `localhost:5433`, healthcheck cada 5s.
-- `auth-local`: imagen construida desde `docker/auth-local/Dockerfile`, depende de `auth-db` con `condition: service_healthy`.
+- `auth-local`: imagen construida desde `docker/auth-local/Dockerfile`, depende de `auth-db` con `condition: service_healthy` y expone healthcheck prop
... (código truncado por longitud) ...
```

#### 📄 `lab_start.bat`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/lab_start.bat
+++ b/lab_start.bat
@@ -4,8 +4,8 @@ setlocal enabledelayedexpansion
 :: =========================================================
 ::  MicroTV CRM - Laboratorio Local
 ::  Levanta el stack completo de pruebas:
-::    1. PostgreSQL de auth  (Docker)
-::    2. auth.microtv        (Docker, puerto 8001)
+::    1. PostgreSQL de auth interno (Docker)
+::    2. auth interno CRM          (Docker, puerto 8001)
 ::    3. CRM Backend         (Python/uvicorn, puerto 8010)
 ::    4. CRM Frontend        (Angular ng serve, puerto 4200)
 :: =========================================================
@@ -40,8 +40,8 @@ if errorlevel 1 (
 echo   OK - Docker activo.
 echo.
 
-:: ---- 2. Levantar auth local + PostgreSQL CRM -------------------
-echo [2/6] Levantando auth.microtv + PostgreSQL de laboratorio (Docker Compose)...
+:: ---- 2. Levantar auth interno + PostgreSQL CRM ------------------
+echo [2/6] Levantando auth interno CRM + PostgreSQL de laboratorio (Docker Compose)...
 echo   Compose: %COMPOSE_DIR%\docker-compose.auth-local.yml
 echo.
 docker compose -f "%COMPOSE_DIR%\docker-compose.auth-local.yml" up --build -d
@@ -49,13 +49,9 @@ if errorlevel 1 (
     echo.
     echo   ERROR: docker compose fallo. Revisa el output arriba.
     echo.
-    echo   Causa frecuente: auth.microtv.ar debe estar clonado
-    echo   en el mismo directorio padre que microtv-crm-ycc.
-    echo   Ejemplo:
-    echo     C:\repos\auth.microtv.ar\
-    echo     C:\repos\microtv-crm-ycc\    <- ejecutas desde aqui
-    echo.
-    echo   Ver: lab_deploy.md - seccion Troubleshooting
+    echo   Causa frecuente: revisar rutas/build-context en docker-compose
+    echo   y que exista la carpeta interna auth.microtv.ar dentro de este repo.
+    echo   Ver: lab_deploy.md - seccion Troubleshooting.
     echo.
     pause
     exit /b 1
@@ -117,9 +113,9 @@ if /I "%CRM_SCHEMA_READY%"=="READY" (
 echo.
 
 :: ---- 5. Abrir terminal de logs de auth --------------------------
-echo [5/6] Abriendo logs de auth.microtv en ventana separada...
-start "auth.microtv logs [8001]" /d "%COMPOSE_DIR%" cmd /k docker compose -f docker-compose.auth-local.yml logs -f auth-local
-echo   Ventana: "auth.microtv logs [8001]"
+echo [5/6] Abriendo logs de auth interno CRM en ventana separada...
+start "Auth interno CRM logs [8001]" /d "%COMPOSE_DIR%" cmd /k docker compose -f docker-compose.auth-local.yml logs -f auth-local
+echo   Ventana: "Auth interno CRM logs [8001]"
 echo.
 
 :: ---- 5a. Esperar que auth responda (healthcheck) ----------------
@@ -131,8 +127,8 @@ set HTTP_CODE=000
 set /a RETRIES=RETRIES+1
 if %RETRIES% GTR 40 (
     echo.
- 
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/.env.example`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/.env.example
+++ b/microtv-crm-backend/.env.example
@@ -11,9 +11,10 @@ AUTH_LOGIN_PATH=/v1/auth/login
 AUTH_TIMEOUT_SECONDS=10
 AUTH_JWT_SECRET=change-me
 AUTH_JWT_ALGORITHM=HS256
-AUTH_JWT_ISSUER=auth.microtv.ar
+AUTH_JWT_ISSUER=auth.crm.ycc.internal
 AUTH_JWT_AUDIENCE=microtv-platform
 
 AUTO_PROVISION_CRM_ROLE=true
-DEFAULT_ADMIN_AUTH_ROLES=platform_admin,company_admin
-DEFAULT_TECH_AUTH_ROLES=company_operator
+DEFAULT_ADMIN_AUTH_ROLES=admin,platform_admin,company_admin
+DEFAULT_DEPOSITO_AUTH_ROLES=operador_deposito,company_operator
+DEFAULT_TECH_AUTH_ROLES=tecnico_campo
```

#### 📄 `microtv-crm-backend/docker-compose.auth-local.yml`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/docker-compose.auth-local.yml
+++ b/microtv-crm-backend/docker-compose.auth-local.yml
@@ -16,8 +16,8 @@ services:
 
   auth-local:
     build:
-      context: ../..
-      dockerfile: microtv-crm-ycc/microtv-crm-backend/docker/auth-local/Dockerfile
+      context: ..
+      dockerfile: microtv-crm-backend/docker/auth-local/Dockerfile
     container_name: crm-auth-local
     depends_on:
       auth-db:
@@ -26,10 +26,16 @@ services:
       DATABASE_URL: postgresql+psycopg://authmicrotv:authmicrotv@auth-db:5432/auth_microtv
       JWT_SECRET: change-me
       JWT_ALGORITHM: HS256
+      JWT_ISSUER: auth.crm.ycc.internal
       JWT_AUDIENCE: microtv-platform
       ALLOWED_ORIGINS: http://localhost:4200,http://localhost:5173,http://localhost:8010
-      CRM_LOCAL_ADMIN_EMAIL: admin.crm@microtv.com
-      CRM_LOCAL_ADMIN_PASSWORD: Passw0rd!
+      CRM_AUTH_TENANT_TYPE: company
+      CRM_AUTH_TENANT_ID: YCC
+      CRM_AUTH_ADMIN_EMAIL: admin@ycc.local
+      CRM_AUTH_ADMIN_PASSWORD: changeme-secure-password
+      CRM_AUTH_ADMIN_NAME: Administrador CRM
+      CRM_LOCAL_ADMIN_EMAIL: admin@ycc.local
+      CRM_LOCAL_ADMIN_PASSWORD: changeme-secure-password
       CRM_LOCAL_YCC_EMAIL: operador.crm@yccbrothers.com
       CRM_LOCAL_YCC_PASSWORD: Passw0rd!
       CRM_LOCAL_YCC_AUX_EMAIL: deposito.aux@yccbrothers.com
@@ -39,6 +45,11 @@ services:
       CRM_LOCAL_YCC_TECH_EMAIL: tecnico.campo@yccbrothers.com
       CRM_LOCAL_YCC_TECH_PASSWORD: Passw0rd!
       CRM_LOCAL_YCC_TECH_USER_ID: auth-user-ycc-tech-001
+    healthcheck:
+      test: ["CMD-SHELL", "wget -q -O - http://127.0.0.1:8001/health >/dev/null 2>&1 || exit 1"]
+      interval: 5s
+      timeout: 5s
+      retries: 20
     ports:
       - "8001:8001"
```

#### 📄 `microtv-crm-backend/docker/auth-local/Dockerfile`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/docker/auth-local/Dockerfile
+++ b/microtv-crm-backend/docker/auth-local/Dockerfile
@@ -6,7 +6,7 @@ ENV PYTHONDONTWRITEBYTECODE=1 \
 WORKDIR /app
 
 COPY auth.microtv.ar/backend/ /app/
-COPY microtv-crm-ycc/microtv-crm-backend/docker/auth-local/seed_crm_auth.py /opt/seed/seed_crm_auth.py
+COPY microtv-crm-backend/docker/auth-local/seed_crm_auth.py /opt/seed/seed_crm_auth.py
 
 RUN rm -f /app/.env
 
@@ -16,4 +16,4 @@ RUN pip install --no-cache-dir --upgrade pip \
 
 EXPOSE 8001
 
-CMD ["sh", "-c", "alembic upgrade head && python /opt/seed/seed_crm_auth.py && uvicorn src.main:app --host 0.0.0.0 --port 8001"]
+CMD ["sh", "-c", "alembic upgrade head && python -m src.cli ensure_crm_bootstrap && python /opt/seed/seed_crm_auth.py && uvicorn src.main:app --host 0.0.0.0 --port 8001"]
```

#### 📄 `microtv-crm-backend/docker/auth-local/seed_crm_auth.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/docker/auth-local/seed_crm_auth.py
+++ b/microtv-crm-backend/docker/auth-local/seed_crm_auth.py
@@ -1,4 +1,4 @@
-"""Script de seed para el entorno local de auth del CRM."""
+"""Script de seed para el entorno local de auth interno del CRM."""
 
 from __future__ import annotations
 
@@ -165,8 +165,10 @@ def main() -> None:
     database_url = normalize_database_url(
         os.getenv("DATABASE_URL", "postgresql+psycopg://authmicrotv:authmicrotv@localhost:5432/auth_microtv")
     )
-    admin_email = os.getenv("CRM_LOCAL_ADMIN_EMAIL", "admin.crm@microtv.com")
-    admin_password = os.getenv("CRM_LOCAL_ADMIN_PASSWORD", "Passw0rd!")
+    admin_email = os.getenv("CRM_AUTH_ADMIN_EMAIL", os.getenv("CRM_LOCAL_ADMIN_EMAIL", "admin@ycc.local"))
+    admin_password = os.getenv("CRM_AUTH_ADMIN_PASSWORD", os.getenv("CRM_LOCAL_ADMIN_PASSWORD", "changeme-secure-password"))
+    admin_name = os.getenv("CRM_AUTH_ADMIN_NAME", "Administrador CRM")
+    tenant_id = os.getenv("CRM_AUTH_TENANT_ID", "YCC")
     ycc_email = os.getenv("CRM_LOCAL_YCC_EMAIL", "operador.crm@yccbrothers.com")
     ycc_password = os.getenv("CRM_LOCAL_YCC_PASSWORD", "Passw0rd!")
     ycc_aux_email = os.getenv("CRM_LOCAL_YCC_AUX_EMAIL", "deposito.aux@yccbrothers.com")
@@ -179,18 +181,24 @@ def main() -> None:
 
     with psycopg.connect(database_url) as connection:
         with connection.cursor() as cursor:
-            platform_admin_role_id = ensure_role(cursor, "platform_admin")
-            company_operator_role_id = ensure_role(cursor, "company_operator")
+            admin_role_id = ensure_role(cursor, "admin")
+            operator_role_id = ensure_role(cursor, "operador_deposito")
             ejecutivo_role_id = ensure_role(cursor, "ejecutivo")
+            tecnico_role_id = ensure_role(cursor, "tecnico_campo")
 
-            microtv_company_id = ensure_company(cursor, company_id="MICROTV", company_name="MicroTV")
-            ycc_company_id = ensure_company(cursor, company_id="YCC", company_name="YCC Brothers")
+            # Keep legacy roles available for compatibility with historic flows/tests.
+            ensure_role(cursor, "platform_admin")
+            ensure_role(cursor, "company_operator")
+            ensure_role(cursor, "company_admin")
+
+            ensure_company(cursor, company_id="MICROTV", company_name="MicroTV")
+            ycc_company_id = ensure_company(cursor, company_id=tenant_id, company_name="YCC Brothers")
 
             admin_user_id = ensure_user(
                 cursor,
                 email=admin_email,
                 password=admin_password,
-                display
... (código truncado por longitud) ...
```

- *microtv-crm-backend/public/images/task/18e4db44c89a4f66b99816d5530e732a.jpg (Omitido por extensión)*
- *microtv-crm-backend/public/images/task/d05e7c1a10404207b377fb644f732c2b.jpg (Omitido por extensión)*
#### 📄 `microtv-crm-backend/public/videos/task/42c92edb5848469aadbf3888c43ade9e.mp4`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/public/videos/task/42c92edb5848469aadbf3888c43ade9e.mp4 differ
```

#### 📄 `microtv-crm-backend/public/videos/task/669ac6cc131a4026bfccaf066f7af13d.mp4`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/public/videos/task/669ac6cc131a4026bfccaf066f7af13d.mp4 differ
```

#### 📄 `microtv-crm-backend/public/videos/task/dbeb27d4fad840fe94ca7be9c0f1a2e5.mp4`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/public/videos/task/dbeb27d4fad840fe94ca7be9c0f1a2e5.mp4 differ
```

#### 📄 `microtv-crm-backend/pyproject.toml`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/pyproject.toml
+++ b/microtv-crm-backend/pyproject.toml
@@ -18,6 +18,8 @@ dependencies = [
     "httpx>=0.28,<1.0",
     "pyjwt>=2.10,<3.0",
     "python-dotenv>=1.1,<2.0",
+    "reportlab>=4.0,<5.0",
+    "Pillow>=10.0,<12.0",
 ]
 
 [project.optional-dependencies]
```

#### 📄 `microtv-crm-backend/src/crm_backend/adapters/__pycache__/auth_service_adapter.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/adapters/__pycache__/auth_service_adapter.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/adapters/__pycache__/auth_service_adapter.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/adapters/auth_service_adapter.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/adapters/auth_service_adapter.py
+++ b/microtv-crm-backend/src/crm_backend/adapters/auth_service_adapter.py
@@ -84,6 +84,15 @@ class AccessPendingResult:
     user_type: str
 
 
+@dataclass(slots=True)
+class AuthManagedUser:
+    user_id: str
+    email: str
+    display_name: str
+    is_active: bool
+    roles: list[str]
+
+
 class AuthServiceAdapter:
     """Encapsulate the HTTP and JWT contract of auth.microtv.ar."""
 
@@ -264,3 +273,106 @@ class AuthServiceAdapter:
             return "El servicio auth devolvió una respuesta no parseable."
         detail = payload.get("detail")
         return str(detail) if detail else "El servicio auth rechazó la solicitud."
+
+    def list_managed_users(self, access_token: str) -> list[AuthManagedUser]:
+        payload = self._call_crm_admin("GET", "/v1/crm-admin/users", access_token=access_token)
+        if not isinstance(payload, list):
+            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al listar usuarios.")
+        return [self._build_managed_user(item) for item in payload if isinstance(item, dict)]
+
+    def create_managed_user(
+        self,
+        *,
+        access_token: str,
+        email: str,
+        display_name: str,
+        password: str,
+        is_active: bool,
+        roles: list[str],
+    ) -> AuthManagedUser:
+        payload = self._call_crm_admin(
+            "POST",
+            "/v1/crm-admin/users",
+            access_token=access_token,
+            body={
+                "email": email,
+                "display_name": display_name,
+                "password": password,
+                "is_active": is_active,
+                "roles": roles,
+            },
+        )
+        if not isinstance(payload, dict):
+            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al crear usuario.")
+        return self._build_managed_user(payload)
+
+    def update_managed_user(self, *, access_token: str, user_id: str, email: str, display_name: str) -> AuthManagedUser:
+        payload = self._call_crm_admin(
+            "PUT",
+            f"/v1/crm-admin/users/{user_id}",
+            access_token=access_token,
+            body={"email": email, "display_name": display_name},
+        )
+        if not isinstance(payload, dict):
+            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al actualizar usuario.")
+        return self._build_managed_user(payload)
+
+    def set_managed_user_status(self, *, access_token: str, user_id: str, is_active: bool) -> AuthManagedUser:
+       
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/__pycache__/dependencies.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/api/__pycache__/dependencies.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/api/__pycache__/dependencies.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/__pycache__/router.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/api/__pycache__/router.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/api/__pycache__/router.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/dependencies.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/api/dependencies.py
+++ b/microtv-crm-backend/src/crm_backend/api/dependencies.py
@@ -370,3 +370,24 @@ def get_settings_service(session: Session = Depends(get_db_session)) -> Settings
     """Provide the settings service."""
 
     return SettingsService(session)
+
+
+def get_satisfaction_form_service(
+    session: Session = Depends(get_db_session),
+    settings: Settings = Depends(get_settings),
+) -> "PublicSatisfactionFormService":
+    """Provide the satisfaction form service."""
+    from crm_backend.services.satisfaction_form_service import PublicSatisfactionFormService  # noqa: PLC0415
+    return PublicSatisfactionFormService(
+        session=session,
+        satisfaction_media_dir=settings.satisfaction_media_dir,
+        expiry_hours=settings.satisfaction_form_expiry_hours,
+    )
+
+
+def get_ticket_export_service(
+    settings: Settings = Depends(get_settings),
+) -> "TicketExportService":
+    """Provide the ticket export service."""
+    from crm_backend.services.ticket_export_service import TicketExportService  # noqa: PLC0415
+    return TicketExportService(media_base_dir=settings.public_dir)
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/public_tickets.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/public_tickets.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/settings.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/settings.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/settings.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tickets.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tickets.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tickets.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/public_tickets.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/public_tickets.py
@@ -0,0 +1,130 @@
+"""Public (unauthenticated) ticket satisfaction endpoints.
+
+These endpoints are accessible without a JWT — the token in the URL path
+acts as the credential. All token lookups return generic errors to prevent
+information leakage.
+"""
+
+from __future__ import annotations
+
+from typing import Annotated
+
+from fastapi import APIRouter, Depends, File, Request, UploadFile
+
+from crm_backend.api.dependencies import get_satisfaction_form_service
+from crm_backend.schemas.tickets import (
+    PublicSatisfactionFormInfoResponse,
+    SatisfactionResponseDetailResponse,
+    SubmitSatisfactionFormRequest,
+)
+from crm_backend.services.satisfaction_form_service import PublicSatisfactionFormService
+
+router = APIRouter(prefix="/public/tickets", tags=["public-tickets"])
+
+
+def _get_client_ip(request: Request) -> str | None:
+    forwarded_for = request.headers.get("X-Forwarded-For")
+    if forwarded_for:
+        return forwarded_for.split(",")[0].strip()
+    return request.client.host if request.client else None
+
+
+@router.get(
+    "/satisfaction/{token}",
+    response_model=PublicSatisfactionFormInfoResponse,
+    responses={404: {"description": "Form not found, expired or already used"}},
+    summary="Get public satisfaction form info",
+)
+def get_public_satisfaction_form(
+    token: str,
+    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
+) -> PublicSatisfactionFormInfoResponse:
+    """Return minimal safe ticket info for the public satisfaction survey.
+
+    No IDs, no sensitive data exposed. Token is validated server-side.
+    """
+    form = sat_service.get_public_form_info(token)
+    ticket = form.ticket
+    client_name: str | None = None
+    location_name: str | None = None
+
+    if ticket:
+        if ticket.client:
+            client_name = getattr(ticket.client, "business_name", None) or getattr(ticket.client, "company_name", None)
+        if ticket.location:
+            location_name = getattr(ticket.location, "address", None) or getattr(ticket.location, "name", None)
+
+    return PublicSatisfactionFormInfoResponse(
+        ticket_number=str(ticket.ticket_number) if ticket else "—",
+        client_name=client_name,
+        location_name=location_name,
+        status_label=form.status_label,
+    )
+
+
+@router.post(
+    "/satisfaction/{token}",
+    response_model=SatisfactionResponseDetailResponse,
+    responses={404: {"description": "Form not found, expired or already used"}, 409: {"descr
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/settings.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/api/endpoints/settings.py
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/settings.py
@@ -4,9 +4,17 @@ from __future__ import annotations
 
 from fastapi import APIRouter, Depends, Query
 
-from crm_backend.api.dependencies import get_authenticated_crm_session, get_settings_service
+from crm_backend.adapters.auth_service_adapter import AuthManagedUser, AuthServiceAdapter
+from crm_backend.api.dependencies import get_auth_service_adapter, get_authenticated_crm_session, get_settings_service
+from crm_backend.core.exceptions import ApplicationError
 from crm_backend.schemas import ErrorResponse
 from crm_backend.schemas.settings import (
+    SettingsAuthUserCreateRequest,
+    SettingsAuthUserResetPasswordRequest,
+    SettingsAuthUserResponse,
+    SettingsAuthUserRolesRequest,
+    SettingsAuthUserStatusRequest,
+    SettingsAuthUserUpdateRequest,
     SettingsCategoryResponse,
     SettingsCategoryWriteRequest,
     SettingsNotificationRuleResponse,
@@ -31,6 +39,22 @@ from crm_backend.services.settings_service import SettingsService
 router = APIRouter(prefix="/settings", tags=["settings"])
 
 
+def _require_admin(actor: ResolvedCrmSession) -> None:
+    if "admin" in actor.role_keys:
+        return
+    raise ApplicationError("settings_admin_required", "La operación requiere rol administrador.", 403)
+
+
+def _map_auth_managed_user(user: AuthManagedUser) -> SettingsAuthUserResponse:
+    return SettingsAuthUserResponse(
+        user_id=user.user_id,
+        email=user.email,
+        display_name=user.display_name,
+        is_active=user.is_active,
+        roles=user.roles,
+    )
+
+
 @router.get("/roles", response_model=list[SettingsRoleResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
 def list_roles(
     actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
@@ -253,3 +277,96 @@ def update_notification_rule(
     settings_service: SettingsService = Depends(get_settings_service),
 ) -> SettingsNotificationRuleResponse:
     return SettingsNotificationRuleResponse.model_validate(settings_service.update_notification_rule(actor, rule_id, payload))
+
+
+@router.get("/auth-users", response_model=list[SettingsAuthUserResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
+def list_auth_users(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
+) -> list[SettingsAuthUserResponse]:
+    _require_admin(actor)
+    users = auth_adapter.list_managed_users(actor.auth_res
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/tickets.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/api/endpoints/tickets.py
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/tickets.py
@@ -3,8 +3,14 @@
 from typing import Annotated
 
 from fastapi import APIRouter, Depends, File, Response, UploadFile, status
+from fastapi.responses import StreamingResponse
 
-from crm_backend.api.dependencies import get_authenticated_crm_session, get_ticket_application_service
+from crm_backend.api.dependencies import (
+    get_authenticated_crm_session,
+    get_satisfaction_form_service,
+    get_ticket_application_service,
+    get_ticket_export_service,
+)
 from crm_backend.schemas import (
     ApproveTicketRequest,
     AssignTicketRequest,
@@ -20,13 +26,32 @@ from crm_backend.schemas import (
     TicketSummaryResponse,
     UpdateTicketStatusRequest,
 )
+from crm_backend.schemas.tickets import (
+    GenerateSatisfactionFormResponse,
+    RegisterArrivalRequest,
+    SatisfactionFormStatusResponse,
+    SatisfactionResponseDetailResponse,
+)
 from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.satisfaction_form_service import PublicSatisfactionFormService
+from crm_backend.services.ticket_export_service import TicketExportService
 from crm_backend.services.ticket_service import TicketApplicationService
 
 
 router = APIRouter(prefix="/tickets", tags=["tickets"])
 
 
+def _to_ticket_detail_response(
+    *,
+    actor: ResolvedCrmSession,
+    ticket_service: TicketApplicationService,
+    ticket,
+) -> TicketDetailResponse:
+    setattr(ticket, "has_arrival_registered", ticket_service.has_arrival_registered(ticket))
+    setattr(ticket, "can_register_arrival", ticket_service.can_register_arrival(actor, ticket))
+    return TicketDetailResponse.model_validate(ticket)
+
+
 @router.get(
     "/roles",
     response_model=list[TicketRoleOptionResponse],
@@ -57,7 +82,8 @@ def create_ticket(
     actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
     ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
 ) -> TicketDetailResponse:
-    return TicketDetailResponse.model_validate(ticket_service.create_ticket(actor, payload))
+    ticket = ticket_service.create_ticket(actor, payload)
+    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)
 
 
 @router.get(
@@ -118,7 +144,8 @@ def get_ticket_detail(
     actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
     ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
 ) -> TicketDetailResponse:
-    return TicketDetailResponse.model_valida
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/router.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/api/router.py
+++ b/microtv-crm-backend/src/crm_backend/api/router.py
@@ -15,6 +15,7 @@ from crm_backend.api.endpoints.settings import router as settings_router
 from crm_backend.api.endpoints.stock import router as stock_router
 from crm_backend.api.endpoints.tasks import router as tasks_router
 from crm_backend.api.endpoints.tickets import router as tickets_router
+from crm_backend.api.endpoints.public_tickets import router as public_tickets_router
 
 
 api_router = APIRouter()
@@ -28,6 +29,7 @@ api_router.include_router(stock_router)
 api_router.include_router(inventory_flow_router)
 api_router.include_router(tasks_router)
 api_router.include_router(tickets_router)
+api_router.include_router(public_tickets_router)
 api_router.include_router(notifications_router)
 api_router.include_router(reports_router)
 api_router.include_router(settings_router)
```

#### 📄 `microtv-crm-backend/src/crm_backend/core/__pycache__/config.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/core/__pycache__/config.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/core/__pycache__/config.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/core/__pycache__/exceptions.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/core/__pycache__/exceptions.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/core/__pycache__/exceptions.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/core/config.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/core/config.py
+++ b/microtv-crm-backend/src/crm_backend/core/config.py
@@ -21,8 +21,8 @@ class Settings(BaseSettings):
         database_url: URL SQLAlchemy de la base del CRM.
         cors_origins: Orígenes permitidos para clientes browser.
         cors_origin_regex: Regex opcional para permitir orígenes dinámicos, por ejemplo LAN privada.
-        auth_base_url: Base URL de auth.microtv.ar.
-        auth_login_path: Path relativo de login en auth.microtv.ar.
+        auth_base_url: Base URL de auth interno del CRM.
+        auth_login_path: Path relativo de login en auth interno.
         auth_timeout_seconds: Timeout de llamadas a auth externo.
         auth_jwt_secret: Secret compartido para validar JWTs de auth.
         auth_jwt_algorithm: Algoritmo de firma del JWT.
@@ -56,17 +56,19 @@ class Settings(BaseSettings):
     auth_timeout_seconds: float = Field(default=10.0)
     auth_jwt_secret: str = Field(default="change-me")
     auth_jwt_algorithm: str = Field(default="HS256")
-    auth_jwt_issuer: str = Field(default="auth.microtv.ar")
+    auth_jwt_issuer: str = Field(default="auth.crm.ycc.internal")
     auth_jwt_audience: str = Field(default="microtv-platform")
     auto_provision_crm_role: bool = Field(default=True)
     product_images_max_bytes: int = Field(default=2 * 1024 * 1024)
     task_images_max_bytes: int = Field(default=8 * 1024 * 1024)
     task_videos_max_bytes: int = Field(default=128 * 1024 * 1024)
     default_admin_auth_roles: Annotated[list[str], NoDecode] = Field(
-        default_factory=lambda: ["platform_admin", "company_admin"]
+        default_factory=lambda: ["admin", "platform_admin", "company_admin"]
     )
-    default_deposito_auth_roles: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["company_operator"])
-    default_tech_auth_roles: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["company_operator"])
+    default_deposito_auth_roles: Annotated[list[str], NoDecode] = Field(
+        default_factory=lambda: ["operador_deposito", "company_operator"]
+    )
+    default_tech_auth_roles: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["tecnico_campo"])
     deposito_demo_tenant_id: str = Field(default="YCC")
 
     @field_validator(
@@ -129,6 +131,22 @@ class Settings(BaseSettings):
     def task_videos_dir(self) -> Path:
         return self.public_videos_dir / "task"
 
+    satisfaction_images_max_bytes: int = Field(default=8 * 1024 * 1024)
+    satisfaction_videos_max_bytes: int = Field(default=64 * 1024 * 1024)
+    satisfaction_form_expiry_hours: int = Field
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/core/exceptions.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/core/exceptions.py
+++ b/microtv-crm-backend/src/crm_backend/core/exceptions.py
@@ -353,6 +353,25 @@ class TicketConflictError(ApplicationError):
         super().__init__(code="ticket_conflict", message=message, status_code=409)
 
 
+class SatisfactionFormNotFoundError(ApplicationError):
+    """Señala que el formulario de satisfacción no existe o el token es inválido."""
+
+    def __init__(self) -> None:
+        # Generic message to avoid token oracle.
+        super().__init__(
+            code="satisfaction_form_not_found",
+            message="El formulario de satisfacción indicado no existe, expiró o ya fue utilizado.",
+            status_code=404,
+        )
+
+
+class SatisfactionFormConflictError(ApplicationError):
+    """Señala un conflicto de estado en el formulario de satisfacción."""
+
+    def __init__(self, message: str) -> None:
+        super().__init__(code="satisfaction_form_conflict", message=message, status_code=409)
+
+
 class NotificationNotFoundError(ApplicationError):
     """Señala que la notificación indicada no existe."""
```

#### 📄 `microtv-crm-backend/src/crm_backend/db/__pycache__/bootstrap.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/db/__pycache__/bootstrap.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/db/__pycache__/bootstrap.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/db/bootstrap.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/db/bootstrap.py
+++ b/microtv-crm-backend/src/crm_backend/db/bootstrap.py
@@ -216,6 +216,9 @@ def _ensure_extension_tables(session: Session) -> None:
         "ticket_assignment_history",
         "ticket_audit_events",
         "crm_notifications",
+        "ticket_satisfaction_forms",
+        "ticket_satisfaction_responses",
+        "ticket_satisfaction_media",
     ]
     bind = session.get_bind()
     inspector = inspect(bind)
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__init__.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/models/__init__.py
+++ b/microtv-crm-backend/src/crm_backend/models/__init__.py
@@ -43,6 +43,9 @@ from crm_backend.models.ticket import (
 	TicketComment,
 	TicketCommentType,
 	TicketPriority,
+	TicketSatisfactionForm,
+	TicketSatisfactionMedia,
+	TicketSatisfactionResponse,
 	TicketStatus,
 	TicketStatusTransition,
 	TicketTransitionAction,
@@ -99,6 +102,9 @@ __all__ = [
 	"TicketComment",
 	"TicketCommentType",
 	"TicketPriority",
+	"TicketSatisfactionForm",
+	"TicketSatisfactionMedia",
+	"TicketSatisfactionResponse",
 	"TicketStatus",
 	"TicketStatusTransition",
 	"TicketTransitionAction",
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/__init__.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/models/__pycache__/__init__.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/models/__pycache__/__init__.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/ticket.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/models/__pycache__/ticket.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/models/__pycache__/ticket.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/ticket.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/models/ticket.py
+++ b/microtv-crm-backend/src/crm_backend/models/ticket.py
@@ -46,6 +46,8 @@ class TicketCommentType(StrEnum):
     GENERAL = "general"
     SYSTEM = "system"
     CLOSURE = "closure"
+    ARRIVAL_REGISTRATION = "arrival_registration"
+    CLOSURE_EVIDENCE = "closure_evidence"
 
 
 class TicketAttachmentType(StrEnum):
@@ -383,3 +385,95 @@ def _normalize_role_key(role_key: str | None) -> str | None:
     if normalized == "encargado_deposito":
         return "deposito"
     return normalized or None
+
+
+# ---------------------------------------------------------------------------
+# Satisfaction forms (US-2: formulario de satisfacción del cliente)
+# ---------------------------------------------------------------------------
+
+
+class TicketSatisfactionForm(Base):
+    """Secure one-use satisfaction form generated for a closed ticket."""
+
+    __tablename__ = "ticket_satisfaction_forms"
+
+    form_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
+    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
+    # SHA-256 hex digest of the raw opaque token — never store the raw token.
+    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
+    created_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
+    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
+    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
+    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
+    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
+
+    ticket: Mapped["Ticket"] = relationship("Ticket", foreign_keys=[ticket_id], lazy="joined")
+    created_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[created_by_user_id], lazy="joined")
+    response: Mapped["TicketSatisfactionResponse | None"] = relationship(
+        "TicketSatisfactionResponse",
+        back_populates="form",
+        uselist=False,
+        cascade="all, delete-orphan",
+        lazy="selectin",
+    )
+
+    @property
+    def is_expired(self) -> bool:
+        from datetime import timezone as _tz
+        return datetime.now(_tz.utc) > self.expires_at
+
+    @property
+    def is_usable(self) -> bool:
+        return self.revoked_at is None and self.used_at is None and not self.is_expired
+
+    @property
+    def status_label(self) -> str
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/auth.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/schemas/__pycache__/auth.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/auth.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/settings.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/schemas/__pycache__/settings.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/settings.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/tickets.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/schemas/__pycache__/tickets.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/tickets.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/auth.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/schemas/auth.py
+++ b/microtv-crm-backend/src/crm_backend/schemas/auth.py
@@ -2,7 +2,7 @@
 
 from typing import Literal
 
-from pydantic import BaseModel, EmailStr, Field
+from pydantic import BaseModel, Field, field_validator
 
 
 class LoginRequest(BaseModel):
@@ -13,9 +13,17 @@ class LoginRequest(BaseModel):
         password: User password.
     """
 
-    email: EmailStr
+    email: str
     password: str = Field(..., min_length=1)
 
+    @field_validator("email")
+    @classmethod
+    def normalize_email(cls, value: str) -> str:
+        normalized = value.strip().lower()
+        if not normalized or "@" not in normalized:
+            raise ValueError("email must contain '@'.")
+        return normalized
+
 
 class MembershipOptionResponse(BaseModel):
     """Represent an auth membership available for selection.
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/settings.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/schemas/settings.py
+++ b/microtv-crm-backend/src/crm_backend/schemas/settings.py
@@ -34,6 +34,39 @@ class SettingsUserRoleAssignmentRequest(BaseModel):
     role_keys: list[str] = Field(default_factory=list)
 
 
+class SettingsAuthUserResponse(BaseModel):
+    user_id: str
+    email: str
+    display_name: str
+    is_active: bool
+    roles: list[str] = Field(default_factory=list)
+
+
+class SettingsAuthUserCreateRequest(BaseModel):
+    email: str = Field(..., min_length=5, max_length=255)
+    display_name: str = Field(..., min_length=2, max_length=120)
+    password: str = Field(..., min_length=8)
+    is_active: bool = True
+    roles: list[str] = Field(default_factory=list)
+
+
+class SettingsAuthUserUpdateRequest(BaseModel):
+    email: str = Field(..., min_length=5, max_length=255)
+    display_name: str = Field(..., min_length=2, max_length=120)
+
+
+class SettingsAuthUserStatusRequest(BaseModel):
+    is_active: bool
+
+
+class SettingsAuthUserRolesRequest(BaseModel):
+    roles: list[str] = Field(default_factory=list)
+
+
+class SettingsAuthUserResetPasswordRequest(BaseModel):
+    new_password: str = Field(..., min_length=8)
+
+
 class SettingsCategoryResponse(BaseModel):
     model_config = ConfigDict(from_attributes=True)
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/tickets.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/schemas/tickets.py
+++ b/microtv-crm-backend/src/crm_backend/schemas/tickets.py
@@ -160,6 +160,8 @@ class TicketSummaryResponse(BaseModel):
 
 
 class TicketDetailResponse(TicketSummaryResponse):
+    has_arrival_registered: bool = False
+    can_register_arrival: bool = False
     comments: list[TicketCommentResponse] = Field(default_factory=list)
     status_history: list[TicketStatusTransitionResponse] = Field(default_factory=list)
     assignment_history: list[TicketAssignmentHistoryResponse] = Field(default_factory=list)
@@ -172,3 +174,82 @@ class TicketRoleOptionResponse(BaseModel):
     crm_role_id: str
     role_key: str
     role_label: str
+
+
+# ---------------------------------------------------------------------------
+# Arrival registration (US-1)
+# ---------------------------------------------------------------------------
+
+
+class RegisterArrivalRequest(BaseModel):
+    body: str = Field(..., min_length=1, max_length=4000)
+    attachment_ids: list[str] = Field(default_factory=list)
+
+
+# ---------------------------------------------------------------------------
+# Satisfaction form (US-2)
+# ---------------------------------------------------------------------------
+
+
+class GenerateSatisfactionFormRequest(BaseModel):
+    """No body needed — ticket_id is in path. Placeholder for future fields."""
+    pass
+
+
+class SatisfactionFormStatusResponse(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    form_id: str
+    ticket_id: str
+    status_label: str
+    expires_at: datetime
+    used_at: datetime | None
+    revoked_at: datetime | None
+    created_at: datetime
+    has_response: bool
+
+    @classmethod
+    def from_orm_form(cls, form) -> "SatisfactionFormStatusResponse":
+        return cls(
+            form_id=form.form_id,
+            ticket_id=form.ticket_id,
+            status_label=form.status_label,
+            expires_at=form.expires_at,
+            used_at=form.used_at,
+            revoked_at=form.revoked_at,
+            created_at=form.created_at,
+            has_response=form.response is not None,
+        )
+
+
+class GenerateSatisfactionFormResponse(BaseModel):
+    """Returned once only — includes raw token for the satisfaction link."""
+    form_id: str
+    ticket_id: str
+    public_link_token: str  # The raw opaque token — shown once.
+    expires_at: datetime
+    status_label: str
+
+
+class PublicSatisfactionFormInfoResponse(BaseModel):
+    """Safe public response — no IDs, no sensitive data."""
+    ticket_number: str
+    client_name: str | None
+    location_name: s
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/satisfaction_form_service.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/services/__pycache__/satisfaction_form_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/ticket_export_service.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/services/__pycache__/ticket_export_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/ticket_service.cpython-313.pyc`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

Binary files a/microtv-crm-backend/src/crm_backend/services/__pycache__/ticket_service.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/__pycache__/ticket_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/satisfaction_form_service.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/microtv-crm-backend/src/crm_backend/services/satisfaction_form_service.py
@@ -0,0 +1,344 @@
+"""Satisfaction form service: secure one-use survey links for closed tickets."""
+
+from __future__ import annotations
+
+import hashlib
+import logging
+import re
+import secrets
+from datetime import UTC, datetime, timedelta
+from typing import TYPE_CHECKING
+from uuid import uuid4
+
+from fastapi import UploadFile
+from sqlalchemy.orm import Session
+
+from crm_backend.core.exceptions import (
+    SatisfactionFormConflictError,
+    SatisfactionFormNotFoundError,
+    TicketAccessDeniedError,
+    TicketConflictError,
+    TicketNotFoundError,
+    TicketValidationError,
+)
+from crm_backend.models.ticket import (
+    Ticket,
+    TicketSatisfactionForm,
+    TicketSatisfactionMedia,
+    TicketSatisfactionResponse,
+    TicketStatus,
+)
+
+if TYPE_CHECKING:
+    from crm_backend.services.auth_service import ResolvedCrmSession
+
+_logger = logging.getLogger(__name__)
+
+# Size limits (configurable via Settings but using sensible defaults here)
+_MAX_IMAGE_BYTES = 8 * 1024 * 1024   # 8 MB
+_MAX_VIDEO_BYTES = 64 * 1024 * 1024  # 64 MB
+_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
+_ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
+_ALLOWED_MIME_TYPES = _ALLOWED_IMAGE_TYPES | _ALLOWED_VIDEO_TYPES
+_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "webm", "mov"}
+
+# Default token expiry in hours
+_DEFAULT_EXPIRY_HOURS = 72
+
+
+def _hash_token(raw_token: str) -> str:
+    """Return the SHA-256 hex digest of a raw token string (never store raw)."""
+    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
+
+
+def _hash_ip(ip: str) -> str:
+    """Return a one-way SHA-256 digest of an IP address for basic audit."""
+    return hashlib.sha256(ip.encode("utf-8")).hexdigest()
+
+
+def _sanitize_filename(name: str) -> str:
+    """Strip path components and non-safe chars from a filename."""
+    basename = re.sub(r"[^\w.\-]", "_", name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
+    return basename[:200] or "file"
+
+
+class PublicSatisfactionFormService:
+    """Handle generation, validation and submission of satisfaction forms.
+
+    Token lifecycle:
+        1. admin/ejecutivo calls generate_form → raw token returned (shown once), hash stored.
+        2. External client GETs /public/ticket-satisfaction/{raw_token} → form info.
+        3. External client POSTs the form → response saved, form marked used.
+        4. Any subsequent POST with same token → HTTP 409.
+        5. admin/ejecutivo can revoke b
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/ticket_export_service.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/microtv-crm-backend/src/crm_backend/services/ticket_export_service.py
@@ -0,0 +1,311 @@
+"""Ticket export service: ZIP + PDF report for the full ticket development."""
+
+from __future__ import annotations
+
+import io
+import logging
+import os
+import re
+import zipfile
+from datetime import UTC, datetime
+from pathlib import Path
+from typing import TYPE_CHECKING
+
+from crm_backend.core.exceptions import TicketAccessDeniedError, TicketNotFoundError
+from crm_backend.models.ticket import (
+    Ticket,
+    TicketAttachmentType,
+    TicketCommentType,
+)
+
+if TYPE_CHECKING:
+    from crm_backend.services.auth_service import ResolvedCrmSession
+
+_logger = logging.getLogger(__name__)
+
+
+def _safe_str(value: object, fallback: str = "—") -> str:
+    if value is None:
+        return fallback
+    return str(value).strip() or fallback
+
+
+def _format_dt(dt: datetime | None) -> str:
+    if dt is None:
+        return "—"
+    try:
+        local = dt.astimezone()
+        return local.strftime("%d/%m/%Y %H:%M")
+    except Exception:
+        return str(dt)
+
+
+def _sanitize_zip_name(name: str) -> str:
+    """Prevent path traversal in ZIP entries."""
+    return re.sub(r"[^\w.\-]", "_", name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])[:200] or "file"
+
+
+class TicketExportService:
+    """Build a ZIP archive containing a PDF report and all media for a ticket."""
+
+    def __init__(self, media_base_dir: Path | str) -> None:
+        self._media_base_dir = Path(media_base_dir)
+
+    def export_development_zip(
+        self,
+        actor: "ResolvedCrmSession",
+        ticket: Ticket,
+    ) -> bytes:
+        """Return the raw ZIP bytes for streaming download.
+
+        Access: admin or ejecutivo only.
+        """
+        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
+            raise TicketAccessDeniedError("Solo admin o ejecutivo pueden exportar el desarrollo de un ticket.")
+
+        zip_buffer = io.BytesIO()
+        ticket_number = _safe_str(ticket.ticket_number, "sin_numero")
+        folder = f"ticket_{ticket_number}"
+
+        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
+            # Build PDF report
+            pdf_bytes = self._build_pdf(ticket)
+            zf.writestr(f"{folder}/desarrollo_ticket_{ticket_number}.pdf", pdf_bytes)
+
+            # Embed media files that still exist on disk
+            media_folder = f"{folder}/multimedia"
+            for attachment in ticket.attachments or []:
+                if not attachment.file_path:
+                    continue
+
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/ticket_service.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/crm_backend/services/ticket_service.py
+++ b/microtv-crm-backend/src/crm_backend/services/ticket_service.py
@@ -360,6 +360,76 @@ class TicketApplicationService:
         )
         return self._ticket_repository.save(ticket)
 
+    def register_arrival(
+        self,
+        actor: ResolvedCrmSession,
+        ticket_id: str,
+        body: str,
+        attachment_ids: list[str],
+    ) -> Ticket:
+        """Register the technician arrival at the site with mandatory video evidence."""
+        ticket = self.get_ticket_detail(actor, ticket_id)
+        self._ensure_ticket_operable(actor, ticket)
+
+        if ticket.status == TicketStatus.CLOSED.value:
+            raise TicketConflictError("No se puede registrar llegada en un ticket cerrado.")
+
+        if self._has_arrival_registered(ticket):
+            raise TicketConflictError("La llegada ya fue registrada para este ticket.")
+
+        normalized_body = body.strip()
+        if not normalized_body:
+            raise TicketValidationError("El registro de llegada requiere un comentario descriptivo.")
+
+        if not attachment_ids:
+            raise TicketValidationError("El registro de llegada requiere al menos un video adjunto obligatorio.")
+
+        comment = TicketComment(
+            ticket_comment_id=str(uuid4()),
+            ticket_id=ticket.ticket_id,
+            author_crm_user_id=actor.crm_user.crm_user_id,
+            location_id=ticket.location_id,
+            comment_type=TicketCommentType.ARRIVAL_REGISTRATION.value,
+            body=normalized_body,
+        )
+        ticket.comments.append(comment)
+        self._attach_files_to_comment(ticket, comment, attachment_ids)
+
+        # Validate that at least one attached file is a video.
+        if not self._comment_has_video(ticket, comment):
+            raise TicketValidationError("El registro de llegada requiere al menos un video obligatorio.")
+
+        ticket.audit_events.append(
+            TicketAuditEvent(
+                event_type="ticket.arrival_registered",
+                actor_crm_user_id=actor.crm_user.crm_user_id,
+                payload_json={
+                    "comment_id": comment.ticket_comment_id,
+                    "location_id": ticket.location_id,
+                    "attachment_ids": list(attachment_ids),
+                },
+            )
+        )
+        return self._ticket_repository.save(ticket)
+
+    def has_arrival_registered(self, ticket: Ticket) -> bool:
+        """Expose arrival registration status for API serialization."""
+        return self._has_arrival_registered(ticket)
+
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/microtv_crm_backend.egg-info/PKG-INFO`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/microtv_crm_backend.egg-info/PKG-INFO
+++ b/microtv-crm-backend/src/microtv_crm_backend.egg-info/PKG-INFO
@@ -13,6 +13,8 @@ Requires-Dist: pydantic-settings<3.0,>=2.9
 Requires-Dist: httpx<1.0,>=0.28
 Requires-Dist: pyjwt<3.0,>=2.10
 Requires-Dist: python-dotenv<2.0,>=1.1
+Requires-Dist: reportlab<5.0,>=4.0
+Requires-Dist: Pillow<12.0,>=10.0
 Provides-Extra: test
 Requires-Dist: pytest<9.0,>=8.3; extra == "test"
 Requires-Dist: httpx<1.0,>=0.28; extra == "test"
```

#### 📄 `microtv-crm-backend/src/microtv_crm_backend.egg-info/SOURCES.txt`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/microtv_crm_backend.egg-info/SOURCES.txt
+++ b/microtv-crm-backend/src/microtv_crm_backend.egg-info/SOURCES.txt
@@ -17,6 +17,7 @@ src/crm_backend/api/endpoints/health.py
 src/crm_backend/api/endpoints/inventory_flow.py
 src/crm_backend/api/endpoints/locations.py
 src/crm_backend/api/endpoints/notifications.py
+src/crm_backend/api/endpoints/public_tickets.py
 src/crm_backend/api/endpoints/reports.py
 src/crm_backend/api/endpoints/settings.py
 src/crm_backend/api/endpoints/stock.py
@@ -82,8 +83,10 @@ src/crm_backend/services/material_flow_service.py
 src/crm_backend/services/notification_service.py
 src/crm_backend/services/reports_service.py
 src/crm_backend/services/role_resolution_service.py
+src/crm_backend/services/satisfaction_form_service.py
 src/crm_backend/services/settings_service.py
 src/crm_backend/services/stock_service.py
+src/crm_backend/services/ticket_export_service.py
 src/crm_backend/services/ticket_service.py
 src/crm_backend/services/tasks/__init__.py
 src/crm_backend/services/tasks/action_execution.py
@@ -100,4 +103,5 @@ tests/test_auth_api.py
 tests/test_clients_api.py
 tests/test_stock_api.py
 tests/test_tasks_api.py
+tests/test_ticket_evidence_and_satisfaction.py
 tests/test_tickets_api.py
\ No newline at end of file
```

#### 📄 `microtv-crm-backend/src/microtv_crm_backend.egg-info/requires.txt`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-backend/src/microtv_crm_backend.egg-info/requires.txt
+++ b/microtv-crm-backend/src/microtv_crm_backend.egg-info/requires.txt
@@ -8,6 +8,8 @@ pydantic-settings<3.0,>=2.9
 httpx<1.0,>=0.28
 pyjwt<3.0,>=2.10
 python-dotenv<2.0,>=1.1
+reportlab<5.0,>=4.0
+Pillow<12.0,>=10.0
 
 [test]
 pytest<9.0,>=8.3
```

#### 📄 `microtv-crm-backend/tests/test_ticket_evidence_and_satisfaction.py`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/microtv-crm-backend/tests/test_ticket_evidence_and_satisfaction.py
@@ -0,0 +1,347 @@
+"""Tests for arrival registration (US-1) and satisfaction form (US-2)."""
+
+from __future__ import annotations
+
+from io import BytesIO
+from pathlib import Path
+from unittest.mock import MagicMock, patch
+
+import pytest
+from sqlalchemy import select
+
+from crm_backend.adapters.auth_service_adapter import ActiveMembershipContext, AuthenticatedAuthResult
+from crm_backend.api.dependencies import get_auth_service_adapter
+from crm_backend.models import Client, CrmRole, CrmUser, CrmUserRole, Location, Ticket, TicketAttachment
+
+
+# ---------------------------------------------------------------------------
+# Fake adapter (same as test_tickets_api.py)
+# ---------------------------------------------------------------------------
+
+
+class FakeTicketAuthAdapter:
+    USER_FIXTURES = {
+        "admin-token": {
+            "auth_user_id": "auth-admin",
+            "email": "admin.crm@microtv.com",
+            "display_name": "Admin CRM",
+            "roles": ["platform_admin"],
+            "tenant_id": "MICROTV",
+        },
+        "tech-token": {
+            "auth_user_id": "auth-tech",
+            "email": "tecnico.crm@yccbrothers.com",
+            "display_name": "Tecnico Campo",
+            "roles": [],
+            "tenant_id": "YCC",
+        },
+        "ejecutivo-token": {
+            "auth_user_id": "auth-ejecutivo",
+            "email": "ejecutivo@ycc.com",
+            "display_name": "Ejecutivo",
+            "roles": ["ejecutivo"],
+            "tenant_id": "YCC",
+        },
+    }
+
+    def validate_access_token(self, access_token: str) -> AuthenticatedAuthResult:
+        fixture = self.USER_FIXTURES[access_token]
+        return AuthenticatedAuthResult(
+            access_token=access_token,
+            refresh_token="refresh-token",
+            token_type="bearer",
+            expires_in=3600,
+            refresh_expires_in=86400,
+            auth_user_id=fixture["auth_user_id"],
+            email=fixture["email"],
+            display_name=fixture["display_name"],
+            active_membership=ActiveMembershipContext(
+                membership_id=f"membership-{fixture['auth_user_id']}",
+                tenant_type="company",
+                tenant_id=fixture["tenant_id"],
+                roles=fixture["roles"],
+            ),
+            claims={"sub": fixture["auth_user_id"], "email": fixture["email"]},
+        )
+
+    def login(self, *, email: str, password: str):
+        raise NotImplementedError
+
+
+def _aut
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/app.routes.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/app.routes.ts
+++ b/microtv-crm-frontend/src/app/app.routes.ts
@@ -15,6 +15,15 @@ export const routes: Routes = [
 		component: LoginPageComponent,
 		data: { title: 'Ingresar' }
 	},
+	{
+		// Public satisfaction form — NO auth guard
+		path: 'satisfaction/:token',
+		loadComponent: () =>
+			import('./features/satisfaction/components/satisfaction-page/satisfaction-page.component').then(
+				(m) => m.SatisfactionPageComponent
+			),
+		data: { title: 'Encuesta de satisfacción' }
+	},
 	{
 		path: '',
 		canActivate: [authGuard],
```

#### 📄 `microtv-crm-frontend/src/app/core/models/settings-management.model.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/core/models/settings-management.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/settings-management.model.ts
@@ -23,6 +23,39 @@ export interface SettingsUserRoleAssignmentRequest {
   role_keys: string[];
 }
 
+export interface SettingsAuthUser {
+  user_id: string;
+  email: string;
+  display_name: string;
+  is_active: boolean;
+  roles: string[];
+}
+
+export interface SettingsAuthUserCreateRequest {
+  email: string;
+  display_name: string;
+  password: string;
+  is_active: boolean;
+  roles: string[];
+}
+
+export interface SettingsAuthUserUpdateRequest {
+  email: string;
+  display_name: string;
+}
+
+export interface SettingsAuthUserStatusRequest {
+  is_active: boolean;
+}
+
+export interface SettingsAuthUserRolesRequest {
+  roles: string[];
+}
+
+export interface SettingsAuthUserResetPasswordRequest {
+  new_password: string;
+}
+
 export interface SettingsCategory {
   category_id: string;
   name: string;
```

#### 📄 `microtv-crm-frontend/src/app/core/models/ticket-management.model.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/core/models/ticket-management.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/ticket-management.model.ts
@@ -120,6 +120,8 @@ export interface TicketSummary {
   closed_by_crm_user_id: string | null;
   closed_by_display_name: string | null;
   closed_at: string | null;
+  has_arrival_registered?: boolean;
+  can_register_arrival?: boolean;
   created_at: string;
   updated_at: string;
 }
@@ -183,6 +185,59 @@ export interface ReopenTicketRequest {
   comment: string;
 }
 
+// ---------------------------------------------------------------------------
+// Arrival registration (US-1)
+// ---------------------------------------------------------------------------
+
+export interface RegisterArrivalRequest {
+  body: string;
+  attachment_ids?: string[];
+}
+
+// ---------------------------------------------------------------------------
+// Satisfaction form (US-2)
+// ---------------------------------------------------------------------------
+
+export interface GenerateSatisfactionFormResponse {
+  form_id: string;
+  ticket_id: string;
+  public_link_token: string;
+  expires_at: string;
+  status_label: string;
+}
+
+export interface SatisfactionFormStatusResponse {
+  form_id: string;
+  ticket_id: string;
+  status_label: string;
+  expires_at: string;
+  used_at: string | null;
+  revoked_at: string | null;
+  created_at: string;
+  has_response: boolean;
+}
+
+export interface SubmitSatisfactionFormRequest {
+  rating: number;
+  comment?: string | null;
+}
+
+export interface SatisfactionResponseDetailResponse {
+  response_id: string;
+  ticket_id: string;
+  rating: number;
+  comment: string | null;
+  submitted_at: string;
+  media_count: number;
+}
+
+export interface PublicSatisfactionFormInfoResponse {
+  ticket_number: string;
+  client_name: string | null;
+  location_name: string | null;
+  status_label: string;
+}
+
 export interface TicketTableItem {
   ticketId: string;
   ticketNumber: string;
```

#### 📄 `microtv-crm-frontend/src/app/core/services/settings-management.service.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/core/services/settings-management.service.ts
+++ b/microtv-crm-frontend/src/app/core/services/settings-management.service.ts
@@ -5,6 +5,12 @@ import { catchError } from 'rxjs/operators';
 
 import { crmApiConfig } from '../config/crm-api.config';
 import {
+  SettingsAuthUser,
+  SettingsAuthUserCreateRequest,
+  SettingsAuthUserResetPasswordRequest,
+  SettingsAuthUserRolesRequest,
+  SettingsAuthUserStatusRequest,
+  SettingsAuthUserUpdateRequest,
   SettingsCategory,
   SettingsCategoryWriteRequest,
   SettingsNotificationRule,
@@ -52,6 +58,30 @@ export class SettingsManagementService {
     return this.request<SettingsUserRoleAssignment>('put', `/settings/user-roles/${userId}`, payload);
   }
 
+  listAuthUsers(): Observable<SettingsAuthUser[]> {
+    return this.request<SettingsAuthUser[]>('get', '/settings/auth-users');
+  }
+
+  createAuthUser(payload: SettingsAuthUserCreateRequest): Observable<SettingsAuthUser> {
+    return this.request<SettingsAuthUser>('post', '/settings/auth-users', payload);
+  }
+
+  updateAuthUser(userId: string, payload: SettingsAuthUserUpdateRequest): Observable<SettingsAuthUser> {
+    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}`, payload);
+  }
+
+  setAuthUserStatus(userId: string, payload: SettingsAuthUserStatusRequest): Observable<SettingsAuthUser> {
+    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}/status`, payload);
+  }
+
+  setAuthUserRoles(userId: string, payload: SettingsAuthUserRolesRequest): Observable<SettingsAuthUser> {
+    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}/roles`, payload);
+  }
+
+  resetAuthUserPassword(userId: string, payload: SettingsAuthUserResetPasswordRequest): Observable<SettingsAuthUser> {
+    return this.request<SettingsAuthUser>('put', `/settings/auth-users/${userId}/reset-password`, payload);
+  }
+
   listCategories(type?: string): Observable<SettingsCategory[]> {
     const query = type ? `?type=${encodeURIComponent(type)}` : '';
     return this.request<SettingsCategory[]>('get', `/settings/categories${query}`);
```

#### 📄 `microtv-crm-frontend/src/app/core/services/ticket-management.service.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/core/services/ticket-management.service.ts
+++ b/microtv-crm-frontend/src/app/core/services/ticket-management.service.ts
@@ -10,8 +10,14 @@ import {
   CloseTicketRequest,
   CreateTicketCommentRequest,
   CreateTicketRequest,
+  GenerateSatisfactionFormResponse,
+  PublicSatisfactionFormInfoResponse,
+  RegisterArrivalRequest,
   RejectTicketApprovalRequest,
   ReopenTicketRequest,
+  SatisfactionFormStatusResponse,
+  SatisfactionResponseDetailResponse,
+  SubmitSatisfactionFormRequest,
   TicketAttachment,
   TicketClientOption,
   TicketDetail,
@@ -169,6 +175,69 @@ export class TicketManagementService {
       .pipe(catchError((error) => this.handleRequestError(error)));
   }
 
+  // -------------------------------------------------------------------------
+  // Arrival registration (US-1)
+  // -------------------------------------------------------------------------
+
+  registerArrival(ticketId: string, payload: RegisterArrivalRequest): Observable<TicketDetail> {
+    return this.request<TicketDetail>('post', `/tickets/${ticketId}/arrival`, payload).pipe(
+      map((ticket) => this.normalizeTicketDetail(ticket))
+    );
+  }
+
+  // -------------------------------------------------------------------------
+  // Satisfaction form (US-2)
+  // -------------------------------------------------------------------------
+
+  generateSatisfactionForm(ticketId: string): Observable<GenerateSatisfactionFormResponse> {
+    return this.request<GenerateSatisfactionFormResponse>('post', `/tickets/${ticketId}/satisfaction-form`);
+  }
+
+  revokeSatisfactionForm(ticketId: string): Observable<SatisfactionFormStatusResponse> {
+    return this.request<SatisfactionFormStatusResponse>('post', `/tickets/${ticketId}/satisfaction-form/revoke`);
+  }
+
+  getSatisfactionFormStatus(ticketId: string): Observable<SatisfactionFormStatusResponse> {
+    return this.request<SatisfactionFormStatusResponse>('get', `/tickets/${ticketId}/satisfaction-form/status`);
+  }
+
+  getSatisfactionResponse(ticketId: string): Observable<SatisfactionResponseDetailResponse> {
+    return this.request<SatisfactionResponseDetailResponse>('get', `/tickets/${ticketId}/satisfaction-form/response`);
+  }
+
+  // Public (no auth required)
+  getPublicSatisfactionForm(token: string): Observable<PublicSatisfactionFormInfoResponse> {
+    return this.http
+      .get<PublicSatisfactionFormInfoResponse>(`${crmApiConfig.baseUrl}/public/tickets/satisfaction/${encodeURIComponent(token)}`)
+      .pipe(catchError((error) => this.handleRequestError(error)));
+  }
+
+  submitPublicSatisfactionForm(token: st
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/satisfaction/components/satisfaction-page/satisfaction-page.component.html`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/microtv-crm-frontend/src/app/features/satisfaction/components/satisfaction-page/satisfaction-page.component.html
@@ -0,0 +1,96 @@
+<div class="satisfaction-page">
+  @if (isLoading()) {
+    <div class="satisfaction-page__loading">
+      <mat-spinner diameter="48"></mat-spinner>
+      <p>Cargando formulario...</p>
+    </div>
+  } @else if (response()) {
+    <mat-card class="satisfaction-page__card">
+      <mat-card-header>
+        <mat-icon mat-card-avatar color="primary">check_circle</mat-icon>
+        <mat-card-title>¡Gracias por tu respuesta!</mat-card-title>
+        <mat-card-subtitle>Tu opinión fue registrada correctamente.</mat-card-subtitle>
+      </mat-card-header>
+      <mat-card-content>
+        <p>Puntuación: <strong>{{ response()!.rating }} / 5</strong></p>
+        @if (response()!.comment) {
+          <p>Comentario: {{ response()!.comment }}</p>
+        }
+      </mat-card-content>
+    </mat-card>
+  } @else if (errorMessage()) {
+    <mat-card class="satisfaction-page__card">
+      <mat-card-header>
+        <mat-icon mat-card-avatar color="warn">error</mat-icon>
+        <mat-card-title>Formulario no disponible</mat-card-title>
+      </mat-card-header>
+      <mat-card-content>
+        <p>{{ errorMessage() }}</p>
+      </mat-card-content>
+    </mat-card>
+  } @else if (formInfo()) {
+    <mat-card class="satisfaction-page__card">
+      <mat-card-header>
+        <mat-card-title>Encuesta de satisfacción</mat-card-title>
+        <mat-card-subtitle>
+          Ticket #{{ formInfo()!.ticket_number }}
+          @if (formInfo()!.client_name) {
+            · {{ formInfo()!.client_name }}
+          }
+          @if (formInfo()!.location_name) {
+            · {{ formInfo()!.location_name }}
+          }
+        </mat-card-subtitle>
+      </mat-card-header>
+      <mat-card-content>
+        <form [formGroup]="satisfactionForm" (ngSubmit)="onSubmit()">
+          <div class="satisfaction-page__rating">
+            <p class="satisfaction-page__rating-label">¿Cómo calificarías el servicio recibido?</p>
+            <div class="satisfaction-page__stars" role="radiogroup" aria-label="Calificación">
+              @for (star of ratingOptions; track star) {
+                <button
+                  type="button"
+                  class="satisfaction-page__star"
+                  [class.satisfaction-page__star--filled]="star <= (hoverRating() || selectedRating)"
+                  (mouseenter)="hoverRating.set(star)"
+                  (mouseleave)="hoverRating.set(0)"
+                  (click)="setRating(star)"
+     
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/satisfaction/components/satisfaction-page/satisfaction-page.component.scss`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/microtv-crm-frontend/src/app/features/satisfaction/components/satisfaction-page/satisfaction-page.component.scss
@@ -0,0 +1,84 @@
+.satisfaction-page {
+  display: flex;
+  justify-content: center;
+  align-items: flex-start;
+  min-height: 100vh;
+  padding: 2rem 1rem;
+  background: #f5f5f5;
+
+  &__loading {
+    display: flex;
+    flex-direction: column;
+    align-items: center;
+    gap: 1rem;
+    padding: 4rem;
+  }
+
+  &__card {
+    width: 100%;
+    max-width: 560px;
+  }
+
+  &__rating {
+    margin: 1.5rem 0 1rem;
+  }
+
+  &__rating-label {
+    font-weight: 500;
+    margin-bottom: 0.75rem;
+  }
+
+  &__stars {
+    display: flex;
+    align-items: center;
+    gap: 0.25rem;
+  }
+
+  &__star {
+    background: none;
+    border: none;
+    cursor: pointer;
+    padding: 0.25rem;
+    color: #ccc;
+    transition: color 0.15s;
+
+    mat-icon {
+      font-size: 2rem;
+      width: 2rem;
+      height: 2rem;
+    }
+
+    &--filled {
+      color: #f59e0b;
+    }
+
+    &:focus-visible {
+      outline: 2px solid #1976d2;
+      border-radius: 4px;
+    }
+  }
+
+  &__rating-value {
+    margin-left: 0.5rem;
+    font-weight: 600;
+    font-size: 1rem;
+    color: #555;
+  }
+
+  &__comment {
+    width: 100%;
+    margin-top: 1rem;
+  }
+
+  &__error {
+    color: #c62828;
+    font-size: 0.9rem;
+    margin: 0.5rem 0;
+  }
+
+  &__actions {
+    display: flex;
+    justify-content: flex-end;
+    margin-top: 1.5rem;
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/satisfaction/components/satisfaction-page/satisfaction-page.component.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

new file mode 100644
--- /dev/null
+++ b/microtv-crm-frontend/src/app/features/satisfaction/components/satisfaction-page/satisfaction-page.component.ts
@@ -0,0 +1,111 @@
+import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
+import { ActivatedRoute } from '@angular/router';
+import { CommonModule } from '@angular/common';
+import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
+import { MatButtonModule } from '@angular/material/button';
+import { MatCardModule } from '@angular/material/card';
+import { MatFormFieldModule } from '@angular/material/form-field';
+import { MatInputModule } from '@angular/material/input';
+import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
+import { MatIconModule } from '@angular/material/icon';
+import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
+
+import { TicketManagementService } from '../../../../core/services/ticket-management.service';
+import {
+  PublicSatisfactionFormInfoResponse,
+  SatisfactionResponseDetailResponse
+} from '../../../../core/models/ticket-management.model';
+
+@Component({
+  selector: 'app-satisfaction-page',
+  standalone: true,
+  imports: [
+    CommonModule,
+    ReactiveFormsModule,
+    MatButtonModule,
+    MatCardModule,
+    MatFormFieldModule,
+    MatInputModule,
+    MatProgressSpinnerModule,
+    MatIconModule,
+    MatSnackBarModule
+  ],
+  templateUrl: './satisfaction-page.component.html',
+  styleUrl: './satisfaction-page.component.scss',
+  changeDetection: ChangeDetectionStrategy.OnPush
+})
+export class SatisfactionPageComponent implements OnInit {
+  private readonly route = inject(ActivatedRoute);
+  private readonly ticketService = inject(TicketManagementService);
+  private readonly snackBar = inject(MatSnackBar);
+  private readonly fb = inject(FormBuilder);
+
+  readonly token = signal<string>('');
+  readonly isLoading = signal(true);
+  readonly isSubmitting = signal(false);
+  readonly formInfo = signal<PublicSatisfactionFormInfoResponse | null>(null);
+  readonly response = signal<SatisfactionResponseDetailResponse | null>(null);
+  readonly errorMessage = signal<string | null>(null);
+  readonly hoverRating = signal(0);
+
+  readonly ratingOptions = [1, 2, 3, 4, 5];
+
+  readonly satisfactionForm = this.fb.group({
+    rating: this.fb.control<number>(0, { validators: [Validators.min(1), Validators.required], nonNullable: true }),
+    comment: this.fb.control<string>('', { nonNullable: true })
+  });
+
+  ngOnInit(): void {
+    const token = this.route.snapshot.paramMap.get('token') ??
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.html`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.html
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.html
@@ -25,7 +25,48 @@
   } @else {
     <mat-card class="settings-page__tabs-card">
       <mat-tab-group>
-        <mat-tab label="Usuarios y roles">
+        @if (isAdmin()) {
+          <mat-tab label="Gestión de usuarios">
+            <section class="settings-page__tab-content">
+              <div class="settings-page__section-header">
+                <h3>Usuarios del auth interno CRM</h3>
+                <button mat-flat-button color="primary" type="button" (click)="createAuthUser()">Nuevo usuario</button>
+              </div>
+
+              <table class="settings-page__table">
+                <thead>
+                  <tr>
+                    <th>Nombre</th>
+                    <th>Email</th>
+                    <th>Estado</th>
+                    <th>Roles</th>
+                    <th></th>
+                  </tr>
+                </thead>
+                <tbody>
+                  @for (item of authUsers(); track item.user_id) {
+                    <tr>
+                      <td>{{ item.display_name }}</td>
+                      <td>{{ item.email }}</td>
+                      <td>{{ item.is_active ? 'Activo' : 'Inactivo' }}</td>
+                      <td>{{ prettyAuthRoles(item.roles) }}</td>
+                      <td class="settings-page__actions-cell">
+                        <button mat-button type="button" (click)="editAuthUser(item)">Editar</button>
+                        <button mat-button type="button" (click)="toggleAuthUserStatus(item)">
+                          {{ item.is_active ? 'Desactivar' : 'Activar' }}
+                        </button>
+                        <button mat-button type="button" (click)="updateAuthUserRoles(item)">Roles</button>
+                        <button mat-button type="button" (click)="resetAuthUserPassword(item)">Reset password</button>
+                      </td>
+                    </tr>
+                  }
+                </tbody>
+              </table>
+            </section>
+          </mat-tab>
+        }
+
+        <mat-tab label="Usuarios y roles CRM">
           <section class="settings-page__tab-content">
             <div class="settings-page__section-header">
               <h3>Roles funcionales</h3>
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.ts
@@ -10,6 +10,7 @@ import { MatTabsModule } from '@angular/material/tabs';
 import { forkJoin } from 'rxjs';
 
 import {
+  SettingsAuthUser,
   SettingsCategory,
   SettingsCategoryWriteRequest,
   SettingsNotificationRule,
@@ -27,6 +28,7 @@ import {
   SettingsUserRoleAssignment,
   SettingsUserRoleAssignmentRequest
 } from '../../../../core/models/settings-management.model';
+import { AuthSessionService } from '../../../../core/services/auth-session.service';
 import { SettingsManagementService } from '../../../../core/services/settings-management.service';
 import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
 import {
@@ -53,6 +55,7 @@ import {
 })
 export class SettingsPageComponent {
   private readonly settingsService = inject(SettingsManagementService);
+  private readonly authSessionService = inject(AuthSessionService);
   private readonly dialog = inject(MatDialog);
   private readonly destroyRef = inject(DestroyRef);
 
@@ -61,6 +64,7 @@ export class SettingsPageComponent {
 
   readonly roles = signal<SettingsRole[]>([]);
   readonly userRoles = signal<SettingsUserRoleAssignment[]>([]);
+  readonly authUsers = signal<SettingsAuthUser[]>([]);
   readonly categories = signal<SettingsCategory[]>([]);
   readonly priorities = signal<SettingsPriority[]>([]);
   readonly statuses = signal<SettingsStatus[]>([]);
@@ -68,6 +72,13 @@ export class SettingsPageComponent {
   readonly slaRules = signal<SettingsSlaRule[]>([]);
   readonly notificationRules = signal<SettingsNotificationRule[]>([]);
 
+  readonly crmOperationalRoles: Array<{ code: string; label: string }> = [
+    { code: 'admin', label: 'Administrador' },
+    { code: 'ejecutivo', label: 'Ejecutivo' },
+    { code: 'tecnico_campo', label: 'Técnico de campo' },
+    { code: 'operador_deposito', label: 'Operador depósito' }
+  ];
+
   constructor() {
     this.reload();
   }
@@ -79,6 +90,7 @@ export class SettingsPageComponent {
     forkJoin({
       roles: this.settingsService.listRoles(),
       userRoles: this.settingsService.listUserRoles(),
+      authUsers: this.settingsService.listAuthUsers(),
       categories: this.settingsService.listCategories(),
       priorities: this.settingsService.listPriorities(),
       statuses: this.settingsService.listStatuses(),
@@ -91,6 +103,7 @@ export class SettingsPageComponent {
         next: (result) => {
           this.roles.set(result.r
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html
@@ -230,13 +230,45 @@
                 <mat-icon>task_alt</mat-icon>
                 <span>Cerrar ticket</span>
               </button>
+              <button mat-menu-item type="button" (click)="showArrivalPanel.set(!showArrivalPanel())">
+                <mat-icon>place</mat-icon>
+                <span>Registrar llegada</span>
+              </button>
             </mat-menu>
 
             <button mat-stroked-button type="button" (click)="toggleInventoryRequestDrawer()" [disabled]="!canCreateInventoryRequest() || isSaving()">
               Hacer solicitud a depósito
             </button>
+
+            @if (!canRegisterArrival() && hasArrivalRegistered()) {
+              <span class="ticket-execution-page__arrival-badge">
+                <mat-icon style="font-size:16px;vertical-align:middle">check_circle</mat-icon>
+                Llegada registrada
+              </span>
+            }
           </div>
 
+          @if (showArrivalPanel()) {
+            <section class="ticket-execution-page__arrival-panel" [formGroup]="arrivalForm">
+              <p style="margin:0 0 8px;font-weight:500">Registrar llegada al sitio</p>
+              <mat-form-field appearance="outline" subscriptSizing="dynamic" style="width:100%">
+                <mat-label>Descripción de la llegada</mat-label>
+                <textarea matInput formControlName="body" rows="3"></textarea>
+              </mat-form-field>
+              <p style="margin:8px 0 4px;font-size:0.85em;color:#666">
+                Adjuntá al menos un video de evidencia usando el panel de adjuntos, luego presioná Guardar.
+              </p>
+              <div style="display:flex;gap:8px;margin-top:8px">
+                <button mat-flat-button color="primary" type="button" (click)="onRegisterArrival()" [disabled]="arrivalForm.invalid || isSaving()">
+                  Guardar llegada
+                </button>
+                <button mat-stroked-button type="button" (click)="showArrivalPanel.set(false)">
+                  Cancelar
+                </button>
+              </div>
+            </section>
+          }
+
           @if (showInventoryRequestDrawer()) {
             <section class="ticket-execution-page__request-drawer" [formGroup]="inventoryRequestForm">
               <mat-form-field appearance="outline" subscriptSizing="dynamic">
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts
@@ -1440,12 +1440,85 @@ export class TicketExecutionPageComponent {
     if (commentType === 'closure') {
       return 'Cierre';
     }
+    if (commentType === 'closure_evidence') {
+      return 'Evidencia de cierre';
+    }
+    if (commentType === 'arrival_registration') {
+      return 'Llegada al sitio';
+    }
     if (commentType === 'system') {
       return 'Sistema';
     }
     return 'Comentario';
   }
 
+  readonly hasArrivalRegistered = computed(() => {
+    const ticket = this.ticket();
+    if (!ticket) return false;
+    if (typeof ticket.has_arrival_registered === 'boolean') {
+      return ticket.has_arrival_registered;
+    }
+    return ticket.comments.some(
+      (c) => (c as any).comment_type === 'arrival_registration'
+    );
+  });
+
+  readonly canRegisterArrival = computed(() => {
+    const ticket = this.ticket();
+    if (!ticket) return false;
+
+    // Keep UI resilient: if backend flag arrives false unexpectedly, preserve local
+    // operability fallback so the option is not blocked by stale/incomplete payloads.
+    const locallyAllowed = ticket.status !== 'CLOSED' && !this.hasArrivalRegistered() && this.canOperateTicket() && !this.isDeposito();
+
+    if (ticket.can_register_arrival === true) {
+      return true;
+    }
+
+    if (ticket.can_register_arrival === false) {
+      return locallyAllowed;
+    }
+
+    return locallyAllowed;
+  });
+
+  readonly arrivalForm = this.formBuilder.group({
+    body: this.formBuilder.control('', { validators: [Validators.required, Validators.minLength(1)], nonNullable: true })
+  });
+  readonly showArrivalPanel = signal(false);
+
+  onRegisterArrival(): void {
+    if (this.arrivalForm.invalid || this.isSaving()) return;
+    const body = this.arrivalForm.getRawValue().body.trim();
+    if (!body) return;
+
+    const attachmentIds = this.pendingAttachments().map((a) => a.id);
+    if (attachmentIds.length === 0) {
+      this.errorMessage.set('Adjuntá al menos un video de evidencia antes de registrar la llegada.');
+      return;
+    }
+
+    this.isSaving.set(true);
+    this.errorMessage.set(null);
+    this.ticketManagementService
+      .registerArrival(this.ticketId(), { body, attachment_ids: attachmentIds })
+      .pipe(takeUntilDestroyed(this.destroyRef))
+      .subscribe({
+        next: (ticket) => {
+          this.ticket.set(ticket);
+          this.pendingAtta
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts`
```diff
commit ce43f62e11646431f86b1e4638630caaeae9ac0f
Author: Valentino_Colella <valentinocolella@microtv.com.ar>
Date:   Sat Apr 25 11:36:43 2026 -0300

    subo avances en las user history de: solicitar comentario de llegada  video de retirada, exportar historial del ticket, formulario de satisfacion del cliente TODO: completar dichas user history y hacer pruebas

--- a/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts
@@ -4,10 +4,12 @@ import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
 import { Router } from '@angular/router';
 import { toSignal } from '@angular/core/rxjs-interop';
 import { map } from 'rxjs';
+import { MatSnackBar } from '@angular/material/snack-bar';
 import { MatButtonModule } from '@angular/material/button';
 import { MatDialog, MatDialogModule } from '@angular/material/dialog';
 import { MatIconModule } from '@angular/material/icon';
 import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
+import { MatSnackBarModule } from '@angular/material/snack-bar';
 import { MatTabsModule } from '@angular/material/tabs';
 
 import {
@@ -46,6 +48,7 @@ interface TicketListUiState {
     MatDialogModule,
     MatIconModule,
     MatProgressSpinnerModule,
+    MatSnackBarModule,
     MatTabsModule,
     ListingControlsComponent,
     PageTitleComponent,
@@ -63,6 +66,7 @@ export class TicketsPageComponent {
   private readonly authSessionService = inject(AuthSessionService);
   private readonly ticketManagementService = inject(TicketManagementService);
   private readonly listingViewPreferenceService = inject(ListingViewPreferenceService);
+  private readonly snackBar = inject(MatSnackBar);
 
   readonly isHandset = toSignal(
     this.breakpointObserver.observe([Breakpoints.Handset]).pipe(map((state) => state.matches)),
@@ -362,4 +366,75 @@ export class TicketsPageComponent {
       minute: '2-digit'
     });
   }
+
+  // -------------------------------------------------------------------------
+  // Satisfaction form (US-2) — history tab actions
+  // -------------------------------------------------------------------------
+
+  readonly satisfactionFormGenerating = signal<string | null>(null); // ticketId
+
+  readonly canGenerateSatisfactionForms = computed(() => {
+    const roles = this.currentRoles();
+    return roles.includes('admin') || roles.includes('ejecutivo');
+  });
+
+  onGenerateSatisfactionForm(ticketId: string): void {
+    if (this.satisfactionFormGenerating()) return;
+    this.satisfactionFormGenerating.set(ticketId);
+    this.errorMessage.set(null);
+
+    this.ticketManagementService
+      .generateSatisfactionForm(ticketId)
+      .pipe(takeUntilDestroyed(this.destroyRef))
+      .subscribe({
+        next: (response) => {
+          this.satisfactionFormGenerating.set(null);
+          const token = response.public_link_token;
... (código truncado por longitud) ...
```

---

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

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/reports.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/reports.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/settings.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/settings.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tasks.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tasks.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tasks.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tickets.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/api/endpoints/__pycache__/tickets.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/dashboard.py`
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
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/dashboard.py
@@ -0,0 +1,23 @@
+"""Dashboard summary endpoint backed by live database metrics."""
+
+from fastapi import APIRouter, Depends
+
+from crm_backend.api.dependencies import get_authenticated_crm_session, get_dashboard_service
+from crm_backend.schemas.common import ErrorResponse
+from crm_backend.schemas.dashboard import DashboardSummaryResponse
+from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.dashboard_service import DashboardService
+
+router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
+
+
+@router.get(
+    "/summary",
+    response_model=DashboardSummaryResponse,
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def get_dashboard_summary(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    dashboard_service: DashboardService = Depends(get_dashboard_service),
+) -> DashboardSummaryResponse:
+    return dashboard_service.get_dashboard_summary(actor)
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/notifications.py`
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
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/notifications.py
@@ -0,0 +1,75 @@
+"""HTTP endpoints for the in-app notification module."""
+
+from fastapi import APIRouter, Depends, status
+
+from crm_backend.api.dependencies import get_authenticated_crm_session, get_notification_service
+from crm_backend.schemas.notifications import (
+    NotificationListResponse,
+    NotificationResponse,
+    UnreadCountResponse,
+)
+from crm_backend.schemas.common import ErrorResponse
+from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.notification_service import NotificationService
+
+router = APIRouter(prefix="/notifications", tags=["notifications"])
+
+
+@router.get(
+    "",
+    response_model=NotificationListResponse,
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def list_notifications(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    notification_service: NotificationService = Depends(get_notification_service),
+) -> NotificationListResponse:
+    notifications = notification_service.list_for_user(actor.crm_user.crm_user_id)
+    unread_count = notification_service.count_unread(actor.crm_user.crm_user_id)
+    return NotificationListResponse(
+        notifications=[NotificationResponse.model_validate(n) for n in notifications],
+        unread_count=unread_count,
+    )
+
+
+@router.get(
+    "/unread-count",
+    response_model=UnreadCountResponse,
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def get_unread_count(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    notification_service: NotificationService = Depends(get_notification_service),
+) -> UnreadCountResponse:
+    count = notification_service.count_unread(actor.crm_user.crm_user_id)
+    return UnreadCountResponse(unread_count=count)
+
+
+@router.patch(
+    "/{notification_id}/read",
+    response_model=NotificationResponse,
+    responses={
+        401: {"model": ErrorResponse},
+        403: {"model": ErrorResponse},

... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/reports.py`
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
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/reports.py
@@ -0,0 +1,212 @@
+"""HTTP endpoints for CRM reports."""
+
+from __future__ import annotations
+
+from datetime import date
+from typing import Literal
+
+from fastapi import APIRouter, Depends, Query
+
+from crm_backend.api.dependencies import get_authenticated_crm_session, get_reports_service
+from crm_backend.schemas import ErrorResponse
+from crm_backend.schemas.reports import (
+    DepositRequestReportResponse,
+    ReportOptionItem,
+    StockCriticalReportResponse,
+    TaskReportResponse,
+    TicketReportResponse,
+    UserActivityReportResponse,
+)
+from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.reports_service import ReportsService
+
+
+router = APIRouter(prefix="/api/reports", tags=["reports"])
+
+
+@router.get(
+    "/options/users",
+    response_model=list[ReportOptionItem],
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def get_report_user_options(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    reports_service: ReportsService = Depends(get_reports_service),
+) -> list[ReportOptionItem]:
+    return reports_service.list_user_options(actor)
+
+
+@router.get(
+    "/options/clients",
+    response_model=list[ReportOptionItem],
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def get_report_client_options(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    reports_service: ReportsService = Depends(get_reports_service),
+) -> list[ReportOptionItem]:
+    return reports_service.list_client_options(actor)
+
+
+@router.get(
+    "/options/categories",
+    response_model=list[ReportOptionItem],
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def get_report_category_options(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    reports_service: ReportsService = Depends(get_reports_service),
+) -> list[ReportOptionItem]:
+    return reports_service.list_ca
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/settings.py`
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
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/settings.py
@@ -0,0 +1,255 @@
+"""HTTP endpoints for CRM settings module."""
+
+from __future__ import annotations
+
+from fastapi import APIRouter, Depends, Query
+
+from crm_backend.api.dependencies import get_authenticated_crm_session, get_settings_service
+from crm_backend.schemas import ErrorResponse
+from crm_backend.schemas.settings import (
+    SettingsCategoryResponse,
+    SettingsCategoryWriteRequest,
+    SettingsNotificationRuleResponse,
+    SettingsNotificationRuleWriteRequest,
+    SettingsPriorityResponse,
+    SettingsPriorityWriteRequest,
+    SettingsRoleResponse,
+    SettingsRoleUpdateRequest,
+    SettingsSlaRuleResponse,
+    SettingsSlaRuleWriteRequest,
+    SettingsStatusResponse,
+    SettingsStatusWriteRequest,
+    SettingsTaskTemplateResponse,
+    SettingsTaskTemplateUpdateRequest,
+    SettingsUserRoleAssignmentRequest,
+    SettingsUserRoleAssignmentResponse,
+)
+from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.settings_service import SettingsService
+
+
+router = APIRouter(prefix="/settings", tags=["settings"])
+
+
+@router.get("/roles", response_model=list[SettingsRoleResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
+def list_roles(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    settings_service: SettingsService = Depends(get_settings_service),
+) -> list[SettingsRoleResponse]:
+    return [SettingsRoleResponse.model_validate(role) for role in settings_service.list_roles(actor)]
+
+
+@router.put("/roles/{role_id}", response_model=SettingsRoleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
+def update_role(
+    role_id: str,
+    payload: SettingsRoleUpdateRequest,
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    settings_service: SettingsService = Depends(get_settings_service),
+) -> SettingsRoleResponse:
+    return SettingsRoleResponse.model_validate(settings_s
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/tasks.py`
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

--- a/microtv-crm-backend/src/crm_backend/api/endpoints/tasks.py
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/tasks.py
@@ -6,10 +6,13 @@ from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
 
 from crm_backend.api.dependencies import get_authenticated_crm_session, get_task_application_service
 from crm_backend.schemas import (
+    ApproveTaskRequest,
+    AssignSubtaskRequest,
     CreateTaskFromTemplateRequest,
     CreateTaskTemplateRequest,
     ErrorResponse,
     ExecuteSubtaskActionRequest,
+    RejectTaskApprovalRequest,
     SetTaskTemplateActivationRequest,
     TaskAttachmentResponse,
     TaskDetailResponse,
@@ -177,6 +180,18 @@ def list_tracking_tasks_for_me(
     return [TaskSummaryResponse.model_validate(item) for item in task_service.list_tracking_tasks_for_actor(actor)]
 
 
+@router.get(
+    "/history/me",
+    response_model=list[TaskSummaryResponse],
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def list_task_history_for_me(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    task_service: TaskApplicationService = Depends(get_task_application_service),
+) -> list[TaskSummaryResponse]:
+    return [TaskSummaryResponse.model_validate(item) for item in task_service.list_task_history_for_actor(actor)]
+
+
 @router.get(
     "/unassigned/me",
     response_model=list[UnassignedSubtaskQueueResponse],
@@ -202,6 +217,50 @@ def claim_subtask(
     return TaskDetailResponse.model_validate(task_service.claim_unassigned_subtask(actor, subtask_id))
 
 
+@router.patch(
+    "/subtasks/{subtask_id}/assignment",
+    response_model=TaskDetailResponse,
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
+)
+def assign_subtask(
+    subtask_id: str,
+    payload: AssignSubtaskRequest,
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    task_service: TaskApplicationService = Depends(get_task_application_service),
+) -> TaskDetailResponse:
+    re
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/endpoints/tickets.py`
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
+++ b/microtv-crm-backend/src/crm_backend/api/endpoints/tickets.py
@@ -0,0 +1,287 @@
+"""HTTP endpoints for the ticket module."""
+
+from typing import Annotated
+
+from fastapi import APIRouter, Depends, File, Response, UploadFile, status
+
+from crm_backend.api.dependencies import get_authenticated_crm_session, get_ticket_application_service
+from crm_backend.schemas import (
+    ApproveTicketRequest,
+    AssignTicketRequest,
+    CloseTicketRequest,
+    CreateTicketCommentRequest,
+    CreateTicketRequest,
+    ErrorResponse,
+    RejectTicketApprovalRequest,
+    ReopenTicketRequest,
+    TicketAttachmentResponse,
+    TicketDetailResponse,
+    TicketRoleOptionResponse,
+    TicketSummaryResponse,
+    UpdateTicketStatusRequest,
+)
+from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.ticket_service import TicketApplicationService
+
+
+router = APIRouter(prefix="/tickets", tags=["tickets"])
+
+
+@router.get(
+    "/roles",
+    response_model=list[TicketRoleOptionResponse],
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
+)
+def list_assignable_roles(
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
+) -> list[TicketRoleOptionResponse]:
+    roles = ticket_service.list_assignable_roles(actor)
+    return [
+        TicketRoleOptionResponse(
+            crm_role_id=role.crm_role_id,
+            role_key=role.role_key,
+            role_label=role.role_label,
+        )
+        for role in roles
+    ]
+
+
+@router.post(
+    "",
+    response_model=TicketDetailResponse,
+    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
+)
+def create_ticket(
+    payload: CreateTicketRequest,
+    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
+    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
+) -> TicketDetailResponse:
+    return Tic
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/api/router.py`
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

--- a/microtv-crm-backend/src/crm_backend/api/router.py
+++ b/microtv-crm-backend/src/crm_backend/api/router.py
@@ -5,19 +5,29 @@ from fastapi import APIRouter
 from crm_backend.api.endpoints.auth import router as auth_router
 from crm_backend.api.endpoints.clients import router as clients_router
 from crm_backend.api.endpoints.crm_users import router as crm_users_router
+from crm_backend.api.endpoints.dashboard import router as dashboard_router
 from crm_backend.api.endpoints.health import router as health_router
 from crm_backend.api.endpoints.inventory_flow import router as inventory_flow_router
 from crm_backend.api.endpoints.locations import router as locations_router
+from crm_backend.api.endpoints.notifications import router as notifications_router
+from crm_backend.api.endpoints.reports import router as reports_router
+from crm_backend.api.endpoints.settings import router as settings_router
 from crm_backend.api.endpoints.stock import router as stock_router
 from crm_backend.api.endpoints.tasks import router as tasks_router
+from crm_backend.api.endpoints.tickets import router as tickets_router
 
 
 api_router = APIRouter()
 api_router.include_router(health_router)
 api_router.include_router(auth_router)
+api_router.include_router(dashboard_router)
 api_router.include_router(clients_router)
 api_router.include_router(crm_users_router)
 api_router.include_router(locations_router)
 api_router.include_router(stock_router)
 api_router.include_router(inventory_flow_router)
 api_router.include_router(tasks_router)
+api_router.include_router(tickets_router)
+api_router.include_router(notifications_router)
+api_router.include_router(reports_router)
+api_router.include_router(settings_router)
```

#### 📄 `microtv-crm-backend/src/crm_backend/core/__pycache__/exceptions.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/core/__pycache__/exceptions.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/core/__pycache__/exceptions.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/core/exceptions.py`
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

--- a/microtv-crm-backend/src/crm_backend/core/exceptions.py
+++ b/microtv-crm-backend/src/crm_backend/core/exceptions.py
@@ -319,3 +319,49 @@ class InventoryDispatchItemNotFoundError(ApplicationError):
             message="El item despachado indicado no existe.",
             status_code=404,
         )
+
+
+class TicketAccessDeniedError(ApplicationError):
+    """Señala que el usuario no puede operar el módulo de tickets."""
+
+    def __init__(self, message: str = "El usuario no tiene permisos para operar tickets.") -> None:
+        super().__init__(code="ticket_access_denied", message=message, status_code=403)
+
+
+class TicketNotFoundError(ApplicationError):
+    """Señala que no existe el ticket solicitado."""
+
+    def __init__(self) -> None:
+        super().__init__(
+            code="ticket_not_found",
+            message="El ticket indicado no existe.",
+            status_code=404,
+        )
+
+
+class TicketValidationError(ApplicationError):
+    """Señala una violación de reglas del dominio de tickets."""
+
+    def __init__(self, message: str) -> None:
+        super().__init__(code="ticket_validation_error", message=message, status_code=422)
+
+
+class TicketConflictError(ApplicationError):
+    """Señala un conflicto de estado dentro del flujo de tickets."""
+
+    def __init__(self, message: str) -> None:
+        super().__init__(code="ticket_conflict", message=message, status_code=409)
+
+
+class NotificationNotFoundError(ApplicationError):
+    """Señala que la notificación indicada no existe."""
+
+    def __init__(self) -> None:
+        super().__init__(code="notification_not_found", message="La notificación indicada no existe.", status_code=404)
+
+
+class NotificationAccessDeniedError(ApplicationError):
+    """Señala que el usuario no puede acceder a la notificación indicada."""
+
+    def __init__(self) -> None:
+        super().__init__(code="notification_access_denied", message="No tenés acceso a esa notificación.", status_code=403)
```

#### 📄 `microtv-crm-backend/src/crm_backend/db/__pycache__/bootstrap.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/db/__pycache__/bootstrap.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/db/__pycache__/bootstrap.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/db/bootstrap.py`
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

--- a/microtv-crm-backend/src/crm_backend/db/bootstrap.py
+++ b/microtv-crm-backend/src/crm_backend/db/bootstrap.py
@@ -209,6 +209,13 @@ def _ensure_extension_tables(session: Session) -> None:
         "inventory_request_items",
         "inventory_dispatches",
         "inventory_dispatch_items",
+        "tickets",
+        "ticket_comments",
+        "ticket_attachments",
+        "ticket_status_transitions",
+        "ticket_assignment_history",
+        "ticket_audit_events",
+        "crm_notifications",
     ]
     bind = session.get_bind()
     inspector = inspect(bind)
@@ -218,7 +225,10 @@ def _ensure_extension_tables(session: Session) -> None:
         Base.metadata.create_all(bind=bind, tables=missing_tables)
 
     _ensure_inventory_product_columns(session, inspector)
+    _ensure_inventory_dispatch_columns(session, inspector)
     _ensure_task_attachment_columns(session, inspector)
+    _ensure_ticket_attachment_columns(session, inspector)
+    _ensure_ticket_columns(session, inspector)
 
 
 def _ensure_inventory_product_columns(session: Session, inspector=None) -> None:
@@ -256,3 +266,211 @@ def _ensure_task_attachment_columns(session: Session, inspector=None) -> None:
 
     session.execute(text("CREATE INDEX IF NOT EXISTS idx_task_attachments_comment ON task_attachments(task_comment_id)"))
     session.commit()
+
+
+def _ensure_inventory_dispatch_columns(session: Session, inspector=None) -> None:
+    bind = session.get_bind()
+    active_inspector = inspector or inspect(bind)
+    table_names = set(active_inspector.get_table_names())
+    if "inventory_dispatches" not in table_names:
+        return
+
+    dispatch_columns = {column["name"] for column in active_inspector.get_columns("inventory_dispatches")}
+    if "received_by_crm_user_id" not in dispatch_columns:
+        if bind.dialect.name == "postgresql" and "crm_users" in table_names:
+            session.execute(
+                text(
+                    "ALTER TABLE inventory_dispatches "
+                    "ADD COLUMN received_by_crm_user_id UUID REFERENCES crm_users(crm_user_id)"
+                )
+         
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__init__.py`
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

--- a/microtv-crm-backend/src/crm_backend/models/__init__.py
+++ b/microtv-crm-backend/src/crm_backend/models/__init__.py
@@ -34,8 +34,23 @@ from crm_backend.models.task_execution import (
 	TaskStatus,
 	TransitionAction,
 )
+from crm_backend.models.ticket import (
+	Ticket,
+	TicketAssignmentHistory,
+	TicketAttachment,
+	TicketAttachmentType,
+	TicketAuditEvent,
+	TicketComment,
+	TicketCommentType,
+	TicketPriority,
+	TicketStatus,
+	TicketStatusTransition,
+	TicketTransitionAction,
+)
 from crm_backend.models.task_template import NextAssignmentPolicy, TaskTemplate, TaskTemplateItem, TaskTemplateSubtask, TemplateItemType
 from crm_backend.models.warehouse import Warehouse
+from crm_backend.models.notification import Notification, NotificationEntityType, NotificationType
+from crm_backend.models.settings import CrmCategory, CrmPriority, CrmStatus, NotificationRule, SlaRule
 
 __all__ = [
 	"CrmRole",
@@ -76,5 +91,24 @@ __all__ = [
 	"TemplateItemType",
 	"NextAssignmentPolicy",
 	"TransitionAction",
+	"Ticket",
+	"TicketAssignmentHistory",
+	"TicketAttachment",
+	"TicketAttachmentType",
+	"TicketAuditEvent",
+	"TicketComment",
+	"TicketCommentType",
+	"TicketPriority",
+	"TicketStatus",
+	"TicketStatusTransition",
+	"TicketTransitionAction",
 	"Warehouse",
+	"Notification",
+	"NotificationEntityType",
+	"NotificationType",
+	"CrmCategory",
+	"CrmPriority",
+	"CrmStatus",
+	"SlaRule",
+	"NotificationRule",
 ]
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/__init__.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/models/__pycache__/__init__.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/models/__pycache__/__init__.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/material_flow.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/models/__pycache__/material_flow.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/models/__pycache__/material_flow.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/notification.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/models/__pycache__/notification.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/settings.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/models/__pycache__/settings.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/task_execution.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/models/__pycache__/task_execution.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/models/__pycache__/task_execution.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/__pycache__/ticket.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/models/__pycache__/ticket.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/material_flow.py`
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

--- a/microtv-crm-backend/src/crm_backend/models/material_flow.py
+++ b/microtv-crm-backend/src/crm_backend/models/material_flow.py
@@ -24,7 +24,10 @@ class InventoryRequestStatus(StrEnum):
     """Lifecycle states for additional inventory requests."""
 
     PENDING = "PENDING"
+    PENDING_DISPATCH = "PENDING_DISPATCH"
+    PENDING_RECEIPT = "PENDING_RECEIPT"
     APPROVED = "APPROVED"
+    COMPLETED = "COMPLETED"
     REJECTED = "REJECTED"
     CANCELLED = "CANCELLED"
 
@@ -195,11 +198,15 @@ class InventoryDispatch(Base):
     dispatched_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
     warehouse_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("warehouses.warehouse_id"), index=True)
     dispatch_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
+    received_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
+    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
+    reception_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
 
     task: Mapped[Task | None] = relationship("Task", back_populates="dispatches")
     request: Mapped[InventoryRequest | None] = relationship("InventoryRequest", back_populates="dispatches")
     dispatched_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[dispatched_by_crm_user_id], lazy="joined")
+    received_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[received_by_crm_user_id], lazy="joined")
     items: Mapped[list[InventoryDispatchItem]] = relationship(
         "InventoryDispatchItem",
         back_populates="dispatch",
@@ -220,6 +227,10 @@ class InventoryDispatch(Base):
     def dispatched_by_display_name(self) -> str | None:
         return _user_display_label(self.dispatched_by_user)
 
+    @property
+    def received_by_display_name(self) -> str | None:
+        retur
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/notification.py`
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
+++ b/microtv-crm-backend/src/crm_backend/models/notification.py
@@ -0,0 +1,66 @@
+"""Notification domain model for in-app operational alerts."""
+
+from __future__ import annotations
+
+from datetime import datetime
+from enum import StrEnum
+from uuid import uuid4
+
+from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid, func
+from sqlalchemy.orm import Mapped, mapped_column, relationship
+
+from crm_backend.db.base import Base
+
+
+class NotificationType(StrEnum):
+    """Supported in-app notification event types."""
+
+    # Ticket events
+    TICKET_ASSIGNED = "ticket_assigned"
+    TICKET_REASSIGNED = "ticket_reassigned"
+    TICKET_REOPENED = "ticket_reopened"
+    TICKET_PENDING_APPROVAL = "ticket_pending_approval"
+    TICKET_APPROVED = "ticket_approved"
+    TICKET_REJECTED = "ticket_rejected"
+    TICKET_RETURNED_TO_TECHNICIAN = "ticket_returned_to_technician"
+
+    # Task / subtask events
+    TASK_SUBTASK_ASSIGNED = "task_subtask_assigned"
+    TASK_SUBTASK_REASSIGNED = "task_subtask_reassigned"
+    TASK_PENDING_APPROVAL = "task_pending_approval"
+    TASK_APPROVED = "task_approved"
+    TASK_REJECTED = "task_rejected"
+
+    # Deposit / inventory request events
+    DEPOSIT_REQUEST_CREATED = "deposit_request_created"
+    DEPOSIT_REQUEST_APPROVED = "deposit_request_approved"
+    DEPOSIT_REQUEST_REJECTED = "deposit_request_rejected"
+    DEPOSIT_REQUEST_DISPATCHED = "deposit_request_dispatched"
+    DEPOSIT_REQUEST_RECEIPT_PENDING = "deposit_request_receipt_pending"
+    DEPOSIT_REQUEST_RECEIVED = "deposit_request_received"
+
+
+class NotificationEntityType(StrEnum):
+    """Entity types that a notification can reference."""
+
+    TICKET = "ticket"
+    TASK = "task"
+    DEPOSIT_REQUEST = "deposit_request"
+
+
+class Notification(Base):
+    """Persisted in-app notification record."""
+
+    __tablename__ = "crm_notifications"
+
+    notification_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
+    recipient_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/settings.py`
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
+++ b/microtv-crm-backend/src/crm_backend/models/settings.py
@@ -0,0 +1,82 @@
+"""Configurable CRM settings domain models."""
+
+from __future__ import annotations
+
+from datetime import datetime
+from uuid import uuid4
+
+from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, Uuid, UniqueConstraint, func
+from sqlalchemy.orm import Mapped, mapped_column
+
+from crm_backend.db.base import Base
+
+
+class CrmCategory(Base):
+    """Configurable category used across CRM entities."""
+
+    __tablename__ = "crm_categories"
+
+    category_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
+    name: Mapped[str] = mapped_column(String(120), index=True)
+    category_type: Mapped[str] = mapped_column(String(50), index=True)
+    description: Mapped[str | None] = mapped_column(Text, nullable=True)
+    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
+    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
+
+
+class CrmPriority(Base):
+    """Configurable priorities that coexist with legacy enum values."""
+
+    __tablename__ = "crm_priorities"
+
+    priority_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
+    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
+    name: Mapped[str] = mapped_column(String(80))
+    order_index: Mapped[int] = mapped_column(Integer, default=0)
+    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
+    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
+    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
+
+
+class CrmStatus(Base):
+    """Configurable statuses by entity type (ticket/task/deposit)."""
+
+    __tablename__ = "crm_statuses"
+    __table_args__ = (UniqueConstraint("code", "entity_type", name="uq_crm_status_code_entity"),)
+
+    status_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primar
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/task_execution.py`
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

--- a/microtv-crm-backend/src/crm_backend/models/task_execution.py
+++ b/microtv-crm-backend/src/crm_backend/models/task_execution.py
@@ -26,6 +26,7 @@ class TaskStatus(StrEnum):
     PENDING = "PENDING"
     IN_PROGRESS = "IN_PROGRESS"
     BLOCKED = "BLOCKED"
+    PENDING_APPROVAL = "PENDING_APPROVAL"
     COMPLETED = "COMPLETED"
 
 
@@ -61,6 +62,7 @@ class TransitionAction(StrEnum):
     """Supported subtask actions."""
 
     CLAIM_SUBTASK = "claim_subtask"
+    ASSIGN_SUBTASK = "assign_subtask"
     START_SUBTASK = "start_subtask"
     CLOSE_SUBTASK = "close_subtask"
     REJECT_SUBTASK = "reject_subtask"
```

#### 📄 `microtv-crm-backend/src/crm_backend/models/ticket.py`
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
+++ b/microtv-crm-backend/src/crm_backend/models/ticket.py
@@ -0,0 +1,385 @@
+"""Ticket domain models for operational incident tracking."""
+
+from __future__ import annotations
+
+from datetime import datetime
+from enum import StrEnum
+from pathlib import Path
+from typing import TYPE_CHECKING
+from uuid import uuid4
+
+from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid, func
+from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship
+
+from crm_backend.db.base import Base
+
+if TYPE_CHECKING:
+    from crm_backend.models.crm_role import CrmRole
+    from crm_backend.models.crm_user import CrmUser
+    from crm_backend.models.material_flow import InventoryDispatch, InventoryRequest
+    from crm_backend.models.task_reference import Client, Location
+
+
+class TicketStatus(StrEnum):
+    """Supported ticket lifecycle states."""
+
+    OPEN = "OPEN"
+    IN_PROGRESS = "IN_PROGRESS"
+    ON_HOLD = "ON_HOLD"
+    RESOLVED = "RESOLVED"
+    PENDING_APPROVAL = "PENDING_APPROVAL"
+    CLOSED = "CLOSED"
+
+
+class TicketPriority(StrEnum):
+    """Supported ticket priority values."""
+
+    LOW = "LOW"
+    MEDIUM = "MEDIUM"
+    HIGH = "HIGH"
+    CRITICAL = "CRITICAL"
+
+
+class TicketCommentType(StrEnum):
+    """Comment types used by ticket timeline."""
+
+    GENERAL = "general"
+    SYSTEM = "system"
+    CLOSURE = "closure"
+
+
+class TicketAttachmentType(StrEnum):
+    """Supported persisted attachment types."""
+
+    PHOTO = "PHOTO"
+    VIDEO = "VIDEO"
+    DOCUMENT = "DOCUMENT"
+
+
+class TicketTransitionAction(StrEnum):
+    """Supported explicit status transition actions."""
+
+    START_WORK = "start_work"
+    PUT_ON_HOLD = "put_on_hold"
+    MARK_RESOLVED = "mark_resolved"
+    SUBMIT_FOR_APPROVAL = "submit_for_approval"
+    APPROVE_CLOSE = "approve_close"
+    REJECT_CLOSE = "reject_close"
+    REOPEN = "reopen"
+    CLOSE = "close"
+
+
+class Ticket(Base):
+    """Operational ticket aggregate root."""
+
+    __tablename__ = "tickets"
+
+    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), pr
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/__init__.py`
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

--- a/microtv-crm-backend/src/crm_backend/repositories/__init__.py
+++ b/microtv-crm-backend/src/crm_backend/repositories/__init__.py
@@ -5,10 +5,12 @@ from crm_backend.repositories.crm_role_repository import CrmRoleRepository
 from crm_backend.repositories.crm_user_repository import CrmUserRepository
 from crm_backend.repositories.inventory_flow_repository import InventoryFlowRepository
 from crm_backend.repositories.location_repository import LocationRepository
+from crm_backend.repositories.notification_repository import NotificationRepository
 from crm_backend.repositories.stock_category_repository import StockCategoryRepository
 from crm_backend.repositories.stock_product_repository import StockProductRepository
 from crm_backend.repositories.task_repository import TaskRepository
 from crm_backend.repositories.task_template_repository import TaskTemplateRepository
+from crm_backend.repositories.ticket_repository import TicketRepository
 
 __all__ = [
 	"ClientRepository",
@@ -16,8 +18,10 @@ __all__ = [
 	"CrmUserRepository",
 	"InventoryFlowRepository",
 	"LocationRepository",
+	"NotificationRepository",
 	"StockCategoryRepository",
 	"StockProductRepository",
 	"TaskRepository",
 	"TaskTemplateRepository",
+	"TicketRepository",
 ]
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/__pycache__/__init__.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/repositories/__pycache__/__init__.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/repositories/__pycache__/__init__.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/__pycache__/crm_role_repository.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/repositories/__pycache__/crm_role_repository.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/repositories/__pycache__/crm_role_repository.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/__pycache__/inventory_flow_repository.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/repositories/__pycache__/inventory_flow_repository.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/repositories/__pycache__/inventory_flow_repository.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/__pycache__/notification_repository.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/repositories/__pycache__/notification_repository.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/__pycache__/task_repository.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/repositories/__pycache__/task_repository.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/repositories/__pycache__/task_repository.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/__pycache__/ticket_repository.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/repositories/__pycache__/ticket_repository.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/crm_role_repository.py`
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

--- a/microtv-crm-backend/src/crm_backend/repositories/crm_role_repository.py
+++ b/microtv-crm-backend/src/crm_backend/repositories/crm_role_repository.py
@@ -30,3 +30,15 @@ class CrmRoleRepository:
 
         statement = select(CrmRole).where(CrmRole.role_key == role_key, CrmRole.is_active.is_(True))
         return self._session.scalar(statement)
+
+    def get_by_id(self, crm_role_id: str) -> CrmRole | None:
+        """Return an active CRM role by internal identifier."""
+
+        statement = select(CrmRole).where(CrmRole.crm_role_id == crm_role_id, CrmRole.is_active.is_(True))
+        return self._session.scalar(statement)
+
+    def list_active(self) -> list[CrmRole]:
+        """Return all active CRM roles ordered by label."""
+
+        statement = select(CrmRole).where(CrmRole.is_active.is_(True)).order_by(CrmRole.role_label.asc(), CrmRole.role_key.asc())
+        return list(self._session.scalars(statement).all())
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/inventory_flow_repository.py`
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

--- a/microtv-crm-backend/src/crm_backend/repositories/inventory_flow_repository.py
+++ b/microtv-crm-backend/src/crm_backend/repositories/inventory_flow_repository.py
@@ -91,7 +91,6 @@ class InventoryFlowRepository:
                 selectinload(InventoryRequest.items).selectinload(InventoryRequestItem.product),
                 selectinload(InventoryRequest.dispatches).selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product),
             )
-            .where(InventoryRequest.request_status.in_(["PENDING", "APPROVED"]))
             .order_by(InventoryRequest.requested_at.desc())
         )
         return list(self._session.scalars(statement).all())
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/notification_repository.py`
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
+++ b/microtv-crm-backend/src/crm_backend/repositories/notification_repository.py
@@ -0,0 +1,77 @@
+"""Repository for notification persistence and querying."""
+
+from __future__ import annotations
+
+from datetime import UTC, datetime
+
+from sqlalchemy import func, select
+from sqlalchemy.orm import Session
+
+from crm_backend.models.notification import Notification
+
+
+class NotificationRepository:
+    """Persist and query per-user notifications."""
+
+    def __init__(self, session: Session) -> None:
+        self._session = session
+
+    def save(self, notification: Notification) -> Notification:
+        self._session.add(notification)
+        self._session.commit()
+        self._session.refresh(notification)
+        return notification
+
+    def save_bulk(self, notifications: list[Notification]) -> None:
+        for notification in notifications:
+            self._session.add(notification)
+        self._session.commit()
+
+    def list_for_user(self, recipient_crm_user_id: str, limit: int = 20) -> list[Notification]:
+        stmt = (
+            select(Notification)
+            .where(Notification.recipient_crm_user_id == recipient_crm_user_id)
+            .order_by(Notification.created_at.desc())
+            .limit(limit)
+        )
+        return list(self._session.scalars(stmt))
+
+    def count_unread_for_user(self, recipient_crm_user_id: str) -> int:
+        stmt = (
+            select(func.count())
+            .select_from(Notification)
+            .where(
+                Notification.recipient_crm_user_id == recipient_crm_user_id,
+                Notification.is_read.is_(False),
+            )
+        )
+        return self._session.scalar(stmt) or 0
+
+    def get_by_id(self, notification_id: str) -> Notification | None:
+        return self._session.scalar(
+            select(Notification).where(Notification.notification_id == notification_id)
+        )
+
+    def mark_read(self, notification: Notification) -> Notification:
+        notification.is_read = True
+        notification.read_at = datetime.now(UTC)
+     
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/task_repository.py`
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

--- a/microtv-crm-backend/src/crm_backend/repositories/task_repository.py
+++ b/microtv-crm-backend/src/crm_backend/repositories/task_repository.py
@@ -1,6 +1,6 @@
 """Repository for task execution aggregates."""
 
-from sqlalchemy import or_, select
+from sqlalchemy import select
 from sqlalchemy.orm import Session, selectinload
 
 from crm_backend.models import (
@@ -18,6 +18,7 @@ from crm_backend.models import (
     TaskAuditEvent,
     TaskComment,
     TaskRequiredMaterial,
+    TaskStatus,
 )
 
 
@@ -76,14 +77,7 @@ class TaskRepository:
         statement = (
             select(Task)
             .options(*self._summary_options())
-            .where(
-                or_(
-                    Task.current_assigned_crm_user_id == crm_user_id,
-                    Task.task_id.in_(
-                        select(Subtask.task_id).where(Subtask.current_assigned_crm_user_id == crm_user_id)
-                    ),
-                )
-            )
+            .where(Task.current_assigned_crm_user_id == crm_user_id)
             .order_by(Task.updated_at.desc())
         )
         return list(self._session.scalars(statement).all())
@@ -93,15 +87,33 @@ class TaskRepository:
             select(Task)
             .options(*self._summary_options())
             .join(Subtask, Subtask.task_id == Task.task_id)
-            .where(Subtask.responsible_role_key.in_(role_keys))
+            .where(Subtask.responsible_role_key.in_(role_keys), Task.status != TaskStatus.COMPLETED.value)
             .order_by(Task.updated_at.desc())
         )
         return list(self._session.scalars(statement).unique().all())
 
+    def list_tracking_tasks_for_all_roles(self) -> list[Task]:
+        statement = (
+            select(Task)
+            .options(*self._summary_options())
+            .where(Task.status != TaskStatus.COMPLETED.value)
+            .order_by(Task.updated_at.desc())
+        )
+        return list(self._session.scalars(statement).all())
+
     def list_all_tasks(self) -> list[Task]:
         statement = select(Task).options(*self._summary_options()).order_by(Task.updated_at.desc())
 
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/repositories/ticket_repository.py`
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
+++ b/microtv-crm-backend/src/crm_backend/repositories/ticket_repository.py
@@ -0,0 +1,121 @@
+"""Repository for ticket aggregates."""
+
+from sqlalchemy import select
+from sqlalchemy.orm import Session, selectinload
+
+from crm_backend.models import (
+    InventoryDispatch,
+    InventoryDispatchItem,
+    InventoryRequest,
+    InventoryRequestItem,
+    Ticket,
+    TicketAssignmentHistory,
+    TicketAttachment,
+    TicketAuditEvent,
+    TicketComment,
+    TicketStatus,
+    TicketStatusTransition,
+)
+
+
+class TicketRepository:
+    """Persist and query ticket aggregates."""
+
+    def __init__(self, session: Session) -> None:
+        self._session = session
+
+    @property
+    def session(self) -> Session:
+        return self._session
+
+    def save(self, ticket: Ticket) -> Ticket:
+        self._session.add(ticket)
+        self._session.commit()
+        self._session.refresh(ticket)
+        return self.get_ticket_detail(ticket.ticket_id) or ticket
+
+    def _summary_options(self):
+        return ()
+
+    def _detail_options(self):
+        return (
+            selectinload(Ticket.comments).selectinload(TicketComment.attachments),
+            selectinload(Ticket.attachments),
+            selectinload(Ticket.status_history),
+            selectinload(Ticket.assignment_history),
+            selectinload(Ticket.audit_events),
+            selectinload(Ticket.inventory_requests)
+            .selectinload(InventoryRequest.items)
+            .selectinload(InventoryRequestItem.product),
+            selectinload(Ticket.inventory_requests)
+            .selectinload(InventoryRequest.dispatches)
+            .selectinload(InventoryDispatch.items)
+            .selectinload(InventoryDispatchItem.product),
+            selectinload(Ticket.dispatches)
+            .selectinload(InventoryDispatch.items)
+            .selectinload(InventoryDispatchItem.product),
+        )
+
+    def get_ticket_detail(self, ticket_id: str) -> Ticket | None:
+        statement = select(Ticket).options(*self._detail_options()).where(Ticket.ticket_id == ticket_
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__init__.py`
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

--- a/microtv-crm-backend/src/crm_backend/schemas/__init__.py
+++ b/microtv-crm-backend/src/crm_backend/schemas/__init__.py
@@ -40,9 +40,12 @@ from crm_backend.schemas.stock import (
     StockProductResponse,
 )
 from crm_backend.schemas.tasks import (
+    ApproveTaskRequest,
+    AssignSubtaskRequest,
     CreateTaskFromTemplateRequest,
     CreateTaskTemplateRequest,
     ExecuteSubtaskActionRequest,
+    RejectTaskApprovalRequest,
     SetTaskTemplateActivationRequest,
     TaskAttachmentResponse,
     TaskDetailResponse,
@@ -52,6 +55,24 @@ from crm_backend.schemas.tasks import (
     UnassignedSubtaskQueueResponse,
     UpdateSubtaskProgressRequest,
 )
+from crm_backend.schemas.tickets import (
+    ApproveTicketRequest,
+    AssignTicketRequest,
+    CloseTicketRequest,
+    CreateTicketCommentRequest,
+    CreateTicketRequest,
+    RejectTicketApprovalRequest,
+    ReopenTicketRequest,
+    TicketAssignmentHistoryResponse,
+    TicketAttachmentResponse,
+    TicketAuditEventResponse,
+    TicketCommentResponse,
+    TicketDetailResponse,
+    TicketRoleOptionResponse,
+    TicketStatusTransitionResponse,
+    TicketSummaryResponse,
+    UpdateTicketStatusRequest,
+)
 
 __all__ = [
     "AccessPendingResponse",
@@ -89,7 +110,10 @@ __all__ = [
     "StockProductResponse",
     "CreateTaskFromTemplateRequest",
     "CreateTaskTemplateRequest",
+    "ApproveTaskRequest",
+    "AssignSubtaskRequest",
     "ExecuteSubtaskActionRequest",
+    "RejectTaskApprovalRequest",
     "SetTaskTemplateActivationRequest",
     "TaskAttachmentResponse",
     "TaskDetailResponse",
@@ -98,4 +122,20 @@ __all__ = [
     "UpdateTaskTemplateRequest",
     "UnassignedSubtaskQueueResponse",
     "UpdateSubtaskProgressRequest",
+    "ApproveTicketRequest",
+    "AssignTicketRequest",
+    "CloseTicketRequest",
+    "CreateTicketCommentRequest",
+    "CreateTicketRequest",
+    "RejectTicketApprovalRequest",
+    "ReopenTicketRequest",
+    "TicketAssignmentHistoryResponse",
+    "TicketAttachmentResponse",
+    "TicketAuditEventResponse",
+    "TicketCommentResponse",
+    "TicketDetailResponse",
+    "TicketR
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/__init__.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/schemas/__pycache__/__init__.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/__init__.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/clients.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/schemas/__pycache__/clients.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/clients.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/dashboard.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/dashboard.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/material_flow.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/schemas/__pycache__/material_flow.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/material_flow.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/notifications.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/notifications.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/reports.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/reports.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/settings.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/settings.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/tasks.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/schemas/__pycache__/tasks.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/tasks.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/__pycache__/tickets.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/schemas/__pycache__/tickets.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/clients.py`
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

--- a/microtv-crm-backend/src/crm_backend/schemas/clients.py
+++ b/microtv-crm-backend/src/crm_backend/schemas/clients.py
@@ -15,6 +15,7 @@ class ClientLocationPayload(BaseModel):
 class ClientLocationResponse(BaseModel):
     model_config = ConfigDict(from_attributes=True)
 
+    location_id: str
     latitude: float
     longitude: float
     address_label: str | None
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/dashboard.py`
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
+++ b/microtv-crm-backend/src/crm_backend/schemas/dashboard.py
@@ -0,0 +1,56 @@
+"""Schemas for dashboard summary endpoint."""
+
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Literal
+
+from pydantic import BaseModel
+
+
+KpiVariantLiteral = Literal["danger", "info", "warning", "success"]
+TicketPriorityToneLiteral = Literal["critical", "high", "medium", "low"]
+TicketStatusToneLiteral = Literal["neutral", "progress", "warning", "success"]
+ActivityToneLiteral = Literal["danger", "info", "warning", "success"]
+
+
+class DashboardKpiResponse(BaseModel):
+    key: str
+    label: str
+    value: int
+    secondary: str
+    variant: KpiVariantLiteral
+
+
+class DashboardRecentTicketResponse(BaseModel):
+    ticket_id: str
+    ticket_public_id: str
+    subject: str
+    client: str
+    priority: str
+    priority_tone: TicketPriorityToneLiteral
+    status: str
+    status_tone: TicketStatusToneLiteral
+    assigned_to: str
+    assigned_initials: str
+    target_route: str
+
+
+class DashboardRecentActivityResponse(BaseModel):
+    type: str
+    tone: ActivityToneLiteral
+    text: str
+    timestamp: datetime
+    actor: str
+    target_entity_type: str | None
+    target_entity_id: str | None
+    target_public_code: str | None
+    target_route: str | None
+
+
+class DashboardSummaryResponse(BaseModel):
+    page_title: str
+    page_subtitle: str
+    kpis: list[DashboardKpiResponse]
+    recent_tickets: list[DashboardRecentTicketResponse]
+    recent_activity: list[DashboardRecentActivityResponse]
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/material_flow.py`
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

--- a/microtv-crm-backend/src/crm_backend/schemas/material_flow.py
+++ b/microtv-crm-backend/src/crm_backend/schemas/material_flow.py
@@ -61,6 +61,7 @@ class CreateTaskDispatchRequest(BaseModel):
 
 class ConfirmDispatchItemRequest(BaseModel):
     confirmation_type: Literal["received", "delivered", "installed"]
+    reception_comment: str | None = None
 
 
 class InventoryRequestItemResponse(BaseModel):
@@ -107,6 +108,10 @@ class InventoryDispatchResponse(BaseModel):
     request_id: str | None
     dispatched_by_crm_user_id: str
     dispatched_by_display_name: str | None = None
+    received_by_crm_user_id: str | None = None
+    received_by_display_name: str | None = None
+    received_at: datetime | None = None
+    reception_comment: str | None = None
     warehouse_id: str
     dispatch_notes: str | None
     created_at: datetime
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/notifications.py`
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
+++ b/microtv-crm-backend/src/crm_backend/schemas/notifications.py
@@ -0,0 +1,32 @@
+"""Pydantic schemas for the notification module."""
+
+from __future__ import annotations
+
+from datetime import datetime
+
+from pydantic import BaseModel, ConfigDict
+
+
+class NotificationResponse(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    notification_id: str
+    recipient_crm_user_id: str
+    notification_type: str
+    title: str
+    body: str
+    entity_type: str | None
+    entity_id: str | None
+    is_read: bool
+    created_at: datetime
+    read_at: datetime | None
+    metadata_json: dict | None = None
+
+
+class NotificationListResponse(BaseModel):
+    notifications: list[NotificationResponse]
+    unread_count: int
+
+
+class UnreadCountResponse(BaseModel):
+    unread_count: int
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/reports.py`
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
+++ b/microtv-crm-backend/src/crm_backend/schemas/reports.py
@@ -0,0 +1,177 @@
+"""Schemas for CRM reporting endpoints."""
+
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Literal
+
+from pydantic import BaseModel, Field
+
+
+ReportKind = Literal[
+    "tickets",
+    "tasks",
+    "stock_critical",
+    "deposit_requests",
+    "user_activity",
+]
+
+ChartKind = Literal["area", "line", "bar", "horizontal_bar", "donut", "pie"]
+
+
+class ReportSeriesPoint(BaseModel):
+    label: str
+    date: str
+    value: float
+    meta: dict[str, str | float | int | None] = Field(default_factory=dict)
+
+
+class ReportOptionItem(BaseModel):
+    id: str
+    label: str
+
+
+class ReportKpiItem(BaseModel):
+    key: str
+    label: str
+    value: float | int | str
+
+
+class ReportSummaryBase(BaseModel):
+    total: int
+
+
+class TicketReportSummary(ReportSummaryBase):
+    open: int
+    closed: int
+    pending: int
+    avg_resolution_hours: float | None = None
+
+
+class TaskReportSummary(ReportSummaryBase):
+    in_progress: int
+    closed: int
+    overdue: int
+    blocked: int
+
+
+class StockCriticalReportSummary(ReportSummaryBase):
+    without_stock: int
+    below_minimum: int
+    valued_stock: float | None = None
+
+
+class DepositRequestReportSummary(ReportSummaryBase):
+    pending: int
+    approved: int
+    dispatched: int
+    rejected: int
+    avg_dispatch_hours: float | None = None
+
+
+class UserActivityReportSummary(ReportSummaryBase):
+    tickets_created: int
+    tickets_assigned: int
+    tickets_closed: int
+    tasks_assigned: int
+    tasks_closed: int
+    requests_created: int
+    requests_approved: int
+    requests_dispatched: int
+
+
+class TicketReportRow(BaseModel):
+    ticket_number: str
+    title: str
+    client: str
+    priority: str
+    status: str
+    assigned_to: str | None = None
+    created_at: datetime
+    closed_at: datetime | None = None
+
+
+class TaskReportRow(BaseModel):
+    task_code: str
+    title: str
+    status: str
+    technician: str | None = None
+    
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/settings.py`
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
+++ b/microtv-crm-backend/src/crm_backend/schemas/settings.py
@@ -0,0 +1,145 @@
+"""Schemas for CRM settings module."""
+
+from __future__ import annotations
+
+from datetime import datetime
+
+from pydantic import BaseModel, ConfigDict, Field
+
+
+class SettingsRoleResponse(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    crm_role_id: str
+    role_key: str
+    role_label: str
+    description: str | None
+    is_active: bool
+
+
+class SettingsRoleUpdateRequest(BaseModel):
+    role_label: str = Field(..., min_length=1, max_length=100)
+    description: str | None = None
+    is_active: bool = True
+
+
+class SettingsUserRoleAssignmentResponse(BaseModel):
+    crm_user_id: str
+    display_name: str | None
+    email: str | None
+    role_keys: list[str] = Field(default_factory=list)
+
+
+class SettingsUserRoleAssignmentRequest(BaseModel):
+    role_keys: list[str] = Field(default_factory=list)
+
+
+class SettingsCategoryResponse(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    category_id: str
+    name: str
+    category_type: str
+    description: str | None
+    is_active: bool
+    created_at: datetime
+
+
+class SettingsCategoryWriteRequest(BaseModel):
+    name: str = Field(..., min_length=1, max_length=120)
+    category_type: str = Field(..., min_length=1, max_length=50)
+    description: str | None = None
+    is_active: bool = True
+
+
+class SettingsPriorityResponse(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    priority_id: str
+    code: str
+    name: str
+    order_index: int
+    color: str | None
+    is_active: bool
+
+
+class SettingsPriorityWriteRequest(BaseModel):
+    code: str = Field(..., min_length=1, max_length=40)
+    name: str = Field(..., min_length=1, max_length=80)
+    order_index: int = Field(default=0, ge=0)
+    color: str | None = Field(default=None, max_length=20)
+    is_active: bool = True
+
+
+class SettingsStatusResponse(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    status_id: str
+    code: str
+    name: str
+    
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/tasks.py`
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

--- a/microtv-crm-backend/src/crm_backend/schemas/tasks.py
+++ b/microtv-crm-backend/src/crm_backend/schemas/tasks.py
@@ -76,6 +76,19 @@ class ExecuteSubtaskActionRequest(BaseModel):
     attachment_ids: list[str] = Field(default_factory=list)
 
 
+class AssignSubtaskRequest(BaseModel):
+    assigned_crm_user_id: str = Field(..., min_length=1)
+    notes: str | None = None
+
+
+class ApproveTaskRequest(BaseModel):
+    comment: str | None = None
+
+
+class RejectTaskApprovalRequest(BaseModel):
+    comment: str = Field(..., min_length=1)
+
+
 class TaskAttachmentResponse(BaseModel):
     model_config = ConfigDict(from_attributes=True)
```

#### 📄 `microtv-crm-backend/src/crm_backend/schemas/tickets.py`
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
+++ b/microtv-crm-backend/src/crm_backend/schemas/tickets.py
@@ -0,0 +1,174 @@
+"""Schemas for the ticket module."""
+
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Literal
+
+from pydantic import BaseModel, ConfigDict, Field
+
+from crm_backend.schemas.locations import LocationResponse
+from crm_backend.schemas.material_flow import InventoryDispatchResponse, InventoryRequestResponse
+
+
+TicketStatusLiteral = Literal["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "PENDING_APPROVAL", "CLOSED"]
+TicketPriorityLiteral = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
+TicketCommentTypeLiteral = Literal["general", "system", "closure"]
+
+
+class CreateTicketRequest(BaseModel):
+    title: str = Field(..., min_length=1, max_length=255)
+    client_id: str
+    location_id: str | None = None
+    description: str = Field(..., min_length=1)
+    priority: TicketPriorityLiteral = "MEDIUM"
+    assigned_role_id: str | None = None
+    assigned_user_id: str | None = None
+
+
+class AssignTicketRequest(BaseModel):
+    assigned_role_id: str | None = None
+    assigned_user_id: str | None = None
+    notes: str | None = None
+
+
+class CreateTicketCommentRequest(BaseModel):
+    body: str = Field(..., min_length=1)
+    location_id: str | None = None
+    attachment_ids: list[str] = Field(default_factory=list)
+
+
+class UpdateTicketStatusRequest(BaseModel):
+    to_status: Literal["IN_PROGRESS", "ON_HOLD", "RESOLVED", "OPEN"]
+    comment: str | None = None
+    attachment_ids: list[str] = Field(default_factory=list)
+
+
+class CloseTicketRequest(BaseModel):
+    comment: str
+    attachment_ids: list[str] = Field(default_factory=list)
+
+
+class ApproveTicketRequest(BaseModel):
+    comment: str | None = None
+
+
+class RejectTicketApprovalRequest(BaseModel):
+    comment: str = Field(..., min_length=1)
+
+
+class ReopenTicketRequest(BaseModel):
+    comment: str = Field(..., min_length=1)
+
+
+class TicketAttachmentResponse(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    id: str
+    fileName: str
+   
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__init__.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/__init__.py
+++ b/microtv-crm-backend/src/crm_backend/services/__init__.py
@@ -7,10 +7,15 @@ from crm_backend.services.client_service import (
 	CreateClientCommand,
 	UpdateClientCommand,
 )
+from crm_backend.services.dashboard_service import DashboardService
 from crm_backend.services.location_service import CreateLocationCommand, LocationApplicationService
 from crm_backend.services.material_flow_service import InventoryRequestFacade, TaskMaterialFlowFacade
+from crm_backend.services.notification_service import NotificationService
 from crm_backend.services.role_resolution_service import RoleResolutionService
+from crm_backend.services.reports_service import ReportsService
+from crm_backend.services.settings_service import SettingsService
 from crm_backend.services.stock_service import CreateStockProductCommand, StockApplicationService
+from crm_backend.services.ticket_service import TicketApplicationService
 from crm_backend.services.tasks import TaskApplicationService
 
 __all__ = [
@@ -19,12 +24,17 @@ __all__ = [
 	"ClientLocationCommand",
 	"CreateClientCommand",
 	"UpdateClientCommand",
+	"DashboardService",
 	"CreateLocationCommand",
 	"LocationApplicationService",
 	"InventoryRequestFacade",
 	"TaskMaterialFlowFacade",
+	"NotificationService",
 	"RoleResolutionService",
+	"ReportsService",
+	"SettingsService",
 	"CreateStockProductCommand",
 	"StockApplicationService",
+	"TicketApplicationService",
 	"TaskApplicationService",
 ]
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/__init__.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/__pycache__/__init__.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/__pycache__/__init__.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/client_service.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/__pycache__/client_service.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/__pycache__/client_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/dashboard_service.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/services/__pycache__/dashboard_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/location_service.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/__pycache__/location_service.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/__pycache__/location_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/material_flow_service.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/__pycache__/material_flow_service.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/__pycache__/material_flow_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/notification_service.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/services/__pycache__/notification_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/reports_service.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/services/__pycache__/reports_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/settings_service.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/services/__pycache__/settings_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/__pycache__/ticket_service.cpython-313.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/src/crm_backend/services/__pycache__/ticket_service.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/client_service.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/client_service.py
+++ b/microtv-crm-backend/src/crm_backend/services/client_service.py
@@ -48,6 +48,7 @@ class UpdateClientCommand:
 class ClientLocationView:
     """Serializable client location snapshot returned by the API."""
 
+    location_id: str
     latitude: float
     longitude: float
     address_label: str | None
@@ -155,6 +156,7 @@ class ClientApplicationService:
         if location is None:
             return None
         return ClientLocationView(
+            location_id=location.location_id,
             latitude=float(location.latitude),
             longitude=float(location.longitude),
             address_label=location.address_label,
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/dashboard_service.py`
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
+++ b/microtv-crm-backend/src/crm_backend/services/dashboard_service.py
@@ -0,0 +1,437 @@
+"""Dashboard application service with role-aware summary aggregation."""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from datetime import UTC, datetime, timedelta
+
+from sqlalchemy import and_, exists, func, or_, select, true
+from sqlalchemy.orm import Session, aliased
+
+from crm_backend.models import Notification, Subtask, Task, TaskStatus, Ticket, TicketPriority, TicketStatus
+from crm_backend.schemas.dashboard import (
+    DashboardKpiResponse,
+    DashboardRecentActivityResponse,
+    DashboardRecentTicketResponse,
+    DashboardSummaryResponse,
+)
+from crm_backend.services.auth_service import ResolvedCrmSession
+
+
+@dataclass(slots=True)
+class VisibilityScope:
+    is_admin_or_executive: bool
+    is_tecnico: bool
+    is_deposito: bool
+    role_keys: list[str]
+    role_ids: list[str]
+    actor_crm_user_id: str
+
+
+class DashboardService:
+    """Build dashboard metrics and lists from live DB data."""
+
+    _OPERATIVE_SEGMENT_KEYS = {"tecnico", "deposito"}
+
+    def __init__(self, session: Session) -> None:
+        self._session = session
+
+    def get_dashboard_summary(self, actor: ResolvedCrmSession) -> DashboardSummaryResponse:
+        return DashboardSummaryResponse(
+            page_title="Resumen operativo",
+            page_subtitle=(
+                "Seguimiento general de tickets, tareas y actividad reciente del equipo "
+                "con datos reales de operación."
+            ),
+            kpis=self.get_kpis(actor),
+            recent_tickets=self.get_recent_tickets(actor),
+            recent_activity=self.get_recent_activity(actor),
+        )
+
+    def get_kpis(self, actor: ResolvedCrmSession) -> list[DashboardKpiResponse]:
+        scope = self._build_scope(actor)
+        now = datetime.now(UTC)
+        week_start = self._start_of_week(now)
+        prev_week_start = week_start - timedelta(days=7)
+        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
+
+ 
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/location_service.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/location_service.py
+++ b/microtv-crm-backend/src/crm_backend/services/location_service.py
@@ -19,11 +19,13 @@ class CreateLocationCommand:
 class LocationApplicationService:
     """Persist reusable locations for clients and tasks."""
 
+    OPERATIONAL_ROLE_KEYS = {"admin", "ejecutivo", "tecnico", "deposito"}
+
     def __init__(self, repository: LocationRepository) -> None:
         self._repository = repository
 
     def create_location(self, actor: ResolvedCrmSession, command: CreateLocationCommand) -> Location:
-        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
+        if not self.OPERATIONAL_ROLE_KEYS.intersection(actor.role_keys):
             raise ClientAccessDeniedError("El usuario no puede crear ubicaciones operativas.")
 
         normalized_address = command.address_label.strip() if command.address_label else None
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/material_flow_service.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/material_flow_service.py
+++ b/microtv-crm-backend/src/crm_backend/services/material_flow_service.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
+import logging
 from datetime import UTC, datetime
 from uuid import uuid4
 
@@ -16,6 +17,8 @@ from crm_backend.core.exceptions import (
     TaskNotFoundError,
 )
 from crm_backend.models import (
+    CrmRole,
+    CrmUser,
     InventoryDispatch,
     InventoryDispatchItem,
     InventoryRequest,
@@ -23,12 +26,17 @@ from crm_backend.models import (
     InventoryRequestStatus,
     InventorySourceType,
     StockProduct,
+    SubtaskStatus,
     Task,
     TaskAuditEvent,
+    TaskStatus,
     TaskRequiredMaterial,
     TemplateMaterial,
+    Ticket,
+    TicketAssignmentHistory,
+    TicketAuditEvent,
 )
-from crm_backend.repositories import InventoryFlowRepository, StockProductRepository, TaskRepository
+from crm_backend.repositories import CrmRoleRepository, CrmUserRepository, InventoryFlowRepository, StockProductRepository, TaskRepository, TicketRepository
 from crm_backend.schemas.material_flow import (
     ConfirmDispatchItemRequest,
     CreateInventoryRequestRequest,
@@ -37,6 +45,8 @@ from crm_backend.schemas.material_flow import (
 )
 from crm_backend.schemas.tasks import CreateTaskTemplateRequest, UpdateTaskTemplateRequest
 from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.notification_service import NotificationService
+from crm_backend.models.notification import NotificationEntityType, NotificationType
 
 
 @dataclass(slots=True)
@@ -47,6 +57,9 @@ class DispatchValidationContext:
     barcode_value: str | None
 
 
+_logger = logging.getLogger(__name__)
+
+
 class DispatchValidationStrategy:
     """Validate dispatch item requirements according to product tracking rules."""
 
@@ -95,10 +108,14 @@ class TaskMaterialFlowFacade:
         task_repository: TaskRepository,
         product_repository: StockProductRepository,
         inventory_flow_repository: InventoryFlowRepository,
+        ticket_re
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/notification_service.py`
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
+++ b/microtv-crm-backend/src/crm_backend/services/notification_service.py
@@ -0,0 +1,109 @@
+"""Application service for creating and querying in-app notifications."""
+
+from __future__ import annotations
+
+from crm_backend.models.notification import Notification, NotificationEntityType, NotificationType
+from crm_backend.repositories.crm_user_repository import CrmUserRepository
+from crm_backend.repositories.notification_repository import NotificationRepository
+from crm_backend.core.exceptions import NotificationNotFoundError, NotificationAccessDeniedError
+
+
+class NotificationService:
+    """Create, list, and mark notifications for CRM users."""
+
+    def __init__(
+        self,
+        notification_repository: NotificationRepository,
+        user_repository: CrmUserRepository,
+    ) -> None:
+        self._notification_repository = notification_repository
+        self._user_repository = user_repository
+
+    # ------------------------------------------------------------------
+    # Query
+    # ------------------------------------------------------------------
+
+    def list_for_user(self, crm_user_id: str, limit: int = 20) -> list[Notification]:
+        return self._notification_repository.list_for_user(crm_user_id, limit=limit)
+
+    def count_unread(self, crm_user_id: str) -> int:
+        return self._notification_repository.count_unread_for_user(crm_user_id)
+
+    # ------------------------------------------------------------------
+    # Mark read
+    # ------------------------------------------------------------------
+
+    def mark_read(self, crm_user_id: str, notification_id: str) -> Notification:
+        notification = self._notification_repository.get_by_id(notification_id)
+        if notification is None:
+            raise NotificationNotFoundError()
+        if notification.recipient_crm_user_id != crm_user_id:
+            raise NotificationAccessDeniedError()
+        if notification.is_read:
+            return notification
+        return self._notification_repository.mark_read(notification)
+
+    def mark_all_re
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/reports_service.py`
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
+++ b/microtv-crm-backend/src/crm_backend/services/reports_service.py
@@ -0,0 +1,880 @@
+"""Application service for CRM reporting aggregates."""
+
+from __future__ import annotations
+
+from collections import defaultdict
+from dataclasses import dataclass
+from datetime import UTC, date, datetime, timedelta
+from statistics import mean
+
+from sqlalchemy import Select, and_, func, or_, select
+from sqlalchemy.orm import Session
+
+from crm_backend.models import (
+    Client,
+    CrmRole,
+    CrmUser,
+    CrmUserRole,
+    InventoryDispatch,
+    InventoryRequest,
+    StockLevel,
+    StockCategory,
+    StockProduct,
+    Subtask,
+    Task,
+    TaskAuditEvent,
+    TaskStatus,
+    Ticket,
+    TicketAuditEvent,
+    Warehouse,
+)
+from crm_backend.schemas.reports import (
+    DepositRequestReportResponse,
+    DepositRequestReportRow,
+    DepositRequestReportSummary,
+    ReportKpiItem,
+    ReportOptionItem,
+    ReportSeriesPoint,
+    StockCriticalReportResponse,
+    StockCriticalReportRow,
+    StockCriticalReportSummary,
+    TaskReportResponse,
+    TaskReportRow,
+    TaskReportSummary,
+    TicketReportResponse,
+    TicketReportRow,
+    TicketReportSummary,
+    UserActivityReportResponse,
+    UserActivityReportRow,
+    UserActivityReportSummary,
+)
+from crm_backend.services.auth_service import ResolvedCrmSession
+
+
+@dataclass(slots=True)
+class DateRange:
+    start: datetime | None
+    end: datetime | None
+
+
+class ReportsService:
+    """Builds report payloads for dashboard-like analytics pages."""
+
+    ACTION_TYPE_LABELS = {
+        "ticket.created": "Ticket creado",
+        "ticket.assignment_changed": "Asignación de ticket modificada",
+        "ticket.pending_executive_approval": "Ticket pendiente de aprobación ejecutiva",
+        "ticket.closed": "Ticket cerrado",
+        "ticket.approved_by_executive": "Ticket aprobado por ejecutivo",
+        "ticket.rejected_by_executive": "Ticket rechazado por ejecutivo",
+        "subtask.assigned_manually": "Tarea asignada",
+        "subtask.claimed": "Tarea tomada por téc
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/settings_service.py`
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
+++ b/microtv-crm-backend/src/crm_backend/services/settings_service.py
@@ -0,0 +1,348 @@
+"""Application service for CRM settings module."""
+
+from __future__ import annotations
+
+from datetime import UTC, datetime
+
+from sqlalchemy import inspect, select, text
+from sqlalchemy.orm import Session
+
+from crm_backend.core.exceptions import ApplicationError
+from crm_backend.models import (
+    CrmCategory,
+    CrmPriority,
+    CrmRole,
+    CrmStatus,
+    CrmUser,
+    CrmUserRole,
+    NotificationRule,
+    SlaRule,
+    TaskTemplate,
+)
+from crm_backend.schemas.settings import (
+    SettingsCategoryWriteRequest,
+    SettingsNotificationRuleWriteRequest,
+    SettingsPriorityWriteRequest,
+    SettingsRoleUpdateRequest,
+    SettingsSlaRuleWriteRequest,
+    SettingsStatusWriteRequest,
+    SettingsTaskTemplateUpdateRequest,
+)
+from crm_backend.services.auth_service import ResolvedCrmSession
+
+
+class SettingsService:
+    """Coordinates CRUD operations for configurable CRM settings."""
+
+    def __init__(self, session: Session) -> None:
+        self._session = session
+
+    def list_roles(self, actor: ResolvedCrmSession) -> list[CrmRole]:
+        self._ensure_admin_or_executive(actor)
+        return list(self._session.scalars(select(CrmRole).order_by(CrmRole.role_label.asc(), CrmRole.role_key.asc())).all())
+
+    def update_role(self, actor: ResolvedCrmSession, role_id: str, payload: SettingsRoleUpdateRequest) -> CrmRole:
+        self._ensure_admin(actor)
+        role = self._session.get(CrmRole, role_id)
+        if role is None:
+            raise ApplicationError("settings_role_not_found", "El rol indicado no existe.", 404)
+
+        role.role_label = payload.role_label.strip()
+        role.description = payload.description.strip() if isinstance(payload.description, str) else None
+        role.is_active = payload.is_active
+        self._log_activity("settings.role.updated", actor.crm_user.crm_user_id, {"role_id": role_id, "role_key": role.role_key})
+        self._session.commit()
+        self._session.refresh(role)
+        r
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/action_execution.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/action_execution.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/action_execution.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/application.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/application.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/application.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/strategies.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/strategies.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/strategies.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/validators.cpython-313.pyc`
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

Binary files a/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/validators.cpython-313.pyc and b/microtv-crm-backend/src/crm_backend/services/tasks/__pycache__/validators.cpython-313.pyc differ
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/action_execution.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/tasks/action_execution.py
+++ b/microtv-crm-backend/src/crm_backend/services/tasks/action_execution.py
@@ -45,11 +45,17 @@ class AdvanceTaskFlowService:
         task = context.task
         next_subtask = next((item for item in task.subtasks if item.order_index == current.order_index + 1), None)
         if next_subtask is None:
-            task.status = TaskStatus.COMPLETED.value
-            task.current_assigned_crm_user_id = None
-            task.is_finalized = True
-            task.finalized_at = datetime.now(UTC)
-            task.finalized_by_crm_user_id = context.actor.crm_user.crm_user_id
+            executive_candidates = self._user_repository.list_active_by_role_key("ejecutivo")
+            if not executive_candidates:
+                executive_candidates = self._user_repository.list_active_by_role_key("admin")
+            if not executive_candidates:
+                raise TaskValidationError("No hay usuarios ejecutivos activos para aprobar el cierre final de la tarea.")
+
+            task.status = TaskStatus.BLOCKED.value
+            task.current_assigned_crm_user_id = executive_candidates[0].crm_user_id
+            task.is_finalized = False
+            task.finalized_at = None
+            task.finalized_by_crm_user_id = None
             return
 
         strategy = self._assignment_registry.get(next_subtask.next_assignment_policy)
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/application.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/tasks/application.py
+++ b/microtv-crm-backend/src/crm_backend/services/tasks/application.py
@@ -2,6 +2,7 @@
 
 from __future__ import annotations
 
+import logging
 from datetime import UTC, datetime
 from uuid import uuid4
 
@@ -31,14 +32,18 @@ from crm_backend.models import (
 )
 from crm_backend.repositories import CrmUserRepository, TaskRepository, TaskTemplateRepository
 from crm_backend.schemas.tasks import (
+    ApproveTaskRequest,
     CreateTaskFromTemplateRequest,
     CreateTaskTemplateRequest,
     ExecuteSubtaskActionRequest,
+    RejectTaskApprovalRequest,
     SetTaskTemplateActivationRequest,
     UpdateTaskTemplateRequest,
     UpdateSubtaskProgressRequest,
 )
 from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.notification_service import NotificationService
+from crm_backend.models.notification import NotificationEntityType, NotificationType
 from crm_backend.services.tasks.action_execution import (
     ActionExecutionContext,
     AdvanceTaskFlowService,
@@ -51,6 +56,7 @@ from crm_backend.services.tasks.strategies import NextAssignmentStrategyRegistry
 from crm_backend.services.tasks.validators import (
     ActorPermissionValidator,
     NextAssignmentValidator,
+    PendingInventoryRequestsResolvedValidator,
     RequiredCommentValidator,
     RequiredItemsCompletedValidator,
     StateActionValidator,
@@ -115,6 +121,9 @@ class TaskBuilder:
         return task
 
 
+_logger = logging.getLogger(__name__)
+
+
 class TaskApplicationService:
     """Orchestrate the task template and execution flows."""
 
@@ -125,12 +134,14 @@ class TaskApplicationService:
         user_repository: CrmUserRepository,
         task_media_storage: TaskMediaStorageFacade,
         task_material_flow: TaskMaterialFlowFacade,
+        notification_service: NotificationService | None = None,
     ) -> None:
         self._template_repository = template_repository
         self._task_repository = task_repository
         self._user_repository = user_repository
         self._task_media_storage = task_medi
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/strategies.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/tasks/strategies.py
+++ b/microtv-crm-backend/src/crm_backend/services/tasks/strategies.py
@@ -40,9 +40,10 @@ class SubtaskItemValueStrategy:
 
 class CheckboxItemValueStrategy(SubtaskItemValueStrategy):
     def apply(self, item: SubtaskItemValue, payload: dict[str, object], actor_crm_user_id: str) -> None:
-        if payload.get("checkbox_value") is None:
-            raise TaskValidationError(f"El item '{item.item_label}' requiere un valor checkbox.")
-        checkbox_value = bool(payload["checkbox_value"])
+        if "checkbox_value" not in payload:
+            return
+
+        checkbox_value = bool(payload.get("checkbox_value"))
         item.checkbox_value = checkbox_value
         item.completed_at = datetime.now(UTC) if checkbox_value else None
         item.last_updated_by_crm_user_id = actor_crm_user_id
@@ -53,9 +54,12 @@ class CheckboxItemValueStrategy(SubtaskItemValueStrategy):
 
 class TextItemValueStrategy(SubtaskItemValueStrategy):
     def apply(self, item: SubtaskItemValue, payload: dict[str, object], actor_crm_user_id: str) -> None:
-        if payload.get("text_value") is None:
-            raise TaskValidationError(f"El item '{item.item_label}' requiere un valor textual.")
-        text_value = str(payload["text_value"]).strip()
+        if "text_value" not in payload:
+            return
+
+        # Saving progress must allow empty text values; strict completion is validated on close action.
+        raw_value = payload.get("text_value")
+        text_value = str(raw_value).strip() if raw_value is not None else ""
         item.text_value = text_value or None
         item.completed_at = datetime.now(UTC) if text_value else None
         item.last_updated_by_crm_user_id = actor_crm_user_id
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/tasks/validators.py`
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

--- a/microtv-crm-backend/src/crm_backend/services/tasks/validators.py
+++ b/microtv-crm-backend/src/crm_backend/services/tasks/validators.py
@@ -5,6 +5,7 @@ from __future__ import annotations
 from dataclasses import dataclass
 
 from crm_backend.core.exceptions import TaskAccessDeniedError, TaskConflictError, TaskValidationError
+from crm_backend.models import InventoryRequestStatus
 from crm_backend.models.task_execution import Subtask, Task
 from crm_backend.repositories import CrmUserRepository
 from crm_backend.services.auth_service import ResolvedCrmSession
@@ -77,6 +78,24 @@ class RequiredItemsCompletedValidator(ValidationHandler):
                 )
 
 
+class PendingInventoryRequestsResolvedValidator(ValidationHandler):
+    def _validate(self, context: ActionValidationContext) -> None:
+        blocking_statuses = {
+            InventoryRequestStatus.PENDING.value,
+            InventoryRequestStatus.PENDING_DISPATCH.value,
+            InventoryRequestStatus.PENDING_RECEIPT.value,
+            InventoryRequestStatus.APPROVED.value,
+        }
+        actor_id = context.actor.crm_user.crm_user_id
+        for request in context.task.inventory_requests:
+            if request.requested_by_crm_user_id != actor_id:
+                continue
+            if request.request_status in blocking_statuses:
+                raise TaskValidationError(
+                    "No se puede cerrar la subtarea porque tenés una solicitud de materiales pendiente de aprobar, despachar o confirmar recibimiento."
+                )
+
+
 class NextAssignmentValidator(ValidationHandler):
     def __init__(
         self,
```

#### 📄 `microtv-crm-backend/src/crm_backend/services/ticket_service.py`
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
+++ b/microtv-crm-backend/src/crm_backend/services/ticket_service.py
@@ -0,0 +1,997 @@
+"""Application services for the ticket module."""
+
+from __future__ import annotations
+
+import re
+import logging
+from datetime import UTC, datetime
+from uuid import uuid4
+
+from fastapi import UploadFile
+from sqlalchemy import text
+
+from crm_backend.core.exceptions import (
+    InvalidTaskAttachmentError,
+    TaskAttachmentNotFoundError,
+    TicketAccessDeniedError,
+    TicketConflictError,
+    TicketNotFoundError,
+    TicketValidationError,
+)
+from crm_backend.infrastructure.task_media_storage import StoredTaskMedia, TaskMediaStorageFacade
+from crm_backend.models import (
+    CrmRole,
+    CrmUser,
+    Ticket,
+    TicketAssignmentHistory,
+    TicketAttachment,
+    TicketAuditEvent,
+    TicketComment,
+    TicketCommentType,
+    TicketPriority,
+    TicketStatus,
+    TicketStatusTransition,
+    TicketTransitionAction,
+)
+from crm_backend.repositories import (
+    ClientRepository,
+    CrmRoleRepository,
+    CrmUserRepository,
+    LocationRepository,
+    TicketRepository,
+)
+from crm_backend.schemas.tickets import CreateTicketRequest
+from crm_backend.services.auth_service import ResolvedCrmSession
+from crm_backend.services.notification_service import NotificationService
+from crm_backend.models.notification import NotificationEntityType, NotificationType
+
+
+_logger = logging.getLogger(__name__)
+
+
+class TicketApplicationService:
+    """Orchestrate ticket lifecycle, comments, assignment, and attachments."""
+
+    ROLE_KEY_ALIASES = {
+        "admin": "admin_crm",
+        "deposito": "encargado_deposito",
+        "tecnico": "tecnico_campo",
+    }
+
+    OPERATIONAL_ROLE_KEYS = {"admin", "ejecutivo", "tecnico", "deposito"}
+
+    ALLOWED_STATUS_TRANSITIONS = {
+        TicketStatus.OPEN.value: {TicketStatus.IN_PROGRESS.value, TicketStatus.ON_HOLD.value, TicketStatus.RESOLVED.value},
+        TicketStatus.IN_PROGRESS.value: {TicketStatus.OPEN.value, TicketStatus.ON_HOLD.value, TicketStatus.RESOLVED.value},
+        TicketStatus.O
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/src/microtv_crm_backend.egg-info/SOURCES.txt`
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

--- a/microtv-crm-backend/src/microtv_crm_backend.egg-info/SOURCES.txt
+++ b/microtv-crm-backend/src/microtv_crm_backend.egg-info/SOURCES.txt
@@ -12,11 +12,16 @@ src/crm_backend/api/endpoints/__init__.py
 src/crm_backend/api/endpoints/auth.py
 src/crm_backend/api/endpoints/clients.py
 src/crm_backend/api/endpoints/crm_users.py
+src/crm_backend/api/endpoints/dashboard.py
 src/crm_backend/api/endpoints/health.py
 src/crm_backend/api/endpoints/inventory_flow.py
 src/crm_backend/api/endpoints/locations.py
+src/crm_backend/api/endpoints/notifications.py
+src/crm_backend/api/endpoints/reports.py
+src/crm_backend/api/endpoints/settings.py
 src/crm_backend/api/endpoints/stock.py
 src/crm_backend/api/endpoints/tasks.py
+src/crm_backend/api/endpoints/tickets.py
 src/crm_backend/core/__init__.py
 src/crm_backend/core/config.py
 src/crm_backend/core/exceptions.py
@@ -31,6 +36,8 @@ src/crm_backend/models/crm_role.py
 src/crm_backend/models/crm_user.py
 src/crm_backend/models/crm_user_role.py
 src/crm_backend/models/material_flow.py
+src/crm_backend/models/notification.py
+src/crm_backend/models/settings.py
 src/crm_backend/models/stock_category.py
 src/crm_backend/models/stock_level.py
 src/crm_backend/models/stock_movement.py
@@ -38,6 +45,7 @@ src/crm_backend/models/stock_product.py
 src/crm_backend/models/task_execution.py
 src/crm_backend/models/task_reference.py
 src/crm_backend/models/task_template.py
+src/crm_backend/models/ticket.py
 src/crm_backend/models/warehouse.py
 src/crm_backend/repositories/__init__.py
 src/crm_backend/repositories/client_repository.py
@@ -45,26 +53,38 @@ src/crm_backend/repositories/crm_role_repository.py
 src/crm_backend/repositories/crm_user_repository.py
 src/crm_backend/repositories/inventory_flow_repository.py
 src/crm_backend/repositories/location_repository.py
+src/crm_backend/repositories/notification_repository.py
 src/crm_backend/repositories/stock_category_repository.py
 src/crm_backend/repositories/stock_product_repository.py
 src/crm_backend/repositories/task_repository.py
 src/crm_backend/repositories/task_template_repository.py
+src/crm_backend/repositorie
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/tests/__pycache__/test_tasks_api.cpython-313-pytest-8.4.2.pyc`
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

Binary files a/microtv-crm-backend/tests/__pycache__/test_tasks_api.cpython-313-pytest-8.4.2.pyc and b/microtv-crm-backend/tests/__pycache__/test_tasks_api.cpython-313-pytest-8.4.2.pyc differ
```

#### 📄 `microtv-crm-backend/tests/__pycache__/test_tickets_api.cpython-313-pytest-8.4.2.pyc`
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
Binary files /dev/null and b/microtv-crm-backend/tests/__pycache__/test_tickets_api.cpython-313-pytest-8.4.2.pyc differ
```

#### 📄 `microtv-crm-backend/tests/test_microtv_crm.db`
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

Binary files a/microtv-crm-backend/tests/test_microtv_crm.db and b/microtv-crm-backend/tests/test_microtv_crm.db differ
```

#### 📄 `microtv-crm-backend/tests/test_tasks_api.py`
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

--- a/microtv-crm-backend/tests/test_tasks_api.py
+++ b/microtv-crm-backend/tests/test_tasks_api.py
@@ -8,7 +8,7 @@ from sqlalchemy import select
 
 from crm_backend.adapters.auth_service_adapter import ActiveMembershipContext, AuthenticatedAuthResult
 from crm_backend.api.dependencies import get_auth_service_adapter
-from crm_backend.models import Client, CrmRole, CrmUser, CrmUserRole, Location, Task, TaskAttachment
+from crm_backend.models import Client, CrmRole, CrmUser, CrmUserRole, Location, StockProduct, Task, TaskAttachment
 
 
 class FakeTaskAuthAdapter:
@@ -310,6 +310,121 @@ def test_close_advances_flow_and_exposes_unassigned_next_subtask(client, db_sess
     assert any(item["subtask_id"] == next_subtask["subtask_id"] for item in unassigned_response.json())
 
 
+def test_cannot_close_subtask_until_request_is_approved_dispatched_and_received(client, db_session) -> None:
+    """Requester cannot close the active subtask while material flow is pending approval, dispatch, or receipt."""
+
+    tech_user = _seed_local_role_user(
+        db_session,
+        role_key="tecnico_campo",
+        auth_user_id="auth-tech",
+        email="tecnico.crm@yccbrothers.com",
+        display_name="Tecnico Campo",
+    )
+    _seed_local_role_user(
+        db_session,
+        role_key="encargado_deposito",
+        auth_user_id="auth-deposito",
+        email="deposito.crm@yccbrothers.com",
+        display_name="Encargado Deposito",
+    )
+    seeded_client = _seed_client(db_session)
+    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()
+
+    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
+    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
+    first_subtask = task["subtasks"][0]
+    checklist_items = first_subtask["items"]
+
+    progress_response = client.put(
+        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
+        headers=_auth_header("tech-token"),
+        json={
+            "items": [
+               
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-backend/tests/test_tickets_api.py`
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
+++ b/microtv-crm-backend/tests/test_tickets_api.py
@@ -0,0 +1,684 @@
+"""Ticket module API tests."""
+
+from __future__ import annotations
+
+from io import BytesIO
+
+from sqlalchemy import select
+
+from crm_backend.adapters.auth_service_adapter import ActiveMembershipContext, AuthenticatedAuthResult
+from crm_backend.api.dependencies import get_auth_service_adapter
+from crm_backend.models import Client, CrmRole, CrmUser, CrmUserRole, Location, StockProduct, TicketAttachment
+
+
+class FakeTicketAuthAdapter:
+    """Fake auth adapter returning deterministic CRM sessions per bearer token."""
+
+    USER_FIXTURES = {
+        "admin-token": {
+            "auth_user_id": "auth-admin",
+            "email": "admin.crm@microtv.com",
+            "display_name": "Admin CRM",
+            "roles": ["platform_admin"],
+            "tenant_id": "MICROTV",
+        },
+        "ejecutivo-token": {
+            "auth_user_id": "auth-ejecutivo",
+            "email": "ejecutivo.crm@yccbrothers.com",
+            "display_name": "Ejecutivo CRM",
+            "roles": ["ejecutivo"],
+            "tenant_id": "YCC",
+        },
+        "tech-token": {
+            "auth_user_id": "auth-tech",
+            "email": "tecnico.crm@yccbrothers.com",
+            "display_name": "Tecnico Campo",
+            "roles": [],
+            "tenant_id": "YCC",
+        },
+        "tech-2-token": {
+            "auth_user_id": "auth-tech-2",
+            "email": "tecnico2.crm@yccbrothers.com",
+            "display_name": "Tecnico Campo 2",
+            "roles": [],
+            "tenant_id": "YCC",
+        },
+        "deposito-token": {
+            "auth_user_id": "auth-deposito",
+            "email": "deposito.crm@yccbrothers.com",
+            "display_name": "Encargado Deposito",
+            "roles": [],
+            "tenant_id": "YCC",
+        },
+    }
+
+    def validate_access_token(self, access_token: str) -> AuthenticatedAuthResult:
+        fixture = self.USER_FIXTURES[access_token]
+        return AuthenticatedAuthResult(
+            access_token=access_token
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/.gitignore`
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

--- a/microtv-crm-frontend/.gitignore
+++ b/microtv-crm-frontend/.gitignore
@@ -44,3 +44,10 @@ public/runtime-config.js
 # System files
 .DS_Store
 Thumbs.db
+
+
+# Images
+
+microtv-crm-backend\public\images\*.png
+microtv-crm-backend\public\images\*.jpg
+microtv-crm-backend\public\images\*.mp4
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/README.md`
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

--- a/microtv-crm-frontend/README.md
+++ b/microtv-crm-frontend/README.md
@@ -57,3 +57,19 @@ Angular CLI does not come with an end-to-end testing framework by default. You c
 ## Additional Resources
 
 For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
+
+## PWA (Instalable)
+
+El frontend incluye configuración PWA básica para instalación en Android/desktop (manifest + service worker).
+
+- El service worker cachea solo recursos estáticos de la app (JS/CSS/iconos/assets).
+- No se configuró cache de endpoints API ni datos autenticados.
+- Los iconos actuales son placeholders internos y deben reemplazarse por arte final de CRM/MicroTV.
+
+### Fallback SPA en Nginx
+
+Para que el refresh o apertura directa de rutas internas (`/dashboard`, `/tickets`, `/tasks`, `/reports`, `/settings`) funcione correctamente en producción, el servidor debe tener fallback a `index.html`:
+
+```nginx
+try_files $uri $uri/ /index.html;
+```
```

- *microtv-crm-frontend/angular.json (Omitido por extensión)*
- *microtv-crm-frontend/ngsw-config.json (Omitido por extensión)*
- *microtv-crm-frontend/package-lock.json (Omitido por extensión)*
- *microtv-crm-frontend/package.json (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-128x128.png (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-144x144.png (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-152x152.png (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-192x192.png (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-384x384.png (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-512x512.png (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-72x72.png (Omitido por extensión)*
- *microtv-crm-frontend/public/icons/icon-96x96.png (Omitido por extensión)*
#### 📄 `microtv-crm-frontend/public/manifest.webmanifest`
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
+++ b/microtv-crm-frontend/public/manifest.webmanifest
@@ -0,0 +1,53 @@
+{
+  "name": "CRM MicroTV",
+  "short_name": "CRM",
+  "description": "CRM operativo interno de MicroTV/YCC",
+  "start_url": "/",
+  "scope": "/",
+  "display": "standalone",
+  "orientation": "portrait",
+  "theme_color": "#ffffff",
+  "background_color": "#ffffff",
+  "icons": [
+    {
+      "src": "icons/icon-72x72.png",
+      "sizes": "72x72",
+      "type": "image/png"
+    },
+    {
+      "src": "icons/icon-96x96.png",
+      "sizes": "96x96",
+      "type": "image/png"
+    },
+    {
+      "src": "icons/icon-128x128.png",
+      "sizes": "128x128",
+      "type": "image/png"
+    },
+    {
+      "src": "icons/icon-144x144.png",
+      "sizes": "144x144",
+      "type": "image/png"
+    },
+    {
+      "src": "icons/icon-152x152.png",
+      "sizes": "152x152",
+      "type": "image/png"
+    },
+    {
+      "src": "icons/icon-192x192.png",
+      "sizes": "192x192",
+      "type": "image/png"
+    },
+    {
+      "src": "icons/icon-384x384.png",
+      "sizes": "384x384",
+      "type": "image/png"
+    },
+    {
+      "src": "icons/icon-512x512.png",
+      "sizes": "512x512",
+      "type": "image/png"
+    }
+  ]
+}
```

#### 📄 `microtv-crm-frontend/src/app/app.config.ts`
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

--- a/microtv-crm-frontend/src/app/app.config.ts
+++ b/microtv-crm-frontend/src/app/app.config.ts
@@ -1,8 +1,9 @@
-import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
+import { ApplicationConfig, isDevMode, provideBrowserGlobalErrorListeners } from '@angular/core';
 import { provideHttpClient } from '@angular/common/http';
 import { provideClientHydration, withEventReplay } from '@angular/platform-browser';
 import { provideRouter, withInMemoryScrolling } from '@angular/router';
 import { provideAnimations } from '@angular/platform-browser/animations';
+import { provideServiceWorker } from '@angular/service-worker';
 
 import { routes } from './app.routes';
 
@@ -18,6 +19,10 @@ export const appConfig: ApplicationConfig = {
         anchorScrolling: 'enabled'
       })
     ),
-    provideClientHydration(withEventReplay())
+    provideClientHydration(withEventReplay()),
+    provideServiceWorker('ngsw-worker.js', {
+      enabled: !isDevMode(),
+      registrationStrategy: 'registerWhenStable:30000'
+    })
   ]
 };
```

#### 📄 `microtv-crm-frontend/src/app/app.routes.server.ts`
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

--- a/microtv-crm-frontend/src/app/app.routes.server.ts
+++ b/microtv-crm-frontend/src/app/app.routes.server.ts
@@ -17,6 +17,14 @@ export const serverRoutes: ServerRoute[] = [
     path: 'tasks/:taskId',
     renderMode: RenderMode.Server
   },
+  {
+    path: 'reports/:category',
+    renderMode: RenderMode.Server
+  },
+  {
+    path: 'reports/:category/:reportId',
+    renderMode: RenderMode.Server
+  },
   {
     path: '**',
     renderMode: RenderMode.Prerender
```

#### 📄 `microtv-crm-frontend/src/app/app.routes.ts`
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

--- a/microtv-crm-frontend/src/app/app.routes.ts
+++ b/microtv-crm-frontend/src/app/app.routes.ts
@@ -1,13 +1,11 @@
 import { Routes } from '@angular/router';
 
-import { guestOnlyGuard, authGuard } from './core/guards/auth.guard';
+import { guestOnlyGuard, authGuard, adminOnlyGuard, adminOrExecutiveGuard } from './core/guards/auth.guard';
 import { DashboardPageComponent } from './features/dashboard/components/dashboard-page/dashboard-page.component';
 import { LoginPageComponent } from './features/auth/components/login-page/login-page.component';
 import { ClientsPageComponent } from './features/clients/components/clients-page/clients-page.component';
 import { InventoryPageComponent } from './features/inventory/components/inventory-page/inventory-page.component';
 import { InventoryRequestsPageComponent } from './features/inventory/components/inventory-requests-page/inventory-requests-page.component';
-import { TicketExecutionPageComponent } from './features/tickets/components/ticket-execution-page/ticket-execution-page.component';
-import { TicketsPageComponent } from './features/tickets/components/tickets-page/tickets-page.component';
 import { AppShellComponent } from './layout/components/app-shell/app-shell.component';
 
 export const routes: Routes = [
@@ -45,12 +43,15 @@ export const routes: Routes = [
 			},
 			{
 				path: 'tickets',
-				component: TicketsPageComponent,
+				loadComponent: () => import('./features/tickets/components/tickets-page/tickets-page.component').then((module) => module.TicketsPageComponent),
 				data: { title: 'Tickets' }
 			},
 			{
 				path: 'tickets/:ticketId',
-				component: TicketExecutionPageComponent,
+				loadComponent: () =>
+					import('./features/tickets/components/ticket-execution-page/ticket-execution-page.component').then(
+						(module) => module.TicketExecutionPageComponent
+					),
 				data: { title: 'Ejecución de ticket' }
 			},
 			{
@@ -58,30 +59,57 @@ export const routes: Routes = [
 				loadComponent: () => import('./features/tasks/components/tasks-page/tasks-page.component').then((module) => module.TasksPageComponent),
 		
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/app.ts`
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

--- a/microtv-crm-frontend/src/app/app.ts
+++ b/microtv-crm-frontend/src/app/app.ts
@@ -1,6 +1,7 @@
 import { Component, inject } from '@angular/core';
 import { RouterOutlet } from '@angular/router';
 
+import { AppUpdateService } from './core/services/app-update.service';
 import { AuthSessionService } from './core/services/auth-session.service';
 
 @Component({
@@ -12,8 +13,10 @@ import { AuthSessionService } from './core/services/auth-session.service';
 })
 export class App {
   private readonly authSessionService = inject(AuthSessionService);
+  private readonly appUpdateService = inject(AppUpdateService);
 
   constructor() {
     this.authSessionService.bootstrap();
+    this.appUpdateService.start();
   }
 }
```

#### 📄 `microtv-crm-frontend/src/app/core/guards/auth.guard.ts`
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

--- a/microtv-crm-frontend/src/app/core/guards/auth.guard.ts
+++ b/microtv-crm-frontend/src/app/core/guards/auth.guard.ts
@@ -25,4 +25,28 @@ export const guestOnlyGuard: CanActivateFn = () => {
   }
 
   return true;
+};
+
+export const adminOnlyGuard: CanActivateFn = () => {
+  const authSessionService = inject(AuthSessionService);
+  const router = inject(Router);
+
+  const session = authSessionService.sessionSnapshot();
+  if (session?.user.role_keys.includes('admin')) {
+    return true;
+  }
+
+  return router.createUrlTree(['/tasks']);
+};
+
+export const adminOrExecutiveGuard: CanActivateFn = () => {
+  const authSessionService = inject(AuthSessionService);
+  const router = inject(Router);
+
+  const roles = authSessionService.sessionSnapshot()?.user.role_keys ?? [];
+  if (roles.includes('admin') || roles.includes('ejecutivo')) {
+    return true;
+  }
+
+  return router.createUrlTree(['/tasks']);
 };
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/src/app/core/models/dashboard.model.ts`
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

--- a/microtv-crm-frontend/src/app/core/models/dashboard.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/dashboard.model.ts
@@ -15,6 +15,7 @@ export interface DashboardStat {
 
 export interface RecentTicket {
   id: string;
+  ticketId?: string;
   subject: string;
   client: string;
   priority: string;
@@ -23,6 +24,7 @@ export interface RecentTicket {
   statusTone: TicketStatusTone;
   assignedTo: string;
   assignedInitials: string;
+  targetRoute?: string;
 }
 
 export interface RecentTicketsColumn {
@@ -42,6 +44,7 @@ export interface RecentActivityItem {
   text: string;
   timestamp: string;
   actor: string;
+  targetRoute?: string;
 }
 
 export interface RecentActivityBlock {
@@ -55,4 +58,43 @@ export interface DashboardData {
   stats: DashboardStat[];
   recentTickets: RecentTicketsBlock;
   recentActivity: RecentActivityBlock;
+}
+
+export interface DashboardKpiApiResponse {
+  key: string;
+  label: string;
+  value: number;
+  secondary: string;
+  variant: DashboardStatVariant;
+}
+
+export interface DashboardRecentTicketApiResponse {
+  ticket_id: string;
+  ticket_public_id: string;
+  subject: string;
+  client: string;
+  priority: string;
+  priority_tone: TicketPriorityTone;
+  status: string;
+  status_tone: TicketStatusTone;
+  assigned_to: string;
+  assigned_initials: string;
+  target_route: string;
+}
+
+export interface DashboardRecentActivityApiResponse {
+  type: string;
+  tone: ActivityTone;
+  text: string;
+  timestamp: string;
+  actor: string;
+  target_route: string | null;
+}
+
+export interface DashboardSummaryApiResponse {
+  page_title: string;
+  page_subtitle: string;
+  kpis: DashboardKpiApiResponse[];
+  recent_tickets: DashboardRecentTicketApiResponse[];
+  recent_activity: DashboardRecentActivityApiResponse[];
 }
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/src/app/core/models/inventory-flow.model.ts`
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

--- a/microtv-crm-frontend/src/app/core/models/inventory-flow.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/inventory-flow.model.ts
@@ -1,5 +1,5 @@
 export type InventorySourceType = 'TASK' | 'TICKET';
-export type InventoryRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
+export type InventoryRequestStatus = 'PENDING' | 'PENDING_DISPATCH' | 'PENDING_RECEIPT' | 'APPROVED' | 'COMPLETED' | 'REJECTED' | 'CANCELLED';
 export type DispatchConfirmationType = 'received' | 'delivered' | 'installed';
 
 export interface RequiredMaterialWriteRequest {
@@ -53,6 +53,7 @@ export interface CreateTaskDispatchRequest {
 
 export interface ConfirmDispatchItemRequest {
   confirmation_type: DispatchConfirmationType;
+  reception_comment?: string | null;
 }
 
 export interface InventoryRequestItem {
@@ -93,6 +94,10 @@ export interface InventoryDispatch {
   request_id: string | null;
   dispatched_by_crm_user_id: string;
   dispatched_by_display_name: string | null;
+  received_by_crm_user_id: string | null;
+  received_by_display_name: string | null;
+  received_at: string | null;
+  reception_comment: string | null;
   warehouse_id: string;
   dispatch_notes: string | null;
   created_at: string;
@@ -129,8 +134,14 @@ export function formatInventoryRequestStatus(status: InventoryRequestStatus): st
   switch (status) {
     case 'PENDING':
       return 'Pendiente';
+    case 'PENDING_DISPATCH':
+      return 'Pendiente de despacho';
+    case 'PENDING_RECEIPT':
+      return 'Pendiente de recibimiento';
     case 'APPROVED':
       return 'Aprobada';
+    case 'COMPLETED':
+      return 'Completada';
     case 'REJECTED':
       return 'Rechazada';
     case 'CANCELLED':
```

#### 📄 `microtv-crm-frontend/src/app/core/models/location.model.ts`
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

--- a/microtv-crm-frontend/src/app/core/models/location.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/location.model.ts
@@ -4,6 +4,10 @@ export interface AppLocation {
   addressLabel?: string;
 }
 
+export interface LocationMapMarker extends AppLocation {
+  title?: string;
+}
+
 export interface LocationPickerDialogData {
   title?: string;
   initialLocation?: AppLocation | null;
```

#### 📄 `microtv-crm-frontend/src/app/core/models/notification.model.ts`
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
+++ b/microtv-crm-frontend/src/app/core/models/notification.model.ts
@@ -0,0 +1,22 @@
+export interface Notification {
+  notification_id: string;
+  recipient_crm_user_id: string;
+  notification_type: string;
+  title: string;
+  body: string;
+  entity_type: 'ticket' | 'task' | 'deposit_request' | null;
+  entity_id: string | null;
+  is_read: boolean;
+  created_at: string;
+  read_at: string | null;
+  metadata_json: Record<string, unknown> | null;
+}
+
+export interface NotificationListResponse {
+  notifications: Notification[];
+  unread_count: number;
+}
+
+export interface UnreadCountResponse {
+  unread_count: number;
+}
```

#### 📄 `microtv-crm-frontend/src/app/core/models/settings-management.model.ts`
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
+++ b/microtv-crm-frontend/src/app/core/models/settings-management.model.ts
@@ -0,0 +1,125 @@
+export interface SettingsRole {
+  crm_role_id: string;
+  role_key: string;
+  role_label: string;
+  description: string | null;
+  is_active: boolean;
+}
+
+export interface SettingsRoleUpdateRequest {
+  role_label: string;
+  description?: string | null;
+  is_active: boolean;
+}
+
+export interface SettingsUserRoleAssignment {
+  crm_user_id: string;
+  display_name: string | null;
+  email: string | null;
+  role_keys: string[];
+}
+
+export interface SettingsUserRoleAssignmentRequest {
+  role_keys: string[];
+}
+
+export interface SettingsCategory {
+  category_id: string;
+  name: string;
+  category_type: string;
+  description: string | null;
+  is_active: boolean;
+  created_at: string;
+}
+
+export interface SettingsCategoryWriteRequest {
+  name: string;
+  category_type: string;
+  description?: string | null;
+  is_active: boolean;
+}
+
+export interface SettingsPriority {
+  priority_id: string;
+  code: string;
+  name: string;
+  order_index: number;
+  color: string | null;
+  is_active: boolean;
+}
+
+export interface SettingsPriorityWriteRequest {
+  code: string;
+  name: string;
+  order_index: number;
+  color?: string | null;
+  is_active: boolean;
+}
+
+export interface SettingsStatus {
+  status_id: string;
+  code: string;
+  name: string;
+  entity_type: string;
+  is_final: boolean;
+  order_index: number;
+  is_active: boolean;
+}
+
+export interface SettingsStatusWriteRequest {
+  code: string;
+  name: string;
+  entity_type: string;
+  is_final: boolean;
+  order_index: number;
+  is_active: boolean;
+}
+
+export interface SettingsTaskTemplate {
+  template_id: string;
+  template_name: string;
+  description: string | null;
+  is_active: boolean;
+  created_at: string;
+  updated_at: string | null;
+}
+
+export interface SettingsTaskTemplateUpdateRequest {
+  template_name: string;
+  description?: string | null;
+  is_active: boolean;
+}
+
+export interface SettingsSlaRule {
+  sla_rule_id: string;
+  entity_type: string;
+  
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/models/task-management.model.ts`
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

--- a/microtv-crm-frontend/src/app/core/models/task-management.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/task-management.model.ts
@@ -6,7 +6,7 @@ import { TaskAttachment } from './task-attachment.model';
 export type TaskAssignmentPolicy = 'role_queue_auto' | 'default_user_auto' | 'manual_required';
 export type TaskItemType = 'checkbox' | 'text';
 export type TaskAction = 'close_subtask' | 'reject_subtask' | 'put_on_hold';
-export type TaskStatus = 'PENDING' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED';
+export type TaskStatus = 'PENDING' | 'IN_PROGRESS' | 'BLOCKED' | 'PENDING_APPROVAL' | 'COMPLETED';
 export type SubtaskStatus = 'locked' | 'pending_assignment' | 'assigned' | 'in_progress' | 'completed' | 'rejected' | 'on_hold';
 export type TaskCommentType = 'general' | 'transition' | 'progress';
 
@@ -100,6 +100,19 @@ export interface ExecuteSubtaskActionRequest {
   attachment_ids?: string[];
 }
 
+export interface AssignSubtaskRequest {
+  assigned_crm_user_id: string;
+  notes?: string | null;
+}
+
+export interface ApproveTaskRequest {
+  comment?: string | null;
+}
+
+export interface RejectTaskApprovalRequest {
+  comment: string;
+}
+
 export interface TaskTemplateItem {
   task_template_item_id: string;
   item_label: string;
@@ -293,6 +306,8 @@ export function formatTaskStatus(status: string): string {
       return 'En progreso';
     case 'BLOCKED':
       return 'Bloqueada';
+    case 'PENDING_APPROVAL':
+      return 'Pendiente aprobación ejecutiva';
     case 'COMPLETED':
       return 'Completada';
     case 'locked':
@@ -335,6 +350,8 @@ export function formatAssignmentPolicy(policy: TaskAssignmentPolicy): string {
 
 export function toTaskTone(status: string): TicketStatusTone {
   switch (status) {
+    case 'PENDING_APPROVAL':
+      return 'warning';
     case 'COMPLETED':
     case 'completed':
       return 'success';
```

#### 📄 `microtv-crm-frontend/src/app/core/models/task.model.ts`
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

--- a/microtv-crm-frontend/src/app/core/models/task.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/task.model.ts
@@ -18,6 +18,10 @@ export interface TaskListItem {
   assignedToUserId: number | string | null;
   assignedTo: string;
   assignedInitials: string;
+  routeTaskId?: string;
+  rowActionLabel?: string;
+  rowActionId?: string;
+  rowActionDisabled?: boolean;
 }
 
 export interface TasksTableColumn {
```

#### 📄 `microtv-crm-frontend/src/app/core/models/ticket-inventory-request.model.ts`
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

--- a/microtv-crm-frontend/src/app/core/models/ticket-inventory-request.model.ts
+++ b/microtv-crm-frontend/src/app/core/models/ticket-inventory-request.model.ts
@@ -6,7 +6,13 @@ export interface TicketInventoryRequestItem {
   requiresTracking?: boolean;
 }
 
-export type TicketInventoryRequestStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';
+export type TicketInventoryRequestStatus =
+  | 'pending_deposit_review'
+  | 'approved_for_dispatch'
+  | 'pending_receipt'
+  | 'dispatched'
+  | 'rejected'
+  | 'cancelled';
 
 export interface TicketInventoryRequest {
   id: string;
```

#### 📄 `microtv-crm-frontend/src/app/core/models/ticket-management.model.ts`
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
+++ b/microtv-crm-frontend/src/app/core/models/ticket-management.model.ts
@@ -0,0 +1,341 @@
+import { TicketPriorityTone, TicketStatusTone } from './dashboard.model';
+import { InventoryDispatch, InventoryRequest } from './inventory-flow.model';
+import { AppLocation } from './location.model';
+
+export type TicketStatus = 'OPEN' | 'IN_PROGRESS' | 'ON_HOLD' | 'RESOLVED' | 'PENDING_APPROVAL' | 'CLOSED';
+export type TicketPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
+
+export interface TicketRoleOption {
+  crm_role_id: string;
+  role_key: string;
+  role_label: string;
+}
+
+export interface TicketClientLocation {
+  location_id: string;
+  latitude: number;
+  longitude: number;
+  address_label: string | null;
+  formatted_address: string | null;
+}
+
+export interface TicketClientOption {
+  client_id: string;
+  business_name: string;
+  tax_id: string;
+  email: string | null;
+  phone: string | null;
+  is_active: boolean;
+  created_at: string;
+  location: TicketClientLocation | null;
+}
+
+export interface TicketAttachment {
+  id: string;
+  fileName: string;
+  fileType: string;
+  kind: 'image' | 'video' | 'other';
+  context?: string | null;
+  publicUrl?: string | null;
+  storagePath?: string | null;
+  previewUrl?: string | null;
+  size?: number | null;
+}
+
+export interface TicketComment {
+  ticket_comment_id: string;
+  author_crm_user_id: string;
+  author_display_name: string | null;
+  comment_type: 'general' | 'system' | 'closure' | string;
+  body: string;
+  created_at: string;
+  location: TicketLocation | null;
+  attachments: TicketAttachment[];
+}
+
+export interface TicketStatusTransition {
+  ticket_status_transition_id: string;
+  from_status: TicketStatus | string;
+  to_status: TicketStatus | string;
+  action: string;
+  performed_by_crm_user_id: string;
+  performed_by_display_name: string | null;
+  ticket_comment_id: string | null;
+  created_at: string;
+}
+
+export interface TicketAssignmentHistory {
+  ticket_assignment_id: string;
+  previous_role_id: string | null;
+  previous_role_key: string | null;
+  
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/services/app-update.service.ts`
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
+++ b/microtv-crm-frontend/src/app/core/services/app-update.service.ts
@@ -0,0 +1,37 @@
+import { ApplicationRef, Injectable, inject } from '@angular/core';
+import { SwUpdate, VersionEvent } from '@angular/service-worker';
+import { concat, interval } from 'rxjs';
+import { filter, first } from 'rxjs/operators';
+
+@Injectable({ providedIn: 'root' })
+export class AppUpdateService {
+  private readonly appRef = inject(ApplicationRef);
+  private readonly updates = inject(SwUpdate);
+
+  start(): void {
+    if (!this.updates.isEnabled) {
+      return;
+    }
+
+    this.updates.versionUpdates.subscribe((event: VersionEvent) => {
+      if (event.type !== 'VERSION_READY') {
+        return;
+      }
+
+      const shouldReload = window.confirm('Hay una nueva versión disponible. ¿Querés actualizar ahora?');
+      if (!shouldReload) {
+        return;
+      }
+
+      this.updates.activateUpdate().then(() => window.location.reload());
+    });
+
+    const appIsStable$ = this.appRef.isStable.pipe(
+      first((isStable) => isStable)
+    );
+
+    concat(appIsStable$, interval(6 * 60 * 60 * 1000)).subscribe(() => {
+      this.updates.checkForUpdate();
+    });
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/core/services/dashboard.service.ts`
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
+++ b/microtv-crm-frontend/src/app/core/services/dashboard.service.ts
@@ -0,0 +1,187 @@
+import { HttpClient, HttpHeaders } from '@angular/common/http';
+import { inject, Injectable } from '@angular/core';
+import { Observable, throwError } from 'rxjs';
+import { catchError, map } from 'rxjs/operators';
+
+import {
+  DashboardData,
+  DashboardStat,
+  DashboardSummaryApiResponse,
+  RecentActivityItem,
+  RecentTicket
+} from '../models/dashboard.model';
+import { crmApiConfig } from '../config/crm-api.config';
+import { AuthSessionService } from './auth-session.service';
+
+interface ApiErrorEnvelope {
+  error?: {
+    code?: string;
+    message?: string;
+  };
+}
+
+@Injectable({ providedIn: 'root' })
+export class DashboardService {
+  private readonly http = inject(HttpClient);
+  private readonly authSessionService = inject(AuthSessionService);
+
+  getSummary(): Observable<DashboardData> {
+    return this.request<DashboardSummaryApiResponse>('get', '/api/dashboard/summary').pipe(
+      map((response) => this.mapDashboardSummary(response))
+    );
+  }
+
+  private request<T>(method: 'get', path: string): Observable<T> {
+    const headers = this.buildAuthHeaders();
+    if (!headers) {
+      return throwError(() => new Error('No hay una sesión autenticada válida para cargar el dashboard.'));
+    }
+
+    const url = `${crmApiConfig.baseUrl}${path}`;
+    return this.http.get<T>(url, { headers }).pipe(catchError((error) => this.handleRequestError(error)));
+  }
+
+  private buildAuthHeaders(): HttpHeaders | null {
+    const session = this.authSessionService.sessionSnapshot();
+    const accessToken = session?.tokens.access_token;
+    if (!accessToken) {
+      return null;
+    }
+
+    return new HttpHeaders({
+      Authorization: `Bearer ${accessToken}`
+    });
+  }
+
+  private handleRequestError(error: unknown): Observable<never> {
+    const apiMessage = (error as { error?: ApiErrorEnvelope })?.error?.error?.message;
+    if (typeof apiMessage === 'string' && apiMessage.trim()) {
+      return throwError(() => new Error(apiMessage));

... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/services/mock-access-control.service.ts`
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

--- a/microtv-crm-frontend/src/app/core/services/mock-access-control.service.ts
+++ b/microtv-crm-frontend/src/app/core/services/mock-access-control.service.ts
@@ -18,9 +18,12 @@ const moduleRules: MockModuleAccessRule[] = [
   { moduleKey: 'clients', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] },
   { moduleKey: 'billing', allowedRoles: ['admin', 'ejecutivo'] },
   { moduleKey: 'reports', allowedRoles: ['admin', 'ejecutivo'] },
-  { moduleKey: 'settings', allowedRoles: ['admin', 'ejecutivo'] }
+  { moduleKey: 'settings', allowedRoles: ['admin', 'ejecutivo', 'deposito', 'tecnico'] }
 ];
 
+const adminOnlyNavigationItemIds = new Set(['task-templates']);
+const adminOrExecutiveNavigationItemIds = new Set(['tasks-history']);
+
 @Injectable({ providedIn: 'root' })
 export class MockAccessControlService {
   private readonly mockUserContextService = inject(MockUserContextService);
@@ -110,7 +113,12 @@ export class MockAccessControlService {
     return sections
       .map((section) => ({
         ...section,
-        items: section.items.filter((item) => this.canRoleViewModule(role, item.moduleKey ?? item.id as MockModuleKey))
+        items: section.items.filter(
+          (item) =>
+            this.canRoleViewModule(role, item.moduleKey ?? item.id as MockModuleKey)
+            && (!adminOnlyNavigationItemIds.has(item.id) || role === 'admin')
+            && (!adminOrExecutiveNavigationItemIds.has(item.id) || role === 'admin' || role === 'ejecutivo')
+        )
       }))
       .filter((section) => section.items.length > 0);
   }
```

#### 📄 `microtv-crm-frontend/src/app/core/services/mock-layout-data.service.ts`
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

--- a/microtv-crm-frontend/src/app/core/services/mock-layout-data.service.ts
+++ b/microtv-crm-frontend/src/app/core/services/mock-layout-data.service.ts
@@ -1,17 +1,21 @@
 import { inject, Injectable } from '@angular/core';
-import { combineLatest, map, of, shareReplay, switchMap } from 'rxjs';
+import { combineLatest, forkJoin, map, merge, of, shareReplay, startWith, switchMap, catchError } from 'rxjs';
 
 import { DashboardData } from '../models/dashboard.model';
 import { BrandInfo, CurrentUser, LayoutMockData, TopbarInfo } from '../models/layout.model';
 import { NavigationSection } from '../models/navigation.model';
 import { MockAccessControlService } from './mock-access-control.service';
 import { MockUserContextService } from './mock-user-context.service';
+import { TaskManagementService } from './task-management.service';
+import { TicketManagementService } from './ticket-management.service';
 import layoutData from '../../../mocks/layout-data.json';
 
 @Injectable({ providedIn: 'root' })
 export class MockLayoutDataService {
   private readonly mockAccessControlService = inject(MockAccessControlService);
   private readonly mockUserContextService = inject(MockUserContextService);
+  private readonly ticketManagementService = inject(TicketManagementService);
+  private readonly taskManagementService = inject(TaskManagementService);
   private readonly layoutDataSource$ = of(layoutData as LayoutMockData).pipe(
     shareReplay({ bufferSize: 1, refCount: false })
   );
@@ -23,8 +27,34 @@ export class MockLayoutDataService {
     })),
     shareReplay({ bufferSize: 1, refCount: true })
   );
+  private readonly countsRefresh$ = merge(
+    this.ticketManagementService.badgeRefresh$,
+    this.taskManagementService.badgeRefresh$
+  ).pipe(startWith(void 0));
+
+  private readonly assignedCounts$ = this.countsRefresh$.pipe(
+    switchMap(() =>
+      forkJoin({
+        tickets: this.ticketManagementService
+          .listAssignedTickets()
+          .pipe(
+            map((tickets) => tickets.filter((ticket) => ticket.status !== 'CLOSED').length),
+            catchError(() => of(0
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/services/mock-ticket-execution.service.ts`
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

--- a/microtv-crm-frontend/src/app/core/services/mock-ticket-execution.service.ts
+++ b/microtv-crm-frontend/src/app/core/services/mock-ticket-execution.service.ts
@@ -137,7 +137,7 @@ export class MockTicketExecutionService {
       requestedByUserId: user.id,
       requestedByUserName: user.name,
       requestedAt: new Date().toISOString(),
-      status: 'pending',
+      status: 'pending_deposit_review',
       items: items.map((item) => ({ ...item }))
     };
 
@@ -153,7 +153,7 @@ export class MockTicketExecutionService {
 
     if (
       !ticket ||
-      (status !== 'approved' && status !== 'rejected') ||
+      (status !== 'approved_for_dispatch' && status !== 'rejected') ||
       !this.mockAccessControlService.canUserReviewTicketInventoryRequests(user, ticket.depositAssigneeId)
     ) {
       return false;
@@ -161,7 +161,7 @@ export class MockTicketExecutionService {
 
     const state = this.cloneExecutionState(this.currentExecutionState(ticketId));
     const nextRequests = state.inventoryRequests.map((request) =>
-      request.id === requestId && request.status === 'pending'
+      request.id === requestId && request.status === 'pending_deposit_review'
         ? {
             ...request,
             status,
@@ -268,11 +268,11 @@ export class MockTicketExecutionService {
       return 'Despacho registrado';
     }
 
-    if (state.inventoryRequests.some((request) => request.status === 'approved')) {
+    if (state.inventoryRequests.some((request) => request.status === 'approved_for_dispatch')) {
       return 'Solicitud autorizada';
     }
 
-    if (state.inventoryRequests.some((request) => request.status === 'pending')) {
+    if (state.inventoryRequests.some((request) => request.status === 'pending_deposit_review')) {
       return 'Esperando depósito';
     }
 
@@ -284,11 +284,11 @@ export class MockTicketExecutionService {
   }
 
   private resolveStatusTone(ticket: TicketExecutionDefinition, state: TicketExecutionState): TicketListItem['statusTone'] {
-    if (state.dispatchedItems.length > 0 || state.inventoryRequests.some((request) => request.status === 'approved
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/services/notifications.service.ts`
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
+++ b/microtv-crm-frontend/src/app/core/services/notifications.service.ts
@@ -0,0 +1,97 @@
+import { HttpClient, HttpHeaders } from '@angular/common/http';
+import { inject, Injectable, OnDestroy } from '@angular/core';
+import { BehaviorSubject, Observable, Subscription, interval } from 'rxjs';
+import { catchError, switchMap, tap } from 'rxjs/operators';
+import { of } from 'rxjs';
+
+import { crmApiConfig } from '../config/crm-api.config';
+import { Notification, NotificationListResponse, UnreadCountResponse } from '../models/notification.model';
+import { AuthSessionService } from './auth-session.service';
+
+const POLL_INTERVAL_MS = 30_000;
+
+@Injectable({ providedIn: 'root' })
+export class NotificationsService implements OnDestroy {
+  private readonly http = inject(HttpClient);
+  private readonly authSessionService = inject(AuthSessionService);
+
+  private readonly unreadCountSubject = new BehaviorSubject<number>(0);
+  private readonly notificationsSubject = new BehaviorSubject<Notification[]>([]);
+  private pollSubscription: Subscription | null = null;
+
+  readonly unreadCount$ = this.unreadCountSubject.asObservable();
+  readonly notifications$ = this.notificationsSubject.asObservable();
+
+  private get authHeaders(): HttpHeaders {
+    const session = this.authSessionService.sessionSnapshot();
+    const token = session?.tokens.access_token;
+    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : new HttpHeaders();
+  }
+
+  startPolling(): void {
+    if (this.pollSubscription) return;
+    this.load();
+    this.pollSubscription = interval(POLL_INTERVAL_MS)
+      .pipe(switchMap(() => this.fetchList()))
+      .subscribe((data) => this.applyList(data));
+  }
+
+  stopPolling(): void {
+    this.pollSubscription?.unsubscribe();
+    this.pollSubscription = null;
+  }
+
+  load(): void {
+    this.fetchList().subscribe((data) => this.applyList(data));
+  }
+
+  dismissFromTray(notificationId: string): void {
+    const current = this.notificationsSubject.getValue();
+    this.notificationsSubject.next(current.filter((
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/services/settings-management.service.ts`
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
+++ b/microtv-crm-frontend/src/app/core/services/settings-management.service.ts
@@ -0,0 +1,163 @@
+import { HttpClient, HttpHeaders } from '@angular/common/http';
+import { inject, Injectable } from '@angular/core';
+import { Observable, throwError } from 'rxjs';
+import { catchError } from 'rxjs/operators';
+
+import { crmApiConfig } from '../config/crm-api.config';
+import {
+  SettingsCategory,
+  SettingsCategoryWriteRequest,
+  SettingsNotificationRule,
+  SettingsNotificationRuleWriteRequest,
+  SettingsPriority,
+  SettingsPriorityWriteRequest,
+  SettingsRole,
+  SettingsRoleUpdateRequest,
+  SettingsSlaRule,
+  SettingsSlaRuleWriteRequest,
+  SettingsStatus,
+  SettingsStatusWriteRequest,
+  SettingsTaskTemplate,
+  SettingsTaskTemplateUpdateRequest,
+  SettingsUserRoleAssignment,
+  SettingsUserRoleAssignmentRequest
+} from '../models/settings-management.model';
+import { AuthSessionService } from './auth-session.service';
+
+interface ApiErrorEnvelope {
+  error?: {
+    code?: string;
+    message?: string;
+  };
+}
+
+@Injectable({ providedIn: 'root' })
+export class SettingsManagementService {
+  private readonly http = inject(HttpClient);
+  private readonly authSessionService = inject(AuthSessionService);
+
+  listRoles(): Observable<SettingsRole[]> {
+    return this.request<SettingsRole[]>('get', '/settings/roles');
+  }
+
+  updateRole(roleId: string, payload: SettingsRoleUpdateRequest): Observable<SettingsRole> {
+    return this.request<SettingsRole>('put', `/settings/roles/${roleId}`, payload);
+  }
+
+  listUserRoles(): Observable<SettingsUserRoleAssignment[]> {
+    return this.request<SettingsUserRoleAssignment[]>('get', '/settings/user-roles');
+  }
+
+  setUserRoles(userId: string, payload: SettingsUserRoleAssignmentRequest): Observable<SettingsUserRoleAssignment> {
+    return this.request<SettingsUserRoleAssignment>('put', `/settings/user-roles/${userId}`, payload);
+  }
+
+  listCategories(type?: string): Observable<SettingsCategory[]> {
+    const query = type ? `?type=${encodeURIComponent(type)}` : '';
+    return this.reque
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/services/task-management.service.ts`
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

--- a/microtv-crm-frontend/src/app/core/services/task-management.service.ts
+++ b/microtv-crm-frontend/src/app/core/services/task-management.service.ts
@@ -1,10 +1,12 @@
 import { HttpClient, HttpHeaders } from '@angular/common/http';
 import { inject, Injectable } from '@angular/core';
-import { Observable, throwError } from 'rxjs';
-import { catchError, map } from 'rxjs/operators';
+import { Observable, Subject, throwError } from 'rxjs';
+import { catchError, map, tap } from 'rxjs/operators';
 
 import { crmApiConfig } from '../config/crm-api.config';
 import {
+  ApproveTaskRequest,
+  AssignSubtaskRequest,
   ClientSummary,
   CreateLocationRequest,
   CrmUserOption,
@@ -12,6 +14,7 @@ import {
   PersistedLocation,
   CreateTaskTemplateRequest,
   ExecuteSubtaskActionRequest,
+  RejectTaskApprovalRequest,
   SetTaskTemplateActivationRequest,
   TaskDetail,
   TaskSummary,
@@ -35,6 +38,9 @@ interface ApiErrorEnvelope {
 export class TaskManagementService {
   private readonly http = inject(HttpClient);
   private readonly authSessionService = inject(AuthSessionService);
+  private readonly badgeRefreshSubject = new Subject<void>();
+
+  readonly badgeRefresh$ = this.badgeRefreshSubject.asObservable();
 
   listTemplates(): Observable<TaskTemplate[]> {
     return this.request<TaskTemplate[]>('get', '/tasks/templates');
@@ -65,7 +71,10 @@ export class TaskManagementService {
   }
 
   createTaskFromTemplate(payload: CreateTaskFromTemplateRequest): Observable<TaskDetail> {
-    return this.request<TaskDetail>('post', '/tasks', payload);
+    return this.request<TaskDetail>('post', '/tasks', payload).pipe(
+      map((task) => this.normalizeTaskDetail(task)),
+      tap(() => this.badgeRefreshSubject.next())
+    );
   }
 
   createLocation(location: AppLocation): Observable<PersistedLocation> {
@@ -93,24 +102,57 @@ export class TaskManagementService {
     return this.request<TaskSummary[]>('get', '/tasks/tracking/me');
   }
 
+  listTaskHistory(): Observable<TaskSummary[]> {
+    return this.request<TaskSummary[]>('get', '/tasks/history/me');
+  }
+
   listUnassignedSubtasks(): Observable
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/core/services/ticket-management.service.ts`
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
+++ b/microtv-crm-frontend/src/app/core/services/ticket-management.service.ts
@@ -0,0 +1,274 @@
+import { HttpClient, HttpHeaders } from '@angular/common/http';
+import { inject, Injectable } from '@angular/core';
+import { Observable, Subject, throwError } from 'rxjs';
+import { catchError, map, tap } from 'rxjs/operators';
+
+import { crmApiConfig } from '../config/crm-api.config';
+import {
+  ApproveTicketRequest,
+  AssignTicketRequest,
+  CloseTicketRequest,
+  CreateTicketCommentRequest,
+  CreateTicketRequest,
+  RejectTicketApprovalRequest,
+  ReopenTicketRequest,
+  TicketAttachment,
+  TicketClientOption,
+  TicketDetail,
+  TicketRoleOption,
+  TicketSummary,
+  UpdateTicketStatusRequest
+} from '../models/ticket-management.model';
+import { CreateLocationRequest, CrmUserOption, PersistedLocation } from '../models/task-management.model';
+import { AppLocation } from '../models/location.model';
+import { AuthSessionService } from './auth-session.service';
+
+interface ApiErrorEnvelope {
+  error?: {
+    code?: string;
+    message?: string;
+  };
+}
+
+@Injectable({ providedIn: 'root' })
+export class TicketManagementService {
+  private readonly http = inject(HttpClient);
+  private readonly authSessionService = inject(AuthSessionService);
+  private readonly badgeRefreshSubject = new Subject<void>();
+
+  readonly badgeRefresh$ = this.badgeRefreshSubject.asObservable();
+
+  listAssignableRoles(): Observable<TicketRoleOption[]> {
+    return this.request<TicketRoleOption[]>('get', '/tickets/roles');
+  }
+
+  listClients(): Observable<TicketClientOption[]> {
+    return this.request<TicketClientOption[]>('get', '/clients');
+  }
+
+  listCrmUsersByRole(roleKey: string): Observable<CrmUserOption[]> {
+    return this.request<CrmUserOption[]>('get', `/crm-users?role_key=${encodeURIComponent(roleKey)}`);
+  }
+
+  createLocation(location: AppLocation): Observable<PersistedLocation> {
+    const payload: CreateLocationRequest = {
+      latitude: location.latitude,
+      longitude: location.longitude,
+      address_label: location.addressLabel?
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.html`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.html
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.html
@@ -1,12 +1,26 @@
-@if (dashboard$ | async; as dashboard) {
-  <section class="dashboard-page">
-    <app-page-title [title]="dashboard.pageTitle" [subtitle]="dashboard.pageSubtitle" />
+@if (vm$ | async; as vm) {
+  @if (vm.loading) {
+    <section class="dashboard-state dashboard-state--loading" aria-live="polite">
+      <p>Cargando resumen operativo...</p>
+    </section>
+  } @else if (vm.error) {
+    <section class="dashboard-state dashboard-state--error" aria-live="assertive">
+      <p>{{ vm.error }}</p>
+    </section>
+  } @else if (vm.dashboard; as dashboard) {
+    <section class="dashboard-page">
+      <app-page-title [title]="dashboard.pageTitle" [subtitle]="dashboard.pageSubtitle" />
 
-    <app-stats-cards [stats]="dashboard.stats" />
+      <app-stats-cards [stats]="dashboard.stats" />
 
-    <div class="dashboard-page__grid">
-      <app-recent-tickets-table [block]="dashboard.recentTickets" />
-      <app-recent-activity-timeline [block]="dashboard.recentActivity" />
-    </div>
-  </section>
+      <div class="dashboard-page__grid">
+        <app-recent-tickets-table [block]="dashboard.recentTickets" />
+        <app-recent-activity-timeline [block]="dashboard.recentActivity" />
+      </div>
+    </section>
+  } @else {
+    <section class="dashboard-state" aria-live="polite">
+      <p>No hay datos disponibles para mostrar todavía.</p>
+    </section>
+  }
 }
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.scss
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.scss
@@ -5,6 +5,24 @@
   min-width: 0;
 }
 
+.dashboard-state {
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 1.2rem;
+  background: rgba(255, 255, 255, 0.9);
+  box-shadow: var(--shadow-panel);
+  padding: 1.25rem;
+  color: var(--text-secondary);
+  font-weight: 600;
+}
+
+.dashboard-state--loading {
+  border-left: 6px solid var(--accent-blue);
+}
+
+.dashboard-state--error {
+  border-left: 6px solid var(--brand-red);
+}
+
 .dashboard-page__grid {
   display: grid;
   gap: 1.5rem;
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/dashboard-page/dashboard-page.component.ts
@@ -1,12 +1,20 @@
 import { AsyncPipe } from '@angular/common';
 import { Component, inject } from '@angular/core';
+import { catchError, map, of, startWith } from 'rxjs';
 
-import { MockLayoutDataService } from '../../../../core/services/mock-layout-data.service';
+import { DashboardData } from '../../../../core/models/dashboard.model';
+import { DashboardService } from '../../../../core/services/dashboard.service';
 import { RecentActivityTimelineComponent } from '../recent-activity-timeline/recent-activity-timeline.component';
 import { RecentTicketsTableComponent } from '../recent-tickets-table/recent-tickets-table.component';
 import { StatsCardsComponent } from '../stats-cards/stats-cards.component';
 import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
 
+interface DashboardPageVm {
+  dashboard: DashboardData | null;
+  loading: boolean;
+  error: string | null;
+}
+
 @Component({
   selector: 'app-dashboard-page',
   standalone: true,
@@ -21,7 +29,27 @@ import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.
   styleUrl: './dashboard-page.component.scss'
 })
 export class DashboardPageComponent {
-  private readonly mockLayoutDataService = inject(MockLayoutDataService);
+  private readonly dashboardService = inject(DashboardService);
 
-  readonly dashboard$ = this.mockLayoutDataService.dashboard$;
+  readonly vm$ = this.dashboardService.getSummary().pipe(
+    map(
+      (dashboard): DashboardPageVm => ({
+        dashboard,
+        loading: false,
+        error: null
+      })
+    ),
+    startWith({
+      dashboard: null,
+      loading: true,
+      error: null
+    } satisfies DashboardPageVm),
+    catchError((error: unknown) =>
+      of({
+        dashboard: null,
+        loading: false,
+        error: error instanceof Error ? error.message : 'No se pudo cargar el dashboard.'
+      } satisf
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.html`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.html
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.html
@@ -6,7 +6,11 @@
   <mat-card-content>
     <ol class="activity-timeline__list">
       @for (item of block().items; track item.timestamp + item.text) {
-        <li class="activity-timeline__item">
+        <li
+          class="activity-timeline__item"
+          [class.activity-timeline__item--clickable]="!!item.targetRoute"
+          (click)="navigateTo(item.targetRoute)"
+        >
           <span class="activity-timeline__marker" [class]="'activity-timeline__marker activity-timeline__marker--' + item.tone"></span>
 
           <div class="activity-timeline__content">
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.scss
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.scss
@@ -26,6 +26,14 @@
   padding: 0.95rem 0;
 }
 
+.activity-timeline__item--clickable {
+  cursor: pointer;
+}
+
+.activity-timeline__item--clickable:hover {
+  background: rgba(37, 99, 235, 0.04);
+}
+
 .activity-timeline__item + .activity-timeline__item {
   border-top: 1px solid rgba(23, 24, 26, 0.08);
 }
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.ts
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/recent-activity-timeline/recent-activity-timeline.component.ts
@@ -1,5 +1,6 @@
-import { Component, input } from '@angular/core';
+import { Component, inject, input } from '@angular/core';
 import { MatCardModule } from '@angular/material/card';
+import { Router } from '@angular/router';
 
 import { RecentActivityBlock } from '../../../../core/models/dashboard.model';
 
@@ -11,5 +12,14 @@ import { RecentActivityBlock } from '../../../../core/models/dashboard.model';
   styleUrl: './recent-activity-timeline.component.scss'
 })
 export class RecentActivityTimelineComponent {
+  private readonly router = inject(Router);
+
   readonly block = input.required<RecentActivityBlock>();
+
+  navigateTo(targetRoute?: string): void {
+    if (!targetRoute) {
+      return;
+    }
+    void this.router.navigateByUrl(targetRoute);
+  }
 }
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.html`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.html
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.html
@@ -48,7 +48,12 @@
         </ng-container>
 
         <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
-        <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
+        <tr
+          mat-row
+          *matRowDef="let row; columns: displayedColumns"
+          class="tickets-table__row"
+          (click)="navigateToTicket(row.targetRoute)"
+        ></tr>
       </table>
     </div>
   </mat-card-content>
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.scss
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.scss
@@ -28,6 +28,14 @@
   font-weight: 700;
 }
 
+.tickets-table__row {
+  cursor: pointer;
+}
+
+.tickets-table__row:hover td {
+  background: rgba(37, 99, 235, 0.04);
+}
+
 .tickets-table__assignee {
   display: inline-flex;
   align-items: center;
```

#### 📄 `microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.ts
+++ b/microtv-crm-frontend/src/app/features/dashboard/components/recent-tickets-table/recent-tickets-table.component.ts
@@ -1,6 +1,7 @@
-import { Component, input } from '@angular/core';
+import { Component, inject, input } from '@angular/core';
 import { MatCardModule } from '@angular/material/card';
 import { MatTableModule } from '@angular/material/table';
+import { Router } from '@angular/router';
 
 import { RecentTicketsBlock } from '../../../../core/models/dashboard.model';
 import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
@@ -15,6 +16,8 @@ import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avat
   styleUrl: './recent-tickets-table.component.scss'
 })
 export class RecentTicketsTableComponent {
+  private readonly router = inject(Router);
+
   readonly block = input.required<RecentTicketsBlock>();
 
   readonly displayedColumns: Array<'id' | 'subject' | 'client' | 'priority' | 'status' | 'assignedTo'> = [
@@ -29,4 +32,11 @@ export class RecentTicketsTableComponent {
   labelFor(column: (typeof this.displayedColumns)[number]): string {
     return this.block().columns.find((item) => item.key === column)?.label ?? column;
   }
+
+  navigateToTicket(targetRoute?: string): void {
+    if (!targetRoute) {
+      return;
+    }
+    void this.router.navigateByUrl(targetRoute);
+  }
 }
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/components/recharts-host.component.ts`
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
+++ b/microtv-crm-frontend/src/app/features/reports/components/recharts-host.component.ts
@@ -0,0 +1,304 @@
+import { AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy, PLATFORM_ID, SimpleChanges, inject } from '@angular/core';
+import { isPlatformBrowser } from '@angular/common';
+
+import React from 'react';
+import { createRoot, Root } from 'react-dom/client';
+import {
+  Area,
+  AreaChart,
+  Bar,
+  BarChart,
+  CartesianGrid,
+  Cell,
+  Legend,
+  Line,
+  LineChart,
+  Pie,
+  PieChart,
+  ResponsiveContainer,
+  Tooltip,
+  XAxis,
+  YAxis
+} from 'recharts';
+
+import { ReportSeriesPoint, formatReportDateTime } from '../report.types';
+
+interface ChartDatum {
+  date: string;
+  [key: string]: string | number;
+}
+
+interface DonutDatum {
+  name: string;
+  value: number;
+}
+
+@Component({
+  selector: 'app-recharts-host',
+  standalone: true,
+  template: '<div class="recharts-host" style="height: 320px; width: 100%;"></div>'
+})
+export class RechartsHostComponent implements AfterViewInit, OnChanges, OnDestroy {
+  @Input({ required: true }) chartKind: 'area' | 'line' | 'bar' | 'horizontal_bar' | 'donut' | 'pie' = 'bar';
+  @Input({ required: true }) series: ReportSeriesPoint[] = [];
+
+  private readonly hostRef = inject(ElementRef<HTMLElement>);
+  private readonly platformId = inject(PLATFORM_ID);
+  private root: Root | null = null;
+
+  ngAfterViewInit(): void {
+    if (!isPlatformBrowser(this.platformId)) {
+      return;
+    }
+
+    const mount = this.hostRef.nativeElement.firstElementChild as HTMLElement | null;
+    if (!mount) {
+      return;
+    }
+
+    this.root = createRoot(mount);
+    this.renderChart();
+  }
+
+  ngOnChanges(changes: SimpleChanges): void {
+    if (!this.root) {
+      return;
+    }
+
+    if (changes['series'] || changes['chartKind']) {
+      this.renderChart();
+    }
+  }
+
+  ngOnDestroy(): void {
+    this.root?.unmount();
+  }
+
+  private renderChart(): void {
+    if (!this.root) {
+      return;
+    }
+
+    const chartData = this.toChartData(this.series);
+    const donutD
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/report-detail.component.html`
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
+++ b/microtv-crm-frontend/src/app/features/reports/report-detail.component.html
@@ -0,0 +1,225 @@
+@if (report; as reportInfo) {
+  <section class="report-detail">
+    <header class="report-detail__header">
+      <div>
+        <a class="report-detail__back" [routerLink]="['/reports', reportInfo.category]">← Volver a reportes</a>
+        <h2>{{ reportInfo.title }}</h2>
+        <p>{{ reportInfo.description }}</p>
+      </div>
+
+      <div class="report-detail__actions">
+        <button type="button" class="btn btn--ghost" (click)="updateReport()">Actualizar</button>
+        <button type="button" class="btn" (click)="exportCsv()">Exportar CSV</button>
+      </div>
+    </header>
+
+    <section class="filters-card">
+      <div class="quick-dates">
+        <button type="button" [ngClass]="{ active: quickDate === 'week' }" (click)="applyQuickRange('week')">Esta semana</button>
+        <button type="button" [ngClass]="{ active: quickDate === 'month' }" (click)="applyQuickRange('month')">Este mes</button>
+        <button type="button" [ngClass]="{ active: quickDate === 'last-month' }" (click)="applyQuickRange('last-month')">Último mes</button>
+        <button type="button" [ngClass]="{ active: quickDate === 'custom' }" (click)="applyQuickRange('custom')">Personalizado</button>
+      </div>
+
+      @if (filtersLoading) {
+        <div class="filters-card__state">Cargando opciones de filtros...</div>
+      } @else if (filtersErrorMessage) {
+        <div class="filters-card__state filters-card__state--error">{{ filtersErrorMessage }}</div>
+      }
+
+      <div class="filters-grid">
+        <label>
+          Desde
+          <input type="date" [(ngModel)]="dateFrom" />
+        </label>
+        <label>
+          Hasta
+          <input type="date" [(ngModel)]="dateTo" />
+        </label>
+
+        @if (reportId === 'tickets-by-priority' || reportId === 'tickets-by-status' || reportId === 'tickets-by-client' || reportId === 'deposit-requests-status' || reportId === 'tasks-by-status' || reportId === 'tasks-by-technician') {
+          <label
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/report-detail.component.scss`
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
+++ b/microtv-crm-frontend/src/app/features/reports/report-detail.component.scss
@@ -0,0 +1,223 @@
+.report-detail {
+  display: grid;
+  gap: 1rem;
+}
+
+.report-detail__header {
+  display: flex;
+  justify-content: space-between;
+  gap: 1rem;
+  align-items: flex-start;
+}
+
+.report-detail__back {
+  display: inline-block;
+  margin-bottom: 0.45rem;
+  color: var(--text-secondary);
+  text-decoration: none;
+}
+
+.report-detail__header h2 {
+  margin: 0;
+}
+
+.report-detail__header p {
+  margin: 0.35rem 0 0;
+  color: var(--text-secondary);
+}
+
+.report-detail__actions {
+  display: flex;
+  gap: 0.5rem;
+}
+
+.filters-card,
+.chart-card,
+.table-card,
+.report-state {
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 1rem;
+  background: rgba(255, 255, 255, 0.95);
+  box-shadow: var(--shadow-panel);
+  padding: 1rem;
+}
+
+.quick-dates {
+  display: flex;
+  flex-wrap: wrap;
+  gap: 0.45rem;
+  margin-bottom: 0.9rem;
+}
+
+.filters-card__state {
+  margin-bottom: 0.9rem;
+  color: var(--text-secondary);
+  font-weight: 600;
+}
+
+.filters-card__state--error {
+  color: var(--brand-red);
+}
+
+.quick-dates button {
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 999px;
+  background: #fff;
+  font-weight: 600;
+  color: var(--text-secondary);
+  padding: 0.35rem 0.75rem;
+  cursor: pointer;
+}
+
+.quick-dates button.active {
+  border-color: rgba(62, 142, 222, 0.35);
+  background: rgba(62, 142, 222, 0.14);
+  color: var(--text-primary);
+}
+
+.filters-grid {
+  display: grid;
+  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
+  gap: 0.65rem;
+}
+
+.filters-grid label {
+  display: grid;
+  gap: 0.3rem;
+  font-size: 0.85rem;
+  color: var(--text-secondary);
+}
+
+.filters-grid input,
+.filters-grid select,
+.table-card__toolbar input {
+  border: 1px solid rgba(23, 24, 26, 0.12);
+  border-radius: 0.6rem;
+  padding: 0.5rem 0.65rem;
+  font-size: 0.9rem;
+  color: var(--text-primary);
+}
+
+.report-state--loading {
+  border-left: 6px solid var(--accent-blue);
+}
+
+.report-state--error {
+  border-left: 6
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/report-detail.component.ts`
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
+++ b/microtv-crm-frontend/src/app/features/reports/report-detail.component.ts
@@ -0,0 +1,402 @@
+import { NgClass } from '@angular/common';
+import { Component, OnDestroy } from '@angular/core';
+import { FormsModule } from '@angular/forms';
+import { ActivatedRoute, RouterLink } from '@angular/router';
+import { Subject, takeUntil } from 'rxjs';
+
+import { RechartsHostComponent } from './components/recharts-host.component';
+import {
+  formatReportActionType,
+  formatReportDateTime,
+  formatReportPriority,
+  formatReportStatus,
+  PRIORITY_OPTIONS,
+  REPORT_CARDS,
+  REPORT_COLUMNS,
+  STATUS_OPTIONS,
+  ReportCardDefinition,
+  ReportColumn,
+  ReportFilterCatalogs,
+  ReportId,
+  ReportOption,
+  ReportPayload,
+  ReportRequestFilters,
+  ReportSeriesPoint
+} from './report.types';
+import { ReportsService } from './reports.service';
+
+@Component({
+  selector: 'app-report-detail',
+  standalone: true,
+  imports: [FormsModule, NgClass, RechartsHostComponent, RouterLink],
+  templateUrl: './report-detail.component.html',
+  styleUrl: './report-detail.component.scss'
+})
+export class ReportDetailComponent implements OnDestroy {
+  readonly destroy$ = new Subject<void>();
+
+  report: ReportCardDefinition | null = null;
+  reportId: ReportId | null = null;
+  loading = false;
+  errorMessage: string | null = null;
+  payload: ReportPayload | null = null;
+  filtersLoading = false;
+  filtersErrorMessage: string | null = null;
+
+  quickDate: 'week' | 'month' | 'last-month' | 'custom' = 'month';
+  dateFrom = '';
+  dateTo = '';
+  filterUser = '';
+  filterTechnician = '';
+  filterClient = '';
+  filterStatus = '';
+  filterPriority = '';
+  filterCategory = '';
+  filterWarehouse = '';
+  filterRequester = '';
+  filterApprover = '';
+  filterActionType = '';
+  onlyCritical = true;
+
+  tableSearch = '';
+  page = 1;
+  pageSize = 10;
+  filterCatalogs: ReportFilterCatalogs = {
+    users: [],
+    clients: [],
+    categories: [],
+    warehouses: [],
+    technicians: [],
+    actionTypes: []
+  };
+
+  readonly statusOptions = STATUS_OPTIO
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/report-list.component.html`
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
+++ b/microtv-crm-frontend/src/app/features/reports/report-list.component.html
@@ -0,0 +1,26 @@
+@if (vm$ | async; as vm) {
+  @if (vm.category === 'saved') {
+    <section class="reports-placeholder">
+      <h2>Mis Reportes</h2>
+      <p>Reportes guardados próximamente.</p>
+    </section>
+  } @else {
+    <section class="reports-grid">
+      @for (card of vm.cards; track trackById($index, card)) {
+        @if (card.enabled) {
+          <a class="report-card" [routerLink]="['/reports', vm.category, card.id]">
+            <h3>{{ card.title }}</h3>
+            <p>{{ card.description }}</p>
+            <span class="report-card__cta">Abrir reporte</span>
+          </a>
+        } @else {
+          <article class="report-card report-card--disabled">
+            <h3>{{ card.title }}</h3>
+            <p>{{ card.description }}</p>
+            <span class="report-card__tag">Próximamente</span>
+          </article>
+        }
+      }
+    </section>
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/report-list.component.scss`
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
+++ b/microtv-crm-frontend/src/app/features/reports/report-list.component.scss
@@ -0,0 +1,65 @@
+.reports-placeholder {
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 1rem;
+  background: rgba(255, 255, 255, 0.9);
+  box-shadow: var(--shadow-panel);
+  padding: 1.1rem;
+}
+
+.reports-grid {
+  display: grid;
+  grid-template-columns: repeat(auto-fill, minmax(16.5rem, 1fr));
+  gap: 0.9rem;
+}
+
+.report-card {
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 1rem;
+  background: rgba(255, 255, 255, 0.95);
+  box-shadow: var(--shadow-panel);
+  padding: 1rem;
+  text-decoration: none;
+  color: inherit;
+  display: grid;
+  gap: 0.6rem;
+  transition: transform 140ms ease, box-shadow 140ms ease;
+}
+
+.report-card:hover {
+  transform: translateY(-2px);
+  box-shadow: 0 16px 32px rgba(9, 19, 38, 0.12);
+}
+
+.report-card h3 {
+  margin: 0;
+  font-size: 1rem;
+}
+
+.report-card p {
+  margin: 0;
+  color: var(--text-secondary);
+  font-size: 0.92rem;
+}
+
+.report-card__cta,
+.report-card__tag {
+  justify-self: start;
+  font-size: 0.8rem;
+  font-weight: 700;
+  border-radius: 999px;
+  padding: 0.25rem 0.65rem;
+}
+
+.report-card__cta {
+  background: rgba(62, 142, 222, 0.12);
+  color: var(--text-primary);
+}
+
+.report-card--disabled {
+  opacity: 0.75;
+}
+
+.report-card__tag {
+  background: rgba(23, 24, 26, 0.09);
+  color: var(--text-secondary);
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/report-list.component.ts`
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
+++ b/microtv-crm-frontend/src/app/features/reports/report-list.component.ts
@@ -0,0 +1,32 @@
+import { Component, inject } from '@angular/core';
+import { ActivatedRoute, RouterLink } from '@angular/router';
+import { map } from 'rxjs';
+import { AsyncPipe } from '@angular/common';
+
+import { REPORT_CARDS, ReportCardDefinition, ReportCategoryKey } from './report.types';
+
+@Component({
+  selector: 'app-report-list',
+  standalone: true,
+  imports: [AsyncPipe, RouterLink],
+  templateUrl: './report-list.component.html',
+  styleUrl: './report-list.component.scss'
+})
+export class ReportListComponent {
+  private readonly route = inject(ActivatedRoute);
+
+  readonly vm$ = this.route.paramMap.pipe(
+    map((params) => {
+      const category = (params.get('category') as ReportCategoryKey | null) ?? 'tickets';
+      const cards = REPORT_CARDS.filter((card) => card.category === category);
+      return {
+        category,
+        cards
+      };
+    })
+  );
+
+  trackById(_: number, card: ReportCardDefinition): string {
+    return card.id;
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/report.types.ts`
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
+++ b/microtv-crm-frontend/src/app/features/reports/report.types.ts
@@ -0,0 +1,304 @@
+export type ReportCategoryKey = 'saved' | 'tickets' | 'tasks' | 'stock' | 'deposit-requests' | 'activity';
+
+export type ReportId =
+  | 'saved-reports'
+  | 'tickets-by-status'
+  | 'tickets-by-priority'
+  | 'tickets-by-client'
+  | 'tasks-by-status'
+  | 'tasks-by-technician'
+  | 'tasks-overdue-blocked'
+  | 'stock-critical'
+  | 'stock-movements'
+  | 'stock-consumption'
+  | 'deposit-requests-status'
+  | 'deposit-requests-approved'
+  | 'deposit-requests-dispatched'
+  | 'activity-by-user'
+  | 'activity-by-action-type'
+  | 'activity-closures-by-user';
+
+export interface ReportTabDefinition {
+  key: ReportCategoryKey;
+  label: string;
+}
+
+export interface ReportCardDefinition {
+  id: ReportId;
+  category: ReportCategoryKey;
+  title: string;
+  description: string;
+  enabled: boolean;
+}
+
+export interface ReportColumn {
+  key: string;
+  label: string;
+}
+
+export interface ReportSeriesPoint {
+  label: string;
+  date: string;
+  value: number;
+  meta?: Record<string, string | number | null>;
+}
+
+export interface ReportKpi {
+  key: string;
+  label: string;
+  value: number | string;
+}
+
+export interface ReportPayload {
+  report_kind: 'tickets' | 'tasks' | 'stock_critical' | 'deposit_requests' | 'user_activity';
+  chart_kind: 'area' | 'line' | 'bar' | 'horizontal_bar' | 'donut' | 'pie';
+  kpis: ReportKpi[];
+  series: ReportSeriesPoint[];
+  rows: Record<string, unknown>[];
+}
+
+export interface ReportOption {
+  id: string;
+  label: string;
+}
+
+export interface ReportFilterCatalogs {
+  users: ReportOption[];
+  clients: ReportOption[];
+  categories: ReportOption[];
+  warehouses: ReportOption[];
+  technicians: ReportOption[];
+  actionTypes: ReportOption[];
+}
+
+export interface ReportRequestFilters {
+  date_from?: string;
+  date_to?: string;
+  group_by?: string;
+  status?: string;
+  priority?: string;
+  client_id?: string;
+  technician_id?: string;
+  category?: string;
+  warehouse_id?: string;
+  only_critical?: boolean;

... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/reports-routing.module.ts`
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
+++ b/microtv-crm-frontend/src/app/features/reports/reports-routing.module.ts
@@ -0,0 +1,27 @@
+import { Routes } from '@angular/router';
+
+import { ReportDetailComponent } from './report-detail.component';
+import { ReportListComponent } from './report-list.component';
+import { ReportsComponent } from './reports.component';
+
+export const REPORTS_ROUTES: Routes = [
+  {
+    path: '',
+    component: ReportsComponent,
+    children: [
+      {
+        path: '',
+        pathMatch: 'full',
+        redirectTo: 'tickets'
+      },
+      {
+        path: ':category',
+        component: ReportListComponent
+      },
+      {
+        path: ':category/:reportId',
+        component: ReportDetailComponent
+      }
+    ]
+  }
+];
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/reports.component.html`
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
+++ b/microtv-crm-frontend/src/app/features/reports/reports.component.html
@@ -0,0 +1,20 @@
+<section class="reports-page">
+  <app-page-title
+    title="Reportes"
+    subtitle="Vista analítica operativa con filtros, KPIs, gráfico y detalle tabular."
+  />
+
+  <nav class="reports-tabs" aria-label="Categorías de reportes">
+    @for (tab of tabs; track tab.key) {
+      <a
+        class="reports-tabs__item"
+        [routerLink]="['/reports', tab.key]"
+        routerLinkActive="reports-tabs__item--active"
+      >
+        {{ tab.label }}
+      </a>
+    }
+  </nav>
+
+  <router-outlet />
+</section>
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/reports.component.scss`
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
+++ b/microtv-crm-frontend/src/app/features/reports/reports.component.scss
@@ -0,0 +1,34 @@
+.reports-page {
+  display: grid;
+  gap: 1rem;
+}
+
+.reports-tabs {
+  display: flex;
+  flex-wrap: wrap;
+  gap: 0.5rem;
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  background: rgba(255, 255, 255, 0.92);
+  border-radius: 1rem;
+  padding: 0.5rem;
+}
+
+.reports-tabs__item {
+  text-decoration: none;
+  color: var(--text-secondary);
+  font-weight: 600;
+  font-size: 0.92rem;
+  border-radius: 0.7rem;
+  padding: 0.55rem 0.8rem;
+  transition: background-color 160ms ease, color 160ms ease;
+}
+
+.reports-tabs__item:hover {
+  background: rgba(62, 142, 222, 0.1);
+  color: var(--text-primary);
+}
+
+.reports-tabs__item--active {
+  background: rgba(62, 142, 222, 0.18);
+  color: var(--text-primary);
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/reports.component.ts`
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
+++ b/microtv-crm-frontend/src/app/features/reports/reports.component.ts
@@ -0,0 +1,16 @@
+import { Component } from '@angular/core';
+import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
+
+import { PageTitleComponent } from '../../shared/ui/page-title/page-title.component';
+import { REPORT_TABS } from './report.types';
+
+@Component({
+  selector: 'app-reports',
+  standalone: true,
+  imports: [RouterLink, RouterLinkActive, RouterOutlet, PageTitleComponent],
+  templateUrl: './reports.component.html',
+  styleUrl: './reports.component.scss'
+})
+export class ReportsComponent {
+  readonly tabs = REPORT_TABS;
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/reports/reports.service.ts`
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
+++ b/microtv-crm-frontend/src/app/features/reports/reports.service.ts
@@ -0,0 +1,111 @@
+import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
+import { inject, Injectable } from '@angular/core';
+import { Observable, forkJoin, of, throwError } from 'rxjs';
+import { catchError } from 'rxjs/operators';
+
+import { crmApiConfig } from '../../core/config/crm-api.config';
+import { AuthSessionService } from '../../core/services/auth-session.service';
+import { ReportFilterCatalogs, ReportId, ReportOption, ReportPayload, ReportRequestFilters } from './report.types';
+
+interface ApiErrorEnvelope {
+  error?: {
+    code?: string;
+    message?: string;
+  };
+}
+
+@Injectable({ providedIn: 'root' })
+export class ReportsService {
+  private readonly http = inject(HttpClient);
+  private readonly authSessionService = inject(AuthSessionService);
+
+  loadFilterCatalogs(reportId: ReportId): Observable<ReportFilterCatalogs> {
+    return forkJoin({
+      users: this.requiresUserOptions(reportId) ? this.loadOptions('/api/reports/options/users') : of([]),
+      clients: reportId === 'tickets-by-client' ? this.loadOptions('/api/reports/options/clients') : of([]),
+      categories: reportId === 'stock-critical' ? this.loadOptions('/api/reports/options/categories') : of([]),
+      warehouses: reportId === 'stock-critical' ? this.loadOptions('/api/reports/options/warehouses') : of([]),
+      technicians: reportId === 'tasks-by-status' || reportId === 'tasks-by-technician' ? this.loadOptions('/api/reports/options/technicians') : of([]),
+      actionTypes: reportId === 'activity-by-user' ? this.loadOptions('/api/reports/options/action-types') : of([])
+    });
+  }
+
+  loadReport(reportId: ReportId, filters: ReportRequestFilters): Observable<ReportPayload> {
+    const endpoint = this.resolveEndpoint(reportId);
+    if (!endpoint) {
+      return throwError(() => new Error('Este reporte está marcado como próximamente.'));
+    }
+
+    const headers = this.buildAuthHeaders();
+    if (!headers) {
+      return throwError(() => new Error('No h
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-edit-dialog/settings-edit-dialog.component.html`
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
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-edit-dialog/settings-edit-dialog.component.html
@@ -0,0 +1,177 @@
+<h2 mat-dialog-title>{{ data.title }}</h2>
+
+<mat-dialog-content>
+  <form [formGroup]="form" class="settings-edit-dialog__form">
+    @if (data.kind === 'role') {
+      <mat-form-field appearance="outline">
+        <mat-label>Nombre del rol</mat-label>
+        <input matInput formControlName="role_label" />
+      </mat-form-field>
+
+      <mat-form-field appearance="outline">
+        <mat-label>Descripción</mat-label>
+        <textarea matInput rows="3" formControlName="description"></textarea>
+      </mat-form-field>
+
+      <mat-slide-toggle formControlName="is_active">Activo</mat-slide-toggle>
+    }
+
+    @if (data.kind === 'user-roles') {
+      <mat-form-field appearance="outline">
+        <mat-label>Roles asignados</mat-label>
+        <mat-select formControlName="role_keys" multiple>
+          @for (role of data.roleOptions ?? []; track role.code) {
+            <mat-option [value]="role.code">{{ role.label }}</mat-option>
+          }
+        </mat-select>
+      </mat-form-field>
+    }
+
+    @if (data.kind === 'category') {
+      <mat-form-field appearance="outline">
+        <mat-label>Nombre</mat-label>
+        <input matInput formControlName="name" />
+      </mat-form-field>
+
+      <mat-form-field appearance="outline">
+        <mat-label>Tipo</mat-label>
+        <input matInput formControlName="category_type" />
+      </mat-form-field>
+
+      <mat-form-field appearance="outline">
+        <mat-label>Descripción</mat-label>
+        <textarea matInput rows="3" formControlName="description"></textarea>
+      </mat-form-field>
+
+      <mat-slide-toggle formControlName="is_active">Activo</mat-slide-toggle>
+    }
+
+    @if (data.kind === 'priority') {
+      <mat-form-field appearance="outline">
+        <mat-label>Código</mat-label>
+        <input matInput formControlName="code" />
+      </mat-form-field>
+
+      <mat-form-field appearance="outline">
+        <mat-label>Nombre
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-edit-dialog/settings-edit-dialog.component.scss`
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
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-edit-dialog/settings-edit-dialog.component.scss
@@ -0,0 +1,5 @@
+.settings-edit-dialog__form {
+  display: grid;
+  gap: 0.9rem;
+  min-width: min(42rem, 80vw);
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-edit-dialog/settings-edit-dialog.component.ts`
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
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-edit-dialog/settings-edit-dialog.component.ts
@@ -0,0 +1,133 @@
+import { CommonModule } from '@angular/common';
+import { Component, Inject, inject } from '@angular/core';
+import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
+import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
+import { MatButtonModule } from '@angular/material/button';
+import { MatFormFieldModule } from '@angular/material/form-field';
+import { MatInputModule } from '@angular/material/input';
+import { MatSelectModule } from '@angular/material/select';
+import { MatSlideToggleModule } from '@angular/material/slide-toggle';
+
+export type SettingsDialogKind =
+  | 'role'
+  | 'user-roles'
+  | 'category'
+  | 'priority'
+  | 'status'
+  | 'template'
+  | 'sla'
+  | 'notification';
+
+export interface SettingsDialogRoleOption {
+  code: string;
+  label: string;
+}
+
+export interface SettingsEditDialogData {
+  kind: SettingsDialogKind;
+  title: string;
+  submitLabel: string;
+  value: Record<string, unknown>;
+  roleOptions?: SettingsDialogRoleOption[];
+  priorityOptions?: string[];
+}
+
+@Component({
+  selector: 'app-settings-edit-dialog',
+  standalone: true,
+  imports: [
+    CommonModule,
+    ReactiveFormsModule,
+    MatDialogActions,
+    MatDialogClose,
+    MatDialogContent,
+    MatDialogTitle,
+    MatButtonModule,
+    MatFormFieldModule,
+    MatInputModule,
+    MatSelectModule,
+    MatSlideToggleModule
+  ],
+  templateUrl: './settings-edit-dialog.component.html',
+  styleUrl: './settings-edit-dialog.component.scss'
+})
+export class SettingsEditDialogComponent {
+  private readonly dialogRef = inject(MatDialogRef<SettingsEditDialogComponent, Record<string, unknown>>);
+  private readonly fb = inject(FormBuilder);
+
+  readonly form: FormGroup;
+
+  constructor(@Inject(MAT_DIALOG_DATA) readonly data: SettingsEditDialogData) {
+    this.form = this.buildForm(data);
+  }
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.html`
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
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.html
@@ -0,0 +1,269 @@
+<section class="settings-page">
+  <app-page-title
+    eyebrow="Configuración"
+    title="Configuración CRM"
+    subtitle="Administrá usuarios y roles, categorías, prioridades y estados, templates, SLA y notificaciones con persistencia real."
+  />
+
+  @if (errorMessage(); as errorMessage) {
+    <mat-card class="settings-page__message settings-page__message--error">
+      <mat-card-content>
+        <mat-icon>error</mat-icon>
+        <p>{{ errorMessage }}</p>
+        <button mat-stroked-button type="button" (click)="reload()">Reintentar</button>
+      </mat-card-content>
+    </mat-card>
+  }
+
+  @if (loading()) {
+    <mat-card class="settings-page__message">
+      <mat-card-content>
+        <mat-spinner diameter="32"></mat-spinner>
+        <p>Cargando configuración...</p>
+      </mat-card-content>
+    </mat-card>
+  } @else {
+    <mat-card class="settings-page__tabs-card">
+      <mat-tab-group>
+        <mat-tab label="Usuarios y roles">
+          <section class="settings-page__tab-content">
+            <div class="settings-page__section-header">
+              <h3>Roles funcionales</h3>
+            </div>
+
+            <table class="settings-page__table">
+              <thead>
+                <tr>
+                  <th>Rol</th>
+                  <th>Código</th>
+                  <th>Estado</th>
+                  <th></th>
+                </tr>
+              </thead>
+              <tbody>
+                @for (role of roles(); track role.crm_role_id) {
+                  <tr>
+                    <td>{{ role.role_label }}</td>
+                    <td>{{ role.role_key }}</td>
+                    <td>{{ role.is_active ? 'Activo' : 'Inactivo' }}</td>
+                    <td class="settings-page__actions-cell">
+                      <button mat-button type="button" (click)="openRoleDialog(role)">Editar</button>
+                    </td>
+                  </tr>
+                }
+              </tb
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.scss`
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
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.scss
@@ -0,0 +1,92 @@
+.settings-page {
+  display: grid;
+  gap: 1rem;
+}
+
+.settings-page__tabs-card,
+.settings-page__message {
+  border-radius: 1.25rem;
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  box-shadow: var(--shadow-panel);
+}
+
+.settings-page__tab-content {
+  display: grid;
+  gap: 1rem;
+  padding: 1rem 0.25rem 0.25rem;
+}
+
+.settings-page__section-header {
+  display: flex;
+  justify-content: space-between;
+  align-items: center;
+  gap: 0.75rem;
+}
+
+.settings-page__section-header h3 {
+  margin: 0;
+  font-size: 1.02rem;
+}
+
+.settings-page__section-header--spaced {
+  margin-top: 0.75rem;
+}
+
+.settings-page__split-header {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 1rem;
+}
+
+.settings-page__split-grid {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 1rem;
+}
+
+.settings-page__table {
+  width: 100%;
+  border-collapse: collapse;
+  font-size: 0.92rem;
+}
+
+.settings-page__table th,
+.settings-page__table td {
+  padding: 0.55rem 0.5rem;
+  border-bottom: 1px solid rgba(23, 24, 26, 0.08);
+  text-align: left;
+}
+
+.settings-page__table th {
+  font-size: 0.72rem;
+  text-transform: uppercase;
+  letter-spacing: 0.07em;
+  color: var(--text-secondary);
+}
+
+.settings-page__actions-cell {
+  width: 1%;
+  white-space: nowrap;
+  text-align: right;
+}
+
+.settings-page__message mat-card-content {
+  display: flex;
+  align-items: center;
+  gap: 0.75rem;
+}
+
+.settings-page__message p {
+  margin: 0;
+}
+
+.settings-page__message--error mat-icon {
+  color: #b3261e;
+}
+
+@media (max-width: 980px) {
+  .settings-page__split-header,
+  .settings-page__split-grid {
+    grid-template-columns: 1fr;
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.ts`
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
+++ b/microtv-crm-frontend/src/app/features/settings/components/settings-page/settings-page.component.ts
@@ -0,0 +1,345 @@
+import { DatePipe } from '@angular/common';
+import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
+import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
+import { MatButtonModule } from '@angular/material/button';
+import { MatCardModule } from '@angular/material/card';
+import { MatDialog, MatDialogModule } from '@angular/material/dialog';
+import { MatIconModule } from '@angular/material/icon';
+import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
+import { MatTabsModule } from '@angular/material/tabs';
+import { forkJoin } from 'rxjs';
+
+import {
+  SettingsCategory,
+  SettingsCategoryWriteRequest,
+  SettingsNotificationRule,
+  SettingsNotificationRuleWriteRequest,
+  SettingsPriority,
+  SettingsPriorityWriteRequest,
+  SettingsRole,
+  SettingsRoleUpdateRequest,
+  SettingsSlaRule,
+  SettingsSlaRuleWriteRequest,
+  SettingsStatus,
+  SettingsStatusWriteRequest,
+  SettingsTaskTemplate,
+  SettingsTaskTemplateUpdateRequest,
+  SettingsUserRoleAssignment,
+  SettingsUserRoleAssignmentRequest
+} from '../../../../core/models/settings-management.model';
+import { SettingsManagementService } from '../../../../core/services/settings-management.service';
+import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
+import {
+  SettingsDialogRoleOption,
+  SettingsEditDialogComponent
+} from '../settings-edit-dialog/settings-edit-dialog.component';
+
+@Component({
+  selector: 'app-settings-page',
+  standalone: true,
+  imports: [
+    DatePipe,
+    MatButtonModule,
+    MatCardModule,
+    MatDialogModule,
+    MatIconModule,
+    MatProgressSpinnerModule,
+    MatTabsModule,
+    PageTitleComponent
+  ],
+  templateUrl: './settings-page.component.html',
+  styleUrl: './settings-page.component.scss',
+  changeDetection: ChangeDetectionStrategy.OnPush
+})
+export class SettingsPageComponent {
+  private readonly settings
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/subtask-success-page/subtask-success-page.component.html`
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
+++ b/microtv-crm-frontend/src/app/features/tasks/components/subtask-success-page/subtask-success-page.component.html
@@ -0,0 +1,14 @@
+<section class="subtask-success-page">
+  <mat-card class="subtask-success-page__card">
+    <mat-card-content>
+      <mat-icon class="subtask-success-page__icon">check_circle</mat-icon>
+      <h1>{{ title() }}</h1>
+      <p>La subtarea se cerro correctamente y el flujo avanzo al siguiente rol/usuario.</p>
+      <p>Redirigiendo al menu de tareas en {{ redirectInSeconds() }}s...</p>
+
+      <button mat-flat-button color="primary" type="button" (click)="goToTasks()">
+        Ir ahora al menu de tareas
+      </button>
+    </mat-card-content>
+  </mat-card>
+</section>
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/subtask-success-page/subtask-success-page.component.scss`
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
+++ b/microtv-crm-frontend/src/app/features/tasks/components/subtask-success-page/subtask-success-page.component.scss
@@ -0,0 +1,38 @@
+.subtask-success-page {
+  display: grid;
+  place-items: center;
+  min-height: min(70vh, 38rem);
+  padding: 1.25rem;
+}
+
+.subtask-success-page__card {
+  width: min(34rem, 100%);
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 1.25rem;
+  box-shadow: var(--shadow-panel);
+}
+
+.subtask-success-page__card mat-card-content {
+  display: grid;
+  gap: 0.9rem;
+  text-align: center;
+  justify-items: center;
+  padding: 1.5rem;
+}
+
+.subtask-success-page__icon {
+  color: #2e7d32;
+  font-size: 2.25rem;
+  width: 2.25rem;
+  height: 2.25rem;
+}
+
+.subtask-success-page__card h1 {
+  margin: 0;
+  font-size: 1.35rem;
+}
+
+.subtask-success-page__card p {
+  margin: 0;
+  color: var(--text-secondary);
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/subtask-success-page/subtask-success-page.component.ts`
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
+++ b/microtv-crm-frontend/src/app/features/tasks/components/subtask-success-page/subtask-success-page.component.ts
@@ -0,0 +1,51 @@
+import { CommonModule } from '@angular/common';
+import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
+import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
+import { ActivatedRoute, Router } from '@angular/router';
+import { interval, timer } from 'rxjs';
+import { MatButtonModule } from '@angular/material/button';
+import { MatCardModule } from '@angular/material/card';
+import { MatIconModule } from '@angular/material/icon';
+
+@Component({
+  selector: 'app-subtask-success-page',
+  standalone: true,
+  imports: [CommonModule, MatButtonModule, MatCardModule, MatIconModule],
+  templateUrl: './subtask-success-page.component.html',
+  styleUrl: './subtask-success-page.component.scss',
+  changeDetection: ChangeDetectionStrategy.OnPush
+})
+export class SubtaskSuccessPageComponent {
+  private readonly activatedRoute = inject(ActivatedRoute);
+  private readonly router = inject(Router);
+  private readonly destroyRef = inject(DestroyRef);
+
+  readonly redirectInSeconds = signal(4);
+  readonly subtaskTitle = signal<string | null>(this.activatedRoute.snapshot.queryParamMap.get('subtask'));
+  readonly title = computed(() => {
+    const subtask = this.subtaskTitle()?.trim();
+    if (!subtask) {
+      return 'Subtarea completada con exito';
+    }
+    return `Subtarea completada: ${subtask}`;
+  });
+
+  constructor() {
+    const totalSeconds = this.redirectInSeconds();
+
+    interval(1000)
+      .pipe(takeUntilDestroyed(this.destroyRef))
+      .subscribe((tick) => {
+        const remaining = totalSeconds - (tick + 1);
+        this.redirectInSeconds.set(Math.max(0, remaining));
+      });
+
+    timer(totalSeconds * 1000)
+      .pipe(takeUntilDestroyed(this.destroyRef))
+      .subscribe(() => this.goToTasks());
+  }
+
+  goToTasks(): void {
+    this.router.navigate(['/tasks']);
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.html
+++ b/microtv-crm-frontend/src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.html
@@ -6,28 +6,28 @@
 
   <mat-card-content>
     <div class="task-attachments-section__actions">
-      <input
-        #fileInput
-        type="file"
-        [accept]="acceptAttribute"
-        multiple
-        hidden
-        [disabled]="disabled() || isUploading()"
-        (change)="onFileSelection($event)"
-      />
+      @if (!disabled()) {
+        <input
+          #fileInput
+          type="file"
+          [accept]="acceptAttribute"
+          multiple
+          hidden
+          [disabled]="isUploading()"
+          (change)="onFileSelection($event)"
+        />
 
-      <button mat-stroked-button type="button" [disabled]="disabled() || isUploading()" (click)="fileInput.click()">
-        <mat-icon>upload_file</mat-icon>
-        <span>{{ isUploading() ? 'Subiendo multimedia...' : 'Agregar fotos o videos' }}</span>
-      </button>
+        <button mat-stroked-button type="button" [disabled]="isUploading()" (click)="fileInput.click()">
+          <mat-icon>upload_file</mat-icon>
+          <span>{{ isUploading() ? 'Subiendo multimedia...' : 'Agregar fotos o videos' }}</span>
+        </button>
 
-      <p class="task-attachments-section__hint">
-        @if (disabled()) {
-          Tarea finalizada: los adjuntos quedan solo en lectura.
-        } @else {
-          La clasificación y validación se resuelven en la fachada, y el archivo queda persistido en el backend al subirlo.
-        }
-      </p>
+        <p class="task-attachments-section__hint">
+          La clasificacion y validacion se resuelven en la fachada, y el archivo queda persistido en el backend al subirlo.
+        </p>
+      } @else {
+        <p class="task-attachments-section__hint">Modo lectura: visualizando multimedia registrada para esta subtarea.</p>
+      }
     </div>
 
     @if (uploadError(); as uploadError) {
@@ -39,11 +39,11 @@
         @for (att
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.ts
+++ b/microtv-crm-frontend/src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.ts
@@ -5,6 +5,7 @@ import { MatButtonModule } from '@angular/material/button';
 import { MatCardModule } from '@angular/material/card';
 import { MatIconModule } from '@angular/material/icon';
 
+import { crmApiConfig } from '../../../../core/config/crm-api.config';
 import { TaskAttachment } from '../../../../core/models/task-attachment.model';
 import { MediaUploadFacade } from '../../../../shared/facades/media-upload.facade';
 
@@ -17,6 +18,8 @@ import { MediaUploadFacade } from '../../../../shared/facades/media-upload.facad
 })
 export class TaskAttachmentsSectionComponent {
   private readonly mediaUploadFacade = inject(MediaUploadFacade);
+  private readonly backendOrigin = this.resolveBackendOrigin();
+  readonly failedPreviewAttachmentIds = signal<Set<string>>(new Set());
 
   readonly taskId = input.required<string>();
   readonly subtaskId = input<string | null>(null);
@@ -63,6 +66,14 @@ export class TaskAttachmentsSectionComponent {
     this.attachmentRemoved.emit(attachmentId);
   }
 
+  markPreviewAsFailed(attachmentId: string): void {
+    this.failedPreviewAttachmentIds.update((current) => {
+      const next = new Set(current);
+      next.add(attachmentId);
+      return next;
+    });
+  }
+
   trackByAttachmentId(_: number, attachment: TaskAttachment): string {
     return attachment.id;
   }
@@ -96,6 +107,40 @@ export class TaskAttachmentsSectionComponent {
   }
 
   canPreview(attachment: TaskAttachment): boolean {
-    return Boolean(attachment.previewUrl && (attachment.kind === 'image' || attachment.kind === 'video'));
+    if (this.failedPreviewAttachmentIds().has(attachment.id)) {
+      return false;
+    }
+
+    return Boolean(this.previewUrl(attachment) && (attachment.kind === 'image' || attachment.kind === 'video'));
+  }
+
+  previewUrl(attachment: TaskAttachment): string | null {
+    return this.toAbsoluteUrl(attachm
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.html
+++ b/microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.html
@@ -13,15 +13,16 @@
         <p>Cargando tarea real...</p>
       </mat-card-content>
     </mat-card>
-  } @else if (errorMessage(); as errorMessage) {
-    <mat-card class="task-execution-page__empty-card">
-      <mat-card-content>
-        <mat-icon>error</mat-icon>
-        <h2>Tarea no disponible</h2>
-        <p>{{ errorMessage }}</p>
-      </mat-card-content>
-    </mat-card>
   } @else if (task(); as task) {
+    @if (pageError(); as pageError) {
+      <mat-card class="task-execution-page__flash task-execution-page__flash--error">
+        <mat-card-content>
+          <mat-icon>error</mat-icon>
+          <p>{{ pageError }}</p>
+        </mat-card-content>
+      </mat-card>
+    }
+
     <div class="task-execution-page__header">
       <app-page-title
         eyebrow="Ejecución de tarea"
@@ -30,15 +31,58 @@
       />
 
       <div class="task-execution-page__header-side">
-        <app-status-badge [label]="formatTaskStatus(task.status)" [tone]="toTaskTone(task.status)" />
-
-        <div class="task-execution-page__assignee">
+        <app-status-badge [label]="taskExecutionStatusLabel(task)" [tone]="toTaskTone(task.status)" />
+
+        <div
+          class="task-execution-page__assignee"
+          [class.task-execution-page__assignee--action]="canOpenHeaderAssigneeMenu()"
+          [matMenuTriggerFor]="canOpenHeaderAssigneeMenu() ? assigneeMenu : null"
+          #assigneeMenuTrigger="matMenuTrigger"
+          (menuOpened)="prepareHeaderAssigneeMenu()"
+        >
           <app-user-avatar [initials]="buildInitials(task.current_assigned_user_display_name, 'NA')" [size]="40" />
           <div>
             <p class="task-execution-page__meta-label">Asignado a</p>
             <p class="task-execution-page__meta-value">{{ task.current_assigned_user_display_name || 'Sin usuario asignado' }}</p>
           </div>
+          @if (canOpenHeaderA
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.scss
+++ b/microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.scss
@@ -4,6 +4,38 @@
   min-width: 0;
 }
 
+.task-execution-page__mobile-collapse {
+  display: grid;
+  gap: 1rem;
+}
+
+.task-execution-page__mobile-collapse-summary {
+  display: none;
+}
+
+.task-execution-page__mobile-collapse--interactive {
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 1rem;
+  padding: 0.5rem;
+  background: rgba(255, 255, 255, 0.9);
+}
+
+.task-execution-page__mobile-collapse--interactive .task-execution-page__mobile-collapse-summary {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 0.75rem;
+  list-style: none;
+  cursor: pointer;
+  padding: 0.65rem 0.75rem;
+  font-weight: 700;
+  color: var(--text-primary);
+}
+
+.task-execution-page__mobile-collapse--interactive .task-execution-page__mobile-collapse-summary::-webkit-details-marker {
+  display: none;
+}
+
 .task-execution-page__topbar,
 .task-execution-page__header,
 .task-execution-page__assignee,
@@ -49,6 +81,34 @@
   gap: 0.8rem;
 }
 
+.task-execution-page__assignee--action {
+  padding: 0.45rem 0.7rem;
+  border-radius: 999px;
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  cursor: pointer;
+  transition: background-color 0.15s ease;
+}
+
+.task-execution-page__assignee--action:hover {
+  background: rgba(23, 24, 26, 0.04);
+}
+
+.task-execution-page__assignee-caret {
+  color: var(--text-secondary);
+}
+
+.task-execution-page__assignee-menu {
+  display: grid;
+  gap: 0.75rem;
+  width: min(24rem, 82vw);
+  padding: 0.35rem 0.25rem 0.2rem;
+}
+
+.task-execution-page__assignee-menu-actions {
+  display: flex;
+  justify-content: flex-end;
+}
+
 .task-execution-page__meta-label,
 .task-execution-page__meta-value,
 .task-execution-page__summary-label,
@@ -270,6 +330,12 @@
   font-weight: 700;
 }
 
+.task-execution-page__task-close-actions {
+  display: flex;
+  justify-content: flex-end;
+  padding-bottom: 0.2rem;
+}
+
 .task-execut
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/tasks/components/task-execution-page/task-execution-page.component.ts
@@ -1,22 +1,24 @@
 import { DatePipe } from '@angular/common';
 import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
 import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
-import { ActivatedRoute, RouterLink } from '@angular/router';
+import { ActivatedRoute, Router, RouterLink } from '@angular/router';
 import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
-import { finalize } from 'rxjs';
+import { finalize, forkJoin, switchMap } from 'rxjs';
 import { MatButtonModule } from '@angular/material/button';
 import { MatCardModule } from '@angular/material/card';
 import { MatCheckboxModule } from '@angular/material/checkbox';
 import { MatIconModule } from '@angular/material/icon';
 import { MatFormFieldModule } from '@angular/material/form-field';
 import { MatInputModule } from '@angular/material/input';
-import { MatMenuModule } from '@angular/material/menu';
+import { MatMenuModule, MatMenuTrigger } from '@angular/material/menu';
 import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
 import { MatSelectModule } from '@angular/material/select';
+import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
 
 import {
-  CreateTaskDispatchRequest,
+  InventoryDispatchItemWriteRequest,
   InventoryDispatchItem,
+  formatInventoryRequestStatus,
   InventoryRequest,
   InventoryRequestItemWriteRequest,
   RequiredMaterial
@@ -48,6 +50,16 @@ import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.
 import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
 import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';
 
+type DispatchIdentifierType = 'none' | 'serial' | 'barcode';
+
+type DispatchDraftItem = InventoryDispatchItemWriteRe
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.html
+++ b/microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.html
@@ -7,12 +7,12 @@
     />
 
     <div class="tasks-page__actions">
-      <a mat-stroked-button type="button" class="tasks-page__action tasks-page__action--secondary" routerLink="/tasks/templates">
-        <mat-icon>schema</mat-icon>
-        <span>Templates</span>
-      </a>
+      @if (isAdmin()) {
+        <a mat-stroked-button type="button" class="tasks-page__action tasks-page__action--secondary" routerLink="/tasks/templates">
+          <mat-icon>schema</mat-icon>
+          <span>Templates</span>
+        </a>
 
-      @if (isAdminOrExecutive()) {
         <a mat-flat-button color="primary" type="button" class="tasks-page__action" routerLink="/tasks/templates/new">
           <mat-icon>add_box</mat-icon>
           <span>Nuevo template</span>
@@ -145,19 +145,34 @@
       </mat-card-content>
     </mat-card>
   } @else {
-    <mat-tab-group>
-      <mat-tab label="Asignadas a mí">
+    <mat-tab-group class="tasks-page__tabs" [selectedIndex]="initialTabIndex()" [dynamicHeight]="isHandset()" [mat-stretch-tabs]="!isHandset()">
+      <mat-tab [label]="isHandset() ? 'Asignadas' : 'Asignadas a mí'">
         <div class="tasks-page__tab-content">
-          @if (!assignedTasks().length) {
+          <app-listing-controls
+            [searchValue]="listState('assigned').search"
+            searchPlaceholder="Buscar por id, cliente o titulo"
+            [selectedStatus]="listState('assigned').status"
+            [statusOptions]="taskStatusOptions"
+            [sortDirection]="listState('assigned').sortDirection"
+            [viewMode]="listState('assigned').viewMode"
+            (searchChanged)="onListSearchChanged('assigned', $event)"
+            (statusChanged)="onListStatusChanged('assigned', $event)"
+            (sortDirectionChanged)="onListSortDirectionChanged('assigned', $event)"
+            (viewModeChanged)="onListViewModeChanged('assigned', $event)"
+          />
+
+          @if
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.scss
+++ b/microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.scss
@@ -45,6 +45,11 @@
   box-shadow: var(--shadow-panel);
 }
 
+.tasks-page__task-card--highlighted {
+  border-color: rgba(46, 125, 50, 0.45);
+  box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.2), var(--shadow-panel);
+}
+
 .tasks-page__message mat-card-content,
 .tasks-page__task-top,
 .tasks-page__create-actions {
@@ -90,9 +95,17 @@
 .tasks-page__task-grid {
   display: grid;
   gap: 1rem;
+  min-width: 0;
+}
+
+.tasks-page__tab-content {
   margin-top: 1rem;
 }
 
+.tasks-page__tabs {
+  min-width: 0;
+}
+
 .tasks-page__task-grid {
   grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
 }
@@ -104,6 +117,10 @@
   color: var(--text-secondary);
 }
 
+.tasks-page__task-meta span {
+  overflow-wrap: anywhere;
+}
+
 .tasks-page__template-materials {
   padding: 1rem;
   border-radius: 1rem;
@@ -194,6 +211,10 @@
     gap: 1rem;
   }
 
+  .tasks-page__header {
+    gap: 0.75rem;
+  }
+
   .tasks-page__actions {
     display: grid;
     grid-template-columns: 1fr;
@@ -208,4 +229,17 @@
     flex-direction: column;
     align-items: stretch;
   }
+
+  .tasks-page__task-grid {
+    grid-template-columns: 1fr;
+  }
+
+  .tasks-page__task-card mat-card-actions {
+    justify-content: stretch;
+  }
+
+  .tasks-page__task-card mat-card-actions a,
+  .tasks-page__task-card mat-card-actions button {
+    width: 100%;
+  }
 }
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/tasks/components/tasks-page/tasks-page.component.ts
@@ -1,7 +1,10 @@
 import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
-import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
-import { Router, RouterLink } from '@angular/router';
+import { DatePipe } from '@angular/common';
+import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
+import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
+import { ActivatedRoute, Router, RouterLink } from '@angular/router';
 import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
+import { map } from 'rxjs';
 import { MatButtonModule } from '@angular/material/button';
 import { MatCardModule } from '@angular/material/card';
 import { MatFormFieldModule } from '@angular/material/form-field';
@@ -14,6 +17,7 @@ import { MatTabsModule } from '@angular/material/tabs';
 import { AuthSessionService } from '../../../../core/services/auth-session.service';
 import { AppLocation } from '../../../../core/models/location.model';
 import {
+  buildInitials,
   ClientSummary,
   countCompletedSubtasks,
   formatRoleKey,
@@ -24,17 +28,31 @@ import {
   toTaskTone,
   UnassignedSubtaskQueueItem
 } from '../../../../core/models/task-management.model';
+import { TaskListItem, TasksTableData } from '../../../../core/models/task.model';
 import { TaskManagementService } from '../../../../core/services/task-management.service';
+import { ListingViewMode, ListingViewPreferenceService } from '../../../../shared/services/listing-view-preference.service';
+import { ListingControlsComponent, ListingSortDirection, ListingStatusOption } from '../../../../shared/ui/listing-controls/listing-controls.component';
 import { LocationPickerService } from '../../../../shared/services/location-picker.service';
 import { LocationLinkService } from '../../../../shared/services/location-link.service';
 import { LocationMapComponent } from 
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.html
+++ b/microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.html
@@ -1,4 +1,4 @@
-<mat-card class="tasks-table">
+<mat-card class="tasks-table" [class.tasks-table--force-table]="viewMode() === 'table'" [class.tasks-table--force-cards]="viewMode() === 'cards'">
   <mat-card-header>
     <mat-card-title>{{ block().title }}</mat-card-title>
   </mat-card-header>
@@ -15,10 +15,24 @@
           <th mat-header-cell *matHeaderCellDef>{{ labelFor('title') }}</th>
           <td mat-cell *matCellDef="let task">
             <div class="tasks-table__title">{{ task.title }}</div>
-            <a mat-button class="tasks-table__open-link" [routerLink]="['/tasks', task.id]">
-              <span>Ver ejecución</span>
-              <mat-icon>arrow_forward</mat-icon>
-            </a>
+            <div class="tasks-table__row-actions">
+              @if (task.rowActionLabel && task.rowActionId) {
+                <button
+                  mat-button
+                  class="tasks-table__open-link"
+                  type="button"
+                  [disabled]="task.rowActionDisabled"
+                  (click)="triggerRowAction(task.rowActionId)"
+                >
+                  <span>{{ task.rowActionLabel }}</span>
+                  <mat-icon>arrow_forward</mat-icon>
+                </button>
+              }
+              <a mat-button class="tasks-table__open-link" [routerLink]="openTaskRoute(task.routeTaskId || task.id)">
+                <span>Ver ejecución</span>
+                <mat-icon>arrow_forward</mat-icon>
+              </a>
+            </div>
           </td>
         </ng-container>
 
@@ -99,7 +113,19 @@
             </div>
           </div>
 
-          <a mat-stroked-button class="tasks-table__mobile-action" [routerLink]="['/tasks', task.id]">
+          @if (task.rowActionLabel && task.rowActionId) {
+            <button
+              mat-stroked-button
+              class="tasks-table__mobile-action"
+              type="button"
+        
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.scss
+++ b/microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.scss
@@ -23,6 +23,31 @@
   display: none;
 }
 
+.tasks-table--force-table .tasks-table__desktop-scroll {
+  display: block;
+}
+
+.tasks-table--force-table .tasks-table__mobile-list {
+  display: none;
+}
+
+.tasks-table--force-cards .tasks-table__desktop-scroll {
+  display: none;
+}
+
+.tasks-table--force-cards .tasks-table__mobile-list {
+  display: grid;
+  grid-template-columns: repeat(3, minmax(0, 18.5rem));
+  justify-content: center;
+  gap: 0.85rem;
+}
+
+@media (max-width: 1240px) {
+  .tasks-table--force-cards .tasks-table__mobile-list {
+    grid-template-columns: repeat(2, minmax(0, 18.5rem));
+  }
+}
+
 .tasks-table__table {
   width: 100%;
   min-width: 860px;
@@ -32,6 +57,13 @@
   font-weight: 700;
 }
 
+.tasks-table__row-actions {
+  display: flex;
+  align-items: center;
+  gap: 0.35rem;
+  flex-wrap: wrap;
+}
+
 .tasks-table__open-link {
   min-width: 0;
   margin-top: 0.25rem;
@@ -94,10 +126,6 @@ td.mat-mdc-cell {
   background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 249, 251, 0.92));
 }
 
-.tasks-table__mobile-card + .tasks-table__mobile-card {
-  margin-top: 0.9rem;
-}
-
 .tasks-table__mobile-top {
   display: flex;
   align-items: flex-start;
@@ -169,9 +197,29 @@ td.mat-mdc-cell {
   }
 
   .tasks-table__mobile-list {
+    display: grid;
+    grid-template-columns: 1fr;
+    gap: 0.85rem;
+  }
+
+  .tasks-table--force-table .tasks-table__desktop-scroll {
     display: block;
   }
 
+  .tasks-table--force-table .tasks-table__mobile-list {
+    display: none;
+  }
+
+  .tasks-table--force-cards .tasks-table__desktop-scroll {
+    display: none;
+  }
+
+  .tasks-table--force-cards .tasks-table__mobile-list {
+    display: grid;
+    grid-template-columns: 1fr;
+    gap: 0.85rem;
+  }
+
   .tasks-table__mobile-grid {
     grid-template-columns: 1fr;
   }
```

#### 📄 `microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.ts
+++ b/microtv-crm-frontend/src/app/features/tasks/components/tasks-table/tasks-table.component.ts
@@ -6,6 +6,7 @@ import { MatIconModule } from '@angular/material/icon';
 import { MatTableModule } from '@angular/material/table';
 
 import { TasksTableData } from '../../../../core/models/task.model';
+import { ListingViewMode } from '../../../../shared/services/listing-view-preference.service';
 import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
 import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';
 
@@ -18,6 +19,8 @@ import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avat
 })
 export class TasksTableComponent {
   readonly block = input.required<TasksTableData>();
+  readonly viewMode = input<ListingViewMode>('table');
+  readonly rowActionRequested = input<((rowActionId: string) => void) | null>(null);
 
   readonly displayedColumns: Array<'id' | 'title' | 'client' | 'subtasks' | 'status' | 'assignedTo'> = [
     'id',
@@ -39,4 +42,16 @@ export class TasksTableComponent {
 
     return Math.round((completed / total) * 100);
   }
+
+  openTaskRoute(taskId: string | undefined): any[] {
+    return ['/tasks', taskId ?? ''];
+  }
+
+  triggerRowAction(rowActionId: string | undefined): void {
+    if (!rowActionId || !this.rowActionRequested()) {
+      return;
+    }
+
+    this.rowActionRequested()?.(rowActionId);
+  }
 }
\ No newline at end of file
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.html
@@ -1,81 +1,139 @@
 <h2 mat-dialog-title>Crear ticket</h2>
 
 <mat-dialog-content>
-  @if (viewModel$ | async; as viewModel) {
+  @if (isLoading()) {
+    <div class="create-ticket-dialog__loading">
+      <mat-spinner diameter="36" />
+      <p>Cargando datos para crear ticket...</p>
+    </div>
+  } @else {
     <form class="create-ticket-dialog__form" [formGroup]="form" (ngSubmit)="submit()">
       <section class="create-ticket-dialog__intro">
         <p class="create-ticket-dialog__intro-title">Registro inicial de incidencia</p>
         <p class="create-ticket-dialog__intro-copy">
-          Documenta el problema reportado, el equipo afectado y los insumos previstos para resolverlo.
+          Define cliente, ubicación real, prioridad y asignación para iniciar el flujo operativo.
         </p>
       </section>
 
+      @if (errorMessage(); as errorMessage) {
+        <p class="create-ticket-dialog__error">{{ errorMessage }}</p>
+      }
+
       <div class="create-ticket-dialog__fields">
         <mat-form-field appearance="outline" subscriptSizing="dynamic">
-          <mat-label>Titulo</mat-label>
-          <input matInput formControlName="title" placeholder="Ej. Sin imagen en monitor de recepcion" />
+          <mat-label>Título</mat-label>
+          <input matInput formControlName="title" placeholder="Ej. Sin imagen en monitor de recepción" />
           @if (form.controls.title.hasError('required') && form.controls.title.touched) {
-            <mat-error>El titulo es obligatorio.</mat-error>
+            <mat-error>El título es obligatorio.</mat-error>
           }
         </mat-form-field>
 
         <mat-form-field appearance="outline" subscriptSizing="dynamic">
-          <mat-label>Categoria</mat-label>
-          <mat-select formControlName="categoryId">
-            @for (category of viewModel.categories; track category.id) {
-     
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.scss
+++ b/microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.scss
@@ -9,6 +9,19 @@
   padding-top: 0.25rem;
 }
 
+.create-ticket-dialog__loading {
+  display: grid;
+  justify-items: center;
+  gap: 0.7rem;
+  padding: 2rem 1rem;
+}
+
+.create-ticket-dialog__loading p {
+  margin: 0;
+  color: var(--text-secondary);
+  font-weight: 600;
+}
+
 .create-ticket-dialog__intro {
   padding: 1rem 1.1rem;
   border: 1px solid rgba(23, 24, 26, 0.08);
@@ -39,19 +52,18 @@
   gap: 1rem;
 }
 
-.create-ticket-dialog__description-field,
-.create-ticket-dialog__device-field {
+.create-ticket-dialog__description-field {
   grid-column: 1 / -1;
 }
 
-.create-ticket-dialog__device-option {
-  display: grid;
-  gap: 0.18rem;
-}
-
-.create-ticket-dialog__device-option small {
-  color: var(--text-secondary);
-  font-size: 0.78rem;
+.create-ticket-dialog__error {
+  margin: 0;
+  padding: 0.8rem 0.95rem;
+  border-radius: 0.85rem;
+  border: 1px solid rgba(183, 28, 28, 0.25);
+  background: rgba(183, 28, 28, 0.08);
+  color: #8b1a1a;
+  font-size: 0.9rem;
   font-weight: 600;
 }
 
@@ -62,6 +74,51 @@
   background: rgba(250, 250, 251, 0.96);
 }
 
+.create-ticket-dialog__section-title,
+.create-ticket-dialog__location-label {
+  margin: 0;
+}
+
+.create-ticket-dialog__section-title {
+  font-size: 0.86rem;
+  font-weight: 800;
+  letter-spacing: 0.06em;
+  text-transform: uppercase;
+  color: var(--text-secondary);
+}
+
+.create-ticket-dialog__location-modes {
+  display: flex;
+  flex-wrap: wrap;
+  gap: 0.6rem;
+  margin-top: 0.75rem;
+}
+
+.create-ticket-dialog__mode--active {
+  border-color: rgba(183, 28, 28, 0.45);
+  background: rgba(183, 28, 28, 0.08);
+}
+
+.create-ticket-dialog__location-actions {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: center;
+  gap: 0.45rem;
+  margin-top: 0.85rem;
+}
+
+.create-ticket-dialog__location-actions mat-icon {
+  margin-right: 0.25rem;
+}
+
+.create-ticket-dialog__location-label {
+  margi
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.ts
@@ -1,24 +1,32 @@
-import { AsyncPipe } from '@angular/common';
-import { Component, inject } from '@angular/core';
+import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
+import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
 import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
-import { combineLatest, map } from 'rxjs';
 import { MatButtonModule } from '@angular/material/button';
 import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
 import { MatFormFieldModule } from '@angular/material/form-field';
+import { MatIconModule } from '@angular/material/icon';
 import { MatInputModule } from '@angular/material/input';
+import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
 import { MatSelectModule } from '@angular/material/select';
 
-import { CreateTicketFormValue } from '../../../../core/models/create-ticket.model';
-import { RequiredInventoryItem } from '../../../../core/models/inventory-item.model';
-import { MockTicketsService } from '../../../../core/services/mock-tickets.service';
-import { CreateTicketFormGroup, CreateTicketFormModel, RequiredInventoryItemFormGroup } from '../create-ticket-form.types';
-import { RequiredItemsEditorComponent } from '../required-items-editor/required-items-editor.component';
+import { AppLocation } from '../../../../core/models/location.model';
+import { CrmUserOption } from '../../../../core/models/task-management.model';
+import { CreateTicketRequest, TicketClientOption, TicketDetail, TicketPriority, TicketRoleOption } from '../../../../core/models/ticket-management.model';
+import { TicketManagementService } from '../../../../core/services/ticket-management.service';
+import { LocationLinkService } from '../../../../shar
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-attachments-section/ticket-attachments-section.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-attachments-section/ticket-attachments-section.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-attachments-section/ticket-attachments-section.component.html
@@ -3,7 +3,7 @@
     <mat-card-title>Adjuntos del ticket</mat-card-title>
     <mat-card-subtitle>
       @if (canEdit()) {
-        Fotos y videos del diagnóstico técnico. El binario real no se persiste; la metadata sí.
+        Fotos y videos del diagnóstico técnico persistidos en backend.
       } @else {
         Evidencia visual cargada en el ticket. Visible para seguimiento cruzado entre técnico, depósito y admin.
       }
@@ -13,14 +13,14 @@
   <mat-card-content>
     @if (canEdit()) {
       <div class="ticket-attachments-section__actions">
-        <input #fileInput type="file" accept="image/*,video/*" multiple hidden (change)="onFileSelection($event)" />
+        <input #fileInput type="file" accept="image/*,video/*" capture="environment" multiple hidden (change)="onFileSelection($event)" />
 
         <button mat-stroked-button type="button" (click)="fileInput.click()">
           <mat-icon>upload_file</mat-icon>
           <span>Agregar fotos o videos</span>
         </button>
 
-        <p class="ticket-attachments-section__hint">La preview completa dura durante la sesión activa del navegador.</p>
+        <p class="ticket-attachments-section__hint">Los archivos quedan disponibles para comentarios, transiciones y cierre del ticket.</p>
       </div>
     }
 
@@ -52,10 +52,6 @@
                 </button>
               }
             </div>
-
-            @if (!attachment.previewUrl && (attachment.kind === 'image' || attachment.kind === 'video')) {
-              <p class="ticket-attachments-section__preview-note">La preview no se conserva luego de recargar. La metadata del archivo sí.</p>
-            }
           </article>
         }
       </div>
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.html
@@ -1,47 +1,70 @@
 <mat-card class="ticket-description-section">
-  <mat-card-header>
-    <mat-card-title>Descripción del ticket</mat-card-title>
-    <mat-card-subtitle>Información base del problema reportado y del contexto operativo asociado.</mat-card-subtitle>
-  </mat-card-header>
-
   <mat-card-content>
-    <p class="ticket-description-section__body">{{ ticket().description }}</p>
+    <section class="ticket-description-section__ticket-number">
+      <p class="ticket-description-section__label">Ticket</p>
+      <p class="ticket-description-section__ticket-value">{{ ticket().ticket_number }}</p>
+    </section>
 
-    <div class="ticket-description-section__grid">
-      <div class="ticket-description-section__item">
-        <p class="ticket-description-section__label">Categoría</p>
-        <p class="ticket-description-section__value">{{ ticket().category }}</p>
-      </div>
+    <section class="ticket-description-section__description-highlight">
+      <p class="ticket-description-section__label">Descripción</p>
+      <p class="ticket-description-section__body">{{ ticket().description }}</p>
+    </section>
 
+    <div class="ticket-description-section__grid">
       <div class="ticket-description-section__item">
-        <p class="ticket-description-section__label">Dispositivo afectado</p>
-        <p class="ticket-description-section__value">{{ ticket().affectedDevice }}</p>
+        <p class="ticket-description-section__label">Cliente</p>
+        <p class="ticket-description-section__value">{{ ticket().client_name }}</p>
       </div>
 
-      <div class="ticket-description-section__item">
+      <div class="ticket-description-section__item ticket-description-section__item--priority">
         <p class="ticket-description-section__label">Prioridad</p>
-        <app-priority-indicator [label]="ticket().priority" [t
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.scss
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.scss
@@ -4,25 +4,44 @@
   box-shadow: var(--shadow-panel);
 }
 
-.ticket-description-section mat-card-header,
 .ticket-description-section mat-card-content {
   padding-inline: 1.25rem;
 }
 
-.ticket-description-section mat-card-header {
-  padding-top: 1.15rem;
-}
-
 .ticket-description-section__body,
 .ticket-description-section__label,
 .ticket-description-section__value {
   margin: 0;
 }
 
+.ticket-description-section__ticket-number {
+  display: grid;
+  gap: 0.35rem;
+  margin-bottom: 0.85rem;
+}
+
+.ticket-description-section__ticket-value {
+  margin: 0;
+  font-size: 1.05rem;
+  font-weight: 800;
+  color: var(--text-primary);
+}
+
+.ticket-description-section__description-highlight {
+  display: grid;
+  gap: 0.65rem;
+  padding: 1.15rem 1.2rem;
+  border: 1px solid rgba(23, 24, 26, 0.12);
+  border-radius: 1rem;
+  background: #ffffff;
+  box-shadow: 0 6px 20px rgba(23, 24, 26, 0.06);
+}
+
 .ticket-description-section__body {
   color: var(--text-primary);
-  font-size: 0.95rem;
-  line-height: 1.65;
+  font-size: 1.12rem;
+  line-height: 1.8;
+  font-weight: 700;
 }
 
 .ticket-description-section__grid {
@@ -41,6 +60,15 @@
   background: rgba(255, 255, 255, 0.82);
 }
 
+.ticket-description-section__item--priority {
+  border-color: rgba(198, 40, 40, 0.24);
+}
+
+.ticket-description-section__item--priority app-priority-indicator {
+  transform: scale(1.06);
+  transform-origin: left center;
+}
+
 .ticket-description-section__item--wide {
   grid-column: 1 / -1;
 }
@@ -60,6 +88,41 @@
   color: var(--text-primary);
 }
 
+.ticket-description-section__location-block {
+  display: grid;
+  gap: 0.9rem;
+  margin-top: 1rem;
+}
+
+.ticket-description-section__location-title-row {
+  display: flex;
+  align-items: center;
+  justify-content: flex-start;
+}
+
+.ticket-description-section__location-map-wrap {
+  position: relative;
+}
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-description-section/ticket-description-section.component.ts
@@ -1,18 +1,78 @@
 import { DatePipe } from '@angular/common';
-import { Component, input } from '@angular/core';
+import { Component, computed, inject, input } from '@angular/core';
 import { MatCardModule } from '@angular/material/card';
+import { MatButtonModule } from '@angular/material/button';
+import { MatIconModule } from '@angular/material/icon';
 
-import { TicketExecutionItem } from '../../../../core/models/ticket-execution.model';
+import { formatTicketPriority, formatTicketStatus, TicketDetail } from '../../../../core/models/ticket-management.model';
+import { AppLocation, LocationMapMarker } from '../../../../core/models/location.model';
+import { LocationLinkService } from '../../../../shared/services/location-link.service';
+import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';
 import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
 import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
 
 @Component({
   selector: 'app-ticket-description-section',
   standalone: true,
-  imports: [DatePipe, MatCardModule, PriorityIndicatorComponent, StatusBadgeComponent],
+  imports: [DatePipe, MatButtonModule, MatCardModule, MatIconModule, LocationMapComponent, PriorityIndicatorComponent, StatusBadgeComponent],
   templateUrl: './ticket-description-section.component.html',
   styleUrl: './ticket-description-section.component.scss'
 })
 export class TicketDescriptionSectionComponent {
-  readonly ticket = input.required<TicketExecutionItem>();
+  private readonly locationLinkService = inject(LocationLinkService);
+
+  readonly ticket = input.required<TicketDetail>();
+
+  readonly formatTicketStatus = formatTicketStatus;
+  readonly formatTicketPriority = formatTicketPriority;
+
+  readonl
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-dispatch-section/ticket-dispatch-section.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-dispatch-section/ticket-dispatch-section.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-dispatch-section/ticket-dispatch-section.component.ts
@@ -40,11 +40,11 @@ export class TicketDispatchSectionComponent {
   });
 
   approvedRequestCount(): number {
-    return this.requests().filter((request) => request.status === 'approved').length;
+    return this.requests().filter((request) => request.status === 'approved_for_dispatch').length;
   }
 
   approvedRequests(): readonly TicketInventoryRequest[] {
-    return this.requests().filter((request) => request.status === 'approved');
+    return this.requests().filter((request) => request.status === 'approved_for_dispatch');
   }
 
   createDispatch(): void {
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html
@@ -1,118 +1,554 @@
-@if (viewModel$ | async; as viewModel) {
-  @if (viewModel.ticket; as ticket) {
-    <section class="ticket-execution-page">
-      <div class="ticket-execution-page__topbar">
-        <a mat-stroked-button routerLink="/tickets" class="ticket-execution-page__back-link">
-          <mat-icon>arrow_back</mat-icon>
-          <span>Volver al listado</span>
-        </a>
+<section class="ticket-execution-page">
+  <div class="ticket-execution-page__topbar">
+    <a mat-stroked-button routerLink="/tickets" class="ticket-execution-page__back-link">
+      <mat-icon>arrow_back</mat-icon>
+      <span>Volver al listado</span>
+    </a>
+  </div>
+
+  @if (errorMessage(); as errorMessage) {
+    <div class="ticket-execution-page__alert ticket-execution-page__alert--error">{{ errorMessage }}</div>
+  }
+
+  @if (successMessage(); as successMessage) {
+    <div class="ticket-execution-page__alert ticket-execution-page__alert--success">{{ successMessage }}</div>
+  }
+
+  @if (isLoading()) {
+    <div class="ticket-execution-page__loading">
+      <mat-spinner diameter="42" />
+      <p>Cargando ticket...</p>
+    </div>
+  } @else if (ticket(); as ticket) {
+    <div class="ticket-execution-page__header">
+      <app-page-title eyebrow="Ejecución de ticket" [title]="ticket.title" [subtitle]="'Ticket ' + ticket.ticket_number" />
+
+      <div class="ticket-execution-page__header-side">
+        <app-status-badge [label]="formatTicketStatus(ticket.status)" [tone]="toTicketStatusTone(ticket.status)" />
+
+        <div
+          class="ticket-execution-page__assignee"
+          [class.ticket-execution-page__assignee--action]="canOpenAssigneeMenu()"
+          [matMenuTriggerFor]="canOpenAssigneeMenu() ? assigneeMenu : null"
+          #assigneeMenuTrigger="matMenuTrigger"
+          (menuOpened)="prepareAssigneeMenu()"
+        >
+          <a
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.scss
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.scss
@@ -4,6 +4,25 @@
   min-width: 0;
 }
 
+.ticket-execution-page__alert {
+  padding: 0.8rem 1rem;
+  border-radius: 0.9rem;
+  font-size: 0.92rem;
+  font-weight: 600;
+}
+
+.ticket-execution-page__alert--error {
+  background: rgba(183, 28, 28, 0.08);
+  border: 1px solid rgba(183, 28, 28, 0.2);
+  color: #8b1a1a;
+}
+
+.ticket-execution-page__alert--success {
+  background: rgba(28, 123, 74, 0.08);
+  border: 1px solid rgba(28, 123, 74, 0.22);
+  color: #1f6a45;
+}
+
 .ticket-execution-page__topbar,
 .ticket-execution-page__header,
 .ticket-execution-page__assignee,
@@ -28,7 +47,6 @@
 }
 
 .ticket-execution-page__header-side,
-.ticket-execution-page__assignee-blocks,
 .ticket-execution-page__main-column,
 .ticket-execution-page__sidebar {
   display: grid;
@@ -39,15 +57,39 @@
   gap: 0.9rem;
 }
 
-.ticket-execution-page__assignee-blocks {
-  gap: 0.8rem;
-}
-
 .ticket-execution-page__assignee {
   align-items: center;
   gap: 0.8rem;
 }
 
+.ticket-execution-page__assignee--action {
+  padding: 0.45rem 0.7rem;
+  border-radius: 999px;
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  cursor: pointer;
+  transition: background-color 0.15s ease;
+}
+
+.ticket-execution-page__assignee--action:hover {
+  background: rgba(23, 24, 26, 0.04);
+}
+
+.ticket-execution-page__assignee-caret {
+  color: var(--text-secondary);
+}
+
+.ticket-execution-page__assignee-menu {
+  display: grid;
+  gap: 0.75rem;
+  width: min(24rem, 82vw);
+  padding: 0.35rem 0.25rem 0.2rem;
+}
+
+.ticket-execution-page__assignee-menu-actions {
+  display: flex;
+  justify-content: flex-end;
+}
+
 .ticket-execution-page__meta-label,
 .ticket-execution-page__meta-value,
 .ticket-execution-page__summary-label,
@@ -81,6 +123,46 @@
   grid-template-columns: repeat(3, minmax(0, 1fr));
 }
 
+.ticket-execution-page__unified-card {
+  border: 1px solid rgba(23, 24, 26, 0.06);
+  border-radius: 1.
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts
@@ -1,218 +1,1453 @@
-import { AsyncPipe, DatePipe } from '@angular/common';
-import { Component, inject } from '@angular/core';
-import { ActivatedRoute, RouterLink } from '@angular/router';
-import { BehaviorSubject, catchError, combineLatest, map, of, switchMap } from 'rxjs';
+import { DatePipe } from '@angular/common';
+import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
+import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
+import { ActivatedRoute, Router, RouterLink } from '@angular/router';
+import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
 import { MatButtonModule } from '@angular/material/button';
 import { MatCardModule } from '@angular/material/card';
+import { MatFormFieldModule } from '@angular/material/form-field';
 import { MatIconModule } from '@angular/material/icon';
+import { MatInputModule } from '@angular/material/input';
+import { MatMenuModule, MatMenuTrigger } from '@angular/material/menu';
+import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
+import { MatSelectModule } from '@angular/material/select';
+import { MatSnackBar } from '@angular/material/snack-bar';
+import { forkJoin } from 'rxjs';
 
-import { InventorySourceFlow } from '../../../../core/models/inventory-flow.model';
+import { CrmUserOption } from '../../../../core/models/task-management.model';
+import { InventoryProduct } from '../../../../core/models/inventory-product.model';
+import { AppLocation } from '../../../../core/models/location.model';
+import {
+  AssignTicketRequest,
+  buildTicketStatusTransitions,
+  formatTicketPriority,
+  formatTicketStatus,
+  TicketAttachment,
+  TicketDetail,
+  TicketStatusTransitionOption,
+  toTicketStatusTone,
+  UpdateTicketStatusRequest
+} from '../../../../core/models/ticket-management.model';
 import 
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-inventory-request-section/ticket-inventory-request-section.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-inventory-request-section/ticket-inventory-request-section.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-inventory-request-section/ticket-inventory-request-section.component.html
@@ -93,7 +93,7 @@
               <p class="ticket-inventory-request-section__decision-note">{{ request.depositDecisionComment }}</p>
             }
 
-            @if (canReviewRequests() && request.status === 'pending') {
+            @if (canReviewRequests() && request.status === 'pending_deposit_review') {
               <div class="ticket-inventory-request-section__decision-box">
                 <label [attr.for]="request.id + '-decision'">Comentario de decisión</label>
                 <textarea
@@ -105,7 +105,7 @@
 
                 <div class="ticket-inventory-request-section__decision-actions">
                   <button mat-stroked-button type="button" (click)="decideRequest(request.id, 'rejected')">Rechazar</button>
-                  <button mat-flat-button color="primary" type="button" (click)="decideRequest(request.id, 'approved')">Autorizar</button>
+                  <button mat-flat-button color="primary" type="button" (click)="decideRequest(request.id, 'approved_for_dispatch')">Autorizar</button>
                 </div>
               </div>
             }
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/ticket-inventory-request-section/ticket-inventory-request-section.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/ticket-inventory-request-section/ticket-inventory-request-section.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/ticket-inventory-request-section/ticket-inventory-request-section.component.ts
@@ -116,7 +116,7 @@ export class TicketInventoryRequestSectionComponent {
   }
 
   statusTone(status: TicketInventoryRequestStatus): 'neutral' | 'warning' | 'success' {
-    if (status === 'approved') {
+    if (status === 'approved_for_dispatch' || status === 'dispatched') {
       return 'success';
     }
 
@@ -128,15 +128,23 @@ export class TicketInventoryRequestSectionComponent {
   }
 
   statusLabel(status: TicketInventoryRequestStatus): string {
-    if (status === 'approved') {
-      return 'Autorizada';
+    if (status === 'approved_for_dispatch') {
+      return 'Aprobada para despacho';
+    }
+
+    if (status === 'dispatched') {
+      return 'Despachada';
     }
 
     if (status === 'rejected') {
       return 'Rechazada';
     }
 
-    return 'Pendiente';
+    if (status === 'cancelled') {
+      return 'Cancelada';
+    }
+
+    return 'Pendiente de depósito';
   }
 
   decisionComment(requestId: string): string {
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.html
@@ -1,25 +1,125 @@
-@if (ticketsPage$ | async; as ticketsPage) {
-  <section class="tickets-page">
-    <div class="tickets-page__header">
-      <app-page-title
-        eyebrow="Mesa operativa"
-        [title]="ticketsPage.pageTitle"
-        [subtitle]="ticketsPage.pageSubtitle"
-      />
-
-      <div class="tickets-page__actions">
-        <button mat-stroked-button type="button" class="tickets-page__action tickets-page__action--secondary">
-          <mat-icon>{{ ticketsPage.secondaryAction.icon }}</mat-icon>
-          <span>{{ ticketsPage.secondaryAction.label }}</span>
-        </button>
-
-        <button mat-flat-button color="primary" type="button" class="tickets-page__action" (click)="openCreateTicketDialog()">
-          <mat-icon>{{ ticketsPage.primaryAction.icon }}</mat-icon>
-          <span>{{ ticketsPage.primaryAction.label }}</span>
-        </button>
-      </div>
+<section class="tickets-page">
+  <div class="tickets-page__header">
+    <app-page-title
+      eyebrow="Mesa operativa"
+      title="Tickets"
+      subtitle="Operación real de tickets integrada con backend, inventario y permisos por rol."
+    />
+
+    <div class="tickets-page__actions">
+      <button mat-stroked-button type="button" class="tickets-page__action tickets-page__action--secondary" (click)="refresh()">
+        <mat-icon>refresh</mat-icon>
+        <span>Actualizar</span>
+      </button>
+
+      <button mat-flat-button color="primary" type="button" class="tickets-page__action" (click)="openCreateTicketDialog()">
+        <mat-icon>add_circle</mat-icon>
+        <span>Crear ticket</span>
+      </button>
+    </div>
+  </div>
+
+  @if (errorMessage(); as errorMessage) {
+    <div class="tickets-page__alert tickets-page__alert--error">{{ errorMessage }}</div>
+  }
+
+  @if (successMessage(); as successMessage) {
+    <div class="tickets-page__alert tickets-page__alert--success">{{ succe
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.scss
+++ b/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.scss
@@ -5,6 +5,25 @@
   min-width: 0;
 }
 
+.tickets-page__alert {
+  padding: 0.8rem 1rem;
+  border-radius: 0.9rem;
+  font-size: 0.92rem;
+  font-weight: 600;
+}
+
+.tickets-page__alert--error {
+  background: rgba(183, 28, 28, 0.08);
+  border: 1px solid rgba(183, 28, 28, 0.2);
+  color: #8b1a1a;
+}
+
+.tickets-page__alert--success {
+  background: rgba(28, 123, 74, 0.08);
+  border: 1px solid rgba(28, 123, 74, 0.22);
+  color: #1f6a45;
+}
+
 .tickets-page__header {
   display: flex;
   align-items: flex-end;
@@ -37,6 +56,32 @@
   border-color: rgba(23, 24, 26, 0.12);
 }
 
+.tickets-page__loading {
+  display: grid;
+  justify-items: center;
+  gap: 0.75rem;
+  padding: 2.2rem 1rem;
+  border: 1px solid rgba(23, 24, 26, 0.08);
+  border-radius: 1rem;
+  background: rgba(255, 255, 255, 0.75);
+}
+
+.tickets-page__loading p {
+  margin: 0;
+  color: var(--text-secondary);
+  font-weight: 600;
+}
+
+.tickets-page__tabs {
+  min-width: 0;
+}
+
+.tickets-page__tab-content {
+  display: grid;
+  gap: 0.9rem;
+  padding-top: 1rem;
+}
+
 @media (max-width: 900px) {
   .tickets-page__header {
     align-items: stretch;
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts
@@ -1,40 +1,365 @@
-import { AsyncPipe } from '@angular/common';
-import { Component, inject } from '@angular/core';
+import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
+import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
+import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
+import { Router } from '@angular/router';
+import { toSignal } from '@angular/core/rxjs-interop';
+import { map } from 'rxjs';
 import { MatButtonModule } from '@angular/material/button';
 import { MatDialog, MatDialogModule } from '@angular/material/dialog';
 import { MatIconModule } from '@angular/material/icon';
+import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
+import { MatTabsModule } from '@angular/material/tabs';
 
-import { CreateTicketFormValue } from '../../../../core/models/create-ticket.model';
-import { MockTicketsService } from '../../../../core/services/mock-tickets.service';
+import {
+  buildGoogleMapsUrlFromTicketLocation,
+  formatTicketPriority,
+  formatTicketStatus,
+  TicketDetail,
+  TicketSummary,
+  TicketTableItem,
+  toLocationLabel,
+  toTicketPriorityTone,
+  toTicketStatusTone
+} from '../../../../core/models/ticket-management.model';
+import { AuthSessionService } from '../../../../core/services/auth-session.service';
+import { TicketManagementService } from '../../../../core/services/ticket-management.service';
+import { ListingSortDirection, ListingStatusOption, ListingControlsComponent } from '../../../../shared/ui/listing-controls/listing-controls.component';
+import { ListingViewMode, ListingViewPreferenceService } from '../../../../shared/services/listing-view-preference.service';
 import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
 import { CreateTicketDialogComponent } from '../create-ticket-dialog/create-ticket-dialog.compon
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.html`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.html
+++ b/microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.html
@@ -1,35 +1,50 @@
-<mat-card class="tickets-table">
+<mat-card class="tickets-table" [class.tickets-table--force-table]="viewMode() === 'table'" [class.tickets-table--force-cards]="viewMode() === 'cards'">
   <mat-card-header>
-    <mat-card-title>{{ block().title }}</mat-card-title>
+    <mat-card-title>{{ title() }}</mat-card-title>
   </mat-card-header>
 
   <mat-card-content>
     <div class="tickets-table__desktop-scroll">
-      <table mat-table [dataSource]="block().items" class="tickets-table__table">
-        <ng-container matColumnDef="id">
-          <th mat-header-cell *matHeaderCellDef>{{ labelFor('id') }}</th>
-          <td mat-cell *matCellDef="let ticket">{{ ticket.id }}</td>
+      <table mat-table [dataSource]="items()" class="tickets-table__table">
+        <ng-container matColumnDef="ticketNumber">
+          <th mat-header-cell *matHeaderCellDef>{{ labelFor('ticketNumber') }}</th>
+          <td mat-cell *matCellDef="let ticket">{{ ticket.ticketNumber }}</td>
         </ng-container>
 
         <ng-container matColumnDef="title">
           <th mat-header-cell *matHeaderCellDef>{{ labelFor('title') }}</th>
           <td mat-cell *matCellDef="let ticket">
             <div class="tickets-table__title">{{ ticket.title }}</div>
-            <a mat-button class="tickets-table__open-link" [routerLink]="['/tickets', ticket.id]">
+            <a mat-button class="tickets-table__open-link" [routerLink]="['/tickets', ticket.ticketId]">
               <span>Ver ejecución</span>
               <mat-icon>arrow_forward</mat-icon>
             </a>
           </td>
         </ng-container>
 
-        <ng-container matColumnDef="category">
-          <th mat-header-cell *matHeaderCellDef>{{ labelFor('category') }}</th>
-          <td mat-cell *matCellDef="let ticket">{{ ticket.category }}</td>
+        <ng-container matColumnDef="client">
+          <th mat-header-cell *matH
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.scss`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.scss
+++ b/microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.scss
@@ -23,6 +23,31 @@
   display: none;
 }
 
+.tickets-table--force-table .tickets-table__desktop-scroll {
+  display: block;
+}
+
+.tickets-table--force-table .tickets-table__mobile-list {
+  display: none;
+}
+
+.tickets-table--force-cards .tickets-table__desktop-scroll {
+  display: none;
+}
+
+.tickets-table--force-cards .tickets-table__mobile-list {
+  display: grid;
+  grid-template-columns: repeat(3, minmax(0, 18.5rem));
+  justify-content: center;
+  gap: 0.85rem;
+}
+
+@media (max-width: 1240px) {
+  .tickets-table--force-cards .tickets-table__mobile-list {
+    grid-template-columns: repeat(2, minmax(0, 18.5rem));
+  }
+}
+
 .tickets-table__table {
   width: 100%;
   min-width: 980px;
@@ -53,6 +78,33 @@
   font-weight: 600;
 }
 
+.tickets-table__location-cell {
+  display: grid;
+  gap: 0.4rem;
+}
+
+.tickets-table__location-label {
+  font-weight: 600;
+}
+
+.tickets-table__maps-link,
+.tickets-table__assign-button {
+  width: fit-content;
+  min-height: 2rem;
+  font-size: 0.75rem;
+  font-weight: 700;
+}
+
+.tickets-table__maps-link--mobile,
+.tickets-table__assign-button--mobile {
+  margin-top: 0.45rem;
+}
+
+.tickets-table__unassigned-wrap {
+  display: grid;
+  gap: 0.45rem;
+}
+
 .tickets-table__unassigned {
   color: var(--text-secondary);
   font-weight: 600;
@@ -84,10 +136,6 @@ td.mat-mdc-cell {
   background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 249, 251, 0.92));
 }
 
-.tickets-table__mobile-card + .tickets-table__mobile-card {
-  margin-top: 0.9rem;
-}
-
 .tickets-table__mobile-top {
   display: flex;
   align-items: flex-start;
@@ -159,9 +207,29 @@ td.mat-mdc-cell {
   }
 
   .tickets-table__mobile-list {
+    display: grid;
+    grid-template-columns: 1fr;
+    gap: 0.85rem;
+  }
+
+  .tickets-table--force-table .tickets-table__desktop-scroll {
     display: block;
   }
 
+  .tickets-table--force-table .tickets-table__mobile-list {
+    
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.ts`
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

--- a/microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.ts
+++ b/microtv-crm-frontend/src/app/features/tickets/components/tickets-table/tickets-table.component.ts
@@ -1,11 +1,12 @@
-import { Component, input } from '@angular/core';
+import { Component, input, output } from '@angular/core';
 import { RouterLink } from '@angular/router';
 import { MatButtonModule } from '@angular/material/button';
 import { MatCardModule } from '@angular/material/card';
 import { MatIconModule } from '@angular/material/icon';
 import { MatTableModule } from '@angular/material/table';
 
-import { TicketsTableData } from '../../../../core/models/ticket.model';
+import { TicketTableItem } from '../../../../core/models/ticket-management.model';
+import { ListingViewMode } from '../../../../shared/services/listing-view-preference.service';
 import { PriorityIndicatorComponent } from '../../../../shared/ui/priority-indicator/priority-indicator.component';
 import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge.component';
 import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avatar.component';
@@ -18,24 +19,50 @@ import { UserAvatarComponent } from '../../../../shared/ui/user-avatar/user-avat
   styleUrl: './tickets-table.component.scss'
 })
 export class TicketsTableComponent {
-  readonly block = input.required<TicketsTableData>();
+  readonly title = input.required<string>();
+  readonly items = input.required<readonly TicketTableItem[]>();
+  readonly canSelfAssign = input(false);
+  readonly isAssigning = input(false);
+  readonly assigningTicketId = input<string | null>(null);
+  readonly viewMode = input<ListingViewMode>('table');
+  readonly selfAssignRequested = output<string>();
 
-  readonly displayedColumns: Array<'id' | 'title' | 'category' | 'affectedDevice' | 'status' | 'priority' | 'createdAt' | 'assignee'> = [
-    'id',
+  readonly displayedColumns: Array<'ticketNumber' | 'title' | 'client' | 'location' | 'status' | 'priority' | 'updatedAt' | 'assignedTo'> = [
+    'ticketNumber',
     'title',
-    
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/layout/components/app-shell/app-shell.component.scss`
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

--- a/microtv-crm-frontend/src/app/layout/components/app-shell/app-shell.component.scss
+++ b/microtv-crm-frontend/src/app/layout/components/app-shell/app-shell.component.scss
@@ -20,12 +20,14 @@
 .app-shell__content {
   min-height: 100dvh;
   min-width: 0;
+  overflow-x: clip;
 }
 
 .app-shell__main {
   width: 100%;
   min-width: 0;
   padding: 1.5rem;
+  overflow-x: clip;
 }
 
 @media (max-width: 959px) {
```

#### 📄 `microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.html`
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

--- a/microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.html
+++ b/microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.html
@@ -13,12 +13,51 @@
   </div>
 
   <div class="topbar__actions">
-    <button type="button" mat-icon-button class="topbar__icon-button topbar__icon-button--alert" aria-label="Notificaciones">
+    <button
+      type="button"
+      mat-icon-button
+      class="topbar__icon-button topbar__icon-button--notifications"
+      [class.topbar__icon-button--notifications-active]="((unreadCount$ | async) ?? 0) > 0"
+      aria-label="Notificaciones"
+      [matMenuTriggerFor]="notifPanel"
+      [matBadge]="(unreadCount$ | async) ?? 0"
+      [matBadgeHidden]="((unreadCount$ | async) ?? 0) === 0"
+      matBadgeColor="warn"
+      matBadgeSize="small"
+    >
       <mat-icon>notifications</mat-icon>
     </button>
 
+    <mat-menu #notifPanel="matMenu" class="notif-panel" xPosition="before" panelClass="topbar__notif-menu-panel">
+      <div class="notif-panel__header" (click)="$event.stopPropagation()">
+        <span class="notif-panel__heading">Notificaciones</span>
+        @if ((unreadCount$ | async) ?? 0) {
+          <button type="button" mat-button color="primary" class="notif-panel__mark-all" (click)="markAllRead()">
+            Marcar todas leídas
+          </button>
+        }
+      </div>
+      @if ((unreadNotifications$ | async)?.length === 0) {
+        <div class="notif-panel__empty" (click)="$event.stopPropagation()">Sin notificaciones</div>
+      }
+      @for (notif of unreadNotifications$ | async; track notif.notification_id) {
+        <button
+          mat-menu-item
+          class="notif-item"
+          [class.notif-item--unread]="!notif.is_read"
+          (click)="openNotification(notif)"
+        >
+          <div class="notif-item__content">
+            <span class="notif-item__title">{{ notif.title }}</span>
+            <span class="notif-item__body">{{ notif.body }}</span>
+            <span class="notif-item__time">{{ notif.created_at | date: 'dd/MM HH:mm' }}</span>
+          </div>
+        </butt
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.scss`
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

--- a/microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.scss
+++ b/microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.scss
@@ -5,6 +5,7 @@
 .topbar {
   display: flex;
   justify-content: space-between;
+  align-items: center;
   gap: 1rem;
   width: 100%;
   min-width: 0;
@@ -24,6 +25,7 @@
 }
 
 .topbar__leading {
+  flex: 1 1 auto;
   min-width: 0;
 }
 
@@ -46,6 +48,9 @@
 
 .topbar__title {
   margin-top: 0.15rem;
+  overflow: hidden;
+  text-overflow: ellipsis;
+  white-space: nowrap;
   font-size: 1.45rem;
   font-weight: 800;
   letter-spacing: -0.03em;
@@ -56,36 +61,101 @@
   background: rgba(23, 24, 26, 0.04);
 }
 
-.topbar__icon-button--alert::after {
-  content: '';
-  position: absolute;
-  top: 0.8rem;
-  right: 0.9rem;
-  width: 0.5rem;
-  height: 0.5rem;
-  border-radius: 50%;
-  background: var(--brand-red);
-  box-shadow: 0 0 0 3px rgba(183, 28, 28, 0.14);
+.topbar__icon-button--notifications {
+  position: relative;
+  background: rgba(23, 24, 26, 0.04);
+}
+
+.topbar__icon-button--notifications-active {
+  background: rgba(229, 57, 53, 0.14);
+  color: #b71c1c;
+}
+
+:host ::ng-deep .topbar__notif-menu-panel {
+  .mat-mdc-menu-content {
+    width: min(24rem, calc(100vw - 1rem));
+    max-height: min(70dvh, 32rem);
+    overflow-y: auto;
+    overflow-x: hidden;
+  }
+
+  .notif-panel__header {
+    position: sticky;
+    top: 0;
+    z-index: 1;
+    display: flex;
+    align-items: center;
+    justify-content: space-between;
+    gap: 0.6rem;
+    padding: 0.65rem 0.8rem;
+    background: #fff;
+    border-bottom: 1px solid rgba(23, 24, 26, 0.08);
+  }
+
+  .notif-panel__heading {
+    font-size: 0.85rem;
+    font-weight: 800;
+  }
+
+  .notif-panel__empty {
+    padding: 0.95rem 0.8rem;
+    color: var(--text-secondary);
+    font-size: 0.88rem;
+  }
+
+  .notif-item {
+    height: auto;
+    min-height: 0;
+    white-space: normal;
+    line-height: 1.3;
+    padding-top: 0.55rem;
+    padding-bottom: 0.55rem;
+  }
+
+  .notif-item__content {
+    display: grid;
+    gap: 0.2rem;
+  }
+
+  .notif-item__title {
+    font-size: 0
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.ts`
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

--- a/microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.ts
+++ b/microtv-crm-frontend/src/app/layout/components/topbar/topbar.component.ts
@@ -1,17 +1,63 @@
-import { Component, input, output } from '@angular/core';
+import { AsyncPipe, DatePipe } from '@angular/common';
+import { Component, inject, input, OnDestroy, OnInit, output } from '@angular/core';
+import { Router } from '@angular/router';
+import { map } from 'rxjs';
+import { MatBadgeModule } from '@angular/material/badge';
 import { MatButtonModule } from '@angular/material/button';
 import { MatIconModule } from '@angular/material/icon';
+import { MatMenuModule } from '@angular/material/menu';
 import { MatToolbarModule } from '@angular/material/toolbar';
+import { MatTooltipModule } from '@angular/material/tooltip';
+
+import { Notification } from '../../../core/models/notification.model';
+import { NotificationsService } from '../../../core/services/notifications.service';
 
 @Component({
   selector: 'app-topbar',
   standalone: true,
-  imports: [MatButtonModule, MatIconModule, MatToolbarModule],
+  imports: [AsyncPipe, DatePipe, MatBadgeModule, MatButtonModule, MatIconModule, MatMenuModule, MatToolbarModule, MatTooltipModule],
   templateUrl: './topbar.component.html',
   styleUrl: './topbar.component.scss'
 })
-export class TopbarComponent {
+export class TopbarComponent implements OnInit, OnDestroy {
   readonly title = input.required<string>();
   readonly showMenuButton = input(false);
   readonly menuToggle = output<void>();
-}
\ No newline at end of file
+
+  private readonly notificationsService = inject(NotificationsService);
+  private readonly router = inject(Router);
+
+  readonly unreadCount$ = this.notificationsService.unreadCount$;
+  readonly notifications$ = this.notificationsService.notifications$;
+  readonly unreadNotifications$ = this.notifications$.pipe(map((items) => items.filter((item) => !item.is_read)));
+
+  ngOnInit(): void {
+    this.notificationsService.startPolling();
+  }
+
+  ngOnDestroy(): void {
+    this.notificationsService.stopPolling();
+  }
+
+  openNotification(n
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/app/shared/services/listing-view-preference.service.ts`
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
+++ b/microtv-crm-frontend/src/app/shared/services/listing-view-preference.service.ts
@@ -0,0 +1,25 @@
+import { Injectable } from '@angular/core';
+
+export type ListingViewMode = 'table' | 'cards';
+
+@Injectable({ providedIn: 'root' })
+export class ListingViewPreferenceService {
+  private readonly storagePrefix = 'microtv.crm.listing.view';
+
+  getView(key: string, fallback: ListingViewMode = 'table'): ListingViewMode {
+    if (typeof window === 'undefined' || !window.localStorage) {
+      return fallback;
+    }
+
+    const value = window.localStorage.getItem(`${this.storagePrefix}.${key}`);
+    return value === 'cards' || value === 'table' ? value : fallback;
+  }
+
+  setView(key: string, mode: ListingViewMode): void {
+    if (typeof window === 'undefined' || !window.localStorage) {
+      return;
+    }
+
+    window.localStorage.setItem(`${this.storagePrefix}.${key}`, mode);
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/shared/ui/listing-controls/listing-controls.component.html`
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
+++ b/microtv-crm-frontend/src/app/shared/ui/listing-controls/listing-controls.component.html
@@ -0,0 +1,45 @@
+<section class="listing-controls" aria-label="Controles de listado">
+  <mat-form-field appearance="outline" class="listing-controls__search">
+    <mat-label>{{ searchPlaceholder() }}</mat-label>
+    <input matInput [value]="searchValue()" (input)="onSearchInput(($any($event.target).value || '').trimStart())" />
+    <mat-icon matSuffix>search</mat-icon>
+  </mat-form-field>
+
+  <mat-form-field appearance="outline" class="listing-controls__status">
+    <mat-label>Estado</mat-label>
+    <mat-select [value]="selectedStatus()" (valueChange)="onStatusSelect($event)">
+      @for (option of statusOptions(); track option.value) {
+        <mat-option [value]="option.value">{{ option.label }}</mat-option>
+      }
+    </mat-select>
+  </mat-form-field>
+
+  <div class="listing-controls__actions">
+    <button mat-stroked-button type="button" (click)="toggleSortDirection()">
+      <mat-icon>{{ sortDirection() === 'asc' ? 'arrow_upward' : 'arrow_downward' }}</mat-icon>
+      <span>{{ sortDirection() === 'asc' ? 'Más antiguo primero' : 'Más reciente primero' }}</span>
+    </button>
+
+    <div class="listing-controls__view-toggle" role="group" aria-label="Modo de vista">
+      <button
+        mat-stroked-button
+        type="button"
+        [class.listing-controls__view-toggle-button--active]="viewMode() === 'table'"
+        (click)="setViewMode('table')"
+      >
+        <mat-icon>table_rows</mat-icon>
+        <span>Tabla</span>
+      </button>
+
+      <button
+        mat-stroked-button
+        type="button"
+        [class.listing-controls__view-toggle-button--active]="viewMode() === 'cards'"
+        (click)="setViewMode('cards')"
+      >
+        <mat-icon>view_agenda</mat-icon>
+        <span>Tarjetas</span>
+      </button>
+    </div>
+  </div>
+</section>
```

#### 📄 `microtv-crm-frontend/src/app/shared/ui/listing-controls/listing-controls.component.scss`
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
+++ b/microtv-crm-frontend/src/app/shared/ui/listing-controls/listing-controls.component.scss
@@ -0,0 +1,63 @@
+.listing-controls {
+  display: grid;
+  grid-template-columns: minmax(14rem, 1.6fr) minmax(12rem, 1fr) auto;
+  gap: 0.8rem;
+  align-items: start;
+}
+
+.listing-controls__search,
+.listing-controls__status {
+  min-width: 0;
+}
+
+.listing-controls__actions {
+  display: flex;
+  align-items: center;
+  justify-content: flex-end;
+  gap: 0.6rem;
+  flex-wrap: wrap;
+}
+
+.listing-controls__view-toggle {
+  display: inline-flex;
+  align-items: center;
+  gap: 0.4rem;
+}
+
+.listing-controls__view-toggle-button--active {
+  background: rgba(204, 38, 38, 0.08);
+  border-color: rgba(204, 38, 38, 0.38);
+}
+
+@media (max-width: 900px) {
+  .listing-controls {
+    grid-template-columns: 1fr 1fr;
+  }
+
+  .listing-controls__actions {
+    grid-column: 1 / -1;
+    justify-content: flex-start;
+  }
+}
+
+@media (max-width: 640px) {
+  .listing-controls {
+    grid-template-columns: 1fr;
+    gap: 0.5rem;
+  }
+
+  .listing-controls__actions {
+    flex-direction: column;
+    align-items: stretch;
+  }
+
+  .listing-controls__actions > button,
+  .listing-controls__view-toggle {
+    width: 100%;
+  }
+
+  .listing-controls__view-toggle {
+    display: grid;
+    grid-template-columns: 1fr 1fr;
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/shared/ui/listing-controls/listing-controls.component.ts`
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
+++ b/microtv-crm-frontend/src/app/shared/ui/listing-controls/listing-controls.component.ts
@@ -0,0 +1,53 @@
+import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
+import { MatButtonModule } from '@angular/material/button';
+import { MatFormFieldModule } from '@angular/material/form-field';
+import { MatIconModule } from '@angular/material/icon';
+import { MatInputModule } from '@angular/material/input';
+import { MatSelectModule } from '@angular/material/select';
+
+import { ListingViewMode } from '../../services/listing-view-preference.service';
+
+export interface ListingStatusOption {
+  value: string;
+  label: string;
+}
+
+export type ListingSortDirection = 'asc' | 'desc';
+
+@Component({
+  selector: 'app-listing-controls',
+  standalone: true,
+  imports: [MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
+  templateUrl: './listing-controls.component.html',
+  styleUrl: './listing-controls.component.scss',
+  changeDetection: ChangeDetectionStrategy.OnPush
+})
+export class ListingControlsComponent {
+  readonly searchValue = input('');
+  readonly searchPlaceholder = input('Buscar');
+  readonly selectedStatus = input('all');
+  readonly statusOptions = input<readonly ListingStatusOption[]>([{ value: 'all', label: 'Todos los estados' }]);
+  readonly viewMode = input<ListingViewMode>('table');
+  readonly sortDirection = input<ListingSortDirection>('desc');
+
+  readonly searchChanged = output<string>();
+  readonly statusChanged = output<string>();
+  readonly viewModeChanged = output<ListingViewMode>();
+  readonly sortDirectionChanged = output<ListingSortDirection>();
+
+  onSearchInput(value: string): void {
+    this.searchChanged.emit(value);
+  }
+
+  onStatusSelect(value: string): void {
+    this.statusChanged.emit(value);
+  }
+
+  setViewMode(mode: ListingViewMode): void {
+    this.viewModeChanged.emit(mode);
+  }
+
+  toggleSortDirection(): void {
+    this.sortDirectionChanged.emit(this.sortDirection() === 'asc' ? 'desc' : 'asc');
+  }
+}
```

#### 📄 `microtv-crm-frontend/src/app/shared/ui/location-map/location-map.component.ts`
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

--- a/microtv-crm-frontend/src/app/shared/ui/location-map/location-map.component.ts
+++ b/microtv-crm-frontend/src/app/shared/ui/location-map/location-map.component.ts
@@ -1,10 +1,10 @@
 import { CommonModule, isPlatformBrowser } from '@angular/common';
-import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, PLATFORM_ID, ViewChild, computed, inject, input, signal } from '@angular/core';
+import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnChanges, OnDestroy, PLATFORM_ID, ViewChild, computed, inject, input, signal } from '@angular/core';
 import { MatIconModule } from '@angular/material/icon';
 import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
 import type { Map as LeafletMap } from 'leaflet';
 
-import { AppLocation } from '../../../core/models/location.model';
+import { AppLocation, LocationMapMarker } from '../../../core/models/location.model';
 import { LocationFacade } from '../../facades/location.facade';
 
 @Component({
@@ -22,18 +22,43 @@ export class LocationMapComponent implements AfterViewInit, OnDestroy {
   @ViewChild('mapCanvas') private mapCanvas?: ElementRef<HTMLElement>;
 
   readonly location = input<AppLocation | null>(null);
+  readonly markers = input<readonly LocationMapMarker[] | null>(null);
   readonly title = input('Ubicación');
   readonly zoom = input(15);
 
   readonly state = signal<'idle' | 'loading' | 'ready' | 'error' | 'invalid'>('idle');
   readonly errorMessage = signal('');
-  readonly hasValidLocation = computed(() => this.locationFacade.isValid(this.location()));
+  readonly validMarkers = computed<readonly LocationMapMarker[]>(() => {
+    const providedMarkers = (this.markers() ?? []).filter((marker) => this.locationFacade.isValid(marker));
+    if (providedMarkers.length) {
+      return providedMarkers;
+    }
+
+    const singleLocation = this.location();
+    if (!this.locationFacade.isValid(singleLocation)) {
+      return [];
+    }
+
+    return [{ ...singleLocation, title: this.title() }];
+  });
+  readonly hasValidLocation = computed(() => this.validMarkers().leng
... (código truncado por longitud) ...
```

#### 📄 `microtv-crm-frontend/src/index.html`
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

--- a/microtv-crm-frontend/src/index.html
+++ b/microtv-crm-frontend/src/index.html
@@ -2,10 +2,17 @@
 <html lang="en">
   <head>
     <meta charset="utf-8" />
-    <title>MicrotvCrmFrontend</title>
+    <title>CRM MicroTV</title>
     <base href="/" />
+    <meta name="theme-color" content="#ffffff" />
     <meta name="viewport" content="width=device-width, initial-scale=1" />
+    <meta name="mobile-web-app-capable" content="yes" />
+    <meta name="apple-mobile-web-app-capable" content="yes" />
+    <meta name="apple-mobile-web-app-title" content="CRM MicroTV" />
+    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
     <link rel="icon" type="image/x-icon" href="favicon.ico" />
+    <link rel="manifest" href="manifest.webmanifest" />
+    <link rel="apple-touch-icon" href="icons/icon-192x192.png" />
     <link rel="preconnect" href="https://fonts.googleapis.com" />
     <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
     <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
```

- *microtv-crm-frontend/src/mocks/layout-data.json (Omitido por extensión)*
#### 📄 `microtv-crm-frontend/src/styles.css`
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

--- a/microtv-crm-frontend/src/styles.css
+++ b/microtv-crm-frontend/src/styles.css
@@ -53,3 +53,91 @@ select {
 .mat-mdc-table {
 	background: transparent;
 }
+/* Notification panel (mat-menu overlay) */
+.notif-panel .mat-mdc-menu-content {
+  padding: 0;
+  min-width: 22rem;
+  max-width: 26rem;
+  max-height: 28rem;
+  overflow-y: auto;
+}
+
+.notif-panel__header {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  padding: 0.75rem 1rem 0.5rem;
+  border-bottom: 1px solid var(--border-soft);
+  position: sticky;
+  top: 0;
+  background: var(--surface-panel);
+  z-index: 1;
+}
+
+.notif-panel__heading {
+  font-weight: 700;
+  font-size: 0.9rem;
+}
+
+.notif-panel__mark-all {
+  font-size: 0.75rem;
+}
+
+.notif-panel__empty {
+  padding: 1.5rem 1rem;
+  color: var(--text-secondary);
+  font-size: 0.85rem;
+  text-align: center;
+}
+
+.notif-item {
+  display: flex !important;
+  align-items: flex-start !important;
+  padding: 0.6rem 1rem !important;
+  min-height: auto !important;
+  border-bottom: 1px solid var(--border-soft);
+  white-space: normal !important;
+}
+
+.notif-item--unread {
+  background: rgba(37, 99, 235, 0.05) !important;
+}
+
+.notif-item--unread::before {
+  content: '';
+  display: inline-block;
+  width: 0.45rem;
+  height: 0.45rem;
+  min-width: 0.45rem;
+  border-radius: 50%;
+  background: var(--accent-blue);
+  margin-top: 0.3rem;
+  margin-right: 0.5rem;
+}
+
+.notif-item__content {
+  display: flex;
+  flex-direction: column;
+  gap: 0.15rem;
+  min-width: 0;
+}
+
+.notif-item__title {
+  font-weight: 600;
+  font-size: 0.83rem;
+  color: var(--text-primary);
+  white-space: normal;
+}
+
+.notif-item__body {
+  font-size: 0.78rem;
+  color: var(--text-secondary);
+  white-space: normal;
+  word-break: break-word;
+}
+
+.notif-item__time {
+  font-size: 0.7rem;
+  color: var(--text-secondary);
+  margin-top: 0.1rem;
+}
\ No newline at end of file
```

---

