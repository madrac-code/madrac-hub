"""
Formateador profesional de subtítulos - MADRAC-SUBS
Genera subtítulos en estándares de streaming (Netflix, etc.)
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
import re

import app_log
import config

logger = app_log.get_logger('formatter')


@dataclass
class Subtitulo:
	"""Representa un subtítulo individual"""

	numero: int
	inicio_ms: int  # Milisegundos
	fin_ms: int     # Milisegundos
	texto: str

	def obtener_inicio_srt(self) -> str:
		"""Formatea el inicio en formato SRT"""
		return self._ms_a_srt(self.inicio_ms)

	def obtener_fin_srt(self) -> str:
		"""Formatea el fin en formato SRT"""
		return self._ms_a_srt(self.fin_ms)

	@staticmethod
	def _ms_a_srt(ms: int) -> str:
		"""Convierte milisegundos a formato SRT (HH:MM:SS,mmm)"""
		segundos_total = ms // 1000
		ms_resto = ms % 1000

		horas = segundos_total // 3600
		minutos = (segundos_total % 3600) // 60
		segundos = segundos_total % 60

		return f"{horas:02d}:{minutos:02d}:{segundos:02d},{ms_resto:03d}"

	def obtener_duracion_ms(self) -> int:
		"""Calcula la duración del subtítulo en milisegundos"""
		return max(self.fin_ms - self.inicio_ms, 0)

	def obtener_lineas(self) -> List[str]:
		"""Divide el texto en líneas"""
		return self.texto.split('\n')

	def contar_palabras(self) -> int:
		"""Cuenta las palabras en el subtítulo"""
		return len(self.texto.split())


class FormateadorSubtitulos:
	"""Formatea y optimiza subtítulos para estándares profesionales"""

	# Configuración de estándares Netflix/Streaming
	MAX_CARACTERES_POR_LINEA = 42
	MAX_LINEAS_POR_SUBTITULO = 2
	DURACION_MINIMA_MS = 1500  # 1.5 segundos
	DURACION_MAXIMA_MS = 7000  # 7 segundos
	CARACTERES_MINIMOS_JUSTIFICACION = 30  # Para justificar 2 líneas

	def __init__(
		self,
		max_chars: int = MAX_CARACTERES_POR_LINEA,
		max_lineas: int = MAX_LINEAS_POR_SUBTITULO,
		duracion_min_ms: int = DURACION_MINIMA_MS,
		duracion_max_ms: int = DURACION_MAXIMA_MS,
	):
		"""
		Inicializa el formateador con parámetros personalizados.

		Args:
			max_chars: Máximo de caracteres por línea
			max_lineas: Máximo de líneas por subtítulo
			duracion_min_ms: Duración mínima en ms
			duracion_max_ms: Duración máxima en ms
		"""
		self.max_chars = max_chars
		self.max_lineas = max_lineas
		self.duracion_min_ms = duracion_min_ms
		self.duracion_max_ms = duracion_max_ms

	@classmethod
	def desde_config(cls) -> 'FormateadorSubtitulos':
		"""Crea un formateador leyendo parámetros desde config.json."""
		cfg = config.get_subtitulos_config()
		return cls(
			max_chars=cfg.get('max_chars_por_linea', cls.MAX_CARACTERES_POR_LINEA),
			max_lineas=cfg.get('max_lineas_por_subtitulo', cls.MAX_LINEAS_POR_SUBTITULO),
			duracion_min_ms=cfg.get('duracion_minima_ms', cls.DURACION_MINIMA_MS),
			duracion_max_ms=cfg.get('duracion_maxima_ms', cls.DURACION_MAXIMA_MS),
		)

	@staticmethod
	def limpiar_subtitulo(texto: str) -> str:
		"""Elimina etiquetas HTML y códigos ASS de un texto de subtítulo."""
		texto = re.sub(r"<[^>]+>", "", texto)
		texto = re.sub(r"\{\\.*?\}", "", texto)
		return texto.strip()

	@staticmethod
	def cargar_desde_srt(ruta_srt: str) -> list:
		"""
		Carga subtítulos desde un archivo SRT existente.

		Parsea el formato SRT estándar:
			numero
			HH:MM:SS,mmm --> HH:MM:SS,mmm
			texto (una o más líneas)
			<linea vacía>

		Args:
			ruta_srt: Ruta al archivo .srt

		Returns:
			Lista de Subtitulo

		Raises:
			FileNotFoundError: Si el archivo no existe
			ValueError: Si el formato SRT es inválido
		"""
		with open(ruta_srt, 'r', encoding='utf-8-sig') as f:
			contenido = f.read()

		bloques = re.split(r'\n\s*\n', contenido.strip())
		subtitulos = []

		for bloque in bloques:
			lineas = bloque.strip().split('\n')
			if len(lineas) < 3:
				continue

			try:
				numero = int(lineas[0].strip())
			except (ValueError, IndexError):
				continue

			tiempo_match = re.match(
				r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*'
				r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
				lineas[1].strip()
			)
			if not tiempo_match:
				continue

			def _ms(h, m, s, ms):
				return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)

			inicio_ms = _ms(*tiempo_match.groups()[:4])
			fin_ms = _ms(*tiempo_match.groups()[4:])

			texto = FormateadorSubtitulos.limpiar_subtitulo('\n'.join(lineas[2:]))

			subtitulos.append(Subtitulo(
				numero=numero,
				inicio_ms=inicio_ms,
				fin_ms=fin_ms,
				texto=texto,
			))

		return subtitulos

	# ========================================================================
	# FORMATEO PRINCIPAL
	# ========================================================================

	def formatear_desde_segmentos_whisper(
		self,
		segmentos: List[dict],
		ajustar_duraciones: bool = True
	) -> List[Subtitulo]:
		"""
		Formatea subtítulos desde segmentos de Whisper.

		Args:
			segmentos: Lista de segmentos de Whisper con 'start', 'end', 'text'
			ajustar_duraciones: Si ajustar duraciones a estándares

		Returns:
			Lista de Subtitulo formateados profesionalmente
		"""
		if not segmentos:
			return []

		# Convertir segmentos Whisper a subtítulos brutos
		subtitulos = [
			Subtitulo(
				numero=i + 1,
				inicio_ms=int(seg['start'] * 1000),
				fin_ms=int(seg['end'] * 1000),
				texto=seg['text'].strip()
			)
			for i, seg in enumerate(segmentos)
		]

		# Aplicar transformaciones
		subtitulos = self._dividir_lineas_largas(subtitulos)
		subtitulos = self._agrupar_subtitulos_cortos(subtitulos)
		subtitulos = self._balancear_lineas(subtitulos)

		if ajustar_duraciones:
			subtitulos = self._ajustar_duraciones(subtitulos)

		# Re-numerar
		for i, sub in enumerate(subtitulos):
			sub.numero = i + 1

		return subtitulos

	# ========================================================================
	# TRANSFORMACIONES
	# ========================================================================

	def _dividir_lineas_largas(self, subtitulos: List[Subtitulo]) -> List[Subtitulo]:
		"""
		Divide subtítulos con líneas muy largas en múltiples líneas.
		Intenta dividir en pausas naturales (comas, puntos).
		"""
		resultado = []

		for sub in subtitulos:
			lineas = sub.texto.split('\n')
			lineas_nuevas = []

			for linea in lineas:
				if len(linea) <= self.max_chars:
					lineas_nuevas.append(linea)
				else:
					# Dividir en pausas naturales
					divididas = self._dividir_en_pausas_naturales(linea, self.max_chars)
					lineas_nuevas.extend(divididas)

			# Limitar a max_lineas
			if len(lineas_nuevas) > self.max_lineas:
				# Agrupar líneas excesivas
				lineas_nuevas = self._agrupar_lineas(lineas_nuevas, self.max_lineas)

			sub.texto = '\n'.join(lineas_nuevas)
			resultado.append(sub)

		return resultado

	def _dividir_en_pausas_naturales(self, texto: str, max_chars: int) -> List[str]:
		"""
		Divide un texto largo en líneas, intentando hacerlo en pausas naturales.
		"""
		if len(texto) <= max_chars:
			return [texto]

		# Intentar dividir en estos separadores (en orden de preferencia)
		separadores = [
			(', ', ', '),       # Coma + espacio
			(' and ', ' and '),  # Conjunción
			(' or ', ' or '),    # O
			(' - ', ' - '),      # Guión
			(' ', ' '),          # Espacio simple
		]

		for sep, join_char in separadores:
			if sep in texto:
				partes = texto.split(sep)

				# Intentar agrupar partes para respetar max_chars
				lineas = []
				linea_actual = ""

				for i, parte in enumerate(partes):
					# Agregar separador si no es primera
					prefijo = "" if i == 0 else join_char
					candidato = linea_actual + prefijo + parte

					if len(candidato) <= max_chars:
						linea_actual = candidato
					else:
						if linea_actual:
							lineas.append(linea_actual)
						linea_actual = parte

				if linea_actual:
					lineas.append(linea_actual)

				# Verificar que todas las líneas respeten max_chars
				if all(len(l) <= max_chars for l in lineas):
					return lineas

		# Fallback: cortar forzadamente
		return [texto[i:i+max_chars] for i in range(0, len(texto), max_chars)]

	def _agrupar_lineas(self, lineas: List[str], max_lineas: int) -> List[str]:
		"""Agrupa líneas excesivas en líneas permitidas"""
		if len(lineas) <= max_lineas:
			return lineas

		resultado = []
		i = 0

		while i < len(lineas):
			grupo = [lineas[i]]
			longitud_total = len(lineas[i])
			i += 1

			# Intentar agregar más líneas mientras quepan
			while i < len(lineas) and len(grupo) < max_lineas:
				nueva_longitud = longitud_total + 1 + len(lineas[i])
				if nueva_longitud <= self.max_chars * max_lineas:
					grupo.append(lineas[i])
					longitud_total = nueva_longitud
					i += 1
				else:
					break

			resultado.append('\n'.join(grupo))

		return resultado

	def _agrupar_subtitulos_cortos(self, subtitulos: List[Subtitulo]) -> List[Subtitulo]:
		"""Agrupa subtítulos muy cortos para mejorar legibilidad"""
		if len(subtitulos) < 2:
			return subtitulos

		resultado = []
		i = 0

		while i < len(subtitulos):
			sub_actual = subtitulos[i]

			# Si el subtítulo es muy corto, intentar agrupar con el siguiente
			if (i + 1 < len(subtitulos) and 
				len(sub_actual.texto) < 15 and
				sub_actual.obtener_duracion_ms() < 1500):

				# Combinar con el siguiente
				sub_siguiente = subtitulos[i + 1]
				sub_combinado = Subtitulo(
					numero=sub_actual.numero,
					inicio_ms=sub_actual.inicio_ms,
					fin_ms=sub_siguiente.fin_ms,
					texto=f"{sub_actual.texto} {sub_siguiente.texto}"
				)
				resultado.append(sub_combinado)
				i += 2
			else:
				resultado.append(sub_actual)
				i += 1

		return resultado

	def _balancear_lineas(self, subtitulos: List[Subtitulo]) -> List[Subtitulo]:
		"""Balancea el contenido entre líneas para mejor visualización"""
		resultado = []

		for sub in subtitulos:
			lineas = sub.texto.split('\n')

			if len(lineas) == 2:
				# Intentar balancear dos líneas
				linea1, linea2 = lineas

				# Si una es mucho más larga que la otra, intentar redistribuir
				if len(linea1) > len(linea2) * 1.5 or len(linea2) > len(linea1) * 1.5:
					palabras = sub.texto.split()
					mitad = len(palabras) // 2

					nueva_linea1 = ' '.join(palabras[:mitad])
					nueva_linea2 = ' '.join(palabras[mitad:])

					if (len(nueva_linea1) <= self.max_chars and 
						len(nueva_linea2) <= self.max_chars):
						sub.texto = f"{nueva_linea1}\n{nueva_linea2}"

			resultado.append(sub)

		return resultado

	def _ajustar_duraciones(self, subtitulos: List[Subtitulo]) -> List[Subtitulo]:
		"""Ajusta duraciones a rangos aceptables"""
		resultado = []

		for i, sub in enumerate(subtitulos):
			duracion = sub.obtener_duracion_ms()

			# Ajustar duración mínima
			if duracion < self.duracion_min_ms:
				sub.fin_ms = sub.inicio_ms + self.duracion_min_ms

			# Ajustar duración máxima
			elif duracion > self.duracion_max_ms:
				sub.fin_ms = sub.inicio_ms + self.duracion_max_ms

			# Evitar solapamientos con siguiente
			if i + 1 < len(subtitulos):
				siguiente = subtitulos[i + 1]
				if sub.fin_ms > siguiente.inicio_ms:
					# Reducir este o mover el siguiente
					diferencia = sub.fin_ms - siguiente.inicio_ms + 1
					sub.fin_ms -= diferencia // 2
					siguiente.inicio_ms += (diferencia - diferencia // 2)

			resultado.append(sub)

		return resultado

	# ========================================================================
	# EXPORTACIÓN
	# ========================================================================

	def generar_srt(self, subtitulos: List[Subtitulo]) -> str:
		"""
		Genera contenido en formato SRT.

		Args:
			subtitulos: Lista de Subtitulo

		Returns:
			Cadena con formato SRT
		"""
		lineas = []

		for sub in subtitulos:
			lineas.append(str(sub.numero))
			lineas.append(f"{sub.obtener_inicio_srt()} --> {sub.obtener_fin_srt()}")
			lineas.append(sub.texto)
			lineas.append("")  # Línea vacía entre subtítulos

		return '\n'.join(lineas).strip()

	def guardar_srt(self, subtitulos: List[Subtitulo], ruta_salida: str) -> bool:
		"""
		Guarda subtítulos en archivo SRT.

		Args:
			subtitulos: Lista de Subtitulo
			ruta_salida: Ruta donde guardar

		Returns:
			True si tuvo éxito
		"""
		try:
			contenido = self.generar_srt(subtitulos)

			Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
			with open(ruta_salida, 'w', encoding='utf-8') as f:
				f.write(contenido)

			return True
		except Exception as e:
			logger.warning("Error guardando SRT: %s", e)
			return False

	def generar_txt(self, subtitulos: List[Subtitulo]) -> str:
		"""
		Genera una transcripción en texto plano.

		Args:
			subtitulos: Lista de Subtitulo

		Returns:
			Cadena con transcripción
		"""
		textos = [sub.texto.replace('\n', ' ') for sub in subtitulos]
		return ' '.join(textos)

	def guardar_txt(self, subtitulos: List[Subtitulo], ruta_salida: str) -> bool:
		"""
		Guarda transcripción en archivo TXT.

		Args:
			subtitulos: Lista de Subtitulo
			ruta_salida: Ruta donde guardar

		Returns:
			True si tuvo éxito
		"""
		try:
			contenido = self.generar_txt(subtitulos)

			Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
			with open(ruta_salida, 'w', encoding='utf-8') as f:
				f.write(contenido)

			return True
		except Exception as e:
			logger.warning("Error guardando TXT: %s", e)
			return False

	# ========================================================================
	# ESTADÍSTICAS
	# ========================================================================

	def obtener_estadisticas(self, subtitulos: List[Subtitulo]) -> dict:
		"""Calcula estadísticas sobre los subtítulos"""
		if not subtitulos:
			return {
				'total_subtitulos': 0,
				'total_palabras': 0,
				'total_caracteres': 0,
				'duracion_total_ms': 0,
				'promedio_duracion_ms': 0,
				'promedio_palabras_por_sub': 0,
			}

		total_palabras = sum(sub.contar_palabras() for sub in subtitulos)
		total_caracteres = sum(len(sub.texto) for sub in subtitulos)
		duracion_total = sum(sub.obtener_duracion_ms() for sub in subtitulos)

		return {
			'total_subtitulos': len(subtitulos),
			'total_palabras': total_palabras,
			'total_caracteres': total_caracteres,
			'duracion_total_ms': duracion_total,
			'promedio_duracion_ms': duracion_total // len(subtitulos) if subtitulos else 0,
			'promedio_palabras_por_sub': total_palabras // len(subtitulos) if subtitulos else 0,
		}
