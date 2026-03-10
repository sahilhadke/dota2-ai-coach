import json
import logging
import os
import re
import time
from threading import Lock, Thread

from google import genai

from dota2_coach.engine.server_log import ServerLog

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "item_recommendation.md")
FULL_BUILD_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "full_item_build.md")

SUPPORT_HEROES = {
    "crystal_maiden", "lion", "witch_doctor", "shadow_shaman", "dazzle",
    "warlock", "lich", "jakiro", "ogre_magi", "vengefulspirit",
    "winter_wyvern", "disruptor", "oracle", "grimstroke", "hoodwink",
    "snapfire", "chen", "enchantress", "keeper_of_the_light", "io",
    "treant", "undying", "silencer", "shadow_demon", "bane",
    "ancient_apparition", "rubick", "earth_spirit", "phoenix",
    "tusk", "bounty_hunter", "spirit_breaker", "clockwerk",
    "elder_titan", "abaddon", "omniknight", "purist_thunderwrath",
    "skywrath_mage", "cm", "venomancer", "aa", "sd",
    "nyx_assassin", "dark_willow", "marci", "muerta",
}

OFFLANE_HEROES = {
    "axe", "tidehunter", "centaur", "bristleback", "mars",
    "legion_commander", "slardar", "underlord", "sand_king",
    "dark_seer", "beastmaster", "brewmaster", "pangolier",
    "primal_beast", "night_stalker", "doom_bringer", "doom",
    "batrider", "timbersaw", "shredder", "necrolyte", "necrophos",
    "enigma", "magnus", "razor", "viper", "venomancer",
}

CONSUMABLES = {
    "item_tango", "item_clarity", "item_flask", "item_enchanted_mango",
    "item_faerie_fire", "item_tpscroll", "item_ward_observer",
    "item_ward_sentry", "item_dust", "item_smoke_of_deceit",
    "item_tome_of_knowledge", "item_bottle", "item_empty_bottle",
}


def _infer_role(hero_name: str) -> str:
    short = hero_name.replace("npc_dota_hero_", "")
    if short in SUPPORT_HEROES:
        return "support"
    if short in OFFLANE_HEROES:
        return "offlane"
    return "carry"


def _format_clock(seconds: int) -> str:
    m, s = divmod(abs(seconds), 60)
    return f"{m}:{s:02d}"


def _extract_items(hero: dict) -> list[str]:
    items = []
    for slot_type in ("inventory", "neutral"):
        for item in (hero.get(slot_type) or []):
            if not item:
                continue
            name = item.get("name", "")
            if name and name not in CONSUMABLES:
                items.append(name.replace("item_", ""))
    return items


TEAM_NUM_TO_NAME = {2: "radiant", 3: "dire"}


def _extract_enemies(state: dict) -> list[str]:
    minimap = state.get("minimap")
    my_team = (state.get("player") or {}).get("team_name", "").lower()
    enemies = set()

    if minimap:
        for _key, entry in minimap.items():
            if not isinstance(entry, dict):
                continue
            unitname = entry.get("unitname", "")
            if not unitname.startswith("npc_dota_hero_"):
                continue
            raw_team = entry.get("team", "")
            entry_team = TEAM_NUM_TO_NAME.get(raw_team, str(raw_team)).lower()
            if entry_team and entry_team != my_team:
                enemies.add(unitname.replace("npc_dota_hero_", ""))

    return sorted(enemies) if enemies else ["unknown"]


def _build_prompt(template: str, state: dict, player_context: dict | None = None) -> str:
    hero = state.get("hero") or {}
    player = state.get("player") or {}
    map_data = state.get("map") or {}

    hero_name = (hero.get("name") or "unknown").replace("npc_dota_hero_", "")
    items = _extract_items(hero)
    enemies = _extract_enemies(state)

    if player_context and player_context.get("position"):
        role = player_context["position"]
    else:
        role = _infer_role(hero.get("name", ""))

    lane = (player_context or {}).get("lane", "unknown")
    lane_ally = (player_context or {}).get("lane_ally", "unknown")
    lane_enemies_list = (player_context or {}).get("lane_enemies", [])
    lane_enemies = ", ".join(lane_enemies_list) if lane_enemies_list else "unknown"

    return template.format(
        hero_name=hero_name,
        level=hero.get("level", 1),
        role=role,
        lane=lane,
        gold=player.get("gold", 0),
        items=", ".join(items) if items else "none",
        clock=_format_clock(map_data.get("clock_time", 0)),
        lane_ally=lane_ally,
        lane_enemies=lane_enemies,
        enemy_list=", ".join(enemies),
        radiant_score=map_data.get("radiant_score", 0),
        dire_score=map_data.get("dire_score", 0),
    )


def _parse_response(text: str) -> dict | None:
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    logger.warning("Failed to parse Gemini response: %s", text[:200])
    return None


class ItemAdvisor:
    """Calls Gemini to get item recommendations based on game state."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash",
                 server_log: ServerLog | None = None):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._lock = Lock()
        self._latest: dict | None = None
        self._latest_full: dict | None = None
        self._in_flight = False
        self._full_in_flight = False
        self._slog = server_log

        with open(PROMPT_PATH, "r") as f:
            self._template = f.read()
        with open(FULL_BUILD_PROMPT_PATH, "r") as f:
            self._full_template = f.read()

    @property
    def latest_recommendation(self) -> dict | None:
        with self._lock:
            return self._latest

    @property
    def latest_full_build(self) -> dict | None:
        with self._lock:
            return self._latest_full

    def recommend(self, state: dict, player_context: dict | None = None) -> None:
        """Trigger a recommendation in a background thread. Non-blocking."""
        with self._lock:
            if self._in_flight:
                return
            self._in_flight = True

        thread = Thread(target=self._run, args=(state, player_context), daemon=True)
        thread.start()

    def _log(self, level: str, msg: str) -> None:
        if self._slog:
            getattr(self._slog, level)("LLM", msg)

    def _run(self, state: dict, player_context: dict | None = None) -> None:
        try:
            prompt = _build_prompt(self._template, state, player_context=player_context)
            self._log("info", "Requesting item recommendation from Gemini...")
            logger.info("Requesting item recommendation from Gemini...")

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
            )
            self._log("info", "Gemini response received, parsing...")
            parsed = _parse_response(response.text)

            if parsed:
                parsed["timestamp"] = time.time()
                parsed["gold_at_request"] = (state.get("player") or {}).get("gold", 0)
                parsed["hero"] = (state.get("hero") or {}).get("name", "").replace("npc_dota_hero_", "")

                with self._lock:
                    self._latest = parsed

                items_str = ", ".join(i["name"] for i in parsed.get("items", []))
                self._log("info", f"Recommendation ready: {items_str}")
                logger.info("Item recommendation: %s", items_str)
            else:
                self._log("warn", "Failed to parse Gemini response")
                logger.warning("Could not parse recommendation from Gemini")
        except Exception as exc:
            self._log("error", f"Gemini API call failed: {exc}")
            logger.exception("Gemini API call failed")
        finally:
            with self._lock:
                self._in_flight = False

    def full_recommend(self, state: dict, player_context: dict | None = None) -> None:
        """Trigger a full 5-item build recommendation. Non-blocking."""
        with self._lock:
            if self._full_in_flight:
                return
            self._full_in_flight = True

        thread = Thread(target=self._run_full, args=(state, player_context), daemon=True)
        thread.start()

    def _run_full(self, state: dict, player_context: dict | None = None) -> None:
        try:
            prompt = _build_prompt(self._full_template, state, player_context=player_context)
            self._log("info", "Requesting full item build from Gemini...")
            logger.info("Requesting full item build from Gemini...")

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
            )
            self._log("info", "Full build response received, parsing...")
            parsed = _parse_response(response.text)

            if parsed:
                parsed["timestamp"] = time.time()
                parsed["gold_at_request"] = (state.get("player") or {}).get("gold", 0)
                parsed["hero"] = (state.get("hero") or {}).get("name", "").replace("npc_dota_hero_", "")

                with self._lock:
                    self._latest_full = parsed

                items_str = ", ".join(i["name"] for i in parsed.get("items", []))
                self._log("info", f"Full build ready: {items_str}")
                logger.info("Full item build: %s", items_str)
            else:
                self._log("warn", "Failed to parse full build response")
                logger.warning("Could not parse full build from Gemini")
        except Exception as exc:
            self._log("error", f"Full build API call failed: {exc}")
            logger.exception("Gemini full-build API call failed")
        finally:
            with self._lock:
                self._full_in_flight = False
