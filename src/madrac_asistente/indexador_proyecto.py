# ────────────────────────────────────────────────────────────────────
# Indexador de Proyecto
# ────────────────────────────────────────────────────────────────────
# Lee archivos .md, estructura, comandos y config del proyecto.
# Expone contexto dinámico para que la IA copiloto entienda la arquitectura.
# ────────────────────────────────────────────────────────────────────

import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Funciones de lectura de documentación
# ────────────────────────────────────────────────────────────────────

def leer_archivo_md(ruta: str) -> Optional[str]:
	"""Lee un archivo markdown."""
	try:
		if os.path.exists(ruta):
			with open(ruta, "r", encoding="utf-8") as f:
				return f.read()
	except Exception as e:
		logger.warning(f"No se pudo leer {ruta}: {e}")
	return None

def obtener_documentacion_arquitectura() -> Optional[str]:
	"""Obtiene la documentación de arquitectura del proyecto."""
	return leer_archivo_md("ARQUITECTURA.md")

def obtener_readme() -> Optional[str]:
	"""Obtiene el README del proyecto."""
	return leer_archivo_md("README.md")

def obtener_documentacion_cambios() -> Optional[str]:
	"""Obtiene el log de cambios."""
	return leer_archivo_md("CAMBIOS.md")

def obtener_ejemplos() -> Optional[str]:
	"""Obtiene ejemplos de uso."""
	return leer_archivo_md("EJEMPLOS.md")

# ────────────────────────────────────────────────────────────────────
# Funciones de indexación de estructura
# ────────────────────────────────────────────────────────────────────

def obtener_estructura_proyecto() -> Dict:
	"""
	Obtiene información sobre la estructura del proyecto.

	Returns:
		Dict: información de archivos y carpetas principales
	"""
	estructura = {
		"archivos_principales": [],
		"carpetas": [],
		"comandos_core": [],
		"comandos_usuario": []
	}

	# Archivos principales
	archivos_importantes = [
		"asistente.py", "core/", "gui.py", 
		"config.json", "perfiles/default.json"
	]
	for archivo in archivos_importantes:
		if os.path.exists(archivo):
			estructura["archivos_principales"].append(archivo)

	# Carpetas
	carpetas = ["comandos", "perfiles", "logs", "data"]
	for carpeta in carpetas:
		if os.path.exists(carpeta):
			estructura["carpetas"].append(carpeta)

	# Comandos core
	if os.path.exists("comandos"):
		for archivo in os.listdir("comandos"):
			if archivo.endswith(".py") and not archivo.startswith("__"):
				estructura["comandos_core"].append(archivo.replace(".py", ""))

	# Comandos usuario
	try:
		import comandos_usuario
		cmds = comandos_usuario.obtener_todos_los_comandos()
		estructura["comandos_usuario"] = [
			{"id": c.get("id"), "nombre": c.get("nombre"), "tipo": c.get("tipo")}
			for c in cmds
		]
	except Exception as e:
		logger.warning(f"No se pudieron cargar comandos usuario: {e}")

	return estructura

# ────────────────────────────────────────────────────────────────────
# Funciones de indexación de configuración
# ────────────────────────────────────────────────────────────────────

def obtener_config_ia() -> Optional[Dict]:
	"""Obtiene información de la configuración de IA."""
	try:
		from core import cargar_config
		config = cargar_config()
		return {
			"tipo_ia": config.get("modelo_ia", {}).get("tipo"),
			"modelo": config.get("modelo_ia", {}).get("opciones", {}).get("ollama", {}).get("modelo"),
			"audio": {
				"sample_rate": config.get("audio", {}).get("sample_rate"),
				"chunk_size": config.get("audio", {}).get("chunk_size")
			},
			"tts": {
				"motor": config.get("tts", {}).get("motor")
			}
		}
	except Exception as e:
		logger.warning(f"No se pudo leer config.json: {e}")
	return None

def obtener_perfil_usuario() -> Optional[Dict]:
	"""Obtiene información del perfil del usuario."""
	try:
		from core import cargar_perfil
		perfil = cargar_perfil()
		return {
			"nombre": perfil.get("nombre"),
			"idioma": perfil.get("idioma"),
			"aplicaciones": list(perfil.get("aplicaciones", {}).keys()),
			"musica_favorita": list(perfil.get("musica", {}).keys())
		}
	except Exception as e:
		logger.warning(f"No se pudo leer perfil: {e}")
	return None

# ────────────────────────────────────────────────────────────────────
# Función principal de contexto
# ────────────────────────────────────────────────────────────────────

def obtener_contexto_completo() -> Dict:
	"""
	Obtiene el contexto completo del proyecto para la IA copiloto.

	Returns:
		Dict: contexto completo incluyendo arquitectura, comandos, config
	"""
	contexto = {
		"proyecto": "Asistente Jarvis",
		"tipo_contexto": "system_prompt_para_ia_copiloto",
		"fecha_generacion": __import__("datetime").datetime.now().isoformat(),

		# Documentación
		"documentacion": {
			"arquitectura": "Disponible (leer ARQUITECTURA.md para detalles completos)",
			"readme": "Disponible (leer README.md para información general)",
			"cambios": "Disponible (leer CAMBIOS.md para histórico)"
		},

		# Estructura
		"estructura": obtener_estructura_proyecto(),

		# Configuración
		"configuracion": obtener_config_ia(),
		"perfil": obtener_perfil_usuario(),

		# Capacidades
		"capacidades": {
			"tipos_comandos_usuario": [
				"abrir_url - abre URL en navegador",
				"abrir_app - abre aplicación",
				"escribir - simula escritura de teclado",
				"secuencia - ejecuta varios comandos",
				"hablar - hace que el asistente hable"
			],
			"comandos_core": [
				"reproducir_musica",
				"abrir_app",
				"cerrar_ventana",
				"obtener_hora",
				"obtener_fecha",
				"escribir",
				"youtube",
				"conversar"
			]
		},

		# API de acciones que puede usar
		"api_acciones_disponibles": {
			"crear_comando": "create_comando(nombre, triggers, tipo, parametro, descripcion)",
			"editar_comando": "editar_comando(cmd_id, **kwargs)",
			"eliminar_comando": "eliminar_comando(cmd_id)",
			"obtener_comando": "obtener_comando_por_id(cmd_id)",
			"listar_comandos": "obtener_todos_los_comandos()",
			"cargar_config": "cargar_config() -> Dict",
			"guardar_config": "guardar_config(config: Dict)",
			"hablar": "hablar(texto: str) -> bool",
			"ejecutar_accion": "ejecutar_accion(accion: str, parametro: str) -> (bool, str)"
		}
	}

	return contexto

def obtener_resumen_contextual(max_chars: int = 2000) -> str:
	"""
	Obtiene un resumen del proyecto en formato texto para incluir en system prompt.

	Args:
		max_chars (int): máximo de caracteres a retornar

	Returns:
		str: resumen contextual
	"""
	contexto = obtener_contexto_completo()

	resumen = f"""
## CONTEXTO DEL PROYECTO JARVIS

### Estructura
- **Comandos core** (Python): {', '.join(contexto['estructura'].get('comandos_core', []))}
- **Comandos usuario** (dinámicos): {len(contexto['estructura'].get('comandos_usuario', []))} comandos creados

### Configuración Actual
- **IA**: {contexto['configuracion'].get('tipo_ia') if contexto.get('configuracion') else 'no configurada'}
- **Usuario**: {contexto['perfil'].get('nombre') if contexto.get('perfil') else 'sin configurar'}

### Tipos de Comandos que Puedes Crear
{chr(10).join(f"- {cap}" for cap in contexto['capacidades'].get('tipos_comandos_usuario', []))}

### Tu rol
Sos el copiloto del usuario. Puedes:
1. Crear nuevos comandos dinámicos
2. Editar/eliminar comandos existentes
3. Hacer recomendaciones
4. Ayudar a configurar el asistente

Siempre explica qué haces antes de ejecutar acciones.
"""

	return resumen[:max_chars]

# ────────────────────────────────────────────────────────────────────
# API pública
# ────────────────────────────────────────────────────────────────────

__all__ = [
	"obtener_documentacion_arquitectura",
	"obtener_readme",
	"obtener_documentacion_cambios",
	"obtener_ejemplos",
	"obtener_estructura_proyecto",
	"obtener_config_ia",
	"obtener_perfil_usuario",
	"obtener_contexto_completo",
	"obtener_resumen_contextual"
]
