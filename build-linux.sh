#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# MADRAC-HUB — Linux build script (venv + AppImage)
# Requisitos: python3, pip, venv, libfuse2
#
# Basado en: build.bat (Windows) + build_appimage_venv.sh (v2)
# ============================================================

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

VERSION="${VERSION:-3.0.0}"
ARCH="$(uname -m)"
APP_NAME="MADRAC-SUBS"
APPDIR="$ROOT_DIR/dist/${APP_NAME}-v3.AppDir"
OUTPUT="$ROOT_DIR/dist/${APP_NAME}-v3-${VERSION}-${ARCH}.AppImage"

echo "============================================"
echo " MADRAC-HUB — Linux build + AppImage"
echo " Root:       $ROOT_DIR"
echo " Version:    $VERSION"
echo " Arch:       $ARCH"
echo " AppDir:     $APPDIR"
echo " Output:     $OUTPUT"
echo "============================================"

# ─── 0. Verificar estructura monorepo ─────────────
echo ""
echo "[1/9] Verificando estructura monorepo..."

if [ ! -d "src/madrac_subs/src/madrac" ]; then
    echo "ERROR: src/madrac_subs/src/madrac no encontrado"
    exit 1
fi
if [ ! -d "src/madrac_subs/tests" ]; then
    echo "ERROR: src/madrac_subs/tests no encontrado"
    exit 1
fi
if [ ! -d "src/madrac_dubbing/src/madrac_dubbing" ]; then
    echo "ERROR: src/madrac_dubbing/src/madrac_dubbing no encontrado"
    exit 1
fi
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt no encontrado"
    exit 1
fi
echo "  [OK] Estructura verificada"

# ─── 1. Verificar/crear venv ──────────────────────
echo ""
echo "[2/9] Verificando entorno virtual..."

PYTHON=$(which python3.11 2>/dev/null || which python3.12 2>/dev/null || which python3)
echo "  Usando: $PYTHON ($($PYTHON --version 2>&1))"

if [ ! -d venv/bin ]; then
    echo "  Creando venv..."
    $PYTHON -m venv venv
fi
echo "  [OK] venv existe"

# ─── 2. Activar venv ──────────────────────────────
echo ""
echo "[3/9] Activando entorno virtual..."
source venv/bin/activate
python --version

# ─── 3. Verificar ffmpeg ──────────────────────────
echo ""
echo "[4/9] Verificando ffmpeg..."
if command -v ffmpeg &>/dev/null; then
    echo "  [OK] ffmpeg en PATH: $(ffmpeg -version 2>&1 | head -1)"
else
    echo "  [WARN] ffmpeg no encontrado. Instalar: sudo apt install ffmpeg"
fi

# ─── 4. Instalar dependencias ─────────────────────
echo ""
echo "[5/9] Instalando dependencias (puede tardar varios minutos)..."
pip install --upgrade pip -q

# 1. Instalar torch CPU-only PRIMERO (antes que transformers etc)
#    El index CPU de PyTorch tiene versiones sin CUDA
echo "  Instalando torch + torchaudio CPU-only..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu -q

# 2. Instalar el resto de dependencias (pip ve torch ya instalado y no lo toca)
echo "  Instalando resto de dependencias..."
pip install -r requirements-linux.txt -q

echo "  Python: $(python --version)"
echo "  [OK] Dependencias instaladas"

# ─── 5. Verificar imports clave ───────────────────
echo ""
echo "[6/9] Verificando imports..."
python -c "import torch; print('  torch OK')" || { echo "ERROR: torch fallo"; exit 1; }
python -c "import transformers; print('  transformers OK')" || { echo "ERROR: transformers fallo"; exit 1; }
python -c "import ctranslate2; print('  ctranslate2 OK')" || { echo "ERROR: ctranslate2 fallo"; exit 1; }
python -c "import faster_whisper; print('  faster_whisper OK')" || { echo "ERROR: faster_whisper fallo"; exit 1; }
python -c "import PySide6; print('  PySide6 OK')" || { echo "ERROR: PySide6 fallo"; exit 1; }
python -c "import demucs; print('  demucs OK')" || echo "  [WARN] demucs no disponible (opcional)"
python -c "import edge_tts; print('  edge_tts OK')" || echo "  [WARN] edge_tts no disponible (opcional)"
python -c "import flask; print('  Flask OK')" || echo "  [WARN] Flask no disponible (opcional)"

PYTHONPATH="$ROOT_DIR/src/madrac_dubbing/src"
export PYTHONPATH
python -c "from madrac_dubbing.pipeline.models import DubbingConfig; print('  dubbing.models OK')" || \
    echo "  [WARN] dubbing.models fallo (opcional)"
PYTHONPATH="$ROOT_DIR/src"
export PYTHONPATH
echo "  [OK] Todos los imports verificados"

# ─── 6. Ejecutar tests ────────────────────────────
echo ""
echo "[7/9] Ejecutando tests..."

echo "  [TEST] madrac-subs..."
PYTHONPATH="$ROOT_DIR/src/madrac_subs/src" \
    python -m pytest src/madrac_subs/tests/ -v --tb=short \
    -m "not real" 2>&1 | tail -20 || echo "  [WARN] Fallaron algunos tests de madrac-subs"

echo "  [TEST] madrac-dubbing..."
PYTHONPATH="$ROOT_DIR/src/madrac_dubbing/src" \
    python -m pytest src/madrac_dubbing/tests/ -v --tb=short \
    2>&1 | tail -20 || echo "  [WARN] Fallaron algunos tests de madrac-dubbing"

# ─── 7. Preparar tools para AppImage ──────────────
echo ""
echo "[8/9] Preparando herramientas AppImage..."

mkdir -p "$ROOT_DIR/tools"

APPIMAGETOOL="$ROOT_DIR/tools/appimagetool"
RUNTIME_FILE="$ROOT_DIR/tools/type2-runtime"

if [ ! -f "$APPIMAGETOOL" ]; then
    echo "  Descargando appimagetool..."
    if [ "$ARCH" = "x86_64" ]; then
        APPIMAGE_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    elif [ "$ARCH" = "aarch64" ]; then
        APPIMAGE_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-aarch64.AppImage"
    else
        echo "ERROR: Arquitectura no soportada: $ARCH"
        exit 1
    fi
    wget -q -O "$APPIMAGETOOL" "$APPIMAGE_URL"
    chmod +x "$APPIMAGETOOL"
    echo "  [OK] appimagetool descargado"
fi

if [ ! -f "$RUNTIME_FILE" ]; then
    echo "  Descargando type2-runtime..."
    wget -q -O "$RUNTIME_FILE" \
        "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
    echo "  [OK] type2-runtime descargado"
fi

# Extraer appimagetool si no hay FUSE
APPIMAGETOOL_RUN="$APPIMAGETOOL"
if ! "$APPIMAGETOOL_RUN" --version >/dev/null 2>&1; then
    echo "  appimagetool no puede ejecutarse (sin FUSE). Extrayendo..."
    (
        cd "$ROOT_DIR/tools"
        ./appimagetool --appimage-extract >/dev/null 2>&1 || true
    )
    APPIMAGETOOL_RUN="$ROOT_DIR/tools/squashfs-root/AppRun"
fi

# ─── 8. Generar AppImage ──────────────────────────
echo ""
echo "[9/9] Generando AppImage..."

# Limpiar builds anteriores
rm -rf "$APPDIR" "$OUTPUT"

# Leer info del Python del venv
VENV_PY="venv/bin/python"
readarray -t PY_INFO < <("$VENV_PY" - <<'PY'
import os, site, sys, sysconfig
print(f"{sys.version_info.major}.{sys.version_info.minor}")
print(os.path.realpath(sys.executable))
print(sysconfig.get_path("stdlib"))
print(sysconfig.get_config_var("DESTSHARED") or "")
paths = [p for p in site.getsitepackages() if p.endswith("site-packages")]
if not paths:
    raise SystemExit("No se encontro site-packages del venv")
print(paths[0])
PY
)

PY_VER="${PY_INFO[0]}"
PYTHON_BIN="${PY_INFO[1]}"
PY_STDLIB="${PY_INFO[2]}"
PY_DYNLIB="${PY_INFO[3]}"
SITE_PACKAGES="${PY_INFO[4]}"

echo "  Python:     $PYTHON_BIN"
echo "  Python ver: $PY_VER"
echo "  stdlib:     $PY_STDLIB"
echo "  packages:   $SITE_PACKAGES"

# Crear AppDir
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/opt/madrac-hub"

# Copiar codigo del proyecto (excluyendo venv, builds, etc.)
echo "  Copiando codigo del proyecto..."
rsync -a --no-owner --no-group \
    --exclude '/.git/' \
    --exclude '/venv/' \
    --exclude '/build/' \
    --exclude '/dist/' \
    --exclude '/tools/' \
    --exclude '/.cache/' \
    --exclude '/.vs/' \
    --exclude '/.github/' \
    --exclude '/.cursor/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude '*.log' \
    --exclude '.coverage' \
    "$ROOT_DIR/" "$APPDIR/opt/madrac-hub/"

# Copiar runtime Python
echo "  Copiando runtime Python..."
cp -L "$PYTHON_BIN" "$APPDIR/usr/bin/python3"
chmod +x "$APPDIR/usr/bin/python3"

mkdir -p "$APPDIR/usr/lib/python${PY_VER}"
rsync -a --copy-links --no-owner --no-group \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude '/test/' \
    --exclude '/tests/' \
    --exclude '/idlelib/' \
    --exclude '/tkinter/' \
    --exclude '/ensurepip/' \
    "$PY_STDLIB/" "$APPDIR/usr/lib/python${PY_VER}/"

if [[ -n "$PY_DYNLIB" && -d "$PY_DYNLIB" && "$PY_DYNLIB" != "$PY_STDLIB"* ]]; then
    mkdir -p "$APPDIR/usr/lib/python${PY_VER}/lib-dynload"
    rsync -a --copy-links --no-owner --no-group \
        "$PY_DYNLIB/" "$APPDIR/usr/lib/python${PY_VER}/lib-dynload/"
fi

# Copiar site-packages del venv
echo "  Copiando dependencias del venv..."
mkdir -p "$APPDIR/opt/madrac-hub/venv/lib/python${PY_VER}/site-packages"
rsync -a --copy-links --no-owner --no-group \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude '*.dist-info/' \
    --exclude 'nvidia/' \
    --exclude 'PySide6/Qt/qml/' \
    --exclude 'PySide6/Qt/plugins/webengine/' \
    --exclude 'PySide6/Qt/plugins/webview/' \
    --exclude 'PySide6/Qt/plugins/geoservices/' \
    --exclude 'PySide6/Qt/plugins/position/' \
    --exclude 'PySide6/Qt/plugins/sensors/' \
    --exclude 'PySide6/Qt/plugins/playlistformats/' \
    --exclude 'PySide6/Qt/plugins/render/' \
    --exclude 'PySide6/Qt/plugins/generic/' \
    --exclude 'PySide6/Qt/plugins/sqldrivers/' \
    --exclude 'PySide6/Qt/plugins/designer/' \
    --exclude 'tests/' \
    --exclude 'test/' \
    "$SITE_PACKAGES/" "$APPDIR/opt/madrac-hub/venv/lib/python${PY_VER}/site-packages/"

# Stripear .so para reducir peso
echo "  Stripeando librerias (.so)..."
find "$APPDIR/opt/madrac-hub/venv" -name '*.so' -type f -exec strip --strip-unneeded {} \; 2>/dev/null || true
find "$APPDIR/usr/lib" -name '*.so' -type f -exec strip --strip-unneeded {} \; 2>/dev/null || true

# Crear iconos y metadata
echo "  Creando metadata AppImage..."
if [ -f "src/madrac_subs/ui/madrac-subs.png" ]; then
    cp "src/madrac_subs/ui/madrac-subs.png" "$APPDIR/madrac-subs.png"
    cp "src/madrac_subs/ui/madrac-subs.png" "$APPDIR/.DirIcon"
fi

cat > "$APPDIR/${APP_NAME}.desktop" <<'DESKTOP_EOF'
[Desktop Entry]
Name=MADRAC-SUBS
Comment=Transcripcion, traduccion y edicion de subtitulos con IA
Exec=AppRun
Icon=madrac-subs
Terminal=false
Type=Application
Categories=AudioVideo;Utility;
StartupNotify=true
DESKTOP_EOF

# Crear AppRun
cat > "$APPDIR/AppRun" <<APP_RUN_EOF
#!/usr/bin/env bash
set -euo pipefail

HERE="\$(dirname "\$(readlink -f "\$0")")"
APPROOT="\$HERE/opt/madrac-hub"
PY_VER="$PY_VER"
SITE_PACKAGES="\$APPROOT/venv/lib/python\${PY_VER}/site-packages"
SRC_DIR="\$APPROOT/src"

export PYTHONNOUSERSITE=1
export PYTHONPATH="\$SRC_DIR:\$SRC_DIR/madrac_subs/src:\$SITE_PACKAGES"
export PATH="\$HERE/usr/bin:\$PATH"

export LD_LIBRARY_PATH="\$HERE/usr/lib:\$SITE_PACKAGES/PySide6/Qt/lib:\$SITE_PACKAGES/PySide6:\$SITE_PACKAGES/shiboken6:\$SITE_PACKAGES/torch/lib:\$SITE_PACKAGES/ctranslate2:\$SITE_PACKAGES/onnxruntime/capi:\$SITE_PACKAGES/av.libs:\${LD_LIBRARY_PATH:-}"
export QT_PLUGIN_PATH="\$SITE_PACKAGES/PySide6/Qt/plugins:\$SITE_PACKAGES/PySide6/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="\$SITE_PACKAGES/PySide6/Qt/plugins/platforms:\$SITE_PACKAGES/PySide6/plugins/platforms"
export QML2_IMPORT_PATH="\$SITE_PACKAGES/PySide6/Qt/qml:\$SITE_PACKAGES/PySide6/qml"

export OMP_NUM_THREADS="\${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="\${MKL_NUM_THREADS:-1}"
export TOKENIZERS_PARALLELISM="\${TOKENIZERS_PARALLELISM:-false}"

if [[ -z "\${XDG_CACHE_HOME:-}" ]]; then
    export XDG_CACHE_HOME="\${HOME:-/tmp}/.cache"
fi
mkdir -p "\$XDG_CACHE_HOME/madrac-subs" 2>/dev/null || {
    export XDG_CACHE_HOME="\${TMPDIR:-/tmp}/madrac-subs-cache"
    mkdir -p "\$XDG_CACHE_HOME/madrac-subs" 2>/dev/null || true
}

exec "\$HERE/usr/bin/python3" "\$SRC_DIR/madrac_subs/run-v3.py" "\$@"
APP_RUN_EOF
chmod +x "$APPDIR/AppRun"

# Generar AppImage
echo ""
echo "  Generando AppImage..."
echo "    $OUTPUT"
"$APPIMAGETOOL_RUN" --runtime-file "$RUNTIME_FILE" "$APPDIR" "$OUTPUT" 2>&1

if [ -f "$OUTPUT" ]; then
    chmod +x "$OUTPUT"
    echo ""
    echo "============================================"
    echo "  BUILD EXITOSO"
    echo "  AppImage: $OUTPUT"
    LSIZE=$(ls -lh "$OUTPUT" | awk '{print $5}')
    echo "  Tamano: $LSIZE"
    echo "============================================"
    echo ""
    echo "  Para ejecutar:"
    echo "    $OUTPUT"
    echo ""
    echo "  Limpiando temporales..."
    rm -rf "$APPDIR" "$ROOT_DIR/tools/squashfs-root"
    echo "  [OK] Limpieza completa"
else
    echo "ERROR: No se pudo crear el AppImage"
    exit 1
fi
