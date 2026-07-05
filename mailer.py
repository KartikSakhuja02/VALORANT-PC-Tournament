"""
mailer.py — Sends HTML confirmation emails using the Gmail API.
"""

import base64
import os
import logging
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

import config

log = logging.getLogger("valorant-bot.mailer")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# HTML Email Template with placeholders for dynamic content
EMAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta content="width=device-width, initial-scale=1.0" name="viewport">
    <title>Registration Confirmed | VALORANT TOURNAMENT SERIES</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
            background-color: #f3f4f6;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #271717;
        }}
        table {{
            border-collapse: collapse !important;
        }}
        .card-wrapper {{
            width: 100%;
            max-width: 600px;
            background-color: #ffffff;
            margin: 40px auto;
            border: 0;
        }}
        .header {{
            background-color: #ff4655;
            padding: 24px 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-family: 'Montserrat', sans-serif;
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 0.2em;
            color: #ffffff;
            text-transform: uppercase;
        }}
        .content {{
            padding: 40px;
        }}
        .headline {{
            font-family: 'Montserrat', sans-serif;
            font-size: 28px;
            line-height: 34px;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 16px;
            color: #271717;
        }}
        .highlight {{
            color: #ff4655;
        }}
        .body-text {{
            font-size: 18px;
            line-height: 28px;
            color: #5b403f;
            margin-bottom: 32px;
        }}
        .btn-container {{
            text-align: center;
            margin-bottom: 32px;
        }}
        .btn {{
            display: inline-block;
            background-color: #ff4655;
            color: #ffffff !important;
            font-family: 'Montserrat', sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-decoration: none;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 16px 40px;
            transition: transform 0.1s ease;
        }}
        .info-box {{
            background-color: #fff0ef;
            border: 1px solid #e4bdbc;
            padding: 16px;
            margin-bottom: 32px;
        }}
        .info-box p {{
            margin: 0 0 16px 0;
            font-size: 14px;
            line-height: 20px;
            color: #5b403f;
        }}
        .btn-outline {{
            display: block;
            border: 2px solid #1a202c;
            color: #1a202c !important;
            font-family: 'Montserrat', sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-decoration: none;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 12px 16px;
            text-align: center;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        .btn-outline:hover {{
            background-color: #1a202c;
            color: #ffffff !important;
        }}
        .divider {{
            border-top: 1px solid #e4bdbc;
            padding-top: 24px;
            margin-top: 24px;
        }}
        .section-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 20px;
            line-height: 26px;
            font-weight: 700;
            text-transform: uppercase;
            color: #1a202c;
            margin-top: 0;
            margin-bottom: 24px;
        }}
        .step-row {{
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
        }}
        .step-num {{
            flex-shrink: 0;
            width: 40px;
            height: 40px;
            border-radius: 9999px;
            background-color: #1a202c;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-family: 'Montserrat', sans-serif;
            font-weight: 800;
            font-size: 16px;
        }}
        .step-content {{
            flex-grow: 1;
        }}
        .step-title {{
            margin: 0 0 4px 0;
            font-size: 16px;
            font-weight: 700;
            color: #1a202c;
        }}
        .step-desc {{
            margin: 0;
            font-size: 14px;
            line-height: 20px;
            color: #5b403f;
        }}
        .discord-mock {{
            background-color: #2b2d31;
            padding: 12px;
            border-radius: 6px;
            margin-top: 8px;
            display: inline-block;
        }}
        .badge {{
            background-color: rgba(255, 70, 85, 0.2);
            border: 1px solid #ff4655;
            color: #ff4655;
            font-size: 10px;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .footer {{
            background-color: #1a202c;
            padding: 32px;
            text-align: center;
            color: #c1c6d7;
        }}
        .footer-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: #ffffff;
            text-transform: uppercase;
            margin-bottom: 16px;
        }}
        .footer-links {{
            margin-bottom: 16px;
            font-size: 14px;
        }}
        .footer-links a {{
            color: #c1c6d7;
            text-decoration: none;
            margin: 0 8px;
            text-transform: uppercase;
            font-weight: 500;
        }}
        .footer-links a:hover {{
            color: #ff4655;
        }}
        .footer-copyright {{
            font-size: 14px;
            color: rgba(193, 198, 215, 0.6);
            line-height: 20px;
            max-width: 400px;
            margin: 16px auto 0 auto;
        }}
    </style>
</head>
<body>
    <div style="background-color: #f3f4f6; padding: 40px 0;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" class="card-wrapper">
            <tbody>
                <tr>
                    <td>
                        <div class="header">
                            <h1>VALORANT TOURNAMENT SERIES</h1>
                        </div>
                    </td>
                </tr>
                <tr>
                    <td class="content">
                        <h2 class="headline">
                            Welcome to the Tournament, <span class="highlight">{captain_ign}</span>!
                        </h2>
                        <p class="body-text">
                            Your team provisioning has been successfully synchronized with our tournament database. Just one last step: confirm your roster using the button below. You are now authorized to begin the roster finalization phase.
                        </p>
                        <div class="btn-container">
                            <a class="btn" href="{confirm_link}">confirm</a>
                        </div>
                        <div class="info-box">
                            <p><strong>Note:</strong> Your registration token is secure. If you need to regenerate your team keys, use the button below.</p>
                            <a class="btn-outline" href="{resend_link}">REQUEST NEW ACTIVATION TOKEN</a>
                        </div>
                        <div class="divider">
                            <h3 class="section-title">Next Steps</h3>
                            
                            <!-- Step 1 -->
                            <div class="step-row">
                                <div class="step-num">1</div>
                                <div class="step-content">
                                    <h4 class="step-title">Complete Player Registration</h4>
                                    <p class="step-desc">Assign your 5 core players and 1 substitute via Discord ID.</p>
                                    <div class="discord-mock">
                                        <span class="badge">PENDING...</span>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Step 2 -->
                            <div class="step-row">
                                <div class="step-num">2</div>
                                <div class="step-content">
                                    <h4 class="step-title">Track Invitations</h4>
                                    <p class="step-desc">Monitor your roster dashboard to ensure all players have accepted the invite via the verification link.</p>
                                </div>
                            </div>
                            
                            <!-- Step 3 -->
                            <div class="step-row">
                                <div class="step-num">3</div>
                                <div class="step-content">
                                    <h4 class="step-title">Lock Your Roster</h4>
                                    <p class="step-desc">Once all 6 slots are verified, your roster will lock automatically for seeding.</p>
                                </div>
                            </div>
                        </div>
                    </td>
                </tr>
                <tr>
                    <td class="footer">
                        <div class="footer-title">VALORANT TOURNAMENT SERIES</div>
                        <div class="footer-links">
                            <a href="#">Support</a>
                            <span style="color: rgba(193,198,215,0.3)">|</span>
                            <a href="#">Tournament Rules</a>
                            <span style="color: rgba(193,198,215,0.3)">|</span>
                            <a href="#">Contact</a>
                        </div>
                        <p class="footer-copyright">
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

def _get_gmail_service():
    """Builds and returns the Gmail service object using token.json."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(project_root, "token.json")
    
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            "token.json not found. Please run gmail_setup.py first to authorize your Gmail API access."
        )

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If the token is expired, refresh it
    if creds and creds.expired and creds.refresh_token:
        log.info("Gmail API credentials expired, refreshing...")
        creds.refresh(Request())
        # Save refreshed credentials
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())
            
    return build("gmail", "v1", credentials=creds)

async def send_confirmation_email(
    captain_ign: str,
    recipient_email: str,
    confirm_link: str,
    resend_link: str
) -> bool:
    """
    Sends the HTML confirmation email to the captain.
    Returns True if successful, False otherwise.
    """
    try:
        service = _get_gmail_service()
        
        # Format the HTML body with custom parameters
        html_content = EMAIL_TEMPLATE.format(
            captain_ign=captain_ign,
            confirm_link=confirm_link,
            resend_link=resend_link
        )
        
        # Create MIME message
        message = MIMEText(html_content, "html")
        message["to"] = recipient_email
        message["from"] = os.getenv("GMAIL_SENDER", "me")
        message["subject"] = "Roster Action Required: Confirm Your VALORANT PC Tournament Registration"
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        body = {"raw": raw_message}
        
        log.info(f"Sending confirmation email to {recipient_email}...")
        service.users().messages().send(userId="me", body=body).execute()
        log.info(f"Confirmation email successfully sent to {recipient_email}")
        return True
        
    except Exception:
        log.exception(f"Failed to send confirmation email to {recipient_email}")
        return False
