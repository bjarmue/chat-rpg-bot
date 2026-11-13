import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import database

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("advent-rpg")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class AdventRPGBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            activity=discord.Activity(type=discord.ActivityType.listening, name="den 24 Türen von Frosthaven"),
        )

    async def setup_hook(self):
        await database.init_db()
        for cog in ("calendar", "character", "story", "afternoon", "inventory"):
            await self.load_extension(f"cogs.{cog}")
        await self.tree.sync()
        log.info("Commands synchronisiert.")

    async def on_ready(self):
        log.info("Eingeloggt als %s (ID: %s)", self.user, self.user.id)


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN fehlt! Bitte .env anlegen (siehe .env.example).")
    async with AdventRPGBot() as bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
