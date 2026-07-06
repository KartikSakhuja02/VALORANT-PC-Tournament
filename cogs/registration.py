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
from datetime import datetime, timezone

import asyncpg
import discord
from discord.ext import commands

import config

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

async def _collect_logo(
    client: discord.Client,
    thread: discord.Thread,
    user: discord.Member,
    team_id: int,
    team_name: str,
    pool: asyncpg.Pool,
) -> None:
    """
    After registration, prompt the captain to upload their team logo as an
    image. Saves it to logos/<team_id>_<safe_name>.<ext> on disk and updates
    the teams.logo_url column with the local file path.
    """
    await thread.send(
        f"{user.mention} — Please send your **team logo** as an image (PNG or JPG).\n"
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


async def _send_verification_and_collect_logo(
    client: discord.Client,
    thread: discord.Thread,
    user: discord.Member,
    team_id: int,
    team_name: str,
    ign: str,
    email: str,
    token: str,
    pool: asyncpg.Pool,
) -> None:
    """
    Background task:
    1. Sends the SMTP email using mailer.py.
    2. Tells user to check their email.
    3. Runs logo collection process.
    """
    status_msg = await thread.send("Generating and sending verification email...")
    try:
        import mailer
        await mailer.send_confirmation_email(email, ign, token)
        await status_msg.edit(content="Please check your gmail to confirm your team (check spam folders too).")
    except Exception as e:
        log.exception(f"Failed to send confirmation email to {email}")
        await status_msg.edit(content="Failed to send verification email. Please contact a moderator to verify manually.")

    # Continue with logo collection
    await _collect_logo(client, thread, user, team_id, team_name, pool)


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

                # Insert team (logo_url left NULL — collected separately as image)
                team_id: int = await conn.fetchval(
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

                # Generate secure 1-hour verification token
                token = secrets.token_urlsafe(32)
                await conn.execute(
                    """
                    INSERT INTO email_tokens (token, team_id, expires_at)
                    VALUES ($1, $2, NOW() + INTERVAL '1 hour')
                    """,
                    token, team_id,
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
                "Staff will approve or contact you shortly."
            ),
            colour=discord.Colour.from_str("#00C851"),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Team", value=f"**{team_name}**", inline=True)
        embed.add_field(name="Captain IGN", value=f"`{ign}`", inline=True)
        embed.add_field(name="Region", value=f"`{region}`", inline=True)
        embed.add_field(name="Status", value="`Pending Review`", inline=False)
        embed.set_footer(text="VALORANT PC Tournament  •  Registration Portal")

        await interaction.followup.send(embed=embed)

        # Send verification email & collect logo concurrently
        if isinstance(interaction.channel, discord.Thread):
            asyncio.create_task(_send_verification_and_collect_logo(
                interaction.client,
                interaction.channel,
                interaction.user,
                team_id,
                team_name,
                ign,
                email,
                token,
                pool,
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
