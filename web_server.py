"""
web_server.py — aiohttp-based verification web server for VALORANT PC Tournament.
Uses pre-installed aiohttp to completely avoid installation overhead and crashes on Pi.
"""

import datetime
import logging
import secrets
import re
from aiohttp import web
import asyncpg

import db
import mailer

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("valorant-web")


async def on_startup(app: web.Application):
    log.info("Connecting to PostgreSQL pool...")
    app["db_pool"] = await db.create_pool()
    log.info("Database pool ready.")


async def on_cleanup(app: web.Application):
    log.info("Closing database pool...")
    await app["db_pool"].close()
    log.info("Database pool closed.")


def _get_base_html(title: str, content_html: str, client_js: str = "") -> str:
    """Base HTML shell matching the requested dark modern design."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | VALORANT TOURNAMENT SERIES</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #121212;
            color: #ffffff;
        }}
        .font-display {{
            font-family: 'Montserrat', sans-serif;
        }}
    </style>
</head>
<body class="bg-zinc-950 text-white min-h-screen flex flex-col justify-between">
    <!-- Navbar -->
    <header class="bg-zinc-900 border-b border-zinc-800 py-4 px-6">
        <div class="max-w-4xl mx-auto flex justify-between items-center">
            <h1 class="font-display text-sm tracking-[0.2em] text-red-500 font-extrabold uppercase">
                VALORANT TOURNAMENT SERIES
            </h1>
        </div>
    </header>

    <!-- Main Section -->
    <main class="flex-grow flex items-center justify-center p-6">
        <div class="w-full max-w-md bg-zinc-900 border border-zinc-800 p-8 shadow-2xl relative overflow-hidden">
            <!-- Red accent bar -->
            <div class="absolute top-0 left-0 right-0 h-1 bg-red-500"></div>
            {content_html}
        </div>
    </main>

    <!-- Footer -->
    <footer class="bg-zinc-900 border-t border-zinc-800 py-6 text-center text-xs text-zinc-500">
        <div class="max-w-4xl mx-auto">
            <p class="font-display tracking-widest text-zinc-400 font-bold uppercase mb-2">VALORANT TOURNAMENT SERIES</p>
            <p>© 2026 VALORANT TOURNAMENT SERIES. ALL RIGHTS RESERVED.</p>
        </div>
    </footer>

    {client_js}
</body>
</html>
"""


async def get_confirm_page(request: web.Request) -> web.Response:
    token = request.match_info.get("token")
    pool: asyncpg.Pool = request.app["db_pool"]

    # Look up token in DB
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT et.token, et.team_id, et.expires_at, et.used, t.team_name, t.captain_ign
            FROM email_tokens et
            JOIN teams t ON et.team_id = t.team_id
            WHERE et.token = $1
            """,
            token,
        )

    if not row:
        content = """
        <div class="text-center">
            <h2 class="font-display text-2xl font-bold text-red-500 mb-4">Invalid Activation Link</h2>
            <p class="text-zinc-400 mb-6">This verification link is invalid. Please double check your email or contact support.</p>
            <div class="h-px bg-zinc-800 my-6"></div>
            <p class="text-xs text-zinc-600">Verification Link Error</p>
        </div>
        """
        return web.Response(text=_get_base_html("Invalid Token", content), content_type="text/html")

    team_name = row["team_name"]
    captain_ign = row["captain_ign"]
    used = row["used"]
    expires_at = row["expires_at"]
    
    # Ensure timezone aware comparison
    now = datetime.datetime.now(datetime.timezone.utc)
    is_expired = now > expires_at

    if used:
        content = f"""
        <div class="text-center">
            <h2 class="font-display text-2xl font-bold text-emerald-500 mb-4">Already Confirmed</h2>
            <p class="text-zinc-400 mb-6">The team <strong>{team_name}</strong> has already been confirmed. You are ready for the tournament!</p>
            <div class="h-px bg-zinc-800 my-6"></div>
            <p class="text-xs text-emerald-600 font-semibold font-display tracking-widest uppercase">Verified</p>
        </div>
        """
        return web.Response(text=_get_base_html("Confirmed", content), content_type="text/html")

    if is_expired:
        content = f"""
        <div class="text-center" id="card-content">
            <h2 class="font-display text-2xl font-bold text-red-500 mb-4">Activation Link Expired</h2>
            <p class="text-zinc-400 mb-6">Verification links expire after 1 hour. Request a new token below to continue.</p>
            <button onclick="requestNewToken()" id="action-btn" class="w-full bg-red-500 hover:bg-red-600 text-white font-display text-xs font-bold tracking-widest uppercase py-3 transition-colors">
                Request New Activation Token
            </button>
            <div class="h-px bg-zinc-800 my-6"></div>
            <p class="text-xs text-zinc-600">Token Expired</p>
        </div>
        """
        client_js = f"""
        <script>
            async function requestNewToken() {{
                const btn = document.getElementById("action-btn");
                btn.disabled = true;
                btn.innerText = "Processing...";
                try {{
                    const res = await fetch("/api/resend/{token}", {{ method: "POST" }});
                    if (res.ok) {{
                        document.getElementById("card-content").innerHTML = `
                            <h2 class="font-display text-2xl font-bold text-emerald-500 mb-4">New Token Sent</h2>
                            <p class="text-zinc-400 mb-6">A new activation link has been sent to your registered captain email address. Please check your Gmail (+ spam folders).</p>
                            <div class="h-px bg-zinc-850 my-6"></div>
                            <p class="text-xs text-emerald-600 font-semibold font-display tracking-widest uppercase">Sent</p>
                        `;
                    }} else {{
                        const data = await res.json();
                        alert("Error: " + (data.detail || "Could not regenerate token."));
                        btn.disabled = false;
                        btn.innerText = "Request New Activation Token";
                    }}
                }} catch (e) {{
                    alert("Network error: " + e.message);
                    btn.disabled = false;
                    btn.innerText = "Request New Activation Token";
                }}
            }}
        </script>
        """
        return web.Response(text=_get_base_html("Token Expired", content, client_js), content_type="text/html")

    # Valid, unused, not expired token -> show verification button
    content = f"""
    <div class="text-center" id="card-content">
        <h2 class="font-display text-2xl font-bold text-white mb-2">Roster Provisioning</h2>
        <p class="text-zinc-400 text-sm mb-6">Confirm registration for team: <strong class="text-red-500">{team_name}</strong></p>
        <div class="bg-zinc-950 p-4 border border-zinc-800 text-left mb-6 text-sm flex flex-col gap-2">
            <div><span class="text-zinc-500">Captain IGN:</span> {captain_ign}</div>
            <div><span class="text-zinc-500">Expires in:</span> <span id="countdown" class="text-red-400 font-mono">Calculating...</span></div>
        </div>
        <button onclick="confirmRegistration()" id="action-btn" class="w-full bg-red-500 hover:bg-red-600 text-white font-display text-xs font-bold tracking-widest uppercase py-3 transition-colors">
            Confirm Registration
        </button>
        <div class="h-px bg-zinc-800 my-6"></div>
        <p class="text-xs text-zinc-600">Pending Verification</p>
    </div>
    """

    # Add a real-time countdown timer in client browser
    expires_timestamp = expires_at.timestamp() * 1000
    client_js = f"""
    <script>
        const target = {expires_timestamp};
        function updateTimer() {{
            const now = new Date().getTime();
            const diff = target - now;
            if (diff <= 0) {{
                location.reload();
                return;
            }}
            const mins = Math.floor(diff / 60000);
            const secs = Math.floor((diff % 60000) / 1000);
            document.getElementById("countdown").innerText = mins + "m " + secs + "s";
        }}
        setInterval(updateTimer, 1000);
        updateTimer();

        async function confirmRegistration() {{
            const btn = document.getElementById("action-btn");
            btn.disabled = true;
            btn.innerText = "Confirming...";
            try {{
                const res = await fetch("/api/confirm/{token}", {{ method: "POST" }});
                if (res.ok) {{
                    document.getElementById("card-content").innerHTML = `
                        <h2 class="font-display text-2xl font-bold text-emerald-500 mb-4">Registration Confirmed</h2>
                        <p class="text-zinc-400 mb-6">Roster provisioned successfully for team <strong>{team_name}</strong>. You are authorized to begin the roster finalization phase on Discord.</p>
                        <div class="h-px bg-zinc-800 my-6"></div>
                        <p class="text-xs text-emerald-600 font-semibold font-display tracking-widest uppercase">Success</p>
                    `;
                }} else {{
                    const data = await res.json();
                    alert("Error: " + (data.detail || "Could not confirm."));
                    btn.disabled = false;
                    btn.innerText = "Confirm Registration";
                }}
            }} catch (e) {{
                alert("Network error: " + e.message);
                btn.disabled = false;
                btn.innerText = "Confirm Registration";
            }}
        }}
    </script>
    """
    return web.Response(text=_get_base_html("Confirm Registration", content, client_js), content_type="text/html")


async def get_resend_page(request: web.Request) -> web.Response:
    """Fallback page showing a Request New Activation Token button if they navigate directly."""
    token = request.match_info.get("token")
    content = f"""
    <div class="text-center" id="card-content">
        <h2 class="font-display text-2xl font-bold text-white mb-4">Request New Link</h2>
        <p class="text-zinc-400 mb-6">Request a new secure activation link for your team registration.</p>
        <button onclick="requestNewToken()" id="action-btn" class="w-full bg-red-500 hover:bg-red-600 text-white font-display text-xs font-bold tracking-widest uppercase py-3 transition-colors">
            Request New Activation Token
        </button>
        <div class="h-px bg-zinc-800 my-6"></div>
        <p class="text-xs text-zinc-600">Verification Resend</p>
    </div>
    """
    client_js = f"""
    <script>
        async function requestNewToken() {{
            const btn = document.getElementById("action-btn");
            btn.disabled = true;
            btn.innerText = "Processing...";
            try {{
                const res = await fetch("/api/resend/{token}", {{ method: "POST" }});
                if (res.ok) {{
                    document.getElementById("card-content").innerHTML = `
                        <h2 class="font-display text-2xl font-bold text-emerald-500 mb-4">New Token Sent</h2>
                        <p class="text-zinc-400 mb-6">A new activation link has been sent to your registered email address. Please check your Gmail.</p>
                        <div class="h-px bg-zinc-850 my-6"></div>
                        <p class="text-xs text-emerald-600 font-semibold font-display tracking-widest uppercase">Sent</p>
                    `;
                }} else {{
                    const data = await res.json();
                    alert("Error: " + (data.detail || "Could not regenerate token."));
                    btn.disabled = false;
                    btn.innerText = "Request New Activation Token";
                }}
            }} catch (e) {{
                alert("Network error: " + e.message);
                btn.disabled = false;
                btn.innerText = "Request New Activation Token";
            }}
        }}
    </script>
    """
    return web.Response(text=_get_base_html("Resend Token", content, client_js), content_type="text/html")


async def api_confirm_token(request: web.Request) -> web.Response:
    token = request.match_info.get("token")
    pool: asyncpg.Pool = request.app["db_pool"]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT team_id, expires_at, used FROM email_tokens WHERE token = $1",
            token,
        )
        if not row:
            return web.json_response({"detail": "Token not found."}, status=404)

        if row["used"]:
            return web.json_response({"detail": "Token already used."}, status=400)

        # Make sure now is offset-aware
        now = datetime.datetime.now(datetime.timezone.utc)
        if now > row["expires_at"]:
            return web.json_response({"detail": "Token has expired."}, status=400)

        team_id = row["team_id"]

        # Update in transaction
        async with conn.transaction():
            # Mark token as used
            await conn.execute(
                "UPDATE email_tokens SET used = TRUE WHERE token = $1",
                token,
            )
            # Confirm team email
            await conn.execute(
                "UPDATE teams SET email_confirmed = TRUE WHERE team_id = $1",
                team_id,
            )

    log.info(f"Team {team_id} registration confirmed via web server.")
    return web.json_response({"status": "success"})


async def api_resend_token(request: web.Request) -> web.Response:
    token = request.match_info.get("token")
    pool: asyncpg.Pool = request.app["db_pool"]

    async with pool.acquire() as conn:
        # Find the team linked to the expired/old token
        row = await conn.fetchrow(
            """
            SELECT et.team_id, t.team_name, t.captain_email, t.captain_ign, t.email_confirmed
            FROM email_tokens et
            JOIN teams t ON et.team_id = t.team_id
            WHERE et.token = $1
            """,
            token,
        )

        if not row:
            return web.json_response({"detail": "Token not found."}, status=404)

        if row["email_confirmed"]:
            return web.json_response({"detail": "Team already confirmed."}, status=400)

        team_id = row["team_id"]
        team_name = row["team_name"]
        recipient_email = row["captain_email"]
        captain_ign = row["captain_ign"]

        new_token = secrets.token_urlsafe(32)

        async with conn.transaction():
            # Invalidate all existing tokens for this team
            await conn.execute(
                "UPDATE email_tokens SET used = TRUE WHERE team_id = $1",
                team_id,
            )
            # Insert new token (expires in 1 hour)
            await conn.execute(
                """
                INSERT INTO email_tokens (token, team_id, expires_at)
                VALUES ($1, $2, NOW() + INTERVAL '1 hour')
                """,
                new_token, team_id,
            )

    # Send new email
    try:
        await mailer.send_confirmation_email(recipient_email, captain_ign, new_token)
        log.info(f"Resent confirmation email to {recipient_email} for team '{team_name}'.")
    except Exception as e:
        log.error(f"Failed to resend confirmation email to {recipient_email}: {e}")
        return web.json_response({"detail": "Failed to send confirmation email."}, status=500)

    return web.json_response({"status": "success"})


def create_app() -> web.Application:
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    app.router.add_get("/confirm/{token}", get_confirm_page)
    app.router.add_get("/resend-page/{token}", get_resend_page)
    app.router.add_post("/api/confirm/{token}", api_confirm_token)
    app.router.add_post("/api/resend/{token}", api_resend_token)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8080)
