# ────────────────────────────────────────────────────────────────────
# Acciones
# ────────────────────────────────────────────────────────────────────
# Funciones para ejecutar acciones decididas por la IA.
# ────────────────────────────────────────────────────────────────────

from typing import Tuple

from .config import logger


def ejecutar_accion(accion: str, parametro: str) -> Tuple[bool, str]:
    """
    Ejecuta la acción decidida por el IA.

    Primero busca en comandos del usuario (dinámicos).
    Si no existe, fallback a comandos core (Python).

    Args:
        accion (str): nombre de la acción
        parametro (str): parámetro para la acción

    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    logger.info(f"Ejecutando acción: {accion} con parámetro: {parametro}")

    try:
        # ─── FASE 1: Buscar en comandos dinámicos del usuario ───
        import comandos_usuario
        cmd = comandos_usuario.buscar_comando_por_trigger(accion)
        if cmd:
            logger.info(f"Comando dinámico encontrado: {cmd['nombre']}")
            return comandos_usuario.ejecutar_comando(cmd)

        # ─── FASE 2: Fallback a comandos core ───
        if accion == "reproducir_musica":
            from comandos import musica
            return musica.ejecutar(parametro)

        elif accion == "detener_musica":
            from comandos import musica
            return musica.detener_musica()

        elif accion == "abrir_app":
            from comandos import apps
            return apps.abrir_app(parametro)

        elif accion == "cerrar_ventana":
            from comandos import apps
            return apps.cerrar_app(parametro)

        elif accion == "obtener_hora":
            from comandos import sistema
            return sistema.obtener_hora()

        elif accion == "obtener_fecha":
            from comandos import sistema
            return sistema.obtener_fecha()

        elif accion == "escribir":
            from comandos import escribir
            return escribir.ejecutar(parametro)

        elif accion == "youtube":
            from comandos import youtube
            return youtube.ejecutar(parametro)

        elif accion == "play_pause":
            from comandos import media
            return media.play_pause()

        elif accion == "siguiente_cancion":
            from comandos import media
            return media.siguiente()

        elif accion == "anterior_cancion":
            from comandos import media
            return media.anterior()

        elif accion == "cerrar_pestania":
            from comandos import media
            return media.cerrar_pestania()

        elif accion == "subir_volumen":
            from comandos import sistema
            return sistema.controlar_volumen("subir")

        elif accion == "bajar_volumen":
            from comandos import sistema
            return sistema.controlar_volumen("bajar")

        elif accion == "silenciar":
            from comandos import sistema
            return sistema.controlar_volumen("silencio")

        elif accion == "establecer_volumen":
            from comandos import sistema
            return sistema.controlar_volumen("establecer", parametro)

        elif accion == "conversar":
            from comandos import conversar
            return conversar.ejecutar(parametro)

        else:
            logger.warning(f"Acción desconocida: {accion}")
            return False, f"No sé cómo ejecutar la acción '{accion}'."

    except Exception as e:
        logger.error(f"Error ejecutando acción {accion}: {e}")
        return False, f"Error al ejecutar {accion}: {str(e)}"

__all__ = [
    "ejecutar_accion"
]
