import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

import database
from utils import current_door, now

log = logging.getLogger("advent-rpg")


class CalendarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduler.start()

    def cog_unload(self):
        self.scheduler.cancel()

    @tasks.loop(minutes=1)
    async def scheduler(self):
        today_door = current_door()
        today = now().date().isoformat()
        for guild in self.bot.guilds:
            channel_id = await database.get_channel_id(guild.id)
            if not channel_id:
                continue
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue
            story_door = await database.get_story_door(guild.id)
            fresh = story_door is None
            if fresh:
                story_door = 1
                await database.set_story_door(guild.id, 1)
            played_door = story_door - 1
            fight = await database.get_fight_state(guild.id, played_door) if played_door >= 1 else None
            fight_open = bool(fight and fight["alive"] and fight["day"] != today)
            if not today_door and not fight_open:
                continue
            day_row = await database.get_day_state(guild.id, today)
            morning_done = bool(day_row and day_row["morning_done"])
            afternoon_done = bool(day_row and day_row["afternoon_done"])
            local = now()
            if local.hour >= 9 and not morning_done:
                try:
                    story_cog = self.bot.get_cog("StoryCog")
                    if fight_open and story_door > 24:
                        await story_cog.post_retreat(channel, played_door, fight, None)
                        await database.set_day_state(guild.id, today, morning_done=1, retreat_door=played_door)
                    elif fight_open and story_door == 24:
                        await database.mark_fight_dead(guild.id, played_door)
                        await database.set_story_door(guild.id, 25)
                        await story_cog.post_morning(channel, 24, skipped=[], abandoned=played_door)
                        await database.set_day_state(guild.id, today, morning_done=1)
                        story_door = 25
                    elif fight_open:
                        await database.mark_fight_dead(guild.id, story_door)
                        await database.set_story_door(guild.id, story_door + 1)
                        await story_cog.post_retreat(channel, played_door, fight, story_door)
                        await database.set_day_state(guild.id, today, morning_done=1, retreat_door=played_door)
                        story_door += 1
                    elif story_door > 24:
                        await database.set_day_state(guild.id, today, morning_done=1)
                    else:
                        if fresh:
                            new_door = 1
                            skipped = []
                        else:
                            days_left = max(0, 25 - today_door)
                            doors_left = 24 - story_door + 1
                            advance = 1 + max(0, doors_left - days_left)
                            skipped = list(range(story_door + 1, min(25, story_door + advance)))
                            new_door = story_door + advance
                        for n in skipped:
                            await database.mark_fight_dead(guild.id, n)
                        await database.set_story_door(guild.id, new_door)
                        await story_cog.post_morning(channel, story_door, skipped=skipped)
                        await database.set_day_state(guild.id, today, morning_done=1)
                        story_door = new_door
                except Exception:
                    log.exception("Morgenpost fehlgeschlagen (Tür %s)", story_door)
            if local.hour >= 15 and not afternoon_done:
                try:
                    day_row = await database.get_day_state(guild.id, today)
                    retreat_door = day_row["retreat_door"] if day_row else None
                    if retreat_door or story_door <= 24:
                        afternoon_cog = self.bot.get_cog("AfternoonCog")
                        target = retreat_door if retreat_door else max(1, story_door - 1)
                        await afternoon_cog.post_afternoon(channel, target, easier=bool(retreat_door))
                        await database.set_day_state(guild.id, today, afternoon_done=1)
                except Exception:
                    log.exception("Nachmittagspost fehlgeschlagen (Tür %s)", story_door)

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
        story_door = await database.get_story_door(interaction.guild_id) or 0
        lines = []
        for n in range(1, 25):
            if n > story_door:
                lines.append(f"🔒 Tür {n}")
                continue
            decision = await database.fetchone(
                "SELECT choice FROM decisions WHERE guild_id = ? AND user_id = ? AND door = ?",
                (interaction.guild_id, interaction.user.id, n),
            )
            morning = "✅" if decision or n < story_door else "📖"
            activity = await database.fetchone(
                "SELECT 1 AS x FROM riddle_answers WHERE guild_id = ? AND user_id = ? AND door = ? "
                "UNION SELECT 1 AS x FROM fight_actions WHERE guild_id = ? AND user_id = ? AND door = ? "
                "UNION SELECT 1 AS x FROM votes WHERE guild_id = ? AND user_id = ? AND door = ?",
                (interaction.guild_id, interaction.user.id, n,
                 interaction.guild_id, interaction.user.id, n,
                 interaction.guild_id, interaction.user.id, n),
            )
            afternoon = "✅" if activity or n < story_door else "⚔️"
            marker = "🎁" if n == story_door else "🔓"
            lines.append(f"{marker} Tür {n}: {morning} {afternoon}")
        embed = discord.Embed(
            title="🎄 Dein Adventskalender",
            description="\n".join(lines[:12]),
            color=0xC0392B,
        )
        embed.add_field(name="Türen 13–24", value="\n".join(lines[12:]), inline=False)
        embed.set_footer(text="📖 = Geschichte wartet · ⚔️ = Abenteuer wartet · ✅ = erledigt/gestaucht · Die Geschichte staucht sich bei Bedarf, damit Tür 24 am 24.12. kommt")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="heute", description="Was wartet heute hinter der Tür?")
    async def heute(self, interaction: discord.Interaction):
        door = await database.get_story_door(interaction.guild_id)
        if not door:
            if not current_door():
                await interaction.response.send_message(
                    "❄️ Der Advent hat noch nicht begonnen — die erste Tür öffnet sich am 1. Dezember!",
                    ephemeral=True,
                )
                return
            door = 1
        story_cog = self.bot.get_cog("StoryCog")
        await story_cog.catch_up(interaction, door)


async def setup(bot: commands.Bot):
    await bot.add_cog(CalendarCog(bot))
