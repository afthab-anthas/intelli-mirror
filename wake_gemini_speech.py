import os
import sys
import time
import speech_recognition as sr
from google import genai
from google.genai import types
from dotenv import load_dotenv
import queue
from gtts import gTTS
import pygame
import io

# We use a Queue to safely pass text from the background thread to the main thread!
speech_queue = queue.Queue()

is_speaking = False

def speak(text):
    global is_speaking
    """Speaks using Google's high-quality human voices via an in-memory stream."""
    is_speaking = True
    try:
        clean_text = text.replace('*', '').replace('#', '')
        print(f"[Audio] Speaking: {clean_text}")
        
        # 1. Ask Google for the audio file
        tts = gTTS(text=clean_text, lang='en')
        
        # 2. Save it to RAM instead of the hard drive (Saves SD card read/writes!)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        # 3. Play the audio stream
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        
        # Block this thread while the audio is actively playing
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
    except Exception as e:
        print(f"TTS Error: {e}")
    finally:
        # Buffer to prevent the mirror from hearing its own echo
        time.sleep(1.2)
        is_speaking = False

# Load your secure API key from a .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key or api_key == "your_actual_api_key_here":
    print("ERROR: Please put your real Gemini API key in the .env file!")
    sys.exit(1)

# Initialize the GenAI Client
client = genai.Client(api_key=api_key)

WAKE_WORD = "hey mirror"
listening_for_command = False

def ask_gemini(text_query):
    """Sends the transcribed text to Gemma LLM, prints it, and speaks it."""
    print(f"\n[Thinking...] Sending to AI: '{text_query}'")
    try:
        # Instructions for the mirror
        instructions = "You are an intelligent, concise smart mirror assistant. Keep responses brief and conversational (1-2 sentences). Do not use lists or bullet points."
        combined_prompt = f"{instructions}\n\nThe user says: {text_query}"
        
        # Using Gemma 3 4B to bypass the 20/day limit for testing!
        response = client.models.generate_content(
            model='gemma-3-4b-it',
            contents=combined_prompt
        )
        
        print("\n>>> AI SAYS:")
        response_text = response.text.strip()
        print(response_text)
        print("====================\n")
        
        # Send speech command to the main thread
        speech_queue.put(response_text)
        
    except Exception as e:
        print(f"Failed to communicate with AI: {e}")
        speech_queue.put("I'm sorry, I am having trouble connecting to my brain right now.")

def audio_callback(recognizer, audio):
    global listening_for_command
    global is_speaking
    
    # Ignore any audio phrases that were captured while the mirror itself was talking!
    if is_speaking:
        return
        
    try:
        text = recognizer.recognize_google(audio).lower()
        
        # Scenario 1: Processing a command after a pause
        if listening_for_command:
            print(f"--- Captured Command: '{text}' ---")
            ask_gemini(text)
            
            listening_for_command = False
            print(f"Ready! Say '{WAKE_WORD}'...")
            return

        # Scenario 2: Listening for the wake word passively
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
        print(f"API Error: {e}")

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
    print("Initializing Smart Mirror Audio, Speech & AI Brain...")
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
