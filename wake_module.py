import speech_recognition as sr
import time
import sys

# The Wake Word we are listening for
WAKE_WORD = "hey mirror"

def audio_callback(recognizer, audio):
    """
    This function is called automatically in a background thread whenever the 
    microphone detects someone speaking.
    """
    try:
        # For prototyping, we use google's free tier. 
        # Later, we can swap this for 'recognize_vosk()' for completely free, offline processing.
        text = recognizer.recognize_google(audio).lower()
        
        # Uncomment this to see everything it hears for debugging
        # print(f"[Heard]: {text}") 
        
        if WAKE_WORD in text:
            print("\n====================")
            print("       HELLO!       ")
            print("====================\n")
            
            # Here is where you will eventually call your LLM or Spotify functions!
            # process_command() 
            
    except sr.UnknownValueError:
        # It heard sound, but couldn't understand words (e.g., a cough or chair squeak)
        pass
    except sr.RequestError as e:
        print(f"API Error: {e}")

def start_listening():
    recognizer = sr.Recognizer()
    
    # Optional: tweaking these values makes it more/less sensitive
    recognizer.energy_threshold = 300 
    recognizer.dynamic_energy_threshold = True

    try:
        microphone = sr.Microphone()
    except OSError:
        print("Error: Could not access the microphone. Are you sure it's plugged in and permitted?")
        sys.exit(1)
        
    with microphone as source:
        print("Calibrating background noise (stay quiet for 2 seconds)...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print(f"\nReady! Say '{WAKE_WORD}'...")
    
    # listen_in_background spawns a separate thread.
    # This means your main program won't freeze while waiting for you to speak!
    stop_listening_func = recognizer.listen_in_background(microphone, audio_callback)
    
    return stop_listening_func

if __name__ == "__main__":
    print("Initializing Smart Mirror Audio Engine...")
    stop_listening = start_listening()
    
    try:
        # the main loop continues doing its own thing, completely unblocked.
        while True:
            time.sleep(0.1) 
    except KeyboardInterrupt:
        print("\nShutting down listener...")
        stop_listening(wait_for_stop=False)
