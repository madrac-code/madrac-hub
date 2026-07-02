# ────────────────────────────────────────────────────────────────────
# Gestor de Comandos (GUI)
# ────────────────────────────────────────────────────────────────────
# Ventanas y widgets para crear/editar/eliminar comandos dinámicamente.
# Integrable en la interfaz principal de Jarvis.
# ────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import comandos_usuario
import threading

class VentanaGestorComandos:
	"""Ventana principal para gestionar comandos del usuario."""

	def __init__(self, parent=None):
		self.ventana = tk.Toplevel(parent) if parent else tk.Tk()
		self.ventana.title("Gestor de Comandos - Jarvis")
		self.ventana.geometry("900x600")
		self.ventana.configure(bg="#1e1e1e")

		self.comandos_actuales = []
		self._crear_interfaz()
		self._cargar_comandos()

	def _crear_interfaz(self):
		"""Construye la interfaz del gestor."""

		# ─── Panel Superior: Lista de comandos ───
		panel_titulo = tk.Frame(self.ventana, bg="#252525", height=50)
		panel_titulo.pack(fill=tk.X, padx=5, pady=5)

		tk.Label(
			panel_titulo,
			text="📋 MIS COMANDOS",
			font=("Segoe UI", 12, "bold"),
			bg="#252525",
			fg="#00ff00"
		).pack(anchor=tk.W, padx=10, pady=8)

		# ─── Tabla de comandos con scrollbar ───
		panel_tabla = tk.Frame(self.ventana, bg="#1e1e1e")
		panel_tabla.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

		# Crear Treeview
		self.tree_comandos = ttk.Treeview(
			panel_tabla,
			columns=("nombre", "triggers", "tipo", "activo"),
			height=15,
			selectmode='browse'
		)

		# Definir columnas
		self.tree_comandos.column("#0", width=0, stretch=tk.NO)
		self.tree_comandos.column("nombre", anchor=tk.W, width=150)
		self.tree_comandos.column("triggers", anchor=tk.W, width=250)
		self.tree_comandos.column("tipo", anchor=tk.W, width=100)
		self.tree_comandos.column("activo", anchor=tk.CENTER, width=50)

		# Headings
		self.tree_comandos.heading("#0", text="", anchor=tk.W)
		self.tree_comandos.heading("nombre", text="NOMBRE", anchor=tk.W)
		self.tree_comandos.heading("triggers", text="TRIGGERS", anchor=tk.W)
		self.tree_comandos.heading("tipo", text="TIPO", anchor=tk.W)
		self.tree_comandos.heading("activo", text="✓", anchor=tk.CENTER)

		# Estilo oscuro para tabla
		style = ttk.Style()
		style.theme_use('clam')
		style.configure(
			"Treeview",
			background="#2d2d2d",
			foreground="#ffffff",
			fieldbackground="#2d2d2d",
			borderwidth=0
		)
		style.configure(
			"Treeview.Heading",
			background="#404040",
			foreground="#00ff00",
			borderwidth=0
		)
		style.map(
			"Treeview",
			background=[("selected", "#0066cc")]
		)

		# Scrollbar
		scrollbar = ttk.Scrollbar(panel_tabla, orient=tk.VERTICAL, command=self.tree_comandos.yview)
		self.tree_comandos.configure(yscroll=scrollbar.set)

		self.tree_comandos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

		# ─── Panel Botones de Acción ───
		panel_botones = tk.Frame(self.ventana, bg="#1e1e1e")
		panel_botones.pack(fill=tk.X, padx=10, pady=10)

		tk.Button(
			panel_botones,
			text="➕ NUEVO",
			command=self._crear_nuevo,
			font=("Segoe UI", 9, "bold"),
			bg="#00aa00",
			fg="#ffffff",
			padx=15,
			pady=8
		).pack(side=tk.LEFT, padx=5)

		tk.Button(
			panel_botones,
			text="✏️ EDITAR",
			command=self._editar_comando,
			font=("Segoe UI", 9, "bold"),
			bg="#0066cc",
			fg="#ffffff",
			padx=15,
			pady=8
		).pack(side=tk.LEFT, padx=5)

		tk.Button(
			panel_botones,
			text="▶️ EJECUTAR",
			command=self._ejecutar_comando,
			font=("Segoe UI", 9, "bold"),
			bg="#ff9900",
			fg="#ffffff",
			padx=15,
			pady=8
		).pack(side=tk.LEFT, padx=5)

		tk.Button(
			panel_botones,
			text="🗑️ ELIMINAR",
			command=self._eliminar_comando,
			font=("Segoe UI", 9, "bold"),
			bg="#aa0000",
			fg="#ffffff",
			padx=15,
			pady=8
		).pack(side=tk.LEFT, padx=5)

		tk.Button(
			panel_botones,
			text="🔄 RECARGAR",
			command=self._cargar_comandos,
			font=("Segoe UI", 9),
			bg="#555555",
			fg="#ffffff",
			padx=15,
			pady=8
		).pack(side=tk.RIGHT, padx=5)

	def _cargar_comandos(self):
		"""Carga los comandos en la tabla."""
		# Limpiar tabla
		for item in self.tree_comandos.get_children():
			self.tree_comandos.delete(item)

		# Cargar comandos
		try:
			self.comandos_actuales = comandos_usuario.obtener_todos_los_comandos()
			for cmd in self.comandos_actuales:
				triggers_str = ", ".join(cmd.get("triggers", [])[:2])
				if len(cmd.get("triggers", [])) > 2:
					triggers_str += "..."

				activo = "✓" if cmd.get("activo", True) else "✗"

				self.tree_comandos.insert(
					"",
					"end",
					values=(
						cmd.get("nombre"),
						triggers_str,
						cmd.get("tipo"),
						activo
					),
					tags=(cmd.get("id"),)
				)
		except Exception as e:
			messagebox.showerror("Error", f"Error cargando comandos: {e}")

	def _crear_nuevo(self):
		"""Abre diálogo para crear nuevo comando."""
		ventana_edicion = VentanaEditarComando(self.ventana, callback=self._cargar_comandos)
		self.ventana.wait_window(ventana_edicion.ventana)

	def _editar_comando(self):
		"""Abre diálogo para editar comando seleccionado."""
		selection = self.tree_comandos.selection()
		if not selection:
			messagebox.showwarning("Advertencia", "Selecciona un comando para editar")
			return

		# Obtener ID del comando
		cmd_id = self.tree_comandos.item(selection[0])["tags"][0]
		cmd = comandos_usuario.obtener_comando_por_id(cmd_id)

		if cmd:
			ventana_edicion = VentanaEditarComando(
				self.ventana, 
				comando=cmd, 
				callback=self._cargar_comandos
			)
			self.ventana.wait_window(ventana_edicion.ventana)

	def _ejecutar_comando(self):
		"""Ejecuta el comando seleccionado."""
		selection = self.tree_comandos.selection()
		if not selection:
			messagebox.showwarning("Advertencia", "Selecciona un comando para ejecutar")
			return

		# Obtener ID del comando
		cmd_id = self.tree_comandos.item(selection[0])["tags"][0]
		cmd = comandos_usuario.obtener_comando_por_id(cmd_id)

		if cmd:
			# Ejecutar en thread para no bloquear GUI
			def ejecutar():
				exito, msg = comandos_usuario.ejecutar_comando(cmd)
				estado = "✓" if exito else "✗"
				messagebox.showinfo("Resultado", f"{estado} {msg}")

			thread = threading.Thread(target=ejecutar, daemon=True)
			thread.start()

	def _eliminar_comando(self):
		"""Elimina el comando seleccionado."""
		selection = self.tree_comandos.selection()
		if not selection:
			messagebox.showwarning("Advertencia", "Selecciona un comando para eliminar")
			return

		# Obtener ID y nombre del comando
		cmd_id = self.tree_comandos.item(selection[0])["tags"][0]
		cmd = comandos_usuario.obtener_comando_por_id(cmd_id)

		if cmd:
			confirmar = messagebox.askyesno(
				"Confirmar eliminación",
				f"¿Eliminar '{cmd.get('nombre')}'?"
			)
			if confirmar:
				exito, msg = comandos_usuario.eliminar_comando(cmd_id)
				if exito:
					messagebox.showinfo("Éxito", msg)
					self._cargar_comandos()
				else:
					messagebox.showerror("Error", msg)

class VentanaEditarComando:
	"""Ventana de edición/creación de comandos."""

	def __init__(self, parent, comando=None, callback=None):
		self.ventana = tk.Toplevel(parent)
		self.ventana.title("Crear Comando" if not comando else f"Editar: {comando.get('nombre')}")
		self.ventana.geometry("500x500")
		self.ventana.configure(bg="#1e1e1e")

		self.comando = comando
		self.callback = callback
		self.cmd_id = comando.get("id") if comando else None

		self._crear_interfaz()
		if comando:
			self._llenar_campos()

	def _crear_interfaz(self):
		"""Construye la interfaz de edición."""

		# Marcos con padding
		marco = tk.Frame(self.ventana, bg="#1e1e1e")
		marco.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

		# ─── Nombre ───
		tk.Label(marco, text="Nombre del Comando:", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff").pack(anchor=tk.W, pady=(0, 5))
		self.entry_nombre = tk.Entry(marco, font=("Segoe UI", 10), bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff")
		self.entry_nombre.pack(fill=tk.X, pady=(0, 15))

		# ─── Triggers ───
		tk.Label(marco, text="Triggers (separados por comas):", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff").pack(anchor=tk.W, pady=(0, 5))
		self.entry_triggers = tk.Entry(marco, font=("Segoe UI", 10), bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff")
		self.entry_triggers.pack(fill=tk.X, pady=(0, 15))

		# ─── Tipo ───
		tk.Label(marco, text="Tipo de Comando:", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff").pack(anchor=tk.W, pady=(0, 5))
		self.var_tipo = tk.StringVar()
		self.combo_tipo = ttk.Combobox(
			marco,
			textvariable=self.var_tipo,
			values=["abrir_url", "abrir_app", "escribir", "secuencia", "hablar"],
			state="readonly",
			font=("Segoe UI", 10)
		)
		self.combo_tipo.pack(fill=tk.X, pady=(0, 15))
		self.combo_tipo.bind("<<ComboboxSelected>>", self._actualizar_parametro_label)

		# ─── Parámetro ───
		self.label_parametro = tk.Label(marco, text="Parámetro:", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff")
		self.label_parametro.pack(anchor=tk.W, pady=(0, 5))
		self.entry_parametro = tk.Entry(marco, font=("Segoe UI", 10), bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff")
		self.entry_parametro.pack(fill=tk.X, pady=(0, 15))

		# ─── Descripción ───
		tk.Label(marco, text="Descripción:", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff").pack(anchor=tk.W, pady=(0, 5))
		self.text_descripcion = tk.Text(marco, font=("Segoe UI", 9), bg="#2d2d2d", fg="#ffffff", height=4, insertbackground="#ffffff")
		self.text_descripcion.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

		# ─── Botones ───
		panel_botones = tk.Frame(marco, bg="#1e1e1e")
		panel_botones.pack(fill=tk.X)

		tk.Button(
			panel_botones,
			text="💾 GUARDAR",
			command=self._guardar,
			font=("Segoe UI", 9, "bold"),
			bg="#00aa00",
			fg="#ffffff",
			padx=20,
			pady=8
		).pack(side=tk.LEFT, padx=5)

		tk.Button(
			panel_botones,
			text="❌ CANCELAR",
			command=self.ventana.destroy,
			font=("Segoe UI", 9),
			bg="#555555",
			fg="#ffffff",
			padx=20,
			pady=8
		).pack(side=tk.RIGHT, padx=5)

	def _actualizar_parametro_label(self, event=None):
		"""Actualiza el label de parámetro según el tipo seleccionado."""
		tipo = self.var_tipo.get()
		labels = {
			"abrir_url": "URL:",
			"abrir_app": "Nombre de aplicación:",
			"escribir": "Texto a escribir:",
			"secuencia": "Comandos (separados por comas):",
			"hablar": "Texto a decir:"
		}
		self.label_parametro.config(text=labels.get(tipo, "Parámetro:"))

	def _llenar_campos(self):
		"""Llena los campos con datos del comando existente."""
		self.entry_nombre.insert(0, self.comando.get("nombre", ""))
		self.entry_triggers.insert(0, ", ".join(self.comando.get("triggers", [])))
		self.var_tipo.set(self.comando.get("tipo", ""))
		self.entry_parametro.insert(0, self.comando.get("parametro", ""))
		self.text_descripcion.insert(tk.END, self.comando.get("descripcion", ""))
		self._actualizar_parametro_label()

	def _guardar(self):
		"""Guarda el comando."""
		nombre = self.entry_nombre.get().strip()
		triggers_str = self.entry_triggers.get().strip()
		tipo = self.var_tipo.get()
		parametro = self.entry_parametro.get().strip()
		descripcion = self.text_descripcion.get("1.0", tk.END).strip()

		# Validar
		if not nombre or not triggers_str or not tipo:
			messagebox.showerror("Error", "Nombre, triggers y tipo son requeridos")
			return

		triggers = [t.strip() for t in triggers_str.split(",")]

		try:
			if self.cmd_id:
				# Editar
				exito, msg = comandos_usuario.editar_comando(
					self.cmd_id,
					nombre=nombre,
					triggers=triggers,
					tipo=tipo,
					parametro=parametro,
					descripcion=descripcion
				)
			else:
				# Crear
				exito, msg, cmd_id = comandos_usuario.crear_comando(
					nombre, triggers, tipo, parametro, descripcion
				)

			if exito:
				messagebox.showinfo("Éxito", msg)
				if self.callback:
					self.callback()
				self.ventana.destroy()
			else:
				messagebox.showerror("Error", msg)
		except Exception as e:
			messagebox.showerror("Error", f"Error al guardar: {e}")

# Función para integrar en la GUI principal
def abrir_gestor_comandos(root_principal=None):
	"""Abre la ventana del gestor de comandos."""
	gestor = VentanaGestorComandos(root_principal)
	return gestor

# Exportar
__all__ = ["VentanaGestorComandos", "VentanaEditarComando", "abrir_gestor_comandos"]
