import os
import sys


def _raiz_proyecto() -> str:
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _raiz_ejecutable() -> str:
    try:
        from madrac.core.paths import get_project_root
        return str(get_project_root())
    except ImportError:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return _raiz_proyecto()


def obtener_ruta_recurso(ruta_relativa: str) -> str:
    return os.path.join(_raiz_proyecto(), ruta_relativa)


def obtener_ruta_escritura(ruta_relativa: str) -> str:
    return os.path.join(_raiz_ejecutable(), ruta_relativa)


__all__ = [
    "obtener_ruta_recurso",
    "obtener_ruta_escritura"
]
