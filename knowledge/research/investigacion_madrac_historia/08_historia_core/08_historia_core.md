# HISTORIA DE MADRAC-CORE

## Resumen

MADRAC-CORE es el concepto arquitectónico central que unifica los 4 componentes del ecosistema MADRAC bajo un núcleo común con Event Bus e IPC Layer. Es la visión de futuro del proyecto.

## El Concepto MADRAC-CORE

**MADRAC-CORE** es un acrónimo recursivo que representa:

- **M** = **M**ADRAC-SUBS (Motor de subtitulación y segmentación)
- **A** = **A**SISTENTE (Asistente JARVIS con IA multi-modelo)
- **D** = **D**UBBING (Motor de doblaje Edge TTS)
- **R** = **R**ECOGNITION (Reconocimiento de voz/audio - componente futuro)
- **A** = **A**I (Inteligencia Artificial - el núcleo compartido)
- **C** = **C**ORE (Coordinación y comunicación)

## Arquitectura del Core

### Event Bus (Pub/Sub)
```
Componente A ──publica evento──→ Event Bus ──distribuye──→ Componente B
                                                              │
                                                  Componente C (suscrito)
```

El Event Bus permite comunicación asíncrona donde los componentes publican eventos y otros se suscriben. Ejemplos:
- SUBS publica "nuevo_subtitulo" → ASISTENTE recibe y ofrece doblaje
- ASISTENTE publica "comando_voz" → DUBS recibe y procesa
- DUBS publica "doblaje_completado" → SUBS recibe y actualiza UI

### IPC Layer (RPC)
```
Componente A ──request──→ IPC Layer ──response──→ Componente B
```

Para comunicación síncrona (request/response):
- SUBS solicita "transcribir(archivo)" → ASISTENTE responde con texto
- ASISTENTE solicita "doblar(video, srt)" → DUBS responde con video

### State Sync
```
Componente A ──actualiza──→ Estado Global ←──lee── Componente B
```

Estado compartido entre componentes:
- Archivo actual abierto en SUBS
- Modelo IA activo en ASISTENTE
- Progreso de doblaje en DUBS

## Patrón "Standalone First + Integrated When Available"

Cada componente funciona independientemente pero se integra opcionalmente:

```
Componente SOLO:
[SUBS] → Funciona sin HUB, sin DUBS
[DUBS] → Funciona sin HUB, sin SUBS
[ASISTENTE] → Funciona sin HUB, sin SUBS

Componente INTEGRADO:
[SUBS + DUBS] → Doblaje desde GUI de subtítulos
[SUBS + ASISTENTE] → Transcripción asistida por voz
[SUBS + DUBS + ASISTENTE + HUB] → Ecosistema completo
```

## Componentes de la Visión

### MADRAC-CORE (Nucleus)
- Event Bus (Pub/Sub asíncrono)
- IPC Layer (RPC síncrono)
- State Sync (estado compartido)
- Multi-window synchronization

### M - MADRAC-SUBS
- Transcripción Whisper
- Traducción MarianMT/Gemini
- Corrector de subtítulos
- Comunidad (compartir/buscar)
- i18n (7 idiomas)

### A - MADRAC-ASISTENTE
- Asistente JARVIS
- Multi-modelo IA (Ollama/Claude/OpenAI)
- Wakeword "Hey Jarvis"
- Control multimedia
- Perfiles de usuario

### D - MADRAC-DUBS
- Doblaje Edge TTS
- Pipeline 8 etapas
- Reducción vocal
- Sync automático
- Flask API

### R - MADRAC-REC (Futuro)
- No hay evidencia de implementación
- Previsto para reconocimiento de audio avanzado

## Estado de Implementación

| Componente | Estado | Versión |
|-----------|--------|---------|
| MADRAC-CORE (Nucleus) | Diseño conceptual | - |
| Event Bus | Diseñado en Contexto.txt | - |
| IPC Layer | Diseñado en Contexto.txt | - |
| MADRAC-SUBS | ✅ Completo | v3.0.0-rc1 |
| MADRAC-ASISTENTE | ✅ Completo | v3.2.0 |
| MADRAC-DUBS | ✅ Completo | v1.0-rc1 |
| MADRAC-HUB | 🟡 Parcial | v1.0 |
| MADRAC-REC | ❌ No iniciado | - |

## Timeline de la Visión

1. **24-25 junio 2026**: Concepto MADRAC-CORE documentado en Contexto.txt
2. **25 junio 2026**: MADRAC-HUB creado como repositorio central
3. **Futuro**: Implementación del Event Bus + IPC Layer
4. **Futuro**: Integración completa de todos los componentes
5. **Futuro**: MADRAC-REC (reconocimiento)

## Tecnologías Propuestas para el Core

- **Comunicación**: HTTP/REST (API Flask en DUBS), stdin/stdout JSON (ASISTENTE)
- **Estado**: Archivos JSON compartidos (config.json)
- **Event Bus**: ZeroMQ, RabbitMQ, o Redis Pub/Sub
- **IPC**: gRPC, JSON-RPC, o named pipes Windows
- **Sync**: File system watching, WebSocket

## Observaciones

1. MADRAC-CORE es actualmente un concepto arquitectónico, no una implementación
2. El patrón "Standalone First" asegura que cada componente funcione independientemente
3. La visión está documentada en Contexto.txt (757 líneas) pero no implementada
4. Los componentes ya tienen interfaces preparadas para integración (APIs HTTP, formatos JSON)
5. El ecosistema completo permitiría: voz → subtítulos → doblaje → exportación en un flujo continuo
