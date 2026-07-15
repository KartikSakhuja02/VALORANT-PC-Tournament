"""
mailer.py — SMTP email helper using aiosmtplib.
Sends the HTML confirmation email to the team captain.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib

import config

log = logging.getLogger("valorant-bot.mailer")


def _get_email_html(captain_ign: str, token: str) -> str:
    """Generate the HTML body for the confirmation email with inlined styles."""
    confirm_url = f"{config.VERCEL_WEBPAGE_URL}/?token={token}&api={config.CONFIRMATION_SERVER_URL}"
    resend_url = f"{config.VERCEL_WEBPAGE_URL}/?token={token}&api={config.CONFIRMATION_SERVER_URL}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Confirmed | VALORANT TOURNAMENT SERIES</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: #f3f4f6;
            font-family: 'Inter', Arial, sans-serif;
            color: #271717;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}
        table {{
            border-collapse: collapse !important;
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: 'Inter', Arial, sans-serif; color: #271717;">
    <div style="width: 100%; background-color: #f3f4f6; padding: 40px 0; display: flex; justify-content: center;">
        <!-- Main Card Wrapper -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; margin: 0 auto; border: 0;">
            <tbody>
                <!-- Header -->
                <tr>
                    <td align="center" style="background-color: #ff4655; height: 80px; padding: 0 40px; text-align: center;">
                        <h1 style="margin: 0; font-family: 'Montserrat', Arial, sans-serif; font-size: 18px; font-weight: 800; letter-spacing: 0.2em; color: #ffffff; text-transform: uppercase;">
                            VALORANT TOURNAMENT SERIES
                        </h1>
                    </td>
                </tr>
                
                <!-- Content -->
                <tr>
                    <td style="padding: 40px 40px 0 40px;">
                        <h2 style="margin: 0 0 16px 0; font-family: 'Montserrat', Arial, sans-serif; font-size: 28px; font-weight: 700; color: #271717;">
                            Welcome to the Tournament, <span style="color: #ff4655; font-weight: 700;">{captain_ign}</span>!
                        </h2>
                        <p style="margin: 0; font-size: 18px; line-height: 28px; color: #5b403f;">
                            Your team provisioning has been successfully synchronized with our tournament database. Just one last step, confirm your roster using the button below. You are now authorized to begin the roster finalization phase.
                        </p>
                    </td>
                </tr>
                
                <!-- Button -->
                <tr>
                    <td align="center" style="padding: 32px 40px;">
                        <a href="{confirm_url}" style="display: inline-block; background-color: #ff4655; color: #ffffff; font-family: 'Montserrat', Arial, sans-serif; font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-decoration: none; padding: 16px 40px; text-transform: uppercase; border-radius: 0;">
                            CONFIRM
                        </a>
                    </td>
                </tr>
                
                <!-- Alert Box -->
                <tr>
                    <td style="padding: 0 40px 32px 40px;">
                        <div style="background-color: #fff0ef; border: 1px solid #e4bdbc; padding: 16px; text-align: left;">
                            <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 20px; color: #5b403f;">
                                <strong>Note:</strong> Your registration token is secure. If you need to regenerate your team keys, use the button below.
                            </p>
                            <a href="{resend_url}" style="display: block; border: 2px solid #1a202c; color: #1a202c; font-family: 'Inter', Arial, sans-serif; font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-decoration: none; padding: 10px; text-align: center; text-transform: uppercase;">
                                REQUEST NEW ACTIVATION TOKEN
                            </a>
                        </div>
                    </td>
                </tr>
                
                <!-- Process Info -->
                <tr>
                    <td style="padding: 24px 40px; border-top: 1px solid #e4bdbc;">
                        <h3 style="margin: 0 0 16px 0; font-family: 'Montserrat', Arial, sans-serif; font-size: 20px; font-weight: 700; color: #1a202c; text-transform: uppercase;">
                            Next Steps
                        </h3>
                        
                        <!-- Step 1 -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 24px;">
                            <tr>
                                <td valign="top" width="50" style="padding-top: 4px;">
                                    <div style="width: 40px; height: 40px; border-radius: 50%; background-color: #1a202c; color: #ffffff; text-align: center; line-height: 40px; font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 16px;">
                                        1
                                    </div>
                                </td>
                                <td valign="top" style="padding-left: 16px;">
                                    <h4 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 700; color: #1a202c;">Complete Player Registration</h4>
                                    <p style="margin: 0 0 8px 0; font-size: 14px; line-height: 20px; color: #5b403f;">Assign your 5 core players and 1 substitute via Discord ID.</p>
                                    <div style="background-color: #2b2d31; padding: 12px; border-radius: 0; display: inline-block;">
                                        <span style="background-color: rgba(255, 70, 85, 0.2); border: 1px solid #ff4655; color: #ff4655; font-size: 10px; padding: 4px 8px; font-weight: 700;">PENDING...</span>
                                    </div>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Step 2 -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 24px;">
                            <tr>
                                <td valign="top" width="50" style="padding-top: 4px;">
                                    <div style="width: 40px; height: 40px; border-radius: 50%; background-color: #1a202c; color: #ffffff; text-align: center; line-height: 40px; font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 16px;">
                                        2
                                    </div>
                                </td>
                                <td valign="top" style="padding-left: 16px;">
                                    <h4 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 700; color: #1a202c;">Track Invitations</h4>
                                    <p style="margin: 0; font-size: 14px; line-height: 20px; color: #5b403f;">Monitor your roster dashboard to ensure all players have accepted the invite via the verification link.</p>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Step 3 -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                            <tr>
                                <td valign="top" width="50" style="padding-top: 4px;">
                                    <div style="width: 40px; height: 40px; border-radius: 50%; background-color: #1a202c; color: #ffffff; text-align: center; line-height: 40px; font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 16px;">
                                        3
                                    </div>
                                </td>
                                <td valign="top" style="padding-left: 16px;">
                                    <h4 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 700; color: #1a202c;">Lock Your Roster</h4>
                                    <p style="margin: 0; font-size: 14px; line-height: 20px; color: #5b403f;">Once all 6 slots are verified, your roster will lock automatically for seeding.</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                
                <!-- Footer -->
                <tr>
                    <td style="background-color: #1a202c; padding: 32px 40px; text-align: center;">
                        <div style="font-family: 'Montserrat', Arial, sans-serif; font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.01em; text-transform: uppercase; margin-bottom: 16px;">
                            VALORANT TOURNAMENT SERIES
                        </div>
                        <div style="font-size: 14px; color: #c1c6d7; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px;">
                            <a href="#" style="color: #c1c6d7; text-decoration: none; margin-right: 8px;">Support</a>
                            <span style="color: rgba(193, 198, 215, 0.3);">|</span>
                            <a href="#" style="color: #c1c6d7; text-decoration: none; margin: 0 8px;">Tournament Rules</a>
                            <span style="color: rgba(193, 198, 215, 0.3);">|</span>
                            <a href="#" style="color: #c1c6d7; text-decoration: none; margin-left: 8px;">Contact</a>
                        </div>
                        <p style="margin: 0; font-size: 14px; line-height: 20px; color: rgba(193, 198, 215, 0.6); max-width: 400px; margin: 0 auto;">
                            © 2026 VALORANT TOURNAMENT SERIES. ALL RIGHTS RESERVED. RIOT GAMES, VALORANT, AND ALL ASSOCIATED LOGOS ARE TRADEMARKS OR REGISTERED TRADEMARKS OF RIOT GAMES, INC.
                        </p>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>
"""


async def send_confirmation_email(recipient_email: str, captain_ign: str, token: str) -> None:
    """Send verification email to recipient_email via aiosmtplib."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Confirm your Team Registration | VALORANT Tournament Series"
    msg["From"] = config.SMTP_EMAIL
    msg["To"] = recipient_email

    # Plain text fallback
    confirm_url = f"{config.VERCEL_WEBPAGE_URL}/?token={token}&api={config.CONFIRMATION_SERVER_URL}"
    resend_url = f"{config.VERCEL_WEBPAGE_URL}/?token={token}&api={config.CONFIRMATION_SERVER_URL}"
    text_content = (
        f"Welcome to the Tournament, {captain_ign}!\n\n"
        f"Please confirm your team registration by visiting the following link within 1 hour:\n"
        f"{confirm_url}\n\n"
        f"If the link has expired, you can request a new one here:\n"
        f"{resend_url}\n\n"
        f"VALORANT Tournament Series"
    )

    html_content = _get_email_html(captain_ign, token)

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    log.info(f"Sending confirmation email to {recipient_email}...")
    try:
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=465,
            username=config.SMTP_EMAIL,
            password=config.SMTP_PASSWORD,
            use_tls=True,
        )
        log.info(f"Email successfully sent to {recipient_email}.")
    except Exception as e:
        log.exception(f"Failed to send email to {recipient_email}: {e}")
        raise e
