"""Stage interface for the MADRAC-SUBS v3 pipeline."""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from ...core import get_logger

StageCallback = Callable[[str, float, Optional[str]], None]
"""Callback signature: (id_item, progress_0_100, fase_optional)"""


@dataclass
class StageResult:
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class PipelineStage:
    """Base class for pipeline stages.

    Each stage is a self-contained processing step.
    Override ``execute()`` and optionally ``rollback()``.
    """

    name: str = "base"

    def __init__(self) -> None:
        self.logger = get_logger(f"stage.{self.name}")

    def execute(
        self,
        item_id: str,
        context: Dict[str, Any],
        on_progress: StageCallback,
        on_log: Callable[[str], None],
        should_cancel: Callable[[], bool],
    ) -> StageResult:
        """Execute this stage.

        Args:
            item_id: Current queue item ID.
            context: Shared dict with accumulated stage outputs.
            on_progress: Progress callback (id, pct_0_100, fase).
            on_log: Log message callback.
            should_cancel: Returns True if processing was cancelled.

        Returns:
            StageResult with success status and optional data.
        """
        raise NotImplementedError

    def rollback(self, context: Dict[str, Any]) -> None:
        """Clean up after a failed stage (e.g. remove temp files)."""

    def cleanup(self) -> None:
        """Release heavy resources between items.

        Called by PipelineWorker after each item finishes.
        Override to free models, GPU memory, file handles, etc.
        """
