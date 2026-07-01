"""Pipeline package for MADRAC-SUBS v3."""

from .models import (
    detectar_modelos_instalados,
    hay_modelos_whisper,
    hay_modelos_marian,
    descargar_modelo_whisper,
    descargar_modelo_marian,
    eliminar_modelo,
    limpiar_modelos_no_seleccionados,
    formatear_tamano,
    primer_inicio_pendiente,
)
from .queue import QueueManager, QueueEntry, ProcessingState
from .stages import (
    PipelineStage, StageResult,
    AudioExtractionStage, TranscribeStage,
    TranslateStage, FormatStage, MuxStage, CommunityStage,
    MetricsCollector, StageMetrics, PipelineMetrics,
)
from .worker import PipelineWorker, MAX_ACTIVE_PIPELINES

__all__ = [
    "detectar_modelos_instalados",
    "hay_modelos_whisper",
    "hay_modelos_marian",
    "descargar_modelo_whisper",
    "descargar_modelo_marian",
    "eliminar_modelo",
    "limpiar_modelos_no_seleccionados",
    "formatear_tamano",
    "primer_inicio_pendiente",
    "QueueManager", "QueueEntry", "ProcessingState",
    "PipelineStage", "StageResult",
    "AudioExtractionStage", "TranscribeStage",
    "TranslateStage", "FormatStage", "MuxStage", "CommunityStage",
    "MetricsCollector", "StageMetrics", "PipelineMetrics",
    "PipelineWorker", "MAX_ACTIVE_PIPELINES",
]
