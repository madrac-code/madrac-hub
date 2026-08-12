@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set HUB_DIR=D:\madrac-hub

echo ============================================
echo   MADRAC-SUBS V3 - desde monorepo HUB
echo   Directorio: %HUB_DIR%
echo ============================================
echo.

if not exist "%HUB_DIR%\venv\Scripts\activate.bat" (
    echo ERROR: venv no encontrado en %HUB_DIR%\venv
    echo Ejecuta primero: build.bat
    pause
    exit /b 1
)

if not exist "%HUB_DIR%\src\madrac_subs\src\madrac" (
    echo ERROR: src\madrac_subs\src\madrac no encontrado
    pause
    exit /b 1
)

call "%HUB_DIR%\venv\Scripts\activate.bat"

set PYTHONPATH=%HUB_DIR%\src\madrac_subs\src;%PYTHONPATH%

cd /d "%HUB_DIR%\src\madrac_subs"

echo Iniciando MADRAC-SUBS...
echo.

python -m madrac

if !errorlevel! neq 0 (
    echo.
    echo ERROR: La aplicacion se cerro con error (codigo: !errorlevel!)
    pause
    exit /b 1
)
