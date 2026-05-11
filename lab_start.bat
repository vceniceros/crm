@echo off
setlocal enabledelayedexpansion

:: =========================================================
::  MicroTV CRM - Laboratorio Local
::  Levanta el stack completo de pruebas:
::    1. PostgreSQL de auth interno (Docker)
::    2. auth interno CRM          (Docker, puerto 8001)
::    3. CRM Backend         (Python/uvicorn, puerto 8010)
::    4. CRM Frontend        (Angular ng serve, puerto 4200)
:: =========================================================

set "ROOT=%~dp0"
set "COMPOSE_DIR=%ROOT%microtv-crm-backend"
set "CRM_DB_CONTAINER=crm-backend-db"
set "CRM_DB_NAME=crm_microtv"
set "CRM_DB_USER=crmmicrotv"
set "CRM_DB_PASSWORD=crmmicrotv"
set "CRM_DB_PORT=5433"
set "CRM_SCHEMA_FILE=%ROOT%docs\diagrams\schema-propuesto-v4.sql"
set "CRM_SQL_DIR=%ROOT%microtv-crm-backend\sql"
set "CRM_DATABASE_URL=postgresql+psycopg://%CRM_DB_USER%:%CRM_DB_PASSWORD%@localhost:%CRM_DB_PORT%/%CRM_DB_NAME%"

echo.
echo =========================================================
echo   MicroTV CRM - Laboratorio Local
echo =========================================================
echo.

:: ---- 1. Verificar Docker ----------------------------------------
echo [1/5] Verificando que Docker este activo...
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

:: ---- 2. Levantar auth interno + PostgreSQL CRM ------------------
echo [2/6] Levantando auth interno CRM + PostgreSQL de laboratorio (Docker Compose)...
echo   Compose: %COMPOSE_DIR%\docker-compose.auth-local.yml
echo.
docker compose -f "%COMPOSE_DIR%\docker-compose.auth-local.yml" up --build -d
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
    for %%f in ("%CRM_SQL_DIR%\*.sql") do (
        set "CRM_MIGRATION_NAME=%%~nxf"
        set "CRM_MIGRATION_EXISTS="
        for /f "usebackq delims=" %%r in (`docker exec %CRM_DB_CONTAINER% psql -U %CRM_DB_USER% -d %CRM_DB_NAME% -qtAX -c "SELECT CASE WHEN EXISTS (SELECT 1 FROM crm_schema_migrations WHERE migration_name='%%~nxf') THEN '1' ELSE '0' END;" 2^>nul`) do set "CRM_MIGRATION_EXISTS=%%r"

        if "!CRM_MIGRATION_EXISTS!"=="1" (
            echo   - Saltando %%~nxf ^(ya aplicada^)
        ) else (
            echo   - Aplicando %%~nxf ...
            docker exec -i %CRM_DB_CONTAINER% psql -v ON_ERROR_STOP=1 -U %CRM_DB_USER% -d %CRM_DB_NAME% < "%%f"
            if errorlevel 1 (
                echo.
                echo   ERROR: Fallo la migracion %%~nxf
                echo.
                pause
                exit /b 1
            )

            docker exec %CRM_DB_CONTAINER% psql -v ON_ERROR_STOP=1 -U %CRM_DB_USER% -d %CRM_DB_NAME% -c "INSERT INTO crm_schema_migrations (migration_name) VALUES ('%%~nxf') ON CONFLICT (migration_name) DO NOTHING;" > nul
            if errorlevel 1 (
                echo.
                echo   ERROR: No se pudo registrar la migracion %%~nxf en crm_schema_migrations.
                echo.
                pause
                exit /b 1
            )
            set /a CRM_MIGRATIONS_APPLIED+=1
            echo   - OK %%~nxf
        )
    )
    echo   OK - migraciones incrementales revisadas. Nuevas aplicadas: !CRM_MIGRATIONS_APPLIED!.
)
echo.

:: ---- 5. Abrir terminal de logs de auth --------------------------
echo [5/6] Abriendo logs de auth interno CRM en ventana separada...
start "Auth interno CRM logs [8001]" /d "%COMPOSE_DIR%" cmd /k docker compose -f docker-compose.auth-local.yml logs -f auth-local
echo   Ventana: "Auth interno CRM logs [8001]"
echo.

:: ---- 5a. Esperar que auth responda (healthcheck) ----------------
echo   Esperando http://localhost:8001/health ...
set /a RETRIES=0
set HTTP_CODE=000

:wait_auth
set /a RETRIES=RETRIES+1
if %RETRIES% GTR 40 (
    echo.
    echo   ERROR: auth interno CRM no respondio en ~120 segundos.
    echo   Revisa la ventana "Auth interno CRM logs [8001]"
    echo   o ejecuta:
    echo     docker compose -f microtv-crm-backend\docker-compose.auth-local.yml logs
    echo.
    pause
    exit /b 1
)
set HTTP_CODE=000
for /f %%r in ('curl -s -o nul -w "%%{http_code}" http://localhost:8001/health 2^>nul') do set HTTP_CODE=%%r
if "%HTTP_CODE%"=="200" goto :auth_ready
if %RETRIES% equ 1 echo   (esperando arranque inicial, puede tardar hasta 60s en la primera vez...)
timeout /t 3 /nobreak > nul
goto wait_auth

:auth_ready
echo   OK - auth interno CRM responde en http://localhost:8001
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
echo     Auth interno CRM   http://localhost:8001/health   (Docker)
echo     CRM PostgreSQL localhost:%CRM_DB_PORT%        (Docker)
echo     CRM Backend    http://localhost:8010/health   (ventana "CRM Backend [8010]")
echo     CRM Frontend   http://localhost:4200          (ventana "CRM Frontend [4200]")
echo.
echo   TERMINALES ABIERTAS:
echo     "Auth interno CRM logs [8001]"   logs de auth en tiempo real
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
echo     docker compose -f microtv-crm-backend\docker-compose.auth-local.yml down
echo.
echo   Variables de laboratorio del CRM:
echo     DATABASE_URL=%CRM_DATABASE_URL%
echo     CRM schema: %CRM_SCHEMA_FILE%
echo.
endlocal
pause
