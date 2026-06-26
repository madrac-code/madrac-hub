# ANEXOS DE COMMITS RELEVANTES DEL PROYECTO MADRAC

## Resumen

Listado completo de todos los commits de todos los repositorios del ecosistema MADRAC, organizados por componente y con metadatos completos.

## MADRAC-HUB (1 commit)

| Hash | Fecha | Autor | Mensaje |
|------|-------|-------|---------|
| `ab85354` | 2026-06-25 03:38:39 -0300 | madrac-code | first commit |

**Repositorio**: https://github.com/madrac-code/madrac-hub.git
**Branch**: main (renombrado de master)

## MADRAC-ASISTENTE (4 commits)

| Hash | Fecha | Autor | Mensaje |
|------|-------|-------|---------|
| `64bf9c7` | 2026-06-12 | madrac-code | Initial commit: Jarvis Windows assistant |
| `02d900a` | 2026-06-13 | madrac-code | fix: play_pause, whisper precision, ollama auto-start, media keys |
| `dafd4d9` | 2026-06-14 | madrac-code | first commit (posible reinicio del repo) |
| `9cc628c` | 2026-06-14 | madrac-code | refactor: modular architecture + setup wizard + fixes |

## MADRAC-SUBS (48 commits)

### Fase de Fundación (28-31 mayo)

| Hash | Fecha | Mensaje |
|------|-------|---------|
| `3c0be7c` | 2026-05-28 | chore: add gitignore for venv, cache and build artifacts |
| `ffa6202` | 2026-05-28 | fix(utils): multiplatform paths, video extensions and ffmpeg cancel |
| `7674be4` | 2026-05-28 | fix(config): wire subtitle and translation settings to runtime helpers |
| `3d46b09` | 2026-05-28 | fix(queue): deduplicate files and add lifecycle helpers |
| `f98c9d0` | 2026-05-28 | fix(worker): load models in background, fix whisper params and cancel |
| `31a6f30` | 2026-05-28 | fix(gui): handle queue events and restore UI after processing |
| `b3568e7` | 2026-05-28 | chore: add config, requirements and cross-platform installer scripts |
| `a469321` | 2026-05-31 | fix(build): revert subprocess worker, auto-install deps in build script, recreate venv on install |

### Fase de Build y Distribución (1 junio)

| Hash | Fecha | Mensaje |
|------|-------|---------|
| `1dc2339` | 2026-06-01 | docs: add prompt and context files for AI agent to fix Windows packaging |
| `7d0aa1f` | 2026-06-01 | build: ONEFILE spec, build script, icons and desktop entry |
| `9583432` | 2026-06-01 | instalableWindowsPreVenvGeneral |

### Fase v1.0-v1.1 (2 junio)

| Hash | Fecha | Mensaje |
|------|-------|---------|
| `4498ebc` | 2026-06-02 | v1.0: Funcional en Windows y exportable |
| `e9bff9d` | 2026-06-02 | V1.1 con basura eliminada |
| `467d636` | 2026-06-02 | fix: resolve PySide6+torch crash, clean up project structure |
| `6e2c11a` | 2026-06-02 | v1.1: App funcional en Windows y Linux con PyInstaller |

### Fase v2.0-v3.0 (3-6 junio)

| Hash | Fecha | Mensaje |
|------|-------|---------|
| `b895c8a` | 2026-06-03 | feat: implementacion completa de instrumentacion y diagnostico (Profiler/Heartbeat) |
| `a243829` | 2026-06-03 | feat: corrector de subtitulos con QGraphicsView overlay, fix EXE packaging |
| `6e84c87` | 2026-06-03 | feat: UI final - splitter 3 paneles, barra animada, persiana espacio, fix constraints Qt6 |
| `4df4c79` | 2026-06-03 | feat: toast notifications animadas + Esc save&close + QSettings placeholder en corrector |
| `cec6c67` | 2026-06-03 | Merge branch 'main' of https://github.com/madrac-code/madrac-subs |
| `1b05966` | 2026-06-03 | fix: set volume explicit, show playback errors to user in corrector |
| `4c5495c` | 2026-06-03 | MADRAC-SUBSv2,02 |
| `5ae9e62` | 2026-06-04 | MADRAC-SUBSv2,3 |

### Fase Comunidad (4 junio)

| Hash | Fecha | Mensaje |
|------|-------|---------|
| `161614c` | 2026-06-04 | persistencia de cola + ultimo_directorio en file dialog |
| `4b99370` | 2026-06-04 | fix: _mover_a_papelera use create_unicode_buffer, remove stale entry_point.py |
| `366ff53` | 2026-06-04 | fix: spec file point to main.py instead of deleted entry_point.py |
| `bc3f39a` | 2026-06-04 | feat: comunidad Fase1 - auth Google OAuth, toggle Online/Offline, compartir/buscar subtitulos |
| `43349c5` | 2026-06-04 | Phase 1.5 stabilization: fix cancellation, FK violation, layout guard + print/log cleanup |
| `e4f6d9f` | 2026-06-04 | hotfix: restore temp_path block and return result in calcular_espacio_por_categoria |
| `deaca1d` | 2026-06-04 | Phase 2: comunidad — compartir subtitulos, busqueda por hash, fixes UI |
| `1f940a9` | 2026-06-04 | docs: contexto completo para IA + fix tecleo corrector + logging buscar_por_hash + config defaults |

### Fase v3.0.0-rc1 (6-7 junio)

| Hash | Fecha | Mensaje |
|------|-------|---------|
| `e7c49e1` | 2026-06-06 | feat: status bar, plugin system, window geometry, UI polishing |
| `1d678ad` | 2026-06-06 | COM DropHandler nativo + fixes |
| `5be7719` | 2026-06-07 | v3.0.0-rc1: pipeline completo, mux/demux/strip/probe, UI, build congelado |
| `c5ad21a` | 2026-06-07 | chore: add .vs/ to gitignore |

### Fase de Madurez (22-25 junio)

| Hash | Fecha | Mensaje |
|------|-------|---------|
| `9ad1248` | 2026-06-22 | v3 consolidation: io_utils UTF-8 safety, config persistence fixes, COM drop handler fix |
| `722de56` | 2026-06-22 | fix: COM DropHandler ScriptPath, shell verb for .srt/.ass/.vtt, launcher argv stripping |
| `76f7bdb` | 2026-06-23 | v3 community/normalization system: Explorer drag-drop SRT, in-place mux, embedded sub, language transcribe |
| `bedc952` | 2026-06-23 | Fix language detection: pass detected lang explicitly to Whisper, add Dutch (nl) |
| `13fa282` | 2026-06-23 | Improve embedded sub track selection (dialogue > signs/songs), dynamic translator chain |
| `5266749` | 2026-06-23 | Translator fallback returns original text |
| `cc6a788` | 2026-06-24 | Add model existence HEAD-check before MarianMT load, Gemini/LibreTranslate engine |
| `9eaa1b3` | 2026-06-24 | Add i18n system with Windows language detection, _(key) wrapper, 7 language dicts |
| `1de16be` | 2026-06-24 | Wrap all UI strings with _(...) across 12 files |
| `c811f5f` | 2026-06-24 | Complete ENGLISH dict with all missing translations |
| `0d0c97e` | 2026-06-24 | fix: separar normalización de subida — ffprobe siempre, parser solo si habilitado |
| `c65a991` | 2026-06-24 | chore(ci): Phase 1.1 - testing foundation + GitHub Actions |
| `01abeb4` | 2026-06-24 | docs: Phase 1.4 - Entry point architecture documentation |
| `25fbb19` | 2026-06-24 | docs: Phase 1.5 - Torch frozen bug analysis + solutions |
| `36408cc` | 2026-06-24 | chore: Phase 1.6 - Pin critical dependency versions |
| `18e97e2` | 2026-06-24 | docs: DUBBING EXTENSION AGENT PROMPT - Ready for AI implementation |
| `c5d4f30` | 2026-06-24 | docs: DUBBING EXTENSION USAGE GUIDE - How to use the AI prompt |

## MADRAC-DUBS (Sin git)

El proyecto MADRAC-DUBS en `D:\madrac-dubs` no tiene historial git. Todos los archivos fueron creados entre 24-25 junio 2026.

## MADRAC-CORE (Diseño conceptual)

No hay commits para MADRAC-CORE. El diseño arquitectónico está documentado en:
- `Contexto.txt` (757 líneas) - Visión Event Bus + IPC Layer
- `ARCHITECTURE.md` (365 líneas) - Diseño técnico DUBS
- `INTEGRATION_GUIDE.md` (498 líneas) - Integración SUBS-DUBS

## Estadísticas de Commits

| Componente | Commits | Período | Días | Promedio/día |
|-----------|---------|---------|------|-------------|
| MADRAC-HUB | 1 | 1 día | 1 | 1.0 |
| MADRAC-ASISTENTE | 4 | 3 días | 3 | 1.3 |
| MADRAC-SUBS | 48 | 28 días | 28 | 1.7 |
| MADRAC-DUBS | 0 | 1 día | - | - |
| **Total** | **53** | **28 días** | - | **1.9** |
