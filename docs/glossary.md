# Intelli-Mirror Glossary & Terminology

**Last Updated:** July 2026

## Domain-Specific Terminology

### Computer Vision

| Term | Definition | Example |
|------|-----------|---------|
| **Face Detection** | Locating faces in an image (bounding box) | YuNet finds face at [100, 50, 80, 90] |
| **Face Alignment** | Normalizing face orientation and crop | SFace rotates face to frontal view |
| **Face Embedding** | Numerical representation of face features | 128-dimensional vector from SFace |
| **Face Recognition** | Identifying who a face belongs to | SVM classifies embedding → "Afthab" |
| **Hand Tracking** | Detecting hand pose and landmarks | MediaPipe returns 21 joint positions |
| **Gesture** | Meaningful hand movement | Pinch (thumb + index) = mouse click |
| **Confidence Score** | Probability that classification is correct | 0.95 = 95% confident it's "Afthab" |
| **Confidence Threshold** | Minimum required confidence | 0.60 = only accept predictions > 60% |

### Machine Learning

| Term | Definition | Location |
|------|-----------|----------|
| **Embedding** | Vector encoding semantic information | SFace outputs 128D embeddings |
| **Feature Extraction** | Converting raw data to meaningful features | SFace does this for face images |
| **Training Data** | Examples used to train model | 150 face samples per user |
| **Inference** | Using trained model to make predictions | SVM classifies embeddings at runtime |
| **Hyperparameters** | Configuration values for ML algorithm | C=5, gamma=0.001 in SVM |
| **Overfitting** | Model memorizes training data vs generalizing | With only 3 users, unlikely |
| **Accuracy** | Fraction of correct predictions | 95% = correct on 95% of test faces |
| **Train/Test Split** | Partition data into training (80%) and testing (20%) | Evaluate model on unseen data |

### Audio Processing

| Term | Definition | Location |
|------|-----------|----------|
| **Speech Recognition** | Converting audio to text | Google Cloud Speech-to-Text |
| **Wake Word** | Trigger phrase to activate mic | "Hey Mirror" (case-insensitive) |
| **Text-to-Speech (TTS)** | Converting text to audio | Google gTTS, played via Pygame |
| **Energy Threshold** | Audio amplitude required to detect speech | Dynamically adjusted per session |
| **Microphone Calibration** | Adjusting recognizer to ambient noise | Done every 60 seconds |
| **Phrase Time Limit** | Maximum duration for single utterance | 8 seconds per command |

### System Architecture

| Term | Definition | Example |
|------|-----------|---------|
| **Thread** | Concurrent execution context | unified_vision_thread runs independently |
| **Daemon Thread** | Background thread that doesn't block shutdown | weather_thread is daemon=True |
| **Queue** | Thread-safe data structure for passing messages | speech_queue holds text to speak |
| **Event** | Synchronization primitive for signaling | approval_event triggers enrollment |
| **Global Variable** | State shared across threads | recognized_user (current user) |
| **Callback** | Function invoked on external event | audio_callback on speech detected |

### Network & Cloud

| Term | Definition | Example |
|------|-----------|---------|
| **WebSocket** | Persistent bidirectional connection | Frontend ↔ Backend on port 8765 |
| **JSON** | Text format for structured data | {"type": "todo_add", "task": "Buy milk"} |
| **MQTT** | Lightweight pub/sub protocol | Publish alerts to HiveMQ broker |
| **Topic** | Named channel in pub/sub | intellimirror_77x9/alerts |
| **Payload** | Data sent in message | Photo + timestamp in intruder alert |
| **OAuth2** | Authentication standard | Google Calendar uses OAuth2 flow |
| **Firestore** | NoSQL database from Firebase | Store todos, layouts, security requests |
| **Collection** | Top-level table in Firestore | "todos", "layouts" |
| **Document** | Row in collection | Document named after username |

### Security

| Term | Definition | Location |
|------|-----------|----------|
| **Intruder** | Unknown face detected | triggers capture + admin approval (SafeAI) |
| **Security Mode** | ENFORCED (strict) vs NORMAL (permissive) | Controlled via MQTT |
| **Admin Approval** | Owner approves new user | Web dashboard checks security_requests |
| **Enrollment** | Process of adding new user to system | Capture 150 samples + retrain model |
| **Spoofing** | Fooling system with photo/mask | Why we require admin approval |
| **Credentials** | API keys and auth files | firebase_credentials.json, .env |

### Intent Detection

| Term | Definition | Handler |
|------|-----------|---------|
| **Intent** | User's goal or desired action | Extracted by Gemini from speech |
| **Spotify Intent** | Music-related command | Play, pause, skip songs |
| **Calendar Intent** | Calendar-related command | Read, add, delete events |
| **Todo Intent** | Task-related command | Add, delete, list items |
| **Vision Intent** | "What am I holding?" query | Image analysis intent |
| **Chat Intent** | Open-ended conversation | Fallback to Gemini chat |

---

## Component Terminology

### Core Components

| Component | Purpose | File |
|-----------|---------|------|
| **Main Engine** | Orchestrates all subsystems | intelli.py / intelli-safeai.py |
| **Vision Thread** | Face + hand processing | unified_vision_thread() |
| **Audio Thread** | Speech recognition | audio_callback() + start_listening() |
| **AI Orchestrator** | Routes intents to handlers | ask_gemini() |
| **UI Interface** | Frontend rendering | website/index.html |

### External Services

| Service | Purpose | Integration |
|---------|---------|------------|
| **Google Gemini** | AI text/image understanding | client.models.generate_content() |
| **Google Calendar** | Event management | googleapiclient.discovery |
| **Spotify** | Music playback control | spotipy.Spotify() |
| **Firebase Firestore** | Cloud database | firebase_admin.firestore |
| **HiveMQ MQTT** | Real-time pub/sub broker | paho.mqtt.client |
| **Open-Meteo** | Weather API | urllib (REST API) |

### ML Models

| Model | Purpose | Format | Source |
|-------|---------|--------|--------|
| **YuNet** | Face detection | ONNX | OpenCV contrib |
| **SFace** | Face feature extraction | ONNX | OpenCV contrib |
| **Hand Landmarker** | Hand pose estimation | ONNX task | MediaPipe |
| **SVM Classifier** | Face identity classification | Joblib | scikit-learn |

---

## File & Path Terminology

| Term | Meaning | Example |
|------|---------|---------|
| **Model Path** | Directory for ML models | `Magic_Mirror_Package/face_profiles/` |
| **Token Path** | OAuth token storage | `calendar_tokens/{username}_token.json` |
| **Credential File** | Service account keys | `firebase_credentials.json` |
| **Entry Point** | Main executable | `intelli.py` line 762 |

---

## Configuration Terminology

| Term | Definition | Value | Usage |
|------|-----------|-------|-------|
| **FRAME_R** | Crop margin for hand tracking | 100 pixels | Avoid edge artifacts |
| **SMOOTHING_FREE** | Hand smoothing when idle | 7 | Lower = more jittery |
| **SMOOTHING_DRAG** | Hand smoothing while dragging | 14 | Higher = more stable clicks |
| **FACE_TIMEOUT** | Auto-logout delay | 30-60 seconds | Drop user after no face |
| **CONFIDENCE_THRESHOLD** | Min probability for face match | 0.60 (60%) | > 0.60 = recognized |
| **WAKE_WORD** | Speech trigger phrase | "hey mirror" | Case-insensitive |
| **TIMEOUT_SECONDS** | Listening mode timeout | 15 seconds | Auto-sleep after inactivity |
| **CALIBRATION_INTERVAL** | Mic recalibration frequency | 60 seconds | Relearn ambient noise |

---

## Data Structure Terminology

### User Models

```python
User = {
    "username": str,           # Unique identifier
    "face_id": int,           # Internal ID (0, 1, 2, ...)
    "enrollment_date": str,   # ISO format date
    "sample_count": int       # Number of training samples
}
```

### Embedding Model

```python
Embedding = np.array([
    f0: float,                # Feature dimension 0
    f1: float,                # Feature dimension 1
    ...
    f127: float               # Feature dimension 127
])  # Shape: (128,)
```

### Intent Models

```python
Calendar_Intent = {
    "intent": "read" | "add" | "delete",
    "summary": str,                          # Event name
    "date": "YYYY-MM-DD",                   # Event date
    "time": "HH:MM:00"                      # Event time
}

Todo_Intent = {
    "intent": "read" | "add" | "delete" | "clear",
    "task": str                             # Task description
}
```

### Layout Model

```python
Layout = {
    "widget_id": {                          # e.g., "spotify"
        "x": int,                           # X coordinate (pixels)
        "y": int                            # Y coordinate (pixels)
    },
    ...  # Multiple widgets
}
```

---

## API Terminology

### WebSocket Messages

```python
# Message types
"todo_add"      # Add new todo item
"todo_delete"   # Remove todo item
"layout_save"   # Save widget position
```

### MQTT Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `intellimirror_77x9/alerts` | Publish | Stats + intruder alerts |
| `intellimirror_77x9/security_mode` | Subscribe | ENFORCED / NORMAL |

### Firebase Collections

| Collection | Documents | Schema |
|-----------|-----------|--------|
| `todos` | {username} | {tasks: [...]} |
| `layouts` | {username} | {widget: {x, y}} |
| `security_requests` | Auto-generated | {name, status, image, timestamp} |
| `templates` | default | {widget: {x, y}} |

---

## Acronyms & Abbreviations

| Acronym | Expansion | Context |
|---------|-----------|---------|
| **TTS** | Text-to-Speech | Audio output via gTTS |
| **ONNX** | Open Neural Network Exchange | ML model format |
| **SVM** | Support Vector Machine | Face classifier |
| **RBF** | Radial Basis Function | SVM kernel type |
| **QoS** | Quality of Service | MQTT message guarantee |
| **RFC** | Request For Comments | Internet standards |
| **OAuth2** | Open Authorization 2.0 | Google authentication |
| **API** | Application Programming Interface | External service calls |
| **PWA** | Progressive Web App | Web-based dashboard |
| **GPIO** | General Purpose I/O | Hardware pins (not used in mirror) |
| **GIL** | Global Interpreter Lock | Python threading limitation |
| **ADR** | Architectural Decision Record | Design documentation |
| **UX** | User Experience | Interface design |
| **MQTT** | Message Queuing Telemetry Transport | Pub/sub protocol |

---

## State Terminology

### Recognition States

| State | Meaning | Duration |
|-------|---------|----------|
| **Recognized** | Known user face detected | Until FACE_TIMEOUT |
| **Unknown** | Face detected but not recognized | Until 3+ frames of non-face |
| **Unrecognized** | No face in view | Triggers logout after FACE_TIMEOUT |

### Audio States

| State | Meaning | Next State |
|-------|---------|-----------|
| **Idle** | Listening for wake word | → Listening |
| **Listening** | Waiting for command after wake word | → Processing or → Idle (timeout) |
| **Processing** | Analyzing user intent | → Speaking |
| **Speaking** | Playing TTS response | → Idle |

### Security States (SafeAI)

| State | Meaning | Action |
|-------|---------|--------|
| **NORMAL** | Accept face recognition as-is | No admin approval needed |
| **ENFORCED** | Require admin approval for unknowns | Send intruder alerts |
| **Pending Approval** | Waiting for admin decision | Queue held until timeout |

---

## Related Documentation

- **ARCHITECTURE.md** - System design overview
- **CODE.md** - Function and class reference
- **DATAFLOW.md** - Data models and transformations
