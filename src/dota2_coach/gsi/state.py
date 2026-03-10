import time
from .server import GameState, EXTRA_DATA_KEYS


def _serialize_ability(ability):
    if ability is None:
        return None
    return {
        "name": ability.name,
        "level": ability.level,
        "can_cast": ability.can_cast,
        "passive": ability.passive,
        "ability_active": ability.ability_active,
        "cooldown": ability.cooldown,
        "ultimate": ability.ultimate,
        "charges": ability.charges,
        "max_charges": ability.max_charges,
        "charge_cooldown": ability.charge_cooldown,
    }


def _serialize_item(item):
    if item is None:
        return None
    return {
        "name": item.name,
        "purchaser": item.purchaser,
        "can_cast": item.can_cast,
        "cooldown": item.cooldown,
        "passive": item.passive,
        "charges": item.charges,
    }


def _serialize_item_list(items):
    if items is None:
        return []
    return [_serialize_item(i) for i in items]


def build_game_state_dict(gs: GameState) -> dict:
    """Convert a GameState into a plain dict suitable for JSON serialization."""
    data = {"timestamp": time.time()}

    if gs.provider is not None:
        data["provider"] = {
            "name": gs.provider.name,
            "appid": gs.provider.appid,
            "version": gs.provider.version,
            "timestamp": gs.provider.timestamp,
        }

    if gs.map is not None:
        data["map"] = {
            "name": gs.map.name,
            "match_id": gs.map.match_id,
            "game_time": gs.map.game_time,
            "clock_time": gs.map.clock_time,
            "daytime": gs.map.daytime,
            "nightstalker_night": gs.map.nightstalker_night,
            "radiant_score": gs.map.radiant_score,
            "dire_score": gs.map.dire_score,
            "state": gs.map.state.name if gs.map.state else None,
            "paused": gs.map.paused,
            "custom_game_name": gs.map.custom_game_name,
            "win_team": gs.map.win_team,
            "ward_purchase_cooldown": gs.map.ward_purchase_cooldown,
        }

    if gs.player is not None:
        data["player"] = {
            "steam_id": gs.player.steam_id,
            "account_id": gs.player.account_id,
            "name": gs.player.name,
            "activity": gs.player.activity,
            "kills": gs.player.kills,
            "deaths": gs.player.deaths,
            "assists": gs.player.assists,
            "last_hits": gs.player.last_hits,
            "denies": gs.player.denies,
            "kill_streak": gs.player.kill_streak,
            "commands_issued": gs.player.commands_issued,
            "kill_list": gs.player.kill_list,
            "team_name": gs.player.team_name,
            "gold": gs.player.gold,
            "gold_reliable": gs.player.gold_reliable,
            "gold_unreliable": gs.player.gold_unreliable,
            "gold_from_hero_kills": gs.player.gold_from_hero_kills,
            "gold_from_creep_kills": gs.player.gold_from_creep_kills,
            "gold_from_income": gs.player.gold_from_income,
            "gold_from_shared": gs.player.gold_from_shared,
            "gold_per_minute": gs.player.gold_per_minute,
            "experience_per_minute": gs.player.experience_per_minute,
        }

    if gs.hero is not None:
        abilities = None
        if gs.hero.abilities is not None:
            abilities = [_serialize_ability(a) for a in gs.hero.abilities]

        data["hero"] = {
            "id": gs.hero.id,
            "name": gs.hero.name,
            "pos": {"x": gs.hero.pos[0], "y": gs.hero.pos[1]} if gs.hero.pos else None,
            "level": gs.hero.level,
            "experience": gs.hero.experience,
            "alive": gs.hero.alive,
            "respawn_seconds": gs.hero.respawn_seconds,
            "buyback_cost": gs.hero.buyback_cost,
            "buyback_cooldown": gs.hero.buyback_cooldown,
            "health": gs.hero.health,
            "max_health": gs.hero.max_health,
            "health_percent": gs.hero.health_percent,
            "mana": gs.hero.mana,
            "max_mana": gs.hero.max_mana,
            "mana_percent": gs.hero.mana_percent,
            "silenced": gs.hero.silenced,
            "stunned": gs.hero.stunned,
            "disarmed": gs.hero.disarmed,
            "magic_immune": gs.hero.magic_immune,
            "hexed": gs.hero.hexed,
            "muted": gs.hero.muted,
            "broken": gs.hero.broken,
            "aghanims_scepter": gs.hero.aghanims_scepter,
            "aghanims_shard": gs.hero.aghanims_shard,
            "smoked": gs.hero.smoked,
            "debuffed": gs.hero.debuffed,
            "talents": gs.hero.talents,
            "abilities": abilities,
            "inventory": _serialize_item_list(gs.hero.inventory),
            "stash": _serialize_item_list(gs.hero.stash),
            "teleport": _serialize_item_list(gs.hero.teleport),
            "neutral": _serialize_item_list(gs.hero.neutral),
        }

    for key in EXTRA_DATA_KEYS:
        value = gs.raw_payload.get(key)
        if value is not None:
            data[key] = value

    return data
