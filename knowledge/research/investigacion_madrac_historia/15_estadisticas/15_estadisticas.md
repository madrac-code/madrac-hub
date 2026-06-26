# ESTADÍSTICAS DEL PROYECTO MADRAC

## Métricas Globales

| Métrica | Valor |
|---------|-------|
| Duración del desarrollo | 28 días (28 mayo - 25 junio 2026) |
| Commits totales | 53 |
| Componentes | 4 (SUBS, ASISTENTE, DUBS, HUB) |
| Repositorios GitHub | 3 (madrac-hub, madrac-subs, madrac-asistente) |
| Líneas de documentación técnica | 1,200+ (ARCHITECTURE + INTEGRATION + IMPLEMENTATION) |
| Líneas de Contexto.txt | 757 (visión MADRAC-CORE) |
| Archivos de prompt/contexto | 7+ (PROMPT_AGENTE, DUBBING_EXTENSION, etc.) |

## Commits por Componente

| Componente | Commits | % del Total |
|-----------|---------|------------|
| MADRAC-SUBS | 48 | 90.6% |
| MADRAC-ASISTENTE | 4 | 7.5% |
| MADRAC-HUB | 1 | 1.9% |
| MADRAC-DUBS | 0 | 0% |
| **Total** | **53** | **100%** |

## Commits por Día

| Fecha | Commits | Componente |
|-------|---------|-----------|
| 2026-05-28 | 7 | SUBS |
| 2026-05-31 | 1 | SUBS |
| 2026-06-01 | 3 | SUBS |
| 2026-06-02 | 4 | SUBS |
| 2026-06-03 | 8 | SUBS |
| 2026-06-04 | 8 | SUBS |
| 2026-06-06 | 2 | SUBS |
| 2026-06-07 | 2 | SUBS |
| 2026-06-12 | 1 | ASISTENTE |
| 2026-06-13 | 1 | ASISTENTE |
| 2026-06-14 | 2 | ASISTENTE |
| 2026-06-22 | 2 | SUBS |
| 2026-06-23 | 3 | SUBS |
| 2026-06-24 | 11 | SUBS |
| 2026-06-25 | 1+ | HUB + DUBS |

## Tipos de Commits

| Tipo | Cantidad | % |
|------|---------|------------|
| feat (nueva funcionalidad) | 12 | 22.6% |
| fix (corrección) | 15 | 28.3% |
| docs (documentación) | 12 | 22.6% |
| chore (mantenimiento) | 6 | 11.3% |
| refactor | 2 | 3.8% |
| vX.X (versiones) | 5 | 9.4% |
| hotfix | 1 | 1.9% |

## Versiones Publicadas

| Componente | Versión | Fecha |
|-----------|---------|-------|
| MADRAC-SUBS | v1.0 | 2026-06-02 |
| MADRAC-SUBS | v1.1 | 2026-06-02 |
| MADRAC-SUBS | v2.0 | 2026-06-03 |
| MADRAC-SUBS | v2.3 | 2026-06-04 |
| MADRAC-SUBS | v3.0.0-rc1 | 2026-06-07 |
| MADRAC-ASISTENTE | v3.2.0 (inferido) | 2026-06-14 |
| MADRAC-DUBS | v1.0-rc1 | 2026-06-25 |
| MADRAC-HUB | v1.0 | 2026-06-25 |

## Archivos por Componente

### MADRAC-SUBS (~80 archivos)
```
src/, tests/, ui/, docs/, installer/, plugins/
core/, fixtures/, scripts/, hooks/, tools/
build scripts, spec files, requirements, config
```

### MADRAC-ASISTENTE (~25 archivos)
```
core/ (8 módulos), ui/, tests/, docs/
asistente.py, config.json, gui.py, historial.py
build scripts, requirements, spec
```

### MADRAC-DUBS (~20 archivos)
```
src/madrac_dubbing/ (pipeline/, tts/, audio/, utils/)
ARCHITECTURE.md, INTEGRATION_GUIDE.md, IMPLEMENTATION_SUMMARY.md
build scripts, spec, requirements, config
```

### MADRAC-HUB (~2 archivos)
```
README.md, investagacion_madrac/
```

## Cobertura de Tests

**Fuente**: PHASES.md Fase 1

| Métrica | Valor |
|---------|-------|
| Tests totales | 257 |
| Cobertura actual | 39% |
| Objetivo Fase 1 | >= 40% |
| CI/CD | GitHub Actions |
| Framework | pytest + coverage |

## Stack Tecnológico por Componente

| Componente | Lenguaje | GUI | IA/ML | Comunicación | Build |
|-----------|----------|-----|-------|-------------|-------|
| SUBS | Python 3.11 | PySide6 | Whisper, MarianMT, Gemini | HTTP, Supabase | PyInstaller |
| ASISTENTE | Python 3.11+ | Tkinter/Qt | Ollama, Claude, OpenAI, Whisper | HTTP local | PyInstaller |
| DUBS | Python 3.11+ | Flask API | Edge TTS, scipy, librosa | HTTP REST | PyInstaller |
| HUB | - | - | - | Event Bus + IPC | - |

## Dependencias Críticas

| Dependencia | Versión | Componente |
|------------|---------|-----------|
| PySide6 | >=6.8.0 | SUBS |
| faster-whisper | ==1.0.2 | SUBS |
| transformers | ==4.35.2 | SUBS |
| torch | >=2.5.0 | SUBS |
| edge-tts | - | DUBS |
| flask | - | DUBS |
| ollama | - | ASISTENTE |
| PyInstaller | >=6.0 | SUBS, ASISTENTE, DUBS |

## Líneas de Código por Archivo Principal

| Archivo | Líneas | Componente |
|---------|--------|-----------|
| asistente.py | 212 | ASISTENTE |
| config.json | 62 | ASISTENTE |
| CONTEXTO_PROYECTO.md | 327 | SUBS |
| ARCHITECTURE.md | 365 | DUBS |
| INTEGRATION_GUIDE.md | 498 | DUBS |
| IMPLEMENTATION_SUMMARY.md | 336 | DUBS |
| Contexto.txt (HUB) | 757 | HUB |
| PHASES.md | 160 | SUBS |
| ENTRY_POINT.md | 54 | SUBS |
