"""
Utilidades compartidas - MADRAC-SUBS
Funciones para ffprobe, ffmpeg, validación, paths, etc.
Multiplataforma: Linux / Windows / macOS
"""

import os
import sys
import json
import subprocess
import threading
from pathlib import Path
from typing import Tuple, Optional, List, Dict
import shutil

import app_log

logger = app_log.get_logger('utils')


# Extensiones multimedia soportadas
EXTENSIONES_VIDEO = {
	'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v', '.wmv',
	'.3gp', '.3g2', '.mts', '.ts', '.vob',
}
EXTENSIONES_AUDIO = {
	'.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma', '.opus',
}
EXTENSIONES_MULTIMEDIA = EXTENSIONES_VIDEO | EXTENSIONES_AUDIO

# Proceso ffmpeg activo (para cancelación cooperativa)
_proceso_ffmpeg_lock = threading.Lock()
_proceso_ffmpeg_activo: Optional[subprocess.Popen] = None


# Flags de creación (Windows: ocultar ventana cmd)
CREATION_FLAGS = 0
if os.name == 'nt':
    CREATION_FLAGS = 0x08000000  # CREATE_NO_WINDOW


def resolver_ejecutable(nombre: str) -> Optional[str]:
    """
    Busca un ejecutable (ffmpeg, ffprobe) en:
    1. sys._MEIPASS (frozen PyInstaller)
    2. PATH del sistema
    Retorna la ruta completa o None si no se encuentra.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        ruta = Path(sys._MEIPASS) / nombre
        if ruta.exists():
            return str(ruta)
    ruta_encontrada = shutil.which(nombre)
    if ruta_encontrada:
        return ruta_encontrada
    return None


# ============================================================================
# FFPROBE - Obtener información de archivos multimedia
# ============================================================================

def obtener_duracion_archivo(ruta_archivo: str) -> float:
	"""
	Obtiene la duración de un archivo multimedia usando ffprobe.

	Args:
		ruta_archivo: Ruta al archivo de audio/video

	Returns:
		Duracion en segundos (float), o 0 si hay error
	"""
	try:
		ffprobe = resolver_ejecutable('ffprobe')
		if ffprobe is None:
			logger.warning("ffprobe no encontrado en PATH ni en bundle")
			return 0.0

		cmd = [
			ffprobe,
			'-v', 'error',
			'-show_entries', 'format=duration',
			'-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1',
			ruta_archivo
		]

		resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
		                           creationflags=CREATION_FLAGS)

		if resultado.returncode == 0:
			return float(resultado.stdout.strip())
		logger.warning("Error ffprobe: %s", resultado.stderr)
		return 0.0

	except subprocess.TimeoutExpired:
		logger.warning("Timeout al obtener duracion de %s", ruta_archivo)
		return 0.0
	except (ValueError, AttributeError):
		logger.warning("No se pudo procesar la duracion")
		return 0.0
	except Exception as e:
		logger.warning("Error inesperado: %s", e)
		return 0.0


# ============================================================================
# FFMPEG - Extracción de audio
# ============================================================================

def cancelar_proceso_activo() -> None:
	"""Termina el proceso ffmpeg en ejecución, si existe."""
	global _proceso_ffmpeg_activo
	with _proceso_ffmpeg_lock:
		proceso = _proceso_ffmpeg_activo
		_proceso_ffmpeg_activo = None

	if not proceso or proceso.poll() is not None:
		return

	try:
		proceso.terminate()
		proceso.wait(timeout=5)
	except subprocess.TimeoutExpired:
		proceso.kill()
		proceso.wait(timeout=5)
	except Exception as e:
		logger.warning("Error cancelando ffmpeg: %s", e)


def extraer_audio(ruta_video: str, ruta_salida: str, formato: str = "wav") -> bool:
	"""
	Extrae el audio de un archivo de video.

	Args:
		ruta_video: Ruta al archivo de video
		ruta_salida: Ruta donde guardar el audio extraído
		formato: Formato de salida (wav, mp3, aac, etc.)

	Returns:
		True si tuvo éxito, False si falló o fue cancelado
	"""
	global _proceso_ffmpeg_activo

	try:
		ffmpeg = resolver_ejecutable('ffmpeg')
		if ffmpeg is None:
			logger.warning("ffmpeg no encontrado en PATH ni en bundle")
			return False

		Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)

		cmd = [
			ffmpeg,
			'-i', ruta_video,
			'-vn',
			'-acodec', 'pcm_s16le' if formato == 'wav' else 'libmp3lame',
			'-ar', '16000',
			'-ac', '1',
			'-y',
			ruta_salida
		]

		with _proceso_ffmpeg_lock:
			_proceso_ffmpeg_activo = subprocess.Popen(
				cmd,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.PIPE,
				text=True,
				creationflags=CREATION_FLAGS,
			)
			proceso = _proceso_ffmpeg_activo

		_, stderr = proceso.communicate(timeout=3600)

		with _proceso_ffmpeg_lock:
			if _proceso_ffmpeg_activo is proceso:
				_proceso_ffmpeg_activo = None

		if proceso.returncode != 0:
			if proceso.returncode in (-15, -9):
				logger.info("Extraccion de audio cancelada")
			else:
				logger.warning("Error ffmpeg: %s", stderr)
			return False

		return Path(ruta_salida).exists()

	except subprocess.TimeoutExpired:
		cancelar_proceso_activo()
		logger.warning("Timeout al extraer audio")
		return False
	except Exception as e:
		cancelar_proceso_activo()
		logger.warning("Error extrayendo audio: %s", e)
		return False


# ============================================================================
# VALIDACIÓN DE ARCHIVOS
# ============================================================================

def validar_archivo(ruta_archivo: str) -> Tuple[bool, str]:
	"""
	Valida que el archivo exista y sea un formato multimedia soportado.

	Returns:
		Tupla (válido: bool, mensaje_error: str)
	"""
	ruta = Path(ruta_archivo)

	if not ruta.exists():
		return False, "Archivo no existe"

	if not ruta.is_file():
		return False, "No es un archivo"

	if ruta.suffix.lower() not in EXTENSIONES_MULTIMEDIA:
		return False, f"Formato no soportado: {ruta.suffix}"

	if ruta.stat().st_size < 100:
		return False, "Archivo muy pequeño (posible corrupción)"

	if not os.access(ruta, os.R_OK):
		return False, "Sin permisos de lectura"

	return True, ""


def es_archivo_video(ruta_archivo: str) -> bool:
	"""True si la extensión corresponde a un contenedor de video."""
	return Path(ruta_archivo).suffix.lower() in EXTENSIONES_VIDEO


def es_archivo_audio(ruta_archivo: str) -> bool:
	"""True si la extensión corresponde a un archivo de audio."""
	return Path(ruta_archivo).suffix.lower() in EXTENSIONES_AUDIO


def normalizar_ruta(ruta: str) -> str:
	"""Resuelve la ruta de forma multiplataforma."""
	return str(Path(ruta).resolve())


# ============================================================================
# GESTIÓN DE PATHS Y CARPETAS
# ============================================================================

def crear_carpeta_salida(ruta_archivo: str, subcarpeta: str = "_transcripcion") -> str:
	"""Crea una carpeta de salida junto al archivo original."""
	ruta = Path(ruta_archivo)
	carpeta_salida = ruta.parent / f"{ruta.stem}{subcarpeta}"
	carpeta_salida.mkdir(parents=True, exist_ok=True)
	return str(carpeta_salida)


def limpiar_archivo_temporal(ruta: str) -> None:
	"""Elimina un archivo temporal."""
	try:
		archivo = Path(ruta)
		if archivo.exists():
			archivo.unlink()
	except Exception as e:
		logger.warning("No se pudo limpiar %s: %s", ruta, e)


def obtener_nombre_base(ruta_archivo: str) -> str:
	"""Obtiene el nombre del archivo sin extensión."""
	return Path(ruta_archivo).stem


def abrir_en_explorador(ruta: Path) -> None:
	"""Abre una carpeta en el gestor de archivos del sistema."""
	import sys

	ruta = Path(ruta)
	if sys.platform == 'win32':
		os.startfile(ruta)  # type: ignore[attr-defined]
	elif sys.platform == 'darwin':
		subprocess.Popen(['open', str(ruta)])
	else:
		subprocess.Popen(['xdg-open', str(ruta)])


# ============================================================================
# HASH DE ARCHIVOS
# ============================================================================

def compute_sha256(ruta: Path, block_size: int = 65536) -> Optional[str]:
    """Computa SHA-256 de un archivo en streaming. Retorna hex digest o None."""
    import hashlib
    try:
        h = hashlib.sha256()
        with open(ruta, 'rb') as f:
            while True:
                block = f.read(block_size)
                if not block:
                    break
                h.update(block)
        return h.hexdigest()
    except Exception as e:
        logger.warning("Error computando SHA256 de %s: %s", ruta, e)
        return None


# ============================================================================
# FORMATEO DE TIEMPO
# ============================================================================

def formatear_tiempo_srt(segundos: float) -> str:
	"""Formatea tiempo en formato SRT (HH:MM:SS,mmm)."""
	horas = int(segundos // 3600)
	minutos = int((segundos % 3600) // 60)
	segs = int(segundos % 60)
	milisegundos = int((segundos % 1) * 1000)
	return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegundos:03d}"


def formatear_tiempo_legible(segundos: float) -> str:
	"""Formatea duración de forma legible (ej: 1h 23m 45s)."""
	if segundos < 0:
		return "0s"

	horas = int(segundos // 3600)
	minutos = int((segundos % 3600) // 60)
	segs = int(segundos % 60)

	partes = []
	if horas > 0:
		partes.append(f"{horas}h")
	if minutos > 0:
		partes.append(f"{minutos}m")
	if segs > 0 or not partes:
		partes.append(f"{segs}s")

	return " ".join(partes)


# ============================================================================
# ESTIMACIONES
# ============================================================================

def estimar_tiempo_transcripcion(
	duracion_segundos: float,
	modelo: str = "base",
	vad_filter: bool = True
) -> float:
	"""Estima el tiempo de transcripción basado en el modelo."""
	factores_rtf = {
		'tiny': 0.2,
		'base': 0.4,
		'small': 0.8,
		'medium': 1.5,
	}

	rtf = factores_rtf.get(modelo, 0.5)
	if vad_filter:
		rtf *= 0.7

	return max(duracion_segundos * rtf, 1.0)


# ============================================================================
# SUBTÍTULOS EMBEBIDOS - Detección y extracción
# ============================================================================

def detectar_pistas_subtitulos(ruta_video: str) -> List[Dict]:
	"""
	Detecta pistas de subtítulos embebidas en un archivo de video.

	Usa ffprobe para listar streams de tipo subtitle con su idioma.

	Args:
		ruta_video: Ruta al archivo de video (mkv, mp4, etc.)

	Returns:
		Lista de dicts con {index, codec, language}
		Vacía si no hay pistas o si falla ffprobe.
	"""
	try:
		ffprobe = resolver_ejecutable('ffprobe')
		if ffprobe is None:
			logger.warning("ffprobe no encontrado en PATH ni en bundle")
			return []

		cmd = [
			ffprobe,
			'-v', 'error',
			'-select_streams', 's',
			'-show_entries', 'stream=index,codec_name:stream_tags=language',
			'-of', 'json',
			ruta_video,
		]
		resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
		                           creationflags=CREATION_FLAGS)

		if resultado.returncode != 0:
			logger.warning("Error ffprobe detectando subtitulos: %s", resultado.stderr[:200])
			return []

		data = json.loads(resultado.stdout)
		pistas = []

		for stream in data.get('streams', []):
			tags = stream.get('tags', {}) or {}
			language = tags.get('language', 'und')
			pistas.append({
				'index': stream['index'],
				'codec': stream.get('codec_name', 'unknown'),
				'language': language,
			})

		return pistas

	except subprocess.TimeoutExpired:
		logger.warning("Timeout detectando subtitulos")
		return []
	except (json.JSONDecodeError, KeyError, ValueError) as e:
		logger.warning("Error parseando pistas de subtitulos: %s", e)
		return []
	except Exception as e:
		logger.warning("Error inesperado detectando subtitulos: %s", e)
		return []


_MAPEO_PRIORIDAD_IDIOMA = {
	'eng': 0,
	'spa': 1,
}

def obtener_idioma_prioritario(pistas: List[Dict]) -> Optional[Dict]:
	"""
	Selecciona la mejor pista de subtítulos según prioridad de idioma.

	Prioridad: inglés (eng) > español (spa) > cualquier otro

	Args:
		pistas: Lista de dicts de detectar_pistas_subtitulos

	Returns:
		Dict con {index, codec, language} de la pista elegida, o None
	"""
	if not pistas:
		return None

	elegida = None
	mejor_prioridad = float('inf')

	for pista in pistas:
		lang = pista.get('language', 'und')
		prioridad = _MAPEO_PRIORIDAD_IDIOMA.get(lang, 999)
		if prioridad < mejor_prioridad:
			mejor_prioridad = prioridad
			elegida = pista

	return elegida


def extraer_pista_subtitulos(
	ruta_video: str,
	indice_stream: int,
	ruta_salida: str
) -> bool:
	"""
	Extrae una pista de subtítulos de un video y la convierte a SRT.

	Args:
		ruta_video: Ruta al archivo de video
		indice_stream: Index del stream a extraer
		ruta_salida: Ruta donde guardar el archivo SRT

	Returns:
		True si la extracción fue exitosa
	"""
	global _proceso_ffmpeg_activo

	try:
		ffmpeg = resolver_ejecutable('ffmpeg')
		if ffmpeg is None:
			logger.warning("ffmpeg no encontrado en PATH ni en bundle")
			return False

		Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)

		cmd = [
			ffmpeg,
			'-i', ruta_video,
			'-map', f'0:{indice_stream}',
			'-c:s', 'srt',
			'-y',
			ruta_salida,
		]

		with _proceso_ffmpeg_lock:
			_proceso_ffmpeg_activo = subprocess.Popen(
				cmd,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.PIPE,
				text=True,
				creationflags=CREATION_FLAGS,
			)
			proceso = _proceso_ffmpeg_activo

		_, stderr = proceso.communicate(timeout=120)

		with _proceso_ffmpeg_lock:
			if _proceso_ffmpeg_activo is proceso:
				_proceso_ffmpeg_activo = None

		if proceso.returncode != 0:
			if proceso.returncode in (-15, -9):
				logger.info("Extraccion de subtitulos cancelada")
			else:
				logger.warning("Error ffmpeg extrayendo subtitulos: %s", stderr)
			return False

		return Path(ruta_salida).exists()

	except subprocess.TimeoutExpired:
		cancelar_proceso_activo()
		logger.warning("Timeout extrayendo subtitulos")
		return False
	except Exception as e:
		cancelar_proceso_activo()
		logger.warning("Error extrayendo subtitulos: %s", e)
		return False


# =============================================================================
# Funciones de espacio en disco y limpieza (Partes 3-4 de release audit)
# =============================================================================

def _tamano_directorio(ruta: Path) -> int:
	"""Suma el tamaño de todos los archivos en un directorio (recursivo)."""
	if not ruta.exists():
		return 0
	total = 0
	for f in ruta.rglob('*'):
		if f.is_file():
			try:
				total += f.stat().st_size
			except OSError as e:
				logger.debug("Error accediendo a %s: %s", f, e)
	return total


def calcular_espacio_por_categoria() -> Dict[str, int]:
	"""
	Calcula espacio ocupado por cada categoría de archivos.
	Retorna dict con bytes: whisper, marian, cache_hf, logs, temporales.
	"""
	result: Dict[str, int] = {
		'whisper': 0,
		'marian': 0,
		'cache_hf': 0,
		'logs': 0,
		'temporales': 0,
	}

	hf_path = Path.home() / '.cache' / 'huggingface' / 'hub'
	if hf_path.exists():
		for model_dir in hf_path.iterdir():
			if not model_dir.is_dir():
				continue
			size = _tamano_directorio(model_dir)
			name_lower = model_dir.name.lower()
			if 'faster-whisper' in name_lower:
				result['whisper'] += size
			elif 'opus-mt' in name_lower:
				result['marian'] += size
			else:
				result['cache_hf'] += size

	log_path = Path.home() / '.cache' / 'madrac-subs' / 'madrac-subs.log'
	if log_path.exists():
		try:
			result['logs'] = log_path.stat().st_size
		except OSError as e:
			logger.debug("Error accediendo a logs: %s", e)

	temp_path = Path('.cache/temporal')
	if temp_path.exists():
		result['temporales'] = _tamano_directorio(temp_path)

	return result


def limpiar_temporales() -> int:
	"""Elimina archivos temporales. Retorna bytes liberados."""
	temp_path = Path('.cache/temporal')
	if not temp_path.exists():
		return 0
	tamano = _tamano_directorio(temp_path)
	for f in temp_path.rglob('*'):
		if f.is_file():
			try:
				f.unlink()
			except OSError as e:
				logger.warning("Error eliminando %s: %s", f, e)
	return tamano


def limpiar_logs() -> int:
	"""Trunca el archivo de log. Retorna bytes liberados."""
	log_path = Path.home() / '.cache' / 'madrac-subs' / 'madrac-subs.log'
	if not log_path.exists():
		return 0
	try:
		tamano = log_path.stat().st_size
		log_path.write_text('', encoding='utf-8')
		return tamano
	except OSError as e:
		logger.warning("Error truncando log: %s", e)
		return 0


def limpiar_cache_huggingface() -> int:
	"""Elimina toda la caché de HuggingFace. Retorna bytes liberados."""
	hf_path = Path.home() / '.cache' / 'huggingface' / 'hub'
	if not hf_path.exists():
		return 0
	tamano = _tamano_directorio(hf_path)
	import shutil
	try:
		shutil.rmtree(hf_path)
	except OSError as e:
		logger.warning("Error limpiando cache HF: %s", e)
	return tamano


def limpiar_todo() -> int:
	"""Ejecuta todas las limpiezas. Retorna bytes totales liberados."""
	total = 0
	total += limpiar_temporales()
	total += limpiar_logs()
	total += limpiar_cache_huggingface()
	if sys.platform == "win32":
		try:
			from core.registry import desregistrar_drop_handler
			desregistrar_drop_handler()
		except Exception:
			pass
	return total
