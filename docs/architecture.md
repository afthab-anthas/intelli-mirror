# Intelli-Mirror System Architecture

**Last Updated:** July 2026  
**Version:** 2.0 (SafeAI + Admin Approval)

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Technology Stack](#technology-stack)
4. [Data Flow](#data-flow)
5. [Integration Patterns](#integration-patterns)
6. [Scalability Considerations](#scalability-considerations)
7. [Performance Optimization](#performance-optimization)

---

## System Overview

Intelli-Mirror is a comprehensive smart mirror engine designed for real-time multimodal interaction. It combines computer vision (face recognition + hand gesture tracking), voice intelligence, and external service integrations into a unified desktop application.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (PWA + Website)                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Website UI (HTML/CSS/JS) via WebSocket on localhost:8765   │ │
│  │ - Draggable Widgets (Clock, Calendar, Todo, Spotify, etc)  │ │
│  │ - Real-time state sync from backend                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               BACKEND (Python Core Engine)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Main Process (intelli.py or intelli-safeai.py)            │ │
│  │                                                            │ │
│  │ ┌─────────────────────────────────────────────────────┐   │ │
│  │ │ Thread 1: unified_vision_thread()                  │   │ │
│  │ │ - Hand Tracking (MediaPipe)                        │   │ │
│  │ │ - Face Detection & Recognition (YuNet + SFace)    │   │ │
│  │ │ - Mouse Control via Hand Gestures                 │   │ │
│  │ │ - Intruder Detection & Admin Approval Flow        │   │ │
│  │ └─────────────────────────────────────────────────────┘   │ │
│  │                                                            │ │
│  │ ┌─────────────────────────────────────────────────────┐   │ │
│  │ │ Thread 2: audio_callback() via start_listening()  │   │ │
│  │ │ - Speech Recognition (Google Speech-to-Text)     │   │ │
│  │ │ - Wake Word Detection ("Hey Mirror")             │   │ │
│  │ │ - Command Processing & AI Integration            │   │ │
│  │ └─────────────────────────────────────────────────────┘   │ │
│  │                                                            │ │
│  │ ┌─────────────────────────────────────────────────────┐   │ │
│  │ │ Thread 3: speak() Function (TTS)                  │   │ │
│  │ │ - Google Text-to-Speech (gTTS)                   │   │ │
│  │ │ - Audio Playback (Pygame Mixer)                  │   │ │
│  │ └─────────────────────────────────────────────────────┘   │ │
│  │                                                            │ │
│  │ ┌─────────────────────────────────────────────────────┐   │ │
│  │ │ Background Threads                               │   │ │
│  │ │ - weather_thread(): Open-Meteo API polling       │   │ │
│  │ │ - spotify_sync_thread(): Spotify status sync     │   │ │
│  │ │ - state_sync_thread(): User layout & todo sync  │   │ │
│  │ │ - approval_listener(): Firebase security stream │   │ │
│  │ └─────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              EXTERNAL SERVICES & DATA STORAGE                   │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │ Google Gemini    │  │ Firebase Cloud   │  │ Spotify API │  │
│  │ AI Models        │  │ - Todos          │  │ Playback    │  │
│  │ - gemini-3-4b-it │  │ - Layouts        │  │ Control     │  │
│  │ - gemini-2.5-flash│ │ - Security Req.  │  │             │  │
│  └──────────────────┘  └──────────────────┘  └─────────────┘  │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │ Google Calendar  │  │ Open-Meteo       │  │ HiveMQ MQTT │  │
│  │ API              │  │ Weather API      │  │ Broker      │  │
│  │ Event Mgmt       │  │ (Dubai coords)   │  │ Security    │  │
│  └──────────────────┘  └──────────────────┘  └─────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Local Storage                                           │  │
│  │ - login_stats.json (daily login tracking)              │  │
│  │ - calendar_tokens/ (per-user Google OAuth)            │  │
│  │ - Magic_Mirror_Package/face_profiles/ (ML models)     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. **Main Engine (intelli.py / intelli-safeai.py)**

**Entry Point:** `if __name__ == "__main__"` at line 762 (intelli.py) or 989 (intelli-safeai.py)

**Key Responsibilities:**
- Initialize all background threads
- Manage the main event loop (speech queue processing)
- Coordinate between vision, audio, and UI systems
- Handle graceful shutdown on KeyboardInterrupt

**Main Files:**
- `intelli.py` - Original version (line 1-799)
- `intelli-safeai.py` - Enhanced version with admin approval flow (line 1-1050)

### 2. **Vision System (unified_vision_thread)**

**Location:** `intelli.py:218-369` / `intelli-safeai.py:359-569`

**Components:**

#### Hand Tracking (MediaPipe)
- **Model:** Hand Landmarker from Google MediaPipe
- **Download:** Auto-downloads from `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`
- **Detection:** Single hand with 21 landmarks per frame
- **Gesture Recognition:**
  - Pinch distance < 0.045 → Mouse DOWN
  - Pinch distance > 0.085 → Mouse UP
  - Hand center mapped to screen coordinates with smoothing
- **Smoothing:** Exponential averaging with SMOOTHING_FREE=7 (no drag) or SMOOTHING_DRAG=14 (dragging)
- **Frame Margin:** FRAME_R=100 pixels to avoid edge activation

#### Face Recognition Pipeline
- **Detection Model:** YuNet ONNX (`Magic_Mirror_Package/yunet.onnx`)
- **Recognition Model:** SFace ONNX (`Magic_Mirror_Package/sface.onnx`)
- **ML Classifier:** Scikit-learn SVM (saved as `hybrid_ai_model.pkl`)
- **Process:**
  1. Every 10 frames, detect faces in the webcam feed
  2. Align and crop the best face using SFace
  3. Extract 128-dimensional embedding
  4. Classify with SVM trained on known users
  5. Confidence threshold: 0.60
- **User Recognition:** Maps to `profiles.pkl` (id_to_name mapping)
- **Timeout:** Auto-logout after FACE_TIMEOUT=30-60 seconds

#### Intruder Detection (intelli-safeai.py only)
- **Workflow:**
  1. Unknown face detected for 3+ consecutive frames
  2. Capture current frame as JPEG (320x240, quality 60)
  3. Encode as Base64
  4. If security_enforced: Publish to MQTT topic `intellimirror_77x9/alerts`
  5. Upload to Firebase collection `security_requests` for admin approval
  6. Set pending_approval flag, timeout after 60 seconds

#### Admin Approval Flow (intelli-safeai.py only)
- **Location:** `approval_listener()` at line 259-274
- **Process:**
  1. Firebase listener watches `security_requests` collection for status='approved'
  2. Sets `approval_event` when approved
  3. Main loop checks `approval_event.is_set()` at line 1003
  4. Calls `enroll_user(approved_username)` at line 1004
  5. New user's face is scanned (150 samples)
  6. retrain.py is executed to update the model

### 3. **Audio System**

#### Speech Recognition
**Location:** `audio_callback()` at line 714-741 (intelli.py) / 941-968 (intelli-safeai.py)

- **Library:** SpeechRecognition (Google Speech-to-Text backend)
- **Microphone:** Auto-detected via `sr.Microphone()`
- **Calibration:**
  - Initial: 3 seconds of ambient noise adjustment
  - Periodic: Every 60 seconds (CALIBRATION_INTERVAL)
  - Energy threshold boosted by +300
- **Wake Word:** "hey mirror" (line 561 / 773)
- **Listening Mode:**
  - Activated after wake word
  - 15-20 second timeout before sleep
  - Single command per wake

#### Text-to-Speech
**Location:** `speak()` at line 184-209 (intelli.py) / 218-243 (intelli-safeai.py)

- **Library:** gTTS (Google Text-to-Speech)
- **Output:** Pygame Mixer for audio playback
- **Cleaning:** Strips markdown (`*`, `#`) and LaTeX (`$`) symbols before speaking
- **Synchronization:** Blocks until audio playback completes

### 4. **AI Integration (ask_gemini)**

**Location:** `ask_gemini()` at line 635-712 (intelli.py) / 847-939 (intelli-safeai.py)

**Models Used:**
- `gemini-3.4b-it` (gemma model) - For structured JSON outputs
- `gemini-2.5-flash` - For vision analysis
- `gemini-3.1-flash-lite` - For conversational chat (intelli-safeai.py)

**Intent Detection & Processing:**

| Intent | Keywords | Processing | Model |
|--------|----------|-----------|-------|
| Spotify | music, play, pause, skip, next | Direct API calls to Spotipy | Native |
| Calendar | calendar, schedule | JSON extraction → `process_calendar_intent()` | gemini-3.4b-it |
| Todo | todo, task, list, remind | JSON extraction → `process_todo_intent()` | gemini-3.4b-it |
| Vision | what is this, what am i holding | Frame capture + analysis | gemini-2.5-flash |
| Pomodoro | focus mode, study session | Timer start + Spotify playlist | Native |
| Chat | anything else | Conversational fallback | gemini-3.1-flash-lite |

**System Awareness Injection:**
Every prompt includes current time, date, and location (Dubai, UAE) for context-aware responses.

### 5. **Data Persistence (Firebase)**

**Location:** Lines 461-516 (intelli.py) / 245-729 (intelli-safeai.py)

**Collections & Documents:**

| Collection | Document | Data | Purpose |
|------------|----------|------|---------|
| `todos` | `{username}` | `{tasks: [...]}` | Per-user todo lists |
| `layouts` | `{username}` | Widget positions | UI widget state persistence |
| `security_requests` | Auto-generated | Image, status, timestamp | Intruder capture & approval |
| `templates` | `default` | Layout template | Auto-onboarding for new users |

**Operations:**
- `get_todos()` - Fetch user's todo list
- `save_todos()` - Update user's todo list
- `get_layout()` - Fetch or create default layout
- `save_layout_widget()` - Update individual widget position

### 6. **WebSocket Communication (Frontend ↔ Backend)**

**Location:** Lines 135-181 (intelli.py) / 169-215 (intelli-safeai.py)

**Protocol:** JSON over WebSocket on `localhost:8765`

**Message Types:**

**Backend → Frontend:**
```json
{
  "ai_state": "idle|listening|thinking",
  "ai_text": "Current assistant message",
  "todos": ["task1", "task2"],
  "temp": "25°C",
  "song": "Song Name",
  "artist": "Artist Name",
  "album_art": "image_url",
  "progress_ms": 120000,
  "duration_ms": 240000,
  "is_playing": true,
  "username": "User Name",
  "layout": {widget_id: {x, y}},
  "is_locked": false
}
```

**Frontend → Backend:**
```json
{
  "type": "todo_add|todo_delete|layout_save",
  "task": "task description",
  "widget_id": "spotify",
  "x": 100,
  "y": 200
}
```

### 7. **MQTT Security Dashboard**

**Location:** Lines 71-132 (intelli.py) / 105-166 (intelli-safeai.py)

**Broker:** HiveMQ (broker.hivemq.com:1883)

**Topics:**
- `intellimirror_77x9/security_mode` → Subscribe (Receive ENFORCED/NORMAL)
- `intellimirror_77x9/alerts` → Publish (Send stats, intruder alerts)

**Payload Examples:**

**Stats Update:**
```json
{
  "type": "stats",
  "data": {
    "2024-07-03": {
      "Alice": 3,
      "Bob": 2
    }
  }
}
```

**Intruder Alert:**
```json
{
  "type": "intruder",
  "time": "02:45:32 PM",
  "image": "data:image/jpeg;base64,..."
}
```

---

## Technology Stack

### Core Runtime
| Technology | Purpose | Version/Location |
|-----------|---------|------------------|
| Python | Core engine | 3.7+ |
| OpenCV | Computer vision (YuNet, SFace) | opencv-contrib-python |
| MediaPipe | Hand tracking | mediapipe (downloads task model) |
| NumPy | Numerical computation | numpy |
| Scikit-learn | ML model training/inference | scikit-learn (SVM) |
| Joblib | Model serialization | joblib |

### Audio & Speech
| Technology | Purpose | Version/Location |
|-----------|---------|------------------|
| SpeechRecognition | Speech-to-Text | SpeechRecognition (Google backend) |
| gTTS | Text-to-Speech | gTTS |
| Pygame | Audio playback | pygame |

### External APIs
| Service | Purpose | Authentication |
|---------|---------|-----------------|
| Google Gemini | AI assistant | GEMINI_API_KEY (env) |
| Google Calendar | Event management | OAuth2 tokens in calendar_tokens/ |
| Spotify | Music playback control | SpotifyOAuth credentials (env) |
| Open-Meteo | Weather data | Public API (no auth) |
| Firebase | Data persistence | firebase_credentials.json |

### Web & Communication
| Technology | Purpose | Port |
|-----------|---------|------|
| WebSocket | Frontend ↔ Backend | 8765 |
| MQTT | Remote security dashboard | HiveMQ broker |
| PyAutoGUI | Mouse control from hand tracking | - |

### Frontend
| Technology | Purpose | Framework |
|-----------|---------|-----------|
| HTML5 | Markup | Semantic HTML |
| CSS3 | Styling | Custom (no framework) |
| JavaScript (Vanilla) | Interactivity | InteractJS for drag-drop |
| WebSocket API | Real-time updates | Native browser API |

---

## Data Flow

### Flow 1: User Recognition & Login
```
1. Vision thread reads webcam frame
2. Every 10 frames:
   - YuNet detects faces
   - SFace aligns best face
   - Extract 128D embedding
   - SVM classifies against known users
   - If confidence > 0.60:
     * Update recognized_user
     * Queue speech: "Hi {name}"
     * log_user_login(name)
     * Reset last_seen_time
3. If no face for 30-60s:
   - recognized_user = None
   - Queue speech: "Session logged out."
4. UI updates with layout & todos for that user
```

### Flow 2: Voice Command Processing
```
1. Microphone listening in background
2. User says "Hey Mirror"
3. audio_callback() detects wake word
4. State → listening_for_command = True
5. UI updates: ai_state = "listening"
6. User speaks command (max 8 seconds)
7. Google Speech-to-Text returns transcription
8. ask_gemini() analyzes intent
9. Appropriate handler processes command
10. Response queued to speech_queue
11. speak() plays TTS audio
12. UI updates and Firebase syncs
```

### Flow 3: Intruder Detection & Admin Approval (intelli-safeai.py)
```
1. Vision thread detects unknown face for 3+ frames
2. Capture and compress current frame to JPEG
3. Encode as Base64
4. Upload to Firebase (security_requests collection)
5. Publish to MQTT if security_enforced
6. approval_listener() thread monitors Firebase
7. When status='approved' in Firebase:
   - approval_event.set()
   - Main loop detects event
   - enroll_user(approved_username) called
   - Pi 5 hardware camera captures 150 samples
   - retrain.py retrains SVM model
   - reload_ai_model flag triggers model reload
   - speech_queue: "Enrollment complete"
```

### Flow 4: Widget State Sync
```
1. User drags widget on UI
2. Frontend broadcasts JSON over WebSocket
3. Backend receives: type="layout_save", widget_id, x, y
4. Firebase saves to layouts/{username}/{widget_id}
5. On next user recognition, get_layout() fetches latest positions
```

---

## Integration Patterns

### 1. **Multi-Service AI Orchestration**

The system uses a "progressive routing" pattern:
1. Check for Spotify keywords → Spotipy API
2. Check for Calendar keywords → Process calendar intent
3. Check for Todo keywords → Process todo intent
4. Check for Vision keywords → Gemini with image
5. Fallback → General chat with Gemini

This avoids unnecessary API calls and keeps responses snappy.

### 2. **Thread-Safe Communication**

All inter-thread communication uses thread-safe primitives:
- `queue.Queue()` for speech_queue (audio → UI)
- `threading.Event()` for approval_event (Firebase → main)
- Global variables with explicit synchronization (e.g., recognized_user)

### 3. **Background Polling Pattern**

Long-running operations (weather, Spotify, state sync) use dedicated threads:
```python
def background_thread():
    while True:
        try:
            # do work
        except:
            pass
        time.sleep(interval)

threading.Thread(target=background_thread, daemon=True).start()
```

All threads are daemon=True for clean shutdown.

### 4. **Firebase Real-Time Listeners**

The approval flow uses Firebase's `on_snapshot()` for push-based updates:
```python
def approval_listener():
    if not db: return
    def on_snapshot(col_snapshot, changes, read_time):
        # Process approved requests
    db.collection('security_requests').where('status', '==', 'approved').on_snapshot(on_snapshot)

threading.Thread(target=approval_listener, daemon=True).start()
```

---

## Scalability Considerations

### Current Limitations
1. **Single Mirror:** Designed for one physical device
2. **Single User Recognition:** At most one recognized_user at a time
3. **Local Model Training:** retrain.py blocks the main process
4. **Synchronous API Calls:** Google Calendar/Spotify operations block

### Potential Improvements
1. **Model Quantization:** Compress SVM model for faster loading
2. **Async Firebase:** Replace blocking calls with async listeners
3. **Batch Vision Processing:** Process multiple faces per frame
4. **Edge Deployment:** Consider TensorFlow Lite for Raspberry Pi
5. **Database Indexing:** Add indexes to Firebase for faster queries

---

## Performance Optimization

### Vision Performance
- **Frame Skip:** Face recognition runs every 10 frames (~3 FPS at 30 FPS camera)
- **Hand Tracking:** Full 30 FPS for responsive mouse control
- **Early Exit:** Skip face detection if mouse is being dragged
- **Lazy Loading:** Models only loaded once at startup

### Audio Performance
- **Acoustic Model Reuse:** Recognizer object reused across callbacks
- **Energy Threshold Tuning:** +300 boost reduces false positives
- **Phrase Time Limit:** 8-second max to prevent timeout lag

### Memory Management
- **Frame Resizing:** Intruder images downsampled to 320x240
- **Pickle Serialization:** Models serialized with joblib (platform-independent)
- **Garbage Collection:** Implicit cleanup of daemon threads on exit

### Network Optimization
- **MQTT QoS 0:** Fire-and-forget for stats/alerts (faster)
- **WebSocket Batching:** Multiple updates can coalesce (browser optimization)
- **Firebase Offline:** Cloud Firestore supports offline persistence

---

## Architecture Decisions

**Q: Why separate intelli.py and intelli-safeai.py?**  
A: intelli-safeai.py adds admin approval flow for security-conscious deployments while keeping original simpler version available.

**Q: Why SVM instead of neural network for face recognition?**  
A: SVM is lightweight, interpretable, and efficient for small number of faces (typically < 20 users).

**Q: Why MQTT for alerts instead of direct Firebase?**  
A: MQTT provides real-time pub/sub with low latency, suitable for security dashboards.

**Q: Why daemon threads throughout?**  
A: Enables clean shutdown on Ctrl+C without waiting for background tasks.

---

## Related Documentation

- **STRUCTURE.md** - Folder organization and module relationships
- **CODE.md** - Detailed function signatures and algorithms
- **DATAFLOW.md** - Data models and transformation pipelines
- **DECISIONS.md** - ADRs for major architectural choices
