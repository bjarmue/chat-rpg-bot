import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import database
from game_data import ITEMS

STORY_DIR = os.path.join(os.path.dirname(__file__), "data", "story")
DEFAULT_TZ = "Europe/Berlin"


def now(tz_name: str | None = None) -> datetime:
    return datetime.now(ZoneInfo(tz_name or DEFAULT_TZ))


def current_door(dt: datetime | None = None) -> int:
    dt = dt or now()
    if dt.month != 12:
        return 0
    return min(24, dt.day)


def door_unlocked(door: int, dt: datetime | None = None) -> bool:
    dt = dt or now()
    return dt.month == 12 and dt.day >= door


def load_door(door: int) -> dict | None:
    path = os.path.join(STORY_DIR, f"door_{door:02d}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def item_line(item_key: str, qty: int = 1) -> str:
    item = ITEMS[item_key]
    suffix = f" ×{qty}" if qty > 1 else ""
    return f"{item['emoji']} **{item['name']}**{suffix} ({item['rarity']})"


async def player_stats(guild_id: int, user_id: int) -> dict | None:
    from game_data import attack_value, base_stats, defense_value, max_hp

    player = await database.get_player(guild_id, user_id)
    if not player:
        return None
    stats = base_stats(player["race"], player["class"])
    growth = list(stats.keys())
    for level in range(1, player["level"]):
        stats[growth[level % len(growth)]] += 1
    weapon = ITEMS.get(player["weapon"]) if player["weapon"] else None
    armor = ITEMS.get(player["armor"]) if player["armor"] else None
    return {
        "player": player,
        "stats": stats,
        "atk": attack_value(player["level"], stats, weapon["atk"] if weapon else 0),
        "def": defense_value(stats, armor["def"] if armor else 0),
        "max_hp": max_hp(player["level"]),
        "weapon": weapon,
        "armor": armor,
    }
