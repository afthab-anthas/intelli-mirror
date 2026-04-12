import pyttsx3
engine = pyttsx3.init()
print("Attempting to speak...")
engine.say("Testing the audio engine. Can you hear me, Afthab?")
engine.runAndWait()
print("Finished.")