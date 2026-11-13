import discord
from discord.ext import commands

import database
from game_data import max_hp
from utils import load_door


class ChoiceView(discord.ui.View):
    def __init__(self, cog: "StoryCog", door: int, choices: list[dict]):
        super().__init__(timeout=None)
        self.cog = cog
        self.door = door
        for choice in choices[:5]:
            self.add_item(ChoiceButton(choice))


class ChoiceButton(discord.ui.Button):
    def __init__(self, choice: dict):
        super().__init__(label=choice["label"][:80], style=discord.ButtonStyle.primary, emoji=choice.get("emoji", "❯"))
        self.choice = choice

    async def callback(self, interaction: discord.Interaction):
        cog: StoryCog = self.view.cog
        await cog.handle_choice(interaction, self.view.door, self.choice)


class StoryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def restore_party(self, guild_id: int):
        rows = await database.fetchall(
            "SELECT user_id, level FROM players WHERE guild_id = ?", (guild_id,)
        )
        for row in rows:
            await database.execute(
                "UPDATE players SET hp = ? WHERE guild_id = ? AND user_id = ?",
                (max_hp(row["level"]), guild_id, row["user_id"]),
            )
        await database.execute(
            "UPDATE fight_actions SET actions = 0, ability_used = 0 WHERE guild_id = ?",
            (guild_id,),
        )

    async def post_morning(self, channel: discord.TextChannel, door: int, skipped: list[int] | None = None, abandoned: int | None = None):
        await self.restore_party(channel.guild.id)
        if door > 1:
            afternoon_cog = self.bot.get_cog("AfternoonCog")
            if afternoon_cog:
                await afternoon_cog.resolve_interaction(channel, door - 1)
        data = load_door(door)
        if not data:
            return
        morning = data["morning"]
        embed = discord.Embed(
            title=f"🚪 Tür {door} · {data.get('title', 'Frosthaven')}",
            description=morning["text"],
            color=0x2E86C1,
        )
        if skipped:
            summary = []
            for n in skipped:
                skipped_data = load_door(n)
                title = skipped_data.get("title", "?") if skipped_data else "?"
                summary.append(f"**Tür {n} · {title}** — unterwegs gestaucht: die Gruppe meisterte diesen Abschnitt im Vorbeiziehen.")
            embed.add_field(name="⏩ Unterwegs gestaucht", value="\n".join(summary), inline=False)
        if abandoned:
            abandoned_data = load_door(abandoned)
            boss = abandoned_data.get("afternoon", {}).get("name", "der Gegner") if abandoned_data else "der Gegner"
            embed.add_field(
                name="🏃 Zurückgelassen",
                value=f"**{boss}** (Tür {abandoned}) wurde im Sturm zurückgelassen, damit ihr das Weihnachtsfest erreicht — manche Kämpfe bleiben eben ungeschlagen.",
                inline=False,
            )
        embed.set_footer(text="Morgengruß aus Frosthaven · Alle Helden erwachen mit frischen Kräften (volle LP und Aktionen)")
        if door == 1:
            embed.add_field(
                name="🎄 Tür 1: Erschaffe deinen Helden",
                value="Nutze **/charakter**, um Rasse und Klasse zu wählen. Danach wartet hier Tür 2 auf dich!",
                inline=False,
            )
            await channel.send(embed=embed)
            return
        choices = morning.get("choices", [])
        if choices:
            embed.add_field(
                name="Was tust du?",
                value="Entscheide dich per Knopfdruck — deine Wahl prägt dein eigenes Schicksal in der Geschichte.",
                inline=False,
            )
        await channel.send(embed=embed, view=ChoiceView(self, door, choices))

    async def post_retreat(self, channel: discord.TextChannel, door: int, fight, skipped_door: int | None):
        await self.restore_party(channel.guild.id)
        data = load_door(door)
        boss = data.get("afternoon", {}).get("name", "der Gegner") if data else "der Gegner"
        custom = data.get("morning", {}).get("retreat_text") if data else None
        text = custom or (
            f"**{boss}** war stärker als gedacht — die Gruppe zieht sich in ein sicheres Lager zurück. "
            "Am Feuer werden Wunden verbunden, Pläne geschmiedet und Mut getankt. "
            "Am Nachmittag folgt der zweite Anlauf: Ihr seid ausgeruht, und der Gegner ist angeschlagen."
        )
        embed = discord.Embed(
            title=f"🚪 Tür {door} · Rückzug und Neuformierung",
            description=text,
            color=0x5D6D7E,
        )
        if skipped_door:
            skipped_data = load_door(skipped_door)
            title = skipped_data.get("title", "?") if skipped_data else "?"
            embed.add_field(
                name="⏩ Kapitel gestaucht",
                value=f"**Tür {skipped_door} · {title}** — dieser Abschnitt wird unterwegs im Schnelldurchlauf gemeistert, damit das Fest am 24. Dezember steigt.",
                inline=False,
            )
        embed.set_footer(text="Ruhetag · LP und Aktionen sind voll · Der zweite Anlauf wartet am Nachmittag")
        await channel.send(embed=embed)

    async def handle_choice(self, interaction: discord.Interaction, door: int, choice: dict):
        guild_id = interaction.guild_id
        player = await database.get_player(guild_id, interaction.user.id)
        if not player:
            await interaction.response.send_message(
                "Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True
            )
            return
        existing = await database.fetchone(
            "SELECT choice FROM decisions WHERE guild_id = ? AND user_id = ? AND door = ?",
            (guild_id, interaction.user.id, door),
        )
        if existing:
            await interaction.response.send_message(
                "Du hast diese Tür bereits geöffnet — dein Schicksal ist entschieden. ❄️",
                ephemeral=True,
            )
            return
        await database.execute(
            "INSERT INTO decisions (guild_id, user_id, door, choice) VALUES (?, ?, ?, ?)",
            (guild_id, interaction.user.id, door, choice["key"]),
        )
        lines = [choice.get("text", "Dein Weg nimmt Gestalt an.")]
        xp = choice.get("xp", 15)
        leveled = await self.grant_xp(player, xp)
        lines.append(f"✨ +{xp} XP")
        for item_key in choice.get("loot", []):
            qty = 1
            await database.add_item(guild_id, interaction.user.id, item_key, qty)
            lines.append(f"🎁 Loot: {self.item_line(item_key, qty)}")
        if leveled:
            lines.append("🎉 **Stufenaufstieg!** Deine LP und Werte wachsen — siehe /profil.")
        embed = discord.Embed(
            title=f" Tür {door} · Deine Entscheidung",
            description="\n".join(lines),
            color=0x48C9B0,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def grant_xp(self, player, xp: int) -> bool:
        from game_data import xp_for_level

        total = player["xp"] + xp
        level = player["level"]
        leveled = False
        while total >= xp_for_level(level):
            total -= xp_for_level(level)
            level += 1
            leveled = True
        await database.execute(
            "UPDATE players SET xp = ?, level = ?, hp = MIN(hp + ?, ?) WHERE guild_id = ? AND user_id = ?",
            (total, level, 10 if leveled else 0, max_hp(level), player["guild_id"], player["user_id"]),
        )
        return leveled

    def item_line(self, item_key: str, qty: int = 1) -> str:
        from game_data import ITEMS
        from utils import item_line

        return item_line(item_key, qty)

    async def catch_up(self, interaction: discord.Interaction, door: int):
        data = load_door(door)
        if not data:
            await interaction.response.send_message(
                f"Tür {door} ist noch nicht beschrieben — die Chronisten von Frosthaven schreiben noch. ✍️",
                ephemeral=True,
            )
            return
        player = await database.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            await interaction.response.send_message(
                "Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True
            )
            return
        existing = await database.fetchone(
            "SELECT choice FROM decisions WHERE guild_id = ? AND user_id = ? AND door = ?",
            (interaction.guild_id, interaction.user.id, door),
        )
        if existing:
            await interaction.response.send_message(
                f"Du hast Tür {door} bereits hinter dir. Nutze /kalender für deinen Überblick. ❄️",
                ephemeral=True,
            )
            return
        if door == 1:
            await interaction.response.send_message(
                "Tür 1 ist die Charaktererschaffung — nutze **/charakter**!", ephemeral=True
            )
            return
        morning = data["morning"]
        embed = discord.Embed(
            title=f"🚪 Tür {door} · {data.get('title', 'Frosthaven')}",
            description=morning["text"],
            color=0x2E86C1,
        )
        choices = morning.get("choices", [])
        if choices:
            await interaction.response.send_message(
                embed=embed, view=ChoiceView(self, door, choices), ephemeral=True
            )
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StoryCog(bot))
