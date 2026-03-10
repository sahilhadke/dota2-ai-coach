import time
from collections import deque
from threading import Lock


class ServerLog:
    """Thread-safe ring buffer for surfacing important server events to the dashboard."""

    def __init__(self, maxlen: int = 200):
        self._entries: deque[dict] = deque(maxlen=maxlen)
        self._lock = Lock()

    def add(self, level: str, source: str, message: str) -> None:
        entry = {
            "timestamp": time.time(),
            "level": level,
            "source": source,
            "message": message,
        }
        with self._lock:
            self._entries.append(entry)

    def info(self, source: str, message: str) -> None:
        self.add("info", source, message)

    def warn(self, source: str, message: str) -> None:
        self.add("warn", source, message)

    def error(self, source: str, message: str) -> None:
        self.add("error", source, message)

    def get_entries(self, since: float = 0) -> list[dict]:
        with self._lock:
            if since:
                return [e for e in self._entries if e["timestamp"] > since]
            return list(self._entries)
