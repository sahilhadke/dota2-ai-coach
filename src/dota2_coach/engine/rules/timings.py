from dota2_coach.engine.event import Event
from .base import BaseRule

HEADS_UP = 20  # seconds before the event to notify


def _periodic_times(start: int, interval: int, max_time: int = 5400) -> list[int]:
    """Generate spawn times for periodic events."""
    times = []
    t = start
    while t <= max_time:
        times.append(t)
        t += interval
    return times


# ── Timing definitions ──────────────────────────────────────────────────────
# Each entry: (clock_time_seconds, event_type, message)

_RUNE_TIMINGS: list[tuple[int, str, str]] = []

# Bounty runes: 0:00, then every 3 minutes
for t in _periodic_times(0, 180):
    _RUNE_TIMINGS.append((t, "bounty_rune", f"Bounty Runes spawning at {t // 60}:{t % 60:02d}"))

# Water runes: 2:00 and 4:00 only
_RUNE_TIMINGS.append((120, "water_rune", "Water Runes spawning at 2:00"))
_RUNE_TIMINGS.append((240, "water_rune", "Water Runes spawning at 4:00"))

# Power runes: 6:00, then every 2 minutes
for t in _periodic_times(360, 120):
    _RUNE_TIMINGS.append((t, "power_rune", f"Power Rune spawning at {t // 60}:{t % 60:02d}"))

# Wisdom runes: 7:00, then every 7 minutes
for t in _periodic_times(420, 420):
    _RUNE_TIMINGS.append((t, "wisdom_rune", f"Wisdom Runes spawning at {t // 60}:{t % 60:02d}"))


_OBJECTIVE_TIMINGS: list[tuple[int, str, str]] = []

# Lotus pools: every 3 minutes starting at 3:00
for t in _periodic_times(180, 180):
    _OBJECTIVE_TIMINGS.append((t, "lotus_pool", f"Healing Lotus spawning at {t // 60}:{t % 60:02d}"))

# Tormentor initial spawn at 20:00
_OBJECTIVE_TIMINGS.append((1200, "tormentor", "Tormentors spawning at 20:00"))

# Day/Night cycle: night at 5:00, 15:00, 25:00...; day at 10:00, 20:00, 30:00...
for t in _periodic_times(300, 600):
    _OBJECTIVE_TIMINGS.append((t, "day_night", f"Nighttime begins at {t // 60}:{t % 60:02d} — Roshan moves to Dire pit"))
for t in _periodic_times(600, 600):
    _OBJECTIVE_TIMINGS.append((t, "day_night", f"Daytime begins at {t // 60}:{t % 60:02d} — Roshan moves to Radiant pit"))


_CREEP_TIMINGS: list[tuple[int, str, str]] = []

# Siege creeps: 5:00, then every 5 minutes
for t in _periodic_times(300, 300):
    _CREEP_TIMINGS.append((t, "siege_creep", f"Siege Creep wave at {t // 60}:{t % 60:02d}"))

# Neutral creeps initial spawn
_CREEP_TIMINGS.append((60, "neutral_creep", "Neutral Creeps spawning at 1:00"))


_NEUTRAL_ITEM_TIMINGS: list[tuple[int, str, str]] = [
    (420, "neutral_item_tier", "Tier 1 Neutral Items now available (7:00)"),
    (1020, "neutral_item_tier", "Tier 2 Neutral Items now available (17:00)"),
    (1620, "neutral_item_tier", "Tier 3 Neutral Items now available (27:00)"),
    (2220, "neutral_item_tier", "Tier 4 Neutral Items now available (37:00)"),
    (3600, "neutral_item_tier", "Tier 5 Neutral Items now available (60:00)"),
]

_MISC_TIMINGS: list[tuple[int, str, str]] = [
    (240, "courier_upgrade", "Flying Courier upgrade at 4:00"),
]

ALL_TIMINGS = _RUNE_TIMINGS + _OBJECTIVE_TIMINGS + _CREEP_TIMINGS + _NEUTRAL_ITEM_TIMINGS + _MISC_TIMINGS


class TimingsRule(BaseRule):
    """Fires heads-up notifications before key game timings.

    Uses clock_time from the game state to alert ~20 seconds before
    rune spawns, objective timings, creep waves, and neutral item tiers.
    Each timing fires exactly once per occurrence.
    """

    def __init__(self, heads_up: int = HEADS_UP):
        self._heads_up = heads_up
        self._alerted: set[tuple[int, str]] = set()
        self._prev_clock: int | None = None

    def evaluate(self, state: dict, delta: dict) -> list[Event]:
        events = []
        map_data = state.get("map")
        if not map_data:
            return events

        clock = map_data.get("clock_time")
        if clock is None:
            return events

        game_state = map_data.get("state", "")
        if game_state != "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS":
            return events

        # Reset alerts if clock went backwards (new game)
        if self._prev_clock is not None and clock < self._prev_clock - 5:
            self._alerted.clear()
        self._prev_clock = clock

        for spawn_time, event_type, message in ALL_TIMINGS:
            alert_key = (spawn_time, event_type)
            if alert_key in self._alerted:
                continue

            notify_at = spawn_time - self._heads_up
            if clock >= notify_at:
                self._alerted.add(alert_key)

                if clock < spawn_time:
                    secs_left = spawn_time - clock
                    display_msg = f"[{secs_left}s] {message}"
                else:
                    display_msg = message

                events.append(Event(
                    type=event_type,
                    message=display_msg,
                    data={
                        "spawn_time": spawn_time,
                        "spawn_clock": f"{spawn_time // 60}:{spawn_time % 60:02d}",
                        "clock_time": clock,
                    },
                ))

        return events
