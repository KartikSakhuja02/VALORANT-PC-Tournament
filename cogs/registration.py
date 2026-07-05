"""
cogs/registration.py — Team registration flow for the VALORANT PC Tournament.

Flow:
  1. Bot posts a persistent panel embed in REGISTRATION_CHANNEL_ID on first start.
  2. User clicks "Register Your Team" → a private thread is created for them.
  3. Thread contains a prompt embed + "Start Registration" button.
  4. Clicking Start opens a Discord Modal (pop-up form) with 5 fields.
  5. On submit the team is saved to PostgreSQL and the thread is updated.

Both views (panel + thread start) are PERSISTENT — they survive bot restarts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone, timedelta

import asyncpg
import discord
from discord.ext import commands

import config
import mailer

log = logging.getLogger("valorant-bot.registration")

VALID_REGIONS = {"NA", "EU", "AP", "KR", "LATAM", "BR", "ME"}
STATE_FILE = "bot_state.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _reg_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="VALORANT PC Tournament — Team Registration",
        description=(
            "**Welcome to the official team registration portal.**\n"
            "Read the steps below, then click the button to begin.\n"
            "\u200b"
        ),
        colour=discord.Colour.from_str("#FF4655"),
    )
    embed.add_field(
        name="How to Register",
        value=(
            "**1.** Click **Register Your Team** below\n"
            "**2.** A private thread opens just for you\n"
            "**3.** Fill in the form with your team details\n"
            "**4.** Staff will review and approve your team\n"
            "**5.** Once approved, invite your 4 teammates"
        ),
        inline=False,
    )
    embed.add_field(
        name="Requirements",
        value=(
            "• **5 players** per team (1 optional substitute)\n"
            "• All players in the **same region**\n"
            "• Valid email address for each player\n"
            "• Unique, appropriate team name"
        ),
        inline=False,
    )
    embed.add_field(
        name="Rules",
        value=(
            "• One account per player — no smurfs\n"
            "• Account sharing = instant disqualification\n"
            "• Staff decisions are final"
        ),
        inline=False,
    )
    embed.set_footer(text="VALORANT PC Tournament  •  Registration Portal")
    return embed


# ── Logo Collection ───────────────────────────────────────────────────────────

# ── Post-Registration Workflow (Gmail verification + Logo collection) ─────────

async def _post_registration_workflow(
    client: discord.Client,
    thread: discord.Thread,
    user: discord.Member,
    team_id: int,
    team_name: str,
    pool: asyncpg.Pool,
    token: str,
    captain_ign: str,
    email: str,
) -> None:
    """
    1. Sends verification link via Gmail API.
    2. Prompts captain to check Gmail inbox.
    3. Prompts captain to upload team logo.
    """
    # Generate links using server url in config
    base_url = getattr(config, "CONFIRMATION_SERVER_URL", "http://localhost:8080").rstrip("/")
    confirm_link = f"{base_url}/confirm/{token}"
    resend_link = f"{base_url}/resend-request/{token}"

    log.info(f"Triggering email dispatch for team {team_name} ({email})...")
    
    # Dispatch email using asyncio.to_thread to prevent blocking the discord event loop
    email_sent = await asyncio.to_thread(
        mailer.send_confirmation_email,
        captain_ign,
        email,
        confirm_link,
        resend_link
    )

    if email_sent:
        await thread.send(
            f"{user.mention} — Please check your **Gmail** to confirm your team (check spam folders too)."
        )
    else:
        log.error(f"Gmail confirmation dispatch failed for team '{team_name}'")
        await thread.send(
            f"{user.mention} — We had an issue sending your confirmation email. Please ask an admin to check the logs."
        )

    # Prompt for team logo
    await thread.send(
        "Please send your **team logo** as an image (PNG or JPG).\n"
        "You have 2 minutes. Reply `skip` to skip."
    )

    def _check(m: discord.Message) -> bool:
        if m.channel.id != thread.id or m.author.id != user.id:
            return False
        if m.content.strip().lower() == "skip":
            return True
        return bool(
            m.attachments
            and m.attachments[0].content_type
            and m.attachments[0].content_type.startswith("image/")
        )

    try:
        msg: discord.Message = await client.wait_for(
            "message", check=_check, timeout=120.0
        )
    except asyncio.TimeoutError:
        await thread.send("No logo received. A moderator can add it later.")
        return

    if msg.content.strip().lower() == "skip":
        await thread.send("Logo skipped. A moderator can add it later.")
        return

    attachment = msg.attachments[0]

    # Determine extension
    ext = "png"
    if "." in attachment.filename:
        ext = attachment.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp", "gif"}:
        ext = "png"

    # Ensure logos directory exists (relative to project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logos_dir = os.path.join(project_root, "logos")
    os.makedirs(logos_dir, exist_ok=True)

    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", team_name)
    filename = f"{team_id}_{safe_name}.{ext}"
    filepath = os.path.join(logos_dir, filename)

    await attachment.save(filepath)
    log.info(f"Logo saved for team '{team_name}' → {filepath}")

    # Update DB
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE teams SET logo_url = $1 WHERE team_id = $2",
            filepath,
            team_id,
        )

    await thread.send("Logo saved. Your registration is complete.")


# ── Modal ─────────────────────────────────────────────────────────────────────

class TeamRegistrationModal(discord.ui.Modal, title="Team Registration"):
    captain_ign = discord.ui.TextInput(
        label="Your IGN  (e.g. Shroud#1234)",
        placeholder="Name#Tag",
        max_length=64,
    )
    team_name = discord.ui.TextInput(
        label="Team Name",
        placeholder="Enter your team name",
        max_length=64,
    )
    region = discord.ui.TextInput(
        label="Region  (NA / EU / AP / KR / LATAM / BR / ME)",
        placeholder="AP",
        max_length=5,
    )
    captain_email = discord.ui.TextInput(
        label="Your Email Address",
        placeholder="captain@example.com",
        max_length=255,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        pool: asyncpg.Pool = interaction.client.db_pool

        # ── Validation ────────────────────────────────────────────────────────
        region = self.region.value.strip().upper()
        if region not in VALID_REGIONS:
            await interaction.followup.send(
                f"Invalid region `{region}`. Valid options: `NA` `EU` `AP` `KR` `LATAM` `BR` `ME`",
                ephemeral=True,
            )
            return

        email = self.captain_email.value.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            await interaction.followup.send(
                "Invalid email address. Please enter a real email.",
                ephemeral=True,
            )
            return

        ign = self.captain_ign.value.strip()
        team_name = self.team_name.value.strip()
        discord_id = str(interaction.user.id)

        token = None
        team_id = None

        # ── Database ──────────────────────────────────────────────────────────
        try:
            async with pool.acquire() as conn:
                # Duplicate check
                row = await conn.fetchrow(
                    """
                    SELECT team_name FROM teams
                    WHERE team_name = $1
                       OR captain_discord_id = $2
                       OR captain_email = $3
                    """,
                    team_name, discord_id, email,
                )
                if row:
                    await interaction.followup.send(
                        "A team already exists with that name, captain, or email.",
                        ephemeral=True,
                    )
                    return

                # Process everything inside a transaction
                async with conn.transaction():
                    # Insert team (logo_url left NULL — collected separately as image)
                    team_id = await conn.fetchval(
                        """
                        INSERT INTO teams
                            (team_name, captain_discord_id, captain_email,
                             region, captain_ign)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING team_id
                        """,
                        team_name, discord_id, email, region, ign,
                    )

                    # Insert captain as player
                    await conn.execute(
                        """
                        INSERT INTO players
                            (team_id, discord_id, email, ign, region,
                             is_captain, joined_server, verified)
                        VALUES ($1, $2, $3, $4, $5, TRUE, TRUE, FALSE)
                        """,
                        team_id, discord_id, email, ign, region,
                    )

                    # Generate and insert 1-hour email confirmation token
                    token = secrets.token_urlsafe(32)
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
                    await conn.execute(
                        """
                        INSERT INTO email_tokens (token, team_id, expires_at)
                        VALUES ($1, $2, $3)
                        """,
                        token, team_id, expires_at
                    )

        except asyncpg.UniqueViolationError:
            await interaction.followup.send(
                "Registration failed: duplicate team name or captain.",
                ephemeral=True,
            )
            return
        except Exception as exc:
            log.exception("DB error during registration")
            await interaction.followup.send(
                f"Database error — please contact a moderator.\n`{exc}`",
                ephemeral=True,
            )
            return

        # ── Success ───────────────────────────────────────────────────────────
        embed = discord.Embed(
            title="Team Registered",
            description=(
                "Your team has been submitted for review.\n"
                "Please check your Gmail inbox (and spam folder) to verify your account."
            ),
            colour=discord.Colour.from_str("#00C851"),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Team", value=f"**{team_name}**", inline=True)
        embed.add_field(name="Captain IGN", value=f"`{ign}`", inline=True)
        embed.add_field(name="Region", value=f"`{region}`", inline=True)
        embed.add_field(name="Status", value="`Pending Email Verification`", inline=False)
        embed.set_footer(text="VALORANT PC Tournament  •  Registration Portal")

        await interaction.followup.send(embed=embed)

        # Trigger background workflow for email verification link and logo upload
        if token and team_id and isinstance(interaction.channel, discord.Thread):
            asyncio.create_task(_post_registration_workflow(
                interaction.client,
                interaction.channel,
                interaction.user,
                team_id,
                team_name,
                pool,
                token,
                ign,
                email
            ))

        # Rename the thread to reflect submission
        if isinstance(interaction.channel, discord.Thread):
            try:
                await interaction.channel.edit(name=f"registered-{team_name}")
            except discord.HTTPException:
                pass

        log.info(
            f"Team registered: '{team_name}' | Captain: {interaction.user} "
            f"({discord_id}) | Region: {region}"
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        log.exception("Modal error")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An unexpected error occurred. Please try again.", ephemeral=True
            )


# ── Thread Start View (persistent) ───────────────────────────────────────────

class ThreadStartView(discord.ui.View):
    """
    Sent inside the registration thread. Persistent so it survives restarts.
    Clicking 'Start Registration' opens the modal form.
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)  # persistent

    @discord.ui.button(
        label="Start Registration",
        style=discord.ButtonStyle.success,
        custom_id="persistent_thread_start_btn",
    )
    async def start(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        # Only allow the thread owner (whose ID is encoded in thread name) to submit
        thread = interaction.channel
        if isinstance(thread, discord.Thread):
            # Thread name format: "reg-<user_id>-<username>"
            parts = thread.name.split("-")
            if len(parts) >= 2 and parts[1].isdigit():
                owner_id = int(parts[1])
                if interaction.user.id != owner_id:
                    await interaction.response.send_message(
                        "Only the person who opened this thread can register.",
                        ephemeral=True,
                    )
                    return

        await interaction.response.send_modal(TeamRegistrationModal())


# ── Registration Panel View (persistent) ─────────────────────────────────────

class RegistrationPanelView(discord.ui.View):
    """
    Persistent view pinned in the registration channel.
    Survives bot restarts — registered in cog_load via bot.add_view().
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)  # persistent

    @discord.ui.button(
        label="Register Your Team",
        style=discord.ButtonStyle.danger,
        custom_id="persistent_register_panel_btn",
    )
    async def register(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        pool: asyncpg.Pool = interaction.client.db_pool

        # ── Already registered? ───────────────────────────────────────────────
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT team_name FROM teams WHERE captain_discord_id = $1",
                str(interaction.user.id),
            )
        if existing:
            await interaction.followup.send(
                f"You already registered team **{existing['team_name']}**. Contact a moderator if you need to make changes.",
                ephemeral=True,
            )
            return

        channel = interaction.channel

        # ── Create thread ─────────────────────────────────────────────────────
        thread_name = f"reg-{interaction.user.id}-{interaction.user.name[:16]}"
        try:
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                reason=f"Registration thread for {interaction.user}",
            )
        except (discord.HTTPException, discord.Forbidden):
            # Fallback: public thread (for servers without Tier 2 boost)
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread,
                reason=f"Registration thread for {interaction.user}",
            )

        # Add the registering user first, then moderators
        await thread.add_user(interaction.user)

        if config.MOD_ROLE_ID:
            mod_role = interaction.guild.get_role(config.MOD_ROLE_ID)
            if mod_role:
                for member in mod_role.members:
                    try:
                        await thread.add_user(member)
                    except discord.HTTPException:
                        pass

        # ── Send prompt in thread ─────────────────────────────────────────────
        embed = discord.Embed(
            title="VALORANT PC Tournament — Team Registration",
            description=(
                f"{interaction.user.mention}\n\n"
                "Click **Start Registration** below to fill in your team details."
            ),
            colour=discord.Colour.from_str("#FF4655"),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="You will be asked for",
            value=(
                "• In-Game Name (IGN)\n"
                "• Team Name\n"
                "• Region (NA / EU / AP / KR / LATAM / BR / ME)\n"
                "• Email Address\n\n"
                "After submitting, you will be asked to upload your **team logo** as an image."
            ),
            inline=False,
        )
        embed.set_footer(text="This thread is visible to moderators only.")

        await thread.send(
            content=interaction.user.mention,
            embed=embed,
            view=ThreadStartView(),
        )

        await interaction.followup.send(
            f"Your registration thread is ready: {thread.mention}",
            ephemeral=True,
        )
        log.info(f"Registration thread created for {interaction.user} ({interaction.user.id})")


# ── Cog ───────────────────────────────────────────────────────────────────────

class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        """Register all persistent views so they work after a restart."""
        self.bot.add_view(RegistrationPanelView())
        self.bot.add_view(ThreadStartView())
        log.info("Registration persistent views registered.")

    async def send_registration_panel(self) -> None:
        """
        Send the registration panel to REGISTRATION_CHANNEL_ID if it doesn't
        already exist. Called from bot.on_ready — safe to call on every restart.
        """
        channel_id = config.REGISTRATION_CHANNEL_ID
        if not channel_id:
            log.warning("REGISTRATION_CHANNEL_ID not set — skipping panel.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            log.warning(f"Registration channel {channel_id} not found.")
            return

        # Check stored message ID
        state = _load_state()
        stored_msg_id: int | None = state.get("registration_panel_message_id")

        if stored_msg_id:
            try:
                await channel.fetch_message(stored_msg_id)
                log.info("Registration panel already exists — skipping resend.")
                return  # Panel message still exists; nothing to do
            except discord.NotFound:
                log.info("Stored panel message was deleted — resending.")
            except discord.HTTPException as e:
                log.warning(f"Could not fetch panel message: {e}")
                return

        # Send a fresh panel
        msg = await channel.send(
            embed=_reg_panel_embed(),
            view=RegistrationPanelView(),
        )
        try:
            await msg.pin()
        except discord.HTTPException:
            pass  # Pin failed (maybe no permission) — not critical

        state["registration_panel_message_id"] = msg.id
        _save_state(state)
        log.info(f"Registration panel sent (message ID: {msg.id}).")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Registration(bot))
