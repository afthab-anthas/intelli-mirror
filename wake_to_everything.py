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
import spotipy
from spotipy.oauth2 import SpotifyOAuth
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

# --- SETUP AI ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: Missing Gemini API key in .env file!")
    sys.exit(1)
client = genai.Client(api_key=api_key)

# --- SETUP SPOTIFY ---
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    print("\nERROR: Missing Spotify credentials in .env file!")
    sys.exit(1)

print("\nInitializing Spotify Authentication...")
try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-modify-playback-state user-read-playback-state"
    ))
    sp.current_user() 
    print("✅ Spotify Connected Successfully!")
except Exception as e:
    print(f"❌ Failed to connect to Spotify: {e}")
    sys.exit(1)

# --- SETUP GOOGLE CALENDAR ---
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
creds = None
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
            print("\n❌ CRITICAL ERROR: 'credentials.json' is missing!")
            sys.exit(1)
        print("\nInitializing Google Calendar Authentication...")
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

service = build('calendar', 'v3', credentials=creds)
print("✅ Google Calendar Connected Successfully!")

# --- ORCHESTRATION LOGIC ---
WAKE_WORD = "hey mirror"
listening_for_command = False
last_interaction_time = time.time()
TIMEOUT_SECONDS = 15

# --- NEW: AUTO-CALIBRATION GLOBALS ---
last_calibration_time = time.time()
CALIBRATION_INTERVAL = 60  # Recalibrate every 60 seconds

def process_calendar_intent(json_data):
    """Executes the Google Calendar API commands based on the LLM's parsed JSON."""
    intent = json_data.get("intent")
    
    if intent == "read":
        now = datetime.datetime.utcnow().isoformat() + 'Z' 
        # Fetch 15 events just in case birthdays are clogging up the top slots
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=15, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        # --- THE FIX: Filter out birthdays and holidays ---
        real_events = []
        for event in events:
            summary = event.get('summary', '').lower()
            # Ignore birthdays, anniversaries, or public holidays
            if "birthday" not in summary and "holiday" not in summary:
                real_events.append(event)
                
        # Limit back down to the top 5 REAL events
        real_events = real_events[:5]
        
        if not real_events:
            speech_queue.put("You have absolutely nothing on your calendar coming up.")
            return
            
        resp = "Here are your upcoming events: "
        for event in real_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                dt = datetime.datetime.fromisoformat(start)
                time_str = dt.strftime("%A at %I:%M %p")
            else:
                time_str = "All day"
            resp += f"{event.get('summary', 'Event')} {time_str}. "
            
        speech_queue.put(resp)
        
    elif intent == "add":
        summary = json_data.get("summary", "New Alert")
        date_str = json_data.get("date")
        time_str = json_data.get("time")
        
        if not date_str or not time_str:
            speech_queue.put("I couldn't figure out exactly when you wanted me to schedule that.")
            return
            
        start_datetime = f"{date_str}T{time_str}"
        dt = datetime.datetime.fromisoformat(start_datetime)
        end_dt = dt + datetime.timedelta(minutes=30)
        end_datetime = end_dt.isoformat()
        
        tz = datetime.datetime.now().astimezone().tzinfo
        local_timezone = str(tz) if tz else 'UTC'
        if "UTC" in local_timezone or local_timezone == "None":
            local_timezone = "America/New_York" # fallback
            
        event = {
          'summary': summary,
          'start': {'dateTime': start_datetime, 'timeZone': local_timezone},
          'end': {'dateTime': end_datetime, 'timeZone': local_timezone},
          'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 10}]},
        }

        try:
            service.events().insert(calendarId='primary', body=event).execute()
            speech_queue.put(f"I've added {summary} to your calendar.")
        except Exception as e:
             print(f"Failed to add to calendar: {e}")
             speech_queue.put("I couldn't sync that format with your Google Calendar.")
             
    elif intent == "delete":
        summary = json_data.get("summary")
        if not summary:
            speech_queue.put("I didn't catch the name of the event to delete.")
            return
            
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        try:
            # Search for the event first
            events_result = service.events().list(calendarId='primary', q=summary, timeMin=now,
                                                  maxResults=5, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])
            
            if not events:
                speech_queue.put(f"I couldn't find an upcoming event matching {summary}.")
                return
                
            # Take the first match
            target_event = events[0]
            event_id = target_event['id']
            event_title = target_event.get('summary', 'Unknown Event')
            
            # Execute deletion
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            speech_queue.put(f"I have canceled {event_title} from your calendar.")
            
        except Exception as e:
            print(f"Failed to delete event: {e}")
            speech_queue.put("I ran into an error trying to cancel that event.")
            
    else:
        speech_queue.put("I'm not sure how to do that with your calendar.")

# --- TO-DO LIST LOGIC ---
TODO_FILE = "todo.json"

def get_todos():
    if not os.path.exists(TODO_FILE):
        return []
    try:
        with open(TODO_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_todos(todos):
    with open(TODO_FILE, "w") as f:
        json.dump(todos, f)

def process_todo_intent(json_data):
    """Executes local file database commands based on the LLM's parsed JSON."""
    intent = json_data.get("intent")
    
    if intent == "read":
        todos = get_todos()
        if not todos:
            speech_queue.put("You don't have anything on your to-do list right now.")
        else:
            tasks = ", ".join(todos)
            speech_queue.put(f"Here is your list: {tasks}.")
            
    elif intent == "add":
        task = json_data.get("task")
        if task:
            todos = get_todos()
            todos.append(task)
            save_todos(todos)
            speech_queue.put(f"I've added {task} to your list.")
        else:
            speech_queue.put("I didn't catch exactly what you wanted to add.")
            
    elif intent == "clear":
        save_todos([])
        speech_queue.put("Your list has been cleared completely.")
        
    elif intent == "delete":
        task = json_data.get("task")
        if not task:
            speech_queue.put("I didn't catch what you wanted to cross off.")
            return
            
        todos = get_todos()
        if not todos:
            speech_queue.put("Your list is already empty.")
            return
            
        task_lower = task.lower()
        matched_item = None
        # Attempt to find partial string overlap 
        for item in todos:
            if task_lower in item.lower() or item.lower() in task_lower:
                matched_item = item
                break
                
        if matched_item:
            todos.remove(matched_item)
            save_todos(todos)
            speech_queue.put(f"I've crossed off {matched_item} from your list.")
        else:
            speech_queue.put(f"I couldn't find {task} on your to-do list.")
            
    else:
        speech_queue.put("I'm not sure what you want me to do with your list.")

def ask_gemini(text_query):
    """Routes transcribed text to Spotify, Calendar AI, or General Conversational AI."""
    query_lower = text_query.lower()
    
    # ⚡ ROUTE 1: SPOTIFY INTERCEPT ⚡
    music_keywords = ["spotify", "music", "song", "track", "play", "pause", "skip", "next"]
    if any(keyword in query_lower for keyword in music_keywords):
        print("\n[🔌 Routing to Spotify...]")
        try:
            if "pause" in query_lower or "stop" in query_lower:
                sp.pause_playback()
                speech_queue.put("Paused Spotify.")
                return 
            elif "next" in query_lower or "skip" in query_lower:
                sp.next_track()
                speech_queue.put("Skipping to the next song.")
                return
            elif "play" in query_lower or "resume" in query_lower:
                if query_lower.startswith("play "):
                    song_name = query_lower.replace("play ", "", 1).strip()
                    if song_name and song_name not in ["music", "spotify", "the music", "the song", "some music"]:
                        search_query = song_name
                        if " by " in song_name:
                            parts = song_name.split(" by ", 1)
                            search_query = f"track:{parts[0]} artist:{parts[1]}"
                            
                        print(f"Searching Spotify for: {search_query}")
                        results = sp.search(q=search_query, limit=1, type='track')
                        if results['tracks']['items']:
                            track_uri = results['tracks']['items'][0]['uri']
                            track_name = results['tracks']['items'][0]['name']
                            artist_name = results['tracks']['items'][0]['artists'][0]['name']
                            sp.start_playback(uris=[track_uri])
                            speech_queue.put(f"Playing {track_name} by {artist_name}.")
                        else:
                            speech_queue.put("I couldn't find that song on Spotify.")
                        return
                sp.start_playback()
                speech_queue.put("Resuming your music.")
                return
            else:
                speech_queue.put("I heard a music command, but I didn't understand play, pause, or skip.")
                return
        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify API Error: {e}")
            speech_queue.put("I couldn't find an active Spotify device. Please open Spotify first.")
            return 
            
    # 📅 ROUTE 2: CALENDAR INTERCEPT 📅
    calendar_keywords = ["calendar"]
    if any(keyword in query_lower for keyword in calendar_keywords):
        print(f"\n[📅 Routing to Calendar AI...]")
        try:
            current_time = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
            current_date_iso = datetime.datetime.now().strftime("%Y-%m-%d")
            
            instructions = f"""You are a strict JSON conversion engine navigating a Google Calendar.
The current real-world time is {current_time}. Today's date is {current_date_iso}.
If the user wants to ADD a calendar event, alert, or reminder, calculate the exact requested time and output ONLY raw JSON matching this schema:
{{"intent": "add", "summary": "<Brief title>", "date": "YYYY-MM-DD", "time": "HH:MM:00"}}
If the user wants to DELETE, CANCEL, or REMOVE a calendar event, output ONLY raw JSON:
{{"intent": "delete", "summary": "<Brief title>"}}
If the user wants to KNOW what is on their schedule or calendar, output ONLY raw JSON:
{{"intent": "read"}}
Return ONLY raw JSON. No markdown formatting. No conversational text."""

            combined_prompt = f"{instructions}\n\nUser command: {text_query}"
            
            response = client.models.generate_content(model='gemma-3-4b-it', contents=combined_prompt)
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            print(f"\n>>> AI Extracted JSON: {raw_text}")
            
            data = json.loads(raw_text)
            process_calendar_intent(data)
            return
            
        except json.JSONDecodeError:
            print("Failed to parse AI output as JSON.")
            speech_queue.put("I had a brain freeze trying to decipher that time format.")
            return
        except Exception as e:
            print(f"Failed to communicate with AI: {e}")
            speech_queue.put("I'm having trouble connecting to my calendar brain.")
            return

    # 📝 ROUTE 4: TO-DO LIST INTERCEPT 📝
    todo_keywords = ["to-do", "todo", "task", "grocery", "list", "buy", "remind", "reminder", "schedule", "event", "appointment", "finish", "complete", "remove", "off", "delete", "cancel"]
    if any(keyword in query_lower for keyword in todo_keywords):
        print(f"\n[📝 Routing to To-Do AI...]")
        try:
            instructions = f"""You are a strict JSON conversion engine managing a simple to-do list.
If the user wants to ADD a task or item, output ONLY raw JSON:
{{"intent": "add", "task": "<Task name>"}}
If the user wants to DELETE, REMOVE, or COMPLETE a task, output ONLY raw JSON:
{{"intent": "delete", "task": "<Task name>"}}
If the user wants to KNOW what is on their list, output ONLY raw JSON:
{{"intent": "read"}}
If the user wants to CLEAR or EMPTY their entire list, output ONLY raw JSON:
{{"intent": "clear"}}
Return ONLY raw JSON. No markdown formatting."""

            combined_prompt = f"{instructions}\n\nUser command: {text_query}"
            
            response = client.models.generate_content(model='gemma-3-4b-it', contents=combined_prompt)
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            print(f"\n>>> AI Extracted To-Do JSON: {raw_text}")
            
            data = json.loads(raw_text)
            process_todo_intent(data)
            return
            
        except json.JSONDecodeError:
            print("Failed to parse AI output as JSON.")
            speech_queue.put("I had a brain freeze managing your tasks.")
            return
        except Exception as e:
            print(f"Failed to communicate with AI: {e}")
            speech_queue.put("I'm having trouble connecting to my task database.")
            return

    # 🧠 ROUTE 3: REGULAR CONVERSATIONAL AI 🧠
    print(f"\n[🧠 Routing to General AI...]")
    try:
        instructions = "You are an intelligent, concise smart mirror assistant. Keep responses brief and conversational (1-2 sentences). Do not use lists or bullet points. Act like a helpful AI."
        combined_prompt = f"{instructions}\n\nThe user says: {text_query}"
        
        response = client.models.generate_content(
            model='gemma-3-4b-it',
            contents=combined_prompt
        )
        
        print("\n>>> AI SAYS:")
        response_text = response.text.strip()
        print(response_text)
        print("====================\n")
        
        speech_queue.put(response_text)
        
    except Exception as e:
        print(f"Failed to communicate with AI: {e}")
        speech_queue.put("I'm sorry, I am having trouble connecting to my brain right now.")

# --- BACKGROUND LISTENER CORE ---
def audio_callback(recognizer, audio):
    global listening_for_command
    global is_speaking
    
    if is_speaking:
        return
        
    try:
        text = recognizer.recognize_google(audio).lower()
        
        if listening_for_command:
            # Safely slice out the bots own voice if the microphone accidentally merged it with the user's speech!
            text = text.replace("i am listening", "").strip()
            
            # If the chunk was ONLY an echo with nothing from the user, drop it cleanly.
            if not text:
                return
                
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
                speech_queue.put("I am listening.")
                print("Waiting for your command...")
                listening_for_command = True
            
    except sr.UnknownValueError:
        pass
    except sr.RequestError as e:
        print(f"Google Speech API Error: {e}")

def start_listening(is_recalibrating=False):
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False 
    recognizer.pause_threshold = 0.5 
    recognizer.non_speaking_duration = 0.4

    try:
        microphone = sr.Microphone()
    except OSError:
        print("Error: Could not access the microphone.")
        sys.exit(1)
        
    with microphone as source:
        if is_recalibrating:
            # A fast 1.5-second check so the mirror isn't deaf for too long
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
            room_baseline = recognizer.energy_threshold
            recognizer.energy_threshold = room_baseline + 300
            print(f"[Auto-Tuning] Quick recalibration. New threshold: {recognizer.energy_threshold:.0f}")
        else:
            # The deep 3-second check when you first turn the mirror on
            print("\n[Boot-Up] Calibrating to your room's background noise...")
            recognizer.adjust_for_ambient_noise(source, duration=3)
            room_baseline = recognizer.energy_threshold
            recognizer.energy_threshold = room_baseline + 300 
            print(f"[Boot-Up] Threshold locked at: {recognizer.energy_threshold:.0f}")
            print(f"\nReady! Say '{WAKE_WORD}'...")
    
    return recognizer.listen_in_background(microphone, audio_callback, phrase_time_limit=8)

if __name__ == "__main__":
    print("-------------------------------------------------------")
    print("Initializing Smart Mirror Audio, Spotify, & Calendar...")
    print("-------------------------------------------------------")
    
    stop_listening = start_listening(is_recalibrating=False)
    
    try:
        while True:
            # 1. Handle TTS Engine (Speaking)
            try:
                text_to_speak = speech_queue.get_nowait()
                speak(text_to_speak)
                last_interaction_time = time.time()
                # Reset calibration timer after talking so it doesn't calibrate immediately
                last_calibration_time = time.time() 
            except queue.Empty:
                pass 
                
            # 2. Watchdog Timer (Auto-Sleep)
            if listening_for_command and not is_speaking:
                if (time.time() - last_interaction_time) > TIMEOUT_SECONDS:
                    print(f"\n[Timeout] No voice detected for {TIMEOUT_SECONDS} seconds.")
                    listening_for_command = False
                    speech_queue.put("Going to sleep.")
                    print(f"Ready! Say '{WAKE_WORD}'...")
            
            # 3. CONTINUOUS CALIBRATION LOOP
            # Only recalibrate if the mirror is idle (not talking, not waiting for a command)
            if not listening_for_command and not is_speaking:
                if (time.time() - last_calibration_time) > CALIBRATION_INTERVAL:
                    # Shut down the current microphone thread
                    stop_listening(wait_for_stop=False)
                    
                    # Fire up a new one with a fresh room reading
                    stop_listening = start_listening(is_recalibrating=True)
                    
                    # Reset the clock for another 60 seconds
                    last_calibration_time = time.time()
                    
            time.sleep(0.1) 
            
    except KeyboardInterrupt:
        print("\nShutting down listener...")
        stop_listening(wait_for_stop=False)
