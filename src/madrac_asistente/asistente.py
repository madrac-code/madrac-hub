# ────────────────────────────────────────────────────────────────────
# JARVIS - Asistente de Escritorio Local en Windows
# ────────────────────────────────────────────────────────────────────
# Loop principal del asistente. Orquesta el flujo completo.
# ────────────────────────────────────────────────────────────────────

import sys
import os
import time
import atexit
import subprocess
import urllib.request
import urllib.error
import threading
from core import (
    cargar_config,
    cargar_perfil,
    guardar_config,
    guardar_perfil,
    configurar_logging,
    logger,
    grabar_audio,
    esperar_wakeword,
    transcribir,
    hablar,
    consultar_ia,
    ejecutar_accion,
    detectar_intencion_basica
)
from historial import HistorialConversacion
from gui import crear_gui

historial = HistorialConversacion(max_tamano=10)
_proceso_ollama = None


def _ollama_responde() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=2)
        return True
    except Exception:
        return False


def _iniciar_ollama():
    global _proceso_ollama
    if _ollama_responde():
        logger.info("Ollama ya está corriendo")
        return

    logger.info("Iniciando Ollama...")
    try:
        _proceso_ollama = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(30):
            if _ollama_responde():
                logger.info("Ollama iniciado correctamente")
                return
            time.sleep(0.5)
        logger.warning("Ollama no respondió después de 15 segundos")
    except FileNotFoundError:
        logger.error("Ollama no encontrado. Instalalo en https://ollama.com")


def _detener_ollama():
    global _proceso_ollama
    if _proceso_ollama:
        logger.info("Deteniendo Ollama...")
        _proceso_ollama.terminate()
        try:
            _proceso_ollama.wait(timeout=5)
        except Exception:
            _proceso_ollama.kill()
        _proceso_ollama = None

def inicializar_sistema():
    """Inicializa todos los componentes del asistente."""
    logger.info("=" * 70)
    logger.info("INICIANDO JARVIS")
    logger.info("=" * 70)
    try:
        config = cargar_config()
        perfil = cargar_perfil()
        logger.info(f"Configuración cargada: {config['modelo_ia']['tipo']}")
        return True
    except Exception as e:
        logger.error(f"Error inicializando sistema: {e}")
        return False

def loop_principal(gui=None):
    """Loop principal del asistente."""
    global historial

    hablar("Asistente iniciado. Decí hey Jarvis para activarme.")
    if gui:
        gui.actualizar_estado("Escuchando...")
        gui.agregar_log("Sistema listo. Esperando palabra clave...")

    logger.info("Sistema listo. Esperando wakeword...")

    while True:
        try:
            if gui and not gui.activo:
                continue

            if gui:
                gui.actualizar_estado("Esperando wakeword...")

            esperar_wakeword()

            logger.info("Palabra clave detectada!")
            if gui:
                gui.actualizar_estado("Palabra clave detectada")
                gui.agregar_log("Palabra clave detectada")

            hablar("Si?")

            if gui:
                gui.actualizar_estado("Grabando comando...")

            config = cargar_config()
            audio_cmd = grabar_audio(segundos=config["audio"]["duracion_grabacion"])

            if gui:
                gui.actualizar_estado("Transcribiendo...")

            comando = transcribir(audio_cmd)

            if gui:
                gui.actualizar_comando(comando)
                gui.agregar_log(f"Transcripcion: '{comando}'")

            if comando:
                if gui:
                    gui.actualizar_estado("Procesando...")

                accion, parametro, es_comando = consultar_ia(comando, historial)
                logger.info(f"Accion: {accion} | Parametro: {parametro}")

                # Limpiar historial después de comandos (no conversación)
                if es_comando:
                    logger.info("Comando ejecutado - limpiando historial")
                    historial.limpiar()

                if gui:
                    gui.actualizar_estado("Ejecutando...")

                exito, mensaje = ejecutar_accion(accion, parametro)

                if gui:
                    gui.actualizar_respuesta(mensaje)
                    gui.agregar_log(f"Respuesta: {mensaje}")

                if gui:
                    gui.actualizar_estado("Hablando...")

                hablar(mensaje)
            else:
                hablar("No entendí nada, intentá de nuevo.")

            if gui:
                gui.actualizar_estado("Escuchando...")

        except KeyboardInterrupt:
            logger.info("Asistente interrumpido por usuario")
            if gui:
                gui.agregar_log("Asistente detenido")
            hablar("Adiós!")
            _detener_ollama()
            break

        except Exception as e:
            logger.error(f"Error en loop principal: {e}", exc_info=True)
            if gui:
                gui.agregar_log(f"Error: {e}")
            hablar("Ocurrió un error. Intentá de nuevo.")

def main():
    """Función principal."""
    configurar_logging()
    _iniciar_ollama()
    atexit.register(_detener_ollama)

    if not inicializar_sistema():
        logger.error("No se pudo inicializar el sistema")
        sys.exit(1)

    config = cargar_config()
    if not config.get("setup_completado", False):
        logger.info("Primera ejecución - lanzando asistente de configuración...")
        from ui.setup_wizard import ejecutar_setup
        ejecutar_setup()
        config = cargar_config()

    if config["interfaz"]["mostrar_gui"]:
        gui, root = crear_gui()
        thread_asistente = threading.Thread(target=loop_principal, args=(gui,), daemon=True)
        thread_asistente.start()
        gui.mostrar()
    else:
        loop_principal(gui=None)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        print(f"Error fatal: {e}", file=sys.stderr)
        sys.exit(1)
