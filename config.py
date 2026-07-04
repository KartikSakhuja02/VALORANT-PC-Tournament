"""
config.py — Centralised configuration loader for the VALORANT Tournament Bot.
Reads secrets from a .env file and exposes them as typed constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # loads .env from the project root


def _require(key: str) -> str:
    """Fetch a required env variable or raise a clear error."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"[Config] Missing required environment variable: '{key}'\n"
            f"  → Copy .env.example to .env and fill in the value."
        )
    return value


# ── Required ──────────────────────────────────────────────────────────────────
DISCORD_TOKEN: str = _require("DISCORD_TOKEN")
GUILD_ID: int = int(_require("GUILD_ID"))

# ── Optional ──────────────────────────────────────────────────────────────────
LOG_CHANNEL_ID: int | None = (
    int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
)
