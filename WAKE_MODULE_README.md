# Wake Module Setup & Summary (Area 2: Audio & Voice)

This document summarizes the development and setup of the `wake_module.py` script, which serves as the foundational listening engine for the Smart Mirror project.

## What was built
We built a continuous, non-blocking audio listener. Instead of relying on a while-loop that freezes the rest of the application, we utilized the `SpeechRecognition` library's `listen_in_background()` method. This spawns a dedicated background Python thread that constantly monitors the microphone, freeing up the main thread to handle WebSockets, the UI, and other logic simultaneously.

## The Approach & Technologies
*   **Rapid Prototyping:** The current implementation uses Google's free Voice API tier. It requires an active internet connection but works flawlessly out-of-the-box, allowing us to immediately begin testing the prompt engineering and logic routing without wrestling with local model installations.
*   **Future-Proofing (The free alternative to Picovoice):** Since Picovoice Porcupine is not a truly free, unlimited tool, we architected this script so it can be transitioned to an offline tool later. When ready to deploy to the Raspberry Pi, you can install the **Vosk** library. It relies on a tiny (40MB) downloadable model and operates completely offline and for free. The transition will only require changing one line of code: `recognizer.recognize_google(audio)` to `recognizer.recognize_vosk(audio)`.

## How to run it (MacOS)
Since MacOS requires a C-library binding for microphone access, you must install `portaudio` before installing the Python packages.

1. **Install PortAudio via Homebrew:**
   ```bash
   brew install portaudio
   ```
2. **Install Python dependencies:**
   ```bash
   pip install pyaudio SpeechRecognition
   ```
3. **Run the script:**
   ```bash
   python wake_module.py
   ```

## Next Steps
Now that the mirror can reliably hear the "Hey Mirror" wake word, the next step in Area 2 is to take the audio that follows the wake word, send it to a smart router (like an OpenAI LLM), and trigger specific Python functions (like fetching the Weather or switching Spotify songs).
