# EVOLUCIÓN ARQUITECTÓNICA DEL PROYECTO MADRAC

## Visión General

La arquitectura del proyecto MADRAC evolucionó a través de 3 etapas claras:
1. **Monolítica** (JARVIS original)
2. **Modular** (core package multi-módulo)
3. **Ecosistema** (MADRAC-CORE con Event Bus + IPC Layer)

## Etapa 1: Arquitectura Monolítica (JARVIS Original)

**Evidencia**: `C:\asistente` (no accesible), `64bf9c7` (Initial commit: Jarvis Windows assistant)

El JARVIS original era un script monolítico en Python que integraba:
- Wakeword detection (hey_jarvis_v0.1.onnx)
- Speech-to-text (Whisper)
- IA conversacional (Ollama qwen2.5:3b)
- Text-to-speech (PowerShell)
- Control multimedia (play/pause, media keys)

**Archivo principal**: `asistente.py` (212 líneas) que importaba todo de `core/`

## Etapa 2: Arquitectura Modular (core/)

**Evidencia**: `9cc628c` (refactor: modular architecture + setup wizard + fixes), `D:\madrac-asistente\core\`

El refactor del 14 de junio dividió el monolito en módulos especializados:

```
core/
├── __init__.py       # Exportación centralizada
├── config.py         # Gestión de configuración JSON
├── audio.py          # Captura de audio
├── transcription.py  # Transcripción Whisper
├── ia.py             # Consulta a modelos IA (Ollama/Claude/OpenAI)
├── tts.py            # Text-to-speech
├── actions.py        # Acciones del sistema
├── utils.py          # Utilidades varias
├── historial.py      # Historial de conversación
└── audio/            # Módulos de audio extendidos
```

**Características modulares**:
- `config.json` centralizado con soporte multi-modelo
- Separación clara de responsabilidades
- Fácil extensibilidad para nuevos modelos IA

## Etapa 3: Arquitectura de Ecosistema (MADRAC-CORE)

**Evidencia**: Contexto.txt (757 líneas, arquitectura Event Bus + IPC Layer)

La visión MADRAC-CORE unifica 4 componentes independientes bajo un coordinador central:

```
┌─────────────────────────────────────────────────────────┐
│                    MADRAC-CORE (Nucleus)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │              IPC Layer (Inter-Process Comm)      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │   │
│  │  │  Event Bus │  │   RPC     │  │   State    │  │   │
│  │  │ (Pub/Sub) │  │ (Request) │  │  (Sync)    │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│                        │                                 │
│  ┌──────────┬──────────┼──────────┬──────────┐          │
│  │          │          │          │          │          │
│  ▼          ▼          ▼          ▼          ▼          │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│ │  M   │ │  A   │ │  D   │ │  R   │ │EXT   │          │
│ │(Subs)│ │(Asist)│ │(Dub) │ │(Rec) │ │      │          │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          │
└─────────────────────────────────────────────────────────┘
```

**Componentes del ecosistema**:
- **M** = MADRAC-SUBS (subtitulación y segmentación)
- **A** = MADRAC-ASISTENTE (asistente JARVIS)
- **D** = MADRAC-DUBS (doblaje con Edge TTS)
- **R** = MADRAC-REC (reconocimiento - futuro)

### Arquitectura de Integración DUBS-SUBS

**Evidencia**: `INTEGRATION_GUIDE.md` (498 líneas), `ARCHITECTURE.md` (365 líneas)

La integración entre DUBS y SUBS sigue el patrón "Standalone + API":

```
┌─────────────────────┐     HTTP API      ┌─────────────────────┐
│  MADRAC-SUBS        │ ────────────────→ │  MADRAC-DUBS        │
│  (GUI PySide6)      │ ←──────────────── │  (Flask:5000)       │
│  [Dub Now Button]   │   JSON responses  │  Pipeline 8 etapas  │
└─────────────────────┘                   └─────────────────────┘
```

## Principios Arquitectónicos Clave

1. **Standalone First**: Cada componente funciona independientemente
2. **API-First**: La comunicación es vía HTTP API REST
3. **Event Bus**: Comunicación asíncrona pub/sub
4. **IPC Layer**: RPC para operaciones síncronas
5. **State Sync**: Estado compartido entre ventanas
6. **Abstract Interfaces**: TTS Engine abstracto, extensible

## Evolución Temporal de la Arquitectura

| Fecha | Etapa | Descripción |
|-------|-------|-------------|
| Pre-12/06 | Monolítica | JARVIS script único en C:\asistente |
| 12/06 | Monolítica+ | Initial commit con imports a core/ |
| 14/06 | Modular | Refactor completo: core/ con 8 módulos |
| 22-24/06 | Microservicios | SUBS v3, i18n, comunidad, API |
| 24/06 | Ecosistema | DUBS como servicio standalone + API |
| 25/06 | MADRAC-CORE | HUB + Event Bus + IPC Layer vision |
