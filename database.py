import aiosqlite
import discord
from game_data import max_hp

DB_PATH = "advent_rpg.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    tz TEXT DEFAULT 'Europe/Berlin'
);
CREATE TABLE IF NOT EXISTS players (
    guild_id INTEGER,
    user_id INTEGER,
    name TEXT,
    race TEXT,
    class TEXT,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    hp INTEGER,
    weapon TEXT,
    armor TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    item TEXT,
    qty INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS decisions (
    guild_id INTEGER,
    user_id INTEGER,
    door INTEGER,
    choice TEXT,
    PRIMARY KEY (guild_id, user_id, door)
);
CREATE TABLE IF NOT EXISTS fight_actions (
    guild_id INTEGER,
    door INTEGER,
    user_id INTEGER,
    actions INTEGER DEFAULT 0,
    ability_used INTEGER DEFAULT 0,
    day TEXT,
    PRIMARY KEY (guild_id, door, user_id)
);
CREATE TABLE IF NOT EXISTS riddle_answers (
    guild_id INTEGER,
    door INTEGER,
    user_id INTEGER,
    correct INTEGER,
    PRIMARY KEY (guild_id, door, user_id)
);
CREATE TABLE IF NOT EXISTS votes (
    guild_id INTEGER,
    door INTEGER,
    user_id INTEGER,
    choice TEXT,
    PRIMARY KEY (guild_id, door, user_id)
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    from_user INTEGER,
    to_user INTEGER,
    offer_item TEXT,
    offer_qty INTEGER,
    request_item TEXT,
    request_qty INTEGER,
    status TEXT DEFAULT 'offen',
    message_id INTEGER
);
CREATE TABLE IF NOT EXISTS resolutions (
    guild_id INTEGER,
    door INTEGER,
    choice TEXT,
    PRIMARY KEY (guild_id, door)
);
CREATE TABLE IF NOT EXISTS schedule (
    guild_id INTEGER,
    door INTEGER,
    morning_done INTEGER DEFAULT 0,
    afternoon_done INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, door)
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        try:
            await db.execute("ALTER TABLE fight_actions ADD COLUMN day TEXT")
        except aiosqlite.OperationalError:
            pass
        await db.commit()


async def fetchone(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return await cur.fetchone()


async def fetchall(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return await cur.fetchall()


async def execute(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()


async def get_channel_id(guild_id: int):
    row = await fetchone("SELECT channel_id FROM config WHERE guild_id = ?", (guild_id,))
    return row["channel_id"] if row else None


async def set_channel_id(guild_id: int, channel_id: int):
    await execute(
        "INSERT INTO config (guild_id, channel_id) VALUES (?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id",
        (guild_id, channel_id),
    )


async def get_player(guild_id: int, user_id: int):
    return await fetchone(
        "SELECT * FROM players WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
    )


async def add_item(guild_id: int, user_id: int, item: str, qty: int = 1):
    row = await fetchone(
        "SELECT id, qty FROM inventory WHERE guild_id = ? AND user_id = ? AND item = ?",
        (guild_id, user_id, item),
    )
    if row:
        await execute("UPDATE inventory SET qty = qty + ? WHERE id = ?", (qty, row["id"]))
    else:
        await execute(
            "INSERT INTO inventory (guild_id, user_id, item, qty) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, item, qty),
        )


async def remove_item(guild_id: int, user_id: int, item: str, qty: int = 1) -> bool:
    row = await fetchone(
        "SELECT id, qty FROM inventory WHERE guild_id = ? AND user_id = ? AND item = ?",
        (guild_id, user_id, item),
    )
    if not row or row["qty"] < qty:
        return False
    if row["qty"] == qty:
        await execute("DELETE FROM inventory WHERE id = ?", (row["id"],))
    else:
        await execute("UPDATE inventory SET qty = qty - ? WHERE id = ?", (qty, row["id"]))
    return True


async def grant_xp(player: dict, xp: int):
    from game_data import xp_for_level

    total = player["xp"] + xp
    level = player["level"]
    leveled = False
    while total >= xp_for_level(level):
        total -= xp_for_level(level)
        level += 1
        leveled = True
    await execute(
        "UPDATE players SET xp = ?, level = ?, hp = MIN(hp + ?, ?) WHERE guild_id = ? AND user_id = ?",
        (total, level, 10 if leveled else 0, max_hp(level), player["guild_id"], player["user_id"]),
    )
    return leveled


def level_embed(player: dict, old_level: int):
    from game_data import CLASSES, RACES

    cls = CLASSES[player["class"]]
    race = RACES[player["race"]]
    embed = discord.Embed(
        title="🎉 Stufenaufstieg!",
        description=(
            f"{race['emoji']} {cls['emoji']} **{player['name']}** ist von "
            f"**Level {old_level}** auf **Level {player['level']}** aufgestiegen!\n"
            f"❤️ Maximale LP: {max_hp(player['level'])}"
        ),
        color=0xF1C40F,
    )
    return embed
