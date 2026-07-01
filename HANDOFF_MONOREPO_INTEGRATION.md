# 🚀 HANDOFF: Monorepo Integration Strategy

**De**: Agente de Engineering Sprint 001 (Distribution Testing)  
**Para**: Agente de madrac-hub (Monorepo Architect)  
**Fecha**: 2026-07-01  
**Prioridad**: ALTA — Bloquea Phase 2

---

## El Contexto

### Lo que pasó

Intentamos compilar madrac-dubs con Nuitka usando `nuitkaBuild_Windows.bat` en D:\madrac-dubs.

**Resultado**: ❌ FALLO
```
ModuleNotFoundError: No module named 'ctranslate2'
```

**Causa raíz**: ctranslate2 es dependencia de madrac-subs, NO de madrac-dubs. Cada repo tiene su requirements.txt independiente y su venv separado. El script asume que TODAS las dependencias están disponibles, pero está en el entorno equivocado.

### El Aprendizaje

**Arquitectura actual = FRÁGIL**:
- Builds dispersos por repo
- Dependencias no alineadas
- No hay orquestación central
- Cada componente es un silo

**Solución**: Centralizar TODO en madrac-hub como **monorepo orchestrator**.

---

## La Propuesta

### Estructura Target

```
D:\madrac-hub\
├── build.bat                        ← ÚNICO script de build
├── requirements.txt                 ← ÚNICO archivo de dependencias
├── pyproject.toml                   ← Metadata unificada (opcional Python 3.12+)
│
├── src/
│   ├── madrac_subs/                 ← UI (de D:\madrac-subs o submodule)
│   │   ├── src/madrac/
│   │   ├── tests/
│   │   └── requirements.txt          ← IGNORAR (usar del hub)
│   │
│   └── madrac_dubbing/              ← API/Engine (de D:\madrac-dubs o submodule)
│       ├── src/madrac_dubbing/
│       ├── tests/
│       └── requirements.txt          ← IGNORAR (usar del hub)
│
├── venv/                            ← ÚNICO virtualenv para todo
│
├── .gitignore                       ← Updated (venv, nuitka builds, etc.)
│
└── docs/
	├── ADR_008_monorepo_integration.md  ← Nueva decisión
	└── BUILD.md                         ← Instrucciones de build
```

### Cambios Clave

| Aspecto | Antes | Ahora |
|--------|-------|-------|
| **Ubicación build.bat** | madrac-subs, madrac-dubs (disperso) | madrac-hub/build.bat (único) |
| **requirements.txt** | Uno por repo | Uno integrado en hub |
| **venv** | Uno por repo | Uno en hub |
| **Punto de entrada** | ¿Cuál? (ambiguo) | **TBD** — ¿UI o API? |
| **Dependencias** | Fragmentadas | Mergeadas (dedupe) |
| **Verificación imports** | Verificar solo del repo | Verificar ambos componentes |
| **Tests** | Corrida individual | Orquestada desde hub |

---

## Tareas para la Agente en madrac-hub

### Task 1: Diseñar estructura final (30 min)

**Decisiones a tomar**:

1. **¿Submodules o carpetas?**
   - `git submodule add <url>` → Control de versiones separado
   - `cp -r <src> dst/` → Más simple, acoplado
   - **Recomendación**: Submodules (más limpio long-term)

2. **¿Punto de entrada único o dual?**
   - **Opción A**: UI es main (`madrac-hub.exe` = PySide6 app), DUBS es servicio background
   - **Opción B**: API es main (`api.exe` = Flask), UI es cliente web
   - **Opción C**: Dos ejecutables + launcher
   - **Recomendación**: Opción A (UI first, DUBS as service para Enterprise)

3. **¿Estructura de imports?**
   - `from madrac_subs import ...`
   - `from madrac_dubbing import ...`
   - (Sin cambios en los módulos internos)

### Task 2: Consolidar requirements.txt (15 min)

**Archivo target**: `D:\madrac-hub\requirements.txt`

**Proceso**:
1. Copiar `D:\madrac-subs\requirements.txt`
2. Copiar `D:\madrac-dubs\requirements.txt`
3. Mergear (eliminar duplicados)
4. Ordenar por categoría (UI, Audio, Translation, API, Tools, Testing)
5. Agregar herramientas de build: `nuitka`, `zstandard`

**Validar**:
- `pip install -r requirements.txt --dry-run`
- No versiones conflictivas

### Task 3: Crear build.bat centralizado (45 min)

**Base**: Combinar `madrac-subs/build_windows.bat` + `madrac-dubs/nuitkaBuild_Windows.bat`

**Estructura general**:

```batch
[1] Verificar estructura (src/madrac_subs, src/madrac_dubbing, etc.)
[2] Crear/activar venv único
[3] Instalar requirements.txt unificado
[4] Verificar imports:
	  - madrac_subs: torch, PySide6, ctranslate2, faster_whisper, etc.
	  - madrac_dubbing: demucs, edge_tts, torch, etc.
[5] Ejecutar tests:
	  - pytest tests/ en madrac_subs
	  - pytest tests/ en madrac_dubbing
[6] Limpiar builds anteriores
[7] Compilar (elegir: Nuitka o PyInstaller)
	  - Decisión: ¿Mantener ambos o elegir uno?
	  - Recomendación: Usar PyInstaller por ahora (probado), Nuitka posterior
[8] Validar ejecutable
[9] Mostrar resultado + próximos pasos
```

### Task 4: Actualizar .gitignore (10 min)

Agregar:
```
venv/
*.exe
*.spec
src/madrac_subs/venv/
src/madrac_dubbing/venv/
.nuitka_build/
build/
dist/
*.log
pip_errors.log
nuitka_build.log
```

### Task 5: Crear documentación (30 min)

**Archivos a crear**:

1. `D:\madrac-hub\docs\BUILD.md`
   - Instrucciones: Cómo buildear desde cero
   - Requisitos (Python 3.14, MSVC, ffmpeg)
   - Troubleshooting

2. Actualizar ADR_008 con decisiones finales

---

## Preguntas Frecuentes para la Agente

**P1: ¿Qué hacemos con los builds individuales en madrac-subs y madrac-dubs?**  
**R**: Los deixamos por ahora (no eliminar). Son útiles para testing local. Pero la fuente oficial de build es madrac-hub.

**P2: ¿Los tests individuales se mantienen?**  
**R**: Sí. Madrac-subs y madrac-dubs siguen con sus tests. El hub solo las orquesta.

**P3: ¿Cuándo hacemos el build de Nuitka?**  
**R**: Después de que PyInstaller funcione desde hub. Primero estabilizar, luego optimizar.

**P4: ¿Qué versión de Python target?**  
**R**: 3.14 (como está). Si Nuitka falla, revert a 3.13 (más stable).

**P5: ¿Cuál es el output final? ¿Un archivo .exe o un directorio?**  
**R**: Inicialmente un archivo .exe (PyInstaller). Más adelante, posiblemente un directorio (Nuitka).

---

## Timeline Estimado

| Task | Duración | Blocker |
|------|----------|---------|
| Diseño estructura | 30 min | No |
| requirements.txt | 15 min | No |
| build.bat | 45 min | **SÍ** — bloquer siguientes |
| .gitignore | 10 min | No |
| Docs | 30 min | No |
| **Total** | ~2 horas | |

---

## Success Criteria

✅ `build.bat` en madrac-hub ejecuta sin errores  
✅ Verifica imports de AMBOS componentes  
✅ Ejecuta tests de AMBOS componentes  
✅ Genera ejecutable final (madrac.exe o similar)  
✅ Documentación clara para usuario  
✅ ADR_008 documentada con decisiones finales

---

## Blockers Conocidos

1. **Submodules vs carpetas**: Decisión de arquitectura. Recomiendo submodules.
2. **Punto de entrada**: ¿UI o API? Recomiendo UI (más user-friendly).
3. **Python 3.14 experimental**: Si hay issues, revert a 3.13.

---

## Siguiente Paso (Después de Completar)

Una vez que build.bat funcione desde madrac-hub:

1. **Validar build**: Usuario ejecuta `build.bat`, verifica output
2. **Testar ejecutable**: Lanzar UI o API según punto de entrada
3. **Documentar**: Crear LLAVE_00X si hay issues
4. **Decidir**: ¿Nuitka o PyInstaller? (basado en experiencia)

Luego: **Phase 2 puede comenzar** (Event Bus, UI improvements, etc.)

---

## Contacto

Si la agente en madrac-hub tiene preguntas durante implementación:
- Revisar ADR_008_monorepo_integration.md (decisiones explicadas)
- Ver notas en este documento (handoff details)
- Preguntar al usuario si hay decisiones ambiguas

