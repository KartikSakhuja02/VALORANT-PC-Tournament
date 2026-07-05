"""
gmail_setup.py — One-time setup script to authenticate with Gmail API and generate token.json.
Make sure to put your credentials.json (downloaded from Google Cloud Console) in this folder before running.

Usage:
  python gmail_setup.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        print("Existing token.json found.")
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired. Refreshing...")
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                print("Error: 'credentials.json' not found!")
                print("Please download it from the Google Cloud Console (OAuth Client ID -> Desktop App)")
                print("and place it in this directory: c:\\Users\\karti\\OneDrive\\Documents\\VALORANT PC Tournament\\credentials.json")
                return
            
            print("Starting authorization flow...")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
        print("Success! token.json has been written.")

if __name__ == "__main__":
    main()
