import discord
from discord import app_commands
from discord.ext import commands

import database
from game_data import ITEMS, RARITY_COLORS, max_hp
from utils import item_line, player_stats


async def owned_items(guild_id: int, user_id: int) -> list[tuple[dict, int]]:
    rows = await database.fetchall(
        "SELECT item, qty FROM inventory WHERE guild_id = ? AND user_id = ? ORDER BY item",
        (guild_id, user_id),
    )
    return [(ITEMS[row["item"]], row["qty"]) for row in rows if row["item"] in ITEMS]


class TradeView(discord.ui.View):
    def __init__(self, trade_id: int):
        super().__init__(timeout=None)
        self.trade_id = trade_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        trade = await database.fetchone("SELECT * FROM trades WHERE id = ?", (self.trade_id,))
        if not trade or trade["status"] != "offen":
            await interaction.response.send_message("Dieses Angebot ist nicht mehr gültig.", ephemeral=True)
            return False
        if interaction.user.id != trade["to_user"]:
            await interaction.response.send_message(
                "Nur der angesprochene Spieler kann dieses Angebot annehmen.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Annehmen", style=discord.ButtonStyle.success, emoji="🤝")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        trade = await database.fetchone("SELECT * FROM trades WHERE id = ?", (self.trade_id,))
        ok_give = await database.remove_item(
            trade["guild_id"], trade["from_user"], trade["offer_item"], trade["offer_qty"]
        )
        ok_take = await database.remove_item(
            trade["guild_id"], trade["to_user"], trade["request_item"], trade["request_qty"]
        )
        if not ok_give or not ok_take:
            await database.execute("UPDATE trades SET status = 'gescheitert' WHERE id = ?", (self.trade_id,))
            await interaction.response.send_message(
                "Einer der Gegenstände ist nicht mehr verfügbar. Tausch gescheitert.", ephemeral=True
            )
            return
        await database.add_item(
            trade["guild_id"], trade["to_user"], trade["offer_item"], trade["offer_qty"]
        )
        await database.add_item(
            trade["guild_id"], trade["from_user"], trade["request_item"], trade["request_qty"]
        )
        await database.execute("UPDATE trades SET status = 'abgeschlossen' WHERE id = ?", (self.trade_id,))
        for child in self.children:
            child.disabled = True
        offer = item_line(trade["offer_item"], trade["offer_qty"])
        request = item_line(trade["request_item"], trade["request_qty"])
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🤝 Tausch abgeschlossen!",
                description=(
                    f"<@{trade['from_user']}> gab {offer}\n"
                    f"<@{trade['to_user']}> gab {request}"
                ),
                color=0x2ECC71,
            ),
            view=self,
        )

    @discord.ui.button(label="Ablehnen", style=discord.ButtonStyle.danger, emoji="✖️")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await database.execute("UPDATE trades SET status = 'abgelehnt' WHERE id = ?", (self.trade_id,))
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(description="❌ Tausch abgelehnt.", color=0xE74C3C), view=self
        )


class InventoryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="inventar", description="Zeige dein Inventar")
    async def inventar(self, interaction: discord.Interaction):
        player = await database.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            await interaction.response.send_message("Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True)
            return
        items = await owned_items(interaction.guild_id, interaction.user.id)
        if not items:
            await interaction.response.send_message(
                "🎒 Dein Rucksack ist leer — doch Frosthaven hat viel zu vergeben!", ephemeral=True
            )
            return
        lines = []
        for item, qty in items:
            marker = ""
            if player["weapon"] and ITEMS[player["weapon"]]["name"] == item["name"]:
                marker = " · **angelegt**"
            elif player["armor"] and ITEMS[player["armor"]]["name"] == item["name"]:
                marker = " · **angelegt**"
            lines.append(f"{item_line(_key_of(item), qty)}{marker}\n   ↳ {item['desc']}")
        embed = discord.Embed(
            title=f"🎒 {player['name']}'s Rucksack",
            description="\n".join(lines),
            color=RARITY_COLORS["gewöhnlich"],
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ausruesten", description="Lege eine Waffe oder Rüstung an")
    @app_commands.describe(item="Name des Gegenstands (Waffe oder Rüstung)")
    async def ausruesten(self, interaction: discord.Interaction, item: str):
        player = await database.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            await interaction.response.send_message("Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True)
            return
        match = next((i for i in ITEMS.values() if i["name"].lower() == item.lower()), None)
        if not match or match["type"] not in ("waffe", "rüstung"):
            await interaction.response.send_message("Das ist keine Waffe oder Rüstung.", ephemeral=True)
            return
        key = _key_of(match)
        owned = await database.fetchone(
            "SELECT qty FROM inventory WHERE guild_id = ? AND user_id = ? AND item = ?",
            (interaction.guild_id, interaction.user.id, key),
        )
        equipped_key = player["weapon"] if match["type"] == "waffe" else player["armor"]
        if not owned and equipped_key != key:
            await interaction.response.send_message("Das besitzt du nicht.", ephemeral=True)
            return
        column = "weapon" if match["type"] == "waffe" else "armor"
        await database.execute(
            f"UPDATE players SET {column} = ? WHERE guild_id = ? AND user_id = ?",
            (key, interaction.guild_id, interaction.user.id),
        )
        await interaction.response.send_message(
            f"✅ **{match['name']}** angelegt: {match['desc']}", ephemeral=True
        )

    @ausruesten.autocomplete("item")
    async def ausruesten_autocomplete(self, interaction: discord.Interaction, current: str):
        player = await database.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            return []
        items = await owned_items(interaction.guild_id, interaction.user.id)
        choices = []
        for item, _qty in items:
            if item["type"] not in ("waffe", "rüstung"):
                continue
            if current.lower() in item["name"].lower():
                choices.append(app_commands.Choice(name=item["name"], value=item["name"]))
        return choices[:25]

    @app_commands.command(name="benutzen", description="Verbrauche einen Gegenstand (z. B. Heiltrank)")
    @app_commands.describe(item="Name des Verbrauchsgegenstands")
    async def benutzen(self, interaction: discord.Interaction, item: str):
        info = await player_stats(interaction.guild_id, interaction.user.id)
        if not info:
            await interaction.response.send_message("Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True)
            return
        match = next((i for i in ITEMS.values() if i["name"].lower() == item.lower()), None)
        if not match or match["type"] != "verbrauch":
            await interaction.response.send_message("Das kann man nicht verzehren.", ephemeral=True)
            return
        player = info["player"]
        if player["hp"] >= info["max_hp"]:
            await interaction.response.send_message("Du bist bereits bei vollen Lebenspunkten. ❤️", ephemeral=True)
            return
        removed = await database.remove_item(
            interaction.guild_id, interaction.user.id, _key_of(match), 1
        )
        if not removed:
            await interaction.response.send_message("Das besitzt du nicht.", ephemeral=True)
            return
        new_hp = min(info["max_hp"], player["hp"] + match["heal"])
        await database.execute(
            "UPDATE players SET hp = ? WHERE guild_id = ? AND user_id = ?",
            (new_hp, interaction.guild_id, interaction.user.id),
        )
        await interaction.response.send_message(
            f"{match['emoji']} **{match['name']}** verzehrt: +{match['heal']} LP "
            f"({new_hp}/{info['max_hp']}) ❤️",
            ephemeral=True,
        )

    @benutzen.autocomplete("item")
    async def benutzen_autocomplete(self, interaction: discord.Interaction, current: str):
        player = await database.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            return []
        items = await owned_items(interaction.guild_id, interaction.user.id)
        choices = []
        for item, _qty in items:
            if item["type"] != "verbrauch":
                continue
            if current.lower() in item["name"].lower():
                choices.append(app_commands.Choice(name=item["name"], value=item["name"]))
        return choices[:25]

    @app_commands.command(name="tauschen", description="Biete einem anderen Helden einen Tausch an")
    @app_commands.describe(
        partner="Mit wem tauschen?",
        angebot="Was du gibst (Name)",
        gefragt="Was du dafür haben willst (Name)",
    )
    async def tauschen(
        self,
        interaction: discord.Interaction,
        partner: discord.Member,
        angebot: str,
        gefragt: str,
    ):
        if partner.bot or partner.id == interaction.user.id:
            await interaction.response.send_message("So ein Tausch geht nicht.", ephemeral=True)
            return
        player = await database.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            await interaction.response.send_message("Du brauchst zuerst einen Helden! Nutze /charakter.", ephemeral=True)
            return
        offer = next((i for i in ITEMS.values() if i["name"].lower() == angebot.lower()), None)
        request = next((i for i in ITEMS.values() if i["name"].lower() == gefragt.lower()), None)
        if not offer or not request:
            await interaction.response.send_message("Unbekannter Gegenstand — prüfe die Namen in /inventar.", ephemeral=True)
            return
        owned = await database.fetchone(
            "SELECT qty FROM inventory WHERE guild_id = ? AND user_id = ? AND item = ?",
            (interaction.guild_id, interaction.user.id, _key_of(offer)),
        )
        if not owned:
            await interaction.response.send_message("Das Angebot besitzt du gar nicht!", ephemeral=True)
            return
        await database.execute(
            "INSERT INTO trades (guild_id, from_user, to_user, offer_item, offer_qty, request_item, request_qty) "
            "VALUES (?, ?, ?, ?, 1, ?, 1)",
            (interaction.guild_id, interaction.user.id, partner.id, _key_of(offer), _key_of(request)),
        )
        trade = await database.fetchone(
            "SELECT id FROM trades WHERE guild_id = ? AND from_user = ? AND status = 'offen' ORDER BY id DESC LIMIT 1",
            (interaction.guild_id, interaction.user.id),
        )
        embed = discord.Embed(
            title="🤝 Tauschangebot!",
            description=(
                f"<@{interaction.user.id}> bietet dir:\n{item_line(_key_of(offer))}\n\n"
                f"…und möchte dafür: {item_line(_key_of(request))}"
            ),
            color=RARITY_COLORS["selten"],
        )
        await interaction.response.send_message(
            content=f"{partner.mention}, ein Angebot!",
            embed=embed,
            view=TradeView(trade["id"]),
        )


def _key_of(item: dict) -> str:
    return next(k for k, v in ITEMS.items() if v is item)


async def setup(bot: commands.Bot):
    await bot.add_cog(InventoryCog(bot))
