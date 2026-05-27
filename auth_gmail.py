"""
Run this script once locally to generate gmail_token.json.
After running, copy the contents of credentials/gmail_token.json
into Render as the GMAIL_TOKEN_JSON environment variable.
"""
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials/gmail_oauth.json",
        SCOPES
    )
    creds = flow.run_local_server(port=0)

    # Save token to file
    with open("credentials/gmail_token.json", "w") as f:
        f.write(creds.to_json())

    print("✅ Done! gmail_token.json saved to credentials/")
    print("Next step: copy its contents into Render as GMAIL_TOKEN_JSON env var.")

if __name__ == "__main__":
    main()
