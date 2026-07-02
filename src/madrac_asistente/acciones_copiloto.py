# ────────────────────────────────────────────────────────────────────
# Acciones Permitidas para IA Copiloto
# ────────────────────────────────────────────────────────────────────
# Define qué acciones puede ejecutar la IA copiloto de forma segura.
# Actúa como "whitelist" de funciones que el copiloto puede llamar.
# ────────────────────────────────────────────────────────────────────

import logging
from typing import Dict, List, Tuple, Any, Callable

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Acciones de Comandos
# ────────────────────────────────────────────────────────────────────

def accion_crear_comando(nombre: str, triggers: List[str], tipo: str, 
						 parametro: str = "", descripcion: str = "") -> Tuple[bool, str, Any]:
	"""Crea un nuevo comando dinámico."""
	import comandos_usuario
	exito, msg, cmd_id = comandos_usuario.crear_comando(nombre, triggers, tipo, parametro, descripcion)
	return exito, msg, {"cmd_id": cmd_id} if exito else None

def accion_editar_comando(cmd_id: str, **kwargs) -> Tuple[bool, str, Any]:
	"""Edita un comando existente."""
	import comandos_usuario
	exito, msg = comandos_usuario.editar_comando(cmd_id, **kwargs)
	return exito, msg, {"cmd_id": cmd_id} if exito else None

def accion_eliminar_comando(cmd_id: str) -> Tuple[bool, str, Any]:
	"""Elimina un comando."""
	import comandos_usuario
	exito, msg = comandos_usuario.eliminar_comando(cmd_id)
	return exito, msg, None

def accion_obtener_comando(cmd_id: str) -> Tuple[bool, str, Any]:
	"""Obtiene información de un comando específico."""
	import comandos_usuario
	cmd = comandos_usuario.obtener_comando_por_id(cmd_id)
	if cmd:
		return True, f"Comando encontrado: {cmd.get('nombre')}", cmd
	return False, f"Comando {cmd_id} no encontrado", None

def accion_listar_comandos() -> Tuple[bool, str, Any]:
	"""Lista todos los comandos del usuario."""
	import comandos_usuario
	cmds = comandos_usuario.obtener_todos_los_comandos()
	return True, f"Total: {len(cmds)} comandos", cmds

def accion_ejecutar_comando(cmd_id: str) -> Tuple[bool, str, Any]:
	"""Ejecuta un comando específico."""
	import comandos_usuario
	cmd = comandos_usuario.obtener_comando_por_id(cmd_id)
	if not cmd:
		return False, f"Comando {cmd_id} no encontrado", None

	exito, msg = comandos_usuario.ejecutar_comando(cmd)
	return exito, msg, None

# ────────────────────────────────────────────────────────────────────
# Acciones de Sistema
# ────────────────────────────────────────────────────────────────────

def accion_obtener_contexto_proyecto() -> Tuple[bool, str, Any]:
	"""Obtiene el contexto completo del proyecto."""
	import indexador_proyecto
	contexto = indexador_proyecto.obtener_contexto_completo()
	return True, "Contexto obtenido", contexto

def accion_hablar(texto: str) -> Tuple[bool, str, Any]:
	"""Hace que Jarvis hable."""
	from core import hablar
	exito = hablar(texto)
	return exito, f"TTS: {texto}" if exito else "Error en TTS", None

def accion_obtener_config() -> Tuple[bool, str, Any]:
	"""Obtiene la configuración actual."""
	from core import cargar_config
	config = cargar_config()
	return True, "Configuración cargada", config

def accion_obtener_perfil() -> Tuple[bool, str, Any]:
	"""Obtiene el perfil del usuario."""
	from core import cargar_perfil
	perfil = cargar_perfil()
	return True, "Perfil cargado", perfil

# ────────────────────────────────────────────────────────────────────
# Acciones de Información
# ────────────────────────────────────────────────────────────────────

def accion_obtener_hora() -> Tuple[bool, str, Any]:
	"""Obtiene la hora actual."""
	from datetime import datetime
	hora = datetime.now().strftime("%H:%M:%S")
	return True, f"La hora es: {hora}", hora

def accion_obtener_fecha() -> Tuple[bool, str, Any]:
	"""Obtiene la fecha actual."""
	from datetime import datetime
	fecha = datetime.now().strftime("%d/%m/%Y")
	return True, f"La fecha es: {fecha}", fecha

def accion_obtener_documentacion_arquitectura() -> Tuple[bool, str, Any]:
	"""Obtiene la documentación de arquitectura."""
	import indexador_proyecto
	doc = indexador_proyecto.obtener_documentacion_arquitectura()
	if doc:
		return True, "Arquitectura obtenida", doc
	return False, "No se pudo obtener arquitectura", None

# ────────────────────────────────────────────────────────────────────
# Registro de Acciones Permitidas
# ────────────────────────────────────────────────────────────────────

ACCIONES_PERMITIDAS: Dict[str, Dict[str, Any]] = {
	# ─── Comandos ───
	"crear_comando": {
		"funcion": accion_crear_comando,
		"descripcion": "Crea un nuevo comando dinámico",
		"parametros": {
			"nombre": "str - nombre del comando",
			"triggers": "list[str] - palabras clave",
			"tipo": "str - tipo (abrir_url, abrir_app, escribir, secuencia, hablar)",
			"parametro": "str (opcional) - parámetro del tipo",
			"descripcion": "str (opcional) - descripción"
		},
		"ejemplo": "crear_comando('abrir jira', ['jira', 'abrí jira'], 'abrir_url', 'https://jira.midominio.com')"
	},

	"editar_comando": {
		"funcion": accion_editar_comando,
		"descripcion": "Edita un comando existente",
		"parametros": {
			"cmd_id": "str - ID del comando",
			"**kwargs": "campos a actualizar (nombre, triggers, tipo, parametro, descripcion, activo)"
		},
		"ejemplo": "editar_comando('cmd_001', nombre='abrir jira updated', triggers=['jira', 'jr'])"
	},

	"eliminar_comando": {
		"funcion": accion_eliminar_comando,
		"descripcion": "Elimina un comando",
		"parametros": {
			"cmd_id": "str - ID del comando"
		},
		"ejemplo": "eliminar_comando('cmd_001')"
	},

	"obtener_comando": {
		"funcion": accion_obtener_comando,
		"descripcion": "Obtiene detalles de un comando",
		"parametros": {
			"cmd_id": "str - ID del comando"
		},
		"ejemplo": "obtener_comando('cmd_001')"
	},

	"listar_comandos": {
		"funcion": accion_listar_comandos,
		"descripcion": "Lista todos los comandos del usuario",
		"parametros": {},
		"ejemplo": "listar_comandos()"
	},

	"ejecutar_comando": {
		"funcion": accion_ejecutar_comando,
		"descripcion": "Ejecuta un comando específico",
		"parametros": {
			"cmd_id": "str - ID del comando"
		},
		"ejemplo": "ejecutar_comando('cmd_001')"
	},

	# ─── Sistema ───
	"obtener_contexto_proyecto": {
		"funcion": accion_obtener_contexto_proyecto,
		"descripcion": "Obtiene el contexto completo del proyecto para entender la arquitectura",
		"parametros": {},
		"ejemplo": "obtener_contexto_proyecto()"
	},

	"hablar": {
		"funcion": accion_hablar,
		"descripcion": "Hace que Jarvis hable un texto",
		"parametros": {
			"texto": "str - texto a decir"
		},
		"ejemplo": "hablar('Comando creado exitosamente')"
	},

	"obtener_config": {
		"funcion": accion_obtener_config,
		"descripcion": "Obtiene la configuración del asistente",
		"parametros": {},
		"ejemplo": "obtener_config()"
	},

	"obtener_perfil": {
		"funcion": accion_obtener_perfil,
		"descripcion": "Obtiene el perfil del usuario",
		"parametros": {},
		"ejemplo": "obtener_perfil()"
	},

	# ─── Información ───
	"obtener_hora": {
		"funcion": accion_obtener_hora,
		"descripcion": "Obtiene la hora actual",
		"parametros": {},
		"ejemplo": "obtener_hora()"
	},

	"obtener_fecha": {
		"funcion": accion_obtener_fecha,
		"descripcion": "Obtiene la fecha actual",
		"parametros": {},
		"ejemplo": "obtener_fecha()"
	},

	"obtener_documentacion_arquitectura": {
		"funcion": accion_obtener_documentacion_arquitectura,
		"descripcion": "Obtiene la documentación de arquitectura",
		"parametros": {},
		"ejemplo": "obtener_documentacion_arquitectura()"
	}
}

# ────────────────────────────────────────────────────────────────────
# Funciones de Ejecución Segura
# ────────────────────────────────────────────────────────────────────

def ejecutar_accion_segura(nombre_accion: str, **kwargs) -> Tuple[bool, str, Any]:
	"""
	Ejecuta una acción de forma segura (solo si está en whitelist).

	Args:
		nombre_accion (str): nombre de la acción
		**kwargs: parámetros para la acción

	Returns:
		tuple: (exito, mensaje, resultado)
	"""
	if nombre_accion not in ACCIONES_PERMITIDAS:
		return False, f"Acción no permitida: {nombre_accion}", None

	try:
		accion_info = ACCIONES_PERMITIDAS[nombre_accion]
		funcion = accion_info["funcion"]
		resultado = funcion(**kwargs)
		return resultado  # (exito, msg, data)
	except TypeError as e:
		return False, f"Parámetros inválidos para {nombre_accion}: {e}", None
	except Exception as e:
		logger.error(f"Error ejecutando acción {nombre_accion}: {e}")
		return False, f"Error: {str(e)}", None

def obtener_acciones_disponibles() -> Dict[str, Dict]:
	"""Retorna el catálogo de acciones permitidas."""
	return {
		nombre: {
			"descripcion": info["descripcion"],
			"parametros": info["parametros"],
			"ejemplo": info["ejemplo"]
		}
		for nombre, info in ACCIONES_PERMITIDAS.items()
	}

def obtener_documentacion_acciones() -> str:
	"""Retorna documentación formateada de todas las acciones."""
	doc = "## ACCIONES DISPONIBLES PARA IA COPILOTO\n\n"
	for nombre, info in ACCIONES_PERMITIDAS.items():
		doc += f"### {nombre}\n"
		doc += f"**Descripción**: {info['descripcion']}\n"
		doc += f"**Parametros**: {info['parametros']}\n"
		doc += f"**Ejemplo**: `{info['ejemplo']}`\n\n"
	return doc

# ────────────────────────────────────────────────────────────────────
# API pública
# ────────────────────────────────────────────────────────────────────

__all__ = [
	"ejecutar_accion_segura",
	"obtener_acciones_disponibles",
	"obtener_documentacion_acciones",
	"ACCIONES_PERMITIDAS"
]
