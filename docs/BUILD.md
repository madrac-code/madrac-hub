# MADRAC-HUB Build Guide

## Overview

MADRAC-HUB es un **monorepo** que integra:
- **madrac-subs**: UI (PySide6) + Speech-to-Text + Translation
- **madrac-dubbing**: API/Engine + Audio Processing + Speech Synthesis

El build unificado (`build.bat`) crea un único ejecutable (`MADRAC-SUBS.exe`) que:
1. Inicia la interfaz gráfica (UI)
2. Puede comunicar con la API de madrac-dubbing (en background o como servicio)

---

## Requisitos

### Sistema Operativo
- Windows 10 / Windows 11 (x86-64)

### Software Requerido
- **Python 3.11+** (testeado en 3.14)
  - Descarga: https://www.python.org/downloads/
  - **Importante**: Marcar "Add Python to PATH" durante instalación

- **Git** (para clonar el repo)
  - Descarga: https://git-scm.com/

- **Visual C++ Build Tools** (para compilar extensiones C)
  - Incluido en Visual Studio Community (recomendado)
  - O: https://visualstudio.microsoft.com/downloads/ → "Desktop development with C++"

- **FFmpeg** (para procesamiento de audio/video)
  - Auto-descargado durante build.bat
  - O manual: https://www.gyan.dev/ffmpeg/builds/

### Espacio en Disco
- ~10 GB (venv + PyTorch + Demucs + models)
- ~500 MB (ejecutable final)

---

## Build Step-by-Step

### 1. Clonar el Repositorio

```powershell
git clone https://github.com/madrac-code/madrac-hub.git
cd madrac-hub
```

### 2. Ejecutar build.bat

Desde la carpeta raíz de madrac-hub:

```cmd
build.bat
```

**El script hará**:
1. ✅ Verificar estructura (src/madrac_subs, src/madrac_dubbing)
2. ✅ Crear venv (si no existe)
3. ✅ Instalar requirements.txt (unificado)
4. ✅ Verificar imports de ambos componentes
5. ✅ Ejecutar tests (pytest)
6. ✅ Limpiar builds anteriores
7. ✅ Compilar con PyInstaller
8. ✅ Validar ejecutable
9. ✅ Mostrar resultado

**Tiempo estimado**: 15-30 minutos (depende de velocidad de internet y hardware)

### 3. Ejecutable Final

Ubicación: `dist\MADRAC-SUBS.exe`

```cmd
dist\MADRAC-SUBS.exe
```

O desde directorio de componentes:

```cmd
src\madrac_subs\dist\MADRAC-SUBS.exe
```

---

## Troubleshooting

### Error: "Python no encontrado"
**Solución**: Asegurate de haber marcado "Add Python to PATH" durante instalación.
```cmd
python --version
```
Si no funciona, agrega Python a PATH manualmente:
- Control Panel → System → Environment Variables
- Agrega: `C:\Users\<YourUser>\AppData\Local\Programs\Python\Python314`

### Error: "ModuleNotFoundError: No module named 'X'"
**Solución**: El requirements.txt no se instaló correctamente.
```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Error: "FFmpeg not found"
**Solución**: build.bat intenta descargar automáticamente. Si falla:
1. Descargar manualmente: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
2. Extraer `ffmpeg.exe` y `ffprobe.exe` en `D:\madrac-hub\`
3. Reintentar `build.bat`

### Error: "PyInstaller failed"
**Solución**: Revisar `pyinstaller_build.log`
```cmd
type pyinstaller_build.log
```
Problemas comunes:
- Permisos de carpeta (ejecutar PowerShell/CMD como Admin)
- Antivirus bloqueando (desactivar temporalmente)
- Disco lleno (liberar espacio)

### Error: "Tests failed"
**Solución**: Revisar logs de tests:
```cmd
type test_subs_errors.log
type test_dubs_errors.log
```
Los warnings no detienen el build. Solo errores críticos.

### Lentitud extrema
**Solución**: Probable descarga de PyTorch/Demucs models
- Primera compilación es lenta (~30-60 min)
- Compilaciones posteriores usan cache (más rápido)
- Considera usar GPU si está disponible

---

## Desarrollo Local (Sin Build)

Si quieres correr madrac-subs o madrac-dubbing sin compilar:

### madrac-subs (UI)

```cmd
cd src\madrac_subs
python run-v3.py
```

### madrac-dubbing (API)

```cmd
cd src\madrac_dubbing
python -m madrac_dubbing.main api --port 5000
```

Luego en otra terminal:
```cmd
curl http://127.0.0.1:5000/health
```

---

## Estructura del Monorepo

```
D:\madrac-hub\
├── build.bat                    ← Script principal de build
├── requirements.txt             ← Dependencias unificadas
├── .gitignore                   ← Git ignore rules
│
├── src/
│   ├── madrac_subs/             ← Componente UI
│   │   ├── src/madrac/          ← Código fuente
│   │   ├── tests/               ← Tests
│   │   ├── requirements.txt     ← (local, no usar)
│   │   └── run-v3.py            ← Entry point UI
│   │
│   └── madrac_dubbing/          ← Componente API/Engine
│       ├── src/madrac_dubbing/  ← Código fuente
│       ├── tests/               ← Tests
│       ├── requirements.txt     ← (local, no usar)
│       └── __main__.py          ← Entry point API
│
├── docs/
│   ├── BUILD.md                 ← Este archivo
│   └── ...
│
├── knowledge/
│   ├── decisions/
│   │   ├── ADR_001.md
│   │   ├── ADR_008_monorepo_integration.md
│   │   └── ...
│   └── ...
│
└── venv/                        ← Virtual environment (único)
```

---

## Environment Variables (Opcional)

Crear `D:\madrac-hub\.env`:

```
# Speech Synthesis
EDGE_TTS_VOICE=es-ES-AlvaroNeural

# API
MADRAC_DUBS_HOST=127.0.0.1
MADRAC_DUBS_PORT=5000

# Logging
LOG_LEVEL=INFO
```

---

## Next Steps

Una vez que tengas `dist\MADRAC-SUBS.exe`:

1. **Distribución**: Empaquetar .exe (ZIP, installer, etc.)
2. **Testing**: Probar features end-to-end
3. **CI/CD**: Automatizar builds en GitHub Actions
4. **Nuitka**: Experimento alternativo a PyInstaller (TBD)

---

## Support

Si encuentras problemas:
1. Revisar `pyinstaller_build.log`, `pip_errors.log`
2. Revisar ADR_008_monorepo_integration.md (decisiones de arquitectura)
3. Revisar HANDOFF_MONOREPO_INTEGRATION.md (contexto técnico)

---

## Versiones Testeadas

| Software | Versión | Status |
|----------|---------|--------|
| Python | 3.14 | ✅ Experimental but working |
| PyInstaller | 6.20+ | ✅ Estable |
| PySide6 | 6.8+ | ✅ Estable |
| PyTorch | 2.5+ | ✅ Estable |
| Demucs | 4.0+ | ✅ Estable |
| Windows | 10/11 x86-64 | ✅ Testeado |

---

**Última actualización**: 2026-07-01
