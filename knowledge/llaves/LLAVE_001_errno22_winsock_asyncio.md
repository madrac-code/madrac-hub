# Llave: [Errno 22] Invalid argument en Windows al conectar SUBS → DUBS

**Autor:** MADRAC debug session log (humano + agente)
**Fecha:** 2026-06-26 (sesiones 010–019, ~10h de diagnóstico)
**Versión:** 1.0
**Estado:** Validado

## Problema

Al hacer clic en "Dub Now" desde MADRAC-SUBS, la aplicación lanzaba
DUBS como subproceso, el health check pasaba, pero al enviar un job
(o durante el procesamiento) se obtenía:

    OSError: [Errno 22] Invalid argument

El error era intermitente y cambiaba de contexto según qué intentáramos:
a veces aparecía en `requests.post("/dubbing")`, a veces en
`requests.get("/health")`, a veces dentro de `edge_tts.Communicate()`,
a veces durante `extract_audio()`.

El síntoma era el mismo en todos los casos: Winsock lanzaba EINVAL
en una operación de red o socket.

## Procedimiento

### Fase 1 — Aislar el origen (sesiones 010–014)

Se partió de la hipótesis de que [Errno 22] venía de
`subprocess.Popen` con `os.environ.copy()`. Se agregaron 4 tests
de diagnóstico en `launch_dubs()`:

1. `Popen(cmd)` sin extras → OK
2. `Popen(cmd, cwd=...)` → OK
3. `Popen(cmd, cwd, stderr=PIPE)` → OK
4. `Popen(cmd, cwd, stderr, stdout, env)` → OK

**Falsación:** El Popen no era el problema. El error ocurría en
`requests.get()` post-Popen, cuando el puerto aún no estaba en LISTEN
(peculiaridad de Winsock vs Linux, que lanza ECONNREFUSED).

Se corrigió `_wait_for_health()` para capturar `OSError errno==22`
y `requests.exceptions.ConnectionError` en lugar de propagarlos.

### Fase 2 — El error se mueve a submit_job (sesiones 014–015)

Corregido el health check, el error aparecía en `submit_job()` al hacer
`requests.post("/dubbing")`. Se implementó:

- Retry 5×2s en `submit_job()` para OSError 22
- `time.sleep(1)` post-health-check para dar tiempo a Flask de terminar init
- `logger.error()` con `traceback.format_exc()` en todos los except

**Falsación:** submit_job() funcionaba, pero el error volvía a aparecer
durante el `poll_job()` y durante el pipeline mismo. No era un problema
de timing — DUBS efectivamente se caía después de responder /health.

### Fase 3 — Capturar stderr de DUBS (sesiones 015–016)

Se implementó un thread `_start_stderr_thread()` que lee `proc.stderr`
línea por línea en background y las loguea con `[DUBS stderr]`.

Se hizo un cambio temporal: `creationflags=CREATE_NEW_CONSOLE` para ver
la salida de DUBS en su propia ventana.

**Resultado:** El stderr de DUBS mostraba un error en `edge-tts` durante
la síntesis de TTS. El traceback apuntaba a `asyncio.new_event_loop()`
seguido de `edge_tts.Communicate()`.

### Fase 4 — asyncio + Windows ProactorEventLoop (sesiones 016–018)

La evidencia apuntaba a que `asyncio.new_event_loop()` en Windows crea
un `ProactorEventLoop`. La librería `aiohttp` (usada por `edge-tts`)
falla con OSError 22 cuando usa ProactorEventLoop desde un thread
secundario. Es un bug conocido en Windows + aiohttp + asyncio.

Se verificó con una prueba aislada:

    # Sin fix: loop = asyncio.new_event_loop() → ProactorEventLoop → crash
    # Con fix: asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    #          loop = asyncio.new_event_loop() → SelectorEventLoop → OK

La prueba aislada confirmó que TTS funciona con SelectorEventLoop
y falla con ProactorEventLoop.

**Fix aplicado:** `asyncio.set_event_loop_policy(
    asyncio.WindowsSelectorEventLoopPolicy())` al inicio de `__main__.py`
y `api.py`.

**Resultado:** El pipeline completo de DUBS (extract → TTS → Demucs → mix → mux)
funcionó correctamente desde la línea de comandos.

### Fase 5 — Flask no responde durante procesamiento (sesiones 018–019)

Aun con el fix de asyncio, la integración desde SUBS fallaba porque
Flask en modo desarrollo es single-threaded. Cuando el pipeline corría
en un background thread (torch/Demucs saturando la CPU), Flask no
respondía a los GET /dubbing/<id> de polling.

**Fix aplicado:** Se reemplazó `app.run(host, port, threaded=True)` por
`waitress.serve(app, host, port, threads=8)`.

**Resultado final:** El integration test corrió de punta a punta:
health check → POST → polling cada 2s → Demucs finalizado → output.mkv.

## Resultados

1. El [Errno 22] en `edge_tts.synthesize()` se resuelve con
   `WindowsSelectorEventLoopPolicy` (causa raíz confirmada).

2. El [Errno 22] en `requests.get/posts()` durante health check
   y submit se resuelve capturando `OSError errno==22` como
   "puerto no listo todavía" (retry + pass).

3. Los timeouts de polling Flask se resuelven con Waitress.

4. Los [Errno 22] que aparecían en distintas partes del pipeline
   eran en realidad *un mismo error* manifestándose en distintos
   puntos según el timing de ejecución:
   - Si fallaba temprano → aparecía en health check
   - Si fallaba en submit → aparecía en POST /dubbing
   - Si fallaba en TTS → aparecía en generating_tts
   - Si Flask se bloqueaba → timeout en GET polling

## Evidencia

### Prueba aislada de asyncio + edge-tts (exitosa con SelectorEventLoop)

```
Loop type: _WindowsSelectorEventLoop
TTS OK: 10512 bytes
Success!
```

### Prueba aislada (sin fix → ProactorEventLoop → crash)

No se incluye porque el crash impedía capturar el output,
pero el traceback apuntaba consistentemente a:

    File "edge_tts.py", line 89, in _synthesize_segment_async
      communicate = edge_tts.Communicate(text, voice)
    OSError: [Errno 22] Invalid argument

### Integration test post-fix (exitoso)

```
[11:16:31] Job submitted: 600fd227
[11:16:31] extracting_audio | 15%
[11:16:33] reducing_vocals | 55%
... (Demucs running, polling responde siempre)
```

### Commits con los cambios

| Repo | Commit | Cambio |
|------|--------|--------|
| madrac-dubs | `9528a3e` | WindowsSelectorEventLoopPolicy en api.py |
| madrac-dubs | `9833be8` | threaded=True en Flask |
| madrac-dubs | `4a0f088` | Waitress threads=8 |
| madrac-subs | `fd33c1c` | DubbingManager + DubDialog + retry/poll |
| madrac-hub | `0867e3d` | Integration test poll timeout 15s |
| madrac-hub | `83bb1fc` | PHASE_0_FOUNDATION.md known issue |
| madrac-hub | (pendiente) | Este Documento Llave |

## Replicaciones

- **2026-06-26** — Humano + agente, Windows 11, Python 3.14.5,
  edge-tts 6.1.12, torch 2.x + Demucs.
  Pipeline completo sobre video real de 36s (45 subtítulos).
  Resultado: coincide.

## Observaciones / Deudas Técnicas

1. **Demucs + GIL:** El pipeline se bloquea durante Demucs porque
   torch toma el GIL. Waitress con threads=8 mitiga el problema
   para polling, pero no resuelve la contención de CPU. Para
   producción haría falta worker processes (gunicorn + waitress
   channel) o desacoplar Demucs a un proceso separado.

2. **ProactorEventLoop vs SelectorEventLoop:** Este fix es
   transitorio. Python 3.16+ elimina `set_event_loop_policy`.
   La solución a largo plazo es que `aiohttp`/`edge-tts` soporte
   ProactorEventLoop, o migrar la TTS a otro mecanismo.

3. **Cache de TTS:** La primera corrida descarga voces de edge-tts
   (~2s) y genera 45 segmentos (~2s c/u con cache miss). Las
   corridas subsecuentes son 100% cache hit en <1s.

4. **Ventana de consola DUBS:** El diagnóstico con CREATE_NEW_CONSOLE
   fue útil pero impráctico (la ventana se cierra al crashear).
   El stderr thread (`_start_stderr_thread`) es la solución
   permanente.

5. **Este Llave no existía antes:** Todo este conocimiento estaba
   distribuido entre 19 sesiones de chat, logs efímeros, y la
   memoria del humano. El costo de no tenerlo: ~10h de diagnóstico
   que podrían haberse reducido a ~2h con un documento similar
   del primer bug de asyncio en Windows.

## Referencias / Fuentes

- ADR-006: `knowledge/decisions/ADR_006_demucs_frozen_bug.md`
  (documenta el bug de Demucs en PyInstaller, diagnosticado
  en paralelo)
- `development/tools/dubs_integration_test.py` — test de
  integración automatizado
- `runtime/contracts/dubbing-api-v1.md` — contrato API
  SUBS↔DUBS
- `development/phases/PHASE_0_FOUNDATION.md` — estado del
  proyecto
- Python docs: `asyncio.set_event_loop_policy()`
- `aiohttp` issue tracker: problemas conocidos con
  ProactorEventLoop en Windows
- `edge-tts` source: usa `aiohttp` para comunicación con
  Microsoft Edge TTS API
