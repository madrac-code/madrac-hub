"""
Sistema modular de traducción para Transcriptor v2
Soporta: MarianMT (offline), Gemini, LibreTranslate, Google Translate
"""

import os
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, Dict, List, Optional
import requests
from pathlib import Path

try:
    from madrac.core.logging import get_logger as _get_v3_logger
    logger = _get_v3_logger('translator')
except ImportError:
    import app_log
    logger = app_log.get_logger('translator')


# ── Whisper→HuggingFace language code mapping ──────────────────────
_WHISPER_TO_HF = {
    "nn": "no",  # Norwegian Nynorsk → Norwegian Bokmål
    "nb": "no",  # Norwegian Bokmål → Norwegian
    "jw": "jv",  # Javanese
}

class IdiomaNoSoportado(Exception):
    """The translation engine does not support this language."""
    pass


class TraductorBase(ABC):
	"""Clase base para traductores"""

	def __init__(self, idioma_destino: str = "es"):
		"""
		Inicializa el traductor.

		Args:
			idioma_destino: Código de idioma destino (es, en, fr, etc.)
		"""
		self.idioma_destino = idioma_destino

	@abstractmethod
	def traducir(self, texto: str) -> str:
		"""
		Traduce un texto.

		Args:
			texto: Texto a traducir

		Returns:
			Texto traducido
		"""
		pass

	@abstractmethod
	def traducir_lote(self, textos: List[str], **kwargs) -> List[str]:
		"""
		Traduce múltiples textos.

		Args:
			textos: Lista de textos

		Returns:
			Lista de textos traducidos
		"""
		pass


class TraductorMarianMT(TraductorBase):
	"""
	Traductor usando MarianMT (offline, Helsinki-NLP/opus-mt-*)
	Soporta cadena de modelos para traducción indirecta (X->EN->ES).
	Requiere: pip install transformers torch sentencepiece
	"""

	def __init__(
		self,
		idioma_destino: str = "es",
		modelo: str = "Helsinki-NLP/opus-mt-en-es",
		dispositivo: str = "cpu",
		half_precision: bool = False,
		batch_size: int = 16,
		max_length: int = 128,
		timeout_lote_s: float = 120,
		modelos_adicionales: Optional[dict] = None,
	):
		"""
		Inicializa MarianMT.

		Args:
			idioma_destino: Idioma destino (es, en, fr, etc.)
			modelo: Nombre del modelo en HuggingFace
			dispositivo: "cpu" o "cuda"
			half_precision: Usar float16 para menos memoria
			modelos_adicionales: Dict {codigo_idioma: modelo_hf} para cadena X->EN
		"""
		super().__init__(idioma_destino)
		self.modelo_nombre = modelo
		self.dispositivo = dispositivo
		self.half_precision = half_precision
		self.batch_size = batch_size
		self.max_length = max_length
		self.timeout_lote_s = timeout_lote_s
		self.modelos_adicionales = modelos_adicionales or {}
		self._modelos_cadena_cache: dict = {}
		self.modelo = None
		self.tokenizer = None
		self._cargar_modelo()

	def _cargar_modelo(self) -> None:
		"""Carga el modelo principal (EN->ES) de transformers"""
		try:
			from transformers import MarianMTModel, MarianTokenizer

			logger.info("Cargando MarianMT: %s", self.modelo_nombre)

			self.tokenizer = MarianTokenizer.from_pretrained(self.modelo_nombre)
			self.modelo = MarianMTModel.from_pretrained(self.modelo_nombre)

			if self.half_precision and self.dispositivo == "cuda":
				self.modelo = self.modelo.half()

			self.modelo = self.modelo.to(self.dispositivo)
			self.modelo.eval()

			logger.info("MarianMT cargado correctamente")
			logger.info("Modelo Marian cargado: %s", self.modelo_nombre)

		except ImportError as e:
			logger.critical("ImportError al cargar MarianMT: %s", e)
			raise RuntimeError(
				f"MarianMT requiere: pip install transformers torch sentencepiece\n"
				f"ImportError: {e}"
			)
		except Exception as e:
			logger.exception("Error cargando MarianMT: %s", e)
			raise RuntimeError(f"Error cargando MarianMT: {e}")

	def _cargar_modelo_cadena(self, idioma_origen: str) -> tuple:
		"""
		Carga (o recupera de caché) un modelo MarianMT para X->EN.

		Args:
			idioma_origen: Código ISO del idioma origen (ja, de, fr, etc.)

		Returns:
			Tupla (tokenizer, model)

		Raises:
			IdiomaNoSoportado: Si el idioma no tiene modelo disponible
			RuntimeError: Si hay otro error al cargar el modelo
		"""
		if idioma_origen == "auto":
			raise RuntimeError(f"No se puede cargar modelo cadena para idioma_origen='auto'")

		# Map Whisper codes to HuggingFace model codes
		idioma_hf = _WHISPER_TO_HF.get(idioma_origen, idioma_origen)

		modelo_nombre = self.modelos_adicionales.get(idioma_origen)
		if not modelo_nombre:
			modelo_nombre = f"Helsinki-NLP/opus-mt-{idioma_hf}-en"
			logger.info("Modelo cadena no configurado para '%s', usando: %s (hf=%s)", idioma_origen, modelo_nombre, idioma_hf)

		if modelo_nombre in self._modelos_cadena_cache:
			return self._modelos_cadena_cache[modelo_nombre]

		# Pre-verificar que el modelo existe en HuggingFace antes de cargar
		# (evita cachear modelos inexistentes que producen traducciones corruptas)
		try:
			import requests as _req
			_check_url = f"https://huggingface.co/{modelo_nombre}/resolve/main/config.json"
			_check_r = _req.head(_check_url, timeout=10, allow_redirects=True)
			if _check_r.status_code not in (200, 302):
				logger.warning("Modelo '%s' no existe en HuggingFace (HTTP %d) — saltando", modelo_nombre, _check_r.status_code)
				raise IdiomaNoSoportado(f"No hay modelo MarianMT para '{idioma_origen}' (hf={idioma_hf})")
		except IdiomaNoSoportado:
			raise
		except Exception as _check_e:
			logger.warning("No se pudo verificar modelo '%s': %s — intentando carga directa", modelo_nombre, _check_e)

		try:
			from transformers import MarianMTModel, MarianTokenizer

			logger.info("Cargando modelo cadena %s->EN: %s", idioma_origen, modelo_nombre)
			tokenizer = MarianTokenizer.from_pretrained(modelo_nombre)
			model = MarianMTModel.from_pretrained(modelo_nombre)

			if self.half_precision and self.dispositivo == "cuda":
				model = model.half()

			model = model.to(self.dispositivo)
			model.eval()

			self._modelos_cadena_cache[modelo_nombre] = (tokenizer, model)
			logger.info("Modelo cadena cargado correctamente")
			return tokenizer, model

		except Exception as e:
			err_str = str(e)
			err_lower = err_str.lower()
			logger.exception("Error cargando modelo cadena %s: %s", modelo_nombre, err_str)
			if ("404" in err_str or "401" in err_str
					or "No such model" in err_str
					or "not found" in err_lower
					or "is not a valid model identifier" in err_lower
					or "RepositoryNotFoundError" in err_str):
				raise IdiomaNoSoportado(f"No hay modelo MarianMT para '{idioma_origen}' (hf={idioma_hf})")
			raise RuntimeError(f"Error cargando modelo cadena {modelo_nombre}: {err_str}")

	def traducir(self, texto: str) -> str:
		"""Traduce un texto individual"""
		if not self.modelo or not self.tokenizer:
			return texto

		try:
			inputs = self.tokenizer(texto, return_tensors="pt")
			inputs = {k: v.to(self.dispositivo) for k, v in inputs.items()}

			with __import__('torch').no_grad():
				outputs = self.modelo.generate(
					**inputs,
					max_length=self.max_length,
					num_beams=1,
				)

			traduccion = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
			return traduccion

		except Exception as e:
			logger.exception("Error en traducción MarianMT (individual): %s", e)
			return texto

	def _generar_lote(
		self,
		lote: List[str],
		tokenizer=None,
		model=None,
	) -> List[str]:
		"""
		Genera traducciones para un lote usando modelo y tokenizer específicos.

		Args:
			lote: Lista de textos a traducir
			tokenizer: Tokenizer a usar (default: self.tokenizer)
			model: Modelo a usar (default: self.modelo)

		Returns:
			Lista de textos traducidos
		"""
		tokenizer = tokenizer or self.tokenizer
		model = model or self.modelo

		inputs = tokenizer(
			lote,
			return_tensors="pt",
			padding=True,
			truncation=True,
			max_length=self.max_length,
		)
		inputs = {k: v.to(self.dispositivo) for k, v in inputs.items()}

		with __import__('torch').no_grad():
			outputs = model.generate(
				**inputs,
				max_length=self.max_length,
				num_beams=1,
			)

		return [
			tokenizer.decode(output, skip_special_tokens=True)
			for output in outputs
		]

	def _traducir_lote_con_modelo(
		self,
		textos: List[str],
		tokenizer,
		model,
		batch_size: Optional[int] = None,
		debe_cancelar: Optional[Callable[[], bool]] = None,
		on_progreso: Optional[Callable[[int, int], None]] = None,
	) -> List[str]:
		"""
		Traduce textos en lotes usando un modelo y tokenizer específicos.

		Args:
			textos: Lista de textos
			tokenizer: Tokenizer a usar
			model: Modelo a usar
			batch_size: Tamaño del lote
			debe_cancelar: Callback que retorna True para abortar
			on_progreso: Callback (lote_actual, total_lotes)

		Returns:
			Lista de textos traducidos
		"""
		if not model or not tokenizer:
			return textos

		if not textos:
			return []

		batch_size = batch_size or self.batch_size
		resultados: List[str] = []
		total_lotes = (len(textos) + batch_size - 1) // batch_size

		for indice_lote, i in enumerate(range(0, len(textos), batch_size)):
			if debe_cancelar and debe_cancelar():
				logger.warning("Traducción cancelada en lote %d/%d", indice_lote + 1, total_lotes)
				raise ProcesamientoCanceladoTraduccion()

			lote = textos[i:i + batch_size]

			if self.timeout_lote_s and self.timeout_lote_s > 0:
				with ThreadPoolExecutor(max_workers=1) as executor:
					future = executor.submit(
						self._generar_lote, lote, tokenizer, model
					)
					traducciones = future.result(timeout=self.timeout_lote_s)
			else:
				traducciones = self._generar_lote(lote, tokenizer, model)

			resultados.extend(traducciones)

			if on_progreso:
				on_progreso(indice_lote + 1, total_lotes)

		return resultados

	def traducir_lote(
		self,
		textos: List[str],
		batch_size: Optional[int] = None,
		debe_cancelar: Optional[Callable[[], bool]] = None,
		on_progreso: Optional[Callable[[int, int], None]] = None,
	) -> List[str]:
		"""
		Traduce múltiples textos en lotes para eficiencia.
		Usa el modelo principal (EN->ES).

		Args:
			textos: Lista de textos
			batch_size: Tamaño del lote
			debe_cancelar: Callback que retorna True para abortar
			on_progreso: Callback (lote_actual, total_lotes)
		"""
		if not self.modelo or not self.tokenizer:
			return textos
		return self._traducir_lote_con_modelo(
			textos, self.tokenizer, self.modelo,
			batch_size=batch_size,
			debe_cancelar=debe_cancelar,
			on_progreso=on_progreso,
		)

	def traducir_con_cadena(
		self,
		textos: List[str],
		idioma_origen: str,
		batch_size: Optional[int] = None,
		debe_cancelar: Optional[Callable[[], bool]] = None,
		on_progreso: Optional[Callable[[int, int], None]] = None,
	) -> List[str]:
		"""
		Traduce usando cadena de modelos según idioma de origen.

		- Si idioma_origen == "es": retorna texto original (sin traducción)
		- Si idioma_origen == "en" o "auto": usa modelo principal EN->ES directo
		- Si idioma_origen es otro válido: usa modelo X->EN -> luego EN->ES

		Args:
			textos: Lista de textos a traducir
			idioma_origen: Código ISO del idioma de origen
			batch_size: Tamaño del lote
			debe_cancelar: Callback que retorna True para abortar
			on_progreso: Callback (lote_actual, total_lotes)

		Returns:
			Lista de textos traducidos al idioma destino
		"""
		if not self.modelo or not self.tokenizer:
			return textos

		if idioma_origen == "es":
			if self.idioma_destino == "es":
				logger.info("Idioma origen es español, no se requiere traducción")
				return textos
			logger.info("Idioma origen es español, destino=%s — usando cadena ES->EN->%s", self.idioma_destino, self.idioma_destino)

		if idioma_origen in ("auto", "en"):
			if idioma_origen != "en":
				logger.warning("Idioma_origen='auto' recibido, tratando como 'en' (traducción directa EN->%s)", self.idioma_destino)
			return self.traducir_lote(
				textos,
				batch_size=batch_size,
				debe_cancelar=debe_cancelar,
				on_progreso=on_progreso,
			)

		logger.info("Cadena: %s->EN->%s", idioma_origen, self.idioma_destino)

		try:
			tokenizer_cadena, model_cadena = self._cargar_modelo_cadena(idioma_origen)
		except IdiomaNoSoportado:
			logger.warning("MarianMT no soporta '%s' — propagando para fallback", idioma_origen)
			raise
		except RuntimeError:
			logger.warning("Error cargando modelo para '%s' — retornando texto original sin traducir", idioma_origen)
			return textos

		textos_en = self._traducir_lote_con_modelo(
			textos, tokenizer_cadena, model_cadena,
			batch_size=batch_size,
			debe_cancelar=debe_cancelar,
			on_progreso=on_progreso,
		)

		if textos_en and textos_en[0] != textos[0]:
			logger.info("X->EN sample: '%s...' → '%s...'", textos[0][:60], textos_en[0][:60])

		textos_es = self._traducir_lote_con_modelo(
			textos_en, self.tokenizer, self.modelo,
			batch_size=batch_size,
			debe_cancelar=debe_cancelar,
			on_progreso=on_progreso,
		)

		if textos_es and textos_es[0] != textos_en[0]:
			logger.info("EN->%s sample: '%s...' → '%s...'", self.idioma_destino.upper(), textos_en[0][:60], textos_es[0][:60])

		return textos_es


class ProcesamientoCanceladoTraduccion(Exception):
	"""Traducción abortada por cancelación cooperativa."""


class TraductorGemini(TraductorBase):
	"""
	Traductor usando Google Gemini API
	Requiere: GOOGLE_API_KEY en variable de entorno
	"""

	def __init__(
		self,
		idioma_destino: str = "es",
		api_key: Optional[str] = None,
		modelo: str = "gemini-2.0-flash",
	):
		"""
		Inicializa Gemini.

		Args:
			idioma_destino: Idioma destino
			api_key: API key de Google (si no, usa variable de entorno)
			modelo: Modelo de Gemini a usar
		"""
		super().__init__(idioma_destino)
		self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
		self.modelo = modelo

		if not self.api_key:
			raise ValueError("GOOGLE_API_KEY no configurada")

	def _call_gemini(self, prompt: str) -> str:
		"""Llama a Gemini con reintentos en 429 (backoff exponencial)"""
		import time as _time
		max_retries = 3
		for attempt in range(max_retries):
			try:
				from google import genai as _genai
				client = _genai.Client(api_key=self.api_key)
				response = client.models.generate_content(
					model=self.modelo,
					contents=prompt,
				)
				return response.text.strip()
			except Exception as e:
				err_str = str(e)
				if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
					if "limit: 0" in err_str:
						logger.error(
							"Gemini: cuota gratuita agotada. "
							"Espera 24h o habilita facturación en "
							"https://aistudio.google.com/app/apikey"
						)
					elif attempt < max_retries - 1:
						wait = (2 ** attempt) * 2
						logger.warning("Gemini rate limited (429), reintentando en %ds (intento %d/%d)", wait, attempt + 1, max_retries)
						_time.sleep(wait)
						continue
				raise
		raise RuntimeError("Gemini max retries exceeded")

	def _es_error_api(self, e: Exception) -> bool:
		err_str = str(e)
		codes = ("429", "403", "503", "RESOURCE_EXHAUSTED", "PERMISSION_DENIED", "UNAVAILABLE")
		return any(c in err_str for c in codes)

	def traducir(self, texto: str) -> str:
		"""Traduce usando Gemini"""
		try:
			prompt = f"Traduce al {self._nombre_idioma(self.idioma_destino)} el siguiente texto, manteniendo la puntuación y sin agregar explicaciones:\n\n{texto}"
			return self._call_gemini(prompt)
		except ImportError:
			raise RuntimeError("Gemini requiere: pip install google-genai")
		except Exception as e:
			if self._es_error_api(e):
				logger.warning("Gemini API error (%s) — propagando a fallback chain", e)
				raise
			logger.exception("Error en traducción Gemini: %s", e)
			return texto

	def traducir_lote(self, textos: List[str], **kwargs) -> List[str]:
		"""Traduce lote EN UNA SOLA LLAMADA a Gemini"""
		if not textos:
			return []
		if len(textos) == 1:
			return [self.traducir(textos[0])]
		try:
			separator = "\n---BLOQUE---\n"
			combined = separator.join(textos)
			dest = self._nombre_idioma(self.idioma_destino)
			prompt = (
				f"Traduce al {dest} cada bloque de texto a continuación.\n"
				"Los bloques están separados por la línea '---BLOQUE---'.\n"
				"Mantén el ORDEN exacto.\n"
				"En tu respuesta, separa cada traducción con '---BLOQUE---'.\n"
				"NO agregues números, viñetas, ni explicaciones.\n"
				"SOLO las traducciones separadas por '---BLOQUE---'.\n\n"
				f"{combined}"
			)
			raw = self._call_gemini(prompt)
			parts = [p.strip() for p in raw.split("---BLOQUE---") if p.strip()]
			if len(parts) == len(textos):
				return parts
			logger.warning("Gemini devolvió %d bloques para %d textos", len(parts), len(textos))
		except Exception as e:
			if self._es_error_api(e):
				raise
			logger.warning("Gemini batch falló (%s) — fallback individual", e)
		import time as _time
		resultados = []
		for i, texto in enumerate(textos):
			try:
				resultados.append(self.traducir(texto))
			except Exception as e:
				if self._es_error_api(e):
					raise
				resultados.append(texto)
			if i < len(textos) - 1:
				_time.sleep(0.5)
		return resultados

	@staticmethod
	def _nombre_idioma(codigo: str) -> str:
		"""Convierte código de idioma a nombre"""
		idiomas = {
			"es": "español",
			"en": "inglés",
			"fr": "francés",
			"de": "alemán",
			"it": "italiano",
			"pt": "portugués",
			"ja": "japonés",
			"zh": "chino",
			"ko": "coreano",
		}
		return idiomas.get(codigo, codigo)


class TraductorLibreTranslate(TraductorBase):
	"""
	Traductor usando LibreTranslate (self-hosted o instancia pública)
	URL por defecto: http://localhost:5000
	"""

	def __init__(
		self,
		idioma_destino: str = "es",
		url: str = "http://localhost:5000",
		api_key: Optional[str] = None,
		timeout: float = 30,
	):
		"""
		Inicializa LibreTranslate.

		Args:
			idioma_destino: Idioma destino
			url: URL de la instancia LibreTranslate
			api_key: API key si lo requiere
			timeout: Timeout para requests
		"""
		super().__init__(idioma_destino)
		self.url = url.rstrip('/')
		self.api_key = api_key
		self.timeout = timeout
		self._verificar_disponibilidad()

	def _verificar_disponibilidad(self) -> None:
		"""Verifica que el servicio esté disponible"""
		try:
			response = requests.get(
				f"{self.url}/frontend/language",
				timeout=5
			)
			response.raise_for_status()
			logger.info("LibreTranslate disponible en %s", self.url)
		except Exception as e:
			raise RuntimeError(
				f"LibreTranslate no disponible en {self.url}: {e}\n"
				"Instala: docker run -it -p 5000:5000 libretranslate/libretranslate"
			)

	def traducir(self, texto: str) -> str:
		"""Traduce usando LibreTranslate"""
		try:
			payload = {
				"q": texto,
				"source": "auto",
				"target": self.idioma_destino,
			}

			if self.api_key:
				payload["api_key"] = self.api_key

			response = requests.post(
				f"{self.url}/translate",
				json=payload,
				timeout=self.timeout
			)
			response.raise_for_status()

			return response.json()["translatedText"]

		except Exception as e:
			logger.exception("Error en traducción LibreTranslate: %s", e)
			return texto

	def traducir_lote(self, textos: List[str], **kwargs) -> List[str]:
		"""Traduce lote de textos"""
		return [self.traducir(texto) for texto in textos]


class TraductorGoogle(TraductorBase):
	"""
	Traductor usando Google Translate (online, sin cuenta)
	Requiere: pip install google-cloud-translate
	"""

	def __init__(
		self,
		idioma_destino: str = "es",
		timeout: float = 30,
	):
		"""
		Inicializa Google Translate.

		Args:
			idioma_destino: Idioma destino
			timeout: Timeout para requests
		"""
		super().__init__(idioma_destino)
		self.timeout = timeout

	def traducir(self, texto: str) -> str:
		"""Traduce usando Google Translate (API web gratuita)"""
		try:
			return self._traducir_web(texto)
		except Exception as e:
			logger.exception("Error en traducción Google: %s", e)
			return texto

	def _traducir_web(self, texto: str) -> str:
		"""
		Traduce usando API no oficial de Google Translate (gratis, sin API key).
		Endpoint usado por translate.googleapis.com (mismo que googletrans).
		"""
		try:
			url = "https://translate.googleapis.com/translate_a/single"
			params = {
				"client": "gtx",
				"sl": "auto",
				"tl": self.idioma_destino,
				"dt": "t",
				"q": texto,
			}
			resp = requests.get(url, params=params, timeout=self.timeout)
			resp.raise_for_status()
			data = resp.json()
			partes = []
			for segmento in data[0]:
				if segmento and segmento[0]:
					partes.append(segmento[0])
			return "".join(partes) if partes else texto
		except Exception as e:
			logger.exception("Error en traducción Google Translate web: %s", e)
			return texto

	def traducir_lote(self, textos: List[str], **kwargs) -> List[str]:
		"""Traduce lote de textos"""
		return [self.traducir(texto) for texto in textos]


class GestorTraduccion:
	"""Gestor centralizado de traducción"""

	@classmethod
	def desde_config(cls) -> 'GestorTraduccion':
		"""Crea el gestor leyendo motor y parámetros desde config.json."""
		_get_cfg = None
		try:
			from madrac.config import get_config as _v3cfg
			_get_cfg = _v3cfg
		except ImportError:
			import config as _v2cfg
			_get_cfg = _v2cfg.get_config

		motor = _get_cfg('traduccion.motor', 'marianmt')
		idioma = _get_cfg('traduccion.idioma_destino', 'es')

		try:
			kwargs = _get_cfg.get_traductor_kwargs(motor, idioma)
		except AttributeError:
			kwargs = {'idioma_destino': idioma}
			cfg = _get_cfg(f'motores_traduccion.{motor}', {}) or {}
			if cfg:
				cleaned = {k: v for k, v in cfg.items() if not k.startswith('modelo_') or k == 'modelo'}
				kwargs.update(cleaned)

		if motor == 'marianmt':
			cfg = _get_cfg(f'motores_traduccion.{motor}', {}) or {}
			modelos_adicionales = {}
			for key, val in cfg.items():
				if key.startswith('modelo_') and key != 'modelo' and val:
					lang_code = key.split('_')[1]  # modelo_ja_en -> ja
					if lang_code:
						modelos_adicionales[lang_code] = val
			if modelos_adicionales:
				kwargs['modelos_adicionales'] = modelos_adicionales

		return cls(motor=motor, **kwargs)

	def __init__(self, motor: str = "marianmt", **kwargs):
		"""
		Inicializa el gestor.

		Args:
			motor: Tipo de motor ("marianmt", "gemini", "libretranslate", "google")
			**kwargs: Argumentos específicos del motor
		"""
		self.motor_tipo = motor
		self._kwargs = kwargs.copy()
		self.idioma_destino = kwargs.get('idioma_destino', 'es')
		self.motor = self._crear_motor(motor, **kwargs)
		self._motores_cache: Dict[str, TraductorBase] = {motor: self.motor}

	def _crear_motor(self, tipo: str, **kwargs) -> TraductorBase:
		"""
		Crea un traductor según el tipo.

		Args:
			tipo: Tipo de traductor
			**kwargs: Argumentos para el traductor

		Returns:
			Instancia del traductor
		"""
		if tipo == "marianmt":
			return TraductorMarianMT(**kwargs)
		elif tipo == "gemini":
			return TraductorGemini(**kwargs)
		elif tipo == "libretranslate":
			return TraductorLibreTranslate(**kwargs)
		elif tipo == "google":
			return TraductorGoogle(**kwargs)
		else:
			raise ValueError(f"Motor de traducción no reconocido: {tipo}")

	def traducir(self, texto: str) -> str:
		"""Traduce un texto"""
		return self.motor.traducir(texto)

	def _motor_para_idioma(self, idioma: str) -> TraductorBase:
		"""
		Retorna el motor configurado para un idioma específico (override),
		o el motor principal si no hay override.
		"""
		try:
			from madrac.config import get_config
			motor_override = get_config("traduccion.motor_por_idioma", {}).get(idioma)
		except Exception:
			motor_override = None

		if motor_override and motor_override != self.motor_tipo:
			if motor_override not in self._motores_cache:
				try:
					kwargs = self._extraer_kwargs(motor_override)
					self._motores_cache[motor_override] = self._crear_motor(motor_override, **kwargs)
				except Exception as e:
					logger.warning("No se pudo crear motor override '%s': %s", motor_override, e)
					return self.motor
			return self._motores_cache[motor_override]
		return self.motor

	def _extraer_kwargs(self, motor_tipo: str) -> dict:
		kwargs = {'idioma_destino': self.idioma_destino}
		try:
			from madrac.config import get_config
			cfg = get_config(f'motores_traduccion.{motor_tipo}', {}) or {}
			if cfg:
				cleaned = {k: v for k, v in cfg.items() if not k.startswith('modelo_') or k == 'modelo'}
				kwargs.update(cleaned)
		except Exception:
			pass
		return kwargs

	def _try_fallbacks(self, textos, **kwargs):
		fallback_types = [t for t in ("google", "libretranslate", "gemini") if t != self.motor_tipo]
		for ftype in fallback_types:
			if ftype not in self._motores_cache:
				try:
					fb_kwargs = self._extraer_kwargs(ftype)
					self._motores_cache[ftype] = self._crear_motor(ftype, **fb_kwargs)
				except Exception as e:
					logger.warning("No se pudo crear fallback '%s': %s", ftype, e)
					continue
			try:
				logger.info("Probando fallback '%s'", ftype)
				resultado = self._motores_cache[ftype].traducir_lote(textos, **kwargs)
				if resultado and resultado[0] != (textos[0] if textos else ''):
					logger.info("Fallback '%s' OK: '%s...' → '%s...'", ftype, (textos[0] if textos else '')[:60], resultado[0][:60])
				return resultado
			except Exception as e:
				logger.warning("Fallback '%s' fallo: %s", ftype, e)
				continue
		return None

	def traducir_lote(
		self,
		textos: List[str],
		idioma_origen: Optional[str] = None,
		**kwargs
	) -> List[str]:
		"""
		Traduce múltiples textos.
		Si es MarianMT y se provee idioma_origen, usa cadena de modelos.
		Si MarianMT no soporta el idioma, prueba otros motores configurados.

		Args:
			textos: Lista de textos
			idioma_origen: Código ISO del idioma de origen (para cadena MarianMT)
			**kwargs: Argumentos adicionales para el traductor

		Returns:
			Lista de textos traducidos
		"""
		if idioma_origen and self.motor_tipo == "marianmt":
			# Look up the override motor name for this language
			_override_nombre = None
			try:
				from madrac.config import get_config
				_override_nombre = get_config("traduccion.motor_por_idioma", {}).get(idioma_origen)
			except Exception:
				pass

			# Check per-language override first
			motor = self._motor_para_idioma(idioma_origen)
			if motor is not self.motor:
				try:
					return motor.traducir_lote(textos, **kwargs)
				except Exception as e:
					logger.warning("Override '%s' fallo para '%s': %s — probando cadena MarianMT",
					               _override_nombre or "?", idioma_origen, e)
					if _override_nombre and _override_nombre != self.motor_tipo:
						self._motores_cache.pop(_override_nombre, None)

			# Try primary MarianMT with chain
			if isinstance(self.motor, TraductorMarianMT):
				try:
					resultado = self.motor.traducir_con_cadena(
						textos, idioma_origen, **kwargs
					)
					if resultado and resultado[0] != textos[0]:
						logger.info("MarianMT cadena OK: '%s...' → '%s...'", textos[0][:60], resultado[0][:60])
					return resultado
				except IdiomaNoSoportado:
					logger.warning("MarianMT no soporta '%s' — probando otros motores", idioma_origen)
					traducciones = self._try_fallbacks(textos, **kwargs)
					if traducciones is not None:
						return traducciones
					logger.warning("Ningun motor soporta '%s' — retornando original", idioma_origen)
					return textos
		return self.motor.traducir_lote(textos, **kwargs)

	def cambiar_motor(self, tipo: str, **kwargs) -> None:
		"""Cambia a un motor diferente"""
		self.motor_tipo = tipo
		self._motores_cache = {tipo: self.motor} if hasattr(self, '_motores_cache') else {}
		self.motor = self._crear_motor(tipo, **kwargs)