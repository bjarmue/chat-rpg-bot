import random

import discord
from discord.ext import commands

import database
from game_data import CLASSES, RARITY_COLORS, boss_damage, roll_damage
from utils import item_line, load_door, now, player_stats

ACTION_LIMIT = 5


class FightView(discord.ui.View):
    def __init__(self, cog: "AfternoonCog", door: int, fight: dict):
        super().__init__(timeout=None)
        self.cog = cog
        self.door = door
        self.fight = fight

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        player = await database.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            await interaction.response.send_message(
                "Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True
            )
            return False
        return True

    def _boss_embed(self, guild: discord.Guild) -> discord.Embed:
        fight = self.fight
        embed = discord.Embed(
            title=f"⚔️ {fight['name']}",
            description=fight.get("intro", "Der Gegner erhebt sich!"),
            color=0xC0392B,
        )
        embed.add_field(
            name="❤️ Lebenspunkte des Gegners",
            value=f"{'█' * max(0, int(10 * fight['hp'] / fight['max_hp'])) or '💀'}\n{fight['hp']} / {fight['max_hp']}",
            inline=False,
        )
        participants = fight["participants"]
        if participants:
            names = ", ".join(f"<@{uid}>" for uid in list(participants)[:15])
            embed.add_field(name="🛡️ Im Kampf", value=names, inline=False)
        embed.set_footer(text="Jeder Held: 5 Aktionen pro Tag · Fähigkeit 1× pro Tag · Block heilt dich · Der Kampf bleibt bestehen, bis der Gegner fällt!")
        return embed

    async def _finish_victory(self, channel: discord.TextChannel):
        fight = self.fight
        guild_id = channel.guild.id
        lines = [f"🎉 **{fight['name']}** ist besiegt! Die Gruppe triumphiert."]
        loot = fight.get("loot", [])
        rows = await database.fetchall(
            "SELECT user_id FROM fight_actions WHERE guild_id = ? AND door = ? AND actions > 0",
            (guild_id, self.door),
        )
        for row in rows:
            player = await database.get_player(guild_id, row["user_id"])
            if not player:
                continue
            xp = fight.get("xp", 30)
            leveled = await self.cog.grant_xp(player, xp)
            gained = [f"✨ +{xp} XP"]
            for item_key in loot:
                await database.add_item(guild_id, row["user_id"], item_key, 1)
                gained.append(f"🎁 {item_line(item_key)}")
            if leveled:
                gained.append("🎉 Stufenaufstieg!")
            lines.append(f"<@{row['user_id']}>: " + " · ".join(gained))
        for child in self.children:
            child.disabled = True
        if fight.get("message"):
            try:
                await fight["message"].edit(embed=self._boss_embed(channel.guild), view=self)
            except discord.HTTPException:
                pass
        await channel.send(embed=discord.Embed(title="🏆 Sieg!", description="\n".join(lines), color=0xF1C40F))

    async def _resolve_action(self, interaction: discord.Interaction, kind: str):
        fight = self.fight
        guild_id = interaction.guild_id
        today = now().date().isoformat()
        row = await database.fetchone(
            "SELECT actions, ability_used, day FROM fight_actions WHERE guild_id = ? AND door = ? AND user_id = ?",
            (guild_id, self.door, interaction.user.id),
        )
        stale = bool(row and row["day"] != today)
        if stale:
            await database.execute(
                "UPDATE fight_actions SET actions = 0, ability_used = 0 WHERE guild_id = ? AND door = ? AND user_id = ?",
                (guild_id, self.door, interaction.user.id),
            )
        actions = 0 if stale or not row else row["actions"]
        ability_used = False if stale or not row else bool(row["ability_used"])
        if actions >= ACTION_LIMIT:
            await interaction.response.send_message(
                "Du bist erschöpft — deine Aktionen für heute sind verbraucht. "
                "Morgen früh erwachst du mit frischen Kräften und der Kampf geht weiter! ❄️",
                ephemeral=True,
            )
            return
        info = await player_stats(guild_id, interaction.user.id)
        player = info["player"]
        if player["hp"] <= 0 and stale:
            await database.execute(
                "UPDATE players SET hp = ? WHERE guild_id = ? AND user_id = ?",
                (info["max_hp"], guild_id, interaction.user.id),
            )
            player = {**player, "hp": info["max_hp"]}
        if player["hp"] <= 0:
            await interaction.response.send_message(
                "Du liegst bewusstlos im Schnee. Ein Kleriker muss dich aufrichten — oder der morgige Tag. ❄️",
                ephemeral=True,
            )
            return
        await database.execute(
            "INSERT INTO fight_actions (guild_id, door, user_id, actions, ability_used, day) VALUES (?, ?, ?, 1, ?, ?) "
            "ON CONFLICT(guild_id, door, user_id) DO UPDATE SET actions = actions + 1, ability_used = ability_used | ?, day = ?",
            (guild_id, self.door, interaction.user.id, 1 if kind == "ability" else 0, today,
             1 if kind == "ability" else 0, today),
        )
        fight["participants"].add(interaction.user.id)
        outcome = []
        cls = CLASSES[player["class"]]
        if kind == "attack":
            dmg, crit = roll_damage(info["atk"], fight.get("def", 0), info["stats"]["geschick"])
            fight["hp"] = max(0, fight["hp"] - dmg)
            outcome.append(
                f"⚔️ <@{interaction.user.id}> greift an: **{dmg} Schaden**"
                + (" — 💥 **Kritischer Treffer!**" if crit else "")
            )
        elif kind == "ability":
            ability = cls["ability"]
            if ability.get("heal_frac"):
                heal = int(info["max_hp"] * ability["heal_frac"])
                new_hp = min(info["max_hp"], player["hp"] + heal)
                await database.execute(
                    "UPDATE players SET hp = ? WHERE guild_id = ? AND user_id = ?",
                    (new_hp, guild_id, interaction.user.id),
                )
                outcome.append(
                    f"✨ <@{interaction.user.id}> wirkt **{ability['name']}** und heilt **{heal} LP**."
                )
            else:
                dmg, crit = roll_damage(
                    int(info["atk"] * ability.get("dmg_mult", 1.5)),
                    0 if ability.get("ignore_def") else fight.get("def", 0),
                    info["stats"]["geschick"],
                    ability.get("crit_bonus", 0),
                )
                fight["hp"] = max(0, fight["hp"] - dmg)
                outcome.append(
                    f"✨ <@{interaction.user.id}> wirkt **{ability['name']}**: **{dmg} Schaden**"
                    + (" — 💥 **Kritisch!**" if crit else "")
                )
        elif kind == "block":
            heal = int(info["max_hp"] * 0.15)
            new_hp = min(info["max_hp"], player["hp"] + heal)
            await database.execute(
                "UPDATE players SET hp = ? WHERE guild_id = ? AND user_id = ?",
                (new_hp, guild_id, interaction.user.id),
            )
            outcome.append(f"🛡️ <@{interaction.user.id}> geht in Deckung und fängt **{heal} LP** auf.")
        if fight["hp"] <= 0:
            outcome.append(f"💀 **{fight['name']}** sinkt zu Boden!")
            await interaction.response.edit_message(embed=self._boss_embed(interaction.guild), view=self)
            self.fight["message"] = await interaction.original_response()
            await self._finish_victory(interaction.channel)
            return
        defended = kind == "block"
        boss_dmg = boss_damage(fight["atk"], info["def"])
        if defended:
            boss_dmg = max(1, boss_dmg // 2)
        dodge_chance = min(30, info["stats"]["geschick"])
        if random.randint(1, 100) <= dodge_chance:
            outcome.append(f"💨 <@{interaction.user.id}> weicht dem Gegenschlag aus!")
        else:
            new_hp = max(0, player["hp"] - boss_dmg)
            await database.execute(
                "UPDATE players SET hp = ? WHERE guild_id = ? AND user_id = ?",
                (new_hp, guild_id, interaction.user.id),
            )
            outcome.append(
                f"🔥 **{fight['name']}** schlägt zurück: <@{interaction.user.id}> verliert **{boss_dmg} LP**"
                + (f" ({new_hp}/{info['max_hp']})" if new_hp > 0 else " — 💀 **bewusstlos!**")
            )
        await interaction.response.edit_message(embed=self._boss_embed(interaction.guild), view=self)
        await interaction.followup.send(
            embed=discord.Embed(description="\n".join(outcome), color=RARITY_COLORS["selten"]),
            ephemeral=False,
        )

    @discord.ui.button(label="Angriff", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve_action(interaction, "attack")

    @discord.ui.button(label="Fähigkeit", style=discord.ButtonStyle.primary, emoji="✨")
    async def ability(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = await database.fetchone(
            "SELECT ability_used FROM fight_actions WHERE guild_id = ? AND door = ? AND user_id = ?",
            (interaction.guild_id, self.door, interaction.user.id),
        )
        if row and row["ability_used"]:
            await interaction.response.send_message(
                "Deine Fähigkeit ist in diesem Kampf bereits verbraucht.", ephemeral=True
            )
            return
        await self._resolve_action(interaction, "ability")

    @discord.ui.button(label="Block", style=discord.ButtonStyle.success, emoji="🛡️")
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve_action(interaction, "block")


class RiddleModal(discord.ui.Modal):
    def __init__(self, cog: "AfternoonCog", door: int, riddle: dict):
        super().__init__(title="Rätsel von Frosthaven", timeout=180)
        self.cog = cog
        self.door = door
        self.riddle = riddle
        self.answer = discord.ui.TextInput(
            label="Deine Antwort", placeholder="Schreib deine Antwort hier …", max_length=100
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.check_riddle(interaction, self.door, self.riddle, self.answer.value)


class RiddleView(discord.ui.View):
    def __init__(self, cog: "AfternoonCog", door: int, riddle: dict):
        super().__init__(timeout=None)
        self.cog = cog
        self.door = door
        self.riddle = riddle

    @discord.ui.button(label="Antwort geben", style=discord.ButtonStyle.primary, emoji="🧩")
    async def answer(self, interaction: discord.Interaction, button: discord.ui.Button):
        existing = await database.fetchone(
            "SELECT correct FROM riddle_answers WHERE guild_id = ? AND door = ? AND user_id = ?",
            (interaction.guild_id, self.door, interaction.user.id),
        )
        if existing:
            await interaction.response.send_message(
                "Du hast dieses Rätsel bereits versucht. 🧩", ephemeral=True
            )
            return
        if not await database.get_player(interaction.guild_id, interaction.user.id):
            await interaction.response.send_message(
                "Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True
            )
            return
        await interaction.response.send_modal(RiddleModal(self.cog, self.door, self.riddle))


class VoteView(discord.ui.View):
    def __init__(self, cog: "AfternoonCog", door: int, options: list[dict]):
        super().__init__(timeout=None)
        self.cog = cog
        self.door = door
        for option in options[:5]:
            self.add_item(VoteButton(option))


class VoteButton(discord.ui.Button):
    def __init__(self, option: dict):
        super().__init__(label=option["label"][:80], style=discord.ButtonStyle.secondary, emoji=option.get("emoji", "🗳️"))
        self.option = option

    async def callback(self, interaction: discord.Interaction):
        cog: AfternoonCog = self.view.cog
        await cog.handle_vote(interaction, self.view.door, self.option)


class AfternoonCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.fights: dict[tuple[int, int], dict] = {}

    async def grant_xp(self, player, xp: int) -> bool:
        from game_data import max_hp, xp_for_level

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

    async def post_afternoon(self, channel: discord.TextChannel, door: int):
        data = load_door(door)
        if not data:
            return
        afternoon = data.get("afternoon")
        if not afternoon:
            return
        kind = afternoon["type"]
        if kind == "fight":
            key = (channel.guild.id, door)
            fight = self.fights.get(key)
            if not fight:
                party_row = await database.fetchone(
                    "SELECT COUNT(*) AS c FROM players WHERE guild_id = ?", (channel.guild.id,)
                )
                scale = min(2.5, max(0.35, party_row["c"] / 3))
                boss_hp = max(20, round(afternoon["hp"] * scale))
                fight = {
                    "name": afternoon["name"],
                    "hp": boss_hp,
                    "max_hp": boss_hp,
                    "atk": afternoon.get("atk", 6),
                    "def": afternoon.get("def", 0),
                    "intro": afternoon.get("intro", ""),
                    "loot": afternoon.get("loot", []),
                    "xp": afternoon.get("xp", 30),
                    "participants": set(),
                    "message": None,
                }
                self.fights[key] = fight
            embed = discord.Embed(
                title=f"⚔️ Tür {door} · {fight['name']}",
                description=fight["intro"],
                color=0xC0392B,
            )
            embed.add_field(
                name="❤️ Lebenspunkte des Gegners",
                value=f"{'█' * 10}\n{fight['hp']} / {fight['max_hp']}",
                inline=False,
            )
            embed.set_footer(text="Jeder Held: 5 Aktionen pro Tag · Fähigkeit 1× pro Tag · Block heilt dich · Der Kampf bleibt bestehen, bis der Gegner fällt!")
            message = await channel.send(embed=embed, view=FightView(self, door, fight))
            fight["message"] = message
        elif kind == "riddle":
            embed = discord.Embed(
                title=f"🧩 Tür {door} · Rätsel",
                description=afternoon["question"],
                color=0x8E44AD,
            )
            embed.set_footer(text="Wer zuerst richtig antwortet, bekommt einen Bonus!")
            await channel.send(embed=embed, view=RiddleView(self, door, afternoon))
        elif kind == "interaction":
            embed = discord.Embed(
                title=f"🗳️ Tür {door} · {afternoon.get('title', 'Die Gruppe berät')}",
                description=afternoon["question"],
                color=0x27AE60,
            )
            embed.set_footer(text="Die Mehrheit entscheidet — das Ergebnis wird morgen früh verkündet!")
            await channel.send(embed=embed, view=VoteView(self, door, afternoon["options"]))

    async def check_riddle(self, interaction: discord.Interaction, door: int, riddle: dict, guess: str):
        guild_id = interaction.guild_id
        correct_answers = [riddle["answer"]] + riddle.get("alternatives", [])
        normalized = guess.strip().lower()
        correct = any(normalized == a.lower() for a in correct_answers)
        first = await database.fetchone(
            "SELECT COUNT(*) AS c FROM riddle_answers WHERE guild_id = ? AND door = ? AND correct = 1",
            (guild_id, door),
        )
        is_first = correct and first["c"] == 0
        await database.execute(
            "INSERT INTO riddle_answers (guild_id, door, user_id, correct) VALUES (?, ?, ?, ?)",
            (guild_id, door, interaction.user.id, 1 if correct else 0),
        )
        player = await database.get_player(guild_id, interaction.user.id)
        lines = []
        if correct:
            xp = riddle.get("xp", 40) + (20 if is_first else 0)
            leveled = await self.grant_xp(player, xp)
            lines.append(f"🧩 **Richtig!** {riddle.get('flavor', '')}".strip())
            lines.append(f"✨ +{xp} XP" + (" (Erster!) 🥇" if is_first else ""))
            for item_key in riddle.get("loot", []):
                if is_first:
                    await database.add_item(guild_id, interaction.user.id, item_key, 1)
                    lines.append(f"🎁 {item_line(item_key)}")
            if leveled:
                lines.append("🎉 **Stufenaufstieg!**")
        else:
            await self.grant_xp(player, 5)
            lines.append("❌ **Leider falsch.** Doch auch Werken bringt Wissen: +5 XP.")
        color = 0x2ECC71 if correct else 0xE74C3C
        await interaction.response.send_message(
            embed=discord.Embed(description="\n".join(lines), color=color), ephemeral=True
        )

    async def handle_vote(self, interaction: discord.Interaction, door: int, option: dict):
        guild_id = interaction.guild_id
        existing = await database.fetchone(
            "SELECT choice FROM votes WHERE guild_id = ? AND door = ? AND user_id = ?",
            (guild_id, door, interaction.user.id),
        )
        if existing:
            await interaction.response.send_message(
                "Deine Stimme ist schon vergeben. 🗳️", ephemeral=True
            )
            return
        if not await database.get_player(guild_id, interaction.user.id):
            await interaction.response.send_message(
                "Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True
            )
            return
        await database.execute(
            "INSERT INTO votes (guild_id, door, user_id, choice) VALUES (?, ?, ?, ?)",
            (guild_id, door, interaction.user.id, option["key"]),
        )
        player = await database.get_player(guild_id, interaction.user.id)
        await self.grant_xp(player, 10)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"🗳️ Deine Stimme ist gezählt: **{option['label']}** · +10 XP",
                color=0x27AE60,
            ),
            ephemeral=True,
        )

    async def resolve_interaction(self, channel: discord.TextChannel, door: int):
        guild_id = channel.guild.id
        done = await database.fetchone(
            "SELECT choice FROM resolutions WHERE guild_id = ? AND door = ?", (guild_id, door)
        )
        if done:
            return
        data = load_door(door)
        if not data or data.get("afternoon", {}).get("type") != "interaction":
            return
        afternoon = data["afternoon"]
        votes = await database.fetchall(
            "SELECT choice, COUNT(*) AS c FROM votes WHERE guild_id = ? AND door = ? GROUP BY choice ORDER BY c DESC",
            (guild_id, door),
        )
        if not votes:
            return
        winner_key = votes[0]["choice"]
        winner = next((o for o in afternoon["options"] if o["key"] == winner_key), None)
        await database.execute(
            "INSERT INTO resolutions (guild_id, door, choice) VALUES (?, ?, ?)", (guild_id, door, winner_key)
        )
        lines = [f"🗳️ Die Gruppe hat entschieden: **{winner['label']}**"]
        lines.append(afternoon.get("outcomes", {}).get(winner_key, "Das Abenteuer nimmt seinen Lauf."))
        loot = winner.get("loot", afternoon.get("loot", []))
        voters = await database.fetchall(
            "SELECT user_id FROM votes WHERE guild_id = ? AND door = ?", (guild_id, door)
        )
        for row in voters:
            player = await database.get_player(guild_id, row["user_id"])
            if not player:
                continue
            for item_key in loot:
                await database.add_item(guild_id, row["user_id"], item_key, 1)
        if loot:
            lines.append("🎁 Gruppenloot für alle Abstimmenden: " + " · ".join(item_line(k) for k in loot))
        await channel.send(
            embed=discord.Embed(
                title=f"📜 Ergebnis von Tür {door}", description="\n".join(lines), color=0x27AE60
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AfternoonCog(bot))
