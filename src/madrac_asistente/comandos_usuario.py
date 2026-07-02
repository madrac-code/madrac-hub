# ────────────────────────────────────────────────────────────────────
# Gestor de Comandos Dinámicos del Usuario
# ────────────────────────────────────────────────────────────────────
# Permite crear, editar, eliminar y ejecutar comandos sin tocar código.
# Funciona en runtime: carga/guarda JSON sin reiniciar.
# ────────────────────────────────────────────────────────────────────

import json
import os
import webbrowser
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

RUTA_COMANDOS_USUARIO = "storage/user_data/comandos_usuario.json"

# ────────────────────────────────────────────────────────────────────
# Funciones de Gestión de JSON
# ────────────────────────────────────────────────────────────────────

def cargar_comandos_usuario() -> Dict:
	"""
	Carga el archivo de comandos del usuario.

	Returns:
		Dict: estructura completa de comandos_usuario.json
	"""
	try:
		if not os.path.exists(RUTA_COMANDOS_USUARIO):
			logger.warning(f"Archivo {RUTA_COMANDOS_USUARIO} no existe. Retornando estructura vacía.")
			return {"comandos": [], "version": "1.0"}

		with open(RUTA_COMANDOS_USUARIO, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception as e:
		logger.error(f"Error cargando comandos usuario: {e}")
		return {"comandos": [], "version": "1.0"}

def guardar_comandos_usuario(data: Dict) -> bool:
	"""
	Guarda los comandos del usuario en JSON.

	Args:
		data (Dict): estructura completa a guardar

	Returns:
		bool: True si se guardó exitosamente
	"""
	try:
		os.makedirs("data", exist_ok=True)
		with open(RUTA_COMANDOS_USUARIO, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2, ensure_ascii=False)
		logger.info(f"Comandos usuario guardados: {len(data.get('comandos', []))} comandos")
		return True
	except Exception as e:
		logger.error(f"Error guardando comandos usuario: {e}")
		return False

# ────────────────────────────────────────────────────────────────────
# Funciones de Búsqueda
# ────────────────────────────────────────────────────────────────────

def buscar_comando_por_trigger(texto: str) -> Optional[Dict]:
	"""
	Busca un comando que coincida con un trigger.

	Args:
		texto (str): texto a buscar (ej: "abre jira")

	Returns:
		Optional[Dict]: comando encontrado o None
	"""
	data = cargar_comandos_usuario()
	texto_lower = texto.lower().strip()

	for cmd in data.get("comandos", []):
		if not cmd.get("activo", True):
			continue

		for trigger in cmd.get("triggers", []):
			if trigger.lower() in texto_lower or texto_lower in trigger.lower():
				logger.info(f"Comando encontrado: {cmd['nombre']}")
				return cmd

	return None

def obtener_comando_por_id(cmd_id: str) -> Optional[Dict]:
	"""
	Obtiene un comando específico por su ID.

	Args:
		cmd_id (str): ID del comando

	Returns:
		Optional[Dict]: comando encontrado o None
	"""
	data = cargar_comandos_usuario()
	for cmd in data.get("comandos", []):
		if cmd.get("id") == cmd_id:
			return cmd
	return None

def obtener_todos_los_comandos() -> List[Dict]:
	"""
	Retorna lista de todos los comandos del usuario.

	Returns:
		List[Dict]: lista de comandos
	"""
	data = cargar_comandos_usuario()
	return data.get("comandos", [])

# ────────────────────────────────────────────────────────────────────
# Funciones de CRUD
# ────────────────────────────────────────────────────────────────────

def crear_comando(nombre: str, triggers: List[str], tipo: str, 
				  parametro: str = "", descripcion: str = "") -> Tuple[bool, str, Optional[str]]:
	"""
	Crea un nuevo comando.

	Args:
		nombre (str): nombre del comando
		triggers (List[str]): palabras clave que lo activan
		tipo (str): tipo de comando (abrir_url, abrir_app, escribir, secuencia, hablar)
		parametro (str): parámetro específico del tipo
		descripcion (str): descripción opcional

	Returns:
		tuple: (exito, mensaje, cmd_id)
	"""
	data = cargar_comandos_usuario()

	# Validaciones
	if not nombre or not triggers:
		return False, "Nombre y triggers son requeridos", None

	if tipo not in data.get("tipos_soportados", []):
		return False, f"Tipo '{tipo}' no soportado", None

	# Generar ID único
	cmd_id = f"cmd_{len(data.get('comandos', [])) + 1:03d}"

	# Crear comando
	nuevo_cmd = {
		"id": cmd_id,
		"nombre": nombre.strip(),
		"triggers": [t.strip().lower() for t in triggers],
		"tipo": tipo,
		"parametro": parametro.strip(),
		"descripcion": descripcion.strip(),
		"activo": True,
		"fecha_creacion": datetime.now().isoformat(),
		"fecha_modificacion": datetime.now().isoformat()
	}

	data["comandos"].append(nuevo_cmd)

	if guardar_comandos_usuario(data):
		return True, f"Comando '{nombre}' creado exitosamente", cmd_id
	else:
		return False, "Error guardando comando", None

def editar_comando(cmd_id: str, **kwargs) -> Tuple[bool, str]:
	"""
	Edita un comando existente.

	Args:
		cmd_id (str): ID del comando a editar
		**kwargs: campos a actualizar (nombre, triggers, tipo, parametro, descripcion, activo)

	Returns:
		tuple: (exito, mensaje)
	"""
	data = cargar_comandos_usuario()

	cmd = None
	for i, c in enumerate(data.get("comandos", [])):
		if c["id"] == cmd_id:
			cmd = c
			idx = i
			break

	if not cmd:
		return False, f"Comando {cmd_id} no encontrado"

	# Actualizar campos permitidos
	campos_permitidos = ["nombre", "triggers", "tipo", "parametro", "descripcion", "activo"]
	for campo, valor in kwargs.items():
		if campo in campos_permitidos:
			if campo == "triggers" and isinstance(valor, list):
				cmd[campo] = [t.strip().lower() for t in valor]
			else:
				cmd[campo] = valor

	cmd["fecha_modificacion"] = datetime.now().isoformat()
	data["comandos"][idx] = cmd

	if guardar_comandos_usuario(data):
		return True, f"Comando {cmd_id} actualizado"
	else:
		return False, "Error guardando cambios"

def eliminar_comando(cmd_id: str) -> Tuple[bool, str]:
	"""
	Elimina un comando.

	Args:
		cmd_id (str): ID del comando a eliminar

	Returns:
		tuple: (exito, mensaje)
	"""
	data = cargar_comandos_usuario()

	original_len = len(data.get("comandos", []))
	data["comandos"] = [c for c in data.get("comandos", []) if c["id"] != cmd_id]

	if len(data["comandos"]) < original_len:
		if guardar_comandos_usuario(data):
			return True, f"Comando {cmd_id} eliminado"
		else:
			return False, "Error guardando cambios"
	else:
		return False, f"Comando {cmd_id} no encontrado"

# ────────────────────────────────────────────────────────────────────
# Funciones de Ejecución
# ────────────────────────────────────────────────────────────────────

def ejecutar_comando(cmd: Dict) -> Tuple[bool, str]:
	"""
	Ejecuta un comando del usuario.

	Args:
		cmd (Dict): estructura del comando

	Returns:
		tuple: (exito, mensaje)
	"""
	try:
		tipo = cmd.get("tipo")
		parametro = cmd.get("parametro", "")

		logger.info(f"Ejecutando comando: {cmd['nombre']} (tipo: {tipo})")

		if tipo == "abrir_url":
			return _ejecutar_abrir_url(parametro)

		elif tipo == "abrir_app":
			return _ejecutar_abrir_app(parametro)

		elif tipo == "escribir":
			return _ejecutar_escribir(parametro)

		elif tipo == "secuencia":
			return _ejecutar_secuencia(cmd.get("acciones", []))

		elif tipo == "hablar":
			return _ejecutar_hablar(parametro)

		else:
			return False, f"Tipo de comando desconocido: {tipo}"

	except Exception as e:
		logger.error(f"Error ejecutando comando: {e}")
		return False, f"Error: {str(e)}"

def _ejecutar_abrir_url(url: str) -> Tuple[bool, str]:
	"""Abre una URL en el navegador."""
	try:
		webbrowser.open(url)
		return True, f"Abriendo URL: {url}"
	except Exception as e:
		return False, f"Error abriendo URL: {e}"

def _ejecutar_abrir_app(app_name: str) -> Tuple[bool, str]:
	"""Abre una aplicación."""
	try:
		# Importar desde comandos.apps para reutilizar lógica existente
		from comandos import apps
		return apps.abrir_app(app_name)
	except Exception as e:
		return False, f"Error abriendo app: {e}"

def _ejecutar_escribir(texto: str) -> Tuple[bool, str]:
	"""Simula escritura de teclado."""
	try:
		from comandos import escribir
		return escribir.ejecutar(texto)
	except Exception as e:
		return False, f"Error escribiendo: {e}"

def _ejecutar_secuencia(acciones: List[str]) -> Tuple[bool, str]:
	"""Ejecuta una secuencia de comandos."""
	resultados = []
	for accion in acciones:
		cmd = buscar_comando_por_trigger(accion)
		if cmd:
			exito, msg = ejecutar_comando(cmd)
			resultados.append(f"✓ {msg}" if exito else f"✗ {msg}")
		else:
			# Intentar ejecutar como comando core
			try:
				from core import ejecutar_accion
				exito, msg = ejecutar_accion(accion, "")
				resultados.append(f"✓ {msg}" if exito else f"✗ {msg}")
			except:
				resultados.append(f"✗ No se encontró acción: {accion}")

	return True, f"Secuencia completada. Resultados: {'; '.join(resultados)}"

def _ejecutar_hablar(texto: str) -> Tuple[bool, str]:
	"""Hace que el asistente hable."""
	try:
		from core import hablar
		exito = hablar(texto)
		if exito:
			return True, f"Jarvis dijo: {texto}"
		else:
			return False, "Error en TTS"
	except Exception as e:
		return False, f"Error hablando: {e}"

# ────────────────────────────────────────────────────────────────────
# API pública
# ────────────────────────────────────────────────────────────────────

__all__ = [
	"cargar_comandos_usuario",
	"guardar_comandos_usuario",
	"buscar_comando_por_trigger",
	"obtener_comando_por_id",
	"obtener_todos_los_comandos",
	"crear_comando",
	"editar_comando",
	"eliminar_comando",
	"ejecutar_comando"
]
