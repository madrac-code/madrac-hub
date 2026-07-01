"""Pipeline metrics collection — lightweight, no external deps."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageMetrics:
    stage: str
    duration_s: float
    item_id: str
    ram_delta_mb: float = 0.0


@dataclass
class PipelineMetrics:
    stages: List[StageMetrics] = field(default_factory=list)
    total_s: float = 0.0
    audio_duration_s: float = 0.0
    rtf: float = 0.0
    ram_peak_mb: float = 0.0
    item_id: str = ""


class MetricsCollector:
    """Collects per-stage metrics during pipeline execution."""

    def __init__(self) -> None:
        self.reset()

    def reset(self, item_id: str = "") -> None:
        self._stages: List[StageMetrics] = []
        self._current_stage: Optional[str] = None
        self._current_start: float = 0.0
        self._ram_at_start: float = 0.0
        self._ram_peak: float = 0.0
        self._item_id = item_id

    def stage_start(self, stage: str) -> None:
        self._current_stage = stage
        self._current_start = time.perf_counter()
        self._ram_at_start = _get_rss_mb()

    def stage_end(self) -> None:
        if self._current_stage is None:
            return
        duration = time.perf_counter() - self._current_start
        ram_now = _get_rss_mb()
        delta = ram_now - self._ram_at_start
        if ram_now > self._ram_peak:
            self._ram_peak = ram_now
        self._stages.append(StageMetrics(
            stage=self._current_stage,
            duration_s=duration,
            item_id=self._item_id,
            ram_delta_mb=round(delta, 1),
        ))
        self._current_stage = None

    def build(self, audio_duration_s: float = 0.0) -> PipelineMetrics:
        total = sum(s.duration_s for s in self._stages)
        return PipelineMetrics(
            stages=list(self._stages),
            total_s=round(total, 3),
            audio_duration_s=audio_duration_s,
            rtf=round(total / audio_duration_s, 3) if audio_duration_s > 0 else 0.0,
            ram_peak_mb=round(self._ram_peak, 1),
            item_id=self._item_id,
        )

    def format_log(self, metrics: PipelineMetrics) -> str:
        parts = []
        for s in metrics.stages:
            parts.append(f"{s.stage}: {s.duration_s:.1f}s")
        parts.append(f"total: {metrics.total_s:.1f}s")
        if metrics.rtf:
            parts.append(f"rtf: {metrics.rtf:.2f}x")
        if metrics.ram_peak_mb:
            parts.append(f"ram_peak: {metrics.ram_peak_mb:.0f}MB")
        return " | ".join(parts)

    def to_dict(self, metrics: PipelineMetrics) -> Dict[str, Any]:
        return {
            "item_id": metrics.item_id,
            "total_s": metrics.total_s,
            "audio_duration_s": metrics.audio_duration_s,
            "rtf": metrics.rtf,
            "ram_peak_mb": metrics.ram_peak_mb,
            "stages": [
                {"stage": s.stage, "duration_s": s.duration_s, "ram_delta_mb": s.ram_delta_mb}
                for s in metrics.stages
            ],
        }


def _get_rss_mb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1_048_576
    except Exception:
        return 0.0
