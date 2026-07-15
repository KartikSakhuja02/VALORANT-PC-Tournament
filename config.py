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


def _optional_int(key: str) -> "int | None":
    v = os.getenv(key)
    return int(v) if v else None


# ── Required ──────────────────────────────────────────────────────────────────
DISCORD_TOKEN: str = _require("DISCORD_TOKEN")
GUILD_ID: int = int(_require("GUILD_ID"))

# ── Optional ──────────────────────────────────────────────────────────────────
LOG_CHANNEL_ID: "int | None" = _optional_int("LOG_CHANNEL_ID")

# ── Registration ───────────────────────────────────────────────────────────────
REGISTRATION_CHANNEL_ID: "int | None" = _optional_int("REGISTRATION_CHANNEL_ID")
MOD_ROLE_ID: "int | None" = _optional_int("MOD_ROLE_ID")

# ── Database ───────────────────────────────────────────────────────────────────
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = _require("DB_NAME")
DB_USER: str = _require("DB_USER")
DB_PASSWORD: str = _require("DB_PASSWORD")

# ── SMTP & Confirmation URL ──────────────────────────────────────────────────
SMTP_EMAIL: str = _require("SMTP_EMAIL")
SMTP_PASSWORD: str = _require("SMTP_PASSWORD")
CONFIRMATION_SERVER_URL: str = _require("CONFIRMATION_SERVER_URL")
VERCEL_WEBPAGE_URL: str = _require("VERCEL_WEBPAGE_URL")
