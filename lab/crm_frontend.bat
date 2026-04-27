@echo off
setlocal

:: =========================================================
::  CRM Frontend Angular - arranque de laboratorio
::  Invocado desde lab_start.bat en ventana separada.
::  No ejecutes este script directamente.
:: =========================================================

set "LAB_DIR=%~dp0"
set "FRONTEND_DIR=%LAB_DIR%..\microtv-crm-frontend"

echo =========================================================
echo   CRM Frontend Angular - Laboratorio (puerto 4200)
echo =========================================================
echo.

:: -- Validar directorio del frontend
if not exist "%FRONTEND_DIR%\package.json" (
    echo   ERROR: No se encontro microtv-crm-frontend\package.json
    echo   Directorio esperado: %FRONTEND_DIR%
    pause
    exit /b 1
)

cd /d "%FRONTEND_DIR%"

:: -- Verificar Node.js
node --version > nul 2>&1
if errorlevel 1 (
    echo   ERROR: Node.js no encontrado en PATH.
    echo   Instala Node.js 20+ desde https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo   [*] Node.js %%v

:: -- Instalar dependencias npm
echo.
echo   [*] Instalando dependencias (npm install)...
call npm install
if errorlevel 1 (
    echo.
    echo   ERROR: npm install fallo.
    echo   Verifica conexion a internet o intenta borrar node_modules y reintentar.
    pause
    exit /b 1
)

:: -- Levantar ng serve
echo.
echo   [*] Iniciando Angular en http://localhost:4200
echo       El frontend apunta al CRM Backend en http://localhost:8010
echo       (configurado en src/app/core/config/crm-api.config.ts)
echo.
echo       Presiona Ctrl+C para detener.
echo.
call npm start

endlocal
pause
