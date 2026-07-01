"""Queue management with thread-safe operations and EventBus integration.

Persistence guarantees:
- Atomic writes via tmp + os.replace
- Crash recovery: PROCESSING items revert to PENDING on load
- Throttled saves (2s debounce) to avoid IO storms
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core import get_logger, get_bus as get_event_bus, read_json, write_json

logger = get_logger("queue")

_SAVE_DEBOUNCE_S = 2.0


class ProcessingState(Enum):
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class QueueEntry:
    id: str
    ruta: str
    state: ProcessingState = ProcessingState.PENDING
    progress: float = 0.0
    stage: str = ""
    error: Optional[str] = None
    output_path: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(ruta: str) -> "QueueEntry":
        import uuid
        now = datetime.now().isoformat()
        return QueueEntry(
            id=uuid.uuid4().hex[:12],
            ruta=ruta,
            created_at=now,
            updated_at=now,
        )


class QueueManager:
    """Thread-safe queue with atomic JSON persistence and EventBus events."""

    def __init__(self, path: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        self._items: Dict[str, QueueEntry] = {}
        self._order: List[str] = []
        self._current: Optional[str] = None
        self._dirty = False
        self._last_save_time = 0.0
        self._save_timer: Optional[threading.Timer] = None

        if path:
            self._path = Path(path)
        else:
            from ..core.paths import get_user_data_dir
            self._path = get_user_data_dir() / "queue.json"
        self._tmp_path = self._path.with_suffix(".json.tmp")

        self._bus = get_event_bus()
        self._load()

    # ---- persistence ----

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = read_json(self._path)
            with self._lock:
                for item_data in data.get("items", []):
                    item = self._deserialize(item_data)
                    self._items[item.id] = item
                    self._order.append(item.id)
                self._current = data.get("current_id")
            # Crash recovery: PROCESSING → PENDING
            recovered = 0
            for entry in self._items.values():
                if entry.state == ProcessingState.PROCESSING:
                    entry.state = ProcessingState.PENDING
                    entry.error = "Interrupted (crash recovery)"
                    entry.progress = 0.0
                    recovered += 1
            if recovered:
                logger.warning("Crash recovery: %d items reset from PROCESSING to PENDING", recovered)
                self._mark_dirty()
                self.save()
            logger.info("Loaded %d queue items", len(self._order))
        except Exception as e:
            logger.warning("Failed to load queue: %s", e)

    def save(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            data = {
                "items": [self._serialize(it) for it in self._items.values()],
                "order": self._order,
                "current_id": self._current,
            }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._tmp_path
            write_json(tmp, data)
            tmp.replace(self._path)
            with self._lock:
                self._dirty = False
                self._last_save_time = time.monotonic()
        except Exception as e:
            logger.warning("Failed to save queue: %s", e)

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _debounced_save(self) -> None:
        """Schedule a save with 2s debounce. Cancels previous pending save."""
        with self._lock:
            if self._save_timer and self._save_timer.is_alive():
                self._save_timer.cancel()
            self._save_timer = threading.Timer(_SAVE_DEBOUNCE_S, self.save)
            self._save_timer.daemon = True
            self._save_timer.start()

    @staticmethod
    def _serialize(entry: QueueEntry) -> Dict:
        d = asdict(entry)
        d["state"] = entry.state.name
        return d

    @staticmethod
    def _deserialize(d: Dict) -> QueueEntry:
        d["state"] = ProcessingState[d.get("state", "PENDING")]
        if "entrada" in d:
            d["ruta"] = d.pop("entrada")
        return QueueEntry(**d)

    # ---- CRUD ----

    def add(self, ruta: str) -> QueueEntry:
        entry = QueueEntry.new(ruta)
        with self._lock:
            self._items[entry.id] = entry
            self._order.append(entry.id)
            self._mark_dirty()
        self._debounced_save()
        self._bus.emit("queue.added", {"id": entry.id, "ruta": ruta})
        logger.info("Queue added: %s", ruta)
        return entry

    def remove(self, item_id: str) -> bool:
        with self._lock:
            if item_id not in self._items:
                return False
            del self._items[item_id]
            self._order = [i for i in self._order if i != item_id]
            if self._current == item_id:
                self._current = None
            self._mark_dirty()
        self._debounced_save()
        self._bus.emit("queue.removed", {"id": item_id})
        return True

    def get(self, item_id: str) -> Optional[QueueEntry]:
        with self._lock:
            return self._items.get(item_id)

    def update(self, item_id: str, **kwargs: Any) -> bool:
        with self._lock:
            entry = self._items.get(item_id)
            if not entry:
                return False
            for k, v in kwargs.items():
                if hasattr(entry, k):
                    setattr(entry, k, v)
            entry.updated_at = datetime.now().isoformat()
            self._mark_dirty()
        self._debounced_save()
        return True

    def set_state(self, item_id: str, state: ProcessingState, error: Optional[str] = None) -> bool:
        with self._lock:
            entry = self._items.get(item_id)
            if not entry:
                return False
            entry.state = state
            entry.updated_at = datetime.now().isoformat()
            if error:
                entry.error = error
            if state == ProcessingState.PROCESSING:
                self._current = item_id
            elif state in (ProcessingState.COMPLETED, ProcessingState.FAILED, ProcessingState.CANCELLED):
                if self._current == item_id:
                    self._current = None
                entry.progress = 100.0 if state == ProcessingState.COMPLETED else entry.progress
            self._mark_dirty()
        self._debounced_save()
        self._bus.emit("queue.state_changed", {
            "id": item_id, "state": state.name, "error": error,
        })
        return True

    def set_progress(self, item_id: str, progress: float, stage: str = "") -> None:
        with self._lock:
            entry = self._items.get(item_id)
            if not entry:
                return
            old_progress = entry.progress
            old_stage = entry.stage
            entry.progress = progress
            if stage:
                entry.stage = stage
            entry.updated_at = datetime.now().isoformat()
            # Save on stage change or >=5% progress change
            if stage and stage != old_stage:
                self._mark_dirty()
            elif progress - old_progress >= 5.0:
                self._mark_dirty()
        if self._dirty:
            self._debounced_save()
        self._bus.emit("queue.progress", {
            "id": item_id, "progress": progress, "stage": stage,
        })

    # ---- query ----

    def list_all(self) -> List[QueueEntry]:
        with self._lock:
            return [self._items[i] for i in self._order if i in self._items]

    def list_pending(self) -> List[QueueEntry]:
        with self._lock:
            return [self._items[i] for i in self._order
                    if i in self._items and self._items[i].state == ProcessingState.PENDING]

    def next_pending(self) -> Optional[QueueEntry]:
        with self._lock:
            # Do not return next if there is an active item
            if self._current and self._current in self._items:
                cur = self._items[self._current]
                if cur.state == ProcessingState.PROCESSING:
                    return None
            for i in self._order:
                entry = self._items.get(i)
                if entry and entry.state == ProcessingState.PENDING:
                    return entry
            return None

    def clear_completed(self) -> int:
        cleared = 0
        with self._lock:
            to_remove = [i for i, e in self._items.items()
                         if e.state in (ProcessingState.COMPLETED, ProcessingState.FAILED, ProcessingState.CANCELLED)]
            for i in to_remove:
                del self._items[i]
                self._order = [o for o in self._order if o != i]
                cleared += 1
            self._mark_dirty()
        if cleared:
            self._debounced_save()
        return cleared

    def clear_all(self) -> int:
        """Remove all items regardless of state."""
        with self._lock:
            n = len(self._items)
            self._items.clear()
            self._order.clear()
            self._current = None
            self._mark_dirty()
        if n:
            self._debounced_save()
        return n

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def current(self) -> Optional[QueueEntry]:
        with self._lock:
            if self._current and self._current in self._items:
                return self._items[self._current]
            return None

    def has_pending(self) -> bool:
        with self._lock:
            return any(e.state == ProcessingState.PENDING for e in self._items.values())

    def requeue_failed(self) -> int:
        count = 0
        with self._lock:
            for entry in self._items.values():
                if entry.state in (ProcessingState.FAILED, ProcessingState.CANCELLED):
                    entry.state = ProcessingState.PENDING
                    entry.error = None
                    entry.progress = 0.0
                    entry.stage = ""
                    count += 1
            self._mark_dirty()
        if count:
            self._debounced_save()
        return count

    def cancel(self, item_id: Optional[str] = None) -> bool:
        if item_id:
            return self.set_state(item_id, ProcessingState.CANCELLED)
        with self._lock:
            if self._current:
                entry = self._items.get(self._current)
                if entry:
                    entry.state = ProcessingState.CANCELLED
                    entry.updated_at = datetime.now().isoformat()
                    self._mark_dirty()
                    self._debounced_save()
                    self._bus.emit("queue.state_changed", {
                        "id": self._current, "state": "CANCELLED",
                    })
                    return True
            return False

    def close(self) -> None:
        """Flush pending save and cancel debounce timer."""
        with self._lock:
            if self._save_timer and self._save_timer.is_alive():
                self._save_timer.cancel()
                self._save_timer = None
        self.save()
