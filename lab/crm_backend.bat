@echo off
setlocal

:: =========================================================
::  CRM Backend - arranque de laboratorio
::  Invocado desde lab_start.bat en ventana separada.
::  No ejecutes este script directamente.
:: =========================================================

set "LAB_DIR=%~dp0"
set "BACKEND_DIR=%LAB_DIR%..\microtv-crm-backend"
set "VENV_ACTIVATE=%LAB_DIR%..\.venv\Scripts\activate.bat"

echo =========================================================
echo   CRM Backend - Laboratorio (puerto 8010)
echo =========================================================
echo.

:: -- Validar directorio del backend
if not exist "%BACKEND_DIR%\pyproject.toml" (
    echo   ERROR: No se encontro microtv-crm-backend\pyproject.toml
    echo   Directorio esperado: %BACKEND_DIR%
    pause
    exit /b 1
)

cd /d "%BACKEND_DIR%"

:: -- Activar venv si existe
if exist "%VENV_ACTIVATE%" (
    echo   [*] Activando venv...
    call "%VENV_ACTIVATE%"
) else (
    echo   [!] .venv no encontrado en la raiz del workspace.
    echo       Se usara Python del sistema.
    echo       Para crear el venv: python -m venv .venv
    echo       Luego reinstala: pip install -e .[test]
    echo.
)

:: -- Copiar .env si no existe (no sobreescribir cambios locales)
if not exist ".env" (
    if exist ".env.example" (
        echo   [*] Creando .env desde .env.example...
        copy ".env.example" ".env" > nul
    ) else (
        echo   [!] No se encontro .env.example. El backend usara defaults.
    )
) else (
    echo   [*] .env existente encontrado, no se sobreescribe.
)

:: -- Forzar variables de auth internas para el lab
if not defined AUTH_BASE_URL set "AUTH_BASE_URL=http://localhost:8001"
set "AUTH_LOGIN_PATH=/v1/auth/login"
set "AUTH_TIMEOUT_SECONDS=10"
set "AUTH_MANAGEMENT_EMAIL=admin@ycc.local"
set "AUTH_MANAGEMENT_PASSWORD=changeme-secure-password"
set "AUTH_JWT_SECRET=change-me"
set "AUTH_JWT_ALGORITHM=HS256"
set "AUTH_JWT_ISSUER=auth.crm.ycc.internal"
set "AUTH_JWT_AUDIENCE=microtv-platform"
set "AUTO_PROVISION_CRM_ROLE=true"
set "DEFAULT_ADMIN_AUTH_ROLES=admin,platform_admin,company_admin"
set "DEFAULT_DEPOSITO_AUTH_ROLES=operador_deposito,company_operator"
set "DEFAULT_TECH_AUTH_ROLES=tecnico_campo"

echo   [*] Auth lab interno forzado por entorno:
echo       AUTH_BASE_URL=%AUTH_BASE_URL%
echo       AUTH_MANAGEMENT_EMAIL=%AUTH_MANAGEMENT_EMAIL%
echo       AUTH_JWT_ISSUER=%AUTH_JWT_ISSUER%
echo       DEFAULT_ADMIN_AUTH_ROLES=%DEFAULT_ADMIN_AUTH_ROLES%

:: -- Instalar dependencias
echo.
echo   [*] Instalando / verificando dependencias (pip install -e .[test])...
python -m pip install -e .[test] -q
if errorlevel 1 (
    echo.
    echo   ERROR: pip install fallo.
    echo   Verifica que Python 3.12+ este en PATH y que el venv este activo.
    pause
    exit /b 1
)

:: -- Levantar uvicorn
echo.
echo   [*] Iniciando CRM Backend en http://localhost:8010
echo       Presiona Ctrl+C para detener.
echo.
python -m uvicorn crm_backend.main:app --reload --host 0.0.0.0 --port 8010

endlocal
pause
