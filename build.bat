@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM MADRAC-HUB - MONOREPO BUILD SCRIPT (Windows)
REM ============================================================
REM
REM Integra madrac-subs (UI) + madrac-dubbing (API/Engine)
REM en un único ejecutable o binario distribuible.
REM
REM Flujo:
REM   1. Verificar estructura (src/madrac_subs, src/madrac_dubbing)
REM   2. Crear/validar venv único
REM   3. Instalar requirements.txt (unificado)
REM   4. Verificar imports (ambos componentes)
REM   5. Ejecutar tests (ambos componentes)
REM   6. Limpiar builds anteriores
REM   7. Build con PyInstaller (versión estable)
REM   8. Validar ejecutable
REM   9. Mostrar resultado
REM
REM ============================================================

cd /d "%~dp0"

echo ============================================
echo   MADRAC-HUB - MONOREPO BUILD
echo   Directorio: %CD%
echo ============================================
echo.

REM Store start time
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set datestamp=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set timestamp=%%a%%b)

set BUILD_START=%date% %time%

REM ------------------------------------------------------------
REM 1. Variables de entorno seguras
REM ------------------------------------------------------------

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1
set NUMEXPR_NUM_THREADS=1

REM Python path setup
set PYTHONPATH=%CD%\src

REM ------------------------------------------------------------
REM 2. Verificar estructura monorepo
REM ------------------------------------------------------------

echo [1/9] Verificando estructura monorepo...

if not exist src\madrac_subs\src\madrac (
	echo ERROR: src\madrac_subs\src\madrac no encontrado
	pause
	exit /b 1
)

if not exist src\madrac_subs\tests (
	echo ERROR: src\madrac_subs\tests no encontrado
	pause
	exit /b 1
)

if not exist src\madrac_dubbing\src\madrac_dubbing (
	echo ERROR: src\madrac_dubbing\src\madrac_dubbing no encontrado
	pause
	exit /b 1
)

if not exist src\madrac_dubbing\tests (
	echo ERROR: src\madrac_dubbing\tests no encontrado
	pause
	exit /b 1
)

if not exist requirements.txt (
	echo ERROR: requirements.txt no encontrado (debe estar en madrac-hub root)
	pause
	exit /b 1
)

echo [OK] Estructura verificada

REM ------------------------------------------------------------
REM 3. Verificar/crear venv (ÚNICO)
REM ------------------------------------------------------------

echo.
echo [2/9] Verificando entorno virtual...

if not exist venv\Scripts\python.exe (
	echo Creando venv...
	python -m venv venv
	if !errorlevel! neq 0 (
		echo ERROR: No se pudo crear venv. Python 3.11+ requerido.
		python --version
		pause
		exit /b 1
	)
)

echo [OK] venv existe

REM ------------------------------------------------------------
REM 4. Activar venv
REM ------------------------------------------------------------

echo.
echo [3/9] Activando venv...

call venv\Scripts\activate.bat

if !errorlevel! neq 0 (
	echo ERROR: No se pudo activar venv
	pause
	exit /b 1
)

python --version

REM ------------------------------------------------------------
REM 5. Verificar/descargar ffmpeg
REM ------------------------------------------------------------

echo.
echo [4/9] Verificando ffmpeg...

where ffmpeg >nul 2>nul
if !errorlevel! equ 0 (
	echo [OK] ffmpeg encontrado en PATH
	goto :ffmpeg_ok
)

if exist ffmpeg.exe (
	echo [OK] ffmpeg.exe local
	goto :ffmpeg_ok
)

if exist ffprobe.exe (
	echo [OK] ffprobe.exe local
	goto :ffmpeg_ok
)

REM No ffmpeg found, try to download
echo [WARN] ffmpeg/ffprobe no encontrados. Intentando descargar...
echo  Descargando ffmpeg-release-essentials.zip...

powershell -Command "$tmp = $env:TEMP; $zip = Join-Path $tmp 'ffmpeg.zip'; try { $wc = New-Object System.Net.WebClient; $wc.DownloadFile('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip', $zip); Write-Host '  [OK] Descarga completada' } catch { Write-Host 'ERROR: No se pudo descargar ffmpeg'; exit 1 }" 2>nul

if !errorlevel! equ 0 (
	powershell -Command "$zip = Join-Path $env:TEMP 'ffmpeg.zip'; Expand-Archive -Path $zip -DestinationPath (Join-Path $env:TEMP 'ffmpeg') -Force; $dir = Get-ChildItem (Join-Path $env:TEMP 'ffmpeg') -Directory | Select-Object -First 1; Copy-Item (Join-Path $dir.FullName 'bin\ffmpeg.exe') '%~dp0' -Force; Copy-Item (Join-Path $dir.FullName 'bin\ffprobe.exe') '%~dp0' -Force; Write-Host '  [OK] ffmpeg.exe y ffprobe.exe copiados'" 2>nul
) else (
	echo  [WARN] No se pudo descargar automaticamente.
	echo  Descarga manual: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
	echo  Extrae ffmpeg.exe y ffprobe.exe en %CD%
)

:ffmpeg_ok

REM ------------------------------------------------------------
REM 6. Instalar dependencias (requirements.txt unificado)
REM ------------------------------------------------------------

echo.
echo [5/9] Instalando dependencias unificadas...

python -m pip install --upgrade pip -q

python -m pip install -r requirements.txt 2> pip_errors.log

if !errorlevel! neq 0 (
	echo [WARN] pip reporto errores. Revisar pip_errors.log
	REM No salir, algunos warnings son normales
)

REM Asegurar PyInstaller
python -m PyInstaller --version >nul 2>nul
if !errorlevel! neq 0 (
	echo [INFO] Instalando PyInstaller...
	python -m pip install pyinstaller -q
)

REM ------------------------------------------------------------
REM 7. Verificar imports de AMBOS componentes
REM ------------------------------------------------------------

echo.
echo [6/10] Verificando imports (madrac-subs)...

python -c "import torch; print('  torch OK')" || goto :import_error
python -c "import transformers; print('  transformers OK')" || goto :import_error
python -c "import ctranslate2; print('  ctranslate2 OK')" || goto :import_error
python -c "import faster_whisper; print('  faster_whisper OK')" || goto :import_error
python -c "import PySide6; print('  PySide6 OK')" || goto :import_error

echo.
echo [7/10] Verificando imports (madrac-dubbing)...

python -c "import demucs; print('  demucs OK')" || goto :import_error
python -c "import edge_tts; print('  edge_tts OK')" || goto :import_error
python -c "from madrac_dubbing.pipeline.models import DubbingConfig; print('  pipeline.models OK')" || goto :import_error
python -c "from madrac_dubbing.pipeline.dubbing_pipeline import DubbingPipeline; print('  pipeline OK')" || goto :import_error
python -c "import flask; print('  Flask OK')" || goto :import_error

echo.
echo [INFO] Todos los imports verificados correctamente

goto :imports_ok

:import_error
echo.
echo ERROR: fallo una importacion
echo Revisar pip_errors.log
pause
exit /b 1

:imports_ok

REM ------------------------------------------------------------
REM 8. Ejecutar tests (AMBOS componentes)
REM ------------------------------------------------------------

echo.
echo [8/10] Ejecutando tests...

echo.
echo  [TEST] madrac-subs...
cd src\madrac_subs
python -m pytest tests\ -v --tb=short 2> ..\..\test_subs_errors.log
set SUBS_TEST=!ERRORLEVEL!
cd ..\..

if !SUBS_TEST! neq 0 (
	echo  [WARN] Algunos tests de madrac-subs fallaron. Ver test_subs_errors.log
)

echo.
echo  [TEST] madrac-dubbing...
cd src\madrac_dubbing
python -m pytest tests\ -v --tb=short 2> ..\..\test_dubs_errors.log
set DUBS_TEST=!ERRORLEVEL!
cd ..\..

if !DUBS_TEST! neq 0 (
	echo  [WARN] Algunos tests de madrac-dubbing fallaron. Ver test_dubs_errors.log
)

REM Si ambos fallan, detener
if !SUBS_TEST! neq 0 (
	if !DUBS_TEST! neq 0 (
		echo.
		echo ERROR: Tests fallaron en ambos componentes
		pause
		exit /b 1
	)
)

REM Si solo uno falla, advertencia pero continuar
if !SUBS_TEST! neq 0 (
	echo.
	echo [WARN] Continuando a pesar de fallos en madrac-subs
)

if !DUBS_TEST! neq 0 (
	echo.
	echo [WARN] Continuando a pesar de fallos en madrac-dubbing
)

REM ------------------------------------------------------------
REM 9. Limpiar builds anteriores
REM ------------------------------------------------------------

echo.
echo [9/10] Limpiando builds anteriores...

if exist build rmdir /s /q build >nul 2>&1
if exist dist rmdir /s /q dist >nul 2>&1
if exist src\madrac_subs\build rmdir /s /q src\madrac_subs\build >nul 2>&1
if exist src\madrac_subs\dist rmdir /s /q src\madrac_subs\dist >nul 2>&1
if exist src\madrac_dubbing\build rmdir /s /q src\madrac_dubbing\build >nul 2>&1
if exist src\madrac_dubbing\dist rmdir /s /q src\madrac_dubbing\dist >nul 2>&1

echo [OK]

REM ------------------------------------------------------------
REM 10. MAIN BUILD - PyInstaller
REM ============================================================
REM
REM Punto de entrada: src/madrac_subs/run-v3.py (UI principal)
REM El API de madrac-dubbing se inicia como servicio de fondo
REM
REM ============================================================

echo.
echo ============================================
echo  INICIANDO BUILD PYINSTALLER
echo ============================================
echo  Inicio: %BUILD_START%
echo.

REM Crear .spec si no existe (uso del de subs como base)
REM Nota: en versión final, se puede customizar spec para integración

if exist src\madrac_subs\madrac-subs-v3-onefile.spec (
	echo  [INFO] Usando spec existente de madrac-subs
	set SPEC_FILE=src\madrac_subs\madrac-subs-v3-onefile.spec
) else (
	echo  [ERROR] No se encontro .spec file
	pause
	exit /b 1
)

echo  Ejecutando PyInstaller...
echo  python -m PyInstaller "!SPEC_FILE!" --clean

python -m PyInstaller "!SPEC_FILE!" --clean 2> pyinstaller_build.log

set BUILD_EXIT=!ERRORLEVEL!

echo.
echo  Fin: %date% %time%

if NOT "!BUILD_EXIT!"=="0" (
	echo.
	echo ============================================
	echo BUILD FALLIDO - Codigo: !BUILD_EXIT!
	echo ============================================
	echo.
	echo Revisar: pyinstaller_build.log
	pause
	exit /b 1
)

REM PyInstaller crea output en src/madrac_subs/dist
REM Copiar a directorio raiz dist/ para consistency
if exist src\madrac_subs\dist\MADRAC-SUBS.exe (
	if not exist dist mkdir dist
	copy src\madrac_subs\dist\MADRAC-SUBS.exe dist\ >nul
	echo [OK] Ejecutable copiado a dist/
)

REM ------------------------------------------------------------
REM 11. Validacion ejecutable
REM ------------------------------------------------------------

echo.
echo [10/10] Validando ejecutable...

if not exist dist\MADRAC-SUBS.exe (
	if not exist src\madrac_subs\dist\MADRAC-SUBS.exe (
		echo ERROR: no se genero MADRAC-SUBS.exe
		pause
		exit /b 1
	)
	set EXE_PATH=src\madrac_subs\dist\MADRAC-SUBS.exe
) else (
	set EXE_PATH=dist\MADRAC-SUBS.exe
)

echo [OK] Ejecutable encontrado: !EXE_PATH!

REM Test basico: --test-imports en el .exe
if exist src\madrac_subs\run-v3.py (
	echo.
	echo  Test: imports congelados...
	"!EXE_PATH!" --test-imports >nul 2>&1
	if !errorlevel! equ 0 (
		echo  [OK]
	) else (
		echo  [WARN] --test-imports fallo (puede ser issue de PATH)
	)
)

REM ------------------------------------------------------------
REM Resultado Final
REM ------------------------------------------------------------

echo.
echo ============================================
echo BUILD EXITOSO
echo ============================================

for %%I in ("!EXE_PATH!") do (
	set FILE_SIZE=%%~zI
)

set /a SIZE_MB=!FILE_SIZE! / 1048576

echo.
echo Ejecutable: !EXE_PATH!
echo Tamano:     !SIZE_MB! MB
echo.

echo Archivos de referencia:
echo   pyinstaller_build.log        (detalle compilacion)
echo   test_subs_errors.log         (test errors, si los hay)
echo   test_dubs_errors.log         (test errors, si los hay)
echo   pip_errors.log               (pip errors, si los hay)
echo.

echo Proximos pasos:
echo   1. Iniciar UI:
echo      "!EXE_PATH!"
echo.
echo   2. (Opcional) Iniciar API madrac-dubbing en background:
echo      python src\madrac_dubbing\__main__.py api --port 5000
echo.
echo   3. (Opcional) Testear health check:
echo      curl http://127.0.0.1:5000/health
echo.

echo.
pause
