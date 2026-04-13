import speech_recognition as sr

r = sr.Recognizer()
with sr.Microphone() as source:
    print("Listening to background noise for 2 seconds...")
    r.adjust_for_ambient_noise(source, duration=2)
    print(f"Your room's baseline energy threshold is: {r.energy_threshold}")
    print("\nNow, say 'Hey Mirror' at a normal volume...")
    
    try:
        audio = r.listen(source, timeout=5)
        print("I heard you! Audio captured successfully.")
    except sr.WaitTimeoutError:
        print("I didn't hear anything. Your mic volume is too low.")