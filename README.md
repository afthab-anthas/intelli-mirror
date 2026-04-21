# Intelli-Mirror

A comprehensive Smart Mirror Engine featuring SFace Hybrid AI Face Recognition, MediaPipe Hand Gesture Tracking, Voice Command Orchestration, and a synced Security Dashboard.

## File Structure

```text
intelli-mirror/
│
├── intelli.py                   # Moved to root
├── retrain.py                   # Moved to root
├── requirements.txt             # Moved to root
├── .env                         # Moved to root
├── credentials.json             # Moved to root
├── firebase_credentials.json    # Moved to root
├── login_stats.json             # Moved to root
├── hand_landmarker.task         # Moved to root
│
├── calendar_tokens/             # Normal name, no emojis
│   └── ...
├── website/                     # Normal name, no emojis
│   └── ...
├── security_pwa/                # Normal name, no emojis
│   └── ...
└── Magic_Mirror_Package/        # Normal name, no emojis
    └── ...
```

---

### Key Components

- **`intelli.py`**: The Master Engine operating Audio, Voice Routing, WebSockets, Face Recognition, Hand Tracking, and the Security Bouncer.
- **`retrain.py`**: Automatic bridge script to extract 128-dimensional Facial Topologies using SFace and compile the `hybrid_ai_model.pkl` security boundary.
- **`/website/`**: The local frontend PWA interface displayed directly onto the mirror screen.
- **`/security_pwa/`**: Remote cross-platform UI dashboard tracking mirror events via MQTT secure sockets.
- **`Magic_Mirror_Package/`**: Core enrollment and legacy Machine Learning assets.