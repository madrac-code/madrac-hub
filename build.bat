@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1
set NUMEXPR_NUM_THREADS=1

set PYTHONPATH=%CD%\src

echo ============================================
echo   MADRAC-HUB - MONOREPO BUILD
echo   Directorio: %CD%
echo ============================================
echo.

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set datestamp=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set timestamp=%%a%%b)
set BUILD_START=%date% %time%

echo [1/9] Verificando estructura monorepo...
if not exist src\madrac_subs\src\madrac (
    echo ERROR: src\madrac_subs\src\madrac no encontrado
    pause
    exit /b 1
)
if not exist src\madrac_subs\tests (
    echo ERROR: src\madrac_subs\tests no encontrado
    exit /b 1
)
if not exist src\madrac_dubbing\src\madrac_dubbing (
    echo ERROR: src\madrac_dubbing\src\madrac_dubbing no encontrado
    exit /b 1
)
if not exist src\madrac_dubbing\tests (
    echo ERROR: src\madrac_dubbing\tests no encontrado
    exit /b 1
)
if not exist requirements.txt (
    echo ERROR: requirements.txt no encontrado
    exit /b 1
)
echo [OK] Estructura verificada

echo.
echo [2/9] Verificando entorno virtual...
if not exist venv\Scripts\python.exe (
    echo Creando venv...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo ERROR: No se pudo crear venv
        python --version
        exit /b 1
    )
)
echo [OK] venv existe

echo.
echo [3/9] Activando venv...
call venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo ERROR: No se pudo activar venv
    exit /b 1
)
python --version

echo.
echo [4/9] Verificando ffmpeg...
where ffmpeg >nul 2>nul
if !errorlevel! equ 0 (
    echo [OK] ffmpeg en PATH
) else (
    if exist ffmpeg.exe (
        echo [OK] ffmpeg.exe local
    ) else (
        echo [WARN] ffmpeg no encontrado
    )
)

echo.
echo [5/9] Instalando dependencias...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if !errorlevel! neq 0 (
    echo [WARN] pip reporto errores. Revisar requisitos
    pause
    exit /b 1
)

echo.
echo [6/9] Verificando imports...
python -c "import torch; print('  torch OK')" || goto :import_error
python -c "import transformers; print('  transformers OK')" || goto :import_error
python -c "import ctranslate2; print('  ctranslate2 OK')" || goto :import_error
python -c "import faster_whisper; print('  faster_whisper OK')" || goto :import_error
python -c "import PySide6; print('  PySide6 OK')" || goto :import_error
python -c "import demucs; print('  demucs OK')" || goto :import_error
python -c "import edge_tts; print('  edge_tts OK')" || goto :import_error
python -c "import flask; print('  Flask OK')" || goto :import_error
set PYTHONPATH=%CD%\src\madrac_dubbing\src
python -c "from madrac_dubbing.pipeline.models import DubbingConfig; print('  pipeline.models OK')" || goto :import_error
set PYTHONPATH=%CD%\src
echo [INFO] Todos los imports verificados
goto :imports_ok

:import_error
echo.
echo ERROR: fallo una importacion
pause
exit /b 1

:imports_ok

echo.
echo [7/9] Ejecutando tests...
echo.
echo  [TEST] madrac-subs...
set PYTHONPATH=%CD%\src\madrac_subs\src
cd src\madrac_subs
python -m pytest tests\ -v --tb=short > ..\..\test_subs_errors.log 2>&1
set SUBS_TEST=!errorlevel!
cd ..\..
set PYTHONPATH=%CD%\src
if !SUBS_TEST! neq 0 (
    echo  [WARN] Fallaron tests de madrac-subs -- resumen:
    type test_subs_errors.log | findstr /c:"FAILED" /c:"ERROR" /c:"error!" 2>nul
)

echo.
echo  [TEST] madrac-dubbing...
set PYTHONPATH=%CD%\src\madrac_dubbing\src
cd src\madrac_dubbing
python -m pytest tests\ -v --tb=short > ..\..\test_dubs_errors.log 2>&1
set DUBS_TEST=!errorlevel!
cd ..\..
set PYTHONPATH=%CD%\src
if !DUBS_TEST! neq 0 (
    echo  [WARN] Fallaron tests de madrac-dubbing
)

if !SUBS_TEST! neq 0 (
    if !DUBS_TEST! neq 0 (
        echo ERROR: Tests fallaron en ambos componentes
        pause
        exit /b 1
    )
)

echo.
echo [8/9] Limpiando builds...
if exist build rmdir /s /q build >nul 2>&1
if exist dist rmdir /s /q dist >nul 2>&1
if exist src\madrac_subs\build rmdir /s /q src\madrac_subs\build >nul 2>&1
if exist src\madrac_subs\dist rmdir /s /q src\madrac_subs\dist >nul 2>&1
if exist src\madrac_dubbing\build rmdir /s /q src\madrac_dubbing\build >nul 2>&1
if exist src\madrac_dubbing\dist rmdir /s /q src\madrac_dubbing\dist >nul 2>&1
echo [OK]

echo.
echo ============================================
echo  INICIANDO BUILD PYINSTALLER
echo ============================================
echo  Inicio: %BUILD_START%
echo.

if exist src\madrac_subs\madrac-subs-v3-onefile.spec (
    set SPEC_FILE=src\madrac_subs\madrac-subs-v3-onefile.spec
) else (
    echo [ERROR] No se encontro spec file
    pause
    exit /b 1
)

python -m PyInstaller "!SPEC_FILE!" --clean > pyinstaller_build.log 2>&1
set BUILD_EXIT=!errorlevel!

if NOT "!BUILD_EXIT!"=="0" (
    echo BUILD FALLIDO - Codigo: !BUILD_EXIT!
    echo Revisar: pyinstaller_build.log
    pause
    exit /b 1
)

if exist src\madrac_subs\dist\MADRAC-SUBS.exe (
    if not exist dist mkdir dist
    copy src\madrac_subs\dist\MADRAC-SUBS.exe dist\ >nul
)

echo.
echo [9/9] Validando ejecutable...
if exist dist\MADRAC-SUBS.exe (
    set EXE_PATH=dist\MADRAC-SUBS.exe
) else (
    if exist src\madrac_subs\dist\MADRAC-SUBS.exe (
        set EXE_PATH=src\madrac_subs\dist\MADRAC-SUBS.exe
    ) else (
        echo ERROR: no se genero MADRAC-SUBS.exe
        pause
        exit /b 1
    )
)

echo [OK] Ejecutable: !EXE_PATH!
for %%I in ("!EXE_PATH!") do set FILE_SIZE=%%~zI
set /a SIZE_MB=!FILE_SIZE! / 1048576
echo Tamano: !SIZE_MB! MB

echo.
echo ============================================
echo BUILD EXITOSO
echo ============================================
echo.
echo Ejecutable: !EXE_PATH!
echo Tamano:     !SIZE_MB! MB
echo.
echo Archivos de salida:
echo   pyinstaller_build.log
echo   test_subs_errors.log
echo   test_dubs_errors.log
echo.
echo Presione una tecla para salir...
pause >nul
echo.
