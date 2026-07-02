# ────────────────────────────────────────────────────────────────────
# Módulo de Comandos del Asistente JARVIS
# ────────────────────────────────────────────────────────────────────
# Este paquete contiene todos los comandos disponibles del asistente.
# Cada módulo debe exponer:
#   - TRIGGERS: lista de palabras clave que activan el comando
#   - ejecutar(parametro): función que ejecuta la acción
# ────────────────────────────────────────────────────────────────────

from . import musica
from . import apps
from . import sistema
from . import conversar
from . import escribir
from . import youtube

__all__ = ["musica", "apps", "sistema", "conversar", "escribir", "youtube"]
