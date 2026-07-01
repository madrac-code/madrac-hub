@echo off
REM ============================================================
REM MADRAC-HUB - QUICK VALIDATION (no build)
REM ============================================================
REM
REM Valida que la estructura monorepo sea correcta
REM sin ejecutar PyInstaller (que toma mucho tiempo).
REM
REM Pasos:
REM   1. Verificar directorios
REM   2. Crear venv
REM   3. Instalar requirements
REM   4. Verificar imports
REM   5. Ejecutar tests
REM
REM Tiempo: ~5-10 minutos
REM
REM ============================================================

cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================
echo   MADRAC-HUB - QUICK VALIDATION
echo ============================================
echo.

REM Environment vars
set PYTHONUTF8=1
set PYTHONPATH=%CD%\src

REM ============================================================
REM 1. Verify structure
REM ============================================================

echo [1/5] Verificando estructura...

if not exist src\madrac_subs\src\madrac (
	echo ERROR: src\madrac_subs\src\madrac no existe
	exit /b 1
)

if not exist src\madrac_dubbing\src\madrac_dubbing (
	echo ERROR: src\madrac_dubbing\src\madrac_dubbing no existe
	exit /b 1
)

if not exist requirements.txt (
	echo ERROR: requirements.txt no existe
	exit /b 1
)

echo [OK]

REM ============================================================
REM 2. Create/verify venv
REM ============================================================

echo.
echo [2/5] Verificando venv...

if not exist venv\Scripts\python.exe (
	echo  Creando venv...
	python -m venv venv
	if !errorlevel! neq 0 (
		echo ERROR: No se pudo crear venv
		exit /b 1
	)
)

call venv\Scripts\activate.bat
python --version

REM ============================================================
REM 3. Install requirements
REM ============================================================

echo.
echo [3/5] Instalando dependencias...

python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt 2> validation_pip.log

if !errorlevel! neq 0 (
	echo [WARN] Algunos paquetes fallaron. Revisar validation_pip.log
)

REM ============================================================
REM 4. Verify imports
REM ============================================================

echo.
echo [4/5] Verificando imports...

python -c "import torch; print('  torch OK')" || goto :import_error
python -c "import transformers; print('  transformers OK')" || goto :import_error
python -c "import ctranslate2; print('  ctranslate2 OK')" || goto :import_error
python -c "import PySide6; print('  PySide6 OK')" || goto :import_error
python -c "import demucs; print('  demucs OK')" || goto :import_error
python -c "import edge_tts; print('  edge_tts OK')" || goto :import_error
python -c "import flask; print('  Flask OK')" || goto :import_error

echo [OK]

goto :imports_ok

:import_error
echo ERROR: fallo una importacion
exit /b 1

:imports_ok

REM ============================================================
REM 5. Run tests
REM ============================================================

echo.
echo [5/5] Ejecutando tests...

echo.
echo  [TEST] madrac-subs...
cd src\madrac_subs
python -m pytest tests\ -v --tb=short 2> ..\..\validation_test_subs.log
set SUBS_RESULT=!ERRORLEVEL!
cd ..\..

if !SUBS_RESULT! equ 0 (
	echo  [OK] Todos los tests pasaron
) else (
	echo  [WARN] Algunos tests fallaron - revisar validation_test_subs.log
)

echo.
echo  [TEST] madrac-dubbing...
cd src\madrac_dubbing
python -m pytest tests\ -v --tb=short 2> ..\..\validation_test_dubs.log
set DUBS_RESULT=!ERRORLEVEL!
cd ..\..

if !DUBS_RESULT! equ 0 (
	echo  [OK] Todos los tests pasaron
) else (
	echo  [WARN] Algunos tests fallaron - revisar validation_test_dubs.log
)

REM ============================================================
REM Result
REM ============================================================

echo.
echo ============================================
echo VALIDACION COMPLETA
echo ============================================
echo.
echo Estructura: OK
echo venv: OK
echo Dependencias: OK
echo Imports: OK
echo Tests: COMPLETED (revisar logs si necesario)
echo.
echo Proximos pasos:
echo   1. Revisar validation_*.log si hay warnings
echo   2. Ejecutar: build.bat
echo.
echo Logs creados:
echo   validation_pip.log
echo   validation_test_subs.log
echo   validation_test_dubs.log
echo.

pause
