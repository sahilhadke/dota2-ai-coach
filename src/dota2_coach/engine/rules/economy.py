from dota2_coach.engine.event import Event
from .base import BaseRule


class EconomyRule(BaseRule):
    """Fires an event when total gold crosses a threshold boundary.

    Thresholds are checked in increments (default every 1000 gold).
    Each threshold fires only once as gold increases.
    """

    def __init__(self, step: int = 1000):
        self._step = step
        self._last_threshold_crossed = 0

    def evaluate(self, state: dict, delta: dict) -> list[Event]:
        events = []
        gold = (state.get("player") or {}).get("gold")
        if gold is None:
            return events

        current_threshold = (gold // self._step) * self._step

        if current_threshold > self._last_threshold_crossed and current_threshold > 0:
            events.append(Event(
                type="economy_threshold",
                message=f"Gold passed {current_threshold} (current: {gold})",
                data={
                    "gold": gold,
                    "threshold": current_threshold,
                    "gold_reliable": (state.get("player") or {}).get("gold_reliable"),
                    "gold_unreliable": (state.get("player") or {}).get("gold_unreliable"),
                },
            ))
            self._last_threshold_crossed = current_threshold

        if "player.gold" in delta:
            old_gold = delta["player.gold"]["old"]
            if old_gold is not None and gold < old_gold:
                new_threshold = (gold // self._step) * self._step
                if new_threshold < self._last_threshold_crossed:
                    self._last_threshold_crossed = new_threshold

        return events
