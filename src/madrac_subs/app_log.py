"""
Logging centralizado - MADRAC-SUBS
Escribe en ~/.cache/madrac-subs/madrac-subs.log
"""

import logging
import sys
from pathlib import Path
from typing import Optional

_LOGGER: Optional[logging.Logger] = None
_LOG_DIR = Path.home() / '.cache' / 'madrac-subs'
_LOG_FILE = _LOG_DIR / 'madrac-subs.log'


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
	"""Configura logging a archivo y stderr. Idempotente."""
	global _LOGGER

	if _LOGGER is not None:
		return _LOGGER

	_LOG_DIR.mkdir(parents=True, exist_ok=True)

	logger = logging.getLogger('madrac_subs')
	logger.setLevel(level)
	logger.propagate = False

	if logger.handlers:
		_LOGGER = logger
		return logger

	formatter = logging.Formatter(
		'[%(asctime)s] %(levelname)-7s %(name)s: %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S',
	)

	file_handler = logging.FileHandler(_LOG_FILE, encoding='utf-8')
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(formatter)

	console_handler = logging.StreamHandler(sys.stderr)
	console_handler.setLevel(logging.INFO)
	console_handler.setFormatter(formatter)

	logger.addHandler(file_handler)
	logger.addHandler(console_handler)

	_LOGGER = logger
	logger.info('Logging iniciado — archivo: %s', _LOG_FILE)
	return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
	"""Obtiene un logger hijo de madrac_subs."""
	if _LOGGER is None:
		setup_logging()
	if name:
		return logging.getLogger(f'madrac_subs.{name}')
	return logging.getLogger('madrac_subs')


def obtener_ruta_log() -> Path:
	"""Ruta del archivo de log persistente."""
	return _LOG_FILE
