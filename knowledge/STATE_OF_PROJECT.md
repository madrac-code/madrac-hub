# STATE_OF_PROJECT.md — MADRAC Ecosystem Technical State Document

**Version**: 1.0  
**Date**: 2026-07-24  
**Current Phase**: Phase 3 — MCP Integration (Phase 3A Complete, Phase 3B/3C Planned)  
**Last Commit**: `25ecc71` (feat(mui): MUI Phase 1 + 6 bug fixes)
**Target Audience**: New developers, AI agents, project maintainers  

---

## 1. Arquitectura General

### 1.1 Componentes del Ecosistema

| Componente | Repositorio | Descripción | Estado |
|------------|-------------|-------------|--------|
| **madrac-subs** | `github.com/madrac-code/madrac-subs` | Motor de subtítulos: Whisper + MarianMT + PySide6 UI | v3.0.0-rc1 |
| **madrac-subs-web** | `github.com/madrac-code/madrac-subs-web` | Frontend web: Next.js 14 + Vercel + Supabase | v2.x (producción) |
| **madrac-asistente** | `github.com/madrac-code/madrac-asistente` | Asistente de voz: Ollama (qwen3.5:9b) + JARVIS | v3.2.0 |
| **madrac-dubs** | `github.com/madrac-code/madrac-dubs` | Motor de doblaje: Edge TTS + Demucs + Flask API | v1.0-rc1 |
| **madrac-hub** | `github.com/madrac-code/madrac-hub` | Coordinador central: knowledge base + build integrado | Phase 0 |

### 1.2 Relaciones entre Componentes

```
┌─────────────────┐     HTTP API      ┌─────────────────┐
│  madrac-subs    │ ◄────────────────► │  madrac-dubs    │
│  (PySide6 UI)   │  localhost:5000   │  (Flask API)    │
└────────┬────────┘                    └─────────────────┘
         │
         │ In-process (QThread + AssistantManager)
         ▼
┌─────────────────┐
│ madrac-asistente│
│  (Ollama LLM)   │
└─────────────────┘

         │ HTTPS
         ▼
┌─────────────────┐
│    Supabase     │
│  (PostgreSQL +  │
│   Auth + S3)    │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│madrac-subs-web  │
│  (Next.js)      │
└─────────────────┘
```

### 1.3 madrac-hub (Monorepo Híbrido - ADR-010)

**Estructura**:
```
D:\madrac-hub\
├── src/
│   ├── madrac_subs/      ← Copia de SUBS para build integrado
│   ├── madrac_asistente/ ← Copia de ASISTENTE para build integrado
│   └── madrac_dubbing/   ← Copia de DUBS para build integrado
├── knowledge/            ← ADRs, arquitectura, metodología
├── development/          ← Fases, prompts, contextos
├── docs/                 ← Guías de build
├── .github/workflows/    ← CI/CD unificado
└── requirements.txt      ← Dependencias unificadas
```

**Responsabilidades por Repositorio**:

| Repositorio | Responsabilidades |
|-------------|-------------------|
| **madrac-subs** | UI (PySide6), Pipeline Whisper/MarianMT, Parser, CommunityStage, Editor, Config, OAuth Desktop |
| **madrac-subs-web** | Next.js App Router, CommunityLibrary, Búsqueda SubDivX, Leaderboard, Perfiles, Supabase Auth Web |
| **madrac-asistente** | Ollama LLM, Acciones hardcodeadas, Wakeword, TTS (Edge), Whisper local, CLI |
| **madrac-dubs** | API Flask, Edge TTS, Demucs/DSP, Mux FFmpeg, API Contract v1 |
| **madrac-hub** | Build unificado, CI/CD, Knowledge base, ADRs, Documentación cross-repo |
| **Supabase** | Auth (Google OAuth), PostgreSQL (subtitles, profiles, downloads, fingerprints), Storage (S3) |

---

## 2. Estado de Supabase

### 2.1 Tablas

#### `subtitles` (Tabla Principal)
```sql
-- Campos principales
id              UUID PRIMARY KEY
file_hash       TEXT NOT NULL          -- SHA256 del video
filename        TEXT NOT NULL          -- hash_nombre.srt
language        TEXT NOT NULL          -- 'es', 'en', etc.
status          TEXT DEFAULT 'published' -- 'published' | 'draft'
user_id         UUID REFERENCES profiles(id)
version         INT DEFAULT 1
download_count  INT DEFAULT 0
created_at      TIMESTAMPTZ DEFAULT now()

-- Metadatos de video (ffprobe)
duration_sec    NUMERIC
file_size       BIGINT
original_video_name TEXT
resolution      TEXT
fps             NUMERIC
bitrate         BIGINT
width           INT
height          INT
video_codec     TEXT
audio_codec     TEXT
container       TEXT

-- Metadatos de normalización (parser)
season          INT
episode         INT
year            INT
title_clean     TEXT
release_group   TEXT
source_type     TEXT
parse_confidence NUMERIC
normalization_version TEXT

-- Calidad
is_manual_revision BOOLEAN
word_count      INT
avg_confidence  NUMERIC
source          TEXT -- 'whisper' | 'manual'
```

**Índices**:
- `subtitles_file_hash_language_idx` (file_hash, language, status)
- `subtitles_user_id_idx` (user_id)
- `subtitles_download_count_idx` (download_count DESC)

**RLS Policies (POST-FIX - ADR-002/LLAVE_004)**:
| Operación | Policy |
|-----------|--------|
| SELECT | `USING (status = 'published' OR auth.uid() = user_id)` — publicados públicos, privados solo owner |
| INSERT | `WITH CHECK (auth.uid() = user_id)` — solo como uno mismo |
| UPDATE | `USING (auth.uid() = user_id)` — solo owner |
| DELETE | `USING (auth.uid() = user_id)` — solo owner |

#### `profiles`
```sql
id              UUID PRIMARY KEY REFERENCES auth.users(id)
display_name    TEXT
created_at      TIMESTAMPTZ DEFAULT now()
```
**RLS**: `USING (auth.uid() = id)` — solo owner

#### `subtitle_downloads`
```sql
id              UUID PRIMARY KEY
subtitle_id     UUID REFERENCES subtitles(id)
user_id         UUID REFERENCES profiles(id)
created_at      TIMESTAMPTZ DEFAULT now()
```
**RLS**: `USING (auth.uid() = user_id)` — solo owner puede ver sus descargas

#### `video_fingerprints`
```sql
id              UUID PRIMARY KEY
file_hash       TEXT UNIQUE NOT NULL
duration_sec    NUMERIC
width           INT
height          INT
video_codec     TEXT
audio_codec     TEXT
container       TEXT
created_at      TIMESTAMPTZ DEFAULT now()
```
**RLS**: `USING (true)` — metadatos no sensibles, lectura pública

#### `download_stats` (Ghost Table - FIXED)
```sql
id              UUID PRIMARY KEY
file_name       TEXT
downloaded_at   TIMESTAMPTZ DEFAULT now()
```
**RLS**: `USING (true)` — agregados públicos

#### Storage Bucket: `subtitle-files`
- **Privado** (antes público) — requiere sesión autenticada o signed URLs
- Path: `{file_hash}_{sanitized_name}.srt`

### 2.2 Migraciones

| Migración | Archivo | Estado | Descripción |
|-----------|---------|--------|-------------|
| Fase 1 | `supabase_schema.sql` | ✅ | Esquema base: subtitles, profiles, storage |
| Fase 2 | `migracion_fase2.sql` | ✅ | video_fingerprints, subtitle_downloads |
| Fase 3 | `migracion_fase3.sql` | ✅ | Metadatos de normalización, download_stats |
| **RLS Fix** | `supabase_rls_audit_fix.sql` | ✅ | **LLAVE_004** — 6 vulnerabilidades corregidas (idempotente) |

**Script de Fix RLS**: `madrac-subs-web/supabase_rls_audit_fix.sql` — idempotente, ejecutar en Supabase Dashboard > SQL Editor.

### 2.3 Credenciales (Hardcoded en Desktop)
```python
# src/madrac_subs/src/madrac/supabase_client.py
SUPABASE_URL = "https://fypmjtesckrgboorjibl.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # anon key pública
```

---

## 3. Estado de la Normalización

### 3.1 `parser.py` — `parse_video_filename()`

**Ubicación**: `src/madrac_subs/src/madrac/core/parser.py`  
**Gate**: Solo activo cuando `comunidad.normalizacion_habilitada = true` (config)

**Patrones Soportados**:
- Season/Episode: `S01E02`, `S03E05E06`, `Capítulo 5`, `Ep 12`
- Año: `(2024)`, `[2023]`, `.2024.`
- Resolución: `2160p`, `1080p`, `720p`, `480p`, `360p`
- Source: `WEB-DL`, `WEBRip`, `BluRay`, `HDTV`, `DVDRip`, `BDRemux`
- Codec: `x264`, `h264`, `x265`, `h265`, `HEVC`, `AV1`, `VP9`
- Audio: `DDP5.1`, `DD5.1`, `DTS-HD`, `DTS`, `AAC`, `AC3`, `FLAC`, `Opus`
- Release Group: `[GroupName]` al inicio o final

**Confidence Scoring (5 categorías, peso igual)**:
| Categoría | Peso | Ejemplo |
|-----------|------|---------|
| Resolución | 1/5 | `1080p` |
| Source | 1/5 | `WEB-DL` |
| Codec/Audio | 1/5 | `x264` / `DDP5.1` |
| Episodio/Season | 1/5 | `S01E02` |
| Año | 1/5 | `2024` |

**Fórmula**: `confidence = matched_categories / 5.0`  
**Threshold**: `< 0.5` → devuelve defaults (confidence=0.0, normalización ignorada)

**Output Keys**:
```python
{
    "title_clean": str,      # Nombre limpio sin metadatos
    "season": int|None,
    "episode": int|None,
    "year": int|None,
    "resolution": str|None,  # lowercase
    "source": str|None,      # normalizado (webdl, bluray, etc.)
    "codec": str|None,
    "audio": str|None,
    "release_group": str|None,
    "type": "movie"|"episode",
    "confidence": float,     # 0.0-1.0, 2 decimales
    "normalization_version": "parser_v1"
}
```

### 3.2 Metadatos Calculados vs Guardados vs Mostrados

| Metadato | Calculado Localmente | Guardado en Supabase | Mostrado en Web | Usado en Desktop |
|----------|---------------------|---------------------|-----------------|------------------|
| `file_hash` (SHA256) | ✅ `utils.sha256` | ✅ `subtitles.file_hash` | ❌ | ✅ (búsqueda) |
| `duration_sec` | ✅ `ffprobe` | ✅ `subtitles.duration_sec` | ❌ | ✅ (búsqueda tolerancia) |
| `width`/`height` | ✅ `ffprobe` | ✅ `subtitles.width/height` | ❌ | ✅ (resolución derivada) |
| `resolution` | ✅ `_derive_resolution()` | ✅ `subtitles.resolution` | ✅ Badge | ✅ |
| `fps`, `bitrate`, codecs | ✅ `ffprobe` | ✅ `subtitles.*` | ❌ | ✅ (compartir) |
| `season`/`episode` | ✅ `parser.py` | ✅ `subtitles.season/episode` | ✅ Badge | ✅ |
| `year` | ✅ `parser.py` | ✅ `subtitles.year` | ✅ Badge | ✅ |
| `title_clean` | ✅ `parser.py` | ✅ `subtitles.title_clean` | ✅ Título | ✅ |
| `release_group` | ✅ `parser.py` | ✅ `subtitles.release_group` | ❌ | ✅ |
| `source_type` | ✅ `parser.py` | ✅ `subtitles.source_type` | ❌ | ✅ |
| `parse_confidence` | ✅ `parser.py` | ✅ `subtitles.parse_confidence` | ✅ Badge | ✅ |
| `normalization_version` | ✅ `parser.py` | ✅ `subtitles.normalization_version` | ❌ | ✅ |
| `avg_confidence` (Whisper) | ✅ Pipeline | ✅ `subtitles.avg_confidence` | ❌ | ✅ |
| `word_count` | ✅ `_word_count()` | ✅ `subtitles.word_count` | ❌ | ✅ |

**Metadatos AÚN NO UTILIZADOS**:
- `fps`, `bitrate`, `video_codec`, `audio_codec`, `container` — guardados pero no expuestos en UI web
- `release_group`, `source_type` — guardados, no en web
- `subtitle_downloads` — track existe, no hay UI de estadísticas de descarga por usuario

### 3.3 `normalization_version`
- Valor actual: `"parser_v1"`
- Se incrementa cuando cambia la lógica de parsing
- Permite filtrar/ignorar metadatos antiguos en consultas web

---

## 4. Flujo Comunidad

### 4.1 Diagrama de Flujo Completo

```
VIDEO INPUT
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ PIPELINE (run-v3.py → PipelineWorker)               │
│ 1. AudioExtractionStage                             │
│ 2. TranscribeStage (Whisper)                        │
│ 3. TranslateStage (si habilitado)                   │
│ 4. CommunityStage  ←── FEATURE FLAGGED              │
│ 5. FormatStage / MuxStage                           │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ CommunityStage.execute()                            │
│                                                     │
│ IF NOT comunidad.habilitado → SKIP                  │
│                                                     │
│ LEVEL 1: ffprobe (siempre)                         │
│   → media_info {duration, width, height, fps,      │
│      bitrate, video_codec, audio_codec, container} │
│                                                     │
│ LEVEL 2: Parser (SI normalizacion_habilitada)       │
│   → parsed {season, episode, year, title_clean,    │
│      resolution, source, codec, audio,             │
│      release_group, confidence, normalization_v}   │
│                                                     │
│ LEVEL 3: Búsqueda (siempre)                        │
│   → CLIENTE.buscar_por_hash(file_hash, idioma,     │
│      duracion, tolerancia=3s)                       │
│   → SI encontrado: return {used_community: False,  │
│      available: True, url: storage_url}             │
│                                                     │
│ LEVEL 4: Upload (SI login + consent + auto)        │
│   puede_subir = (CLIENTE.is_logged_in()            │
│       AND share_consent_given                       │
│       AND subir_automaticamente)                    │
│   → CLIENTE.compartir_subtitulo() con TODOS        │
│     los metadatos (ffprobe + parser)                │
└─────────────────────────────────────────────────────┘
```

### 4.2 Matriz de Comportamiento (Config Flags)

| Flag Config | Default | Descripción | Afecta a |
|-------------|---------|-------------|----------|
| `comunidad.habilitado` | `false` | Master switch comunidad | Todo el flujo CommunityStage |
| `comunidad.auto_buscar` | `true` | Buscar en comunidad antes de Whisper | CommunityStage búsqueda |
| `comunidad.auto_descargar` | `true` | Auto-descargar SRT encontrado | Pipeline salta Whisper |
| `comunidad.subir_automaticamente` | `true` | Subir SRT tras generar | CommunityStage upload |
| `comunidad.share_consent_given` | `false` | Usuario consintió compartir metadatos | Upload (requerido) |
| `comunidad.normalizacion_habilitada` | `true` | Extraer metadatos parser/ffprobe | Parser + metadatos upload |
| `traduccion.idioma_destino` | `"es"` | Idioma búsqueda/compartir | Búsqueda + upload |

### 4.3 Comportamiento por Combinación de Flags

| `habilitado` | `auto_buscar` | `auto_descargar` | `subir_auto` | `consent` | `normalizacion` | Resultado |
|--------------|---------------|------------------|--------------|-----------|-----------------|-----------|
| ❌ | — | — | — | — | — | **CommunityStage SKIP** |
| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **Completo**: busca → descarga → normaliza → sube |
| ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | Busca → informa disponible → normaliza → sube |
| ✅ | ❌ | — | ✅ | ✅ | ✅ | No busca → genera → normaliza → sube |
| ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | Busca → descarga → normaliza → NO sube |
| ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | Busca → descarga → normaliza → NO sube (falta consent) |
| ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | Busca → descarga → **sin parser/ffprobe** → sube (metadatos mínimos) |

---

## 5. OAuth y Autenticación

### 5.1 Desktop (madrac-subs)

**Flujo**: Google OAuth 2.0 + PKCE (Proof Key for Code Exchange)
- **Archivo**: `src/madrac_subs/src/madrac/supabase_client.py`
- **Clase**: `SupabaseClient(QObject)` — async via `QTimer` polling
- **Scopes**: `email profile`

**Flujo**:
1. `login_google_async()` → genera PKCE pair → abre navegador en `https://supabase.co/auth/v1/authorize?provider=google&redirect_to=http://127.0.0.1:{puerto}&code_challenge=...`
2. Usuario autentica en Google → redirect a `http://127.0.0.1:{puerto}/?code=...`
3. Servidor HTTP local captura `code` → `_exchange_code()` → POST a `/auth/v1/token?grant_type=pkce`
4. Recibe `access_token`, `refresh_token`, `user` → guarda en `~/.cache/madrac-subs/sesion.json`
5. Emite `loginFinished(bool)` → UI actualiza

**Token Refresh**: Automático en `_validar_token()` si 401 → POST a `/auth/v1/token?grant_type=refresh_token`

**Logout**: POST a `/auth/v1/logout` + limpia sesión local

**Sesión Persistida**: `~/.cache/madrac-subs/sesion.json` (access_token, refresh_token, user)

### 5.2 Web (madrac-subs-web)

**Supabase Auth (Next.js App Router)**:
- **Google Login**: `supabase.auth.signInWithOAuth({ provider: 'google' })`
- **Callback Route**: `/auth/callback` → `supabase.auth.exchangeCodeForSession()`
- **Session**: Cookie-based (Supabase SSR)
- **Middleware**: `middleware.ts` refresca sesión en cada request

**Rutas Protegidas**:
- `/community` — requiere sesión
- `/profile` — requiere sesión
- `/download-srt/[id]` — requiere sesión (download tracking)

### 5.3 Tareas Pendientes

| Tarea | Estado | Prioridad |
|-------|--------|-----------|
| Refresh token automático en Web | ✅ (Supabase SSR) | — |
| Logout global (Desktop + Web) | ❌ | Media |
| Revocación de tokens en Supabase | ❌ | Baja |
| Tests de aislamiento cross-user (RLS) | ❌ | **Alta** (ADR-002) |
| Penetration testing community endpoints | ❌ | Media |

---

## 6. Estado de la Web (madrac-subs-web)

### 6.1 Inventario de Features

| Feature | Estado | Descripción |
|---------|--------|-------------|
| **CommunityLibrary** | ✅ | Lista pública de subtítulos publicados con filtros (idioma, tipo, búsqueda) |
| **Búsqueda Local** | ✅ | Busca en Supabase `subtitles` por título, hash, tags |
| **Búsqueda SubDivX** | ✅ | Scraper externo integrado como fuente alternativa |
| **Leaderboard** | ✅ | Ranking usuarios por uploads/downloads |
| **Perfiles de Usuario** | ✅ | `/profile/[id]` — stats, uploads, badges |
| **Descargas SRT** | ✅ | `/download-srt/[id]` — tracking en `subtitle_downloads` |
| **Badges de Normalización** | ✅ | Badges visuales: confidence, tipo (movie/episode), resolution, source |
| **Leaderboard Global** | ✅ | Top contributors por uploads |
| **Autenticación Google** | ✅ | Supabase Auth + Next.js middleware |
| **PWA / Offline** | ❌ | Planificado |
| **Notificaciones Push** | ❌ | Planificado |
| **Editor Web** | ❌ | Planificado (editor de subtítulos en navegador) |
| **API Rate Limiting** | ✅ | LLAVE_003 — serverless rate limiting (Vercel Edge) |

### 6.2 Stack Técnico

| Componente | Tech |
|------------|------|
| Framework | Next.js 14 (App Router) |
| Hosting | Vercel |
| Auth | Supabase Auth (Google OAuth) |
| Database | Supabase PostgreSQL (RLS enabled) |
| Storage | Supabase Storage (S3-compatible) |
| Styling | Tailwind CSS |
| Deployment | Vercel (auto-deploy on push) |
| Rate Limiting | Vercel Edge Functions + KV |

---

## 7. Estado del Desktop (madrac-subs)

### 7.1 Inventario de Features

| Feature | Estado | Descripción |
|---------|--------|-------------|
| **Setup Wizard** | ✅ | 4 pasos: Idioma/Términos/Comunidad → FFmpeg → Modelo Whisper → Directorios |
| **Extensiones** | ✅ | Diálogo con tabs: Traducción, Comunidad, Avanzado, Directorio, Cache |
| **Cola de Procesamiento** | ✅ | QueueManager (JSON persistente, crash recovery, EventBus) |
| **Editor de Subtítulos** | ✅ | Timeline, waveform, edición inline, split/merge, formatos SRT/ASS |
| **Comunidad** | ✅ | Búsqueda + Upload automático + Consent UI (Setup Wizard + Extensiones) |
| **Parser** | ✅ | `parse_video_filename()` + confidence + normalization_version |
| **Fingerprints** | ✅ | SHA256 video + ffprobe metadata + parser metadata |
| **Dubbing Integration** | ✅ | "Dub Now" button → DubDialog → DUBS API → Progress polling |
| **MCP Server** | ✅ Phase 3C | 15 tools | stdio + HTTP 127.0.0.1:7654 | edit_subtitle_segment + export_srt + workspace tools |
| **MUI Protocol** | ✅ Phase 1 | 20 tools — create/update/close/list/events, UIManager always active |
| **Assistant Integration** | ✅ Phase 2C | AssistantManager (in-process QThread) + ConfigDialog |
| **Build System** | ✅ | PyInstaller onefile ~601 MB, CI/CD GitHub Actions |

### 7.2 Pipeline Stages (Orden de Ejecución)

1. **AudioExtractionStage** — FFmpeg extrae audio a WAV temporal
2. **TranscribeStage** — faster-whisper (modelo configurable: tiny/base/small/medium)
3. **TranslateStage** — MarianMT (offline) / Gemini / LibreTranslate / Google
4. **CommunityStage** — Feature-flagged (ver §4)
5. **FormatStage** — SRT/ASS cleanup, merge short lines
6. **MuxStage** — FFmpeg muxea subtítulos en MKV/MP4 (opcional)

### 7.3 Configuración (TOML + Overlays)

- **Defaults**: `src/madrac_subs/src/madrac/config/defaults.py`
- **Bundled**: `config.json` (read-only, empaquetado)
- **User**: `~/.cache/madrac-subs/config.toml` (overlay, persistencia)
- **Acceso**: `get_config(key)`, `set_config(key, value)` → singleton `ConfigManager`

### 7.4 Tareas Pendientes Desktop

| Feature | Estado | Prioridad |
|---------|--------|-----------|
| PyInstaller ADR-006 Opción A (bundle Demucs) | ❌ | Media |
| Event Bus / IPC Layer (MADRAC-CORE) | ❌ | **Alta** (Phase 3+) |
| Plugin System | ❌ | Media |
| Actualización automática (auto-update) | ❌ | Media |
| Telemetría anónima opt-in | ❌ | Baja |

---

## 8. Roadmap Priorizado

### ✅ COMPLETADO

| Item | Fase | Commit/Fecha |
|------|------|--------------|
| Knowledge Foundation (ADRs, methodology) | Phase 0 | 2026-06-26 |
| SUBS ↔ DUBS Integration (Dub Now) | Phase 1 | 2026-07-01 |
| Community Feature (Search + Upload) | Phase 1.5 | 2026-07-15 |
| Normalización (Parser + Confidence) | Phase 1.5 | 2026-07-20 |
| Supabase RLS Audit & Fix | LLAVE_004 | 2026-07-02 |
| Assistant In-Process Integration | Phase 2C | 2026-07-23 |
| Hybrid Monorepo (HUB src/) | ADR-010 | 2026-07-23 |
| CI/CD GitHub Actions | Phase 2 | 2026-07-23 |
| MCP Server Phase 3A (stdio) | Phase 3A | 2026-07-24 |
| MCP Phase 3B — Ollama Tool Calling | Phase 3B | cc4ac21 / 2026-07-24 |
| MCP Phase 3C — HTTP Transport | Phase 3C | 2325dec / 2026-07-24 |
| MCP 15 tools + workspace editing | Phase 3C | 1227b48 / 2026-08-06 |
| MUI Phase 1 — procedural windows + 6 bug fixes | Phase MUI | 25ecc71 |
| Security: Gemini API Key → Env Var | — | 2026-07-24 |
| Model Name Fix (gemini-2.5-flash) | — | 2026-07-24 |

### 🔄 EN PROGRESO

| Item | Fase | Avance | Bloqueadores |
|------|------|--------|--------------|
| MCP Phase 3B — Ollama Tool Calling | Phase 3B | ✅ COMPLETE | — |
| Event Bus / MADRAC-CORE (IPC Layer) | Phase 4 | 0% | Arquitectura pendiente |

### ⏳ PENDIENTE (Ordenado por Prioridad Real)

| Prioridad | Item | Fase | Esfuerzo | Dependencias |
|-----------|------|------|----------|--------------|
| **P0** | Tests de aislamiento RLS (cross-user) | Supabase | 2-3 días | ADR-002 checklist |
| **P1** | Event Bus / MADRAC-CORE (IPC Layer) | Phase 3+ | 2-3 semanas | Arquitectura |
| **P1** | PyInstaller Fix Demucs (ADR-006 Opción A) | Build | 1 día | `datas=` en .spec |
| **P2** | Penetration Testing Community | Supabase | 1 semana | RLS tests passing |
| **P2** | Web: PWA / Offline Support | Web | 1 semana | Service Workers |
| **P2** | Desktop: Auto-update (WinSparkle/NSIS) | Build | 3 días | Code signing |
| **P3** | Plugin System (madrac-subs) | Desktop | 2 semanas | Event Bus |
| **P3** | Web Editor de Subtítulos | Web | 2-3 semanas | Monaco/CodeMirror |
| **P3** | madrac-recon (Voice Cloning + Wakeword) | Phase 4+ | 4+ semanas | MCP Server listo |

---

## 9. Riesgos Técnicos Detectados

| Riesgo | Severidad | Estado | Mitigación |
|--------|-----------|--------|------------|
| **RLS Policies Inconsistentes** | 🔴 CRÍTICO | **RESUELTO** (LLAVE_004) | Fix script ejecutado, pendiente tests de aislamiento |
| **Metadatos Históricos sin Normalizar** | 🟠 MEDIO | Abierto | Script de backfill `normalization_version` para subtítulos antiguos |
| **Fingerprints Incompletos (históricos)** | 🟠 MEDIO | Abierto | Backfill `video_fingerprints` para subtítulos pre-normalización |
| **Demucs >10 min para 36s video** | 🟠 MEDIO | Abierto | DSP fallback funcional; perfilado pendiente |
| **Demucs Frozen .exe Bug** | 🟡 BAJO | Workaround (ADR-006) | Opción A pendiente (`datas=` en .spec) |
| **Rating System No Implementado** | 🟡 BAJO | Abierto | Schema listo (`rating` en subtitles), falta UI + API |
| **Honor System No Implementado** | 🟡 BAJO | Abierto | Confianza en `is_manual_revision`; sin verificación criptográfica |
| **Config Drift HUB src/ vs Upstream** | 🟠 MEDIO | Crónico (ADR-010) | Sync manual antes de build; automatizar con git submodules |
| **Supabase Anon Key Hardcoded** | 🟡 BAJO | Aceptado | Es clave pública (anon), rotación no crítica |
| **Gemini API Key en Config (ya fix)** | ✅ RESUELTO | — | Ahora usa `MADRAC_GEMINI_API_KEY` env var |
| **Model Name Incorrecto (gemini-3.5-flash)** | ✅ RESUELTO | — | Corregido a `gemini-2.5-flash` / `gemini-1.5-flash` |
| **Claude Desktop ignora `cwd` en Windows** | 🟡 BAJO | Documentado (ADR-008) | Usar paths absolutos en `args` |
| **Audio device blocker (Windows PortAudio MME/WDM-KS)** | 🟡 BAJO | Documentado LLAVE-005 | Workaround: resample en callback mode |
| **MUI button JSON format** | ✅ RESUELTO | e91f093 | Descriptor normalizado (action anidado o tool/internal plano) + whitelist MUI ampliada; documentado en AI_READY_CODEBASE.md |

---

## 10. Contrato entre Repositorios

### 10.1 Qué Cambia en Cada Repo

| Cambio | madrac-subs | madrac-subs-web | madrac-asistente | madrac-dubs | madrac-hub | Supabase |
|--------|-------------|-----------------|------------------|-------------|------------|----------|
| **UI/UX Desktop** | ✅ Owner | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Pipeline Whisper/MarianMT** | ✅ Owner | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Parser / Normalización** | ✅ Owner | ❌ (lee metadata) | ❌ | ❌ | ❌ | ❌ |
| **CommunityStage / Upload** | ✅ Owner | ❌ (lee) | ❌ | ❌ | ❌ | Schema/RLS |
| **OAuth Desktop (PKCE)** | ✅ Owner | ❌ | ❌ | ❌ | ❌ | Auth Config |
| **OAuth Web (Next.js)** | ❌ | ✅ Owner | ❌ | ❌ | ❌ | Auth Config |
| **Supabase Schema/RLS** | ❌ | ❌ (propone) | ❌ | ❌ | ❌ | **Owner** |
| **Storage Bucket Policies** | ❌ | ❌ | ❌ | ❌ | ❌ | **Owner** |
| **Web UI (Next.js)** | ❌ | ✅ Owner | ❌ | ❌ | ❌ | ❌ |
| **Leaderboard/Perfiles Web** | ❌ | ✅ Owner | ❌ | ❌ | ❌ | ❌ |
| **Asistente Voz (Ollama)** | ❌ (integra) | ❌ | ✅ Owner | ❌ | ❌ | ❌ |
| **Dubbing API (Flask)** | ❌ (consume) | ❌ | ❌ | ✅ Owner | ❌ | ❌ |
| **Demucs/Edge TTS/FFmpeg** | ❌ | ❌ | ❌ | ✅ Owner | ❌ | ❌ |
| **Build Unificado / CI/CD** | ❌ | ❌ | ❌ | ❌ | ✅ Owner | ❌ |
| **ADRs / Architecture Decisions** | ❌ | ❌ | ❌ | ❌ | ✅ Owner | ❌ |
| **Sync src/ copies** | ❌ | ❌ | ❌ | ❌ | **Human** | ❌ |

### 10.2 APIs Contractuales (No Romper Sin Coordinación)

| Contrato | Owner | Consumers | Versionado |
|----------|-------|-----------|------------|
| **Dubbing API v1** | madrac-dubs | madrac-subs | `dubbing-api-v1.md` — POST/GET `/dubbing`, `/health` |
| **Supabase Schema** | Supabase | madrac-subs, madrac-subs-web | Migraciones SQL idempotentes |
| **CommunityStage Data Contract** | madrac-subs | Supabase | `compartir_subtitulo()` JSON payload |
| **MCP Tools/Resources** | madrac-subs | Claude Desktop, Ollama | `PHASE_3_MCP.md` — tool schemas |
| **Config Keys (TOML)** | madrac-hub (defaults) | Todos | `defaults.py` + `schema.py` |
| **Event Bus (Future)** | MADRAC-CORE | Todos | TBD — Phase 3+ |

### 10.3 Reglas de Modificación

1. **Nunca** modifiques `knowledge/` sin ADR correspondiente
2. **Nunca** toques `runtime/` hasta que Phase 1+ inicie oficialmente
3. **Antes de build en HUB**: `git pull` en upstreams → sync manual `src/`
4. **Cambios en Supabase**: Solo via migración SQL idempotente + ADR si breaking
5. **Cambios en MCP**: Actualizar `PHASE_3_MCP.md` + tests en `test_mcp_server.py`

---

## Apéndice: Referencias Rápidas

### Archivos Clave por Área

| Área | Archivos Principales |
|------|---------------------|
| Pipeline Principal | `src/madrac_subs/run-v3.py`, `src/madrac_subs/src/madrac/app.py` |
| Pipeline Stages | `src/madrac_subs/src/madrac/pipeline/stages/*.py` |
| CommunityStage | `src/madrac_subs/src/madrac/pipeline/stages/community.py` |
| Parser | `src/madrac_subs/src/madrac/core/parser.py` |
| Supabase Client | `src/madrac_subs/src/madrac/supabase_client.py` |
| Config System | `src/madrac_subs/src/madrac/config/` (defaults, schema, manager) |
| OAuth Desktop | `src/madrac_subs/src/madrac/supabase_client.py` (SupabaseClient) |
| MCP Server | `src/madrac_subs/src/madrac/mcp/` (server.py, tools/, resources/) |
| MCP Launcher | `src/madrac_subs/run_mcp.py` |
| AssistantManager | `src/madrac_subs/src/madrac/assistant/manager.py` |
| Setup Wizard | `src/madrac_subs/src/madrac/ui/dialogs/setup_wizard.py` |
| Extensions Dialog | `src/madrac_subs/src/madrac/ui/dialogs/extensions_dialog.py` |
| Integration Layer | `src/madrac_dubbing/src/madrac_dubbing/integration_layer.py` |
| ADRs | `knowledge/decisions/ADR_*.md` |
| Phase Docs | `development/phases/PHASE_*.md` |
| LLAVES | `knowledge/llaves/LLAVE_*.md` |

### Variables de Entorno Críticas

| Variable | Uso | Requerida |
|----------|-----|-----------|
| `MADRAC_GEMINI_API_KEY` | Gemini API (preferida sobre GOOGLE_API_KEY) | No (pero recomendada) |
| `GOOGLE_API_KEY` | Gemini API (fallback legacy) | No |
| `MADRAC_DUBS_HOST` | Host DUBS API (default 127.0.0.1) | No |
| `MADRAC_DUBS_PORT` | Puerto DUBS API (default 5000) | No |
| `MADRAC_MCP_PORT` | Puerto HTTP del MCP server (default: 7654) | No |
| `MADRAC_INTEGRATION_AVAILABLE` | Force integration mode (testing) | No |
| `MADRAC_OPERATING_MODE` | `standalone` | `integrated` | No |
| `EDGE_TTS_VOICE` | Voz por defecto dubbing | No |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` | No |

---

**Fin del Documento**  
*Este documento es la fuente de verdad única para el estado del proyecto MADRAC. Actualizar con cada cambio arquitectural significativo.*
