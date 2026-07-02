# ────────────────────────────────────────────────────────────────────
# IA
# ────────────────────────────────────────────────────────────────────
# Funciones para interacción con IA, detección de intenciones y consulta a modelos.
# ────────────────────────────────────────────────────────────────────

import json
from typing import Tuple, Optional

from .config import cargar_config, logger
from .historial import HistorialConversacion


def normalizar(texto: str) -> str:
    """
    Normaliza texto para detección de intenciones.

    Args:
        texto: texto a normalizar

    Returns:
        str: texto normalizado (minusculas, sin acentos, sin espacios extra)
    """
    import unicodedata

    # Convertir a minusculas
    texto = texto.lower()

    # Eliminar acentos
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('ascii')

    # Normalizar espacios
    texto = ' '.join(texto.split())

    return texto


def _distancia_edicion(s1: str, s2: str) -> int:
    """Distancia Levenshtein entre dos strings."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    anterior = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        actual = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            actual.append(min(actual[j] + 1, anterior[j + 1] + 1, anterior[j] + cost))
        anterior = actual
    return anterior[-1]


def detectar_intencion_basica(comando: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Detecta intenciones básicas en el texto del usuario ANTES de llamar a Ollama.

    Args:
        comando: texto transcrito del usuario

    Returns:
        tuple: (accion, parametro, es_comando)
        Retorna (None, None, False) si no hay coincidencia, sino la acción detectada.
    """
    import unicodedata

    if not comando:
        return None, None, False

    # Normalizar el comando
    texto_normalizado = normalizar(comando)

    # Crear lista de palabras una vez para todas las verificaciones
    palabras_texto = texto_normalizado.split()

    # ─── Correccion fonetica para verbos de control con palabras de musica ───
    PALABRAS_MUSICA = {"musica", "reproductor", "cancion", "tema",
                       "playlist", "genero", "artista", "album", "canciones"}
    VERBOS_CONTROL = {
        "cerrar": "cerrar", "detener": "detener", "pausa": "pausa",
        "pausar": "pausa", "reanudar": "reanudar", "reproducir": "reproducir",
    }
    if any(p in palabras_texto for p in PALABRAS_MUSICA):
        for i, palabra in enumerate(palabras_texto):
            if palabra in VERBOS_CONTROL:
                palabras_texto[i] = VERBOS_CONTROL[palabra]
                continue
            if palabra in PALABRAS_MUSICA:
                continue
            for verbo, canonical in VERBOS_CONTROL.items():
                if _distancia_edicion(palabra, verbo) <= 2:
                    palabras_texto[i] = canonical
                    logger.debug("Intencion basica: correccion fonetica '%s' -> '%s' sobre musica", palabra, canonical)
                    break

    # Mapeo de palabras clave a acciones (palabras exactas)
    # Prioridad alta: palabras clave exactas
    palabras_clave_contenido = [
        # Múltiples formas de decir lo mismo
        ("reproducir", "reproducir_musica", ""),
        ("poner", "reproducir_musica", ""),
        ("pon", "reproducir_musica", ""),  # Elisión común en español
        ("pone", "reproducir_musica", ""),
        ("silenciar", "silenciar", ""),
        ("subir", "subir_volumen", ""),
        ("bajar", "bajar_volumen", ""),
        ("volumen", "subir_volumen", ""),  # Predeterminado: subir volumen
        ("volumen", "bajar_volumen", ""),  # Podría ser bajar volumen
        ("qué", "obtener_hora", ""),
        ("que", "obtener_hora", ""),
        ("hora", "obtener_hora", ""),
        ("qué", "obtener_fecha", ""),
        ("que", "obtener_fecha", ""),
        ("fecha", "obtener_fecha", ""),
        # Control de reproduccion
        ("pausa", "play_pause", ""),
        ("pause", "play_pause", ""),
        ("pausar", "play_pause", ""),
        ("reanudar", "play_pause", ""),
        # Cierre
        ("cerrar", "cerrar_ventana", ""),
    ]

    # Intentar coincidencia de palabras clave primero (contenido de palabras exactas en cualquier orden)
    # Para intenciones que pueden expresarse con diferentes palabras
    for palabra_clave, accion, parametro in palabras_clave_contenido:
        if palabra_clave in palabras_texto:
            # Extraer parametro dinamicamente para cerrar: tomar palabras despues de "cerrar"
            if palabra_clave == "cerrar":
                idx = palabras_texto.index("cerrar")
                resto = palabras_texto[idx+1:]
                # "cerrar musica/reproductor/cancion" -> detener_musica
                if resto and resto[0] in ("musica", "reproductor", "cancion"):
                    return "detener_musica", "", True
                parametro = " ".join(resto) if resto else ""
            logger.info("Intencion basica detectada (coincidencia de palabra clave): %s en '%s' -> %s", palabra_clave, texto_normalizado, accion)
            return accion, parametro, True

    # Mapeo de prefijos a acciones (palabras exactas)
    # Cada entrada: (prefijo_detectado, accion, parametro)
    # El prefijo_detectado puede ser palabra completa o inicio
    patrones_intencion = [
        # Navegadores
        ("abrir youtube", "youtube", ""),
        ("abrir chrome", "abrir_app", "chrome"),
        ("abrir brave", "abrir_app", "brave"),
        ("abrir navegador", "abrir_app", "iexplore"),

        # Control de ventanas y música
        ("cerrar ventana", "cerrar_ventana", ""),
        ("cerrar música", "cerrar_ventana", "música"),
        ("cerrar pestania", "cerrar_pestania", ""),

        # Detener musica
        ("detener musica", "detener_musica", ""),
        ("detener reproductor", "detener_musica", ""),
        ("detener cancion", "detener_musica", ""),
        # Variantes fonéticas (Whisper segmenta "detener" como "de tener")
        ("de tener musica", "detener_musica", ""),
        ("de tener reproductor", "detener_musica", ""),
        ("de tener cancion", "detener_musica", ""),
        # Variantes fonéticas (Whisper distorsiona "cerrar" como "cera"/"sera")
        ("cera musica", "detener_musica", ""),
        ("sera musica", "detener_musica", ""),
        # Música
        ("poner música", "reproducir_musica", ""),
        ("reproducir música", "reproducir_musica", ""),

        # Volumen
        ("subir volumen", "subir_volumen", ""),
        ("bajar volumen", "bajar_volumen", ""),
        ("silenciar", "silenciar", ""),

        # Fecha y hora
        ("hora", "obtener_hora", ""),
        ("fecha", "obtener_fecha", ""),
    ]

    # Intentar coincidencia exacta primero (palabras exactas)
    for prefijo, accion, parametro in patrones_intencion:
        if prefijo == texto_normalizado:
            logger.info("Intencion basica detectada (coincidencia exacta): %s -> %s", prefijo, accion)
            return accion, parametro, True

    # Intentar coincidencia flexible (prefijo)
    for prefijo, accion, parametro in patrones_intencion:
        palabras_prefijo = prefijo.split()

        # Si el texto comienza con el prefijo
        if len(palabras_texto) >= len(palabras_prefijo):
            # Verificar si las primeras palabras coinciden (orden importante)
            texto_inicio = ' '.join(palabras_texto[:len(palabras_prefijo)])
            if texto_inicio == prefijo:
                logger.info("Intencion basica detectada (coincidencia flexible): %s -> %s", texto_normalizado, accion)
                return accion, parametro, True

    logger.debug("No se detecto intencion basica en: '%s'", comando)
    return None, None, False


def consultar_ia(comando: str, historial: HistorialConversacion) -> Tuple[str, str, bool]:
    """
    Consulta al modelo de IA configurado.
    Procesa la respuesta y gestiona el historial correctamente:
    - Solo agrega mensajes de conversación (user/assistant)
    - NO agrega respuestas JSON de comandos ejecutados

    Args:
        comando (str): comando o pregunta del usuario
        historial: Instancia de HistorialConversacion

    Returns:
        tuple: (accion, parametro, es_comando)
        es_comando = True si la acción no es "conversar"
    """
    # INTENTAR deteccion basica ANTES de llamar a Ollama
    accion_basica, parametro_basico, es_comando_basico = detectar_intencion_basica(comando)
    if accion_basica is not None:
        logger.info("Intencion basica detectada: %s con parametro '%s'", accion_basica, parametro_basico)
        return accion_basica, parametro_basico, es_comando_basico

    # Si no hay coincidencia basica, continuar con el flujo de IA
    config = cargar_config()
    tipo_ia = config["modelo_ia"]["tipo"]

    # Agregar el mensaje del usuario al historial
    historial.agregar_usuario(comando)

    if tipo_ia == "ollama":
        accion, parametro = _consultar_ollama(comando, historial)
    elif tipo_ia == "claude":
        accion, parametro = _consultar_claude(comando, historial)
    elif tipo_ia == "openai":
        accion, parametro = _consultar_openai(comando, historial)
    else:
        logger.error("Tipo de IA desconocido: %s", tipo_ia)
        return "conversar", "No tengo conexion con el modelo de IA.", False

    es_comando = historial.es_comando(accion)

    # SOLO agregar al historial si es conversacion
    # Si es comando, NO guardamos la respuesta JSON (evita contaminar el historial)
    if not es_comando:
        historial.agregar_asistente(parametro)

    return accion, parametro, es_comando


def _consultar_ollama(comando: str, historial: HistorialConversacion) -> Tuple[str, str]:
    """
    Consulta a Ollama.

    Args:
        comando (str): comando del usuario
        historial: Instancia de HistorialConversacion

    Returns:
        tuple: (accion, parametro)
    """
    import ollama

    config = cargar_config()
    modelo = config["modelo_ia"]["opciones"]["ollama"]["modelo"]

    system_prompt = (
        "Sos un asistente de escritorio en español rioplatense.\n"
        "Respondé SIEMPRE con un JSON válido y nada más, sin explicaciones, sin markdown.\n"
        "Formato exacto: {\"accion\": \"ACCION\", \"parametro\": \"VALOR\"}\n"
        "Acciones disponibles:\n"
        "- conversar: para charla o preguntas generales. parametro = tu respuesta corta.\n"
        "- reproducir_musica: cuando pidan poner música, si no mencionan canción específica dejá parametro vacío. parametro = nombre canción, artista o género.\n"
        "- cerrar_ventana: cuando pidan cerrar un programa (ej: 'cerrá el bloc de notas', 'cerrá la música', 'cerrá el navegador'). parametro = nombre del programa.\n"
        "- abrir_app: cuando pidan abrir algo. parametro = nombre del programa.\n"
        "- obtener_hora: cuando pidan la hora. parametro = vacio.\n"
        "- obtener_fecha: cuando pidan la fecha. parametro = vacio.\n"
        "- escribir: cuando pidan escribir algo (búsqueda, formulario, etc). parametro = texto a escribir.\n"
        "- youtube: cuando pidan youtube o buscar video. parametro = término de búsqueda (opcional).\n"
        "- play_pause: cuando pidan pausar o reanudar la reproducción de música o video. NO usar para cerrar programas. parametro = vacio.\n"
        "- siguiente_cancion: cuando pidan pasar a la siguiente canción. parametro = vacio.\n"
        "- anterior_cancion: cuando pidan volver a la canción anterior. parametro = vacio.\n"
        "- cerrar_pestania: cuando pidan cerrar una pestaña del navegador. parametro = vacio.\n"
        "- subir_volumen: cuando pidan subir el volumen. parametro = vacio.\n"
        "- bajar_volumen: cuando pidan bajar el volumen. parametro = vacio.\n"
        "- silenciar: cuando pidan silenciar o mutear. parametro = vacio.\n"
        "- establecer_volumen: cuando pidan un volumen específico. parametro = número del 0 al 100.\n"
        "Nunca respondas fuera del JSON. Nunca inventes información."
    )

    try:
        # Usar historial.mensajes (copia) para enviar a Ollama
        logger.info("=== MENSAJES ENVIADOS A OLLAMA ===")

        for i, msg in enumerate(historial.mensajes):
            logger.info("[%d] %s: %s",
                        i,
                        msg["role"],
                        msg["content"])

        logger.info("================================")
        respuesta = ollama.chat(
            model=modelo,
            messages=[{"role": "system", "content": system_prompt}] + historial.mensajes
        )

        texto = respuesta["message"]["content"].strip()

        # Limpiar markdown si existe
        texto = texto.replace("```json", "").replace("```", "").strip()
        logger.info("=== RESPUESTA RAW OLLAMA ===")
        logger.info(repr(texto))
        logger.info("============================")
        try:
            data = json.loads(texto)
            accion = data.get("accion", "conversar")
            parametro = data.get("parametro", "")
            logger.info(f"Acción: {accion} | Parámetro: {parametro}")
            return accion, parametro
        except json.JSONDecodeError:
            logger.error(f"JSON inválido de Ollama: {texto}")
            return "conversar", "No entendí bien, podés repetir?"

    except Exception as e:
        logger.error(f"Error consultando Ollama: {e}")
        return "conversar", "Hubo un error consultando el modelo de IA."


def _consultar_claude(comando: str, historial: HistorialConversacion) -> Tuple[str, str]:
    """Consulta a Claude API (por implementar)."""
    logger.warning("Claude API no implementado aún")
    return "conversar", "Claude API no está configurada."


def _consultar_openai(comando: str, historial: HistorialConversacion) -> Tuple[str, str]:
    """Consulta a OpenAI API (por implementar)."""
    logger.warning("OpenAI API no implementado aún")
    return "conversar", "OpenAI API no está configurada."

__all__ = [
    "normalizar",
    "_distancia_edicion",
    "detectar_intencion_basica",
    "consultar_ia",
    "_consultar_ollama",
    "_consultar_claude",
    "_consultar_openai"
]
