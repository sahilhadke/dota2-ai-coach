import logging
from threading import Lock

from .differ import StateDiffer
from .event import EventBus
from .advisor import ItemAdvisor
from .server_log import ServerLog
from .rules.base import BaseRule
from .rules import DEFAULT_RULES

logger = logging.getLogger(__name__)


class EventEngine:
    """Wires StateDiffer + Rules + EventBus + ItemAdvisor together.

    Call `process(state_dict)` on every incoming game state.
    The engine diffs against the previous state, evaluates all rules,
    and triggers LLM item recommendations on economy thresholds.
    """

    def __init__(
        self,
        bus: EventBus | None = None,
        rules: list[BaseRule] | None = None,
        advisor: ItemAdvisor | None = None,
    ):
        self._differ = StateDiffer()
        self._bus = bus or EventBus()
        self._rules = rules or [cls() for cls in DEFAULT_RULES]
        self._advisor = advisor
        self._server_log = ServerLog()
        self._current_state: dict = {}
        self._player_context: dict | None = None
        self._lock = Lock()

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def advisor(self) -> ItemAdvisor | None:
        return self._advisor

    @property
    def server_log(self) -> ServerLog:
        return self._server_log

    @property
    def player_context(self) -> dict | None:
        with self._lock:
            return self._player_context.copy() if self._player_context else None

    @player_context.setter
    def player_context(self, ctx: dict) -> None:
        with self._lock:
            self._player_context = ctx

    @property
    def current_state(self) -> dict:
        with self._lock:
            return self._current_state.copy()

    def process(self, state: dict) -> None:
        delta = self._differ.diff(state)

        with self._lock:
            self._current_state = state

        triggered_economy = False

        for rule in self._rules:
            try:
                events = rule.evaluate(state, delta)
                if events:
                    self._bus.fire_all(events)
                    if any(e.type == "economy_threshold" for e in events):
                        triggered_economy = True
            except Exception:
                logger.exception("Rule %s failed", rule.__class__.__name__)

        if triggered_economy and self._advisor is not None:
            self._advisor.recommend(state, player_context=self.player_context)
