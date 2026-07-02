# ────────────────────────────────────────────────────────────────────
# Ventana Principal de la Interfaz de Usuario
# ────────────────────────────────────────────────────────────────────
# Ventana principal de la interfaz de usuario del asistente JARVIS.
# Contiene el panel de monitorización y el panel de copiloto IA.
# ────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, scrolledtext
import json
from datetime import datetime
from core import cargar_config
from core.utils import obtener_ruta_recurso

class InterfazJarvis:
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente JARVIS")
        self.root.geometry("900x650")
        self.root.configure(bg="#1e1e1e")
        self.estado_actual = "Iniciando..."
        self.ultimo_comando = ""
        self.ultima_respuesta = ""
        self.activo = True
        with open(obtener_ruta_recurso("config.json"), "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self._crear_interfaz()

    def _crear_interfaz(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        frame_monitor = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(frame_monitor, text="Monitor")
        self._crear_monitor(frame_monitor)
        frame_copiloto = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(frame_copiloto, text="Copiloto")
        self._crear_copiloto(frame_copiloto)

    def _crear_monitor(self, pf):
        pe = tk.Frame(pf, bg="#252525", height=80)
        pe.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(pe, text="Estado:", font=("Segoe UI", 10, "bold"), bg="#252525", fg="#ffffff").pack(anchor=tk.W, padx=10, pady=5)
        self.label_estado = tk.Label(pe, text=self.estado_actual, font=("Segoe UI", 12, "bold"), bg="#252525", fg="#00ff00")
        self.label_estado.pack(anchor=tk.W, padx=20)
        pc = tk.Frame(pf, bg="#1e1e1e")
        pc.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(pc, text="Ultimo Comando:", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff").pack(anchor=tk.W)
        self.label_comando = tk.Label(pc, text="", font=("Segoe UI", 9), bg="#1e1e1e", fg="#cccccc", wraplength=850, justify=tk.LEFT)
        self.label_comando.pack(anchor=tk.W, padx=10)
        pr = tk.Frame(pf, bg="#1e1e1e")
        pr.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(pr, text="Ultima Respuesta:", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff").pack(anchor=tk.W)
        self.label_respuesta = tk.Label(pr, text="", font=("Segoe UI", 9), bg="#1e1e1e", fg="#90ee90", wraplength=850, justify=tk.LEFT)
        self.label_respuesta.pack(anchor=tk.W, padx=10)
        pl = tk.Frame(pf, bg="#1e1e1e")
        pl.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        tk.Label(pl, text="Log de Actividad:", font=("Segoe UI", 9, "bold"), bg="#1e1e1e", fg="#ffffff").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(pl, height=10, font=("Consolas", 8), bg="#2d2d2d", fg="#00ff00", insertbackground="#00ff00")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        pb = tk.Frame(pf, bg="#1e1e1e")
        pb.pack(fill=tk.X, padx=10, pady=5)
        self.btn_activar = tk.Button(pb, text="Desactivar", command=self.toggle_activo, font=("Segoe UI", 9), bg="#00aa00", fg="#ffffff", padx=15, pady=5)
        self.btn_activar.pack(side=tk.LEFT, padx=5)
        tk.Button(pb, text="Comandos", command=self.abrir_gestor, font=("Segoe UI", 9), bg="#9900cc", fg="#ffffff", padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(pb, text="Limpiar Log", command=self.limpiar_log, font=("Segoe UI", 9), bg="#555555", fg="#ffffff", padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(pb, text="Cerrar", command=self.root.quit, font=("Segoe UI", 9), bg="#aa0000", fg="#ffffff", padx=15, pady=5).pack(side=tk.RIGHT, padx=5)

    def _crear_copiloto(self, pf):
        from ui.copilot import crear_panel_copilot
        self.panel_copilot = crear_panel_copilot(pf)

    def actualizar_estado(self, s): self.estado_actual = s; self.label_estado.config(text=s); self.root.update()
    def actualizar_comando(self, c): self.ultimo_comando = c; self.label_comando.config(text=c if c else "(ninguno)"); self.root.update()
    def actualizar_respuesta(self, r): self.ultima_respuesta = r; self.label_respuesta.config(text=r if r else "(ninguna)"); self.root.update()
    def agregar_log(self, m): ts = datetime.now().strftime("%H:%M:%S"); self.log_text.insert(tk.END, f"[{ts}] {m}\n"); self.log_text.see(tk.END); self.root.update()
    def limpiar_log(self): self.log_text.delete(1.0, tk.END)
    def toggle_activo(self): self.activo = not self.activo; self.btn_activar.config(text="Desactivar" if self.activo else "Activar", bg="#00aa00" if self.activo else "#555555"); self.actualizar_estado("Escuchando..." if self.activo else "Desactivado")
    def abrir_gestor(self):
        from ui.commands import abrir_gestor_comandos
        abrir_gestor_comandos(self.root)
    def mostrar(self): self.root.mainloop()

__all__ = ["InterfazJarvis", "crear_gui"]

# Función para integrar en la GUI principal
def crear_gui():
    root = tk.Tk()
    gui = InterfazJarvis(root)
    return gui, root
