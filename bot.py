"""
bot.py — Entry point for the VALORANT PC Tournament Discord Bot.

Features:
  • /ping         — Latency check (gateway + REST round-trip)
  • Registration  — Persistent team registration panel (cogs/registration.py)

Architecture:
  • discord.py 2.x with app_commands (slash commands)
  • asyncpg pool shared across all cogs via bot.db_pool
  • Guild-scoped command sync for instant updates during development
"""

import asyncio
import datetime
import logging
import sys

import discord
from discord import app_commands
from discord.ext import commands

import db
from config import DISCORD_TOKEN, GUILD_ID, LOG_CHANNEL_ID

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("valorant-bot")


# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
intents.members = True        # required for member-lookup & thread management
intents.message_content = True


# ── Bot class ─────────────────────────────────────────────────────────────────
class ValorantBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.target_guild = discord.Object(id=GUILD_ID)
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.db_pool = None  # set in setup_hook

    # ── Lifecycle ──────────────────────────────────────────────────────────────
    async def setup_hook(self) -> None:
        """Called once after login, before connecting to the gateway."""
        # 1. Connect to PostgreSQL
        log.info("Connecting to PostgreSQL...")
        self.db_pool = await db.create_pool()
        log.info("Database pool ready.")

        # 2. Load cogs
        await self.load_extension("cogs.registration")
        log.info("Cogs loaded.")

        # 3. Sync slash commands to guild (instant vs up-to-1-hour for global)
        self.tree.copy_global_to(guild=self.target_guild)
        synced = await self.tree.sync(guild=self.target_guild)
        log.info(f"Synced {len(synced)} slash command(s) to guild {GUILD_ID}.")

    async def on_ready(self) -> None:
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        log.info(f"discord.py version: {discord.__version__}")
        log.info("━" * 50)

        # Set bot presence
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="VALORANT Tournaments 🎯",
            ),
        )

        # Send/verify the persistent registration panel
        reg_cog = self.get_cog("Registration")
        if reg_cog:
            await reg_cog.send_registration_panel()

        # Optional startup log message in a designated channel
        if LOG_CHANNEL_ID:
            channel = self.get_channel(LOG_CHANNEL_ID)
            if channel and isinstance(channel, discord.TextChannel):
                embed = discord.Embed(
                    title="✅ Bot Online",
                    description="VALORANT Tournament Bot is up and running!",
                    colour=discord.Colour.from_str("#FF4655"),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                embed.set_footer(text="VALORANT PC Tournament Bot")
                await channel.send(embed=embed)

    async def close(self) -> None:
        """Gracefully close DB pool on shutdown."""
        if self.db_pool:
            await self.db_pool.close()
            log.info("Database pool closed.")
        await super().close()

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        log.error(f"Command error in '{ctx.command}': {error}")


# ── Bot instance ──────────────────────────────────────────────────────────────
bot = ValorantBot()


# ── Slash Commands ────────────────────────────────────────────────────────────
@bot.tree.command(name="ping", description="Check the bot's latency and status.")
async def ping(interaction: discord.Interaction) -> None:
    """Returns gateway latency and a REST API round-trip time."""
    await interaction.response.defer(ephemeral=False)

    ws_latency_ms = round(bot.latency * 1000)

    before = datetime.datetime.now(datetime.timezone.utc)
    msg = await interaction.followup.send("📡 Calculating ping…", wait=True)
    after = datetime.datetime.now(datetime.timezone.utc)
    rest_latency_ms = round((after - before).total_seconds() * 1000)

    uptime_delta = datetime.datetime.now(datetime.timezone.utc) - bot.start_time
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    if ws_latency_ms < 100:
        colour = discord.Colour.from_str("#00C851")
        quality = "🟢 Excellent"
    elif ws_latency_ms < 200:
        colour = discord.Colour.from_str("#FFD700")
        quality = "🟡 Good"
    else:
        colour = discord.Colour.from_str("#FF4655")
        quality = "🔴 Poor"

    embed = discord.Embed(
        title="🏓 Pong!",
        colour=colour,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(name="WebSocket Latency", value=f"`{ws_latency_ms} ms`", inline=True)
    embed.add_field(name="REST Latency", value=f"`{rest_latency_ms} ms`", inline=True)
    embed.add_field(name="Connection Quality", value=quality, inline=True)
    embed.add_field(name="Bot Uptime", value=f"`{uptime_str}`", inline=False)
    embed.set_footer(
        text="VALORANT PC Tournament Bot",
        icon_url=(bot.user.display_avatar.url if bot.user else None),
    )

    await msg.edit(content=None, embed=embed)
    log.info(
        f"/ping used by {interaction.user} — WS: {ws_latency_ms}ms, REST: {rest_latency_ms}ms"
    )


# ── Entry point ───────────────────────────────────────────────────────────────
async def main() -> None:
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot shut down via KeyboardInterrupt.")
