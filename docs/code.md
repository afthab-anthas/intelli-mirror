# Intelli-Mirror Code Reference

**Last Updated:** July 2026

## Table of Contents

1. [Core Engine Functions](#core-engine-functions)
2. [Vision & Detection](#vision--detection)
3. [Audio & Speech](#audio--speech)
4. [AI & Intent Processing](#ai--intent-processing)
5. [Data Persistence](#data-persistence)
6. [UI & Communication](#ui--communication)
7. [ML Training](#ml-training)
8. [Setup & Configuration](#setup--configuration)

---

## Core Engine Functions

### main() - Entry Point

**File:** `intelli.py:762` / `intelli-safeai.py:989`

```python
if __name__ == "__main__":
    print("starting intelli-mirror core...")
    
    website_path = os.path.abspath("website/index.html")
    print(f"launching browser at {website_path}")
    webbrowser.open(f"file://{website_path}")
    
    send_to_ui({"ai_state": "idle", "ai_text": "Ready! Say 'Hey Mirror'", "todos": get_todos()})
    
    stop_listening = start_listening(False)
    
    try:
        while True:
            # Main event loop
    except KeyboardInterrupt:
        print("stopping mirror...")
        stop_listening(wait_for_stop=False)
```

**Key Responsibilities:**
1. Launch browser window with local website UI
2. Send initial UI state via WebSocket
3. Start speech recognition listener
4. Enter main loop for speech queue processing
5. Handle graceful shutdown

**Global State Initialized:**
- `latest_frame` - None initially
- `latest_temp` - "--°C"
- `recognized_user` - None
- `login_stats` - Loaded from JSON or empty dict

---

### Main Event Loop

**File:** `intelli.py:773-799` / `intelli-safeai.py:1000-1046`

**Purpose:** Process speech queue, manage timeouts, recalibrate microphone

**Operations:**
```python
while True:
    # 1. Get next speech item from queue (non-blocking)
    try:
        speak(speech_queue.get_nowait())
        last_interaction_time = time.time()
        last_calibration_time = time.time()
    except queue.Empty:
        pass
    
    # 2. Timeout listening mode after 15 seconds (intelli.py:784)
    if listening_for_command and not is_speaking and (time.time() - last_interaction_time) > TIMEOUT_SECONDS:
        listening_for_command = False
        send_to_ui({"ai_state": "idle", "ai_text": "Say 'Hey Mirror'"})
        speech_queue.put("Going to sleep.")
    
    # 3. (SafeAI only) Wipe conversation memory after 60 seconds
    if not listening_for_command and not is_speaking and (time.time() - last_interaction_time) > 60:
        if mirror_chat.get_history():
            mirror_chat = client.chats.create(model='gemini-3.1-flash-lite')
            print("1 minute passed: Conversation memory wiped.")
    
    # 4. Recalibrate microphone every 60 seconds
    if not listening_for_command and not is_speaking and (time.time() - last_calibration_time) > CALIBRATION_INTERVAL:
        stop_listening(wait_for_stop=False)
        stop_listening = start_listening(True)
        last_calibration_time = time.time()
    
    time.sleep(0.1)
```

**Important Flags:**
- `listening_for_command` - Waiting for user command after wake word
- `is_speaking` - Currently playing TTS audio (blocks new commands)
- `recognized_user` - Non-None if face recognized

---

## Vision & Detection

### unified_vision_thread()

**File:** `intelli.py:218-369` / `intelli-safeai.py:359-569`

**Purpose:** Continuous webcam processing with hand tracking and face recognition

**Architecture:**
```
Input: Webcam frames (30 FPS)
  ↓
├─ 1. Hand Tracking (every frame)
│  ├─ Detect 21 landmarks per hand
│  ├─ Calculate pinch distance (thumb ↔ index)
│  ├─ Map hand center to screen coordinates
│  ├─ Apply exponential smoothing
│  └─ Control mouse position and clicks
│
├─ 2. Face Recognition (every 10 frames)
│  ├─ Detect faces with YuNet
│  ├─ Align and crop with SFace
│  ├─ Extract 128D embedding
│  ├─ Classify with SVM
│  ├─ Update recognized_user if confidence > 0.60
│  └─ Handle intruder detection (SafeAI)
│
└─ 3. State Management
   ├─ Timeout user after 30-60 seconds without face
   ├─ Publish login stats to MQTT
   └─ Update latest_frame for vision analysis
```

#### Hand Tracking Algorithm

```python
def hand_center(lm):
    """Calculate center of 21 hand landmarks"""
    return sum(p.x for p in lm) / len(lm), sum(p.y for p in lm) / len(lm)

def dist(p1, p2):
    """Euclidean distance between two landmarks"""
    return math.hypot(p2.x - p1.x, p2.y - p1.y)

# In unified_vision_thread:
if results.hand_landmarks:
    lm = results.hand_landmarks[0]
    px, py = hand_center(lm)
    fx, fy = px * w, py * h
    
    # Map to screen with crop margin
    x_mapped = int((fx - FRAME_R) / (w - 2 * FRAME_R) * SCREEN_W)
    y_mapped = int((fy - FRAME_R) / (h - 2 * FRAME_R) * SCREEN_H)
    x_mapped = max(0, min(SCREEN_W - 1, x_mapped))
    y_mapped = max(0, min(SCREEN_H - 1, y_mapped))
    
    # Exponential smoothing
    active_smoothing = SMOOTHING_DRAG if mouse_held else SMOOTHING_FREE
    curr_x = prev_x + (x_mapped - prev_x) / active_smoothing
    curr_y = prev_y + (y_mapped - prev_y) / active_smoothing
    
    pyautogui.moveTo(int(curr_x), int(curr_y))
    prev_x, prev_y = curr_x, curr_y
    
    # Pinch detection
    thumb_tip = lm[4]
    index_tip = lm[8]
    pinch_distance = dist(thumb_tip, index_tip)
    
    if not mouse_held and pinch_distance < PINCH_GRAB_DIST:
        pyautogui.mouseDown(button="left")
        mouse_held = True
    elif mouse_held and pinch_distance > PINCH_DROP_DIST:
        pyautogui.mouseUp(button="left")
        mouse_held = False
```

**Configuration Constants:**
- `FRAME_R = 100` - Crop margin (pixels) to avoid edge activation
- `SMOOTHING_FREE = 7` - Exponential averaging when not dragging
- `SMOOTHING_DRAG = 14` - Exponential averaging when dragging
- `PINCH_GRAB_DIST = 0.045` - Threshold to activate pinch
- `PINCH_DROP_DIST = 0.085` - Threshold to release pinch

#### Face Recognition Algorithm

```python
if frame_idx % 10 == 0 and not mouse_held and face_detector and model and face_recognizer:
    try:
        # 1. Detect faces
        _, faces = face_detector.detect(image)
        
        if faces is not None:
            # 2. Align and crop best face
            face_aligned = face_recognizer.alignCrop(image, faces[0])
            
            # 3. Extract embedding (128D)
            current_embedding = face_recognizer.feature(face_aligned).flatten().reshape(1, -1)
            
            # 4. Classify with SVM
            probs = model.predict_proba(current_embedding)[0]
            best_idx = np.argmax(probs)
            
            # 5. Threshold check
            if probs[best_idx] > 0.60:
                new_user = profiles.get("id_to_name", {}).get(int(model.classes_[best_idx]), "Unknown")
            else:
                new_user = "Unknown"
            
            # 6. Handle unknown faces (SafeAI only)
            if new_user == "Unknown":
                unknown_consecutive_frames += 1
                if unknown_consecutive_frames >= 3:
                    # Send to Firebase for admin approval
                    # Publish intruder alert to MQTT if security_enforced
            else:
                unknown_consecutive_frames = 0
                if recognized_user != new_user:
                    recognized_user = new_user
                    speech_queue.put(f"Hi {recognized_user}")
                    log_user_login(recognized_user)
                last_seen_time = time.time()
    except:
        pass

# Auto-logout
if recognized_user is not None and (time.time() - last_seen_time > FACE_TIMEOUT):
    recognized_user = None
    speech_queue.put("Session logged out.")
```

**Models:**
- `YuNet` (yunet.onnx) - Face detection, returns bounding box
- `SFace` (sface.onnx) - Face alignment and feature extraction (128D embeddings)
- `SVM` (hybrid_ai_model.pkl) - Classification on embeddings

**Confidence Threshold:** `0.60` (60%)

**Timeout:** `FACE_TIMEOUT = 30` (SafeAI: 60) seconds

---

### enroll_user() - User Enrollment

**File:** `intelli-safeai.py:277-350`

**Purpose:** Capture 150 face samples and prepare for retraining

**Workflow:**
```python
def enroll_user(name):
    enrollment_active = True
    speech_queue.put(f"Access granted. Initializing facial scan for {name}. Please look at the camera.")
    time.sleep(4)  # Wait for speech
    
    # 1. Initialize Pi 5 hardware camera (rpicam-vid command)
    w, h = 640, 480
    cmd = ["rpicam-vid", "-t", "0", "--width", str(w), "--height", str(h), 
           "--framerate", "30", "--codec", "yuv420", "--inline", "--flush", "-o", "-"]
    camera_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    # 2. Load existing profiles
    if PROFILES_PATH.exists():
        with open(PROFILES_PATH, "rb") as f:
            pro = pickle.load(f)
    else:
        pro = {"name_to_id": {}, "id_to_name": {}}
    
    # 3. Assign ID to new user
    if name not in pro["name_to_id"]:
        new_id = len(pro["name_to_id"])
        pro["name_to_id"][name] = new_id
        pro["id_to_name"][new_id] = name
    pid = pro["name_to_id"][name]
    
    # 4. Collect 150 samples
    collected = 0
    faces_list, labels_list = [], []
    
    while collected < 150:
        raw_data = camera_process.stdout.read(frame_size)
        yuv_array = np.frombuffer(raw_data, dtype=np.uint8).reshape((int(h * 1.5), w))
        frame = cv2.cvtColor(yuv_array, cv2.COLOR_YUV2BGR_I420)
        frame = cv2.flip(frame, 1)
        
        _, faces = face_detector.detect(frame)
        if faces is not None:
            aligned = face_recognizer.alignCrop(frame, faces[0])
            gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
            faces_list.append(cv2.resize(gray, (100, 100)))
            labels_list.append(pid)
            collected += 1
            cv2.putText(frame, f"Scanning: {collected}/150", (50,50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        
        cv2.imshow("Registration Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # 5. Save face data and profiles
    with open(FACE_DATA_PATH, "wb") as f:
        pickle.dump((faces_list, labels_list), f)
    with open(PROFILES_PATH, "wb") as f:
        pickle.dump(pro, f)
    
    # 6. Retrain model
    speech_queue.put("Scan complete. Updating neural network.")
    subprocess.run([sys.executable, "retrain.py"])
    
    enrollment_active = False
    return True
```

**Important:**
- Captures 150 samples for robust SVM training
- Uses Pi 5 hardware camera via `rpicam-vid`
- Stores as 100x100 grayscale for compatibility
- Triggers automatic model retraining
- Updates `reload_ai_model` flag for live reloading

---

## Audio & Speech

### start_listening()

**File:** `intelli.py:743-760` / `intelli-safeai.py:970-987`

**Purpose:** Initialize microphone and start background speech recognition

```python
def start_listening(is_recalibrating=False):
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False
    recognizer.pause_threshold = 0.5
    recognizer.non_speaking_duration = 0.4
    
    try:
        microphone = sr.Microphone()
    except OSError:
        sys.exit("could not access microphone")
    
    with microphone as source:
        # Adjust for ambient noise
        duration = 1.5 if is_recalibrating else 3
        recognizer.adjust_for_ambient_noise(source, duration=duration)
        recognizer.energy_threshold += 300
        if not is_recalibrating:
            print(f"microphone ready. say '{WAKE_WORD}'")
    
    # Start background listening
    return recognizer.listen_in_background(microphone, audio_callback, phrase_time_limit=8)
```

**Configuration:**
- `dynamic_energy_threshold = False` - Use fixed energy level
- `pause_threshold = 0.5` - Min silence to end sentence (500ms)
- `non_speaking_duration = 0.4` - Wait before recognizing (400ms)
- `energy_threshold += 300` - Boost to reduce false positives
- `phrase_time_limit = 8` - Max 8 seconds per utterance

**Recalibration:** Every 60 seconds (CALIBRATION_INTERVAL)

---

### audio_callback()

**File:** `intelli.py:714-741` / `intelli-safeai.py:941-968`

**Purpose:** Process speech recognition results

```python
def audio_callback(recognizer, audio):
    global listening_for_command, is_speaking
    
    if is_speaking:
        return  # Don't process while speaking
    
    try:
        text = recognizer.recognize_google(audio).lower()
        
        if listening_for_command:
            # User is responding to listening prompt
            text = text.replace("i am listening", "").strip()
            if not text:
                return
            
            if recognized_user is None:
                speech_queue.put("User is not recognised.")
                listening_for_command = False
            else:
                ask_gemini(text)
            
            listening_for_command = False
        
        elif WAKE_WORD in text:
            # Wake word detected
            if recognized_user is None:
                return speech_queue.put("User is not recognised.")
            
            send_to_ui({"ai_state": "listening", "ai_text": "I am listening..."})
            cmd = text.replace(WAKE_WORD, "").strip()
            
            if cmd:
                ask_gemini(cmd)
            else:
                speech_queue.put("I am listening.")
                listening_for_command = True
    except:
        pass  # Recognition failed, ignore
```

**Key Logic:**
1. Ignore if already speaking (is_speaking flag)
2. Recognize text via Google API
3. If in listening_for_command mode, process as command
4. Otherwise, check for wake word "hey mirror"
5. Require recognized_user before processing commands
6. Queue response to speech_queue

---

### speak()

**File:** `intelli.py:184-209` / `intelli-safeai.py:218-243`

**Purpose:** Convert text to speech and play audio

```python
def speak(text):
    global is_speaking
    is_speaking = True
    send_to_ui({"ai_state": "idle", "ai_text": text})
    
    try:
        # Clean text
        clean_text = text.replace('*', '').replace('#', '').replace('$', '')
        print(f"Mirror says: {clean_text}")
        
        # Generate audio
        tts = gTTS(text=clean_text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        # Play audio
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"tts error: {e}")
    finally:
        time.sleep(1.2)
        is_speaking = False
```

**Character Stripping:**
- `*` - Markdown bold/italic
- `#` - Markdown headers
- `$` - LaTeX math delimiters

**Synchronization:** Blocks until audio finishes (prevents overlapping speech)

---

## AI & Intent Processing

### ask_gemini()

**File:** `intelli.py:635-712` / `intelli-safeai.py:847-939`

**Purpose:** Route user query to appropriate handler or AI model

**Intent Routing:**
```python
def ask_gemini(text_query):
    query_lower = text_query.lower()
    send_to_ui({"ai_state": "thinking", "ai_text": "Thinking..."})
    
    sys_aw = f"SYSTEM AWARENESS: {datetime.datetime.now().strftime('%I:%M %p on %A, %B %d, %Y')}. Location: Dubai, UAE.\n"
    
    # 1. Spotify commands (native Spotipy API)
    if any(k in query_lower.split() for k in ["spotify", "music", "song", "track", "play", "pause", "skip", "next"]):
        try:
            if "pause" in query_lower or "stop" in query_lower:
                sp.pause_playback()
                return speech_queue.put("Paused Spotify.")
            elif "next" in query_lower or "skip" in query_lower:
                sp.next_track()
                return speech_queue.put("Skipping to the next song.")
            elif "play" in query_lower or "resume" in query_lower:
                song_name = query_lower.replace("play ", "", 1).strip()
                if song_name not in ["music", "spotify", "the music", "some music"]:
                    search_q = f"track:{song_name.split(' by ')[0]} artist:{song_name.split(' by ')[1]}" if " by " in song_name else song_name
                    results = sp.search(q=search_q, limit=1, type='track')
                    if results['tracks']['items']:
                        track = results['tracks']['items'][0]
                        sp.start_playback(uris=[track['uri']])
                        return speech_queue.put(f"Playing {track['name']} by {track['artists'][0]['name']}.")
                    return speech_queue.put("I couldn't find that song on Spotify.")
                sp.start_playback()
                return speech_queue.put("Resuming your music.")
        except spotipy.exceptions.SpotifyException:
            return speech_queue.put("I couldn't find an active Spotify device.")
    
    # 2. Calendar commands (JSON extraction)
    if "calendar" in query_lower.split() or "schedule" in query_lower.split():
        try:
            prompt = f"{sys_aw}EXTREMELY STRICT RULES: Output ONLY a single raw JSON object. NO markdown, NO text. Action mappings -> Add: {{\"intent\": \"add\", \"summary\": \"X\", \"date\": \"YYYY-MM-DD\", \"time\": \"HH:MM:00\"}}. Delete: {{\"intent\": \"delete\", \"summary\": \"X\"}}. Read: {{\"intent\": \"read\"}}.\nUser: {text_query}"
            res = client.models.generate_content(model='gemini-3.1-flash-lite', contents=prompt).text
            import re
            match = re.search(r'\{.*\}', res, re.DOTALL)
            if match:
                return process_calendar_intent(json.loads(match.group()))
        except:
            return speech_queue.put("I'm having trouble connecting to my calendar brain.")
    
    # 3. Todo commands (JSON extraction)
    if any(k in query_lower.split() for k in ["todo", "task", "list", "buy", "remind", "finish", "delete", "cancel", "to-do", "tasks", "lists"]):
        try:
            prompt = f"{sys_aw}EXTREMELY STRICT RULES: Output ONLY a single raw JSON object. NO markdown, NO conversational text. Action mappings -> Add: {{\"intent\": \"add\", \"task\": \"...\"}}. Delete: {{\"intent\": \"delete\", \"task\": \"...\"}}. Read: {{\"intent\": \"read\"}}. Clear: {{\"intent\": \"clear\"}}.\nUser: {text_query}"
            res = client.models.generate_content(model='gemini-3.1-flash-lite', contents=prompt).text
            import re
            match = re.search(r'\{.*\}', res, re.DOTALL)
            if match:
                return process_todo_intent(json.loads(match.group()))
        except:
            return speech_queue.put("I had a brain freeze managing your tasks.")
    
    # 4. Fallback chat (conversational)
    try:
        res = mirror_chat.send_message(f"{sys_aw}Keep responses brief (1-2 sentences).\nUser: {text_query}")
        speech_queue.put(res.text.strip())
    except:
        speech_queue.put("I am having trouble connecting to my brain right now.")
```

**Models Used:**
- `gemini-3.1-flash-lite` - Structured JSON extraction (calendar, todos)
- `gemini-3.1-flash-lite` - Conversational chat (fallback)
- `gemini-2.5-flash` - Vision analysis (image description)

**System Awareness Injection:**
Every prompt includes: current time/date, day of week, location (Dubai, UAE)

---

### process_calendar_intent()

**File:** `intelli.py:568-612` / `intelli-safeai.py:780-824`

**Intent Mapping:**
| Intent | Operation | Example |
|--------|-----------|---------|
| read | List upcoming events | "What's on my calendar?" |
| add | Insert new event | "Schedule meeting at 2pm" |
| delete | Remove event | "Cancel my 3pm meeting" |

```python
def process_calendar_intent(json_data):
    service = get_calendar_service()
    if not service:
        return speech_queue.put("I don't have your calendar linked yet.")
    
    intent = json_data.get("intent")
    
    if intent == "read":
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        events = service.events().list(calendarId='primary', timeMin=now, maxResults=15, 
                                       singleEvents=True, orderBy='startTime').execute().get('items', [])
        real_events = [e for e in events if "birthday" not in e.get('summary', '').lower()][:5]
        
        if not real_events:
            return speech_queue.put("You have absolutely nothing on your calendar coming up.")
        
        resp = "Here are your upcoming events: "
        for event in real_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            time_str = datetime.datetime.fromisoformat(start).strftime("%A at %I:%M %p") if 'T' in start else "All day"
            resp += f"{event.get('summary', 'Event')} {time_str}. "
        speech_queue.put(resp)
    
    elif intent == "add":
        summary, date_str, time_str = json_data.get("summary", "New Alert"), json_data.get("date"), json_data.get("time")
        if not date_str or not time_str:
            return speech_queue.put("I couldn't figure out exactly when you wanted me to schedule that.")
        
        start_datetime = f"{date_str}T{time_str}"
        end_datetime = (datetime.datetime.fromisoformat(start_datetime) + datetime.timedelta(minutes=30)).isoformat()
        tz = datetime.datetime.now().astimezone().tzinfo
        local_tz = str(tz) if tz else 'America/New_York'
        
        try:
            service.events().insert(calendarId='primary', body={
                'summary': summary,
                'start': {'dateTime': start_datetime, 'timeZone': local_tz},
                'end': {'dateTime': end_datetime, 'timeZone': local_tz}
            }).execute()
            speech_queue.put(f"I've added {summary} to your calendar.")
        except:
            speech_queue.put("I couldn't sync that format with your Google Calendar.")
    
    elif intent == "delete":
        summary = json_data.get("summary")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            events = service.events().list(calendarId='primary', q=summary, timeMin=now, maxResults=5, 
                                          singleEvents=True, orderBy='startTime').execute().get('items', [])
            service.events().delete(calendarId='primary', eventId=events[0]['id']).execute()
            speech_queue.put(f"I have canceled {events[0].get('summary', 'Unknown Event')} from your calendar.")
        except:
            speech_queue.put("I ran into an error trying to cancel that event.")
```

---

### process_todo_intent()

**File:** `intelli.py:614-633` / `intelli-safeai.py:826-845`

**Intent Mapping:**
| Intent | Operation | Example |
|--------|-----------|---------|
| read | List tasks | "What's on my list?" |
| add | Add task | "Add buy milk to my list" |
| delete | Remove task | "Remove buy milk" |
| clear | Clear all | "Clear my list" |

```python
def process_todo_intent(json_data):
    intent, task = json_data.get("intent"), json_data.get("task")
    todos = get_todos()
    
    if intent == "read":
        speech_queue.put(f"Here is your list: {', '.join(todos)}." if todos else 
                        "You don't have anything on your to-do list right now.")
    
    elif intent == "add" and task:
        todos.append(task)
        save_todos(todos)
        speech_queue.put(f"I've added {task} to your list.")
    
    elif intent == "clear":
        save_todos([])
        speech_queue.put("Your list has been cleared completely.")
    
    elif intent == "delete" and task:
        matched = next((item for item in todos if task.lower() in item.lower() or 
                       item.lower() in task.lower()), None)
        if matched:
            todos.remove(matched)
            save_todos(todos)
            speech_queue.put(f"I've crossed off {matched} from your list.")
        else:
            speech_queue.put(f"I couldn't find {task} on your to-do list.")
```

**Fuzzy Matching:** Handles partial task names (e.g., "milk" matches "buy milk")

---

## Data Persistence

### get_todos() / save_todos()

**File:** `intelli.py:474-488` / `intelli-safeai.py:676-690`

```python
def get_todos():
    if not db or not recognized_user:
        return []
    try:
        doc = db.collection('todos').document(recognized_user).get()
        return doc.to_dict().get('tasks', []) if doc.exists else []
    except:
        return []

def save_todos(todos):
    if not db or not recognized_user:
        return
    try:
        db.collection('todos').document(recognized_user).set({'tasks': todos})
        send_to_ui({"todos": todos})
    except Exception as e:
        print(f"firebase push error: {e}")
```

**Firebase Structure:**
```
todos/
├── {username}/
│   └── tasks: ["task1", "task2", ...]
```

---

### get_layout() / save_layout_widget()

**File:** `intelli.py:490-516` / `intelli-safeai.py:692-728`

**Get Layout:**
```python
def get_layout():
    baseline_layout = {
        "clock": {"x":0,"y":0}, "ai-assistant": {"x":0,"y":0},
        "calendar": {"x":0,"y":0}, "todo": {"x":0,"y":0},
        "weather": {"x":0,"y":0}, "spotify": {"x":0,"y":0}
    }
    
    if not db or not recognized_user:
        return baseline_layout
    
    try:
        doc = db.collection('layouts').document(recognized_user).get()
        if doc.exists:
            user_layout = doc.to_dict()
            for widget_id, coords in user_layout.items():
                if widget_id in baseline_layout:
                    baseline_layout[widget_id] = coords
            return baseline_layout
        else:
            # SafeAI: Auto-onboarding from template
            tmpl = db.collection('templates').document('default').get()
            if tmpl.exists:
                data = tmpl.to_dict()
                db.collection('layouts').document(recognized_user).set(data)
                return data
            else:
                db.collection('layouts').document(recognized_user).set(baseline_layout)
                return baseline_layout
    except:
        return baseline_layout

def save_layout_widget(widget_id, x, y):
    if not db or not recognized_user:
        return
    try:
        db.collection('layouts').document(recognized_user).set(
            {widget_id: {"x": x, "y": y}}, merge=True)
    except Exception as e:
        print(f"firebase layout error: {e}")
```

**Firebase Structure:**
```
layouts/
├── {username}/
│   ├── clock: {x: 10, y: 20}
│   ├── spotify: {x: 100, y: 50}
│   └── ...
```

---

### log_user_login()

**File:** `intelli.py:89-105` / `intelli-safeai.py:123-139`

**Purpose:** Track daily login counts for statistics

```python
def log_user_login(username):
    global login_stats
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if today not in login_stats:
        login_stats[today] = {}
    if username not in login_stats[today]:
        login_stats[today][username] = 0
    
    login_stats[today][username] += 1
    
    with open(login_stats_file, "w") as f:
        json.dump(login_stats, f)
    
    try:
        mqtt_client.publish(TOPIC_ALERTS, json.dumps({"type": "stats", "data": login_stats}))
    except Exception as e:
        print(f"mqtt stats error: {e}")
```

**Local Storage Format:**
```json
{
  "2024-07-03": {
    "Alice": 3,
    "Bob": 2
  },
  "2024-07-04": {
    "Alice": 1
  }
}
```

---

## UI & Communication

### send_to_ui()

**File:** `intelli.py:174-179` / `intelli-safeai.py:208-213`

```python
def send_to_ui(data_dict):
    if ws_server:
        try:
            ws_server.send_message_to_all(json.dumps(data_dict))
        except Exception as e:
            print(f"ws send error: {e}")
```

**WebSocket Message Protocol:**
```python
# Backend sends:
send_to_ui({
    "ai_state": "idle|listening|thinking",
    "ai_text": "Message to display",
    "todos": ["task1", "task2"],
    "temp": "25°C",
    "song": "Song Name",
    "artist": "Artist Name",
    "album_art": "https://...",
    "username": "Afthab",
    "layout": {"spotify": {"x": 100, "y": 50}},
    "is_locked": false
})

# Frontend sends:
{
    "type": "todo_add|todo_delete|layout_save",
    "task": "Buy milk",
    "widget_id": "spotify",
    "x": 150,
    "y": 100
}
```

---

### state_sync_thread()

**File:** `intelli.py:518-558` / `intelli-safeai.py:730-770`

**Purpose:** Sync user state (layout, todos) when user changes

```python
def state_sync_thread():
    last_todos = None
    last_user = None
    
    while True:
        try:
            # Detect user change
            if recognized_user != last_user:
                last_user = recognized_user
                last_todos = None
                
                if recognized_user:
                    layout = get_layout()
                    send_to_ui({
                        "username": recognized_user,
                        "layout": layout,
                        "is_locked": False
                    })
                else:
                    # Lock screen
                    baseline_layout = {...}
                    send_to_ui({
                        "username": "Guest",
                        "layout": baseline_layout,
                        "todos": [],
                        "is_locked": True
                    })
            
            # Sync todos if changed
            if recognized_user:
                current_todos = get_todos()
                if current_todos != last_todos:
                    send_to_ui({"todos": current_todos})
                    last_todos = current_todos
        
        except:
            pass
        
        time.sleep(2)
```

---

## ML Training

### retrain.py

**File:** `retrain.py:1-51`

**Purpose:** Train SVM classifier on face embeddings

```python
print("═════════════════════════════════════════════════")
print("   INTELLI-MIRROR : HYBRID AI RETRAINING HUB     ")
print("═════════════════════════════════════════════════")

print("\n1. Loading RAW enrollment data (100x100 crops)...")
DATA_FILE = Path('Magic_Mirror_Package/face_profiles/face_data.pkl')
OUT_FILE = Path('Magic_Mirror_Package/face_profiles/hybrid_ai_model.pkl')
SFACE_PATH = 'Magic_Mirror_Package/sface.onnx'

with open(DATA_FILE, 'rb') as f:
    faces, labels = pickle.load(f)

print(f"   Loaded {len(labels)} face captures.")

print("\n2. Booting up SFace Neural Network to extract 128d features...")
recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")

embeddings = []
for face in faces:
    bgr = cv2.cvtColor(cv2.resize(face, (112, 112)), cv2.COLOR_GRAY2BGR)
    feat = recognizer.feature(bgr)
    embeddings.append(feat.flatten())

X = np.array(embeddings)
y = np.array(labels)

print(f"\n3. Activating Support Vector Machine (SVM) on {len(set(y))} unique identities...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

svm = SVC(kernel='rbf', class_weight='balanced', probability=True, C=5, gamma=0.001)
svm.fit(X_train, y_train)

acc = svm.score(X_test, y_test)
print(f"   Test Accuracy mapped at: {acc*100:.1f}%")

print("\n4. Serializing final unified logic payload...")
joblib.dump(svm, OUT_FILE)
print(f"\n✅ SUCCESS! Retrained and securely serialized model to:\n   {OUT_FILE}\n")
```

**SVM Hyperparameters:**
- `kernel='rbf'` - Radial basis function kernel for non-linear separation
- `class_weight='balanced'` - Handle imbalanced classes
- `probability=True` - Enable probability estimates
- `C=5` - Regularization parameter
- `gamma=0.001` - RBF kernel coefficient

**Train/Test Split:** 80/20 with stratification

---

## Setup & Configuration

### generate_token.py

**File:** `generate_token.py:1-35`

**Purpose:** Set up Google Calendar OAuth for a user

```python
def main():
    print("==================================================")
    name = input("Enter the EXACT name of the person (e.g. Afthab, Pavan): ").strip()
    if not name:
        print("❌ Error: Name cannot be empty!")
        return
    
    token_dir = "calendar_tokens"
    os.makedirs(token_dir, exist_ok=True)
    
    if not os.path.exists('credentials.json'):
        print("❌ Error: 'credentials.json' is missing from this folder!")
        return
    
    print(f"\nOpening browser to authenticate Google Calendar events for {name}...")
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    token_filename = os.path.join(token_dir, f"{name}_token.json")
    with open(token_filename, 'w') as token:
        token.write(creds.to_json())
    
    print(f"\n✅ Success! {token_filename} has been created and saved.")
```

**Scopes:** `['https://www.googleapis.com/auth/calendar.events']`

---

## Related Documentation

- **ARCHITECTURE.md** - System design and component interactions
- **STRUCTURE.md** - Project organization and module relationships
- **DATAFLOW.md** - Data models and transformation pipelines
- **DECISIONS.md** - Architectural decision records
