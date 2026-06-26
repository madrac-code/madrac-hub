# HISTORIA DE MADRAC-ASISTENTE (JARVIS)

## Resumen

MADRAC-ASISTENTE es la evolución del asistente personal JARVIS para Windows. Comenzó como un script monolítico y evolucionó hacia una arquitectura modular multi-modelo con soporte para Ollama, Claude y OpenAI.

## Línea de Tiempo

### 12 de junio 2026 - Nacimiento
- `64bf9c7` - "Initial commit: Jarvis Windows assistant"
- Primer commit del proyecto en D:\madrac-asistente
- Autor: madrac-code
- Estructura inicial: asistente.py monolítico con imports a core/

### 13 de junio 2026 - Primeras Mejoras
- `02d900a` - "fix: play_pause, whisper precision, ollama auto-start, media keys"
- Correcciones en control multimedia
- Mejora en precisión de Whisper
- Auto-inicio de Ollama al arrancar
- Soporte de teclas multimedia

### 14 de junio 2026 - Refactor Mayor
- `dafd4d9` - "first commit" (posible reinicio del repo)
- `9cc628c` - "refactor: modular architecture + setup wizard + fixes"
- División del monolito en 8 módulos core/
- Nuevo setup wizard
- Correcciones varias

## Arquitectura Actual

### Módulos Core (D:\madrac-asistente\core\)

```
core/
├── __init__.py       # Exporta todas las funciones clave
├── config.py         # Carga/guarda config.json y perfiles
├── audio.py          # Grabación de audio
├── transcription.py  # Transcripción Whisper
├── ia.py             # Consulta a modelos IA
├── tts.py            # Text-to-speech (PowerShell)
├── actions.py        # Acciones del sistema
├── utils.py          # Utilidades varias
└── historial.py      # Historial de conversación
  → Movido a historial.py raíz
```

### Archivos Principales

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| asistente.py | 212 | Loop principal, orquestación |
| config.json | 62 | Configuración multi-modelo |
| core/config.py | - | Gestor de configuración |
| core/ia.py | - | Cliente IA multi-backend |
| gui.py | - | Interfaz gráfica |
| historial.py | - | Historial de conversación |

### Configuración Multi-Modelo

```json
{
  "modelo_ia": {
    "tipo": "ollama",
    "opciones": {
      "ollama": { "modelo": "qwen2.5:3b" },
      "claude": { "modelo": "claude-3-5-sonnet-20241022" },
      "openai": { "modelo": "gpt-4o-mini" }
    }
  }
}
```

### Instalación

- `iniciar.bat` - Script de inicio
- `empaquetar.bat` - Script de empaquetado PyInstaller
- `Jarvis.spec` - Especificación PyInstaller
- `requirements.txt` - Dependencias
- `run_test.bat` - Script de tests

## Características Implementadas

1. **Wakeword**: "Hey Jarvis" con modelo ONNX (umbral 0.35)
2. **STT**: Whisper small (CPU, int8)
3. **IA**: Ollama (qwen2.5:3b) por defecto, Claude/OpenAI como alternativas
4. **TTS**: PowerShell (Microsoft Sabina Desktop), con opciones pyttsx3/Azure
5. **GUI**: Interfaz gráfica con tema dark
6. **Media Keys**: Control de reproducción multimedia
7. **Perfiles**: Sistema de perfiles de usuario
8. **Historial**: Conversación con max 10 turnos

## Estado Actual

- **Versión**: v3.2.0 (inferido del código)
- **Setup**: Completado
- **Ollama**: Auto-inicio al arrancar
- **Multi-modelo**: Configurado pero solo Ollama funcional
- **Empaquetado**: Configurado para PyInstaller

## Relación con MADRAC-CORE

MADRAC-ASISTENTE representa el componente **A** del ecosistema MADRAC:
- Originalmente independiente (JARVIS)
- Posteriormente integrado al ecosistema vía Event Bus + IPC Layer
- Comparte la arquitectura modular con SUBS y DUBS
