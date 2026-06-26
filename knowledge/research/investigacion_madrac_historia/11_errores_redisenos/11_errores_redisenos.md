# ERRORES, RIESGOS Y REDISEÑOS DEL PROYECTO MADRAC

## Resumen

El proyecto MADRAC enfrentó múltiples problemas técnicos documentados, desde crashes de librerías hasta bugs de empaquetado. La evidencia muestra un patrón de "debugging intensivo" especialmente en las fases de build y empaquetado.

## Errores Técnicos Documentados

### 1. Torch Frozen Bug (Crítico)
**Evidencia**: `TORCH_FROZEN_BUG_ANALYSIS.md`, `25fbb19`, `36408cc`
- **Síntoma**: PyTorch se congela durante la inicialización de modelos
- **Impacto**: Crítico - bloquea toda la funcionalidad de transcripción
- **Investigación Documentada**: Fase 1.5 - análisis completo con soluciones
- **Mitigación Propuesta**: Offload a API, usar ONNX Runtime
- **Estado**: Bug analizado, workaround identificado

### 2. PySide6 + Torch Crash
**Evidencia**: `467d636` - "fix: resolve PySide6+torch crash"
- **Síntoma**: Crashes al cargar PySide6 y torch simultáneamente
- **Impacto**: Alto - bloquea la GUI en Windows
- **Solución**: Limpieza de estructura del proyecto, posiblemente reorden de imports

### 3. Empaquetado PyInstaller (Recurrente)
**Evidencia**: Múltiples commits de fix:
- `a469321` - "fix(build): revert subprocess worker, auto-install deps"
- `366ff53` - "fix: spec file point to main.py instead of deleted entry_point.py"
- `4b99370` - "fix: _mover_a_papelera use create_unicode_buffer"
- `1dc2339` - "docs: add prompt and context files for AI agent to fix Windows packaging"
- **Impacto**: Alto - afecta la distribución del producto
- **Archivos de log**: `build_errors.log`, `exe_stderr.log` (4 archivos), `exe_stdout.log` (4 archivos), `build_output.log`

### 4. Problemas de Encoding (UTF-8)
**Evidencia**: `9ad1248` - "v3 consolidation: io_utils UTF-8 safety"
- **Síntoma**: Archivos con caracteres especiales no se procesaban correctamente
- **Impacto**: Medio - afecta subtítulos con caracteres no ASCII

### 5. COM DropHandler Issues
**Evidencia**: `722de56`, `1d678ad`, `9ad1248`
- **Síntoma**: El handler de arrastrar y soltar en Explorer no funcionaba
- **Impacto**: Medio - afecta UX en Windows
- **Iteraciones**: 3 fixes distintos hasta solución

## Riesgos Identificados

**Fuente**: `PHASES.md` sección "Riesgos principales"

| Riesgo | Impacto | Mitigación |
|--------|---------|-----------|
| Bug torch frozen no resuelto | 🔴 CRÍTICO | Offload a API, ONNX Runtime |
| Versiones incompatibles (torch 2.6+, transformers 4.40+) | 🟠 ALTO | CI tests en múltiples versiones |
| Supabase RLS insuficiente | 🔴 CRÍTICO | Audit + penetration test |
| Arquitectura raíz/src confusa | 🟠 ALTO | Consolidar en Fase 1 |
| Web MVP incompleto | 🟠 ALTO | Priorizar Fase 2.1-2.3 |

## Rediseños y Refactors

### 1. Refactor Arquitectura Modular (14 junio)
**Evidencia**: `9cc628c`
- **De**: Monolito JARVIS
- **A**: core/ package con 8 módulos
- **Incluye**: Setup wizard nuevo

### 2. Consolidación v3 SUBS (22 junio)
**Evidencia**: `9ad1248`
- **De**: Arquitectura raíz/src duplicada
- **A**: Unificación en src/madrac/
- **Incluye**: UTF-8 safety, COM drop handler fix

### 3. Reorganización Entry Point
**Evidencia**: `ENTRY_POINT.md`
- **De**: `main.py` raíz (legacy)
- **A**: `src/madrac/cli/main.py`
- **Estado**: En progreso (deprecación pendiente)

## Problemas de Calidad

### Coverage de Tests
**Evidencia**: `PHASES.md`
- **Actual**: 257 tests, 39% coverage
- **Objetivo Fase 1**: >= 40% coverage
- **Estado**: En progreso, CI/CD GitHub Actions configurado

### Dependencias
**Evidencia**: `requirements.txt` en SUBS
- Python 3.11 (versión específica)
- PySide6>=6.8.0, faster-whisper==1.0.2, transformers==4.35.2
- Versiones pineadas en Phase 1.6 (`36408cc`)

## Patrón de Errores Observado

1. **Problemas de Build**: El mayor grupo de errores (5+ commits de fix)
2. **Compatibilidad de Librerías**: PySide6+Torch, PyInstaller+Torch
3. **Encoding y Paths**: Problemas multiplataforma (Windows vs Linux)
4. **Recurrencia**: Algunos bugs (COM handler) requirieron 3+ iteraciones
