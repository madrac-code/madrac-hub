# PARTICIPACIÓN DE LAS IA EN EL PROYECTO MADRAC

## Resumen

El proyecto MADRAC utilizó múltiples modelos de IA tanto en su producto final como probablemente en su proceso de desarrollo. Este documento analiza la evidencia disponible.

## Modelos IA en el Producto

### Ollama (Local)
- **Modelo**: qwen2.5:3b
- **Propósito**: Asistente conversacional local (JARVIS)
- **Evidencia**: `config.json` línea 7: `"modelo": "qwen2.5:3b"`
- **Configuración**: `base_url: http://localhost:11434`
- **Integración**: Inicio automático al arrancar JARVIS (`asistente.py:45-65`)
- **Estado**: Funcional, detectado como "corriendo" al inicio

### Claude (Anthropic)
- **Modelo**: claude-3-5-sonnet-20241022
- **Propósito**: Modelo remoto alternativo
- **Evidencia**: `config.json` línea 11-12
- **Configuración**: API key vacía (`""`) - no configurado aún
- **Estado**: Previsto pero no funcional (sin API key)

### OpenAI (GPT)
- **Modelo**: gpt-4o-mini
- **Propósito**: Modelo remoto alternativo
- **Evidencia**: `config.json` línea 15-16
- **Configuración**: API key vacía (`""`) - no configurado aún
- **Estado**: Previsto pero no funcional (sin API key)

### Whisper (STT)
- **Modelo**: faster-whisper small/base/tiny/medium
- **Propósito**: Speech-to-text (transcripción)
- **Evidencia**: `config.json` líneas 20-29
- **Dispositivo**: CPU, compute_type int8
- **Integración**: En SUBS (transcripción) y ASISTENTE (comandos de voz)

### Edge TTS (TTS)
- **Propósito**: Text-to-speech para doblaje
- **Evidencia**: `ARCHITECTURE.md` sección "Edge TTS as Primary"
- **Características**: 200+ voces, 50+ idiomas, gratuito, requiere internet
- **Motor**: Microsoft Edge TTS (no pyttsx3)

## Modelos IA en el Proceso de Desarrollo

### Evidencia de Desarrollo Asistido por IA

1. **Prompt files especializados**:
   - `DUBBING_EXTENSION_AGENT_PROMPT.md` - Prompt para agente IA de doblaje
   - `PROMPT_AGENTE.md` - Prompt para agente IA de empaquetado
   - `PROMPT_NORMALIZACION.md` - Prompt para normalización
   - `WINDOWS_OPENCODE.txt` - Contexto para empaquetado Windows
   - `CONTEXTO_COMPLETO_PARA_IA.md` - Contexto completo para IA
   - `CONTEXTO_PROYECTO.md` (327 líneas) - Contexto detallado

2. **Documentación técnica para IA**:
   - `CODIGO_1_CORE.txt` - Código core para revisión por IA
   - `CODIGO_2_DOCS.txt` - Documentación para IA
   - `CODIGO_INTERFAZ.txt` - Código de interfaz para IA
   - `CODIGO_NUCLEO.txt` - Código núcleo para IA

3. **Commits que mencionan IA**:
   - `1dc2339` - "docs: add prompt and context files for AI agent to fix Windows packaging"
   - `1f940a9` - "docs: contexto completo para IA + fix tecleo corrector"
   - `18e97e2` - "docs: DUBBING EXTENSION AGENT PROMPT - Ready for AI implementation"
   - `c5d4f30` - "docs: DUBBING EXTENSION USAGE GUIDE - How to use the AI prompt"

## Análisis de Participación

### Por Componente

| Componente | Modelos IA Producto | Evidencia IA Desarrollo |
|-----------|-------------------|----------------------|
| MADRAC-SUBS | Whisper, MarianMT | Prompt files, context files, commits IA |
| MADRAC-ASISTENTE | Ollama, Claude, OpenAI, Whisper | Código modular con multi-modelo |
| MADRAC-DUBS | Edge TTS | Agent prompt, architecture IA-driven |
| MADRAC-HUB | Ninguno (coordinador) | Contexto.txt con diseño IA-asistido |

### Patrón de Uso Observado

1. **Desarrollo con IA**: El proyecto usó prompts especializados para que agentes IA generaran o modificaran código
2. **Multi-modelo**: El asistente JARVIS soporta 3 backends de IA (Ollama local, Claude remoto, OpenAI remoto)
3. **Especialización**: Cada componente usa el modelo más adecuado (Whisper para audio, MarianMT para traducción, Edge TTS para voz)
4. **Ciclo IA**: Prompt → Implementación por IA → Revisión → Commit (evidente en commits de documentación)

### Inferencias sobre el Proceso

Basado en la estructura de archivos y commits:
- El desarrollador principal (madrac-code) probablemente usó asistentes IA (como Claude u OpenAI) para generar código
- Los archivos de contexto/prompt servían como "briefings" para que la IA entendiera el proyecto
- La documentación técnica detallada (ARCHITECTURE.md, INTEGRATION_GUIDE.md, 365-498 líneas) sugiere generación asistida por IA
- La velocidad de desarrollo (~25 días para 4 componentes) es consistente con desarrollo asistido por IA
