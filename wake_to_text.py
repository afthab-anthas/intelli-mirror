import speech_recognition as sr
import time
import sys

# The Wake Word we are listening for
WAKE_WORD = "hey mirror"

# A state tracker. True if we heard "Hey Mirror" and are waiting for the next sentence.
listening_for_command = False

def audio_callback(recognizer, audio):
    global listening_for_command
    
    try:
        # Convert the audio chunk to text
        text = recognizer.recognize_google(audio).lower()
        
        # SCENARIO 1: We are expecting a command because they just said "Hey Mirror"
        if listening_for_command:
            print(f">>> You said: '{text}'")
            print("====================\n")
            
            # Reset state back to passive listening
            listening_for_command = False
            print(f"Ready! Say '{WAKE_WORD}' to trigger again...")
            return

        # SCENARIO 2: We are passively listening for the wake word
        if WAKE_WORD in text:
            print("\n====================")
            print("       HELLO!       ")
            
            # People speak differently. Sometimes they pause: "Hey Mirror... [pause] ... what's the weather?"
            # Sometimes they say it all at once: "Hey Mirror what's the weather?"
            
            # Let's remove the wake word and see if anything is left over
            command_in_same_breath = text.replace(WAKE_WORD, "").strip()
            
            if command_in_same_breath:
                # They said it all in one breath!
                print(f">>> You said: '{command_in_same_breath}'")
                print("====================\n")
            else:
                # They paused. Let's change our state so we treat the NEXT audio chunk as the command.
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
        print("Calibrating background noise (stay quiet for 2 seconds)...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print(f"\nReady! Say '{WAKE_WORD}'...")
    
    # We continue using the background thread because it is superior to a blocking while-loop
    stop_listening_func = recognizer.listen_in_background(microphone, audio_callback)
    return stop_listening_func

if __name__ == "__main__":
    print("Initializing Smart Mirror Audio Engine: Wake to Text...")
    stop_listening = start_listening()
    
    try:
        while True:
            time.sleep(0.1) 
    except KeyboardInterrupt:
        print("\nShutting down listener...")
        stop_listening(wait_for_stop=False)
