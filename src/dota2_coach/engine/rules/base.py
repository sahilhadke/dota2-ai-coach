from abc import ABC, abstractmethod
from dota2_coach.engine.event import Event


class BaseRule(ABC):
    @abstractmethod
    def evaluate(self, state: dict, delta: dict) -> list[Event]:
        """Return a list of events triggered by this state + delta."""
        ...
