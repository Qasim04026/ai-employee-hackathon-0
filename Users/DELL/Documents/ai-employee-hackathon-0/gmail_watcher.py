from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pathlib import Path
from datetime import datetime
import time
import os

VAULT_PATH = r"C:\Users\DELL\Documents\AI_Employee_Vault"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def watch_gmail():
    service = get_gmail_service()
    processed = set()
    needs_action = Path(VAULT_PATH) / 'Needs_Action'

    print("Gmail watcher started...")
    while True:
        try:
            results = service.users().messages().list(
                userId='me', q='is:unread is:important', maxResults=5
            ).execute()

            messages = results.get('messages', [])
            for msg in messages:
                if msg['id'] in processed:
                    continue

                full = service.users().messages().get(
                    userId='me', id=msg['id']
                ).execute()
                headers = {h['name']: h['value'] 
                          for h in full['payload']['headers']}

                filepath = needs_action / f'EMAIL_{msg["id"]}.md'
                filepath.write_text(
                    f'---\ntype: email\n'
                    f'from: {headers.get("From", "Unknown")}\n'
                    f'subject: {headers.get("Subject", "No Subject")}\n'
                    f'received: {datetime.now().isoformat()}\n'
                    f'status: pending\n---\n'
                    f'## Content\n{full.get("snippet", "")}\n\n'
                    f'## Suggested Actions\n'
                    f'- [ ] Reply to sender\n'
                    f'- [ ] Archive after processing\n'
                )
                processed.add(msg['id'])
                print(f"New email: {headers.get('Subject', 'No Subject')}")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(120)

watch_gmail()