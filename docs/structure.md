# Intelli-Mirror Project Structure

**Last Updated:** July 2026

## Table of Contents

1. [Directory Layout](#directory-layout)
2. [Root-Level Files](#root-level-files)
3. [Core Modules](#core-modules)
4. [Configuration](#configuration)
5. [Data Directories](#data-directories)
6. [Dependencies & Versioning](#dependencies--versioning)
7. [Module Relationships](#module-relationships)

---

## Directory Layout

```
intelli-mirror/
│
├── ROOT EXECUTABLES
│   ├── intelli.py                     # Main engine (original)
│   ├── intelli-safeai.py              # Main engine (with admin approval)
│   ├── retrain.py                     # Face model retraining script
│   ├── generate_token.py              # Google Calendar OAuth setup
│   │
│   ├── requirements.txt               # Python dependencies
│   ├── .env                           # Environment variables (SECRETS)
│   ├── .gitignore                     # Git ignore rules
│   ├── README.md                      # Project overview
│   │
│   ├── firebase_credentials.json      # Firebase service account (SECRETS)
│   ├── credentials.json               # Google OAuth client config (SECRETS)
│   ├── login_stats.json               # Local login tracking JSON
│   ├── hand_landmarker.task           # MediaPipe hand model (auto-downloaded)
│   │
│   ├── calendar_tokens/               # Per-user Google Calendar OAuth tokens
│   │   ├── Afthab_token.json
│   │   ├── Pavan_token.json
│   │   └── ...
│   │
│   ├── docs/                          # Documentation
│   │   ├── ARCHITECTURE.md            # System design & components
│   │   ├── STRUCTURE.md               # This file
│   │   ├── CODE.md                    # Function/class reference
│   │   ├── DATAFLOW.md                # Data models & APIs
│   │   ├── DECISIONS.md               # Architectural decision records
│   │   ├── GLOSSARY.md                # Domain terminology
│   │   ├── RISK.md                    # Security & performance risks
│   │   └── ...
│   │
│   ├── website/                       # Local PWA frontend (displayed on mirror)
│   │   ├── index.html                 # Main UI markup
│   │   ├── js/
│   │   │   └── main.js                # UI interactivity & WebSocket
│   │   └── css/
│   │       └── style.css              # UI styling
│   │
│   ├── security_pwa/                  # Remote security dashboard
│   │   ├── index.html                 # Admin dashboard UI
│   │   └── (styles & logic embedded)
│   │
│   ├── Magic_Mirror_Package/          # ML models & face enrollment
│   │   ├── yunet.onnx                 # YuNet face detection model
│   │   ├── sface.onnx                 # SFace face recognition model
│   │   ├── face_recognition_system.py # Legacy face enroll module
│   │   └── face_profiles/
│   │       ├── hybrid_ai_model.pkl    # Trained SVM classifier
│   │       ├── profiles.pkl           # User ID mapping
│   │       ├── face_data.pkl          # Raw face embeddings
│   │       └── .ipynb_checkpoints/    # Jupyter notebook versions
│   │
│   ├── lib/                           # Utility libraries
│   │   └── redact.mjs                 # Data redaction utilities
│   │
│   ├── old files/                     # Legacy/archived scripts
│   │   ├── wake_to_gemini.py
│   │   ├── wake_to_spotify.py
│   │   ├── wake_to_calendar.py
│   │   ├── hand_tracker.py
│   │   ├── wake_module.py
│   │   └── ...
│   │
│   ├── safeai-intelli/                # Alternative branch (snapshot)
│   │   ├── intelli-safeai.py          # SafeAI version (backup)
│   │   ├── intelli-adu-ready.py       # ADU-optimized variant
│   │   ├── generate_token.py
│   │   ├── retrain.py
│   │   ├── requirements.txt
│   │   ├── website/                   # Frontend copy
│   │   ├── security_pwa/              # Dashboard copy
│   │   ├── Magic_Mirror_Package/      # ML package copy
│   │   └── login_stats.json
│   │
│   └── .claude/                       # Claude IDE settings
│       └── settings.json              # Cursor configuration
```

---

## Root-Level Files

### Executables

| File | Purpose | Entry Point | Status |
|------|---------|-------------|--------|
| `intelli.py` | Main smart mirror engine | `if __name__ == "__main__"` (line 762) | Active |
| `intelli-safeai.py` | Enhanced version with admin approval | `if __name__ == "__main__"` (line 989) | Active |
| `retrain.py` | ML model retraining bridge | Direct execution | On-demand |
| `generate_token.py` | Google Calendar OAuth setup | Direct execution | One-time setup |

### Configuration

| File | Purpose | Format | Content |
|------|---------|--------|---------|
| `.env` | Environment variables | KEY=VALUE | GEMINI_API_KEY, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI |
| `requirements.txt` | Python dependencies | pip format | 19 packages listed (see below) |
| `.gitignore` | Git exclusions | glob patterns | Excludes .env, credentials, token files |

### Secrets (NOT IN VERSION CONTROL)

| File | Purpose | Source |
|------|---------|--------|
| `firebase_credentials.json` | Firebase service account | Generated via Google Cloud Console |
| `credentials.json` | Google OAuth client config | Generated via Google Cloud Console |
| `.env` | API keys | User-provided |

### Data Files

| File | Purpose | Format | Usage |
|------|---------|--------|-------|
| `login_stats.json` | Daily login tracking | JSON dict | Read/write by `log_user_login()` |
| `hand_landmarker.task` | MediaPipe hand model | ONNX task | Downloaded on first run from Google Storage |

### Tokens Directory

**`calendar_tokens/`** - Per-user Google Calendar OAuth tokens

- Named: `{username}_token.json` (e.g., `Afthab_token.json`)
- Created by: `generate_token.py`
- Used by: `get_calendar_service()` to access user's calendar events

---

## Core Modules

### 1. **intelli.py (Original Version)**

**Lines:** 1-799  
**Size:** ~20KB  
**Entry:** Line 762

**Key Functions:**
- `unified_vision_thread()` (218-369) - Face & hand tracking
- `weather_thread()` (372-387) - Weather polling
- `ask_gemini()` (635-712) - AI orchestration
- `audio_callback()` (714-741) - Speech recognition
- `start_listening()` (743-760) - Microphone setup
- Main event loop (773-799) - Speech queue + calibration

**Global State:**
- `recognized_user` - Current logged-in user
- `latest_frame` - Current webcam frame
- `security_enforced` - Security mode (MQTT-controlled)
- `speech_queue` - Inter-thread audio queue
- Various config constants (FACE_TIMEOUT, SMOOTHING_FREE, etc.)

### 2. **intelli-safeai.py (Enhanced Version)**

**Lines:** 1-1050  
**Size:** ~30KB  
**Entry:** Line 989

**Additional Features Over intelli.py:**
- Admin approval flow for unknown faces
- Enrollment system for new users
- Dynamic model reloading after training
- Persisted conversation memory (mirror_chat)
- Pomodoro/focus mode support
- Stricter audio callback handling

**Key Additions:**
- `approval_listener()` (259-274) - Firebase admin stream
- `enroll_user()` (277-350) - Full enrollment pipeline
- Admin approval event handling (1003-1010)
- Conversation memory cleanup (1024-1038)

### 3. **retrain.py**

**Lines:** 1-51  
**Size:** ~1.5KB

**Purpose:** Retrains the face recognition SVM model

**Workflow:**
1. Load raw face captures from `face_data.pkl`
2. Initialize SFace model
3. Extract 128D embeddings for each face
4. Train SVM with specific hyperparameters:
   - `kernel='rbf'`
   - `class_weight='balanced'`
   - `probability=True`
   - `C=5`
   - `gamma=0.001`
5. Serialize to `hybrid_ai_model.pkl`

**Called By:** `enroll_user()` in intelli-safeai.py (line 348)

### 4. **generate_token.py**

**Lines:** 1-35  
**Size:** ~1KB

**Purpose:** One-time setup for Google Calendar OAuth

**Workflow:**
1. Prompt user for name (must match face ID)
2. Verify `credentials.json` exists
3. Launch browser OAuth flow
4. Save token to `calendar_tokens/{name}_token.json`

**Requires:** Google OAuth client credentials in `credentials.json`

### 5. **Magic_Mirror_Package/face_recognition_system.py**

**Lines:** 1-161  
**Size:** ~5KB

**Purpose:** Legacy face enrollment system (alternative to intelli-safeai.py)

**Key Functions:**
- `enroll_mode()` (73-149) - Capture 150 face samples
- `get_ai_tools()` (66-71) - Load YuNet + SFace models
- `load_profiles()` / `save_profiles()` - Profile persistence
- FaceAPIHandler - Local HTTP server for enrollment

**Note:** Mostly superseded by intelli-safeai.py's built-in enrollment

---

## Configuration

### Environment Variables (.env)

```
GEMINI_API_KEY=<your-api-key>
SPOTIPY_CLIENT_ID=<spotify-id>
SPOTIPY_CLIENT_SECRET=<spotify-secret>
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

### Global Configuration (in source code)

| Variable | File | Value | Purpose |
|----------|------|-------|---------|
| FRAME_R | intelli.py:57 | 100 | Hand tracking margin (pixels) |
| SMOOTHING_FREE | intelli.py:58 | 7 | Exponential averaging (idle) |
| SMOOTHING_DRAG | intelli.py:59 | 14 | Exponential averaging (dragging) |
| FACE_TIMEOUT | intelli.py:65 | 60 | Auto-logout delay (seconds) |
| MQTT_BROKER | intelli.py:74 | broker.hivemq.com | MQTT endpoint |
| TOPIC_MODE | intelli.py:76 | intellimirror_77x9/security_mode | MQTT topic |
| WAKE_WORD | intelli.py:561 | "hey mirror" | Voice trigger |
| TIMEOUT_SECONDS | intelli.py:564 | 15 | Voice listening timeout |
| CALIBRATION_INTERVAL | intelli.py:566 | 60 | Mic recalibration (seconds) |

### Model Paths

| Model | Path | Type | Source |
|-------|------|------|--------|
| YuNet | Magic_Mirror_Package/yunet.onnx | ONNX | User-provided |
| SFace | Magic_Mirror_Package/sface.onnx | ONNX | User-provided |
| Hand Landmarker | hand_landmarker.task | ONNX | Auto-downloaded |
| SVM Classifier | Magic_Mirror_Package/face_profiles/hybrid_ai_model.pkl | Joblib | Generated by retrain.py |

---

## Data Directories

### calendar_tokens/
**Purpose:** Per-user Google Calendar OAuth tokens  
**Created By:** `generate_token.py`  
**Naming:** `{username}_token.json`  
**Example:**
```
calendar_tokens/
├── Afthab_token.json
├── Pavan_token.json
└── Alice_token.json
```

### Magic_Mirror_Package/face_profiles/
**Purpose:** Face recognition models and training data  
**Files:**

| File | Format | Created By | Used By |
|------|--------|-----------|---------|
| hybrid_ai_model.pkl | Joblib (SVM) | retrain.py | unified_vision_thread() |
| profiles.pkl | Pickle (dict) | enroll_user() | unified_vision_thread() |
| face_data.pkl | Pickle (list) | enroll_user() | retrain.py |
| .ipynb_checkpoints/ | Jupyter | (legacy) | (legacy) |

### lib/
**Purpose:** Shared utilities  
**Contents:**
- `redact.mjs` - Data redaction utilities (for security dashboard)

---

## Dependencies & Versioning

### requirements.txt

```
google-genai             # Google Gemini API
SpeechRecognition        # Google Speech-to-Text
gTTS                     # Google Text-to-Speech
pygame                   # Audio playback
spotipy                  # Spotify API
google-api-python-client # Google Calendar API
google-auth-httplib2     # OAuth2 HTTP
google-auth-oauthlib     # OAuth2 flows
opencv-contrib-python   # YuNet + SFace models
numpy                    # Numerical computing
scikit-learn             # SVM classifier
joblib                   # Model serialization
mediapipe                # Hand tracking
PyAutoGUI                # Mouse control
websocket-server         # Frontend communication
paho-mqtt                # MQTT client
firebase-admin           # Firebase integration
pillow                   # Image processing
python-dotenv            # Environment loading
```

**Installation:**
```bash
pip install -r requirements.txt
```

**Note:** Some packages have large dependencies (opencv, mediapipe) and may take several minutes to install.

---

## Module Relationships

### Dependency Graph

```
intelli.py / intelli-safeai.py (MAIN)
│
├─→ Audio System
│   ├─→ SpeechRecognition + microphone
│   ├─→ gTTS + pygame.mixer
│   └─→ ask_gemini() orchestrator
│
├─→ Vision System
│   ├─→ cv2 (YuNet + SFace)
│   ├─→ mediapipe (hand landmarker)
│   ├─→ numpy (arrays)
│   └─→ joblib (load SVM model)
│
├─→ External Services
│   ├─→ google.genai (Gemini API)
│   ├─→ spotipy (Spotify playback)
│   ├─→ googleapiclient (Calendar events)
│   ├─→ firebase_admin (Firestore)
│   ├─→ paho.mqtt (HiveMQ broker)
│   └─→ urllib (Open-Meteo weather)
│
├─→ Web Frontend
│   ├─→ websocket_server (Python)
│   └─→ website/js/main.js (WebSocket client)
│
├─→ ML Training
│   ├─→ retrain.py (SVM training)
│   │   ├─→ cv2 (SFace embeddings)
│   │   ├─→ sklearn.svm (SVM)
│   │   └─→ joblib (save model)
│   │
│   └─→ Magic_Mirror_Package/face_recognition_system.py (legacy enroll)
│
└─→ Setup Tools
    ├─→ generate_token.py (OAuth setup)
    └─→ .env loader (python-dotenv)
```

### Thread Hierarchy

```
Main Thread (intelli.py/__main__)
│
├─ unified_vision_thread (DAEMON)
│  ├─ camera capture
│  ├─ hand tracking
│  └─ face recognition
│
├─ audio_callback (via listener thread, DAEMON)
│  ├─ speech recognition
│  └─ wake word detection
│
├─ weather_thread (DAEMON)
│  └─ Open-Meteo polling
│
├─ spotify_sync_thread (DAEMON)
│  └─ Spotify status updates
│
├─ state_sync_thread (DAEMON)
│  └─ User/layout/todo sync
│
├─ approval_listener (DAEMON, intelli-safeai.py only)
│  └─ Firebase admin stream
│
├─ WebSocket server (DAEMON)
│  └─ Frontend communication
│
└─ Main event loop
   ├─ speech_queue processing
   ├─ approval event handling
   └─ microphone recalibration
```

### Data Flow Between Modules

```
Vision Thread ──→ recognized_user ──→ Firebase (get_todos, get_layout)
                                   ──→ UI (send_to_ui)
                                   ──→ Speech Queue (greeting)
                                   ──→ MQTT (login_stats)

Audio Thread ────→ speech_queue ────→ speak() (TTS)
                                   ──→ ask_gemini()
                                   ──→ Various intent handlers

ask_gemini() ─────→ Spotify API (playback)
              ─────→ Google Calendar (events)
              ─────→ Firebase (todos)
              ─────→ Vision frame (image analysis)

WebSocket ───────→ Firebase (layout save)
              ───→ todos update/delete

Main Loop ───────→ Background thread coordination
              ───→ Microphone recalibration
              ───→ Approval event handling (SafeAI)
```

---

## Configuration Hierarchy

### Load Order

1. **Startup (line 1-40)**
   - Import warnings suppression
   - Environment variable setup (GRPC_VERBOSITY, GLOG_minloglevel)
   - Dependency imports

2. **Initialization (line 390)**
   - Load .env file (python-dotenv)
   - Read GEMINI_API_KEY
   - Initialize Spotify auth
   - Connect Firebase
   - Start MQTT broker connection
   - Launch WebSocket server

3. **Thread Startup (line 369-387, 434, 558, 771)**
   - unified_vision_thread
   - weather_thread
   - spotify_sync_thread
   - state_sync_thread
   - start_listening (speech recognition)

4. **Main Loop (line 773-799)**
   - Process speech queue
   - Calibrate microphone (every 60s)
   - Timeout listening mode (every 15s of silence)

---

## Related Documentation

- **ARCHITECTURE.md** - System design and component interactions
- **CODE.md** - Function signatures and implementation details
- **DATAFLOW.md** - Data models and transformation pipelines
