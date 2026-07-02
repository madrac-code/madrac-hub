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
    - Se limpia el historial después de cada comando no conversacional
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
        Se llama después de ejecutar un comando no conversacional.
        """
        self._mensajes.clear()

    def _recortar(self) -> None:
        """Mantiene el historial dentro del límite máximo."""
        while len(self._mensajes) > self._max_tamano:
            self._mensajes.pop(0)


# ─── FUNCIONES AUXILIARES ─────────────────────────────────────────

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


# ─── TESTS UNITARIOS INLINE ───────────────────────────────────────

if __name__ == "__main__":
    print("=== TESTS UNITARIOS: historial.py ===\n")

    # Test 1: Crear historial vacío
    h = crear_historial(max_tamano=5)
    assert h.tamano == 0, "Historial debería empezar vacío"
    print("[OK] Test 1: Historial empieza vacío")

    # Test 2: Agregar mensajes
    h.agregar_usuario("Hola")
    h.agregar_asistente("¡Hola! ¿Cómo estás?")
    assert h.tamano == 2, f"Debería tener 2 mensajes, tiene {h.tamano}"
    print("[OK] Test 2: Agregar mensajes funciona")

    # Test 3: Límite de tamaño
    h2 = crear_historial(max_tamano=3)
    for i in range(5):
        h2.agregar_usuario(f"Mensaje {i}")
    assert h2.tamano == 3, f"Debería tener 3 mensajes, tiene {h2.tamano}"
    assert h2.mensajes[0]["content"] == "Mensaje 2", "Primer mensaje debería ser 'Mensaje 2'"
    print("[OK] Test 3: Límite de tamaño funciona")

    # Test 4: Limpiar historial
    h.limpiar()
    assert h.tamano == 0, "Historial debería estar vacío después de limpiar()"
    print("[OK] Test 4: limpiar() funciona")

    # Test 5: Detectar comandos vs conversación
    h3 = crear_historial()
    assert h3.es_comando("reproducir_musica") == True, "reproducir_musica es comando"
    assert h3.es_comando("cerrar_ventana") == True, "cerrar_ventana es comando"
    assert h3.es_comando("conversar") == False, "conversar NO es comando"
    assert h3.es_comando("obtener_hora") == True, "obtener_hora es comando"
    print("[OK] Test 5: Detección comando vs conversación")

    # Test 6: Respuesta JSON NO se guarda en historial
    h4 = crear_historial()
    accion, param, es_cmd = procesar_respuesta_ollama(
        h4,
        "poner música",
        '{"accion": "reproducir_musica", "parametro": ""}'
    )
    assert accion == "reproducir_musica", f"Acción incorrecta: {accion}"
    assert es_cmd == True, "Debería detectar como comando"
    assert h4.tamano == 1, f"Debería tener 1 mensaje (solo user), tiene {h4.tamano}"
    assert h4.mensajes[0]["role"] == "user", "El mensaje debería ser del user"
    print("[OK] Test 6: JSON de comando NO se guarda en historial")

    # Test 7: Respuesta conversacional SÍ se guarda
    h5 = crear_historial()
    accion, param, es_cmd = procesar_respuesta_ollama(
        h5,
        "¿Qué hora es?",
        '{"accion": "conversar", "parametro": "Son las 3 de la tarde."}'
    )
    assert accion == "conversar", f"Acción incorrecta: {accion}"
    assert es_cmd == False, "Debería detectar como conversación"
    assert h5.tamano == 2, f"Debería tener 2 mensajes (user+assistant), tiene {h5.tamano}"
    print("[OK] Test 7: Respuesta conversacional SÍ se guarda")

    # Test 8: Limpiar después de comando
    h6 = crear_historial()
    h6.agregar_usuario("Hola")
    h6.agregar_asistente("¡Hola!")
    assert h6.tamano == 2

    accion, _, _ = procesar_respuesta_ollama(
        h6,
        "poner música",
        '{"accion": "reproducir_musica", "parametro": ""}'
    )
    if h6.es_comando(accion):
        h6.limpiar()
    assert h6.tamano == 0, f"Debería estar vacío después de comando, tiene {h6.tamano}"
    print("[OK] Test 8: Limpiar después de comando funciona")

    # Test 9: JSON inválido se trata como conversación
    h7 = crear_historial()
    accion, param, es_cmd = procesar_respuesta_ollama(
        h7,
        "hola",
        'Esto no es JSON válido'
    )
    assert accion == "conversar", "JSON inválido debería ser conversación"
    assert es_cmd == False
    assert h7.tamano == 2, "Debería tener user + assistant"
    print("[OK] Test 9: JSON inválido se trata como conversación")

    print("\n=== TODOS LOS TESTS PASARON ===")
