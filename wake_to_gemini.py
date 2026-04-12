import os
import sys
import time
import speech_recognition as sr
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Load your secure API key from a .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key or api_key == "your_actual_api_key_here":
    print("ERROR: Please put your real Gemini API key in the .env file!")
    sys.exit(1)

# 2. Initialize the new GenAI Client
client = genai.Client(api_key=api_key)

WAKE_WORD = "hey mirror"
listening_for_command = False

def ask_gemini(text_query):
    """Sends the transcribed text to Gemini LLM and prints the response."""
    print(f"\n[Thinking...] Sending to Gemini: '{text_query}'")
    try:
        # We give the LLM a system instruction so it acts like a mirror
        instructions = "You are an intelligent, concise smart mirror assistant. Keep responses brief and conversational (1-2 sentences)."
        
        # Make the API call using the new SDK!
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=text_query,
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        print("\n>>> GEMINI SAYS:")
        # We strip the text to remove trailing whitespace
        print(response.text.strip())
        print("====================\n")
        
    except Exception as e:
        print(f"Failed to communicate with Gemini: {e}")

def audio_callback(recognizer, audio):
    global listening_for_command
    
    try:
        text = recognizer.recognize_google(audio).lower()
        
        # Scenario 1: Processing a command after a pause
        if listening_for_command:
            print(f"--- Captured Command: '{text}' ---")
            # PASS THE TEXT TO GEMINI!
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
                # PASS THE TEXT TO GEMINI!
                ask_gemini(command_in_same_breath)
                print(f"Ready! Say '{WAKE_WORD}'...")
            else:
                print("Listening for your command...")
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
    print("Initializing Smart Mirror Audio & Gemini Brain...")
    stop_listening = start_listening()
    
    try:
        while True:
            time.sleep(0.1) 
    except KeyboardInterrupt:
        print("\nShutting down listener...")
        stop_listening(wait_for_stop=False)
