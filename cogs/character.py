import discord
from discord import app_commands
from discord.ext import commands

import database
from game_data import CLASSES, RACES, RARITY_COLORS, max_hp, xp_for_level
from utils import item_line, player_stats


class CharacterView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.race: str | None = None
        self.class_key: str | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Das ist nicht dein Charakterbogen! 😄", ephemeral=True)
            return False
        return True

    @discord.ui.select(placeholder="Wähle deine Rasse", options=[])
    async def race_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.race = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(placeholder="Wähle deine Klasse", options=[])
    async def class_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.class_key = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Charakter erschaffen", style=discord.ButtonStyle.success, emoji="❄️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.race or not self.class_key:
            await interaction.response.send_message("Bitte wähle zuerst Rasse und Klasse aus.", ephemeral=True)
            return
        guild_id = interaction.guild_id
        existing = await database.get_player(guild_id, self.author_id)
        if existing:
            await interaction.response.send_message("Du hast bereits einen Charakter! Nutze /profil.", ephemeral=True)
            return
        race = RACES[self.race]
        cls = CLASSES[self.class_key]
        name = interaction.user.display_name
        await database.execute(
            "INSERT INTO players (guild_id, user_id, name, race, class, level, xp, hp) VALUES (?, ?, ?, ?, ?, 1, 0, ?)",
            (guild_id, self.author_id, name, self.race, self.class_key, max_hp(1)),
        )
        await database.execute(
            "INSERT OR IGNORE INTO decisions (guild_id, user_id, door, choice) VALUES (?, ?, 1, 'charakter')",
            (guild_id, self.author_id),
        )
        embed = discord.Embed(
            title=f"{race['emoji']} {cls['emoji']} Willkommen in Frosthaven, {name}!",
            description=(
                f"**Rasse:** {race['name']}\n**Klasse:** {cls['name']}\n"
                f"**Spezialfähigkeit:** {cls['ability']['name']} — {cls['ability']['desc']}\n\n"
                f"{race['desc']}\n\nDein Abenteuer beginnt, wenn die erste Tür des Adventskalenders geöffnet wird. ❄️"
            ),
            color=RARITY_COLORS["selten"],
        )
        await interaction.response.edit_message(embed=embed, view=None)
        for child in self.children:
            child.disabled = True


def _select_options(source: dict) -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"{data['name']} — {data['desc']}", value=key, emoji=data["emoji"])
        for key, data in source.items()
    ]


class CharacterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="charakter", description="Erstelle deinen Charakter für das Advents-RPG")
    async def charakter(self, interaction: discord.Interaction):
        existing = await database.get_player(interaction.guild_id, interaction.user.id)
        if existing:
            await interaction.response.send_message(
                "Du hast bereits einen Charakter. Schau mit /profil nach!", ephemeral=True
            )
            return
        view = CharacterView(interaction.user.id)
        view.race_select.options = _select_options(RACES)
        view.class_select.options = _select_options(CLASSES)
        embed = discord.Embed(
            title="❄️ Erschaffe deinen Helden",
            description=(
                "Die 24 Türen von Frosthaven öffnen sich — doch wer seid ihr, die sie betreten?\n\n"
                "Wähle **Rasse** und **Klasse**. Deine Wahl bestimmt deine Werte (Stärke, Verteidigung, "
                "Geschick, Magie) und deine Spezialfähigkeit in den Kämpfen."
            ),
            color=0x5DADE2,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="profil", description="Zeige dein Abenteurer-Profil")
    @app_commands.describe(member="Profil eines anderen Mitglieds ansehen")
    async def profil(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        info = await player_stats(interaction.guild_id, target.id)
        if not info:
            await interaction.response.send_message(
                f"{target.display_name} hat noch keinen Charakter. Starte mit /charakter!", ephemeral=True
            )
            return
        player = info["player"]
        race = RACES[player["race"]]
        cls = CLASSES[player["class"]]
        needed = xp_for_level(player["level"])
        bar = "█" * int(10 * player["xp"] / needed) + "░" * (10 - int(10 * player["xp"] / needed))
        stats = info["stats"]
        equip = []
        equip.append(info["weapon"]["name"] if info["weapon"] else "— keine Waffe —")
        equip.append(info["armor"]["name"] if info["armor"] else "— keine Rüstung —")
        embed = discord.Embed(
            title=f"{race['emoji']} {cls['emoji']} {player['name']}",
            description=f"Level {player['level']} · {race['name']} · {cls['name']}",
            color=RARITY_COLORS["selten"],
        )
        embed.add_field(
            name="❤️ Lebenspunkte",
            value=f"{player['hp']} / {info['max_hp']}",
            inline=True,
        )
        embed.add_field(name="⚡ Erfahrung", value=f"{bar}\n{player['xp']} / {needed} XP", inline=True)
        embed.add_field(
            name="💪 Werte",
            value=(
                f"Stärke: **{stats['staerke']}** · Verteidigung: **{stats['verteidigung']}**\n"
                f"Geschick: **{stats['geschick']}** · Magie: **{stats['magie']}**\n"
                f"Angriffswert: **{info['atk']}** · Schutz: **{info['def']}**"
            ),
            inline=False,
        )
        embed.add_field(name="🗡️ Ausrüstung", value="\n".join(equip), inline=False)
        embed.add_field(
            name="✨ Fähigkeit",
            value=f"**{cls['ability']['name']}** — {cls['ability']['desc']}",
            inline=False,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bestenliste", description="Die heldenhaftesten Abenteurer von Frosthaven")
    async def bestenliste(self, interaction: discord.Interaction):
        rows = await database.fetchall(
            "SELECT name, race, class, level, xp FROM players WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10",
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message(
                "Noch keine Helden in Frosthaven! Erstelle deinen Charakter mit /charakter.", ephemeral=True
            )
            return
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, row in enumerate(rows):
            prefix = medals[i] if i < 3 else f"**{i + 1}.**"
            lines.append(
                f"{prefix} {RACES[row['race']]['emoji']}{CLASSES[row['class']]['emoji']} "
                f"**{row['name']}** — Level {row['level']} ({row['xp']} XP)"
            )
        embed = discord.Embed(
            title="🏆 Bestenliste von Frosthaven", description="\n".join(lines), color=0xF1C40F
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CharacterCog(bot))
