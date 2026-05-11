"""Thread-safe progress event distribution for warm-up runs."""

from __future__ import annotations

import queue
import threading
from typing import Optional

from .schemas import ProgressEvent


class ProgressEmitter:
    """Publish progress events to web subscribers and in-memory history."""

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue] = []
        self._history: list[ProgressEvent] = []
        self._history_limit = 500
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def emit(self, event: ProgressEvent) -> None:
        print(f"[{event.event_type.value}] {event.message}")
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit :]
            for q in self._subscribers:
                q.put_nowait(event)

    def get_history(self, limit: Optional[int] = None) -> list[ProgressEvent]:
        with self._lock:
            history = list(self._history)
        if limit is not None and limit > 0:
            return history[-limit:]
        return history
