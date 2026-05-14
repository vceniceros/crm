@echo off
setlocal enabledelayedexpansion

:: =========================================================
::  MicroTV CRM - Laboratorio Local
::  Levanta el stack completo de pruebas:
::    1. PostgreSQL de auth interno (Docker)
::    2. auth interno CRM          (Docker, puerto 8001 o alternativo)
::    3. CRM Backend         (Python/uvicorn, puerto 8010)
::    4. CRM Frontend        (Angular ng serve, puerto 4200)
:: =========================================================

set "ROOT=%~dp0"
set "COMPOSE_DIR=%ROOT%microtv-crm-backend"
if not defined LAB_STACK_NAME set "LAB_STACK_NAME=microtv-crm-ycc"
set "COMPOSE_PROJECT_NAME=%LAB_STACK_NAME%"
set "LAB_AUTH_DB_CONTAINER=%LAB_STACK_NAME%-auth-db"
set "LAB_AUTH_LOCAL_CONTAINER=%LAB_STACK_NAME%-auth-local"
set "LAB_CRM_DB_CONTAINER=%LAB_STACK_NAME%-crm-db"
set "CRM_DB_CONTAINER=%LAB_CRM_DB_CONTAINER%"
set "AUTH_PORT_DEFAULT=8001"
set "AUTH_PORT=%AUTH_PORT_DEFAULT%"
set "CRM_DB_NAME=crm_microtv"
set "CRM_DB_USER=crmmicrotv"
set "CRM_DB_PASSWORD=crmmicrotv"
set "CRM_DB_DEFAULT_PORT=5433"
set "CRM_DB_PORT=%CRM_DB_DEFAULT_PORT%"
set "CRM_SCHEMA_FILE=%ROOT%docs\diagrams\schema-propuesto-v4.sql"
set "CRM_SQL_DIR=%ROOT%microtv-crm-backend\sql"
set "BACKEND_ENV_FILE=%ROOT%microtv-crm-backend\.env"
set "BACKEND_ENV_EXAMPLE_FILE=%ROOT%microtv-crm-backend\.env.example"
set "FRONTEND_ENV_FILE=%ROOT%microtv-crm-frontend\.env"
set "FRONTEND_ENV_EXAMPLE_FILE=%ROOT%microtv-crm-frontend\.env.example"
set "LAB_VAPID_PUBLIC_KEY="
set "LAB_VAPID_PRIVATE_KEY="

echo.
echo =========================================================
echo   MicroTV CRM - Laboratorio Local
echo =========================================================
echo.

:: ---- 1. Verificar Docker ----------------------------------------
echo [1/6] Verificando que Docker este activo...
docker info > nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERROR: Docker no esta corriendo.
    echo   Inicia Docker Desktop y vuelve a ejecutar este script.
    echo.
    pause
    exit /b 1
)
echo   OK - Docker activo.
echo.

:: ---- 1a. Elegir puertos externos de laboratorio ----------------
echo [1a/6] Verificando puertos locales de laboratorio...
if defined LAB_AUTH_PORT (
    set "AUTH_PORT=%LAB_AUTH_PORT%"
    set "AUTH_PORT_SOURCE=LAB_AUTH_PORT"
) else (
    set "AUTH_PORT=%AUTH_PORT_DEFAULT%"
    set "AUTH_PORT_SOURCE=default"
    set "AUTH_EXISTING_PORT="
    set "AUTH_CONTAINER_RUNNING="
    for /f "usebackq delims=" %%s in (`docker inspect -f "{{.State.Running}}" %LAB_AUTH_LOCAL_CONTAINER% 2^>nul`) do set "AUTH_CONTAINER_RUNNING=%%s"
    if /I "!AUTH_CONTAINER_RUNNING!"=="true" for /f "tokens=2 delims=:" %%p in ('docker port %LAB_AUTH_LOCAL_CONTAINER% 8001/tcp 2^>nul') do if not defined AUTH_EXISTING_PORT set "AUTH_EXISTING_PORT=%%p"
    if /I "!AUTH_CONTAINER_RUNNING!"=="true" if defined AUTH_EXISTING_PORT (
        set "AUTH_PORT=!AUTH_EXISTING_PORT!"
        set "AUTH_PORT_SOURCE=existing-container"
    )
)

if /I "%AUTH_PORT_SOURCE%"=="existing-container" goto :auth_port_selected

call :port_is_free "%AUTH_PORT%" AUTH_PORT_FREE
if "!AUTH_PORT_FREE!"=="0" (
    if defined LAB_AUTH_PORT (
        echo.
        echo   ERROR: LAB_AUTH_PORT=%AUTH_PORT% ya esta ocupado.
        echo   Cierra el proceso que usa ese puerto o, en PowerShell, ejecuta:
        echo     $env:LAB_AUTH_PORT="58001"
        echo     lab_start.bat
        echo.
        pause
        exit /b 1
    )

    echo   [*] Puerto auth %AUTH_PORT% ocupado. Buscando alternativa para este laboratorio...
    set "AUTH_PORT_FOUND="
    for %%p in (58001 58002 58003 58004 58005 58006 58007 58008 58009) do (
        if not defined AUTH_PORT_FOUND (
            call :port_is_free "%%p" AUTH_PORT_FREE
            if "!AUTH_PORT_FREE!"=="1" set "AUTH_PORT_FOUND=%%p"
        )
    )

    if not defined AUTH_PORT_FOUND (
        echo.
        echo   ERROR: No se encontro puerto libre para auth.
        echo   Puertos probados: %AUTH_PORT_DEFAULT%, 58001-58009
        echo.
        pause
        exit /b 1
    )

    set "AUTH_PORT=!AUTH_PORT_FOUND!"
    set "AUTH_PORT_SOURCE=auto"
)

:auth_port_selected
set "AUTH_BASE_URL=http://localhost:%AUTH_PORT%"
echo   OK - Auth interno CRM usara %AUTH_BASE_URL% ^(%AUTH_PORT_SOURCE%^).

if defined LAB_CRM_DB_PORT (
    set "CRM_DB_PORT=%LAB_CRM_DB_PORT%"
    set "CRM_DB_PORT_SOURCE=LAB_CRM_DB_PORT"
) else (
    set "CRM_DB_PORT=%CRM_DB_DEFAULT_PORT%"
    set "CRM_DB_PORT_SOURCE=default"
    set "CRM_DB_EXISTING_PORT="
    set "CRM_DB_CONTAINER_RUNNING="
    for /f "usebackq delims=" %%s in (`docker inspect -f "{{.State.Running}}" %CRM_DB_CONTAINER% 2^>nul`) do set "CRM_DB_CONTAINER_RUNNING=%%s"
    if /I "!CRM_DB_CONTAINER_RUNNING!"=="true" for /f "tokens=2 delims=:" %%p in ('docker port %CRM_DB_CONTAINER% 5432/tcp 2^>nul') do if not defined CRM_DB_EXISTING_PORT set "CRM_DB_EXISTING_PORT=%%p"
    if /I "!CRM_DB_CONTAINER_RUNNING!"=="true" if defined CRM_DB_EXISTING_PORT (
        set "CRM_DB_PORT=!CRM_DB_EXISTING_PORT!"
        set "CRM_DB_PORT_SOURCE=existing-container"
    )
)

if /I "%CRM_DB_PORT_SOURCE%"=="existing-container" goto :crm_db_port_selected

call :port_is_free "%CRM_DB_PORT%" CRM_DB_PORT_FREE
if "!CRM_DB_PORT_FREE!"=="0" (
    if defined LAB_CRM_DB_PORT (
        echo.
        echo   ERROR: LAB_CRM_DB_PORT=%CRM_DB_PORT% ya esta ocupado.
        echo   Cierra el proceso que usa ese puerto o, en PowerShell, ejecuta:
        echo     $env:LAB_CRM_DB_PORT="55433"
        echo     lab_start.bat
        echo.
        pause
        exit /b 1
    )

    echo   [*] Puerto %CRM_DB_PORT% ocupado. Buscando alternativa para este laboratorio...
    set "CRM_DB_PORT_FOUND="
    for %%p in (55433 55434 55435 55436 55437 55438 55439) do (
        if not defined CRM_DB_PORT_FOUND (
            call :port_is_free "%%p" CRM_DB_PORT_FREE
            if "!CRM_DB_PORT_FREE!"=="1" set "CRM_DB_PORT_FOUND=%%p"
        )
    )

    if not defined CRM_DB_PORT_FOUND (
        echo.
        echo   ERROR: No se encontro puerto libre para PostgreSQL CRM.
        echo   Puertos probados: %CRM_DB_DEFAULT_PORT%, 55433-55439
        echo.
        pause
        exit /b 1
    )

    set "CRM_DB_PORT=!CRM_DB_PORT_FOUND!"
    set "CRM_DB_PORT_SOURCE=auto"
)

:crm_db_port_selected
set "CRM_DATABASE_URL=postgresql+psycopg://%CRM_DB_USER%:%CRM_DB_PASSWORD%@localhost:%CRM_DB_PORT%/%CRM_DB_NAME%"
set "CRM_DB_PORT=%CRM_DB_PORT%"
echo   OK - PostgreSQL CRM usara localhost:%CRM_DB_PORT% ^(%CRM_DB_PORT_SOURCE%^).
echo.

:: ---- 1b. Preparar .env y push para laboratorio ------------------
echo [1b/6] Preparando .env de backend/frontend para laboratorio...

if not exist "%BACKEND_ENV_FILE%" (
    if exist "%BACKEND_ENV_EXAMPLE_FILE%" (
        echo   [*] Creando microtv-crm-backend\.env desde .env.example
        copy "%BACKEND_ENV_EXAMPLE_FILE%" "%BACKEND_ENV_FILE%" > nul
    ) else (
        echo.
        echo   ERROR: No se encontro %BACKEND_ENV_EXAMPLE_FILE%
        echo.
        pause
        exit /b 1
    )
)

if not exist "%FRONTEND_ENV_FILE%" (
    if exist "%FRONTEND_ENV_EXAMPLE_FILE%" (
        echo   [*] Creando microtv-crm-frontend\.env desde .env.example
        copy "%FRONTEND_ENV_EXAMPLE_FILE%" "%FRONTEND_ENV_FILE%" > nul
    ) else (
        echo.
        echo   ERROR: No se encontro %FRONTEND_ENV_EXAMPLE_FILE%
        echo.
        pause
        exit /b 1
    )
)

for /f "usebackq tokens=1* delims==" %%A in (`findstr /R /C:"^VAPID_PUBLIC_KEY=" "%BACKEND_ENV_FILE%"`) do set "LAB_VAPID_PUBLIC_KEY=%%B"
for /f "usebackq tokens=1* delims==" %%A in (`findstr /R /C:"^VAPID_PRIVATE_KEY=" "%BACKEND_ENV_FILE%"`) do set "LAB_VAPID_PRIVATE_KEY=%%B"

if not defined LAB_VAPID_PUBLIC_KEY (
    echo   [*] No se encontraron VAPID keys en backend .env. Generando claves para dev...
    for /f "usebackq tokens=1* delims==" %%A in (`powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $output = npx --yes web-push generate-vapid-keys --json 2^> $null; $jsonLine = $output ^| Where-Object { $_ -match '^\s*\{.*\}\s*$' } ^| Select-Object -Last 1; if (-not $jsonLine) { throw 'No se pudo parsear salida JSON de web-push.' }; $obj = $jsonLine ^| ConvertFrom-Json; Write-Output ('PUBLIC=' + $obj.publicKey); Write-Output ('PRIVATE=' + $obj.privateKey)"`) do (
        if /I "%%A"=="PUBLIC" set "LAB_VAPID_PUBLIC_KEY=%%B"
        if /I "%%A"=="PRIVATE" set "LAB_VAPID_PRIVATE_KEY=%%B"
    )
)

if not defined LAB_VAPID_PUBLIC_KEY (
    echo   [!] WARNING: No se pudo generar VAPID_PUBLIC_KEY. Push quedara deshabilitado.
) else (
    call :upsert_env_value "%BACKEND_ENV_FILE%" "VAPID_PUBLIC_KEY" "%LAB_VAPID_PUBLIC_KEY%"
)

if not defined LAB_VAPID_PRIVATE_KEY (
    echo   [!] WARNING: No se pudo generar VAPID_PRIVATE_KEY. Push quedara deshabilitado.
) else (
    call :upsert_env_value "%BACKEND_ENV_FILE%" "VAPID_PRIVATE_KEY" "%LAB_VAPID_PRIVATE_KEY%"
)

call :upsert_env_value "%BACKEND_ENV_FILE%" "VAPID_CLAIMS_SUB" "mailto:admin@microtv.ar"
call :upsert_env_value "%BACKEND_ENV_FILE%" "DATABASE_URL" "%CRM_DATABASE_URL%"
call :upsert_env_value "%BACKEND_ENV_FILE%" "AUTH_BASE_URL" "%AUTH_BASE_URL%"
call :upsert_env_value "%BACKEND_ENV_FILE%" "AUTH_MANAGEMENT_EMAIL" "admin@ycc.local"
call :upsert_env_value "%BACKEND_ENV_FILE%" "AUTH_MANAGEMENT_PASSWORD" "changeme-secure-password"
call :upsert_env_value "%FRONTEND_ENV_FILE%" "CRM_API_BASE_URL" "http://localhost:8010"
call :upsert_env_value "%FRONTEND_ENV_FILE%" "CRM_MEDIA_PUBLIC_URL" "/media"
if defined LAB_VAPID_PUBLIC_KEY call :upsert_env_value "%FRONTEND_ENV_FILE%" "VAPID_PUBLIC_KEY" "%LAB_VAPID_PUBLIC_KEY%"

if defined LAB_VAPID_PUBLIC_KEY (
    echo   [*] Push dev habilitado con VAPID_PUBLIC_KEY en backend y frontend .env
) else (
    echo   [*] Push dev no configurado automaticamente. Completa VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY manualmente.
)
echo.

:: ---- 2. Levantar auth interno + PostgreSQL CRM ------------------
echo [2/6] Levantando auth interno CRM + PostgreSQL de laboratorio (Docker Compose)...
echo   Compose: %COMPOSE_DIR%\docker-compose.auth-local.yml
echo.
docker compose -p "%COMPOSE_PROJECT_NAME%" -f "%COMPOSE_DIR%\docker-compose.auth-local.yml" up --build -d
if errorlevel 1 (
    echo.
    echo   ERROR: docker compose fallo. Revisa el output arriba.
    echo.
    echo   Causa frecuente: revisar rutas/build-context en docker-compose
    echo   y que exista la carpeta interna auth.microtv.ar dentro de este repo.
    echo   Ver: lab_deploy.md - seccion Troubleshooting.
    echo.
    pause
    exit /b 1
)
echo.

:: ---- 3. Esperar PostgreSQL del CRM -----------------------------
echo [3/6] Esperando PostgreSQL del CRM en localhost:%CRM_DB_PORT%...
set /a CRM_DB_RETRIES=0

:wait_crm_db
set /a CRM_DB_RETRIES=CRM_DB_RETRIES+1
if %CRM_DB_RETRIES% GTR 40 (
    echo.
    echo   ERROR: PostgreSQL del CRM no quedo healthy en ~120 segundos.
    echo   Revisa el contenedor %CRM_DB_CONTAINER% con:
    echo     docker logs %CRM_DB_CONTAINER%
    echo.
    pause
    exit /b 1
)
set "CRM_DB_STATUS="
for /f %%r in ('docker inspect -f "{{.State.Health.Status}}" %CRM_DB_CONTAINER% 2^>nul') do set "CRM_DB_STATUS=%%r"
if /I "%CRM_DB_STATUS%"=="healthy" goto :crm_db_ready
if %CRM_DB_RETRIES% equ 1 echo   (esperando readiness de PostgreSQL y healthcheck...)
timeout /t 3 /nobreak > nul
goto :wait_crm_db

:crm_db_ready
echo   OK - PostgreSQL CRM disponible.
echo.

:: ---- 4. Aplicar schema v4 --------------------------------------
echo [4/6] Verificando schema v4 del CRM...
if not exist "%CRM_SCHEMA_FILE%" (
    echo.
    echo   ERROR: No se encontro el schema SQL esperado.
    echo   Archivo: %CRM_SCHEMA_FILE%
    echo.
    pause
    exit /b 1
)
set "CRM_SCHEMA_READY="
for /f "usebackq delims=" %%r in (`docker exec %CRM_DB_CONTAINER% psql -U %CRM_DB_USER% -d %CRM_DB_NAME% -qtAX -c "SELECT CASE WHEN to_regclass(''public.crm_users'') IS NOT NULL THEN 'READY' ELSE 'MISSING' END;" 2^>nul`) do set "CRM_SCHEMA_READY=%%r"
if /I "%CRM_SCHEMA_READY%"=="READY" (
    echo   Schema v4 detectado en la BD del CRM, se omite bootstrap SQL.
) else (
    echo   Aplicando %CRM_SCHEMA_FILE% ...
    docker exec -i %CRM_DB_CONTAINER% psql -v ON_ERROR_STOP=1 -U %CRM_DB_USER% -d %CRM_DB_NAME% < "%CRM_SCHEMA_FILE%"
    if errorlevel 1 (
        echo.
        echo   ERROR: Fallo la aplicacion del schema v4 sobre PostgreSQL CRM.
        echo.
        pause
        exit /b 1
    )
    echo   OK - schema v4 aplicado.
)
echo.

:: ---- 4b. Aplicar migraciones incrementales ----------------------
echo [4b/6] Aplicando migraciones incrementales del CRM...
if not exist "%CRM_SQL_DIR%\*.sql" (
    echo   WARNING: No se encontraron archivos .sql en %CRM_SQL_DIR%.
    echo   Se omite la fase de migraciones incrementales.
) else (
    docker exec %CRM_DB_CONTAINER% psql -v ON_ERROR_STOP=1 -U %CRM_DB_USER% -d %CRM_DB_NAME% -c "CREATE TABLE IF NOT EXISTS crm_schema_migrations (migration_name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW());" > nul
    if errorlevel 1 (
        echo.
        echo   ERROR: No se pudo preparar la tabla crm_schema_migrations.
        echo.
        pause
        exit /b 1
    )

    set /a CRM_MIGRATIONS_APPLIED=0

    call :apply_crm_migration "%CRM_SQL_DIR%\20260414_task_schema_v4_delta.sql"
    if errorlevel 1 (
        pause
        exit /b 1
    )
    call :apply_crm_migration "%CRM_SQL_DIR%\20260414_task_media_comment_link.sql"
    if errorlevel 1 (
        pause
        exit /b 1
    )
    call :apply_crm_migration "%CRM_SQL_DIR%\20260414_task_schema_v4_1_hardening.sql"
    if errorlevel 1 (
        pause
        exit /b 1
    )
    call :apply_crm_migration "%CRM_SQL_DIR%\20260414_task_schema_v4_1_post_validation.sql"
    if errorlevel 1 (
        pause
        exit /b 1
    )

    for %%f in ("%CRM_SQL_DIR%\*.sql") do (
        call :apply_crm_migration "%%f"
        if errorlevel 1 (
            pause
            exit /b 1
        )
    )
    echo   OK - migraciones incrementales revisadas. Nuevas aplicadas: !CRM_MIGRATIONS_APPLIED!.
)
echo.

:: ---- 5. Abrir terminal de logs de auth --------------------------
echo [5/6] Abriendo logs de auth interno CRM en ventana separada...
start "Auth interno CRM logs [%AUTH_PORT%]" /d "%COMPOSE_DIR%" cmd /k docker compose -p "%COMPOSE_PROJECT_NAME%" -f docker-compose.auth-local.yml logs -f auth-local
echo   Ventana: "Auth interno CRM logs [%AUTH_PORT%]"
echo.

:: ---- 5a. Esperar que auth responda (healthcheck) ----------------
echo   Esperando %AUTH_BASE_URL%/health ...
set /a RETRIES=0
set HTTP_CODE=000

:wait_auth
set /a RETRIES=RETRIES+1
if %RETRIES% GTR 40 (
    echo.
    echo   ERROR: auth interno CRM no respondio en ~120 segundos.
    echo   Revisa la ventana "Auth interno CRM logs [%AUTH_PORT%]"
    echo   o ejecuta:
    echo     docker compose -p %COMPOSE_PROJECT_NAME% -f microtv-crm-backend\docker-compose.auth-local.yml logs
    echo.
    pause
    exit /b 1
)
set HTTP_CODE=000
for /f %%r in ('curl -s -o nul -w "%%{http_code}" %AUTH_BASE_URL%/health 2^>nul') do set HTTP_CODE=%%r
if "%HTTP_CODE%"=="200" goto :auth_ready
if %RETRIES% equ 1 echo   (esperando arranque inicial, puede tardar hasta 60s en la primera vez...)
timeout /t 3 /nobreak > nul
goto wait_auth

:auth_ready
echo   OK - auth interno CRM responde en %AUTH_BASE_URL%
echo.

:: ---- 6. Abrir CRM Backend ---------------------------------------
echo [6/6] Abriendo CRM Backend en ventana separada...
echo   DATABASE_URL=%CRM_DATABASE_URL%
set "DATABASE_URL=%CRM_DATABASE_URL%"
start "CRM Backend [8010]" /d "%ROOT%" cmd /k call lab\crm_backend.bat
timeout /t 2 /nobreak > nul

:: ---- 6a. Abrir CRM Frontend ------------------------------------
echo   Abriendo CRM Frontend en ventana separada...
start "CRM Frontend [4200]" /d "%ROOT%" cmd /k call lab\crm_frontend.bat

:: ---- Resumen final ---------------------------------------------
echo.
echo =========================================================
echo   Stack de laboratorio iniciado
echo =========================================================
echo.
echo   SERVICIOS:
echo     Auth interno CRM   %AUTH_BASE_URL%/health   (Docker)
echo     CRM PostgreSQL localhost:%CRM_DB_PORT%        (Docker)
echo     CRM Backend    http://localhost:8010/health   (ventana "CRM Backend [8010]")
echo     CRM Frontend   http://localhost:4200          (ventana "CRM Frontend [4200]")
echo.
echo   TERMINALES ABIERTAS:
echo     "Auth interno CRM logs [%AUTH_PORT%]"   logs de auth en tiempo real
echo     "CRM Backend [8010]"         uvicorn CRM backend
echo     "CRM Frontend [4200]"        ng serve Angular
echo.
echo   USUARIOS DE PRUEBA:
echo     admin@ycc.local                changeme-secure-password   (rol auth: admin)
echo     deposito.aux@yccbrothers.com   Passw0rd!   (rol local: encargado_deposito ^| alias UI: deposito)
echo     operador.crm@yccbrothers.com   Passw0rd!   (rol local: encargado_deposito ^| alias UI: deposito)
echo     ejecutivo.crm@yccbrothers.com  Passw0rd!   (rol local: ejecutivo ^| alias UI: ejecutivo)
echo     tecnico.campo@yccbrothers.com  Passw0rd!   (rol local: tecnico_campo ^| alias UI: tecnico)
echo.
echo   Para detener auth Docker:
echo     docker compose -p %COMPOSE_PROJECT_NAME% -f microtv-crm-backend\docker-compose.auth-local.yml down
echo.
echo   Variables de laboratorio del CRM:
echo     DATABASE_URL=%CRM_DATABASE_URL%
echo     CRM schema: %CRM_SCHEMA_FILE%
echo.
endlocal
pause
goto :eof

:upsert_env_value
set "UPSERT_FILE=%~1"
set "UPSERT_KEY=%~2"
set "UPSERT_VALUE=%~3"
powershell -NoProfile -Command "$path = $env:UPSERT_FILE; $key = $env:UPSERT_KEY; $value = $env:UPSERT_VALUE; if (-not (Test-Path -LiteralPath $path)) { New-Item -ItemType File -Path $path -Force ^| Out-Null }; $lines = Get-Content -LiteralPath $path; $found = $false; for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match ('^\s*' + [regex]::Escape($key) + '\s*=')) { $lines[$i] = ($key + '=' + $value); $found = $true; break } }; if (-not $found) { $lines += ($key + '=' + $value) }; Set-Content -LiteralPath $path -Value $lines -Encoding UTF8"
if errorlevel 1 (
    echo   [!] WARNING: No se pudo actualizar %UPSERT_KEY% en %UPSERT_FILE%
)
exit /b 0

:apply_crm_migration
set "CRM_MIGRATION_FILE=%~1"
set "CRM_MIGRATION_NAME=%~nx1"

if not exist "%CRM_MIGRATION_FILE%" (
    echo.
    echo   ERROR: No se encontro la migracion %CRM_MIGRATION_NAME%.
    echo   Archivo: %CRM_MIGRATION_FILE%
    echo.
    exit /b 1
)

set "CRM_MIGRATION_EXISTS="
for /f "usebackq delims=" %%r in (`docker exec %CRM_DB_CONTAINER% psql -U %CRM_DB_USER% -d %CRM_DB_NAME% -qtAX -c "SELECT CASE WHEN EXISTS (SELECT 1 FROM crm_schema_migrations WHERE migration_name='%CRM_MIGRATION_NAME%') THEN '1' ELSE '0' END;" 2^>nul`) do set "CRM_MIGRATION_EXISTS=%%r"

if "%CRM_MIGRATION_EXISTS%"=="1" (
    echo   - Saltando %CRM_MIGRATION_NAME% ^(ya aplicada^)
    exit /b 0
)

echo   - Aplicando %CRM_MIGRATION_NAME% ...
docker exec -i %CRM_DB_CONTAINER% psql -v ON_ERROR_STOP=1 -U %CRM_DB_USER% -d %CRM_DB_NAME% < "%CRM_MIGRATION_FILE%"
if errorlevel 1 (
    echo.
    echo   ERROR: Fallo la migracion %CRM_MIGRATION_NAME%
    echo.
    exit /b 1
)

docker exec %CRM_DB_CONTAINER% psql -v ON_ERROR_STOP=1 -U %CRM_DB_USER% -d %CRM_DB_NAME% -c "INSERT INTO crm_schema_migrations (migration_name) VALUES ('%CRM_MIGRATION_NAME%') ON CONFLICT (migration_name) DO NOTHING;" > nul
if errorlevel 1 (
    echo.
    echo   ERROR: No se pudo registrar la migracion %CRM_MIGRATION_NAME% en crm_schema_migrations.
    echo.
    exit /b 1
)

set /a CRM_MIGRATIONS_APPLIED+=1
echo   - OK %CRM_MIGRATION_NAME%
exit /b 0

:port_is_free
set "CHECK_PORT=%~1"
set "%~2=0"
docker ps --filter "publish=%CHECK_PORT%" --format "{{.ID}}" 2>nul | findstr /R "." >nul 2>&1
if not errorlevel 1 exit /b 0
powershell -NoProfile -Command "$listener = $null; try { $port = [int]$env:CHECK_PORT; $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Any, $port); $listener.Start(); exit 0 } catch { exit 1 } finally { if ($listener) { $listener.Stop() } }" > nul 2>&1
if not errorlevel 1 set "%~2=1"
exit /b 0
