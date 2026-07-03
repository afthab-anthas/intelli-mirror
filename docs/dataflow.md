# Intelli-Mirror Data Flow & Models

**Last Updated:** July 2026

## Table of Contents

1. [Data Models](#data-models)
2. [Input/Output Flows](#inputoutput-flows)
3. [External API Contracts](#external-api-contracts)
4. [Database Schema](#database-schema)
5. [Message Protocols](#message-protocols)
6. [State Management](#state-management)
7. [Data Transformation Pipelines](#data-transformation-pipelines)

---

## Data Models

### User Identity Model

**Representation:**
```python
User = {
    "username": str,              # Unique identifier (e.g., "Afthab")
    "recognized_user": bool,      # Currently logged in?
    "last_seen_time": timestamp,  # Last face detection
    "login_count": int           # Daily login count
}
```

**Lifecycle:**
1. **Enrollment:** Face capture (150 samples) → SFace embedding extraction → SVM training
2. **Recognition:** Webcam frame → YuNet detection → SFace embedding → SVM classification (confidence > 0.60)
3. **Timeout:** No face for 30-60s → Auto-logout

---

### Face Embedding Model

**Source:** SFace ONNX neural network

**Transformation:**
```
Raw Face (arbitrary size)
    ↓ (YuNet detection)
Bounding Box [x, y, w, h]
    ↓ (SFace alignment + crop)
Aligned 112×112 BGR image
    ↓ (SFace feature extraction)
128-dimensional embedding [f0, f1, ..., f127] ∈ ℝ^128
```

**Storage Format:**
```python
# In face_data.pkl (during enrollment)
faces_list = [
    np.array(100, 100),  # Grayscale face crop
    np.array(100, 100),
    ...  # 150 samples per user
]
labels_list = [0, 0, ..., 1, 1, ..., 2, 2, ...]  # User ID mapping

# During inference (in hybrid_ai_model.pkl)
embeddings = [
    np.array([f0, f1, ..., f127]),
    np.array([f0, f1, ..., f127]),
    ...
]
```

**Confidence:** SVM.predict_proba() returns normalized probability [0, 1]

---

### Speech Recognition Model

**Source:** Google Cloud Speech-to-Text API

**Input:**
```
Audio bytes (WAV format)
    ↓
Google Speech-to-Text API
    ↓
Transcript string (lowercase)
```

**Output:**
```
recognized_text: str  # e.g., "hey mirror play some music"
```

**Error Handling:** Recognition failures are silently ignored

---

### ML Classifier Model (SVM)

**Training Data:**
```
X_train: shape (N_train, 128)        # Face embeddings
y_train: shape (N_train,)            # User IDs [0, 1, 2, ...]
```

**Hyperparameters:**
```
SVC(
    kernel='rbf',                    # Radial basis function
    class_weight='balanced',         # Handle imbalanced data
    probability=True,                # Enable probability estimates
    C=5,                            # Regularization strength
    gamma=0.001                     # RBF kernel coefficient
)
```

**Inference:**
```
embedding: np.array([f0, ..., f127])
    ↓
model.predict_proba(embedding.reshape(1, -1))
    ↓
probs: [0.02, 0.95, 0.03]  # Probability per user
    ↓
max_prob = 0.95
if max_prob > 0.60:
    user_id = argmax(probs) = 1
    username = profiles["id_to_name"][1]
else:
    username = "Unknown"
```

---

### Hand Gesture Model

**Source:** MediaPipe Hand Landmarker

**Detection Output:**
```python
hand_landmarks = [
    Landmark(x=0.5, y=0.3, z=0.1),  # 0: Palm
    Landmark(x=0.4, y=0.2, z=0.1),  # 1: Thumb CMC
    ...
    Landmark(x=0.55, y=0.25, z=0.1) # 20: Pinky tip
]  # 21 total landmarks per hand
```

**Gesture Recognition:**
```
Landmark[4]: Thumb tip
Landmark[8]: Index finger tip

pinch_distance = euclidean(thumb_tip, index_tip)

if pinch_distance < 0.045:
    state = "GRABBED"  → pyautogui.mouseDown()
elif pinch_distance > 0.085:
    state = "RELEASED" → pyautogui.mouseUp()
else:
    state = "NEUTRAL"
```

**Mouse Coordinate Mapping:**
```
Hand center: (hand_x, hand_y) in frame space [0, w] × [0, h]
    ↓ (Crop margin FRAME_R=100)
Mapped coordinates: (x', y') in [FRAME_R, w-FRAME_R] × [FRAME_R, h-FRAME_R]
    ↓ (Normalize)
Screen coordinates: (screen_x, screen_y) in [0, SCREEN_W] × [0, SCREEN_H]
    ↓ (Exponential smoothing)
Final position: (curr_x, curr_y) with smoothing factor 7 or 14
    ↓
pyautogui.moveTo(curr_x, curr_y)
```

---

## Input/Output Flows

### Flow 1: Voice Command Processing

**Input:** User speech

**Process:**
```
Audio Recording (8-second max)
    ↓
Google Speech-to-Text
    ↓
Transcript string (lowercase)
    ↓
Wake word detection ("hey mirror")
    ↓
Intent classification (Spotify / Calendar / Todo / Chat / Vision)
    ↓
Intent handler routing
    ↓
Response generation
    ↓
gTTS text-to-speech
    ↓
Pygame audio playback
```

**Output:** Spoken audio response

---

### Flow 2: Face Recognition

**Input:** Webcam frame (30 FPS)

**Process (every 10 frames):**
```
Frame (640×480 BGR)
    ↓ (Skip if mouse_held)
    ↓
YuNet face detection
    ↓ (If faces detected)
SFace alignment + crop
    ↓
Extract 128D embedding
    ↓
SVM classification (probability > 0.60?)
    ↓
├─ YES → Update recognized_user, queue greeting
└─ NO → Check intruder logic (SafeAI only)
    ↓
Update last_seen_time
    ↓
(Every 60s of no face) → Auto-logout
```

**Output:** recognized_user state update, UI notification

---

### Flow 3: Hand Gesture Control

**Input:** Webcam frame (30 FPS)

**Process:**
```
Frame (640×480 BGR)
    ↓
MediaPipe hand detection
    ↓ (If hand detected)
Extract 21 landmarks
    ↓
Calculate hand center
    ↓
Map to screen coordinates with smoothing
    ↓
pyautogui.moveTo(x, y)
    ↓
Check pinch distance (thumb ↔ index)
    ↓
├─ < 0.045 → pyautogui.mouseDown()
├─ > 0.085 → pyautogui.mouseUp()
└─ Otherwise → Maintain state
```

**Output:** Mouse cursor position, mouse clicks

---

### Flow 4: Widget State Persistence

**Input:** User drags widget on UI

**Process:**
```
Frontend drag event
    ↓
Send WebSocket: {type: "layout_save", widget_id, x, y}
    ↓
Backend receives message
    ↓
Firebase: layouts/{username}/{widget_id} = {x, y}
    ↓
(On next user login)
    ↓
Firebase: get layouts/{username}
    ↓
UI updates widget positions via send_to_ui()
```

**Output:** Persisted widget positions

---

## External API Contracts

### Google Gemini API

**Endpoints:**
- `client.models.generate_content(model='gemini-3.4b-it', contents=prompt)`
- `client.models.generate_content(model='gemini-2.5-flash', contents=[image, prompt])`
- `client.chats.create(model='gemini-3.1-flash-lite')`
- `mirror_chat.send_message(...)`

**Request:**
```python
# Structured output (calendar/todo)
prompt = """
EXTREMELY STRICT RULES: Output ONLY a single raw JSON object. NO markdown, NO text.
Action mappings:
- Add: {"intent": "add", "summary": "X", "date": "YYYY-MM-DD", "time": "HH:MM:00"}
- Delete: {"intent": "delete", "summary": "X"}
- Read: {"intent": "read"}

User: {user_input}
"""

# Conversational
prompt = """
SYSTEM AWARENESS: 02:45 PM on Friday, July 03, 2026. Location: Dubai, UAE.
Keep responses brief and conversational (1-2 sentences).
User: {user_input}
"""

# Vision analysis
contents = [image_pil, prompt_str]
```

**Response:**
```python
# Structured
{"intent": "add", "summary": "Buy milk", "date": "2024-07-05", "time": "14:30:00"}

# Conversational
"That's a great idea! I'll help you with that."

# Vision
"You're holding a coffee mug. It looks like your favorite one!"
```

**Error Handling:** Wrapped in try/except, fallback to generic error message

---

### Google Calendar API

**Scope:** `https://www.googleapis.com/auth/calendar.events`

**Operations:**

| Operation | Method | Parameters | Response |
|-----------|--------|-----------|----------|
| List events | `events().list()` | calendarId, timeMin, maxResults, orderBy | items array |
| Create event | `events().insert()` | calendarId, body | event object |
| Delete event | `events().delete()` | calendarId, eventId | (none) |

**Request Examples:**
```python
# List upcoming events
events = service.events().list(
    calendarId='primary',
    timeMin=now,
    maxResults=15,
    singleEvents=True,
    orderBy='startTime'
).execute().get('items', [])

# Insert event
service.events().insert(
    calendarId='primary',
    body={
        'summary': 'Team Meeting',
        'start': {'dateTime': '2024-07-05T14:30:00', 'timeZone': 'Asia/Dubai'},
        'end': {'dateTime': '2024-07-05T15:00:00', 'timeZone': 'Asia/Dubai'}
    }
).execute()

# Delete event
service.events().delete(
    calendarId='primary',
    eventId='event_id_here'
).execute()
```

---

### Spotify API

**Authentication:** OAuth2 with SpotifyOAuth

**Operations:**

| Operation | Method | Parameters | Response |
|-----------|--------|-----------|----------|
| Get playback state | `current_playback()` | (none) | playback object |
| Pause playback | `pause_playback()` | (none) | (none) |
| Resume playback | `start_playback()` | (optional) uris | (none) |
| Skip track | `next_track()` | (none) | (none) |
| Search tracks | `search()` | q, limit, type | search results |

**Request Examples:**
```python
# Get current playback
playback = sp.current_playback()
print(playback['item']['name'])      # Song name
print(playback['is_playing'])        # Playing status
print(playback['progress_ms'])       # Current position
print(playback['item']['duration_ms'])  # Total duration
print(playback['item']['album']['images'][0]['url'])  # Album art

# Search and play
results = sp.search(q='track:Bohemian artist:Queen', limit=1, type='track')
track_uri = results['tracks']['items'][0]['uri']
sp.start_playback(uris=[track_uri])

# Pause/resume
sp.pause_playback()
sp.start_playback()
```

---

### Firebase Firestore

**Collections:**

| Collection | Document | Structure | Usage |
|-----------|----------|-----------|-------|
| todos | {username} | {tasks: [...]} | Per-user todo lists |
| layouts | {username} | {widget_id: {x, y}} | Widget positions |
| security_requests | Auto | {name, status, image, timestamp} | Intruder capture |
| templates | default | {widget_id: {x, y}} | Auto-onboarding |

**Operations:**
```python
# Read
doc = db.collection('todos').document(username).get()
if doc.exists:
    data = doc.to_dict()
    tasks = data.get('tasks', [])

# Write
db.collection('todos').document(username).set({'tasks': new_tasks})

# Write with merge (partial update)
db.collection('layouts').document(username).set(
    {'spotify': {'x': 100, 'y': 50}},
    merge=True
)

# Real-time listener
def on_snapshot(col_snapshot, changes, read_time):
    for doc in col_snapshot:
        data = doc.to_dict()
        print(data)

db.collection('security_requests').where(
    'status', '==', 'approved'
).on_snapshot(on_snapshot)
```

---

### Open-Meteo Weather API

**Endpoint:** `https://api.open-meteo.com/v1/forecast`

**Parameters:**
```
latitude=25.2048  (Dubai)
longitude=55.2708 (Dubai)
current_weather=true
```

**Response:**
```json
{
    "current_weather": {
        "temperature": 38.5,
        "windspeed": 12.3,
        "time": "2024-07-03T14:00"
    }
}
```

**Processing:**
```python
data = json.loads(response.read().decode())
temp = data['current_weather']['temperature']
latest_temp = f"{round(temp)}°C"
send_to_ui({"temp": latest_temp})
```

---

### HiveMQ MQTT Broker

**Broker:** `broker.hivemq.com:1883`

**Topics:**
- Publish: `intellimirror_77x9/alerts`
- Subscribe: `intellimirror_77x9/security_mode`

**Messages:**

| Type | Payload | Triggered By |
|------|---------|--------------|
| stats | {type: "stats", data: login_stats} | `log_user_login()` |
| intruder | {type: "intruder", time, image} | Unknown face in SafeAI |
| security_mode | "ENFORCED" or "NORMAL" | Remote control |

**Example:**
```python
# Publish stats
mqtt_client.publish(TOPIC_ALERTS, json.dumps({
    "type": "stats",
    "data": {
        "2024-07-03": {"Alice": 3, "Bob": 2}
    }
}))

# Publish intruder alert
mqtt_client.publish(TOPIC_ALERTS, json.dumps({
    "type": "intruder",
    "time": "02:45:32 PM",
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}))

# Receive security mode
def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    if payload == "ENFORCED":
        security_enforced = True
```

---

## Database Schema

### Firebase Firestore

```
intelli-mirror/
├── todos/
│   ├── Afthab/
│   │   └── tasks: ["Buy milk", "Call mom"]
│   ├── Pavan/
│   │   └── tasks: ["Study ML", "Fix bug"]
│   └── Alice/
│       └── tasks: []
│
├── layouts/
│   ├── Afthab/
│   │   ├── clock: {x: 10, y: 20}
│   │   ├── spotify: {x: 100, y: 50}
│   │   ├── ai-assistant: {x: 500, y: 100}
│   │   ├── calendar: {x: 20, y: 100}
│   │   ├── weather: {x: 400, y: 20}
│   │   └── todo: {x: 600, y: 200}
│   └── Pavan/
│       └── (similar structure)
│
├── security_requests/
│   ├── {auto-id}/
│   │   ├── name: "Unknown"
│   │   ├── status: "pending|approved|rejected"
│   │   ├── image: "data:image/jpeg;base64,..."
│   │   └── timestamp: FieldValue.SERVER_TIMESTAMP
│   └── ...
│
└── templates/
    └── default/
        ├── clock: {x: 0, y: 0}
        ├── spotify: {x: 0, y: 0}
        └── ...
```

### Local JSON Storage

**login_stats.json:**
```json
{
  "2024-07-03": {
    "Afthab": 5,
    "Pavan": 2,
    "Alice": 1
  },
  "2024-07-04": {
    "Afthab": 3,
    "Bob": 1
  }
}
```

### Face Recognition Models

**face_data.pkl (Pickle binary):**
```python
(
    faces_list=[
        np.array((100, 100), dtype=uint8),  # Grayscale face crop
        np.array((100, 100), dtype=uint8),
        ...  # 150 × num_users samples
    ],
    labels_list=[
        0, 0, ..., 0,  # 150 samples for user 0
        1, 1, ..., 1,  # 150 samples for user 1
        ...
    ]
)
```

**profiles.pkl (Pickle binary):**
```python
{
    "name_to_id": {
        "Afthab": 0,
        "Pavan": 1,
        "Alice": 2
    },
    "id_to_name": {
        0: "Afthab",
        1: "Pavan",
        2: "Alice"
    }
}
```

**hybrid_ai_model.pkl (Joblib binary):**
```python
# Scikit-learn SVM classifier
SVC(
    C=5,
    class_weight='balanced',
    kernel='rbf',
    probability=True,
    gamma=0.001
)
# Fitted on 128D embeddings
# Classes: [0, 1, 2, ...] mapping to user IDs
```

---

## Message Protocols

### WebSocket (Frontend ↔ Backend)

**Port:** 8765 (localhost)

**Backend → Frontend:**
```json
{
  "ai_state": "idle|listening|thinking",
  "ai_text": "Current message",
  "todos": ["task1", "task2"],
  "temp": "25°C",
  "song": "Bohemian Rhapsody",
  "artist": "Queen",
  "album_art": "https://i.scdn.co/...",
  "progress_ms": 120000,
  "duration_ms": 354612,
  "is_playing": true,
  "username": "Afthab",
  "layout": {
    "spotify": {"x": 100, "y": 50},
    "clock": {"x": 10, "y": 20}
  },
  "is_locked": false,
  "type": "start_timer",
  "minutes": 25
}
```

**Frontend → Backend:**
```json
{
  "type": "todo_add",
  "task": "Buy milk"
}

{
  "type": "todo_delete",
  "task": "Buy milk"
}

{
  "type": "layout_save",
  "widget_id": "spotify",
  "x": 150,
  "y": 100
}
```

### MQTT Messages

**Security Stats:**
```json
{
  "type": "stats",
  "data": {
    "2024-07-03": {
      "Afthab": 5,
      "Pavan": 2
    }
  }
}
```

**Intruder Alert:**
```json
{
  "type": "intruder",
  "time": "02:45:32 PM",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA..."
}
```

**Security Mode Control (inbound):**
```
"ENFORCED"
"NORMAL"
```

---

## State Management

### Global Variables (Python)

```python
# User state
recognized_user: Optional[str]      # Currently logged-in user
last_seen_time: float              # Timestamp of last face detection
FACE_TIMEOUT: int                  # Auto-logout delay (seconds)

# Audio state
is_speaking: bool                  # Currently playing TTS?
listening_for_command: bool        # Waiting for voice command?
speech_queue: queue.Queue          # Thread-safe speech queue

# Vision state
latest_frame: Optional[np.ndarray] # Current webcam frame
latest_temp: str                   # Latest weather temperature

# Security state (SafeAI)
pending_approval: bool             # Intruder awaiting admin approval?
approved_username: Optional[str]   # User approved for enrollment
approval_event: threading.Event    # Signal for enrollment trigger
enrollment_active: bool            # Currently enrolling user?
reload_ai_model: bool             # Reload SVM model after training?

# MQTT state
security_enforced: bool            # Security mode active?

# Login tracking
login_stats: dict                  # Daily login counts

# Configuration
WAKE_WORD: str = "hey mirror"
TIMEOUT_SECONDS: int = 15
CALIBRATION_INTERVAL: int = 60
```

### Firebase Listener State

```python
approval_listener():
    # Watches: db.collection('security_requests').where('status', '==', 'approved')
    # On update: approval_event.set()
    # On trigger: Main loop calls enroll_user(approved_username)
```

---

## Data Transformation Pipelines

### User Enrollment Pipeline

```
User says: "Hey Mirror, enroll [name]"
    ↓
enroll_user(name) called
    ↓
1. Load existing profiles.pkl
2. Assign new ID to name
3. Initialize Pi 5 camera
    ↓
4. Capture 150 face samples (YuNet + SFace)
    ↓
5. Save to face_data.pkl:
   faces: [100×100 grayscale crop] × 150
   labels: [user_id] × 150
    ↓
6. Serialize profiles.pkl (id ↔ name mapping)
    ↓
7. Execute retrain.py:
   Load faces + labels
   Extract embeddings via SFace
   Train SVM with RBF kernel
   Save to hybrid_ai_model.pkl
    ↓
8. reload_ai_model flag triggers model reload in vision thread
    ↓
9. "Enrollment complete" spoken
```

### Intent Processing Pipeline

```
User speech: "play my favorite song"
    ↓
Google Speech-to-Text: "play my favorite song"
    ↓
ask_gemini() keyword matching:
   - Contains "play" → Spotify intent
    ↓
handle Spotify:
   - Default: resume current playback
   - No song specified: sp.start_playback()
    ↓
send_to_ui({
  "song": "Current Song",
  "artist": "Artist Name",
  "is_playing": true
})
    ↓
speech_queue.put("Resuming your music.")
    ↓
Main loop: speak("Resuming your music.")
```

### Widget State Pipeline

```
User drags Spotify widget on UI
    ↓
Frontend InteractJS event: move
    ↓
Frontend sends WebSocket:
{
  "type": "layout_save",
  "widget_id": "spotify",
  "x": 150,
  "y": 100
}
    ↓
Backend on_message() receives
    ↓
Firebase save:
db.collection('layouts').document(recognized_user).set(
  {'spotify': {'x': 150, 'y': 100}},
  merge=True
)
    ↓
(Next user login)
    ↓
get_layout() retrieves from Firebase
    ↓
Frontend renders at saved coordinates
```

---

## Related Documentation

- **ARCHITECTURE.md** - System design and component interactions
- **CODE.md** - Function signatures and implementation details
- **DECISIONS.md** - Architectural decision records
