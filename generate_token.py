import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def main():
    print("==================================================")
    # Prompt for user name (matching exactly their Face ID/recognized name, e.g. Afthab)
    name = input("Enter the EXACT name of the person (e.g. Afthab, Pavan): ").strip()
    if not name:
        print("❌ Error: Name cannot be empty!")
        return

    # Ensure token folder exists
    token_dir = "calendar_tokens"
    os.makedirs(token_dir, exist_ok=True)
    
    if not os.path.exists('credentials.json'):
        print("❌ Error: 'credentials.json' is missing from this folder!")
        print("Please make sure your OAuth client configuration 'credentials.json' is present in the repository root.")
        return

    print(f"\nOpening browser to authenticate Google Calendar events for {name}...")
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    token_filename = os.path.join(token_dir, f"{name}_token.json")
    with open(token_filename, 'w') as token:
        token.write(creds.to_json())
        
    print(f"\n✅ Success! {token_filename} has been created and saved.")

if __name__ == '__main__':
    main()
