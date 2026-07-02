# ────────────────────────────────────────────────────────────────────
# Comando: Conversar
# ────────────────────────────────────────────────────────────────────
# Gestiona conversación general con el LLM, preguntas y respuestas
# que no encajan en categorías específicas.
# ────────────────────────────────────────────────────────────────────

import json

TRIGGERS = ["decir", "preguntar", "consultar", "explicar", "cuéntame", "qué", "cómo", 
            "dónde", "cuándo", "quién", "por qué", "cuál"]

def ejecutar(parametro):
    """
    Ejecuta conversación general.

    En la versión actual, simplemente retorna el parámetro como respuesta.
    El LLM ya ha procesado esto y generado una respuesta coherente.

    Args:
        parametro (str): respuesta del LLM para el usuario

    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    if not parametro or parametro.strip() == "":
        return False, "No tengo nada que decir al respecto."

    return True, parametro

# Funciones auxiliares expuestas
__all__ = ["ejecutar", "TRIGGERS"]
