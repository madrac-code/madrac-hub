# CRONOLOGÍA COMPLETA DEL PROYECTO MADRAC

## Resumen Ejecutivo

El ecosistema MADRAC nació como un asistente personal llamado JARVIS para Windows y evolucionó en ~25 días (31 de mayo - 25 de junio de 2026) hasta convertirse en una suite multi-componente con subtitulación, asistente IA, doblaje y un coordinador central (HUB).

## Línea de Tiempo Global

### Fase 0: Pre-JARVIS (Antes del 31 de mayo 2026)
- No hay evidencia de código previo al 31 de mayo
- El proyecto JARVIS original residía en `C:\asistente` (no accesible por permisos)
- Se infiere que existía un prototipo funcional local antes del primer commit

### Fase 1: Época JARVIS (28 de mayo - 14 de junio 2026)

**28 de mayo 2026**
- Primeros commits de infraestructura en madrac-subs: gitignore, config, requirements, scripts instaladores
- Fuente: `madrac-subs.git` commits `3c0be7c`, `ffa6202`, `7674be4`, `3d46b09`

**31 de mayo 2026**
- `a469321` - fix(build): revert subprocess worker, auto-install deps
- Fuente: `madrac-subs.git` commit `a469321`

**1 de junio 2026**
- `7d0aa1f` - build: ONEFILE spec, build script, icons and desktop entry
- `1dc2339` - docs: add prompt and context files for AI agent
- `9583432` - instalableWindowsPreVenvGeneral
- Fuente: `madrac-subs.git` commits

**2 de junio 2026**
- `4498ebc` - v1.0: Funcional en Windows y exportable
- `e9bff9d` - V1.1 con basura eliminada
- `467d636` - fix: resolve PySide6+torch crash, clean up project structure
- `6e2c11a` - v1.1: App funcional en Windows y Linux con PyInstaller
- Fuente: `madrac-subs.git` commits

**3 de junio 2026**
- `b895c8a` - feat: instrumentación y diagnóstico (Profiler/Heartbeat)
- `a243829` - feat: corrector de subtitulos con QGraphicsView overlay
- `6e84c87` - feat: UI final - splitter 3 paneles, barra animada
- `4df4c79` - feat: toast notifications animadas + Esc save&close
- `cec6c67` - Merge branch 'main'
- `1b05966` - fix: set volume explicit
- `4c5495c` - MADRAC-SUBSv2,02
- `5ae9e62` - MADRAC-SUBSv2,3
- Fuente: `madrac-subs.git` commits

**4 de junio 2026**
- `161614c` - persistencia de cola + ultimo_directorio
- `4b99370` - fix: _mover_a_papelera + remove stale entry_point.py
- `366ff53` - fix: spec file point to main.py
- `bc3f39a` - feat: comunidad Fase1 - auth Google OAuth
- `43349c5` - Phase 1.5 stabilization
- `e4f6d9f` - hotfix: restore temp_path block
- `deaca1d` - Phase 2: comunidad — compartir subtitulos, busqueda por hash
- `1f940a9` - docs: contexto completo para IA
- Fuente: `madrac-subs.git` commits

**6 de junio 2026**
- `e7c49e1` - feat: status bar, plugin system, window geometry
- `1d678ad` - COM DropHandler nativo + fixes
- Fuente: `madrac-subs.git` commits

**7 de junio 2026**
- `5be7719` - v3.0.0-rc1: pipeline completo, mux/demux/strip/probe, UI, build congelado
- `c5ad21a` - chore: add .vs/ to gitignore
- Fuente: `madrac-subs.git` commits

**12 de junio 2026**
- `64bf9c7` - Initial commit: Jarvis Windows assistant (madrac-asistente)
- Fuente: `madrac-asistente.git` commit `64bf9c7`

**13 de junio 2026**
- `02d900a` - fix: play_pause, whisper precision, ollama auto-start, media keys
- Fuente: `madrac-asistente.git` commit `02d900a`

**14 de junio 2026**
- `dafd4d9` - first commit (madrac-asistente - nuevo repo?)
- `9cc628c` - refactor: modular architecture + setup wizard + fixes
- Fuente: `madrac-asistente.git` commits

### Fase 2: Época de Expansión Multi-Componente (22-25 de junio 2026)

**22 de junio 2026**
- `722de56` - fix: COM DropHandler ScriptPath, shell verb for .srt/.ass/.vtt
- `9ad1248` - v3 consolidation: io_utils UTF-8 safety, config persistence fixes
- Fuente: `madrac-subs.git` commits

**23 de junio 2026**
- `bedc952` - Fix language detection: detected lang explicitly to Whisper, add Dutch
- `13fa282` - Improve embedded sub track selection, dynamic translator chain
- `5266749` - Translator fallback returns original text
- Fuente: `madrac-subs.git` commits

**24 de junio 2026**
- `cc6a788` - Add model existence HEAD-check before MarianMT load
- `9eaa1b3` - Add i18n system with Windows language detection, 7 language dicts
- `1de16be` - Wrap all UI strings with _(...) across 12 files
- `c811f5f` - Complete ENGLISH dict with all missing translations
- `0d0c97e` - fix: separar normalización de subida
- `c65a991` - chore(ci): Phase 1.1 - testing foundation + GitHub Actions
- `01abeb4` - docs: Phase 1.4 - Entry point architecture
- `25fbb19` - docs: Phase 1.5 - Torch frozen bug analysis
- `36408cc` - chore: Phase 1.6 - Pin critical dependency versions
- `18e97e2` - docs: DUBBING EXTENSION AGENT PROMPT
- `c5d4f30` - docs: DUBBING EXTENSION USAGE GUIDE
- Fuente: `madrac-subs.git` commits

**25 de junio 2026**
- `ab85354` - "first commit" - MADRAC-HUB creado (coordinador del ecosistema)
- Contexto.txt (757 líneas) - Arquitectura MADRAC-CORE con Event Bus + IPC Layer
- ARCHITECTURE.md - Diseño técnico MADRAC-DUBS
- INTEGRATION_GUIDE.md - Guía de integración entre DUBS y SUBS
- IMPLEMENTATION_SUMMARY.md - Resumen de implementación DUBS
- Fuente: `madrac-hub.git`, archivos en `D:\madrac-dubs`

## Resumen por Componente

### MADRAC-SUBS (Motor de Subtitulación)
- **Inicio**: 28 de mayo 2026
- **Commits**: 48+ commits
- **Evolución**: v1.0 → v1.1 → v2.0 → v2.3 → v3.0.0-rc1
- **Tags**: v3.0.0-rc1
- **Características**: Transcripción Whisper, traducción MarianMT, comunidad, i18n, 7 idiomas

### MADRAC-ASISTENTE (Asistente JARVIS)
- **Inicio**: 12 de junio 2026
- **Commits**: 4 commits
- **Evolución**: JARVIS original → arquitectura modular core/ → multi-modelo IA
- **Modelos**: Ollama (qwen2.5:3b), Claude, OpenAI GPT-4o-mini

### MADRAC-DUBS (Motor de Doblaje)
- **Inicio**: 24 de junio 2026
- **Commits**: Sin git (proyecto nuevo)
- **Versión**: v1.0-rc1
- **Stack**: Edge TTS, Flask API, pipeline 8 etapas

### MADRAC-HUB (Coordinador del Ecosistema)
- **Inicio**: 25 de junio 2026
- **Commits**: 1 commit (ab85354)
- **Rol**: Coordinador maestro con Event Bus + IPC Layer

## Observaciones Clave

1. El desarrollo completo abarca ~25 días (31 mayo - 25 junio 2026)
2. MADRAC-SUBS es el componente más maduro con 48+ commits y múltiples fases
3. El salto más significativo ocurrió el 25 de junio cuando se crearon HUB, DUBS y la visión MADRAC-CORE simultáneamente
4. El proyecto JARVIS original (C:\asistente) contiene la historia más temprana pero no es accesible
5. Todos los componentes comparten el autor: `madrac-code <madrac666@gmail.com>`
