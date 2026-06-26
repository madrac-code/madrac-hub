# LÍNEA TEMPORAL COMPLETA DEL PROYECTO MADRAC

## Resumen

Línea de tiempo unificada de todos los eventos del ecosistema MADRAC, integrando commits de todos los repositorios y archivos clave.

## Timeline Visual

```
Mayo 2026                     Junio 2026
28  31  1   2   3   4   6   7   12  13  14  22  23  24  25
│   │   │   │   │   │   │   │   │   │   │   │   │   │   │
├───┴───┤   │   │   │   │   │   │   │   │   │   │   │   │
│ SUBS Setup     │   │   │   │   │   │   │   │   │   │   │
├───────┴───────┤   │   │   │   │   │   │   │   │   │   │
│ SUBS v1.0-v1.1    │   │   │   │   │   │   │   │   │   │
├───────────────┴───┤   │   │   │   │   │   │   │   │   │
│ SUBS v2.0-v3.0    │   │   │   │   │   │   │   │   │   │
├───────────────────┴───┤   │   │   │   │   │   │   │   │
│ SUBS Comunidad+Features    │   │   │   │   │   │   │   │
├───────────────────────┴───┴───┤   │   │   │   │   │   │
│ JARVIS Asistente                │   │   │   │   │   │   │
├───────────────────────┬───┬───┴───┤   │   │   │   │   │
│                       │   │ JARVIS Modular  │   │   │   │
├───────────────────────┴───┴───────────┴───┤   │   │   │
│ SUBS v3+i18n+CI/CD                           │   │   │   │
├───────────────────────────────────────────┴───┤   │   │
│ DUBS v1.0-rc1                                   │   │   │
├───────────────────────────────────────────────┴───┤   │
│ HUB + MADRAC-CORE                                  │   │
└───────────────────────────────────────────────┴───┴───┘
```

## Tabla Cronológica Detallada

### Mayo 2026

| Fecha | Commit | Componente | Descripción |
|-------|--------|-----------|-------------|
| 28 | `3c0be7c` | SUBS | chore: add gitignore for venv, cache and build artifacts |
| 28 | `ffa6202` | SUBS | fix(utils): multiplatform paths, video extensions and ffmpeg cancel |
| 28 | `7674be4` | SUBS | fix(config): wire subtitle and translation settings to runtime helpers |
| 28 | `3d46b09` | SUBS | fix(queue): deduplicate files and add lifecycle helpers |
| 28 | `f98c9d0` | SUBS | fix(worker): load models in background, fix whisper params and cancel |
| 28 | `31a6f30` | SUBS | fix(gui): handle queue events and restore UI after processing |
| 28 | `b3568e7` | SUBS | chore: add config, requirements and cross-platform installer scripts |
| 31 | `a469321` | SUBS | fix(build): revert subprocess worker, auto-install deps in build script |

### Junio 2026

| Fecha | Commit | Componente | Descripción |
|-------|--------|-----------|-------------|
| 1 | `7d0aa1f` | SUBS | build: ONEFILE spec, build script, icons and desktop entry |
| 1 | `1dc2339` | SUBS | docs: add prompt and context files for AI agent |
| 1 | `9583432` | SUBS | instalableWindowsPreVenvGeneral |
| 2 | `4498ebc` | SUBS | v1.0: Funcional en Windows |
| 2 | `e9bff9d` | SUBS | V1.1 con basura eliminada |
| 2 | `467d636` | SUBS | fix: resolve PySide6+torch crash |
| 2 | `6e2c11a` | SUBS | v1.1: App funcional en Windows y Linux |
| 3 | `b895c8a` | SUBS | feat: Profiler/Heartbeat |
| 3 | `a243829` | SUBS | feat: corrector subtítulos QGraphicsView |
| 3 | `6e84c87` | SUBS | feat: UI final - splitter 3 paneles |
| 3 | `4df4c79` | SUBS | feat: toast notifications animadas |
| 3 | `cec6c67` | SUBS | Merge branch 'main' |
| 3 | `1b05966` | SUBS | fix: set volume explicit |
| 3 | `4c5495c` | SUBS | MADRAC-SUBSv2,02 |
| 3 | `5ae9e62` | SUBS | MADRAC-SUBSv2,3 |
| 4 | `161614c` | SUBS | persistencia de cola |
| 4 | `4b99370` | SUBS | fix: mover a papelera |
| 4 | `366ff53` | SUBS | fix: spec file point to main.py |
| 4 | `bc3f39a` | SUBS | feat: comunidad Fase1 - Google OAuth |
| 4 | `43349c5` | SUBS | Phase 1.5 stabilization |
| 4 | `e4f6d9f` | SUBS | hotfix: temp_path |
| 4 | `deaca1d` | SUBS | Phase 2: comunidad |
| 4 | `1f940a9` | SUBS | docs: contexto completo IA |
| 6 | `e7c49e1` | SUBS | feat: status bar, plugin system |
| 6 | `1d678ad` | SUBS | COM DropHandler nativo |
| 7 | `5be7719` | SUBS | v3.0.0-rc1: pipeline completo |
| 7 | `c5ad21a` | SUBS | chore: add .vs/ to gitignore |
| 12 | `64bf9c7` | ASISTENTE | Initial commit: Jarvis Windows assistant |
| 13 | `02d900a` | ASISTENTE | fix: play_pause, whisper precision, ollama auto-start |
| 14 | `dafd4d9` | ASISTENTE | first commit (reset?) |
| 14 | `9cc628c` | ASISTENTE | refactor: modular architecture + setup wizard |
| 22 | `722de56` | SUBS | fix: COM DropHandler ScriptPath |
| 22 | `9ad1248` | SUBS | v3 consolidation: UTF-8 safety |
| 23 | `bedc952` | SUBS | Fix language detection, Dutch support |
| 23 | `13fa282` | SUBS | Embedded sub track selection |
| 23 | `5266749` | SUBS | Translator fallback |
| 24 | `cc6a788` | SUBS | MarianMT HEAD-check, Gemini/LibreTranslate |
| 24 | `9eaa1b3` | SUBS | i18n: 7 language dicts |
| 24 | `1de16be` | SUBS | UI strings wrap x12 files |
| 24 | `c811f5f` | SUBS | Complete ENGLISH dict |
| 24 | `0d0c97e` | SUBS | fix: separar normalización |
| 24 | `c65a991` | SUBS | Phase 1.1: testing + CI/CD |
| 24 | `01abeb4` | SUBS | docs: Entry point architecture |
| 24 | `25fbb19` | SUBS | docs: Torch frozen bug analysis |
| 24 | `36408cc` | SUBS | Phase 1.6: Pin dependencies |
| 24 | `18e97e2` | SUBS/DUBS | docs: DUBBING EXTENSION AGENT PROMPT |
| 24 | `c5d4f30` | SUBS/DUBS | docs: DUBBING EXTENSION USAGE GUIDE |
| 25 | `ab85354` | HUB | first commit - MADRAC-HUB |
| 25 | - | DUBS | ARCHITECTURE.md (365 líneas) |
| 25 | - | DUBS | INTEGRATION_GUIDE.md (498 líneas) |
| 25 | - | DUBS | IMPLEMENTATION_SUMMARY.md (336 líneas) |
| 25 | - | HUB | Contexto.txt (757 líneas, MADRAC-CORE visión) |
