"""
mailer.py — Gmail API email sender for the VALORANT Tournament Bot.

Shared by both bot.py (for initial confirmation email) and
confirmation_server/main.py (for resend requests).
"""
from __future__ import annotations

import asyncio
import base64
import secrets
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import asyncpg
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import config

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_EXPIRY_HOURS = 1


# ── Gmail service ─────────────────────────────────────────────────────────────

def _build_gmail_service():
    """Build a Gmail API service client using the stored OAuth2 refresh token."""
    creds = Credentials(
        token=None,
        refresh_token=config.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.GMAIL_CLIENT_ID,
        client_secret=config.GMAIL_CLIENT_SECRET,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ── Email HTML template ───────────────────────────────────────────────────────

def _confirmation_email_html(
    captain_ign: str,
    confirm_url: str,
    resend_url: str,
) -> str:
    """
    Returns the full HTML email body.
    Inline styles are used throughout for email client compatibility.
    Same design language as the Vercel confirmation page.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Confirm Your Registration | VALORANT Tournament Series</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Inter:wght@400;500;700&display=swap');
    body {{ margin:0; padding:0; background-color:#f3f4f6; }}
    table {{ border-collapse:collapse; }}
    a {{ text-decoration:none; }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:'Inter',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f3f4f6;padding:40px 0;">
  <tr><td align="center">

    <table width="600" cellpadding="0" cellspacing="0" border="0"
           style="max-width:600px;width:100%;background-color:#ffffff;">

      <!-- ── Header ─────────────────────────────────────────────────── -->
      <tr>
        <td align="center"
            style="background-color:#FF4655;padding:28px 40px;">
          <div style="font-family:'Montserrat',Arial,sans-serif;font-size:17px;
                      font-weight:800;letter-spacing:0.22em;color:#ffffff;
                      text-transform:uppercase;">
            VALORANT TOURNAMENT SERIES
          </div>
        </td>
      </tr>

      <!-- ── Welcome ────────────────────────────────────────────────── -->
      <tr>
        <td style="padding:32px 40px 0 40px;">
          <h2 style="margin:0 0 16px 0;font-family:'Montserrat',Arial,sans-serif;
                     font-size:26px;font-weight:700;color:#271717;
                     letter-spacing:-0.01em;line-height:1.3;">
            Welcome to the Tournament,&nbsp;
            <span style="color:#FF4655;">{captain_ign}</span>!
          </h2>
          <p style="margin:0;font-family:'Inter',Arial,sans-serif;font-size:17px;
                    line-height:27px;color:#5b403f;">
            Your team provisioning has been successfully synchronized with our
            tournament database. Just one last step &mdash; confirm your
            registration using the button below.
          </p>
        </td>
      </tr>

      <!-- ── CTA Button ─────────────────────────────────────────────── -->
      <tr>
        <td align="center" style="padding:32px 40px;">
          <a href="{confirm_url}"
             style="display:inline-block;background-color:#FF4655;color:#ffffff;
                    font-family:'Montserrat',Arial,sans-serif;font-size:12px;
                    font-weight:800;letter-spacing:0.12em;text-transform:uppercase;
                    padding:16px 44px;">
            CONFIRM
          </a>
        </td>
      </tr>

      <!-- ── Info Box ───────────────────────────────────────────────── -->
      <tr>
        <td style="padding:0 40px 32px 40px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="border:1px solid #e4bdbc;background-color:#fff0ef;">
            <tr>
              <td style="padding:16px;">
                <p style="margin:0 0 14px 0;font-family:'Inter',Arial,sans-serif;
                          font-size:14px;line-height:21px;color:#5b403f;">
                  <strong>Note:</strong> This confirmation link is valid for
                  <strong>1 hour</strong>. If it expires, request a new one
                  using the button below.
                </p>
                <a href="{resend_url}"
                   style="display:inline-block;border:2px solid #1a202c;
                          color:#1a202c;font-family:'Inter',Arial,sans-serif;
                          font-size:11px;font-weight:700;letter-spacing:0.1em;
                          text-transform:uppercase;padding:8px 16px;">
                  REQUEST NEW ACTIVATION TOKEN
                </a>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- ── Next Steps ─────────────────────────────────────────────── -->
      <tr>
        <td style="padding:24px 40px 32px 40px;border-top:1px solid #e4bdbc;">
          <h3 style="margin:0 0 24px 0;font-family:'Montserrat',Arial,sans-serif;
                     font-size:18px;font-weight:700;color:#1a202c;
                     text-transform:uppercase;">
            Next Steps
          </h3>

          <!-- Step 1 -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="margin-bottom:20px;">
            <tr>
              <td width="44" valign="top" style="padding-right:16px;">
                <div style="width:40px;height:40px;background-color:#1a202c;
                            color:#ffffff;font-family:'Montserrat',Arial,sans-serif;
                            font-weight:700;font-size:15px;text-align:center;
                            line-height:40px;border-radius:9999px;">1</div>
              </td>
              <td valign="top">
                <div style="font-family:'Inter',Arial,sans-serif;font-size:15px;
                            font-weight:700;color:#1a202c;margin-bottom:4px;">
                  Complete Player Registration
                </div>
                <div style="font-family:'Inter',Arial,sans-serif;font-size:13px;
                            line-height:19px;color:#5b403f;">
                  Assign your 5 core players and 1 substitute via Discord.
                </div>
              </td>
            </tr>
          </table>

          <!-- Step 2 -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="margin-bottom:20px;">
            <tr>
              <td width="44" valign="top" style="padding-right:16px;">
                <div style="width:40px;height:40px;background-color:#1a202c;
                            color:#ffffff;font-family:'Montserrat',Arial,sans-serif;
                            font-weight:700;font-size:15px;text-align:center;
                            line-height:40px;border-radius:9999px;">2</div>
              </td>
              <td valign="top">
                <div style="font-family:'Inter',Arial,sans-serif;font-size:15px;
                            font-weight:700;color:#1a202c;margin-bottom:4px;">
                  Track Invitations
                </div>
                <div style="font-family:'Inter',Arial,sans-serif;font-size:13px;
                            line-height:19px;color:#5b403f;">
                  Monitor your roster to ensure all players have accepted the invite.
                </div>
              </td>
            </tr>
          </table>

          <!-- Step 3 -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td width="44" valign="top" style="padding-right:16px;">
                <div style="width:40px;height:40px;background-color:#1a202c;
                            color:#ffffff;font-family:'Montserrat',Arial,sans-serif;
                            font-weight:700;font-size:15px;text-align:center;
                            line-height:40px;border-radius:9999px;">3</div>
              </td>
              <td valign="top">
                <div style="font-family:'Inter',Arial,sans-serif;font-size:15px;
                            font-weight:700;color:#1a202c;margin-bottom:4px;">
                  Lock Your Roster
                </div>
                <div style="font-family:'Inter',Arial,sans-serif;font-size:13px;
                            line-height:19px;color:#5b403f;">
                  Once all 6 slots are verified, your roster will lock automatically.
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- ── Footer ─────────────────────────────────────────────────── -->
      <tr>
        <td style="background-color:#1a202c;padding:32px 40px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td align="center">
                <div style="font-family:'Montserrat',Arial,sans-serif;font-size:18px;
                            font-weight:700;color:#ffffff;text-transform:uppercase;
                            letter-spacing:-0.01em;margin-bottom:14px;">
                  VALORANT TOURNAMENT SERIES
                </div>
                <div style="margin-bottom:14px;">
                  <span style="font-family:'Inter',Arial,sans-serif;font-size:11px;
                               color:#c1c6d7;letter-spacing:0.1em;text-transform:uppercase;
                               margin:0 8px;">Support</span>
                  <span style="color:#c1c6d7;opacity:0.4;">|</span>
                  <span style="font-family:'Inter',Arial,sans-serif;font-size:11px;
                               color:#c1c6d7;letter-spacing:0.1em;text-transform:uppercase;
                               margin:0 8px;">Tournament Rules</span>
                  <span style="color:#c1c6d7;opacity:0.4;">|</span>
                  <span style="font-family:'Inter',Arial,sans-serif;font-size:11px;
                               color:#c1c6d7;letter-spacing:0.1em;text-transform:uppercase;
                               margin:0 8px;">Contact</span>
                </div>
                <div style="font-family:'Inter',Arial,sans-serif;font-size:11px;
                            color:#c1c6d7;opacity:0.6;max-width:400px;
                            text-align:center;margin:0 auto;line-height:17px;">
                  &copy; 2026 VALORANT TOURNAMENT SERIES. ALL RIGHTS RESERVED.
                  RIOT GAMES, VALORANT, AND ALL ASSOCIATED LOGOS ARE TRADEMARKS
                  OR REGISTERED TRADEMARKS OF RIOT GAMES, INC.
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


# ── Sync send (runs in thread pool) ──────────────────────────────────────────

def _send_email_sync(
    to: str,
    captain_ign: str,
    confirm_url: str,
    resend_url: str,
) -> None:
    service = _build_gmail_service()
    html = _confirmation_email_html(captain_ign, confirm_url, resend_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Confirm Your Team Registration — VALORANT Tournament Series"
    msg["From"] = config.GMAIL_SENDER
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


# ── Token helpers (async) ─────────────────────────────────────────────────────

async def generate_token(pool: asyncpg.Pool, team_id: int) -> str:
    """Invalidate previous tokens for this team, create a new one, return it."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE email_tokens SET used = TRUE WHERE team_id = $1 AND used = FALSE",
            team_id,
        )
        await conn.execute(
            "INSERT INTO email_tokens (token, team_id, expires_at) VALUES ($1, $2, $3)",
            token, team_id, expires_at,
        )

    return token


async def send_confirmation_email(
    pool: asyncpg.Pool,
    team_id: int,
    captain_ign: str,
    captain_email: str,
) -> None:
    """
    Generate a token, build the confirmation email, and send it.
    The confirmation link points to the Vercel frontend (config.FRONTEND_URL).
    """
    token = await generate_token(pool, team_id)
    confirm_url = f"{config.FRONTEND_URL}/confirm/{token}"
    resend_url  = f"{config.FRONTEND_URL}/confirm/{token}"  # same page handles resend

    await asyncio.to_thread(
        _send_email_sync, captain_email, captain_ign, confirm_url, resend_url
    )
