import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
from typing import Optional

from core.config import cargar_config, guardar_config, logger
from core.utils import obtener_ruta_recurso, obtener_ruta_escritura


class SetupWizard:
    PAD = 15
    BG = "#1e1e1e"
    FG = "#ffffff"
    ACCENT = "#00ff00"
    SECONDARY = "#252525"
    ENTRY_BG = "#2d2d2d"
    BTN_GREEN = "#00aa00"
    BTN_BLUE = "#0066cc"
    BTN_GRAY = "#555555"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Jarvis - Configuración Inicial")
        self.root.geometry("620x520")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        self.config = cargar_config()
        self.perfil = self._cargar_perfil()

        self.paso_actual = 0
        self.pasos = [self._screen1, self._screen2, self._screen3]
        self.titulos = ["Bienvenido", "Modelo de IA", "Audio y Voz"]

        self.frame_contenido = tk.Frame(self.root, bg=self.BG)
        self.frame_contenido.pack(fill=tk.BOTH, expand=True, padx=self.PAD, pady=self.PAD)

        self._crear_barra_progreso()
        self._render_paso()

        self.root.protocol("WM_DELETE_WINDOW", self._salir)
        self.root.mainloop()

    def _cargar_perfil(self) -> dict:
        ruta = obtener_ruta_escritura("perfiles/default.json")
        if not os.path.exists(ruta):
            ruta = obtener_ruta_recurso("perfiles/default.json")
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)

    def _guardar_perfil(self):
        ruta = obtener_ruta_escritura("perfiles/default.json")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(self.perfil, f, indent=2, ensure_ascii=False)

    def _crear_barra_progreso(self):
        frame = tk.Frame(self.root, bg=self.SECONDARY, height=40)
        frame.pack(fill=tk.X)
        self.label_paso = tk.Label(frame, text="", font=("Segoe UI", 9, "bold"),
                                    bg=self.SECONDARY, fg=self.ACCENT)
        self.label_paso.pack(side=tk.LEFT, padx=15, pady=8)
        self.progress = ttk.Progressbar(frame, length=200, mode="determinate")
        self.progress.pack(side=tk.RIGHT, padx=15, pady=8)

    def _actualizar_barra(self):
        total = len(self.pasos)
        self.label_paso.config(text=f"Paso {self.paso_actual + 1} de {total}: {self.titulos[self.paso_actual]}")
        self.progress["value"] = ((self.paso_actual + 1) / total) * 100

    def _limpiar_contenido(self):
        for w in self.frame_contenido.winfo_children():
            w.destroy()

    def _render_paso(self):
        self._limpiar_contenido()
        self._actualizar_barra()
        self.pasos[self.paso_actual]()

    # ────────────────────────────── SCREEN 1: Bienvenido ──────────────────────────────

    def _screen1(self):
        tk.Label(self.frame_contenido, text="¡Bienvenido a Jarvis!",
                 font=("Segoe UI", 16, "bold"), bg=self.BG, fg=self.ACCENT).pack(anchor=tk.W, pady=(0, 5))
        tk.Label(self.frame_contenido,
                 text="Soy tu asistente de escritorio local.\n"
                      "Vamos a configurarlo en 3 pasos simples.",
                 font=("Segoe UI", 10), bg=self.BG, fg=self.FG, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))

        tk.Label(self.frame_contenido, text="¿Cómo te llamás?",
                 font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.entry_nombre = tk.Entry(self.frame_contenido, font=("Segoe UI", 11),
                                      bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG)
        self.entry_nombre.pack(fill=tk.X, pady=(5, 20))
        nombre_actual = self.perfil.get("nombre", "")
        if nombre_actual:
            self.entry_nombre.insert(0, nombre_actual)

        tk.Label(self.frame_contenido, text="Idioma del asistente:",
                 font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.var_idioma = tk.StringVar(value=self.config.get("audio", {}).get("idioma", "es"))
        combo_idioma = ttk.Combobox(self.frame_contenido, textvariable=self.var_idioma,
                                      values=["es", "en", "pt"], state="readonly", font=("Segoe UI", 10))
        combo_idioma.pack(fill=tk.X, pady=(5, 20))

        tk.Label(self.frame_contenido, text="Motor de voz (TTS):",
                 font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.var_tts = tk.StringVar(value=self.config.get("tts", {}).get("motor", "powershell"))
        combo_tts = ttk.Combobox(self.frame_contenido, textvariable=self.var_tts,
                                   values=["powershell", "pyttsx3"], state="readonly", font=("Segoe UI", 10))
        combo_tts.pack(fill=tk.X, pady=(5, 20))

        self._botones_navegacion(es_primero=True)

    # ────────────────────────────── SCREEN 2: Modelo IA ──────────────────────────────

    def _screen2(self):
        tk.Label(self.frame_contenido, text="Modelo de Inteligencia Artificial",
                 font=("Segoe UI", 16, "bold"), bg=self.BG, fg=self.ACCENT).pack(anchor=tk.W, pady=(0, 5))
        tk.Label(self.frame_contenido,
                 text="Elegí cómo Jarvis va a procesar tus comandos.\n"
                      "Ollama es local y gratuito. Claude/OpenAI requieren API key.",
                 font=("Segoe UI", 10), bg=self.BG, fg=self.FG, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))

        tk.Label(self.frame_contenido, text="Proveedor de IA:",
                 font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.var_tipo_ia = tk.StringVar(value=self.config["modelo_ia"]["tipo"])
        combo_ia = ttk.Combobox(self.frame_contenido, textvariable=self.var_tipo_ia,
                                  values=["ollama", "claude", "openai"], state="readonly", font=("Segoe UI", 10))
        combo_ia.pack(fill=tk.X, pady=(5, 10))
        combo_ia.bind("<<ComboboxSelected>>", self._toggle_ia_opciones)

        self.frame_ollama = tk.Frame(self.frame_contenido, bg=self.BG)
        tk.Label(self.frame_ollama, text="Modelo Ollama (ej: qwen2.5:3b, llama3.2:1b):",
                 font=("Segoe UI", 9, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.entry_ollama_modelo = tk.Entry(self.frame_ollama, font=("Segoe UI", 10),
                                              bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG)
        self.entry_ollama_modelo.pack(fill=tk.X, pady=(5, 10))
        self.entry_ollama_modelo.insert(0, self.config["modelo_ia"]["opciones"]["ollama"]["modelo"])
        self.btn_verificar = tk.Button(self.frame_ollama, text="Verificar Ollama",
                                        command=self._verificar_ollama,
                                        font=("Segoe UI", 9), bg=self.BTN_BLUE, fg=self.FG,
                                        padx=10, pady=4)
        self.btn_verificar.pack(anchor=tk.W)
        self.label_ollama_status = tk.Label(self.frame_ollama, text="",
                                              font=("Segoe UI", 9), bg=self.BG, fg=self.FG)
        self.label_ollama_status.pack(anchor=tk.W, pady=(5, 0))

        self.frame_cloud = tk.Frame(self.frame_contenido, bg=self.BG)
        tk.Label(self.frame_cloud, text="API Key:",
                 font=("Segoe UI", 9, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.entry_api_key = tk.Entry(self.frame_cloud, font=("Segoe UI", 10),
                                        bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG, show="*")
        self.entry_api_key.pack(fill=tk.X, pady=(5, 10))

        self._toggle_ia_opciones()
        self._botones_navegacion()

    def _toggle_ia_opciones(self, event=None):
        tipo = self.var_tipo_ia.get()
        self.frame_ollama.pack_forget()
        self.frame_cloud.pack_forget()
        if tipo == "ollama":
            self.frame_ollama.pack(fill=tk.X, pady=5)
        else:
            key_actual = self.config["modelo_ia"]["opciones"].get(tipo, {}).get("api_key", "")
            self.entry_api_key.delete(0, tk.END)
            self.entry_api_key.insert(0, key_actual)
            self.frame_cloud.pack(fill=tk.X, pady=5)

    def _verificar_ollama(self):
        def check():
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:11434", timeout=3)
                self.label_ollama_status.config(text="Ollama está funcionando ✅", fg=self.ACCENT)
            except Exception:
                self.label_ollama_status.config(text="Ollama no responde. ¿Está instalado? ❌", fg="#ff4444")
            self.btn_verificar.config(state=tk.NORMAL)
        self.btn_verificar.config(state=tk.DISABLED)
        self.label_ollama_status.config(text="Verificando...")
        threading.Thread(target=check, daemon=True).start()

    # ────────────────────────────── SCREEN 3: Audio y Voz ──────────────────────────────

    def _screen3(self):
        tk.Label(self.frame_contenido, text="Audio y Voz",
                 font=("Segoe UI", 16, "bold"), bg=self.BG, fg=self.ACCENT).pack(anchor=tk.W, pady=(0, 5))
        tk.Label(self.frame_contenido,
                 text="Configurá el micrófono y la voz del asistente.",
                 font=("Segoe UI", 10), bg=self.BG, fg=self.FG, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))

        tk.Label(self.frame_contenido, text="Micrófono:",
                 font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.var_mic = tk.StringVar()
        self.combo_mic = ttk.Combobox(self.frame_contenido, textvariable=self.var_mic,
                                        state="readonly", font=("Segoe UI", 10))
        self.combo_mic.pack(fill=tk.X, pady=(5, 15))
        self._listar_microfonos()

        tk.Label(self.frame_contenido, text="Sensibilidad de activación (0-1):",
                 font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.var_umbral = tk.DoubleVar(value=self.config["wakeword"]["umbral"])
        scale = tk.Scale(self.frame_contenido, from_=0.1, to=0.8, resolution=0.05,
                          orient=tk.HORIZONTAL, variable=self.var_umbral,
                          bg=self.BG, fg=self.FG, highlightbackground=self.BG,
                          troughcolor=self.ENTRY_BG, length=400)
        scale.pack(fill=tk.X, pady=(5, 15))

        tk.Label(self.frame_contenido, text="Voz del asistente:",
                 font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.FG).pack(anchor=tk.W)
        self.var_voz = tk.StringVar(value=self.config.get("tts", {}).get("voz", "Microsoft Helena Desktop"))
        combo_voz = ttk.Combobox(self.frame_contenido, textvariable=self.var_voz,
                                   values=["Microsoft Helena Desktop", "Microsoft Sabina Desktop",
                                           "Microsoft David Desktop", "Microsoft Zira Desktop"],
                                   state="readonly", font=("Segoe UI", 10))
        combo_voz.pack(fill=tk.X, pady=(5, 20))

        self._botones_navegacion(es_ultimo=True)

    def _listar_microfonos(self):
        opciones = ["(Predeterminado del sistema)"]
        dispositivo_actual = self.config.get("audio", {}).get("dispositivo_mic")
        seleccionado = 0
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    label = f"{i}: {dev['name']}"
                    opciones.append(label)
                    if dispositivo_actual is not None and i == dispositivo_actual:
                        seleccionado = len(opciones) - 1
        except Exception:
            pass
        self.combo_mic["values"] = opciones
        self.combo_mic.current(seleccionado)

    # ────────────────────────────── Navegación ──────────────────────────────

    def _limpiar_frame_botones(self):
        for w in self.root.pack_slaves():
            if isinstance(w, tk.Frame) and w != self.frame_contenido:
                pack_info = w.pack_info()
                if pack_info.get("side") == tk.BOTTOM:
                    w.destroy()

    def _botones_navegacion(self, es_primero=False, es_ultimo=False):
        self._limpiar_frame_botones()
        frame = tk.Frame(self.root, bg=self.BG)
        frame.pack(side=tk.BOTTOM, fill=tk.X, padx=self.PAD, pady=self.PAD)

        if not es_primero:
            tk.Button(frame, text="← Anterior", command=self._anterior,
                       font=("Segoe UI", 10), bg=self.BTN_GRAY, fg=self.FG,
                       padx=20, pady=8).pack(side=tk.LEFT, padx=5)

        if es_ultimo:
            tk.Button(frame, text="✅ Finalizar", command=self._finalizar,
                       font=("Segoe UI", 10, "bold"), bg=self.BTN_GREEN, fg=self.FG,
                       padx=20, pady=8).pack(side=tk.RIGHT, padx=5)
        else:
            tk.Button(frame, text="Siguiente →", command=self._siguiente,
                       font=("Segoe UI", 10, "bold"), bg=self.BTN_BLUE, fg=self.FG,
                       padx=20, pady=8).pack(side=tk.RIGHT, padx=5)

        tk.Button(frame, text="Salir", command=self._salir,
                   font=("Segoe UI", 9), bg="#aa0000", fg=self.FG,
                   padx=15, pady=8).pack(side=tk.RIGHT, padx=5)

    def _siguiente(self):
        if self.paso_actual == 0:
            if not self._validar_screen1():
                return
        elif self.paso_actual == 1:
            if not self._validar_screen2():
                return
        self.paso_actual += 1
        self._render_paso()

    def _anterior(self):
        self.paso_actual -= 1
        self._render_paso()

    def _validar_screen1(self) -> bool:
        nombre = self.entry_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Falta el nombre", "Decime tu nombre para poder llamarte.")
            self.entry_nombre.focus()
            return False
        self.perfil["nombre"] = nombre
        self.config["audio"]["idioma"] = self.var_idioma.get()
        self.config["tts"]["motor"] = self.var_tts.get()
        return True

    def _validar_screen2(self) -> bool:
        tipo = self.var_tipo_ia.get()
        self.config["modelo_ia"]["tipo"] = tipo
        if tipo == "ollama":
            modelo = self.entry_ollama_modelo.get().strip()
            if not modelo:
                messagebox.showwarning("Falta el modelo", "Escribí el nombre del modelo Ollama.")
                return False
            self.config["modelo_ia"]["opciones"]["ollama"]["modelo"] = modelo
        else:
            api_key = self.entry_api_key.get().strip()
            if not api_key:
                messagebox.showwarning("Falta API Key",
                                        f"Necesitás una API key para usar {tipo}.\n"
                                        "Configurala ahora o elegí Ollama.")
                return False
            if tipo not in self.config["modelo_ia"]["opciones"]:
                self.config["modelo_ia"]["opciones"][tipo] = {"api_key": "", "modelo": ""}
            self.config["modelo_ia"]["opciones"][tipo]["api_key"] = api_key
        return True

    def _finalizar(self):
        try:
            mic_texto = self.combo_mic.get()
            if mic_texto and mic_texto != "(Predeterminado del sistema)":
                try:
                    self.config["audio"]["dispositivo_mic"] = int(mic_texto.split(":")[0])
                except (ValueError, IndexError):
                    self.config["audio"]["dispositivo_mic"] = None
            else:
                self.config["audio"]["dispositivo_mic"] = None

            self.config["wakeword"]["umbral"] = round(self.var_umbral.get(), 2)
            self.config["tts"]["voz"] = self.var_voz.get()

            self.config["setup_completado"] = True

            guardar_config(self.config)
            self._guardar_perfil()

            messagebox.showinfo("¡Listo!",
                                "Configuración guardada correctamente.\n\n"
                                "Ya podés empezar a usar Jarvis.\n"
                                "Decí: ¡Hey Jarvis!")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración:\n{e}")
            logger.error(f"Error guardando setup: {e}")

    def _salir(self):
        if messagebox.askyesno("Salir", "¿Salir de la configuración inicial?\n"
                                         "Podés ejecutarla después desde el menú."):
            self.root.destroy()
            sys.exit(0)

    def _limpiar_tk(self):
        for attr in ("var_idioma", "var_tts", "var_tipo_ia", "var_umbral", "var_mic", "var_voz"):
            setattr(self, attr, None)


def ejecutar_setup():
    SetupWizard()


if __name__ == "__main__":
    ejecutar_setup()
