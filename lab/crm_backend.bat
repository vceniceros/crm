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
