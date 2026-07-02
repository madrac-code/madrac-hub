# Decisión: Monorepo Integration — Centralizar en madrac-hub

**Date**: 2026-07-01  
**Status**: DECISION POINT  
**Impact**: Arquitectura de build + dependencias

---

## El Problema

El script `nuitkaBuild_Windows.bat` en madrac-dubs falló porque:

```
ModuleNotFoundError: No module named 'ctranslate2'
```

**Raíz**: ctranslate2 es dependencia de **madrac-subs** (MarianMT translation), NO de madrac-dubs.

**Por qué pasó**:
- Cada repo tiene su propio `requirements.txt`
- Cada repo tiene su propio `venv`
- El script intenta verificar imports de múltiples componentes
- ctranslate2 **no está en madrac-dubs/requirements.txt**
- Pero el script asume que todos los imports están disponibles

**Síntoma**: Arquitectura dispersa = dependencias no alineadas = builds frágiles

---

## La Decisión

**CANCELAR**: builds individuales por repo (madrac-dubs, madrac-subs)

**ADOPTAR**: madrac-hub como **único punto de entrada**

```
D:\madrac-hub\
├── build.bat                    ← ÚNICO build script (Nuitka o PyInstaller)
├── requirements.txt             ← ÚNICA lista de dependencias (integrada)
├── pyproject.toml               ← Metadata unificada
├── venv/                        ← ÚNICO virtualenv para todo
│
├── src/
│   ├── madrac_subs/             ← Librería (madrac-subs como submódulo)
│   └── madrac_dubbing/          ← Librería (madrac-dubs como submódulo)
│
└── tests/                       ← Tests integrados
```

---

## Cambios Requeridos

### 1. Dependencias Unificadas

**Nuevo**: `D:\madrac-hub\requirements.txt`

Incluir:
- Todas las dependencias de madrac-subs (PySide6, torch, faster_whisper, ctranslate2, etc.)
- Todas las dependencias de madrac-dubs (demucs, edge_tts, etc.)
- Herramientas de build (nuitka, pyinstaller, etc.)

**Ejemplo estructura**:
```
# UI (madrac-subs)
PySide6>=6.6.0
qdarkstyle>=3.2

# Translation (madrac-subs)
faster-whisper>=0.10
ctranslate2>=4.0
transformers>=4.30

# Audio (shared + madrac-dubs)
librosa>=0.10.0
soundfile>=0.12.1
scipy>=1.11.0
torch>=2.0
torchaudio>=0.8
demucs>=4.0

# Speech Synthesis (madrac-dubs)
edge-tts>=6.1.12

# API + Flask (madrac-dubs)
Flask>=3.0.0
waitress>=3.0.0

# Tools
nuitka>=1.4.0
zstandard>=0.21.0
pyinstaller>=6.2

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0

# Utils
python-dotenv>=1.0.0
requests>=2.31.0
click>=8.1.3
numpy>=1.24.0
```

### 2. Build Script Unificado

**Nuevo**: `D:\madrac-hub\build.bat`

Estructura:
1. Verificar estructura (src/madrac_subs, src/madrac_dubbing, etc.)
2. Crear/activar venv
3. Instalar requirements.txt (TODO integrado)
4. Verificar imports de AMBOS componentes
5. Ejecutar tests de AMBOS componentes
6. Compilar con Nuitka (o PyInstaller) → binario único

**Punto de entrada**: ¿Cuál será? ¿Subs (UI) o Dubs (API)?

### 3. Submodulos Git

Consideramos:
```
D:\madrac-hub\.gitmodules
[submodule "src/madrac_subs"]
	path = src/madrac_subs
	url = https://github.com/madrac-code/madrac-subs

[submodule "src/madrac_dubbing"]
	path = src/madrac_dubbing
	url = https://github.com/madrac-code/madrac-dubs
```

**Ventaja**: Histórico separado, pero controlado desde madrac-hub  
**Alternativa**: Clonar directorios como carpetas (sin submodulos)

---

## Acciones Inmediatas

### Para la agente en madrac-hub:

1. **Crear estructura monorepo**
   ```
   src/madrac_subs/      ← copiar desde D:\madrac-subs o usar submodule
   src/madrac_dubbing/   ← copiar desde D:\madrac-dubs o usar submodule
   ```

2. **Consolidar requirements.txt**
   - Mergear madrac-subs/requirements.txt + madrac-dubs/requirements.txt
   - Eliminar duplicados
   - Agregar herramientas de build

3. **Crear build.bat**
   - Base: combinar build_windows.bat (madrac-subs) + nuitkaBuild_Windows.bat
   - Verificar imports de AMBOS componentes
   - Ejecutar tests de AMBOS
   - Single binary output

4. **Actualizar .gitignore**
   - venv/ (único en madrac-hub)
   - src/madrac_subs/.venv → ignorar
   - src/madrac_dubbing/.venv → ignorar
   - nuitka/pyinstaller outputs

---

## FAQ

**P: ¿Qué pasa con los repos actuales (madrac-subs, madrac-dubs)?**  
R: Se mantienen como source of truth para desarrollo individual. madrac-hub es solo el punto de integración.

**P: ¿Los tests siguen siendo individuales por repo?**  
R: Sí, pero madrac-hub/build.bat puede orquestar `pytest` en ambas locations.

**P: ¿Cuál es el binario final? ¿UI o API?**  
R: **Decisión pendiente**. Opciones:
- UI (madrac-subs) como main executable, DUBS como background service
- API (madrac-dubs) como main, UI como client
- Ambos ejecutables + launcher

**P: ¿Submodulos de Git o carpetas copiadas?**  
R: **Pendiente discusión**. Submodulos = control de versiones separado (más limpio). Carpetas = más simple inicialmente.

---

## Timeline

| Step | Owner | Estimado |
|------|-------|----------|
| Diseñar estructura final | agente madrac-hub | 30 min |
| Crear requirements.txt unificado | agente madrac-hub | 15 min |
| Crear build.bat | agente madrac-hub | 45 min |
| Testar build end-to-end | Usuario/agente | 1-2 horas |
| Validar imports/tests | agente madrac-hub | 30 min |
| Documentar decisiones (ADR) | agente madrac-hub | 30 min |

---

## Riesgos & Mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Conflicto dependencias | Usar pipdeptree para auditar; elegir versiones comunes |
| Build time aumenta | Cachear Nuitka; paralelizar tests |
| Confusión entre repos + hub | Documentar clara: hub=integración, subs/dubs=libs |
| Regresión en madrac-subs/dubs | Mantener tests individuales activos; CI/CD por repo |

---

## Conclusión

**madrac-hub es ahora el "monorepo orchestrator"**, no solo un contenedor de docs.

Esto resuelve:
- ✅ Dependencias duplicadas/conflictivas
- ✅ Scripts de build dispersos
- ✅ Import errors por falta de coordination
- ✅ Reproducibilidad (single source of dependencies)

Next: Implementar estructura en D:\madrac-hub

