# HISTORIA DE MADRAC-SUBS

## Resumen

MADRAC-SUBS es el componente más maduro del ecosistema, con 48+ commits y evolución desde v1.0 hasta v3.0.0-rc1. Es un motor de subtitulación que integra transcripción Whisper, traducción MarianMT y características de comunidad.

## Línea de Tiempo Completa

### Fundación (28-31 mayo 2026)

**28 de mayo 2026**
- Infraestructura inicial: `.gitignore`, `config`, `requirements.txt`, scripts de instalación
- Commits: `3c0be7c`, `ffa6202`, `7674be4`, `3d46b09`, `f98c9d0`, `31a6f30`
- Funcionalidad básica: GUI, worker, queue manager, config, utils
- Stack: PySide6, faster-whisper, transformers, torch
- Plataformas: Windows, Linux, macOS

**31 de mayo 2026**
- `a469321` - Fix build: revert subprocess worker, auto-install deps
- Scripts: `build_windows.bat`, `instalar.bat`

### Primeras Versiones (1-2 junio 2026)

**1 de junio 2026**
- `7d0aa1f` - Build: ONEFILE spec, icons, desktop entry
- `1dc2339` - Docs: prompt files for AI agent
- `9583432` - Instalador Windows pre-venv

**2 de junio 2026** - **Versiones Oficiales**
- `4498ebc` - **v1.0**: Funcional en Windows
- `e9bff9d` - **v1.1**: Limpieza de código
- `467d636` - Fix: PySide6+torch crash
- `6e2c11a` - **v1.1**: App funcional Windows y Linux

### Maduración (3-4 junio 2026)

**3 de junio 2026**
- `b895c8a` - Instrumentación: Profiler/Heartbeat
- `a243829` - Corrector subtítulos con QGraphicsView
- `6e84c87` - UI final: splitter 3 paneles, barra animada
- `4df4c79` - Toast notifications animadas
- `4c5495c`, `5ae9e62` - **v2.0, v2.3**

**4 de junio 2026** - **Comunidad Fase 1 y 2**
- `bc3f39a` - Comunidad Fase1: Google OAuth, toggle Online/Offline
- `43349c5` - Phase 1.5: estabilización, cancellation, FK violation
- `deaca1d` - Phase 2: compartir/buscar subtítulos
- `1f940a9` - Contexto completo IA
- `161614c` - Persistencia de cola
- `e4f6d9f` - Hotfix: temp_path

### v3 Release (6-7 junio 2026)

**6 de junio 2026**
- `e7c49e1` - Status bar, plugin system, window geometry
- `1d678ad` - COM DropHandler nativo

**7 de junio 2026** - **v3.0.0-rc1**
- `5be7719` - Pipeline completo: mux/demux/strip/probe, UI, build
- `c5ad21a` - Gitignore

### Madurez y Expansión (22-25 junio 2026)

**22 de junio 2026**
- `722de56` - COM DropHandler fix, shell verbs
- `9ad1248` - v3: UTF-8 safety, config fixes

**23 de junio 2026**
- `bedc952` - Language detection fix, Dutch support
- `13fa282` - Embedded sub track selection, dynamic translator
- `5266749` - Translator fallback

**24 de junio 2026** - **Gran Actualización**
- `cc6a788` - MarianMT HEAD-check, Gemini/LibreTranslate, Google GenAI
- `9eaa1b3` - **i18n**: 7 language dicts, auto-detect
- `1de16be` - UI wrapp: 12 archivos con _(...)
- `c811f5f` - Diccionario inglés completo
- `0d0c97e` - Normalización separada
- `c65a991` - **Phase 1.1**: Testing foundation + CI/CD
- `01abeb4` - Docs: Entry point architecture
- `25fbb19` - Docs: Torch frozen bug analysis
- `36408cc` - Phase 1.6: Pin dependencies
- `18e97e2` - Docs: DUBBING EXTENSION AGENT PROMPT
- `c5d4f30` - Docs: DUBBING EXTENSION USAGE GUIDE

## Evolución de Características

| Versión | Fecha | Características Clave |
|---------|-------|----------------------|
| Pre-v1.0 | 28-31 mayo | Infraestructura, GUI básica, worker, queue |
| v1.0 | 2 junio | Funcional en Windows, PyInstaller build |
| v1.1 | 2 junio | Linux support, PySide6+torch fix |
| v2.0 | 3 junio | Corrector subtítulos, UI 3 paneles |
| v2.3 | 3 junio | Profiler, instrumentación |
| v3.0.0-rc1 | 7 junio | Pipeline mux/demux, COM handler, UI final |
| v3+ | 22-24 junio | i18n (7 idiomas), comunidad, CI/CD, Phase 1.x |

## Arquitectura Actual

```
src/madrac/
├── cli/main.py          # Entry point principal
├── app.py               # Inicialización
├── main.py (raíz)       # Legacy (deprecado)
├── worker.py            # Worker transcripción
├── queue_manager.py     # Cola procesamiento
├── translator.py        # Traducción MarianMT + Gemini
├── subtitle_formatter.py # Formateo SRT
├── config.py            # Configuración
├── utils.py             # Utilidades
├── model_manager.py     # Gestor modelos
├── app_log.py           # Logging
├── muxer.py             # Muxer/demuxer
├── corrector_ui.py      # Corrector subtítulos
├── registry.py          # Registro Windows
├── supabase_client.py   # Cliente comunidad
└── plugins/             # Sistema plugins
```

## Estado Actual

- **Versión**: v3.0.0-rc1
- **Tests**: 257 tests, 39% coverage
- **CI/CD**: GitHub Actions configurado
- **i18n**: 7 idiomas (en, fr, pt, de, it, ja, zh)
- **Comunidad**: Google OAuth, Supabase, compartir/buscar
- **Traducción**: MarianMT, Gemini, LibreTranslate
- **Build**: PyInstaller ONEFILE/ONEDIR
- **Documentación**: PHASES.md (Plan 3 fases, 150+ horas estimadas)
