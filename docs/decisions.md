# Intelli-Mirror Architectural Decisions

**Last Updated:** July 2026

## Table of Contents

1. [ADR-001: Technology Stack](#adr-001-technology-stack)
2. [ADR-002: Face Recognition Architecture](#adr-002-face-recognition-architecture)
3. [ADR-003: Multi-Threading vs Event Loop](#adr-003-multi-threading-vs-event-loop)
4. [ADR-004: Single vs Multiple Versions](#adr-004-single-vs-multiple-versions)
5. [ADR-005: Firebase for State Management](#adr-005-firebase-for-state-management)
6. [ADR-006: MQTT for Security Alerts](#adr-006-mqtt-for-security-alerts)
7. [ADR-007: Daemon Threads for Graceful Shutdown](#adr-007-daemon-threads-for-graceful-shutdown)
8. [ADR-008: Admin Approval Flow for Unknown Users](#adr-008-admin-approval-flow-for-unknown-users)
9. [ADR-009: Exponential Smoothing for Hand Tracking](#adr-009-exponential-smoothing-for-hand-tracking)
10. [Trade-Offs & Future Considerations](#trade-offs--future-considerations)

---

## ADR-001: Technology Stack

### Context

The project needed to integrate multiple modalities:
- Computer vision (face recognition, hand tracking)
- Speech processing (recognition, synthesis)
- Cloud services (calendar, music, AI)
- Real-time UI updates

### Decision

**Chosen:** Python-based backend with:
- OpenCV for vision (YuNet + SFace models)
- MediaPipe for hand tracking
- Google Gemini for AI orchestration
- Firebase for cloud state
- WebSocket for frontend communication

**Alternatives Considered:**
1. **Full JavaScript/Node.js:** Would require porting all ML models, adds complexity for native OS control (PyAutoGUI equivalent)
2. **C++/Rust:** Faster performance but higher development friction for rapid prototyping
3. **Mixed Python + C++:** Could optimize hot paths but adds build complexity

### Rationale

- **Rapid Development:** Python + well-maintained libraries (scikit-learn, PIL, etc.)
- **ML Ecosystem:** Mature support for face recognition models (ONNX format)
- **Multimodal Integration:** Google API ecosystem well-supported
- **Deployment:** Single process, minimal dependencies for Pi 5 target

### Trade-Offs

- **Performance:** Python slower than compiled languages, but sufficient for 30 FPS vision processing
- **Memory:** Larger runtime than Go/Rust, but acceptable for edge device

### Status

✅ **Approved** - Production in use

---

## ADR-002: Face Recognition Architecture

### Context

The system needed to:
1. Detect faces in real-time (30 FPS)
2. Recognize known users with high accuracy
3. Support dynamic enrollment of new users
4. Flag intruders for security

### Decision

**Pipeline:** YuNet (detection) → SFace (alignment + embedding) → SVM (classification)

**Why this stack?**

| Component | Choice | Alternative | Why Not |
|-----------|--------|-------------|---------|
| Detection | YuNet ONNX | MTCNN, Dlib | YuNet is faster, hardware-optimized |
| Alignment | SFace | Manual crop | SFace improves ML accuracy |
| Embedding | SFace 128D | ResNet, ArcFace | Good accuracy/speed trade-off |
| Classification | SVM (RBF) | k-NN, Cosine similarity | SVM robust for small dataset (< 20 users) |

**Hyperparameters:**
```python
SVC(kernel='rbf', C=5, gamma=0.001, class_weight='balanced', probability=True)
```

- `rbf` kernel: Non-linear decision boundaries
- `C=5`: Moderate regularization (tested empirically)
- `gamma=0.001`: RBF kernel coefficient
- `probability=True`: Enable confidence scores
- `class_weight='balanced'`: Handle imbalanced enrollment data

**Confidence Threshold:** 0.60 (60%)
- Rationale: High recall for recognized users, low false positives for intruders

### Rationale

1. **ONNX Models:** Lightweight, no GPU required, runs on Pi 5
2. **SVM over Neural Networks:** 
   - Fewer parameters to tune
   - Better generalization on small datasets
   - Deterministic behavior for security
3. **128D Embeddings:** 
   - Sufficient dimensionality for separation
   - Memory efficient for storage

### Trade-Offs

- **Accuracy:** Worse than modern face ID (Face++, Azure Face). Good enough for smart mirror (home environment)
- **Speed:** Entire pipeline ~30ms per frame (YuNet ~5ms, SFace ~15ms, SVM ~1ms)
- **Scalability:** SVM training O(n²) in data size; OK for < 50 users, problematic for > 1000

### Status

✅ **Approved** - Deployed, works well for 5-10 household members

**Future:** Consider SwiftFace or VGGFace2 fine-tuning for better accuracy if needed

---

## ADR-003: Multi-Threading vs Event Loop

### Context

The system processes multiple concurrent streams:
- Webcam (vision) at 30 FPS
- Microphone (audio) continuously
- Weather polling every 30 minutes
- Spotify status every 3 seconds
- Firebase listeners real-time

### Decision

**Chosen:** Multi-threaded architecture with daemon threads

**Design:**
```
Main thread
├─ unified_vision_thread (daemon)
├─ audio_callback via listener thread (daemon)
├─ weather_thread (daemon)
├─ spotify_sync_thread (daemon)
├─ state_sync_thread (daemon)
├─ approval_listener (daemon, SafeAI only)
├─ WebSocket server thread (daemon)
└─ Main event loop (non-daemon)
```

**Synchronization Primitives:**
- `queue.Queue()` - Thread-safe speech queue
- `threading.Event()` - Approval event signaling
- Global variables with implicit synchronization (Python GIL)

### Alternatives Considered

1. **Event Loop (asyncio):**
   - ✅ Simpler concurrency model
   - ❌ Requires async-compatible libraries (SpeechRecognition not async-friendly)
   - ❌ Complex integration with blocking I/O (microphone, camera)

2. **Process Pool:**
   - ✅ True parallelism (no GIL)
   - ❌ Inter-process communication overhead
   - ❌ Shared state (latest_frame) harder to manage

### Rationale

- **Blocking I/O:** Camera and microphone are blocking; threads handle naturally
- **Python GIL:** Not an issue; threads mostly wait on I/O (not CPU-bound)
- **Simplicity:** Easier to reason about than async/await chains
- **Existing Code:** SpeechRecognition library provides listen_in_background() which manages its own thread

### Trade-Offs

- **Complexity:** More complex than single-threaded for some scenarios
- **Debugging:** Thread timing issues harder to reproduce
- **Scalability:** Limited by number of OS threads (~1000 on Linux), but we use ~10

### Status

✅ **Approved** - Works well in practice

**Alternative Explored:** Message broker (Celery), too heavyweight for single device

---

## ADR-004: Single vs Multiple Versions

### Context

After initial development, requirements expanded to include admin approval for unknown users (security feature).

### Decision

**Chosen:** Two versions co-exist in repo

1. **intelli.py** - Original, simple version (no approval flow)
2. **intelli-safeai.py** - Enhanced with admin approval (security-focused)

**Rationale for Duplication:**

| Aspect | intelli.py | intelli-safeai.py | Why duplicate? |
|--------|-----------|-----------------|-----------------|
| Setup | Simple | Requires Firebase admin | Different deployment profiles |
| Security | Open to anyone | Admin approval | User preference |
| Enrollment | Manual (retrain.py) | Built-in + auto-trigger | Different UX |
| Size | ~800 lines | ~1050 lines | Minimal overlap |

### Alternatives Considered

1. **Feature Flags (single file):**
   - ❌ Nested conditionals make code hard to read
   - ❌ Both code paths must be maintained
   - ✅ Easier to test variations

2. **Modular Design (separate modules):**
   - ✅ Would be cleaner
   - ❌ Requires refactoring existing code
   - ❌ Complex imports and dependencies

3. **Merge into Single File:**
   - ❌ intelli-safeai.py already merged; reverting wastes time

### Rationale

- **User Choice:** Simple deployment for personal use vs. security-conscious families
- **Minimal Maintenance:** < 30% code difference, easy to sync bug fixes
- **Pragmatism:** Sometimes duplication is simpler than abstraction (WET vs DRY trade-off)

### Status

✅ **Approved** - Both versions maintained in parallel

**Documentation:** `.cursorrules.md` specifies sync requirements

---

## ADR-005: Firebase for State Management

### Context

The system needs to persist:
- User todo lists
- Widget positions (layout)
- Security approval requests

### Decision

**Chosen:** Firebase Firestore (hosted NoSQL database)

**Why Firestore?**

| Criteria | Firebase | Alternatives | Why Firebase |
|----------|----------|--------------|-------------|
| Real-time sync | ✅ Yes | ❌ REST APIs | Automatic push to connected clients |
| Offline support | ✅ Yes | ❌ (Lambda dependent) | Works during network outages |
| Free tier | ✅ 50k reads/day | ❌ AWS/GCP more expensive | Sufficient for prototype |
| Integration | ✅ Admin SDK exists | ❌ More setup | One-click authentication |

**Collections:**
```
todos/
├── {username}/ → {tasks: [...]}

layouts/
├── {username}/ → {widget_id: {x, y}}

security_requests/ (SafeAI only)
├── {auto-id}/ → {name, status, image, timestamp}

templates/
├── default/ → Default layout for new users
```

### Alternatives Considered

1. **Local JSON Files:**
   - ✅ Works offline
   - ❌ No real-time sync across devices
   - ❌ No admin dashboard

2. **PostgreSQL + Sync Service:**
   - ✅ Full control
   - ❌ Requires server, more ops burden
   - ❌ Overkill for smart mirror

3. **MongoDB + Realm:**
   - ✅ Similar to Firebase
   - ❌ More setup, less managed

### Rationale

- **Serverless:** No backend to manage
- **Multi-Device:** Security dashboard (separate PWA) can read stats in real-time
- **Cost:** Free tier sufficient for home use
- **Simplicity:** Firebase Admin SDK handles auth, database, real-time listeners

### Trade-Offs

- **Vendor Lock-in:** Difficult to migrate off Firebase later
- **Privacy:** Data on Google servers (use encryption if needed)
- **Connectivity:** Requires internet; local fallback uses stale data

### Status

✅ **Approved** - Proven in production

**Future:** Consider Firebase offline persistence for continued operation without internet

---

## ADR-006: MQTT for Security Alerts

### Context

The security dashboard (separate PWA) needs to receive:
- Intruder alerts with photos
- Daily login statistics
- Security mode changes

### Decision

**Chosen:** HiveMQ MQTT broker (public cloud)

**Architecture:**
```
intelli.py
    ↓
mqtt_client.publish(TOPIC_ALERTS, json.dumps({...}))
    ↓
HiveMQ Broker (broker.hivemq.com:1883)
    ↓
security_pwa/index.html
    (subscribes to TOPIC_ALERTS)
```

**Why MQTT?**

| Criteria | MQTT | Alternatives | Why MQTT |
|----------|------|--------------|---------|
| Real-time | ✅ Pub/Sub | ❌ REST polling | Instant push updates |
| Lightweight | ✅ Binary protocol | ❌ JSON over HTTP | Low bandwidth |
| Mobile-friendly | ✅ Native JS support | ❌ WebSocket setup required | Web browser can subscribe |
| Persistence | ⚠️ Optional (QoS) | ✅ Full history | Sufficient for alerts |

**Topics:**
- `intellimirror_77x9/security_mode` → Subscribe (receive mode changes)
- `intellimirror_77x9/alerts` → Publish (send intruder/stats)

### Alternatives Considered

1. **Firebase Realtime Database:**
   - ✅ Similar functionality
   - ❌ Would need two Firebase services (overkill)
   - ❌ Less standardized than MQTT

2. **WebSocket Direct:**
   - ✅ Direct connection
   - ❌ Requires always-on server
   - ❌ NAT traversal complexity

3. **AWS IoT Core:**
   - ✅ Enterprise-grade
   - ❌ More expensive
   - ❌ Overkill for home project

### Rationale

- **Public Broker:** HiveMQ free tier (no authentication needed for prototype)
- **Standardized:** MQTT widely supported in JavaScript
- **Fire-and-Forget:** Use QoS 0 for alerts (OK if one drops)
- **Simplicity:** Single `paho-mqtt` library handles everything

### Trade-Offs

- **Security:** Public MQTT broker; use VPN for privacy
- **Reliability:** Free HiveMQ tier may have downtime
- **Authentication:** No built-in auth (use API gateway in production)

### Status

✅ **Approved** - Works for prototype, needs auth for production

**Future:** Consider secure MQTT broker or private Kafka cluster

---

## ADR-007: Daemon Threads for Graceful Shutdown

### Context

The system has 10+ background threads. On Ctrl+C:
- Should stop cleanly
- Should not hang waiting for background tasks
- Should minimize resource leaks

### Decision

**Chosen:** Mark all background threads as daemon=True

```python
threading.Thread(target=unified_vision_thread, daemon=True).start()
threading.Thread(target=weather_thread, daemon=True).start()
# ... etc for all background threads
```

**Why Daemon Threads?**

- When main thread exits, Python terminates all daemon threads immediately
- No need for explicit thread shutdown logic
- Clean exit on KeyboardInterrupt

### Alternatives Considered

1. **Manual Thread Stopping:**
   ```python
   stop_event = threading.Event()
   def worker():
       while not stop_event.is_set():
           # do work
   
   # On shutdown:
   stop_event.set()
   for thread in threads:
       thread.join(timeout=2)
   ```
   - ✅ Explicit control
   - ❌ Boilerplate code
   - ❌ Need timeout for threads that don't check flag

2. **No Daemon Threads (all foreground):**
   - ❌ Ctrl+C hangs waiting for all threads
   - ❌ Impossible to exit promptly

### Rationale

- **Simplicity:** No shutdown logic needed
- **Safety:** Automatic cleanup on process termination
- **Acceptable:** None of our threads hold exclusive resources
- **Trade-Off:** Potential data loss if thread writing to file when killed, but acceptable for logs/cache

### Status

✅ **Approved** - Proven reliable

**Note:** Main event loop is NOT daemon, so KeyboardInterrupt handler (line 797 in intelli.py) runs before shutdown

---

## ADR-008: Admin Approval Flow for Unknown Users

### Context

In **intelli-safeai.py**, unknown faces are security concern:
- Should not auto-enroll (spoof risk)
- Owner should approve new users
- Visual confirmation needed

### Decision

**Chosen:** Admin Approval Flow

```
Unknown face detected
    ↓
Capture photo → Encode as JPEG
    ↓
Upload to Firebase (security_requests collection)
    ↓
If security_enforced: Publish to MQTT
    ↓
Admin reviews in web dashboard
    ↓
Admin clicks "Approve"
    ↓
approval_listener detects status='approved'
    ↓
Main loop: enroll_user(name)
    ↓
Pi 5 camera: Capture 150 samples
    ↓
Auto-train: retrain.py
    ↓
reload_ai_model flag: Live model reload
```

### Rationale

- **Security:** Prevents spoofing attacks (photos, masks, etc.)
- **Control:** Owner decides who gets access
- **Auditing:** All approval requests logged in Firebase
- **UX:** Minimal friction once approved (automatic training + reload)

### Alternatives Considered

1. **Automatic Enrollment on First Detection:**
   - ❌ Security hole; any stranger could enroll themselves

2. **No Support for New Users:**
   - ✅ Secure
   - ❌ Bad UX; requires manual file operations

3. **Enrollment via Web Dashboard Only:**
   - ✅ Secure
   - ❌ Can't upload faces if no dashboard

### Status

✅ **Approved** - Critical for home security scenario

**Notes:**
- Only in intelli-safeai.py (not intelli.py)
- Requires Firebase admin credentials
- Requires security dashboard access

---

## ADR-009: Exponential Smoothing for Hand Tracking

### Context

Hand tracking can be jittery due to:
- Lighting variations
- Tracking ambiguity
- MediaPipe frame drops

### Decision

**Chosen:** Exponential smoothing with two rates

```python
SMOOTHING_FREE = 7      # Idle hand
SMOOTHING_DRAG = 14     # While dragging (heavier smoothing)

active_smoothing = SMOOTHING_DRAG if mouse_held else SMOOTHING_FREE
curr_x = prev_x + (x_mapped - prev_x) / active_smoothing
curr_y = prev_y + (y_mapped - prev_y) / active_smoothing
```

**Why Exponential Smoothing?**

| Aspect | Formula |
|--------|---------|
| Mathematical | `x_t = x_{t-1} + (x_new - x_{t-1}) / α` |
| Intuition | Weight 1-second history heavier than jitter |
| Simplicity | O(1) time, O(1) memory |

### Rationale

- **Jitter Reduction:** Smoothing factor of 7 means each new sample contributes 1/7 of distance change
- **Responsive:** Still tracks hand movements in ~200ms (30 frames * 7 / 30 FPS)
- **Adaptive:** Use SMOOTHING_DRAG=14 while dragging to reduce accidental clicks

### Trade-Offs

- **Latency:** User perception of ~200ms lag (noticeable but acceptable)
- **Tuning:** SMOOTHING_FREE=7 chosen empirically; may vary by hardware

### Status

✅ **Approved** - Works well in practice

**Alternative:** Kalman filter (overkill for this application)

---

## Trade-Offs & Future Considerations

### Performance vs Maintainability

**Current:** Prioritize maintainability
- 30 FPS vision adequate for gesture control
- ML inference every 10 frames (3 FPS face recognition)
- Not optimized for maximum throughput

**Future Optimization:**
- ONNX quantization (16-bit) for 2x speedup
- Batch processing for multiple faces
- GPU acceleration on edge device (e.g., Jetson)

### Security vs Usability

**Current:** Balance
- Face recognition for usability (no PIN)
- Admin approval for security (prevents spoofing)
- Public MQTT for simplicity (compromised for security)

**Production Hardening:**
- TLS certificates for MQTT
- End-to-end encryption for photos
- Rate limiting on API endpoints

### Local vs Cloud

**Current:** Hybrid
- ML inference local (Pi 5)
- State management cloud (Firebase)
- Intruder alerts cloud (MQTT)

**Trade-Off Rationale:**
- ✅ ML local: Fast, works offline, private
- ✅ State cloud: Multi-device sync, backup
- ⚠️ Alerts cloud: Real-time but requires internet

### Scalability

**Current Design:** Single mirror, 1 location

**For Multiple Mirrors:**
- Add location ID to MQTT topics
- Partition Firebase collections by location
- Shared ML model (central training) or local (distributed)

---

## Summary of Approved Decisions

| ADR | Title | Status | Owner | Version |
|-----|-------|--------|-------|---------|
| 001 | Technology Stack | ✅ Approved | Afthab | 1.0+ |
| 002 | Face Recognition | ✅ Approved | Afthab | 1.0+ |
| 003 | Multi-Threading | ✅ Approved | Afthab | 1.0+ |
| 004 | Dual Versions | ✅ Approved | Afthab | 2.0+ |
| 005 | Firebase Storage | ✅ Approved | Afthab | 1.0+ |
| 006 | MQTT Alerts | ✅ Approved | Afthab | 2.0+ |
| 007 | Daemon Threads | ✅ Approved | Afthab | 1.0+ |
| 008 | Admin Approval | ✅ Approved | Afthab | 2.0+ |
| 009 | Hand Smoothing | ✅ Approved | Afthab | 1.0+ |

---

## Related Documentation

- **ARCHITECTURE.md** - System design and components
- **RISK.md** - Known vulnerabilities and mitigations
- **CODE.md** - Implementation details
