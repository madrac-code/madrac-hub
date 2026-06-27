# Llave: [Errno 22] Invalid argument en Windows – asyncio + Winsock + timing

**Autor:** MADRAC debug session (humano + agente)
**Fecha:** 2026-06-26
**Versión:** 1.1
**Estado:** Validado

## Problema

`OSError: [Errno 22] Invalid argument` apareciendo en puntos aparentemente aleatorios del pipeline (health check, requests, edge_tts, polling) al correr DUBS desde SUBS en Windows.

## Conocimiento Extraído

Un mismo error raíz (incompatibilidad asyncio ProactorEventLoop + aiohttp/edge-tts en Windows) se manifestaba como síntomas distintos según el momento exacto de ejecución. El error "viajaba" por el sistema porque cada componente tocaba el event loop o sockets en momentos diferentes.

Que un error cambie de punto de aparición no significa que sean múltiples bugs: puede ser un solo bug subyacente que cada subsistema expone en el momento en que lo toca.

## Generalización

Cuando un error parece moverse entre subsistemas sin causa obvia, es probable que haya un componente compartido subyacente (event loop, scheduler, runtime, socket layer) que está fallando. Investigar primero las dependencias comunes antes de asumir múltiples bugs independientes es mucho más eficiente.

Este patrón aplica a:
- Aplicaciones Windows con asyncio/aiohttp
- Sistemas con threads + event loops
- Cualquier pipeline donde el timing afecta la visibilidad del error
- Incluso sistemas no técnicos (organizaciones donde un mismo problema estructural aparece como "incendios" en diferentes áreas)

El principio general: **cuando ves el mismo error en N lugares distintos, busca lo que comparten, no lo que los diferencia.**

## Procedimiento (Cómo llegamos ahí)

1. **Fase 1** — Aislar `subprocess.Popen`. Falsado: 4 tests de Popen pasan. El error está fuera del Popen.
2. **Fase 2** — Health check + retries en submit/poll. Parcialmente efectivo: el síntoma cambiaba de lugar pero no desaparecía.
3. **Fase 3** — Captura de stderr del subproceso DUBS (`_start_stderr_thread`). Reveló que el crash ocurría dentro de `edge_tts.synthesize()`.
4. **Fase 4** — Prueba aislada de asyncio + edge-tts. Confirmación: `ProactorEventLoop` → crash, `SelectorEventLoop` → OK.
5. **Fase 5** — Flask no respondía durante Demucs (CPU-bound). Reemplazo con Waitress.

**Fix principal:** `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` al inicio del entry point, + `waitress.serve(app, threads=8)`.

## Evidencia

- Prueba aislada: `SelectorEventLoop` completa edge-tts sin errores. `ProactorEventLoop` (default en Windows) lanza OSError 22.
- Integration test post-fix: pipeline completo (extract → TTS → Demucs → mux).
- Replicado en Windows 11, Python 3.14.5, edge-tts 6.1.12.

## Resultados / Fix

Pipeline SUBS → DUBS funcionando de punta a punta:
- Health check → POST /dubbing → polling cada 2s → TTS (45/45 segments) → Demucs → mux → output.mkv
- Polling nunca timeout (Waitress threads=8)
- Sin [Errno 22] en ningún punto del flujo

## Deudas Técnicas / Observaciones

- Demucs sigue tomando el GIL → el servidor responde pero la latencia de polling aumenta durante separación. Mitigado con waitress threads, no resuelto.
- `set_event_loop_policy()` está deprecado en Python 3.16+. Solución permanente requiere que aiohttp/edge-tts soporte ProactorEventLoop, o migrar TTS a otro mecanismo.
- Cache de TTS: primera corrida lenta (~45s para 45 segmentos con cache miss). Corridas subsecuentes: <1s (100% cache hit).

## Costo Evitado

~8-10 horas de diagnóstico para el próximo equipo que enfrente errores similares de asyncio/Winsock en Windows. Potencialmente más si el bug aparecía en producción (el error se manifiesta en distintos puntos según timing, lo que lleva a "arreglar" el síntoma equivocado y perder días).

**Nivel de Confianza:** Alto

## Referencias

- ADR-006: `knowledge/decisions/ADR_006_demucs_frozen_bug.md`
- `development/tools/dubs_integration_test.py` — test automatizado
- `runtime/contracts/dubbing-api-v1.md`
- Código: madrac-dubs commits `9528a3e`, `9833be8`, `4a0f088`
