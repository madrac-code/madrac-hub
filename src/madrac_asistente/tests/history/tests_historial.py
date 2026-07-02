"""
Tests unitarios para la refactorización del historial de Ollama
y el manejo de PID en musica.py / apps.py.

Ejecutar: venv\Scripts\python.exe tests_historial.py
"""

import sys
import os
import json

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historial import HistorialConversacion, procesar_respuesta_ollama, ACCIONES_COMANDO


def test_historial_basico():
    """Test: crear historial y agregar mensajes."""
    h = HistorialConversacion(max_tamano=10)
    assert h.tamano == 0, "Historial debería empezar vacío"

    h.agregar_usuario("Hola")
    h.agregar_asistente("¡Hola!")
    assert h.tamano == 2, f"Debería tener 2 mensajes, tiene {h.tamano}"

    msgs = h.mensajes
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hola"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "¡Hola!"

    print("[OK] test_historial_basico")


def test_limite_tamano():
    """Test: el historial respeta el límite máximo."""
    h = HistorialConversacion(max_tamano=3)

    for i in range(5):
        h.agregar_usuario(f"Mensaje {i}")

    assert h.tamano == 3, f"Debería tener 3 mensajes, tiene {h.tamano}"
    assert h.mensajes[0]["content"] == "Mensaje 2"
    assert h.mensajes[2]["content"] == "Mensaje 4"

    print("[OK] test_limite_tamano")


def test_limpiar():
    """Test: limpiar() vacía el historial."""
    h = HistorialConversacion()
    h.agregar_usuario("Test")
    h.agregar_asistente("Respuesta")
    assert h.tamano == 2

    h.limpiar()
    assert h.tamano == 0, "Debería estar vacío después de limpiar()"

    print("[OK] test_limpiar")


def test_es_comando():
    """Test: es_comando() detecta correctamente."""
    h = HistorialConversacion()

    comandos = [
        "reproducir_musica", "cerrar_ventana", "abrir_app",
        "obtener_hora", "obtener_fecha", "play_pause",
        "siguiente_cancion", "anterior_cancion", "youtube"
    ]

    for cmd in comandos:
        assert h.es_comando(cmd) == True, f"'{cmd}' debería ser comando"

    conversaciones = ["conversar", "otra_accion", "respuesta"]
    for conv in conversaciones:
        assert h.es_comando(conv) == False, f"'{conv}' NO debería ser comando"

    print("[OK] test_es_comando")


def test_respuesta_json_no_guardada():
    """Test: JSON de comando NO se guarda en historial."""
    h = HistorialConversacion()

    accion, param, es_cmd = procesar_respuesta_ollama(
        h,
        "poner música",
        '{"accion": "reproducir_musica", "parametro": ""}'
    )

    assert accion == "reproducir_musica"
    assert es_cmd == True
    assert h.tamano == 1, f"Debería tener 1 mensaje (solo user), tiene {h.tamano}"
    assert h.mensajes[0]["role"] == "user"
    assert h.mensajes[0]["content"] == "poner música"

    print("[OK] test_respuesta_json_no_guardada")


def test_respuesta_conversacional_guardada():
    """Test: respuesta conversacional SÍ se guarda."""
    h = HistorialConversacion()

    accion, param, es_cmd = procesar_respuesta_ollama(
        h,
        "¿Qué hora es?",
        '{"accion": "conversar", "parametro": "Son las 3."}'
    )

    assert accion == "conversar"
    assert es_cmd == False
    assert h.tamano == 2, f"Debería tener 2 mensajes, tiene {h.tamano}"
    assert h.mensajes[0]["role"] == "user"
    assert h.mensajes[1]["role"] == "assistant"

    print("[OK] test_respuesta_conversacional_guardada")


def test_json_invalido_tratado_como_conversacion():
    """Test: JSON inválido se trata como conversación."""
    h = HistorialConversacion()

    accion, param, es_cmd = procesar_respuesta_ollama(
        h,
        "hola",
        'Esto no es JSON'
    )

    assert accion == "conversar"
    assert es_cmd == False
    assert h.tamano == 2

    print("[OK] test_json_invalido_tratado_como_conversacion")


def test_limpiar_despues_de_comando():
    """Test: después de un comando, se limpia el historial."""
    h = HistorialConversacion()

    # Simular conversación previa
    h.agregar_usuario("Hola")
    h.agregar_asistente("¡Hola!")
    assert h.tamano == 2

    # Ejecutar comando
    accion, _, _ = procesar_respuesta_ollama(
        h,
        "poner música",
        '{"accion": "reproducir_musica", "parametro": ""}'
    )

    # Verificar que es comando
    assert h.es_comando(accion) == True

    # Limpiar después de comando
    h.limpiar()
    assert h.tamano == 0, f"Debería estar vacío, tiene {h.tamano}"

    print("[OK] test_limpiar_despues_de_comando")


def test_historial_independiente():
    """Test: dos historiales son independientes."""
    h1 = HistorialConversacion()
    h2 = HistorialConversacion()

    h1.agregar_usuario("Mensaje h1")
    h2.agregar_usuario("Mensaje h2")

    assert h1.tamano == 1
    assert h2.tamano == 1
    assert h1.mensajes[0]["content"] == "Mensaje h1"
    assert h2.mensajes[0]["content"] == "Mensaje h2"

    print("[OK] test_historial_independiente")


def test_mensajes_retorna_copia():
    """Test: mensajes retorna una copia, no la referencia."""
    h = HistorialConversacion()
    h.agregar_usuario("Original")

    msgs1 = h.mensajes
    msgs1.append({"role": "assistant", "content": "Modificado"})

    assert h.tamano == 1, "Modificar la copia no debería afectar el historial"

    print("[OK] test_mensajes_retorna_copia")


def test_acciones_comando_completo():
    """Test: ACCIONES_COMANDO contiene todas las acciones esperadas."""
    esperadas = {
        "reproducir_musica", "cerrar_ventana", "abrir_app",
        "obtener_hora", "obtener_fecha", "escribir", "youtube",
        "play_pause", "siguiente_cancion", "anterior_cancion",
        "cerrar_pestania", "subir_volumen", "bajar_volumen",
        "silenciar", "establecer_volumen"
    }

    assert ACCIONES_COMANDO == esperadas, \
        f"Faltan acciones: {esperadas - ACCIONES_COMANDO}"

    print("[OK] test_acciones_comando_completo")


def test_ejemplo_antes_vs_despues():
    """
    Ejemplo ilustrativo: comportamiento ANTES vs DESPUÉS de la refactorización.

    ANTES (código original):
        historial = []
        historial.append({"role": "user", "content": "poner música"})
        historial.append({"role": "assistant", "content": '{"accion": "reproducir_musica", "parametro": ""}'})
        # Resultado: historial = [user_msg, assistant_json_msg]
        # Problema: Ollama ve JSONs viejos y puede confundirse

    DESPUÉS (código refactorizado):
        historial = HistorialConversacion()
        historial.agregar_usuario("poner música")
        # NO se agrega la respuesta JSON al historial
        historial.limpiar()  # Se limpia después del comando
        # Resultado: historial = [] (limpio)
    """
    h = HistorialConversacion()

    # Simular flujo: usuario → comando → limpiar
    procesar_respuesta_ollama(
        h,
        "poner música",
        '{"accion": "reproducir_musica", "parametro": ""}'
    )
    # ANTES: esto agregaría JSON al historial
    # DESPUÉS: NO se agrega, y luego limpiamos
    h.limpiar()

    assert h.tamano == 0, "Historial debería estar limpio después de comando"

    print("[OK] test_ejemplo_antes_vs_despues")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTS UNITARIOS: Refactorización de Historial")
    print("=" * 60)
    print()

    test_historial_basico()
    test_limite_tamano()
    test_limpiar()
    test_es_comando()
    test_respuesta_json_no_guardada()
    test_respuesta_conversacional_guardada()
    test_json_invalido_tratado_como_conversacion()
    test_limpiar_despues_de_comando()
    test_historial_independiente()
    test_mensajes_retorna_copia()
    test_acciones_comando_completo()
    test_ejemplo_antes_vs_despues()

    print()
    print("=" * 60)
    print("TODOS LOS TESTS PASARON")
    print("=" * 60)
