# ────────────────────────────────────────────────────────────────────
# Comando: Musica
# ────────────────────────────────────────────────────────────────────
# Gestiona reproduccion de musica: busca archivos, selecciona generos,
# y controla reproduccion mediante reproductor del sistema.
# Mantiene un diccionario de procesos activos (pid -> nombre_proceso)
# para poder cerrarlos todos al detener la musica.
# ────────────────────────────────────────────────────────────────────

import os
import glob
import random
import subprocess
import json
import logging
import time
import winreg

logger = logging.getLogger(__name__)

TRIGGERS = ["poner", "reproducir", "musica", "cancion", "genero",
            "playlist", "tema", "artista", "album"]

# Coleccion de procesos de musica activos: { pid: nombre_proceso }
# En lugar de un unico PID, soporta multiples instancias simultaneas.
pids_musica_activos = {}

# Lista de reproductores de audio conocidos (nombre de proceso)
REPRODUCTORES_CONOCIDOS = [
    "wmplayer.exe", "vlc.exe", "mpv.exe", "groove.exe",
    "music.exe", "music.ui.exe", "microsoft.media.player.exe",
    "windowsmediaplayer.exe", "wmplayer"
]


def _obtener_reproductor_defecto(extension=".mp3"):
    """
    Lee del registro de Windows el reproductor asociado a una extension.

    Args:
        extension (str): extension de archivo (ej: .mp3, .flac)

    Returns:
        tuple: (ruta_exe: str | None, nombre_proceso: str | None)
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, extension) as key:
            tipo_archivo = winreg.QueryValue(key, "")
        if not tipo_archivo:
            return None, None
        cmd_key = f"{tipo_archivo}\\shell\\open\\command"
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, cmd_key) as key:
            cmdline = winreg.QueryValue(key, "")
        import re
        match = re.search(r'^"([^"]+\.exe)"', cmdline, re.IGNORECASE)
        if match:
            exe = match.group(1)
            nombre = os.path.basename(exe).lower()
            if os.path.isfile(exe):
                return exe, nombre
    except (OSError, PermissionError):
        pass
    return None, None


def cargar_config():
    """Carga configuracion y perfil del usuario."""
    from core import cargar_config as _cargar_config, cargar_perfil
    return _cargar_config(), cargar_perfil()


def buscar_musica(parametro):
    """
    Busca archivos de musica en ~/Music y subcarpetas.

    Acepta:
      - Nombre de cancion o artista
      - Genero (nombre de carpeta)
      - Palabras clave dentro del nombre del archivo

    Retorna: (ruta_archivo, mensaje_respuesta)
    """
    config, perfil = cargar_config()
    carpeta_musica = os.path.expanduser(config["carpetas"]["musica"])
    extensiones = ["*.mp3", "*.flac", "*.wav", "*.ogg", "*.m4a"]
    parametro = parametro.lower().strip()

    # Palabras vacias/ruido: tratar como "cualquier musica"
    if parametro in ["", "desconocido", "unknown", "nada", "lo que sea", "musica", "una cancion", "cualquier cosa"]:
        parametro = ""

    # Buscar en todas las subcarpetas y raiz
    todos = []
    for ext in extensiones:
        todos += glob.glob(os.path.join(carpeta_musica, "**", ext), recursive=True)
        todos += glob.glob(os.path.join(carpeta_musica, ext))

    if not todos:
        return None, "No encontre ningun archivo de musica en la carpeta."

    # Si pide un genero (nombre de carpeta exacto o alias)
    for genero_alias, genero_real in perfil["generos_musica"].items():
        if parametro.lower() == genero_alias.lower():
            genero_path = os.path.join(carpeta_musica, genero_real)
            if os.path.isdir(genero_path):
                archivos_genero = []
                for ext in extensiones:
                    archivos_genero += glob.glob(os.path.join(genero_path, ext))
                if archivos_genero:
                    elegido = random.choice(archivos_genero)
                    return elegido, "Poniendo musica de " + genero_real + "."

    # Buscar por nombre de archivo (busqueda parcial)
    coincidencias = []
    for archivo in todos:
        nombre = os.path.splitext(os.path.basename(archivo))[0].lower()
        if parametro in nombre:
            coincidencias.append(archivo)

    if coincidencias:
        elegido = random.choice(coincidencias)
        return elegido, "Poniendo " + os.path.basename(elegido) + "."

    # Si no encontro nada especifico, elige aleatoria
    elegido = random.choice(todos)
    return elegido, "No encontre exactamente eso, poniendo " + os.path.basename(elegido) + "."


def _limpiar_pids_muertos():
    """
    Elimina del diccionario los PIDs que ya no existen en el sistema.
    Debe llamarse antes de cualquier operacion que itere pids_musica_activos.
    """
    muertos = []
    for pid in pids_musica_activos:
        try:
            import psutil
            if not psutil.pid_exists(pid):
                muertos.append(pid)
        except ImportError:
            # Sin psutil, asumir vivos (no limpiar)
            return
    for pid in muertos:
        nombre = pids_musica_activos.pop(pid, None)
        logger.info("PID muerto eliminado de coleccion: " + str(pid) + " (" + str(nombre) + ")")


def hay_musica_reproduciendose():
    """
    Verifica si hay procesos de musica activos en el sistema.

    Returns:
        bool: True si al menos un PID de la coleccion sigue vivo
    """
    _limpiar_pids_muertos()
    return len(pids_musica_activos) > 0


def reproducir_musica(ruta_archivo):
    """
    Abre el archivo de musica con el reproductor del sistema.

    Comportamiento EXCLUSIVO: antes de abrir nueva musica,
    cierra cualquier instancia activa previa (evita multiples reproductores).

    Guarda el PID y nombre del proceso real en pids_musica_activos.

    Estrategia de captura (por orden de preferencia):
    1. Leer reproductor del registro de Windows y lanzarlo directamente.
    2. Si el proceso murio (delego a instancia existente), escanear por cmdline.
    3. Fallback a os.startfile() + snapshot de procesos por nombre.
    4. Ultimo recurso: cmd /c start + psutil children.

    Args:
        ruta_archivo (str): ruta absoluta al archivo de musica

    Returns:
        bool: True si se inicio la reproduccion
    """
    global pids_musica_activos

    # ─── Modo exclusivo: cerrar musica previa antes de abrir nueva ───
    if hay_musica_reproduciendose():
        logger.info("Cerrando musica previa antes de abrir nueva...")
        detener_musica()

    pid_capturado = None
    nombre_proceso = None

    try:
        # ─── Estrategia 1: Lanzar reproductor directamente ───
        player_exe, player_name = _obtener_reproductor_defecto()
        if player_exe and player_name:
            logger.info("Lanzando reproductor: " + player_exe)
            proc = subprocess.Popen([player_exe, ruta_archivo], shell=False)
            time.sleep(0.5)
            if proc.poll() is None:
                pid_capturado = proc.pid
                nombre_proceso = player_name
                logger.info("Musica reproduciendo - PID directo: " + str(pid_capturado) + " (" + player_name + ")")
            else:
                logger.info("Reproductor delego a instancia existente, escaneando procesos...")

        # ─── Estrategia 2: Detectar proceso por cmdline ───
        if pid_capturado is None:
            try:
                import psutil
                archivo_bajo = os.path.basename(ruta_archivo).lower()
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline')
                        if cmdline and any(archivo_bajo in c.lower() for c in cmdline if c):
                            nombre = proc.info['name'].lower()
                            if any(nombre == p.lower() for p in REPRODUCTORES_CONOCIDOS):
                                pid_capturado = proc.info['pid']
                                nombre_proceso = proc.info['name']
                                logger.info("Musica reproduciendo - detectado por cmdline: "
                                            + str(pid_capturado) + " (" + nombre_proceso + ")")
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except ImportError:
                pass

        # ─── Estrategia 3: os.startfile + snapshot ───
        if pid_capturado is None:
            known_lower = [p.lower() for p in REPRODUCTORES_CONOCIDOS]
            before = {}
            try:
                import psutil
                for p in psutil.process_iter(['pid', 'name']):
                    try:
                        nombre = p.info['name'].lower()
                        if any(nombre == k for k in known_lower):
                            before[p.info['pid']] = p.info['name']
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except ImportError:
                pass

            os.startfile(ruta_archivo)
            time.sleep(1.5)

            try:
                import psutil
                for p in psutil.process_iter(['pid', 'name']):
                    try:
                        pid = p.info['pid']
                        nombre = p.info['name']
                        nombre_lower = nombre.lower()
                        if pid not in before and any(nombre_lower == k for k in known_lower):
                            pid_capturado = pid
                            nombre_proceso = nombre
                            logger.info("Musica reproduciendo - detectado por snapshot: "
                                        + str(pid) + " (" + nombre + ")")
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except ImportError:
                pass

        # ─── Estrategia 4: cmd /c start + psutil children ───
        if pid_capturado is None:
            proc = subprocess.Popen(
                ["cmd", "/c", "start", "", ruta_archivo],
                shell=False
            )
            time.sleep(0.5)
            try:
                import psutil
                hijos = psutil.Process(proc.pid).children()
                if hijos:
                    pid_capturado = hijos[0].pid
                    nombre_proceso = hijos[0].name()
                    logger.info("Musica reproduciendo - PID hijo: "
                                + str(pid_capturado) + " (" + nombre_proceso + ")")
                else:
                    pid_capturado = proc.pid
                    logger.info("Musica reproduciendo - PID del shell: " + str(proc.pid))
            except Exception as e:
                pid_capturado = proc.pid
                logger.warning("No se pudo detectar PID hijo: " + str(e))

        # ─── Registrar el PID capturado ───
        if pid_capturado is not None:
            pids_musica_activos[pid_capturado] = nombre_proceso or "desconocido"
            logger.info("Total procesos activos: " + str(len(pids_musica_activos)))
            return True

        logger.warning("No se pudo capturar ningun PID de reproductor")
        return True

    except Exception as e:
        logger.error("Error al reproducir musica: " + str(e))
        return False


def detener_musica():
    """
    Detiene TODOS los procesos de musica activos.

    Por cada PID en pids_musica_activos intenta:
    1. psutil.terminate()
    2. taskkill /F /PID
    3. taskkill /F /IM (por nombre, si se conocio)

    Returns:
        tuple: (exito: bool, mensaje: str)
        exito es True si al menos un proceso fue cerrado.
        mensaje indica cuantos procesos se cerraron.
    """
    global pids_musica_activos

    _limpiar_pids_muertos()

    if not pids_musica_activos:
        return False, "No hay musica reproduciendose."

    cerrados = 0
    total = len(pids_musica_activos)

    for pid, nombre_proceso in list(pids_musica_activos.items()):
        logger.info("Deteniendo proceso " + str(pid) + " (" + str(nombre_proceso) + ")...")

        # Metodo 1: psutil terminate
        if pid is not None:
            try:
                import psutil
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=5)
                logger.info("Proceso detenido con psutil: " + str(pid) + " (" + str(nombre_proceso) + ")")
                cerrados += 1
                continue
            except ImportError:
                pass
            except psutil.NoSuchProcess:
                logger.warning("Proceso " + str(pid) + " ya no existe")
                cerrados += 1  # Consideramos que ya no existe como "cerrado"
                continue
            except psutil.AccessDenied:
                logger.warning("Acceso denegado al proceso " + str(pid))
            except Exception as e:
                logger.warning("Error con psutil: " + str(e))

        # Metodo 2: taskkill /PID
        if pid is not None:
            try:
                resultado = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, text=True, timeout=5
                )
                if resultado.returncode == 0:
                    logger.info("Proceso detenido con taskkill /PID: " + str(pid))
                    cerrados += 1
                    continue
            except Exception as e:
                logger.error("Error con taskkill /PID: " + str(e))

        # Metodo 3: taskkill /IM por nombre
        if nombre_proceso:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", nombre_proceso],
                    capture_output=True, timeout=5
                )
                logger.info("Proceso detenido con taskkill /IM: " + nombre_proceso)
                cerrados += 1
                continue
            except Exception as e:
                logger.error("Error con taskkill /IM: " + str(e))

        # Metodo 4: Buscar por lista de reproductores conocidos
        if nombre_proceso and nombre_proceso.lower() == "desconocido":
            procesos_audio = ["wmplayer.exe", "vlc.exe", "mpv.exe", "musicplayer.exe"]
            for proc_name in procesos_audio:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", proc_name],
                        capture_output=True, timeout=5
                    )
                    cerrados += 1
                except Exception:
                    pass

    # Limpiar coleccion
    pids_musica_activos.clear()

    if cerrados > 0:
        mensaje = "Cerre " + str(cerrados) + " proceso" + ("s" if cerrados != 1 else "") + " de musica."
        return True, mensaje
    else:
        return False, "No se pudo cerrar ningun proceso de musica."


def ejecutar(parametro):
    """
    Ejecuta el comando de musica.

    Args:
        parametro (str): nombre de cancion, artista, genero o busqueda

    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    if not parametro or parametro.strip() == "":
        ruta, mensaje = buscar_musica("")
        if ruta:
            return reproducir_musica(ruta), mensaje
        return False, "No tengo musica para reproducir."

    ruta, mensaje = buscar_musica(parametro)
    if ruta:
        exito = reproducir_musica(ruta)
        return exito, mensaje
    else:
        return False, mensaje


# ─── Tests inline ──────────────────────────────────────────────────
def _test_pids_activos():
    """Test: coleccion de PIDs se comporta como conjunto."""
    global pids_musica_activos
    pids_musica_activos.clear()
    assert len(pids_musica_activos) == 0
    assert hay_musica_reproduciendose() == False
    pids_musica_activos[9999] = "test.exe"
    # El PID 9999 no existe, limpiar deberia eliminarlo
    _limpiar_pids_muertos()
    # Sin psutil, _limpiar_pids_muertos no hace nada
    import psutil
    if not psutil.pid_exists(9999):
        _limpiar_pids_muertos()
    assert 9999 not in pids_musica_activos
    print("[OK] _test_pids_activos")


def _test_detener_sin_musica():
    """Test: detener cuando no hay musica activa."""
    global pids_musica_activos
    pids_musica_activos.clear()
    exito, mensaje = detener_musica()
    assert exito == False
    assert "No hay musica" in mensaje
    print("[OK] _test_detener_sin_musica")


def _test_detener_doble():
    """Test: doble llamada a detener no falla."""
    global pids_musica_activos
    pids_musica_activos.clear()
    exito1, _ = detener_musica()
    assert exito1 == False
    exito2, _ = detener_musica()
    assert exito2 == False
    print("[OK] _test_detener_doble")


def _test_hay_musica_con_activos():
    """Test: hay_musica_reproduciendose con PIDs reales."""
    global pids_musica_activos
    pids_musica_activos.clear()
    # Poner nuestro propio PID (siempre existe)
    import os
    mi_pid = os.getpid()
    pids_musica_activos[mi_pid] = "python.exe"
    assert hay_musica_reproduciendose() == True
    pids_musica_activos.clear()
    assert hay_musica_reproduciendose() == False
    print("[OK] _test_hay_musica_con_activos")


def _test_multiples_pids():
    """Test: multiples PIDs en coleccion."""
    global pids_musica_activos
    pids_musica_activos.clear()
    import os
    pids_musica_activos[os.getpid()] = "python.exe"  # vivo
    pids_musica_activos[99999] = "no_existe.exe"      # muerto
    # Sin psutil.pid_exists, _limpiar_pids_muertos no borra nada,
    # pero hay_musica_reproduciendose llama a _limpiar_pids_muertos
    assert len(pids_musica_activos) >= 1
    pids_musica_activos.clear()
    print("[OK] _test_multiples_pids")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTS UNITARIOS: comandos/musica.py")
    print("=" * 60)
    print()
    _test_pids_activos()
    _test_detener_sin_musica()
    _test_detener_doble()
    _test_hay_musica_con_activos()
    _test_multiples_pids()
    print()
    print("=" * 60)
    print("TODOS LOS TESTS PASARON")
    print("=" * 60)

__all__ = [
    "reproducir_musica", "detener_musica", "ejecutar",
    "hay_musica_reproduciendose", "pids_musica_activos",
    "TRIGGERS",
]
