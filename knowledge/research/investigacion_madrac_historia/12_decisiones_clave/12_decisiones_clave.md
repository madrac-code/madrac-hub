# DECISIONES CLAVE DEL PROYECTO MADRAC

## Resumen

Este documento enumera las decisiones arquitectónicas, técnicas y de diseño más importantes que moldearon el ecosistema MADRAC.

## Decisiones Arquitectónicas

### 1. Modularización del Asistente (14 junio)
**Decisión**: Dividir el monolito JARVIS en core/ modular
**Evidencia**: `9cc628c` - "refactor: modular architecture + setup wizard + fixes"
**Impacto**: Permitió escalar a multi-modelo IA y múltiples componentes
**Alternativa**: Mantener el monolito

### 2. Multi-Modelo IA (12-14 junio)
**Decisión**: Soportar Ollama + Claude + OpenAI como backends intercambiables
**Evidencia**: `config.json` con 3 modelos configurados
**Impacto**: Flexibilidad máxima, pero solo Ollama funcional (Claude/OpenAI sin API key)
**Alternativa**: Usar solo un modelo (Ollama)

### 3. Ecosistema Multi-Componente (25 junio)
**Decisión**: Separar SUBS, ASISTENTE, DUBS, HUB en repositorios independientes
**Evidencia**: 3 repositorios separados en GitHub madrac-code
**Impacto**: Componentes independientes pero integrables vía Event Bus
**Alternativa**: Todo en un monorepo

### 4. Patrón "Standalone First" (24-25 junio)
**Decisión**: Cada componente funciona independientemente
**Evidencia**: `ARCHITECTURE.md` - diseño standalone + API
**Impacto**: Cada componente es usable por sí solo
**Alternativa**: Dependencia entre componentes

### 5. Event Bus + IPC Layer (25 junio)
**Decisión**: Comunicación asíncrona (pub/sub) + síncrona (RPC)
**Evidencia**: `Contexto.txt` (757 líneas) - diseño arquitectónico
**Impacto**: Visión de futuro para integración completa
**Alternativa**: Comunicación directa entre componentes

## Decisiones Técnicas

### 6. Edge TTS como Motor Primario de Doblaje
**Decisión**: Usar Edge TTS (gratuito, 200+ voces)
**Evidencia**: `ARCHITECTURE.md` sección 4
**Impacto**: Sin necesidad de API key, 50+ idiomas
**Alternativa**: ElevenLabs (pago), pyttsx3 (voces limitadas)

### 7. Flask API para Integración DUBS-SUBS
**Decisión**: API REST HTTP como interfaz de integración
**Evidencia**: `ARCHITECTURE.md` sección 2
**Impacto**: Language-agnostic, fácil testing
**Alternativa**: Named pipes, shared memory

### 8. Faster-Whisper como STT
**Decisión**: Whisper CTranslate2 para transcripción
**Evidencia**: `config.json`, `CONTEXTO_PROYECTO.md`
**Impacto**: Buen rendimiento CPU con int8
**Alternativa**: OpenAI Whisper API (pago), Vosk (menos preciso)

### 9. MarianMT para Traducción
**Decisión**: Modelos Helsinki-NLP para traducción
**Evidencia**: `CONTEXTO_PROYECTO.md`, `translator.py`
**Impacto**: Traducción local sin API
**Alternativa**: Google Translate API, DeepL

### 10. PySide6 para GUI
**Decisión**: PySide6 (Qt6) para interfaces gráficas
**Evidencia**: `CONTEXTO_PROYECTO.md`, `main.py`
**Impacto**: UI moderna, multiplataforma
**Alternativa**: Tkinter, PyQt5, Electron

## Decisiones de Proyecto

### 11. Nombramiento MADRAC
**Decisión**: Nombre recursivo: M(Subs) + A(Asistente) + D(Dubbing) + R(Recognition) + A + C(Core)
**Evidencia**: Significado del acrónimo inferido de la estructura
**Impacto**: Marca unificada para el ecosistema

### 12. Separación de Repositorios
**Decisión**: 4 repositorios separados (SUBS, ASISTENTE, DUBS, HUB)
**Evidencia**: .git/config pointing a diferentes URLs
**Impacto**: Versionado independiente, pero más complejidad de integración
**Alternativa**: Monorepo

### 13. PyInstaller para Distribución
**Decisión**: Empaquetar como .exe standalone
**Evidencia**: Múltiples .spec files, builds scripts
**Impacto**: Distribución fácil para usuarios Windows
**Problemas**: Múltiples bugs de empaquetado (5+ commits de fix)

### 14. GitHub Actions para CI/CD
**Decisión**: Automatizar tests y builds
**Evidencia**: `.github/` directory, `c65a991`
**Impacto**: Calidad garantizada en cada commit

### 15. Supabase para Comunidad
**Decisión**: Supabase como backend de comunidad (auth + storage)
**Evidencia**: `supabase_client.py`, `supabase_schema.sql`
**Impacto**: Backend serverless rápido
**Riesgo**: RLS insuficiente (documentado en PHASES.md)

## Decisiones No Tomadas (Pendientes)

1. **Migración a typing**: Planificado en PHASES.md Fase 2
2. **Android/Kivy**: Planificado en PHASES.md Fase 3
3. **Prometheus/Sentry**: Planificado en PHASES.md Fase 3
4. **Web MVP**: Planificado en PHASES.md Fase 2
5. **Entry point unificado**: Documentado en ENTRY_POINT.md como pendiente

## Cronología de Decisiones

| Fecha | Decisión | Impacto |
|-------|----------|---------|
| 28 mayo | Crear SUBS | Componente más maduro |
| 12 junio | Crear JARVIS | Base del asistente |
| 14 junio | Modularizar core/ | Arquitectura extensible |
| 14 junio | Multi-modelo IA | 3 backends IA |
| 1-7 junio | Prompts para IA | Metodología IA-asistida |
| 7 junio | v3.0.0-rc1 | Pipeline completo SUBS |
| 24 junio | Edge TTS + Flask API | DUBS standalone |
| 24 junio | i18n (7 idiomas) | Internacionalización |
| 24 junio | GitHub Actions | CI/CD |
| 25 junio | Crear HUB | Coordinador central |
| 25 junio | Visión MADRAC-CORE | Event Bus + IPC Layer |
