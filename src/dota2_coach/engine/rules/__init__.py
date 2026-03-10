from .economy import EconomyRule
from .combat import CombatRule
from .map_awareness import MapAwarenessRule
from .timings import TimingsRule

DEFAULT_RULES = [EconomyRule, CombatRule, MapAwarenessRule, TimingsRule]
