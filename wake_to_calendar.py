import os
import sys
import time
import speech_recognition as sr
from google import genai
from dotenv import load_dotenv
import queue
from gtts import gTTS
import pygame
import io
import json
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- SETUP AUDIO QUEUE & TTS ---
speech_queue = queue.Queue()
is_speaking = False

def speak(text):
    global is_speaking
    is_speaking = True
    try:
        clean_text = text.replace('*', '').replace('#', '')
        print(f"[Audio] Speaking: {clean_text}")
        tts = gTTS(text=clean_text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"TTS Error: {e}")
    finally:
        time.sleep(1.2)
        is_speaking = False

# --- LOAD SECRETS ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: Missing Gemini API key in .env file!")
    sys.exit(1)
client = genai.Client(api_key=api_key)

# --- SETUP GOOGLE CALENDAR ---
# We request full access to read and create events
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

creds = None
# The token.json file stores the user's access and refresh tokens
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print("Failed to refresh token. Please delete token.json and re-authenticate.")
            sys.exit(1)
    else:
        if not os.path.exists('credentials.json'):
            print("\n" + "="*50)
            print("❌ CRITICAL ERROR: 'credentials.json' is missing!")
            print("You must download your OAuth credentials from Google Cloud Console.")
            print("Please follow the AI's instructions to obtain this file, and place it in the intelli-mirror folder.")
            print("="*50 + "\n")
            sys.exit(1)
            
        print("\nInitializing Google Calendar Authentication...")
        print("(It will open a browser to ask for permission)")
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        # Port 0 auto-selects an open port 
        creds = flow.run_local_server(port=0)
        
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

service = build('calendar', 'v3', credentials=creds)
print("✅ Google Calendar Connected Successfully!")

# --- WAKE WORD & ROUTING LOGIC ---
WAKE_WORD = "hey mirror"
listening_for_command = False

def process_calendar_intent(json_data):
    """Executes the Google Calendar API commands based on the LLM's parsed JSON."""
    intent = json_data.get("intent")
    
    if intent == "read":
        # Check the next 5 events
        now = datetime.datetime.utcnow().isoformat() + 'Z' 
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=5, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        if not events:
            speech_queue.put("You have absolutely nothing on your calendar coming up.")
            return
            
        resp = "Here are your upcoming events: "
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                dt = datetime.datetime.fromisoformat(start)
                time_str = dt.strftime("%A at %I:%M %p")
            else:
                time_str = "All day"
            resp += f"{event['summary']} {time_str}. "
            
        speech_queue.put(resp)
        
    elif intent == "add":
        summary = json_data.get("summary", "New Alert")
        date_str = json_data.get("date")
        time_str = json_data.get("time")
        
        if not date_str or not time_str:
            speech_queue.put("I couldn't figure out exactly when you wanted me to schedule that.")
            return
            
        start_datetime = f"{date_str}T{time_str}"
        # Set event for 30 minutes duration minimum
        dt = datetime.datetime.fromisoformat(start_datetime)
        end_dt = dt + datetime.timedelta(minutes=30)
        end_datetime = end_dt.isoformat()
        
        # Calculate local timezone
        tz = datetime.datetime.now().astimezone().tzinfo
        local_timezone = str(tz) if tz else 'UTC'
        if "UTC" in local_timezone or local_timezone == "None":
            local_timezone = "America/New_York" # fallback
            
        event = {
          'summary': summary,
          'start': {
            'dateTime': start_datetime,
            'timeZone': local_timezone,
          },
          'end': {
            'dateTime': end_datetime,
            'timeZone': local_timezone,
          },
          'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'popup', 'minutes': 10},
            ],
          },
        }

        try:
            service.events().insert(calendarId='primary', body=event).execute()
            speech_queue.put(f"I've added {summary} to your calendar.")
        except Exception as e:
             print(f"Failed to add to calendar: {e}")
             speech_queue.put("I couldn't sync that format with your Google Calendar.")
    else:
        speech_queue.put("I'm not sure how to do that with your calendar.")


def ask_gemini(text_query):
    """Sends the transcribed text to Gemma LLM configured strictly for Calendar extraction."""
    print(f"\n[Thinking...] Sending to AI: '{text_query}'")
    try:
        # We give the AI absolute awareness of time so it can calculate "tomorrow" or "in 2 hours"
        current_time = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        current_date_iso = datetime.datetime.now().strftime("%Y-%m-%d")
        
        instructions = f"""You are a strict JSON conversion engine navigating a Google Calendar.
The current real-world time is {current_time}. Today's date is {current_date_iso}.
If the user wants to ADD a calendar event, alert, or reminder, calculate the exact requested time and output ONLY raw JSON matching this schema:
{{"intent": "add", "summary": "<Brief title>", "date": "YYYY-MM-DD", "time": "HH:MM:00"}}
If the user wants to KNOW what is on their schedule or calendar, output ONLY raw JSON:
{{"intent": "read"}}
Return ONLY raw JSON. No markdown formatting. No conversational text."""

        combined_prompt = f"{instructions}\n\nUser command: {text_query}"
        
        response = client.models.generate_content(
            model='gemma-3-4b-it',
            contents=combined_prompt
        )
        
        # Clean the output in case the LLM wrapped it in markdown code blocks
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        print(f"\n>>> AI Extracted JSON: {raw_text}")
        
        # Parse the JSON string into a Python Dictionary
        data = json.loads(raw_text)
        
        # Send it to our API Controller
        process_calendar_intent(data)
        
    except json.JSONDecodeError:
        print("Failed to parse AI output as JSON.")
        speech_queue.put("I had a brain freeze trying to decipher that time format.")
    except Exception as e:
        print(f"Failed to communicate with AI: {e}")
        speech_queue.put("I'm having trouble connecting to my brain right now.")

# --- BACKGROUND LISTENER CORE ---
def audio_callback(recognizer, audio):
    global listening_for_command
    global is_speaking
    
    if is_speaking:
        return
        
    try:
        text = recognizer.recognize_google(audio).lower()
        
        if listening_for_command:
            print(f"--- Captured Command: '{text}' ---")
            ask_gemini(text)
            
            listening_for_command = False
            print(f"Ready! Say '{WAKE_WORD}'...")
            return

        if WAKE_WORD in text:
            print("\n====================")
            print("       HELLO!       ")
            
            command_in_same_breath = text.replace(WAKE_WORD, "").strip()
            
            if command_in_same_breath:
                print(f"--- Captured Command: '{command_in_same_breath}' ---")
                ask_gemini(command_in_same_breath)
                print(f"Ready! Say '{WAKE_WORD}'...")
            else:
                speech_queue.put("What can I get on the calendar for you?")
                print("Waiting for your command...")
                listening_for_command = True
            
    except sr.UnknownValueError:
        pass
    except sr.RequestError as e:
        print(f"Google Speech API Error: {e}")

def start_listening():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300 
    recognizer.dynamic_energy_threshold = True

    try:
        microphone = sr.Microphone()
    except OSError:
        print("Error: Could not access the microphone.")
        sys.exit(1)
        
    with microphone as source:
        print("Calibrating background noise...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print(f"\nReady! Say '{WAKE_WORD}'...")
    return recognizer.listen_in_background(microphone, audio_callback)

if __name__ == "__main__":
    print("-------------------------------------------------------")
    print("Initializing Smart Mirror Audio & Calendar Engine...")
    print("-------------------------------------------------------")
    
    stop_listening = start_listening()
    
    try:
        while True:
            try:
                text_to_speak = speech_queue.get_nowait()
                speak(text_to_speak)
            except queue.Empty:
                time.sleep(0.1) 
    except KeyboardInterrupt:
        print("\nShutting down listener...")
        stop_listening(wait_for_stop=False)
