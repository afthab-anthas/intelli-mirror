import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def main():
    name = input("Enter the EXACT name of the person (matching their Face ID name): ").strip()
    
    if not os.path.exists('credentials.json'):
        print("❌ Error: 'credentials.json' is missing from this folder!")
        return

    print(f"\nOpening browser to authenticate {name}...")
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    token_filename = f"{name}_token.json"
    with open(token_filename, 'w') as token:
        token.write(creds.to_json())
        
    print(f"\n✅ Success! {token_filename} has been created.")

if __name__ == '__main__':
    main()
