# ────────────────────────────────────────────────────────────────────
# Panel del Copiloto en GUI
# ────────────────────────────────────────────────────────────────────
# Interfaz de chat para comunicarse con la IA copiloto.
# Se integra como una pestaña adicional en la GUI principal.
# ────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import json
from datetime import datetime
import system_prompt_copiloto
import acciones_copiloto

class PanelCopiloto:
	"""Panel de chat para el copiloto IA integrado en Jarvis."""

	def __init__(self, parent_frame):
		self.frame = parent_frame
		self.historial = []
		self._crear_interfaz()

	def _crear_interfaz(self):
		"""Construye la interfaz del copiloto."""

		# ─── Panel Superior: Título y Estado ───
		panel_titulo = tk.Frame(self.frame, bg="#252525", height=40)
		panel_titulo.pack(fill=tk.X, padx=0, pady=0)

		tk.Label(
			panel_titulo,
			text="🤖 COPILOTO IA - Configuración Inteligente",
			font=("Segoe UI", 11, "bold"),
			bg="#252525",
			fg="#00ff00"
		).pack(anchor=tk.W, padx=10, pady=8)

		# ─── Área de Chat ───
		panel_chat = tk.Frame(self.frame, bg="#1e1e1e")
		panel_chat.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

		# Historial de conversación
		self.chat_text = scrolledtext.ScrolledText(
			panel_chat,
			font=("Consolas", 9),
			bg="#2d2d2d",
			fg="#ffffff",
			insertbackground="#00ff00",
			state=tk.DISABLED,
			wrap=tk.WORD
		)
		self.chat_text.pack(fill=tk.BOTH, expand=True)

		# Configurar tags para colores
		self.chat_text.tag_configure("usuario", foreground="#00ff00", font=("Consolas", 9, "bold"))
		self.chat_text.tag_configure("copiloto", foreground="#00ddff", font=("Consolas", 9))
		self.chat_text.tag_configure("sistema", foreground="#ffaa00", font=("Consolas", 9))
		self.chat_text.tag_configure("error", foreground="#ff0000", font=("Consolas", 9, "bold"))

		# ─── Entrada de texto ───
		panel_entrada = tk.Frame(self.frame, bg="#1e1e1e")
		panel_entrada.pack(fill=tk.X, padx=5, pady=5)

		# Campo de entrada
		self.entrada_copiloto = tk.Entry(
			panel_entrada,
			font=("Segoe UI", 10),
			bg="#2d2d2d",
			fg="#ffffff",
			insertbackground="#00ff00"
		)
		self.entrada_copiloto.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 5))
		self.entrada_copiloto.bind("<Return>", lambda e: self._enviar_mensaje())

		# Botón enviar
		tk.Button(
			panel_entrada,
			text="📤 ENVIAR",
			command=self._enviar_mensaje,
			font=("Segoe UI", 9, "bold"),
			bg="#0066cc",
			fg="#ffffff",
			padx=15,
			pady=5
		).pack(side=tk.LEFT, padx=2)

		# ─── Panel Información ───
		panel_info = tk.Frame(self.frame, bg="#252525", height=80)
		panel_info.pack(fill=tk.X, padx=5, pady=5)

		info_texto = (
			"💡 El copiloto entiende la arquitectura de Jarvis. "
			"Pedile que cree/edite comandos, te recomiende automatizaciones, o explique cómo funciona el sistema."
		)

		tk.Label(
			panel_info,
			text=info_texto,
			font=("Segoe UI", 8),
			bg="#252525",
			fg="#cccccc",
			wraplength=700,
			justify=tk.LEFT
		).pack(anchor=tk.W, padx=10, pady=8)

		# Agregar mensaje de bienvenida
		self._agregar_mensaje_sistema("Copiloto iniciado. ¿En qué puedo ayudarte con Jarvis?")

	def _agregar_mensaje_usuario(self, texto: str):
		"""Agrega un mensaje del usuario al chat."""
		self.chat_text.config(state=tk.NORMAL)
		timestamp = datetime.now().strftime("%H:%M:%S")
		self.chat_text.insert(tk.END, f"[{timestamp}] Tú: ", "usuario")
		self.chat_text.insert(tk.END, f"{texto}\n\n")
		self.chat_text.config(state=tk.DISABLED)
		self.chat_text.see(tk.END)

	def _agregar_mensaje_copiloto(self, texto: str):
		"""Agrega un mensaje del copiloto al chat."""
		self.chat_text.config(state=tk.NORMAL)
		timestamp = datetime.now().strftime("%H:%M:%S")
		self.chat_text.insert(tk.END, f"[{timestamp}] Copiloto: ", "copiloto")
		self.chat_text.insert(tk.END, f"{texto}\n\n")
		self.chat_text.config(state=tk.DISABLED)
		self.chat_text.see(tk.END)

	def _agregar_mensaje_sistema(self, texto: str):
		"""Agrega un mensaje del sistema."""
		self.chat_text.config(state=tk.NORMAL)
		timestamp = datetime.now().strftime("%H:%M:%S")
		self.chat_text.insert(tk.END, f"[{timestamp}] ", "sistema")
		self.chat_text.insert(tk.END, f"{texto}\n\n", "sistema")
		self.chat_text.config(state=tk.DISABLED)
		self.chat_text.see(tk.END)

	def _enviar_mensaje(self):
		"""Envía un mensaje al copiloto."""
		mensaje = self.entrada_copiloto.get().strip()
		if not mensaje:
			return

		# Limpiar entrada
		self.entrada_copiloto.delete(0, tk.END)

		# Agregar mensaje del usuario
		self._agregar_mensaje_usuario(mensaje)

		# Procesar en thread para no bloquear GUI
		thread = threading.Thread(
			target=self._procesar_mensaje,
			args=(mensaje,),
			daemon=True
		)
		thread.start()

	def _procesar_mensaje(self, mensaje: str):
		"""Procesa el mensaje y genera respuesta del copiloto."""
		try:
			# Aquí se integraría la lógica de la IA real
			# Por ahora, mostramos una simulación inteligente

			respuesta = self._generar_respuesta_simulada(mensaje)
			self._agregar_mensaje_copiloto(respuesta)

		except Exception as e:
			error_msg = f"Error procesando tu mensaje: {e}"
			self._agregar_mensaje_sistema(error_msg)

	def _generar_respuesta_simulada(self, mensaje: str) -> str:
		"""
		Genera una respuesta simulada. En producción, aquí iría la llamada a la IA real.

		Esta función detecta patrones comunes para demostrar las capacidades.
		"""
		msg_lower = mensaje.lower()

		# Reconocer intenciones comunes
		if any(word in msg_lower for word in ["crear", "nuevo", "comando", "quiero"]):
			return self._respuesta_crear_comando(mensaje)

		elif any(word in msg_lower for word in ["lista", "cuales", "comandos"]):
			return self._respuesta_listar_comandos()

		elif any(word in msg_lower for word in ["ayuda", "como funciona", "explicar"]):
			return self._respuesta_explicar_sistema()

		elif any(word in msg_lower for word in ["abrí", "abrir", "ejecutar"]):
			return self._respuesta_sugerencia_comando(mensaje)

		else:
			# Respuesta genérica
			return (
				"Entendí tu solicitud boludo 🤖\n\n"
				"Para que pueda ayudarte mejor, podés:\n"
				"• Pedirme que cree un comando nuevo\n"
				"• Decirme qué tareas repetitivas hacés\n"
				"• Preguntar cómo funciona algo\n\n"
				"¿Qué te gustaría hacer?"
			)

	def _respuesta_crear_comando(self, mensaje: str) -> str:
		"""Respuesta cuando el usuario quiere crear un comando."""
		return (
			"Perfecto che! 🚀 Voy a ayudarte a crear un comando.\n\n"
			"Para armarlo necesito saber:\n"
			"1. ¿Qué nombre le ponemos?\n"
			"2. ¿Qué palabras va a escuchar el asistente? (triggers)\n"
			"3. ¿Qué queres que haga? (abrir URL/app, escribir, secuencia, etc)\n\n"
			"Describime tu caso de uso y me encargo del resto 💪"
		)

	def _respuesta_listar_comandos(self) -> str:
		"""Respuesta que lista los comandos existentes."""
		try:
			import comandos_usuario
			cmds = comandos_usuario.obtener_todos_los_comandos()
			if not cmds:
				return "No hay comandos dinámicos aún. ¿Creamos el primero? 🆕"

			respuesta = f"Tenés {len(cmds)} comandos creados:\n\n"
			for cmd in cmds:
				respuesta += f"✓ {cmd.get('nombre')} ({cmd.get('tipo')})\n"
			respuesta += "\n¿Querés editar alguno o crear uno nuevo?"
			return respuesta
		except Exception as e:
			return f"Error listando comandos: {e}"

	def _respuesta_explicar_sistema(self) -> str:
		"""Respuesta que explica cómo funciona el sistema."""
		return (
			"Claro boludo! 🧠 Así funciona Jarvis:\n\n"
			"1. **Asistente principal**: Escucha por voz, usa IA para entender, ejecuta acciones\n"
			"2. **Comandos core**: 8 comandos Python nativos (música, apps, etc)\n"
			"3. **Comandos dinámicos**: Los que TÚ creas sin tocar código (guardados en JSON)\n"
			"4. **Yo (copiloto)**: Te ayudo a crear/editar comandos via chat\n"
			"5. **Menú 🧩**: También podes crearlos desde la interfaz gráfica\n\n"
			"Todo es en tiempo real - sin necesidad de reiniciar nada 🔥"
		)

	def _respuesta_sugerencia_comando(self, mensaje: str) -> str:
		"""Respuesta que sugiere crear un comando."""
		# Extraer palabras clave
		palabras = mensaje.lower().split()
		app = None
		for palabra in palabras:
			if palabra in ["chrome", "firefox", "edge", "vscode", "slack", "spotify"]:
				app = palabra
				break

		if app:
			return (
				f"Dale! 🎯 Te voy a crear un comando para abrir {app}.\n\n"
				f"Si querés, puedo agregarlo ya mismo. "
				f"¿Qué triggers te gustaría? (ej: 'abrí {app}', '{app}', 'ir a {app}')"
			)
		else:
			return (
				"Entendí que querés un comando para algo.\n\n"
				"¿Me decís qué aplicación/URL querés abrir? "
				"O si es algo más complejo, me lo describís y armamos un comando personalizado."
			)

# Función para integrar en la GUI principal
def crear_panel_copilot(parent_frame) -> PanelCopiloto:
	"""Crea e integra el panel del copiloto."""
	panel = PanelCopiloto(parent_frame)
	return panel

# Exportar
__all__ = ["PanelCopiloto", "crear_panel_copilot"]
