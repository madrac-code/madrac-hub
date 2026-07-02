# ────────────────────────────────────────────────────────────────────
# Comando: Sistema
# ────────────────────────────────────────────────────────────────────
# Controla funciones del sistema: volumen, hora, fecha, apagado,
# captura de pantalla y análisis visual.
# ────────────────────────────────────────────────────────────────────

import subprocess
import json
from datetime import datetime
import os

TRIGGERS = ["volumen", "hora", "fecha", "apagar", "restart", "reiniciar", "screenshot", 
            "pantalla", "describir", "imagen", "captura"]

def cargar_config():
    """Carga la configuración del usuario."""
    from core import cargar_config as _cargar_config
    return _cargar_config()

def obtener_hora():
    """Retorna la hora actual formateada."""
    ahora = datetime.now()
    hora_str = ahora.strftime("%H:%M")
    return True, f"Son las {hora_str}."

def obtener_fecha():
    """Retorna la fecha actual en español."""
    ahora = datetime.now()
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", 
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    dia_semana = dias[ahora.weekday()]
    dia = ahora.day
    mes = meses[ahora.month - 1]
    anio = ahora.year

    fecha_str = f"{dia_semana.capitalize()} {dia} de {mes} de {anio}"
    return True, f"Hoy es {fecha_str}."

def _volumen_pycaw(accion, valor=None):
    from pycaw.pycaw import AudioUtilities
    devices = AudioUtilities.GetSpeakers()
    volume = devices.EndpointVolume

    if accion == "obtener":
        current = int(volume.GetMasterVolumeLevelScalar() * 100)
        mute = volume.GetMute()
        estado = "silenciado" if mute else f"al {current}%"
        return True, f"Volumen {estado}."
    elif accion == "subir":
        v = min(1.0, volume.GetMasterVolumeLevelScalar() + 0.1)
        volume.SetMasterVolumeLevelScalar(v, None)
        volume.SetMute(0, None)
        return True, f"Volumen al {int(v * 100)}%."
    elif accion == "bajar":
        v = max(0.0, volume.GetMasterVolumeLevelScalar() - 0.1)
        volume.SetMasterVolumeLevelScalar(v, None)
        return True, f"Volumen al {int(v * 100)}%."
    elif accion == "silencio":
        volume.SetMute(1, None)
        return True, "Sistema en silencio."
    elif accion == "sonido":
        volume.SetMute(0, None)
        return True, "Sonido activado."
    elif accion == "establecer":
        try:
            v = max(0, min(100, int(valor))) / 100.0
            volume.SetMasterVolumeLevelScalar(v, None)
            volume.SetMute(0, None)
            return True, f"Volumen al {int(v * 100)}%."
        except (ValueError, TypeError):
            return False, "Decí un número del 0 al 100."
    return False, "Acción no reconocida."

def _volumen_nircmd(accion, valor=None):
    try:
        if accion == "subir":
            subprocess.run(["nircmd", "changesysvolume", "5000"], capture_output=True)
            return True, "Subí el volumen."
        elif accion == "bajar":
            subprocess.run(["nircmd", "changesysvolume", "-5000"], capture_output=True)
            return True, "Bajé el volumen."
        elif accion == "silencio":
            subprocess.run(["nircmd", "mutesysvolume", "1"], capture_output=True)
            return True, "Sistema en silencio."
        elif accion == "sonido":
            subprocess.run(["nircmd", "mutesysvolume", "0"], capture_output=True)
            return True, "Sonido activado."
        else:
            return False, "Acción de volumen no reconocida."
    except FileNotFoundError:
        return False, "nircmd no está instalado."
    except Exception as e:
        return False, f"Error: {str(e)}"

def controlar_volumen(accion, valor=None):
    try:
        return _volumen_pycaw(accion, valor)
    except Exception:
        return _volumen_nircmd(accion, valor)

def apagar_sistema(modo="apagar"):
    """
    Apaga, reinicia o hiberna el sistema.

    Args:
        modo (str): "apagar", "reiniciar", "hibernar"

    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    comandos = {
        "apagar": "shutdown /s /t 30 /c 'Apagando en 30 segundos'",
        "reiniciar": "shutdown /r /t 30 /c 'Reiniciando en 30 segundos'",
        "hibernar": "shutdown /h"
    }

    if modo not in comandos:
        return False, "Modo de apagado no reconocido."

    try:
        subprocess.run(comandos[modo], shell=True)
        return True, f"Sistema {modo}ndose en 30 segundos. Escribí 'shutdown /a' en CMD para cancelar."
    except Exception as e:
        return False, f"Error al {modo}: {str(e)}"

def ejecutar(parametro):
    """
    Ejecuta comandos del sistema basado en parámetros.

    Args:
        parametro (str): comando específico como "hora", "fecha", "volumen subir"

    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    parametro = parametro.lower().strip()

    if not parametro:
        return False, "Especificá qué comando de sistema querés ejecutar."

    # Detectar comando
    if "hora" in parametro:
        return obtener_hora()
    elif "fecha" in parametro:
        return obtener_fecha()
    elif "volumen" in parametro or "sonido" in parametro:
        import re
        if "subir" in parametro or "más" in parametro or "alto" in parametro:
            return controlar_volumen("subir")
        elif "bajar" in parametro or "menos" in parametro or "bajo" in parametro:
            return controlar_volumen("bajar")
        elif "mudo" in parametro or "silencio" in parametro or "mutear" in parametro:
            return controlar_volumen("silencio")
        elif "activa" in parametro or "saca" in parametro or "quita" in parametro:
            return controlar_volumen("sonido")
        else:
            m = re.search(r'(\d+)', parametro)
            if m:
                return controlar_volumen("establecer", m.group(1))
            return controlar_volumen("obtener")
    elif "apagar" in parametro:
        return apagar_sistema("apagar")
    elif "reiniciar" in parametro or "restart" in parametro:
        return apagar_sistema("reiniciar")
    elif "hibernar" in parametro:
        return apagar_sistema("hibernar")
    else:
        return False, "Comando de sistema no reconocido."

# Funciones auxiliares expuestas
__all__ = ["obtener_hora", "obtener_fecha", "controlar_volumen", "apagar_sistema", 
           "ejecutar", "TRIGGERS"]
