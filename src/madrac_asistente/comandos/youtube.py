# ────────────────────────────────────────────────────────────────────
# Comando: YouTube
# ────────────────────────────────────────────────────────────────────
# Abre YouTube en el navegador predeterminado con opción de buscar.
# ────────────────────────────────────────────────────────────────────

import subprocess
import json

TRIGGERS = ["youtube", "you tube", "yt", "videos", "video", "buscar video"]

def cargar_config():
	"""Carga configuración y perfil del usuario."""
	from core import cargar_config as _cargar_config, cargar_perfil
	return _cargar_config(), cargar_perfil()

def get_navegador_predeterminado():
	"""Obtiene el ejecutable del navegador predeterminado."""
	config, perfil = cargar_config()

	# Intentar con brave primero (por defecto configurado)
	navegadores = ["brave.exe", "chrome.exe", "firefox.exe", "msedge.exe"]

	return navegadores[0]  # Brave es el predeterminado

def abrir_youtube(busqueda=None):
	"""
	Abre YouTube en el navegador.

	Args:
		busqueda (str): término de búsqueda (opcional)

	Returns:
		str: URL a abrir
	"""
	if busqueda:
		# Codificar espacios para URL
		busqueda_encoded = busqueda.replace(" ", "+")
		url = f"https://www.youtube.com/results?search_query={busqueda_encoded}"
	else:
		url = "https://www.youtube.com"

	return url

def ejecutar(parametro):
	"""
	Ejecuta el comando de YouTube.

	Args:
		parametro (str): término de búsqueda (opcional)

	Returns:
		tuple: (exito: bool, mensaje: str)
	"""
	try:
		# Obtener URL
		url = abrir_youtube(parametro if parametro else None)

		# Abrir en navegador predeterminado
		subprocess.Popen(f'start {url}', shell=True)

		if parametro:
			return True, f"Buscando '{parametro}' en YouTube"
		else:
			return True, "Abriendo YouTube"

	except Exception as e:
		return False, f"Error abriendo YouTube: {str(e)}"

# Exportar
__all__ = ["ejecutar", "TRIGGERS"]
