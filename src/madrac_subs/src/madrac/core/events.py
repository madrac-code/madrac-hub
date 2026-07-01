"""Simple thread-safe event bus for pipeline-UI communication."""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("madrac.events")


class EventBus:
    """Pub/sub event bus. Thread-safe. One instance shared across the app."""

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            subs = self._subscribers.get(event_type, [])
            if callback in subs:
                subs.remove(callback)

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            subs = list(self._subscribers.get(event_type, []))
        for cb in subs:
            try:
                cb(data or {})
            except Exception as e:
                logger.exception("EventBus callback error [%s]: %s", event_type, e)

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()


_SHARED_BUS: Optional[EventBus] = None
_BUS_LOCK = threading.Lock()


def get_bus() -> EventBus:
    global _SHARED_BUS
    if _SHARED_BUS is None:
        with _BUS_LOCK:
            if _SHARED_BUS is None:
                _SHARED_BUS = EventBus()
    return _SHARED_BUS
