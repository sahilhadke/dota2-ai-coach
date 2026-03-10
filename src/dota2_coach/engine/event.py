import logging
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class Event:
    type: str
    message: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class EventBus:
    """Thread-safe ring buffer that stores recent events and logs them."""

    def __init__(self, max_events: int = 100):
        self._events: deque[Event] = deque(maxlen=max_events)
        self._lock = Lock()

    def fire(self, event: Event) -> None:
        with self._lock:
            self._events.append(event)
        logger.info("[%s] %s", event.type, event.message)

    def fire_all(self, events: list[Event]) -> None:
        for event in events:
            self.fire(event)

    def get_events(self, event_type: str | None = None) -> list[dict]:
        with self._lock:
            events = list(self._events)
        if event_type:
            events = [e for e in events if e.type == event_type]
        return [e.to_dict() for e in events]
