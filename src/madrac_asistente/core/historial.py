# ────────────────────────────────────────────────────────────────────
# historial.py — Gestión del historial de conversación con Ollama
# ────────────────────────────────────────────────────────────────────
# Separa el historial de conversación (user/assistant) de los comandos
# JSON ejecutados. Limpia el historial tras cada comando no conversacional.
# ────────────────────────────────────────────────────────────────────

import json
from typing import List, Dict, Tuple


# ─── CONSTANTES ────────────────────────────────────────────────────

# Acciones que NO son conversacionales (son comandos ejecutables)
ACCIONES_COMANDO = {
    "reproducir_musica", "cerrar_ventana", "abrir_app",
    "obtener_hora", "obtener_fecha", "escribir", "youtube",
    "play_pause", "siguiente_cancion", "anterior_cancion",
    "cerrar_pestania", "subir_volumen", "bajar_volumen",
    "silenciar", "establecer_volumen"
}


# ─── CLASE HISTORIAL ──────────────────────────────────────────────

class HistorialConversacion:
    """
    Gestiona el historial de mensajes para Ollama.

    Reglas:
    - Solo se guardan mensajes de conversación (user/assistant)
    - NO se guardan respuestas JSON de comandos ejecutados
    - Se limpia el historial tras cada comando no conversacional
    - Se limita el tamaño máximo del historial
    """

    def __init__(self, max_tamano: int = 10):
        self._mensajes: List[Dict] = []
        self._max_tamano = max_tamano

    @property
    def mensajes(self) -> List[Dict]:
        """Retorna copia del historial actual."""
        return self._mensajes.copy()

    @property
    def tamano(self) -> int:
        """Retorna cantidad de mensajes en el historial."""
        return len(self._mensajes)

    def agregar_usuario(self, texto: str) -> None:
        """
        Agrega un mensaje del usuario al historial.

        Args:
            texto: Texto que dijo el usuario
        """
        self._mensajes.append({
            "role": "user",
            "content": texto
        })
        self._recortar()

    def agregar_asistente(self, texto: str) -> None:
        """
        Agrega un mensaje del asistente al historial.
        Solo se usa para respuestas conversacionales (NO para JSON de comandos).

        Args:
            texto: Texto de respuesta del asistente
        """
        self._mensajes.append({
            "role": "assistant",
            "content": texto
        })
        self._recortar()

    def es_comando(self, accion: str) -> bool:
        """
        Determina si una acción es un comando ejecutable
        (no conversacional).

        Args:
            accion: Nombre de la acción devuelta por Ollama

        Returns:
            True si es un comando, False si es conversación
        """
        return accion in ACCIONES_COMANDO

    def limpiar(self) -> None:
        """
        Limpia todo el historial.
        Se llama tras ejecutar un comando no conversacional.
        """
        self._mensajes.clear()

    def _recortar(self) -> None:
        """Mantiene el historial dentro del límite máximo."""
        while len(self._mensajes) > self._max_tamano:
            self._mensajes.pop(0)


def crear_historial(max_tamano: int = 10) -> HistorialConversacion:
    """Factory function para crear un historial."""
    return HistorialConversacion(max_tamano=max_tamano)


def procesar_respuesta_ollama(
    historial: HistorialConversacion,
    comando: str,
    respuesta_texto: str
) -> Tuple[str, str, bool]:
    """
    Procesa la respuesta de Ollama:
    1. Agrega el comando del usuario al historial
    2. Parsea el JSON de respuesta
    3. Si es conversación, agrega la respuesta al historial
    4. Si es comando, NO agrega la respuesta (solo limpiar después)

    Args:
        historial: Instancia de HistorialConversacion
        comando: Texto del usuario
        respuesta_texto: Respuesta JSON de Ollama

    Returns:
        Tupla (accion, parametro, es_comando)
    """
    # Siempre agregar el mensaje del usuario
    historial.agregar_usuario(comando)

    # Parsear respuesta
    texto = respuesta_texto.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(texto)
        accion = data.get("accion", "conversar")
        parametro = data.get("parametro", "")
    except json.JSONDecodeError:
        # JSON inválido → tratar como conversación
        historial.agregar_asistente(texto)
        return "conversar", "No entendí bien, podés repetir?", False

    es_comando = historial.es_comando(accion)

    # SOLO agregar al historial si es conversación
    if not es_comando:
        historial.agregar_asistente(texto)
    # Si es comando, NO guardamos la respuesta JSON en el historial

    return accion, parametro, es_comando