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
import spotipy
from spotipy.oauth2 import SpotifyOAuth

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
    print("Please add SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET.")
    sys.exit(1)

print("\nInitializing Spotify Authentication...")
print("(If this is your first time, it may open a browser to ask for permission)")
try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-modify-playback-state user-read-playback-state"
    ))
    # Quick test to see if it connects (throws error if not)
    sp.current_user() 
    print("✅ Spotify Connected Successfully!")
except Exception as e:
    print(f"❌ Failed to connect to Spotify: {e}")
    sys.exit(1)


# --- WAKE WORD & ROUTING LOGIC ---
WAKE_WORD = "hey mirror"
listening_for_command = False

def ask_gemini(text_query):
    """Sends transcribed text to Gemma LLM OR intercepts it for Spotify!"""
    query_lower = text_query.lower()
    
    # ⚡ === FAST INTERCEPT: SPOTIFY COMMANDS === ⚡
    music_keywords = ["spotify", "music", "song", "track", "play", "pause", "skip", "next"]
    if any(keyword in query_lower for keyword in music_keywords):
        print("\n[🔌 Spotify Intercept] Attempting to control playback...")
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
                # Check if they asked for a specific song
                if query_lower.startswith("play "):
                    song_name = query_lower.replace("play ", "", 1).strip()
                    # Ignore generic play commands
                    if song_name and song_name not in ["music", "spotify", "the music", "the song", "some music"]:
                        
                        # Spotify API gets confused by the word "by" in basic searches. 
                        # We split it into specific track and artist fields for 100% accuracy!
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
                            # Tell Spotify to explicitly play this specific track
                            sp.start_playback(uris=[track_uri])
                            speech_queue.put(f"Playing {track_name} by {artist_name}.")
                        else:
                            speech_queue.put("I couldn't find that song on Spotify.")
                        return
                        
                # If no specific song was requested, just resume playback
                sp.start_playback()
                speech_queue.put("Resuming your music.")
                return
            else:
                speech_queue.put("I heard a music command, but I didn't understand play, pause, or skip.")
                return
        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify API Error: {e}")
            speech_queue.put("I couldn't find an active Spotify device. Please open Spotify on your phone or computer first.")
            return 
            
    # 🧠 === REGULAR AI PROCESSING === 🧠
    print(f"\n[Thinking...] Sending to AI: '{text_query}'")
    try:
        instructions = "You are an intelligent, concise smart mirror assistant. Keep responses brief and conversational (1-2 sentences). Do not use lists or bullet points."
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
    print("Initializing Smart Mirror Audio, Spotify, & AI Brain...")
    print("-------------------------------------------------------")
    
    stop_listening = start_listening()
    
    try:
        # The main loop checks the queue and executes audio commands safely on the MAIN thread!
        while True:
            try:
                text_to_speak = speech_queue.get_nowait()
                speak(text_to_speak)
            except queue.Empty:
                time.sleep(0.1) 
    except KeyboardInterrupt:
        print("\nShutting down listener...")
        stop_listening(wait_for_stop=False)
