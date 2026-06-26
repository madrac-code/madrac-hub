# HISTORIA DE MADRAC-DUBS

## Resumen

MADRAC-DUBS es un motor de doblaje independiente que se integra con MADRAC-SUBS. Implementa un pipeline completo de 8 etapas usando Edge TTS para síntesis de voz. Versión v1.0-rc1.

## Origen

- **Creado**: 24-25 junio 2026
- **Basado en**: Prompt de agente IA (`DUBBING_EXTENSION_AGENT_PROMPT.md`)
- **Propósito**: Extensión de doblaje para madrac-subs
- **Versión**: v1.0-rc1

## Arquitectura

### Pipeline de 8 Etapas

```
Stage 1: Validation (10%)       - Check archivos
Stage 2: Audio Extraction (25%) - ffmpeg video→WAV
Stage 3: TTS Generation (50%)   - Edge TTS por subtítulo
Stage 4: Vocal Reduction (60%)  - Cancelación centro + EQ
Stage 5: TTS Sync (70%)         - Time-stretch a timing
Stage 6: Normalization (75%)    - LUFS broadcast standard
Stage 7: Audio Mixing (80%)     - Blend 30%/70%
Stage 8: Video Muxing (95%)     - ffmpeg mux final
Stage 9: Cleanup (100%)         - Remove temp files
```

### Stack Tecnológico

- **TTS**: Microsoft Edge TTS (gratuito, 200+ voces, 50+ idiomas)
- **API**: Flask REST (localhost:5000)
- **Audio**: scipy, librosa, ffmpeg
- **CLI**: Click
- **Build**: PyInstaller (madrac-dubbing.exe)

### Modos de Uso

1. **CLI Mode**: Línea de comandos standalone
2. **API Mode**: Servidor HTTP para integración SUBS
3. **Subprocess Mode**: Llamada directa con argumentos

## Archivos del Proyecto

### Código Principal
```
src/madrac_dubbing/
├── pipeline/
│   ├── models.py           # DubbingJob, DubbingConfig
│   └── dubbing_pipeline.py # Orquestador 8 etapas
├── tts/
│   ├── engine.py           # TTSEngine abstracto
│   └── edge_tts.py         # Edge TTS implementación
├── audio/
│   └── mixer.py            # Reducción, sync, mix, normalize
├── utils/
│   ├── audio.py            # SRT parsing, timecode
│   └── ffmpeg.py           # FFmpeg wrappers
├── __main__.py             # Entry point CLI
├── api.py                  # Flask HTTP API
├── config.py               # Configuración
└── cli.py                  # CLI handler (deprecado)
```

### Documentación Generada

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| ARCHITECTURE.md | 365 | Diseño técnico profundo |
| INTEGRATION_GUIDE.md | 498 | Guía integración SUBS |
| IMPLEMENTATION_SUMMARY.md | 336 | Resumen implementación |
| QUICKSTART.md | - | Guía rápido 5 min |
| README.md | - | Guía usuario completa |

### Ejecutables Compilados
- `madrac-dubbing.exe` - Motor de doblaje
- `MADRAC-SUBS.exe` - Copia de SUBS (?) 
- `ffmpeg.exe`, `ffprobe.exe` - Binarios incluidos

## Decisiones de Diseño

**Fuente**: `ARCHITECTURE.md` sección "Design Decisions"

1. **Separate Process**: Exe independiente, no modifica core
2. **HTTP API**: Flask REST, language-agnostic
3. **Abstract TTS**: TTSEngine ABC, extensible a ElevenLabs, pyttsx3
4. **Edge TTS Primary**: Gratuito, 200+ voces, sin API key
5. **Vocal Reduction**: Cancelación centro + EQ, rápido
6. **Time-Stretch Sync**: librosa, matching a timing subtítulo

## Integración con SUBS

**Fuente**: `INTEGRATION_GUIDE.md`

La integración sigue el patrón:
```
[SUBS GUI] → HTTP POST → [DUBS API] → Pipeline → Response
[SUBS GUI] → Lanza .exe → [DUBS CLI] → Pipeline → Output file
```

## Estado Actual

- **Versión**: v1.0-rc1
- **Modo**: Standalone + API
- **Dependencias**: edge-tts, flask, scipy, librosa
- **Idiomas**: ES, EN, FR, PT, IT, DE, JA, ZH, RU, AR
- **Documentación**: Completa (4 guías detalladas)
- **Sin git**: El proyecto no tiene historial git
