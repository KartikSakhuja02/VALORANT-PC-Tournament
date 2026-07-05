"""
web_server.py — FastAPI server that handles email verification requests.
Connects to the local PostgreSQL database, processes tokens, and serves the frontend.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
import mailer

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("valorant-web")

app = FastAPI(title="VALORANT PC Tournament Verification Portal")

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    log.info("Connecting to PostgreSQL pool...")
    db_pool = await asyncpg.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        min_size=1,
        max_size=5,
    )
    log.info("PostgreSQL pool ready.")

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()
        log.info("PostgreSQL pool closed.")

async def get_db():
    async with db_pool.acquire() as conn:
        yield conn

# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/status/{token}")
async def get_status(token: str, conn: asyncpg.Connection = Depends(get_db)):
    """Check the status of a verification token."""
    row = await conn.fetchrow(
        """
        SELECT t.team_name, t.captain_ign, t.email_confirmed, e.expires_at, e.used
        FROM email_tokens e
        JOIN teams t ON e.team_id = t.team_id
        WHERE e.token = $1
        """,
        token
    )
    if not row:
        return {"status": "invalid"}

    # Check if team is already confirmed (regardless of this specific token)
    if row["email_confirmed"]:
        return {
            "status": "already_confirmed",
            "team_name": row["team_name"],
            "captain_ign": row["captain_ign"]
        }

    if row["used"]:
        return {
            "status": "used",
            "team_name": row["team_name"],
            "captain_ign": row["captain_ign"]
        }

    now = datetime.now(timezone.utc)
    # Check if expired
    if row["expires_at"] < now:
        return {
            "status": "expired",
            "team_name": row["team_name"],
            "captain_ign": row["captain_ign"]
        }

    return {
        "status": "valid",
        "team_name": row["team_name"],
        "captain_ign": row["captain_ign"]
    }

@app.post("/api/confirm/{token}")
async def confirm_email(token: str, conn: asyncpg.Connection = Depends(get_db)):
    """Confirm the team's email using the token."""
    row = await conn.fetchrow(
        """
        SELECT e.team_id, e.expires_at, e.used, t.email_confirmed
        FROM email_tokens e
        JOIN teams t ON e.team_id = t.team_id
        WHERE e.token = $1
        """,
        token
    )
    if not row:
        raise HTTPException(status_code=404, detail="Token not found.")

    if row["email_confirmed"]:
        return {"message": "Email is already confirmed."}

    if row["used"]:
        raise HTTPException(status_code=400, detail="Token already used.")

    now = datetime.now(timezone.utc)
    if row["expires_at"] < now:
        raise HTTPException(status_code=400, detail="Token has expired.")

    # Process confirmation inside a transaction
    async with conn.transaction():
        # Mark token as used
        await conn.execute(
            "UPDATE email_tokens SET used = TRUE WHERE token = $1",
            token
        )
        # Mark team as confirmed
        await conn.execute(
            "UPDATE teams SET email_confirmed = TRUE WHERE team_id = $1",
            row["team_id"]
        )

    log.info(f"Team ID {row['team_id']} email successfully verified.")
    return {"message": "Email confirmed successfully."}

@app.post("/api/resend/{token}")
async def resend_email(token: str, conn: asyncpg.Connection = Depends(get_db)):
    """Invalidate the old token and send a new 1-hour verification token to the captain."""
    row = await conn.fetchrow(
        """
        SELECT e.team_id, t.team_name, t.captain_ign, t.captain_email, t.email_confirmed
        FROM email_tokens e
        JOIN teams t ON e.team_id = t.team_id
        WHERE e.token = $1
        """,
        token
    )
    if not row:
        raise HTTPException(status_code=404, detail="Token not found.")

    if row["email_confirmed"]:
        return {"message": "Email is already confirmed."}

    # Generate new token active for 1 hour
    new_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    async with conn.transaction():
        # Invalidate old token
        await conn.execute(
            "UPDATE email_tokens SET used = TRUE WHERE token = $1",
            token
        )
        # Insert new token
        await conn.execute(
            """
            INSERT INTO email_tokens (token, team_id, expires_at)
            VALUES ($1, $2, $3)
            """,
            new_token, row["team_id"], expires_at
        )

    # Generate links pointing to the confirmation web server
    base_url = os.getenv("CONFIRMATION_SERVER_URL", "http://localhost:8080").rstrip("/")
    confirm_link = f"{base_url}/confirm/{new_token}"
    resend_link = f"{base_url}/resend-request/{new_token}"

    # Send the email
    email_sent = await mailer.send_confirmation_email(
        captain_ign=row["captain_ign"],
        recipient_email=row["captain_email"],
        confirm_link=confirm_link,
        resend_link=resend_link
    )

    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send email.")

    log.info(f"New verification email sent to team ID {row['team_id']}")
    return {"message": "New verification email has been sent."}

# ── Serve Built Frontend ──────────────────────────────────────────────────────

# Serve built static files at root
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent API routes from falling through to the index.html serve
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build files not found.")
else:
    @app.get("/")
    async def dev_root():
        return {"message": "Verification API running. Frontend static build directory is missing."}
