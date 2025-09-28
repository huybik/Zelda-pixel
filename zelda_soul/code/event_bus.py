from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from enum import Enum, auto
from typing import Callable, Dict, Tuple


class GameEvent(Enum):
    ENTITY_TAKES_DAMAGE = auto()
    PLAYER_ENTERS_RADIUS = auto()
    RESOURCE_DEPLETED = auto()


EventToken = Tuple[GameEvent, str]
EventCallback = Callable[[dict], None]


class EventBus:
    """Thread-safe pub/sub event dispatcher for gameplay events."""

    def __init__(self):
        self._listeners: Dict[GameEvent, Dict[str, EventCallback]] = defaultdict(dict)
        self._lock = threading.Lock()

    def subscribe(self, event_type: GameEvent, callback: EventCallback) -> EventToken:
        token = uuid.uuid4().hex
        with self._lock:
            self._listeners[event_type][token] = callback
        return event_type, token

    def unsubscribe(self, token: EventToken) -> None:
        event_type, identifier = token
        with self._lock:
            callbacks = self._listeners.get(event_type)
            if callbacks and identifier in callbacks:
                callbacks.pop(identifier, None)

    def emit(self, event_type: GameEvent, payload: dict | None = None) -> None:
        payload = payload or {}
        callbacks: list[tuple[EventToken, EventCallback]]
        with self._lock:
            callbacks = [((event_type, token), cb) for token, cb in self._listeners.get(event_type, {}).items()]
        for token, callback in callbacks:
            try:
                callback(payload)
            except Exception as exc:  # pragma: no cover - guard against handler failure
                print(f"EventBus handler error for {event_type.name}: {exc}")


event_bus = EventBus()

