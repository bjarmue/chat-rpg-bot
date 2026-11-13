import random

STAT_KEYS = ("staerke", "verteidigung", "geschick", "magie")

RACES = {
    "mensch": {
        "name": "Mensch", "emoji": "🧑",
        "desc": "Anpassungsfähig und mutig. +1 auf alle Werte.",
        "bonus": {"staerke": 1, "verteidigung": 1, "geschick": 1, "magie": 1},
    },
    "elf": {
        "name": "Elf", "emoji": "🧝",
        "desc": "Alt und weise, vertraut mit alter Magie. +2 Magie, +1 Geschick.",
        "bonus": {"magie": 2, "geschick": 1},
    },
    "zwerg": {
        "name": "Zwerg", "emoji": "🧔",
        "desc": "Zäh wie Granit, Freund des Schmiedehandwerks. +2 Stärke, +2 Verteidigung, -1 Geschick.",
        "bonus": {"staerke": 2, "verteidigung": 2, "geschick": -1},
    },
    "wichtel": {
        "name": "Wichtel", "emoji": "🧚",
        "desc": "Flink und listig, Werkstattgeschöpf des Weihnachtsmanns. +2 Geschick, +1 Magie, -1 Stärke.",
        "bonus": {"geschick": 2, "magie": 1, "staerke": -1},
    },
    "schneewesen": {
        "name": "Schneewesen", "emoji": "⛄",
        "desc": "Aus ewigem Schnee geformt, frostig und standhaft. +2 Verteidigung, +1 Magie, -1 Stärke.",
        "bonus": {"verteidigung": 2, "magie": 1, "staerke": -1},
    },
}

CLASSES = {
    "krieger": {
        "name": "Krieger", "emoji": "⚔️",
        "desc": "Meister der Klinge. +3 Stärke, +2 Verteidigung.",
        "bonus": {"staerke": 3, "verteidigung": 2},
        "ability": {"name": "Wuchtschlag", "desc": "Ein schwerer Schlag, der die Verteidigung des Gegners durchbricht.", "dmg_mult": 2.0, "ignore_def": True},
    },
    "magier": {
        "name": "Magier", "emoji": "🔮",
        "desc": "Beherrscher von Frost und Flammen. +3 Magie, +1 Geschick.",
        "bonus": {"magie": 3, "geschick": 1},
        "ability": {"name": "Frostfunke", "desc": "Ein Eiszauber, der den Gegner schwer trifft.", "dmg_mult": 1.8},
    },
    "waldlaeufer": {
        "name": "Waldläufer", "emoji": "🏹",
        "desc": "Scharfäugiger Jäger der verschneiten Wälder. +3 Geschick, +1 Stärke.",
        "bonus": {"geschick": 3, "staerke": 1},
        "ability": {"name": "Präziser Schuss", "desc": "Ein gezielter Schuss mit hoher Chance auf kritischen Schaden.", "dmg_mult": 1.6, "crit_bonus": 30},
    },
    "kleriker": {
        "name": "Kleriker", "emoji": "✨",
        "desc": "Geweihter des Winterlichts. +2 Magie, +2 Verteidigung.",
        "bonus": {"magie": 2, "verteidigung": 2},
        "ability": {"name": "Lichtsegen", "desc": "Heilt dich um einen Teil deiner maximalen Lebenspunkte.", "heal_frac": 0.35},
    },
}

BASE_STAT = 5

ITEMS = {
    "holzschwert": {"name": "Holzschwert", "emoji": "🗡️", "type": "waffe", "rarity": "gewöhnlich", "atk": 2, "desc": "Ein einfaches Übungsschwert der Wichtelwerkstatt."},
    "lebkuchenklinge": {"name": "Lebkuchenklinge", "emoji": "🍪", "type": "waffe", "rarity": "selten", "atk": 4, "desc": "Hart gebacken und scharf gezuckert."},
    "eiszapfenlanze": {"name": "Eiszapfenlanze", "emoji": "🧊", "type": "waffe", "rarity": "episch", "atk": 6, "desc": "Gefrorenes Eis, das niemals schmilzt."},
    "sternenschwert": {"name": "Sternenschwert", "emoji": "🌟", "type": "waffe", "rarity": "legendär", "atk": 9, "desc": "Geschmiedet aus einem Splitter des Weihnachtssterns."},
    "wollmantel": {"name": "Wollmantel", "emoji": "🧥", "type": "rüstung", "rarity": "gewöhnlich", "def": 2, "desc": "Warm und zuverlässig gegen den Winter."},
    "zinnpanzer": {"name": "Zinnpanzer", "emoji": "🛡️", "type": "rüstung", "rarity": "selten", "def": 4, "desc": "Aus den Spielzeugsoldaten der Werkstatt gegossen."},
    "polarfuchspelz": {"name": "Polarfuchspelz", "emoji": "🦊", "type": "rüstung", "rarity": "episch", "def": 6, "desc": "Vom Polarfuchs geschenkt, wärmt bei jedem Sturm."},
    "glanzruestung": {"name": "Glanzrüstung", "emoji": "✨", "type": "rüstung", "rarity": "legendär", "def": 9, "desc": "Strahlt im Mondlicht wie frisch gefallener Schnee."},
    "plaetzchen": {"name": "Zimtplätzchen", "emoji": "🍪", "type": "verbrauch", "rarity": "gewöhnlich", "heal": 15, "desc": "Heilt 15 LP. Du isst es in einem Happen."},
    "heiltrank": {"name": "Glühweintrank", "emoji": "🍷", "type": "verbrauch", "rarity": "selten", "heal": 30, "desc": "Heilt 30 LP. Würzig und wärmend."},
    "goldglocke": {"name": "Goldene Glocke", "emoji": "🔔", "type": "trophy", "rarity": "selten", "desc": "Klingt leise, wenn Weihnachten naht."},
    "kristallkugel": {"name": "Kristallkugel", "emoji": "🔮", "type": "trophy", "rarity": "episch", "desc": "Zeigt Funken ferner Wintermärchen."},
    "sternsplitter": {"name": "Sternsplitter", "emoji": "💫", "type": "trophy", "rarity": "legendär", "desc": "Ein Funke des Weihnachtssterns selbst."},
}

RARITY_ORDER = {"gewöhnlich": 0, "selten": 1, "episch": 2, "legendär": 3}

RARITY_COLORS = {
    "gewöhnlich": 0x9E9E9E,
    "selten": 0x3498DB,
    "episch": 0x9B59B6,
    "legendär": 0xF1C40F,
}


def xp_for_level(level: int) -> int:
    return 80 + (level - 1) * 40


def base_stats(race_key: str, class_key: str) -> dict:
    stats = {key: BASE_STAT for key in STAT_KEYS}
    for source in (RACES[race_key]["bonus"], CLASSES[class_key]["bonus"]):
        for key, value in source.items():
            stats[key] += value
    return stats


def max_hp(level: int) -> int:
    return 40 + level * 10


def attack_value(level: int, stats: dict, weapon_atk: int) -> int:
    return stats["staerke"] + weapon_atk + level


def defense_value(stats: dict, armor_def: int) -> int:
    return stats["verteidigung"] + armor_def


def roll_damage(atk: int, target_def: int, geschick: int, crit_bonus: int = 0) -> tuple[int, bool]:
    crit_chance = min(35, 5 + geschick // 2 + crit_bonus)
    crit = random.randint(1, 100) <= crit_chance
    dmg = int(atk * random.uniform(0.85, 1.15)) - target_def // 2
    if crit:
        dmg = int(dmg * 1.6)
    return max(1, dmg), crit


def boss_damage(boss_atk: int, defense: int) -> int:
    dmg = int(boss_atk * random.uniform(0.8, 1.2)) - defense // 2
    return max(1, dmg)
