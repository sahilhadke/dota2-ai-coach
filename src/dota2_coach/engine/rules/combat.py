from dota2_coach.engine.event import Event
from .base import BaseRule


class CombatRule(BaseRule):
    """Fires when HP drops below a threshold and usable active items are available.

    Checks inventory for items with can_cast=True and charges > 0.
    Has a cooldown so it doesn't spam every tick while low HP.
    """

    def __init__(self, hp_threshold: int = 20, cooldown_seconds: float = 10.0):
        self._hp_threshold = hp_threshold
        self._cooldown = cooldown_seconds
        self._last_alert_time: float = 0

    def evaluate(self, state: dict, delta: dict) -> list[Event]:
        events = []
        hero = state.get("hero")
        if not hero:
            return events

        hp_pct = hero.get("health_percent")
        if hp_pct is None or hp_pct > self._hp_threshold:
            return events

        if not hero.get("alive", True):
            return events

        import time
        now = time.time()
        if now - self._last_alert_time < self._cooldown:
            return events

        usable_items = self._find_usable_items(hero.get("inventory") or [])
        if not usable_items:
            return events

        item_names = [i["name"] for i in usable_items]
        self._last_alert_time = now
        events.append(Event(
            type="combat_alert",
            message=f"HP at {hp_pct}%! Use: {', '.join(item_names)}",
            data={
                "health_percent": hp_pct,
                "usable_items": usable_items,
                "hero_name": hero.get("name"),
            },
        ))
        return events

    def _find_usable_items(self, inventory: list[dict]) -> list[dict]:
        usable = []
        for item in inventory:
            if not item or not item.get("name"):
                continue
            if item.get("can_cast") and item.get("charges", 0) > 0:
                usable.append(item)
        return usable
