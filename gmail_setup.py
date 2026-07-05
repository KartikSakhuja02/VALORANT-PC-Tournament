"""
gmail_setup.py — One-time Gmail OAuth2 setup script.

Run this ONCE on a machine with a web browser (your Windows PC):
    pip install google-auth-oauthlib
    python gmail_setup.py

It will open a browser, ask you to sign in with the Gmail account that
will send tournament emails, then print the credentials to paste into .env.

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create a project → Enable "Gmail API"
  3. OAuth consent screen → External → Add your Gmail as test user
  4. Credentials → Create OAuth client ID → Desktop app
  5. Download the JSON → save as "credentials.json" in this folder
  6. Run this script
"""

import json
import os

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Run: pip install google-auth-oauthlib")
    raise

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDS_FILE = "credentials.json"


def main() -> None:
    if not os.path.exists(CREDS_FILE):
        print(f"\n[ERROR] '{CREDS_FILE}' not found.")
        print("  Download it from Google Cloud Console:")
        print("  Credentials → your OAuth Desktop client → Download JSON")
        print(f"  Save it as '{CREDS_FILE}' in the project root.\n")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Also extract client_id / client_secret from the downloaded JSON
    with open(CREDS_FILE) as f:
        raw = json.load(f)
    client_info = raw.get("installed") or raw.get("web") or {}

    print("\n" + "=" * 60)
    print("  Copy these values into your .env file on the Pi:")
    print("=" * 60)
    print(f"GMAIL_CLIENT_ID={client_info.get('client_id', creds.client_id)}")
    print(f"GMAIL_CLIENT_SECRET={client_info.get('client_secret', creds.client_secret)}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 60)
    print("\nDone! You can delete credentials.json from the Pi (keep it safe).\n")


if __name__ == "__main__":
    main()
