import copy


class StateDiffer:
    """Computes a flat delta between consecutive game state dicts.

    The delta is a dict of dotted paths to {"old": ..., "new": ...} entries,
    e.g. {"player.gold": {"old": 800, "new": 1200}}.
    Only leaf values that actually changed are included.
    """

    def __init__(self):
        self._previous: dict | None = None

    def diff(self, state: dict) -> dict:
        if self._previous is None:
            self._previous = copy.deepcopy(state)
            return {}

        delta = {}
        self._deep_diff(self._previous, state, "", delta)
        self._previous = copy.deepcopy(state)
        return delta

    def _deep_diff(self, old: object, new: object, prefix: str, delta: dict) -> None:
        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old.keys()) | set(new.keys())
            for key in all_keys:
                path = f"{prefix}.{key}" if prefix else key
                old_val = old.get(key)
                new_val = new.get(key)
                if old_val is None and new_val is not None:
                    delta[path] = {"old": None, "new": new_val}
                elif old_val is not None and new_val is None:
                    delta[path] = {"old": old_val, "new": None}
                else:
                    self._deep_diff(old_val, new_val, path, delta)
        elif isinstance(old, list) and isinstance(new, list):
            if old != new:
                delta[prefix] = {"old": old, "new": new}
        else:
            if old != new:
                delta[prefix] = {"old": old, "new": new}
