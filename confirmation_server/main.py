"""
confirmation_server/main.py — FastAPI server for email confirmation.

Endpoints:
  GET  /api/status/{token}  → check token state
  POST /api/confirm/{token} → mark team email-confirmed
  POST /api/resend/{token}  → generate new token + resend email

Exposed publicly via Cloudflare Tunnel (cloudflared).
The Vercel React frontend calls this API.
"""
from __future__ import annotations

import secrets
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

# ── Allow importing from project root (mailer.py, config.py) ─────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import config
import mailer

TOKEN_EXPIRY_HOURS = 1


# ── App lifespan (DB pool) ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        min_size=1,
        max_size=5,
    )
    yield
    await app.state.pool.close()


app = FastAPI(title="VALORANT Tournament Confirmation API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Vercel will have its own domain; set this in prod
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/status/{token}")
async def token_status(token: str, request: Request):
    """
    Returns token state:
      valid | expired | used | invalid | already_confirmed
    """
    async with _pool(request).acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT et.used, et.expires_at,
                   t.team_name, t.captain_ign, t.email_confirmed
            FROM   email_tokens et
            JOIN   teams t ON t.team_id = et.team_id
            WHERE  et.token = $1
            """,
            token,
        )

    if not row:
        return {"status": "invalid"}
    if row["email_confirmed"]:
        return {"status": "already_confirmed", "team_name": row["team_name"]}
    if row["used"]:
        return {"status": "used"}
    if row["expires_at"] < datetime.now(timezone.utc):
        return {"status": "expired"}

    return {
        "status": "valid",
        "team_name": row["team_name"],
        "captain_ign": row["captain_ign"],
        "expires_at": row["expires_at"].isoformat(),
    }


@app.post("/api/confirm/{token}")
async def confirm_token(token: str, request: Request):
    """Mark the token as used and set teams.email_confirmed = TRUE."""
    async with _pool(request).acquire() as conn:
        row = await conn.fetchrow(
            "SELECT team_id, used, expires_at FROM email_tokens WHERE token = $1",
            token,
        )
        if not row:
            raise HTTPException(404, detail="Invalid token.")
        if row["used"]:
            raise HTTPException(400, detail="Token already used.")
        if row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(400, detail="Token has expired. Please request a new one.")

        await conn.execute(
            "UPDATE email_tokens SET used = TRUE WHERE token = $1", token
        )
        await conn.execute(
            "UPDATE teams SET email_confirmed = TRUE WHERE team_id = $1",
            row["team_id"],
        )
        team = await conn.fetchrow(
            "SELECT team_name FROM teams WHERE team_id = $1", row["team_id"]
        )

    return {"status": "confirmed", "team_name": team["team_name"]}


@app.post("/api/resend/{token}")
async def resend_token(token: str, request: Request):
    """
    Invalidate all previous tokens for this team, generate a new one,
    and send a fresh confirmation email to the captain.
    """
    async with _pool(request).acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT et.team_id, t.captain_email, t.captain_ign,
                   t.team_name, t.email_confirmed
            FROM   email_tokens et
            JOIN   teams t ON t.team_id = et.team_id
            WHERE  et.token = $1
            """,
            token,
        )
        if not row:
            raise HTTPException(404, detail="Invalid token.")
        if row["email_confirmed"]:
            raise HTTPException(400, detail="Team already confirmed.")

        # Generate new token
        new_token  = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)

        await conn.execute(
            "UPDATE email_tokens SET used = TRUE WHERE team_id = $1 AND used = FALSE",
            row["team_id"],
        )
        await conn.execute(
            "INSERT INTO email_tokens (token, team_id, expires_at) VALUES ($1, $2, $3)",
            new_token, row["team_id"], expires_at,
        )

    # Build URLs pointing back to the Vercel frontend
    confirm_url = f"{config.FRONTEND_URL}/confirm/{new_token}"
    resend_url  = f"{config.FRONTEND_URL}/confirm/{new_token}"

    import asyncio
    await asyncio.to_thread(
        mailer._send_email_sync,
        row["captain_email"],
        row["captain_ign"],
        confirm_url,
        resend_url,
    )

    return {"status": "sent"}


# ── Entry point (for direct run) ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
