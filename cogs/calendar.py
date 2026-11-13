import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

import database
from utils import current_door, door_unlocked, now

log = logging.getLogger("advent-rpg")


class CalendarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduler.start()

    def cog_unload(self):
        self.scheduler.cancel()

    @tasks.loop(minutes=1)
    async def scheduler(self):
        door = current_door()
        if not door:
            return
        for guild in self.bot.guilds:
            channel_id = await database.get_channel_id(guild.id)
            if not channel_id:
                continue
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue
            row = await database.fetchone(
                "SELECT morning_done, afternoon_done FROM schedule WHERE guild_id = ? AND door = ?",
                (guild.id, door),
            )
            morning_done = bool(row and row["morning_done"])
            afternoon_done = bool(row and row["afternoon_done"])
            local = now()
            if local.hour >= 9 and not morning_done:
                await database.execute(
                    "INSERT OR IGNORE INTO schedule (guild_id, door) VALUES (?, ?)", (guild.id, door)
                )
                try:
                    story_cog = self.bot.get_cog("StoryCog")
                    await story_cog.post_morning(channel, door)
                    await database.execute(
                        "UPDATE schedule SET morning_done = 1 WHERE guild_id = ? AND door = ?",
                        (guild.id, door),
                    )
                except Exception:
                    log.exception("Morgenpost fehlgeschlagen (Tür %s)", door)
            if local.hour >= 15 and not afternoon_done:
                await database.execute(
                    "INSERT OR IGNORE INTO schedule (guild_id, door) VALUES (?, ?)", (guild.id, door)
                )
                try:
                    afternoon_cog = self.bot.get_cog("AfternoonCog")
                    await afternoon_cog.post_afternoon(channel, door)
                    await database.execute(
                        "UPDATE schedule SET afternoon_done = 1 WHERE guild_id = ? AND door = ?",
                        (guild.id, door),
                    )
                except Exception:
                    log.exception("Nachmittagspost fehlgeschlagen (Tür %s)", door)

    @scheduler.before_loop
    async def wait_ready(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="kanal", description="Setzt den Kanal für die täglichen Advents-Posts")
    @app_commands.describe(kanal="Der Story-Kanal (z. B. #adventsrpg)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def kanal(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        await database.set_channel_id(interaction.guild_id, kanal.id)
        await interaction.response.send_message(
            f"✅ Die Türen von Frosthaven öffnen sich ab jetzt in {kanal.mention} — "
            "morgens um 9 Uhr die Geschichte, nachmittags um 15 Uhr Kampf, Rätsel oder Gruppenabenteuer.",
            ephemeral=True,
        )

    @app_commands.command(name="kalender", description="Zeigt deinen Adventskalender von Frosthaven")
    async def kalender(self, interaction: discord.Interaction):
        door = current_door()
        lines = []
        for n in range(1, 25):
            if not door_unlocked(n):
                lines.append(f"🔒 Tür {n}")
                continue
            decision = await database.fetchone(
                "SELECT choice FROM decisions WHERE guild_id = ? AND user_id = ? AND door = ?",
                (interaction.guild_id, interaction.user.id, n),
            )
            morning = "✅" if decision else "📖"
            activity = await database.fetchone(
                "SELECT 1 AS x FROM riddle_answers WHERE guild_id = ? AND user_id = ? AND door = ? "
                "UNION SELECT 1 AS x FROM fight_actions WHERE guild_id = ? AND user_id = ? AND door = ? "
                "UNION SELECT 1 AS x FROM votes WHERE guild_id = ? AND user_id = ? AND door = ?",
                (interaction.guild_id, interaction.user.id, n,
                 interaction.guild_id, interaction.user.id, n,
                 interaction.guild_id, interaction.user.id, n),
            )
            afternoon = "✅" if activity else "⚔️"
            marker = "🎁" if n == door else "🔓"
            lines.append(f"{marker} Tür {n}: {morning} {afternoon}")
        embed = discord.Embed(
            title="🎄 Dein Adventskalender",
            description="\n".join(lines[:12]),
            color=0xC0392B,
        )
        embed.add_field(name="Türen 13–24", value="\n".join(lines[12:]), inline=False)
        embed.set_footer(text="📖 = Geschichte wartet · ⚔️ = Abenteuer wartet · ✅ = erledigt")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="heute", description="Was wartet heute hinter der Tür?")
    async def heute(self, interaction: discord.Interaction):
        door = current_door()
        if not door:
            await interaction.response.send_message(
                "❄️ Der Advent hat noch nicht begonnen — die erste Tür öffnet sich am 1. Dezember!",
                ephemeral=True,
            )
            return
        story_cog = self.bot.get_cog("StoryCog")
        await story_cog.catch_up(interaction, door)


async def setup(bot: commands.Bot):
    await bot.add_cog(CalendarCog(bot))
