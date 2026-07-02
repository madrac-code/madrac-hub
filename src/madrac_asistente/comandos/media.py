import time
import keyboard as kb

TRIGGERS = ["pausa", "pausar", "play", "pasar", "seguir", "siguiente",
            "anterior", "volver", "music", "música", "pestania", "pestaña",
            "cerrar pestania", "cerrar pestaña", "cerra esa pestaña"]

def play_pause():
    kb.press_and_release('play/pause')
    return True, "Play/Pause"

def siguiente():
    kb.press_and_release('next track')
    return True, "Siguiente canción"

def anterior():
    kb.press_and_release('previous track')
    return True, "Canción anterior"

def cerrar_pestania():
    time.sleep(0.3)
    kb.press_and_release('ctrl+w')
    return True, "Pestaña cerrada"

def ejecutar(parametro):
    p = parametro.lower().strip()

    if not p:
        return play_pause()

    if any(w in p for w in ["pausa", "pausar", "stop", "seguir", "play"]):
        return play_pause()
    elif any(w in p for w in ["siguiente", "pasar", "proximo", "próximo"]):
        return siguiente()
    elif any(w in p for w in ["anterior", "volver", "volvé", "atras"]):
        return anterior()
    elif any(w in p for w in ["pestaña", "pestania", "ventana"]):
        return cerrar_pestania()
    else:
        return play_pause()

__all__ = ["play_pause", "siguiente", "anterior", "cerrar_pestania", "ejecutar", "TRIGGERS"]
