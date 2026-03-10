import math
import time
from dota2_coach.engine.event import Event
from .base import BaseRule

TEAM_NUM_TO_NAME = {2: "radiant", 3: "dire"}

# Approximate danger thresholds in Dota 2 world units.
# Heroes move at ~300-400 units/s, so 3000 units ≈ 8-10 seconds away.
APPROACH_RADIUS = 3500
CLOSE_RADIUS = 2000


def _dist(a: dict, b: dict) -> float:
    dx = a.get("x", 0) - b.get("x", 0)
    dy = a.get("y", 0) - b.get("y", 0)
    return math.hypot(dx, dy)


def _minimap_pos(entry: dict) -> dict:
    return {"x": entry.get("xpos", 0), "y": entry.get("ypos", 0)}


class MapAwarenessRule(BaseRule):
    """Detects enemies approaching the player's position on the minimap.

    Instead of spamming 'hero missing' for every fog entry, this rule
    tracks each enemy hero's position over time and fires alerts when:

    1. **gank_warning** – An enemy who was far away is now within the
       approach radius AND closing distance toward the player.
    2. **enemy_nearby** – An enemy enters a close-danger radius around
       the player (e.g. TP gank, smoke gank, sudden appearance).

    Both alerts have per-hero cooldowns to prevent spam.
    """

    def __init__(self, approach_cooldown: float = 25.0, nearby_cooldown: float = 30.0):
        self._approach_cd = approach_cooldown
        self._nearby_cd = nearby_cooldown

        # hero_name -> {"pos": {"x":..,"y":..}, "time": float}
        self._prev_positions: dict[str, dict] = {}
        self._approach_alerted: dict[str, float] = {}
        self._nearby_alerted: dict[str, float] = {}

    def evaluate(self, state: dict, delta: dict) -> list[Event]:
        events: list[Event] = []
        minimap = state.get("minimap")
        player = state.get("player") or {}
        hero_data = state.get("hero") or {}
        hero_pos = hero_data.get("pos")
        my_team = (player.get("team_name") or "").lower()

        if not minimap or not hero_pos or not my_team:
            return events

        now = time.time()

        for _key, entry in minimap.items():
            if not isinstance(entry, dict):
                continue
            unitname = entry.get("unitname", "")
            if not unitname.startswith("npc_dota_hero_"):
                continue
            raw_team = entry.get("team", "")
            entry_team = TEAM_NUM_TO_NAME.get(raw_team, str(raw_team)).lower()
            if not entry_team or entry_team == my_team:
                continue

            pos = _minimap_pos(entry)
            dist = _dist(pos, hero_pos)
            prev = self._prev_positions.get(unitname)
            short = unitname.replace("npc_dota_hero_", "")

            if prev:
                prev_dist = _dist(prev["pos"], hero_pos)
                closing = prev_dist - dist

                # Gank warning: enemy entered approach range and is closing in
                if (dist < APPROACH_RADIUS
                        and closing > 400
                        and prev_dist > APPROACH_RADIUS * 0.8):
                    last = self._approach_alerted.get(unitname, 0)
                    if now - last > self._approach_cd:
                        self._approach_alerted[unitname] = now
                        direction = self._direction_label(pos, hero_pos)
                        events.append(Event(
                            type="gank_warning",
                            message=(
                                f"GANK ALERT: {short} approaching from {direction}"
                                f" (~{dist:.0f} units away)"
                            ),
                            data={
                                "hero": unitname,
                                "short_name": short,
                                "distance": round(dist),
                                "direction": direction,
                            },
                        ))

            # Close-range sudden appearance (TP, smoke, blink)
            if dist < CLOSE_RADIUS:
                was_far = prev is None or _dist(prev["pos"], hero_pos) > APPROACH_RADIUS
                last = self._nearby_alerted.get(unitname, 0)
                if was_far and now - last > self._nearby_cd:
                    self._nearby_alerted[unitname] = now
                    events.append(Event(
                        type="enemy_nearby",
                        message=(
                            f"DANGER: {short} appeared near you!"
                            f" (~{dist:.0f} units)"
                        ),
                        data={
                            "hero": unitname,
                            "short_name": short,
                            "distance": round(dist),
                        },
                    ))

            self._prev_positions[unitname] = {"pos": pos, "time": now}

        return events

    @staticmethod
    def _direction_label(enemy_pos: dict, player_pos: dict) -> str:
        dx = enemy_pos["x"] - player_pos["x"]
        dy = enemy_pos["y"] - player_pos["y"]
        if abs(dx) > abs(dy):
            return "east" if dx > 0 else "west"
        return "north" if dy > 0 else "south"
