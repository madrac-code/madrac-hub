# ────────────────────────────────────────────────────────────────────
# Comando: Escritura (Simular escritura con teclado)
# ────────────────────────────────────────────────────────────────────
# Escribe texto como si fuera escrito por el usuario en tiempo real.
# Útil para búsquedas, escribir en formularios, etc.
# ────────────────────────────────────────────────────────────────────

import pyautogui
import time

TRIGGERS = ["escribi", "escribe", "escrito", "escrib", "write", "type"]

def ejecutar(parametro):
	"""
	Escribe texto mediante simulación de teclado.

	Args:
		parametro (str): texto a escribir

	Returns:
		tuple: (exito: bool, mensaje: str)
	"""
	if not parametro or parametro.strip() == "":
		return False, "No hay texto para escribir."

	# Pequeña pausa para que el usuario tenga tiempo de enfocarse en la ventana
	time.sleep(1)

	try:
		# pyautogui.write() tiene limitaciones con caracteres especiales
		# Por eso usamos typewrite que es más confiable
		# Convertir a string seguro
		texto_seguro = str(parametro)

		# Usar typewrite en lugar de write para mejor compatibilidad
		pyautogui.typewrite(texto_seguro, interval=0.05)

		return True, f"Escribí: {parametro}"
	except Exception as e:
		# Si falla typewrite, intentar con un método alternativo
		try:
			# Usar pyperclip si está disponible (más seguro para texto complejo)
			import pyperclip
			pyperclip.copy(parametro)
			pyautogui.hotkey('ctrl', 'v')
			return True, f"Pegué: {parametro}"
		except:
			# Si todo falla, retornar error
			return False, f"Error escribiendo texto: {str(e)}"

# Exportar
__all__ = ["ejecutar", "TRIGGERS"]
