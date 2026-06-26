# EVIDENCIA DOCUMENTAL DEL PROYECTO MADRAC

## Resumen

Compilación de toda la evidencia documental utilizada para la investigación histórica del proyecto MADRAC. Cada ítem incluye ubicación, fecha, y relevancia.

## Documentación Arquitectónica

### Contexto.txt (Visión MADRAC-CORE)
- **Ubicación**: No encontrado en madrac-hub (mencionado previamente)
- **Tamaño**: 757 líneas
- **Contenido**: Arquitectura Event Bus + IPC Layer, diseño multi-componente
- **Relevancia**: Visión central del ecosistema

### ARCHITECTURE.md (DUBS)
- **Ubicación**: `D:\madrac-dubs\ARCHITECTURE.md`
- **Tamaño**: 365 líneas
- **Contenido**: Diseño técnico detallado, pipeline 8 etapas, decisiones de diseño
- **Relevancia**: Arquitectura completa del motor de doblaje

### INTEGRATION_GUIDE.md (SUBS-DUBS)
- **Ubicación**: `D:\madrac-dubs\INTEGRATION_GUIDE.md`
- **Tamaño**: 498 líneas
- **Contenido**: Guía de integración entre SUBS y DUBS con código de ejemplo
- **Relevancia**: Muestra el patrón de integración cross-componente

### IMPLEMENTATION_SUMMARY.md (DUBS)
- **Ubicación**: `D:\madrac-dubs\IMPLEMENTATION_SUMMARY.md`
- **Tamaño**: 336 líneas
- **Contenido**: Resumen de implementación, features, entregables
- **Relevancia**: Estado completo del componente DUBS

## Documentación de Planificación

### PHASES.md (SUBS)
- **Ubicación**: `D:\madrac-subs\PHASES.md`
- **Tamaño**: 160 líneas
- **Contenido**: Plan de mejora 3 fases (Fase 1-3), 150+ horas estimadas
- **Relevancia**: Roadmap del proyecto SUBS

### ENTRY_POINT.md (SUBS)
- **Ubicación**: `D:\madrac-subs\ENTRY_POINT.md`
- **Tamaño**: 54 líneas
- **Contenido**: Arquitectura de entry point, migración de main.py a src/madrac/
- **Relevancia**: Documentación de refactor arquitectónico

## Prompts y Contextos para IA

### PROMPT_AGENTE.md
- **Ubicación**: `D:\madrac-subs\PROMPT_AGENTE.md`
- **Propósito**: Briefing para agente IA de empaquetado Windows
- **Relevancia**: Evidencia de metodología IA-asistida

### DUBBING_EXTENSION_AGENT_PROMPT.md
- **Ubicación**: `D:\madrac-subs\DUBBING_EXTENSION_AGENT_PROMPT.md`
- **Propósito**: Prompt para implementar extensión de doblaje
- **Relevancia**: Génesis del componente DUBS

### PROMPT_NORMALIZACION.md
- **Ubicación**: `D:\madrac-subs\PROMPT_NORMALIZACION.md`
- **Propósito**: Prompt para normalización de subtítulos
- **Relevancia**: Proceso de mejora continua

### CONTEXTO_COMPLETO_PARA_IA.md
- **Ubicación**: `D:\madrac-subs\CONTEXTO_COMPLETO_PARA_IA.md`
- **Propósito**: Contexto completo del proyecto para IA
- **Relevancia**: Documentación exhaustiva del ecosistema

### CONTEXTO_PROYECTO.md
- **Ubicación**: `D:\madrac-subs\CONTEXTO_PROYECTO.md`
- **Tamaño**: 327 líneas
- **Propósito**: Contexto detallado de MADRAC-SUBS
- **Relevancia**: Documentación completa del componente SUBS

### WINDOWS_OPENCODE.txt
- **Ubicación**: `D:\madrac-subs\WINDOWS_OPENCODE.txt`
- **Propósito**: Contexto para empaquetado Windows
- **Relevancia**: Documentación de build multiplataforma

### DUBBING_EXTENSION_USAGE_GUIDE.md
- **Ubicación**: `D:\madrac-subs\DUBBING_EXTENSION_USAGE_GUIDE.md`
- **Propósito**: Guía de uso de extensión de doblaje
- **Relevancia**: Documentación de usuario para DUBS

## Código para Revisión IA

### CODIGO_1_CORE.txt
- **Ubicación**: `D:\madrac-subs\CODIGO_1_CORE.txt`
- **Propósito**: Código core del proyecto para revisión por IA

### CODIGO_2_DOCS.txt
- **Ubicación**: `D:\madrac-subs\CODIGO_2_DOCS.txt`
- **Propósito**: Documentación para revisión por IA

### CODIGO_INTERFAZ.txt
- **Ubicación**: `D:\madrac-asistente\CODIGO_INTERFAZ.txt`
- **Propósito**: Código de interfaz para IA

### CODIGO_NUCLEO.txt
- **Ubicación**: `D:\madrac-asistente\CODIGO_NUCLEO.txt`
- **Propósito**: Código del núcleo para IA

## Análisis Técnico

### TORCH_FROZEN_BUG_ANALYSIS.md
- **Ubicación**: `D:\madrac-subs\TORCH_FROZEN_BUG_ANALYSIS.md`
- **Propósito**: Análisis del bug de congelamiento de PyTorch
- **Relevancia**: Documentación de bug crítico

### INFORME_COMPARATIVO.md
- **Ubicación**: `D:\madrac-subs\INFORME_COMPARATIVO.md`
- **Propósito**: Informe comparativo de versiones

### INFORME_FINAL.md
- **Ubicación**: `D:\madrac-subs\INFORME_FINAL.md`
- **Propósito**: Informe final del proyecto

### OBJETIVO_DISTRIBUCION.md
- **Ubicación**: `D:\madrac-subs\OBJETIVO_DISTRIBUCION.md`
- **Propósito**: Objetivos de distribución

## Logs de Error

### Build Errors
| Archivo | Tamaño | Propósito |
|---------|--------|-----------|
| `build_errors.log` | - | Errores de build |
| `build_output.log` | - | Salida de build |
| `build-phase-a.log` | - | Log de fase de build |
| `exe_stderr.log` | - | Stderr del exe |
| `exe_stderr2.log` | - | Stderr del exe |
| `exe_stderr3.log` | - | Stderr del exe |
| `exe_stderr4.log` | - | Stderr del exe |
| `exe_stdout.log` | - | Stdout del exe |
| `exe_stdout2.log` | - | Stdout del exe |
| `exe_stdout3.log` | - | Stdout del exe |
| `exe_stdout4.log` | - | Stdout del exe |
| `pip_errors.log` | - | Errores de pip |

## Evidencia de Git

### MADRAC-HUB
- `.git\config`: Remote → github.com/madrac-code/madrac-hub.git
- `.git\logs\HEAD`: 1 commit + rename master→main
- Commit: `ab85354` - "first commit" (2026-06-25 03:38:39 -0300)

### MADRAC-ASISTENTE
- 4 commits (64bf9c7, 02d900a, dafd4d9, 9cc628c)
- Timeline: 12-14 junio 2026

### MADRAC-SUBS
- 48 commits en git log
- Timeline: 28 mayo - 24 junio 2026
- Tags: v3.0.0-rc1
- Merges: branch 'main' from origin

## Archivos de Configuración

### config.json (ASISTENTE)
- 62 líneas
- Multi-modelo IA (Ollama, Claude, OpenAI)
- Whisper (small, CPU, int8)
- Wakeword (hey_jarvis, ONNX)
- Audio (16kHz, chunk 1280)
- TTS (PowerShell, Microsoft Sabina)

### pyproject.toml (SUBS, DUBS)
- Configuración de proyecto Python
- Dependencias y metadata

### .gitignore (SUBS, ASISTENTE)
- Patrones de exclusión git

## Documentación de Usuario

### README.md (cada componente)
- **SUBS**: Guía de usuario del motor de subtitulación
- **ASISTENTE**: Guía del asistente JARVIS
- **DUBS**: Guía del motor de doblaje
- **HUB**: Punto de entrada del ecosistema
- **Nota**: Todos son archivos binarios con solo `# nombre-componente`

### QUICKSTART.md (DUBS)
- **Ubicación**: `D:\madrac-dubs\QUICKSTART.md`
- **Propósito**: Guía rápida de 5 minutos

## Archivos de Scripts/Build

### Scripts de Build
| Archivo | Componente | Propósito |
|---------|-----------|-----------|
| `build_windows.bat` | SUBS | Build Windows |
| `build_dubbing.bat` | DUBS | Build DUBS |
| `build_linux.sh` | SUBS | Build Linux |
| `build_appimage_venv.sh` | SUBS | Build AppImage |
| `empaquetar.bat` | ASISTENTE | Empaquetar JARVIS |
| `madrac-subs.spec` | SUBS | PyInstaller spec |
| `madrac-dubbing.spec` | DUBS | PyInstaller spec |
| `Jarvis.spec` | ASISTENTE | PyInstaller spec |

### Scripts de Instalación
| Archivo | Componente | Propósito |
|---------|-----------|-----------|
| `instalar.bat` | SUBS | Instalador Windows |
| `iniciar.bat` | SUBS/ASISTENTE | Iniciar aplicación |
| `iniciar.vbs` | SUBS | Inicio silencioso |
| `iniciar.sh` | SUBS | Inicio Linux |
| `run_dubbing.bat` | DUBS | Iniciar dubbing |

## Archivos de Base de Datos

### supabase_schema.sql
- **Ubicación**: `D:\madrac-subs\supabase_schema.sql`
- **Propósito**: Esquema de base de datos para comunidad
- **Tablas**: subtitles, users, shared_subtitles
- **Stack**: Supabase (PostgreSQL + Auth + Storage)

### supabase_client.py
- **Ubicación**: `D:\madrac-subs\supabase_client.py`
- **Propósito**: Cliente Python para Supabase
