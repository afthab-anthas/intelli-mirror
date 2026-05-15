import warnings
import urllib3
# suppress annoying ssl warnings from urllib3
warnings.filterwarnings("ignore", category=FutureWarning)
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

import urllib.request
import os
import sys
import subprocess

# --- STEP 1: AUTO-DEPENDENCY CHECK ---
REQUIRED_PACKAGES = [
    'opencv-python', 'opencv-contrib-python', 'mediapipe', 'pyautogui', 
    'firebase-admin', 'google-genai', 'python-dotenv', 'gTTS', 'pygame',
    'spotipy', 'google-auth-oauthlib', 'google-api-python-client', 
    'websocket-server', 'joblib', 'scikit-learn'
]

def check_dependencies():
    print("Checking dependencies...")
    for pkg in REQUIRED_PACKAGES:
        try:
            module_name = pkg.split('-')[0] if '-' in pkg else pkg
            if pkg == 'scikit-learn': module_name = 'sklearn'
            if pkg == 'python-dotenv': module_name = 'dotenv'
            if pkg == 'gTTS': module_name = 'gtts'
            __import__(module_name)
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# Run check automatically on boot
# check_dependencies()

# --- STEP 2: STANDARD IMPORTS ---
# hide the mediapipe/tf lite spam in terminal
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

import time
import threading
import queue
import io
import json
import datetime
import math
from pathlib import Path
import pickle
import base64
from PIL import Image
import webbrowser

import speech_recognition as sr
from google import genai
from dotenv import load_dotenv
from gtts import gTTS
import pygame

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import cv2
import numpy as np
import joblib
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
from websocket_server import WebsocketServer

# global vars
latest_frame = None
latest_temp = "--°C"
pyautogui.FAILSAFE = False 
pyautogui.PAUSE = 0
SCREEN_W, SCREEN_H = pyautogui.size()

# hand tracking config
FRAME_R = 100  # crop margin so you don't have to reach the edge of the camera
SMOOTHING_FREE = 7      
SMOOTHING_DRAG = 14     
PINCH_GRAB_DIST = 0.045  
PINCH_DROP_DIST = 0.085  

recognized_user = None
last_seen_time = 0
FACE_TIMEOUT = 60  # auto logout after 1 min
last_intruder_alert_time = 0

speech_queue = queue.Queue()
is_speaking = False

# New global vars for Admin Approval Flow
pending_approval = False
approved_username = None
approval_event = threading.Event()
reload_ai_model = False # Flag to dynamically reload model after training

# mqtt setup for the pwa panel
import paho.mqtt.client as mqtt

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883 
TOPIC_MODE = "intellimirror_77x9/security_mode"
TOPIC_ALERTS = "intellimirror_77x9/alerts"

security_enforced = False

# load local json for the login chart
login_stats_file = "login_stats.json"
if os.path.exists(login_stats_file):
    with open(login_stats_file, "r") as f:
        login_stats = json.load(f)
else:
    login_stats = {}

def log_user_login(username):
    # track logins for the dashboard graph
    global login_stats
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if today not in login_stats: login_stats[today] = {}
    if username not in login_stats[today]: login_stats[today][username] = 0
    
    login_stats[today][username] += 1
    
    with open(login_stats_file, "w") as f:
        json.dump(login_stats, f)
        
    try:
        mqtt_client.publish(TOPIC_ALERTS, json.dumps({"type": "stats", "data": login_stats}))
    except Exception as e: 
        print(f"mqtt stats error: {e}")

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    print("mqtt connected to hivemq broker")
    client.subscribe(TOPIC_MODE)
    try: 
        mqtt_client.publish(TOPIC_ALERTS, json.dumps({"type": "stats", "data": login_stats}))
    except: pass

def on_mqtt_message(client, userdata, msg):
    global security_enforced
    payload = msg.payload.decode("utf-8")
    if payload == "ENFORCED":
        security_enforced = True
        print("security mode set to ENFORCED")
    elif payload == "NORMAL":
        security_enforced = False
        print("security mode set to NORMAL")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start() 
except Exception as e:
    print(f"couldn't connect to mqtt: {e}")

# websockets (talks to the js frontend)
try:
    ws_server = WebsocketServer(host='127.0.0.1', port=8765)
    
    def new_client(client, server):
        print("frontend ui connected to backend")
        try:
            server.send_message(client, json.dumps({
                "ai_state": "idle", 
                "ai_text": "Ready! Say 'Hey Mirror'", 
                "todos": get_todos(),
                "temp": latest_temp
            }))
        except Exception as e: 
            print(f"dropped ws connection: {e}")

    def on_message(client, server, message):
        try:
            data = json.loads(message)
            if data.get("type") == "todo_add":
                t = get_todos()
                t.append(data["task"])
                save_todos(t)
            elif data.get("type") == "todo_delete":
                t = get_todos()
                if data["task"] in t: t.remove(data["task"])
                save_todos(t)
            elif data.get("type") == "layout_save":
                # save widget pos to firebase
                save_layout_widget(data.get("widget_id"), data.get("x"), data.get("y"))
        except Exception as e: 
            print(f"ws incoming error: {e}")
        
    ws_server.set_fn_new_client(new_client)
    ws_server.set_fn_message_received(on_message)
    print("websocket server running on port 8765")
except Exception as e:
    print(f"failed to start websocket: {e}")
    ws_server = None

def send_to_ui(data_dict):
    if ws_server:
        try: 
            ws_server.send_message_to_all(json.dumps(data_dict))
        except Exception as e: 
            print(f"ws send error: {e}")

threading.Thread(target=lambda: ws_server.run_forever() if ws_server else None, daemon=True).start()

# text to speech function
def speak(text):
    global is_speaking
    is_speaking = True
    send_to_ui({"ai_state": "idle", "ai_text": text})
    try:
        # clean text so it doesn't read out markdown symbols
        clean_text = text.replace('*', '').replace('#', '')
        print(f"Mirror says: {clean_text}")
        
        tts = gTTS(text=clean_text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): 
            time.sleep(0.1)
    except Exception as e:
        print(f"tts error: {e}")
    finally:
        time.sleep(1.2)
        is_speaking = False

# firebase connection for to-dos, layouts, and admin approval
import firebase_admin
from firebase_admin import credentials, firestore

db = None
try:
    cred = credentials.Certificate('firebase_credentials.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("firebase loaded ok")
except Exception as e:
    print(f"firebase failed: {e}")

# --- ADMIN APPROVAL LISTENER ---
def approval_listener():
    global approved_username
    if not db: return
    def on_snapshot(col_snapshot, changes, read_time):
        global approved_username
        for doc in col_snapshot:
            data = doc.to_dict()
            if data.get('status') == 'approved' and not approved_username:
                approved_username = data.get('name')
                approval_event.set()
                # Clean up the request after triggering enrollment
                doc.reference.delete()
                
    db.collection('security_requests').where('status', '==', 'approved').on_snapshot(on_snapshot)

threading.Thread(target=approval_listener, daemon=True).start()

# --- BUILT-IN FACE SCANNING ---
def enroll_user(name):
    print(f"ENROLLMENT STARTED for {name}")
    speech_queue.put(f"Access granted. Initializing facial scan for {name}. Please look at the camera.")
    
    # Wait for the speech to finish before stealing the camera
    time.sleep(4) 
    
    cap = cv2.VideoCapture(0)
    w, h = int(cap.get(3)), int(cap.get(4))

    YUNET_PATH = "Magic_Mirror_Package/yunet.onnx"
    SFACE_PATH = "Magic_Mirror_Package/sface.onnx"
    FACE_DATA_PATH = Path("Magic_Mirror_Package/face_profiles/face_data.pkl")
    PROFILES_PATH = Path("Magic_Mirror_Package/face_profiles/profiles.pkl")

    face_detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (w, h))
    face_recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")

    collected = 0
    faces_list, labels_list = [], []

    if FACE_DATA_PATH.exists():
        with open(FACE_DATA_PATH, "rb") as f:
            faces_list, labels_list = pickle.load(f)

    if PROFILES_PATH.exists():
        with open(PROFILES_PATH, "rb") as f: pro = pickle.load(f)
    else: pro = {"name_to_id": {}, "id_to_name": {}}

    if name not in pro["name_to_id"]:
        new_id = len(pro["name_to_id"])
        pro["name_to_id"][name] = new_id
        pro["id_to_name"][new_id] = name

    pid = pro["name_to_id"][name]

    while collected < 150:
        ret, frame = cap.read()
        if not ret: continue
        frame = cv2.flip(frame, 1)
        _, faces = face_detector.detect(frame)
        if faces is not None:
            # Align and save (100x100 grayscale for compatibility with your notebook)
            aligned = face_recognizer.alignCrop(frame, faces[0])
            gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
            faces_list.append(cv2.resize(gray, (100, 100)))
            labels_list.append(pid)
            collected += 1
            cv2.putText(frame, f"Scanning: {collected}/150", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        cv2.imshow("Registration Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyWindow("Registration Scanner")

    with open(FACE_DATA_PATH, "wb") as f: pickle.dump((faces_list, labels_list), f)
    with open(PROFILES_PATH, "wb") as f: pickle.dump(pro, f)

    print("Scan complete! Self-training AI...")
    speech_queue.put("Scan complete. Updating neural network.")
    subprocess.run([sys.executable, "retrain.py"]) 
    return True

# main webcam (face and hands)
def dist(p1, p2):
    return math.hypot(p2.x - p1.x, p2.y - p1.y)

def hand_center(lm):
    return sum(p.x for p in lm) / len(lm), sum(p.y for p in lm) / len(lm)

def unified_vision_thread():
    global recognized_user, last_seen_time, latest_frame, last_intruder_alert_time, pending_approval, reload_ai_model
    
    YUNET_PATH = "Magic_Mirror_Package/yunet.onnx"
    SFACE_PATH = "Magic_Mirror_Package/sface.onnx"
    MODEL_PATH = Path("Magic_Mirror_Package/face_profiles/hybrid_ai_model.pkl")
    PROFILES_JSON = Path("Magic_Mirror_Package/face_profiles/profiles.pkl")
    HAND_MODEL_PATH = "hand_landmarker.task"
    
    # download mediapipe model
    if not os.path.exists(HAND_MODEL_PATH):
        print("downloading mediapipe hand model...")
        urllib.request.urlretrieve("https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task", HAND_MODEL_PATH)
    
    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=HAND_MODEL_PATH),
        num_hands=1, min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6, min_tracking_confidence=0.6,
    )
    hand_detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("error opening webcam")
        return
        
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    face_detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (w, h), 0.9, 0.3, 5000) if os.path.exists(YUNET_PATH) else None
    face_recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "") if os.path.exists(SFACE_PATH) else None

    profiles, model = {}, None
    if PROFILES_JSON.exists():
        with open(PROFILES_JSON, "rb") as f: profiles = pickle.load(f)
    if MODEL_PATH.exists():
        model = joblib.load(MODEL_PATH)

    print("vision thread started")
    frame_idx = 0
    prev_x, prev_y = 0, 0
    mouse_held = False

    while True:
        # Check if we need to reload the model (after a new user is trained)
        if reload_ai_model:
            print("Vision thread reloading updated AI model...")
            if MODEL_PATH.exists(): model = joblib.load(MODEL_PATH)
            if PROFILES_JSON.exists():
                with open(PROFILES_JSON, "rb") as f: profiles = pickle.load(f)
            reload_ai_model = False

        success, image = cap.read()
        if not success: 
            time.sleep(0.01)
            continue
            
        image = cv2.flip(image, 1)
        latest_frame = image.copy()
        frame_idx += 1

        # 1. Hand Tracking
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        results = hand_detector.detect(mp_image)

        if results.hand_landmarks:
            lm = results.hand_landmarks[0]
            px, py = hand_center(lm)
            fx, fy = px * w, py * h  

            # map coordinates to screen size
            x_mapped = int((fx - FRAME_R) / (w - 2 * FRAME_R) * SCREEN_W)
            y_mapped = int((fy - FRAME_R) / (h - 2 * FRAME_R) * SCREEN_H)
            x_mapped = max(0, min(SCREEN_W - 1, x_mapped))
            y_mapped = max(0, min(SCREEN_H - 1, y_mapped))

            active_smoothing = SMOOTHING_DRAG if mouse_held else SMOOTHING_FREE
            curr_x = prev_x + (x_mapped - prev_x) / active_smoothing
            curr_y = prev_y + (y_mapped - prev_y) / active_smoothing

            try: 
                pyautogui.moveTo(int(curr_x), int(curr_y))
            except: 
                pass

            prev_x, prev_y = curr_x, curr_y

            # check pinch for clicking
            thumb_tip = lm[4]
            index_tip = lm[8]
            pinch_distance = dist(thumb_tip, index_tip)

            if not mouse_held and pinch_distance < PINCH_GRAB_DIST:
                pyautogui.mouseDown(button="left")
                mouse_held = True
            elif mouse_held and pinch_distance > PINCH_DROP_DIST:
                pyautogui.mouseUp(button="left")
                mouse_held = False
        else:
            # release mouse if hand disappears
            if mouse_held:
                pyautogui.mouseUp(button="left")
                mouse_held = False

        # 2. Face ID
        if frame_idx % 10 == 0 and not mouse_held and face_detector and model and face_recognizer:
            try:
                _, faces = face_detector.detect(image)
                if faces is not None:
                    face_aligned = face_recognizer.alignCrop(image, faces[0])
                    current_embedding = face_recognizer.feature(face_aligned).flatten().reshape(1, -1)
                    probs = model.predict_proba(current_embedding)[0]
                    best_idx = np.argmax(probs)
                    
                    if probs[best_idx] > 0.60:
                        new_user = profiles.get("id_to_name", {}).get(int(model.classes_[best_idx]), "Unknown")
                    else:
                        new_user = "Unknown"

                    # intruder logic & Admin Approval Flow
                    if new_user == "Unknown":
                        if not pending_approval and (time.time() - last_intruder_alert_time > 30):
                            last_intruder_alert_time = time.time()
                            print("Unknown face detected. Capturing and sending request...")
                            
                            # compress image to b64 string
                            small_frame = cv2.resize(latest_frame, (320, 240))
                            _, buffer = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                            img_b64 = base64.b64encode(buffer).decode('utf-8')
                            
                            # 1. Send MQTT security alert
                            if security_enforced:
                                payload = {
                                    "type": "intruder",
                                    "time": datetime.datetime.now().strftime("%I:%M:%S %p"),
                                    "image": f"data:image/jpeg;base64,{img_b64}"
                                }
                                mqtt_client.publish(TOPIC_ALERTS, json.dumps(payload))
                                
                            # 2. Upload to Firebase for Admin Approval
                            if db: 
                                db.collection('security_requests').add({
                                    "name": "Unknown",
                                    "status": "pending",
                                    "image": f"data:image/jpeg;base64,{img_b64}",
                                    "timestamp": firestore.SERVER_TIMESTAMP
                                })
                            
                            pending_approval = True
                            speech_queue.put("I don't recognize you. Sent a join request to the owner.")
                        
                        recognized_user = None 
                    else:
                        # normal login
                        pending_approval = False
                        if recognized_user != new_user:
                            recognized_user = new_user
                            speech_queue.put(f"Hi {recognized_user}")
                            log_user_login(recognized_user) 
                            
                        last_seen_time = time.time()
            except: 
                pass
                
        # logout if no face seen for a while
        if recognized_user is not None and (time.time() - last_seen_time > FACE_TIMEOUT):
            recognized_user = None
            speech_queue.put("Session logged out.")
            
        time.sleep(0.01)

threading.Thread(target=unified_vision_thread, daemon=True).start()

# weather api background thread
def weather_thread():
    global latest_temp
    while True:
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=25.2048&longitude=55.2708&current_weather=true"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                temp = data['current_weather']['temperature']
                latest_temp = f"{round(temp)}°C"
                send_to_ui({"temp": latest_temp})
        except Exception as e: 
            print(f"weather error: {e}")
        time.sleep(1800) # update every 30 mins

threading.Thread(target=weather_thread, daemon=True).start()

# load keys from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key: 
    sys.exit("missing gemini key in .env")
client = genai.Client(api_key=api_key)

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    sys.exit("missing spotify creds")

print("connecting to spotify...")
try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-modify-playback-state user-read-playback-state"
    ))
    sp.current_user() 
    print("spotify ready")
except Exception as e: 
    sys.exit(f"spotify failed: {e}")

def spotify_sync_thread():
    while True:
        try:
            current = sp.current_playback()
            if current and current.get('item'):
                is_playing = current['is_playing']
                item = current['item']
                images = item['album']['images']
                send_to_ui({
                    "song": item['name'] if is_playing else f"{item['name']} (Paused)",
                    "artist": item['artists'][0]['name'],
                    "album_art": images[0]['url'] if images else "https://misc.scdn.co/liked-songs/liked-songs-300.png",
                    "progress_ms": current.get('progress_ms', 0),
                    "duration_ms": item.get('duration_ms', 1),
                    "is_playing": is_playing
                })
        except: 
            pass 
        time.sleep(3)
        
threading.Thread(target=spotify_sync_thread, daemon=True).start()

# google calendar api
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
calendar_services = {} 

def get_calendar_service():
    if not recognized_user: return None
    if recognized_user in calendar_services:
        return calendar_services[recognized_user]
        
    token_path = f"calendar_tokens/{recognized_user}_token.json"
    creds = Credentials.from_authorized_user_file(token_path, SCOPES) if os.path.exists(token_path) else None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: 
            creds.refresh(Request())
        else:
            print(f"no valid calendar token for {recognized_user}")
            return None
        with open(token_path, 'w') as token: 
            token.write(creds.to_json())
            
    service = build('calendar', 'v3', credentials=creds)
    calendar_services[recognized_user] = service
    return service

def get_todos():
    if not db or not recognized_user: return []
    try:
        doc = db.collection('todos').document(recognized_user).get()
        return doc.to_dict().get('tasks', []) if doc.exists else []
    except: 
        return []

def save_todos(todos):
    if not db or not recognized_user: return
    try:
        db.collection('todos').document(recognized_user).set({'tasks': todos})
        send_to_ui({"todos": todos})
    except Exception as e: 
        print(f"firebase push error: {e}")

def get_layout():
    # default coordinates
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
            # AUTO-ONBOARDING: Pull from a template if new user
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
    if not db or not recognized_user: return
    try:
        db.collection('layouts').document(recognized_user).set(
            {widget_id: {"x": x, "y": y}}, merge=True)
    except Exception as e: 
        print(f"firebase layout error: {e}")

def state_sync_thread():
    # watches for user changes and pushes the right layout
    last_todos = None
    last_user = None
    while True:
        try:
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
                    # lock screen defaults
                    baseline_layout = {
                        "clock": {"x":0,"y":0}, "ai-assistant": {"x":0,"y":0},
                        "calendar": {"x":0,"y":0}, "todo": {"x":0,"y":0},
                        "weather": {"x":0,"y":0}, "spotify": {"x":0,"y":0}
                    }
                    send_to_ui({
                        "username": "Guest", 
                        "layout": baseline_layout, 
                        "todos": [],
                        "is_locked": True 
                    })
            
            if recognized_user:
                current_todos = get_todos()
                if current_todos != last_todos:
                    send_to_ui({"todos": current_todos})
                    last_todos = current_todos
                    
        except: pass
        time.sleep(2)

threading.Thread(target=state_sync_thread, daemon=True).start()

# voice logic
WAKE_WORD = "hey mirror"
listening_for_command = False
last_interaction_time = time.time()
TIMEOUT_SECONDS = 15
last_calibration_time = time.time()
CALIBRATION_INTERVAL = 60

def process_calendar_intent(json_data):
    service = get_calendar_service()
    if not service: 
        return speech_queue.put("I don't have your calendar linked yet.")
        
    intent = json_data.get("intent")
    if intent == "read":
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z") 
        events = service.events().list(calendarId='primary', timeMin=now, maxResults=15, singleEvents=True, orderBy='startTime').execute().get('items', [])
        # filtering out
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
            service.events().insert(calendarId='primary', body={'summary': summary, 'start': {'dateTime': start_datetime, 'timeZone': local_tz}, 'end': {'dateTime': end_datetime, 'timeZone': local_tz}}).execute()
            speech_queue.put(f"I've added {summary} to your calendar.")
        except: 
            speech_queue.put("I couldn't sync that format with your Google Calendar.")
             
    elif intent == "delete":
        summary = json_data.get("summary")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            events = service.events().list(calendarId='primary', q=summary, timeMin=now, maxResults=5, singleEvents=True, orderBy='startTime').execute().get('items', [])
            service.events().delete(calendarId='primary', eventId=events[0]['id']).execute()
            speech_queue.put(f"I have canceled {events[0].get('summary', 'Unknown Event')} from your calendar.")
        except: 
            speech_queue.put("I ran into an error trying to cancel that event.")

def process_todo_intent(json_data):
    intent, task = json_data.get("intent"), json_data.get("task")
    todos = get_todos()
    if intent == "read": 
        speech_queue.put(f"Here is your list: {', '.join(todos)}." if todos else "You don't have anything on your to-do list right now.")
    elif intent == "add" and task:
        todos.append(task)
        save_todos(todos)
        speech_queue.put(f"I've added {task} to your list.")
    elif intent == "clear":
        save_todos([])
        speech_queue.put("Your list has been cleared completely.")
    elif intent == "delete" and task:
        matched = next((item for item in todos if task.lower() in item.lower() or item.lower() in task.lower()), None)
        if matched:
            todos.remove(matched)
            save_todos(todos)
            speech_queue.put(f"I've crossed off {matched} from your list.")
        else: 
            speech_queue.put(f"I couldn't find {task} on your to-do list.")

def ask_gemini(text_query):
    query_lower = text_query.lower()
    send_to_ui({"ai_state": "thinking", "ai_text": "Thinking..."})
    
    # inject current time so ai knows what today is
    sys_aw = f"SYSTEM AWARENESS: {datetime.datetime.now().strftime('%I:%M %p on %A, %B %d, %Y')}. Location: Dubai, UAE.\n"
    
    # 1. Spotify commands
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
                if song_name and song_name not in ["music", "spotify", "the music", "some music"]:
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
            
    # 2. Calendar commands
    if "calendar" in query_lower.split() or "schedule" in query_lower.split():
        try:
            # prompt regex forcing gemini to return purely json
            prompt = f"{sys_aw}EXTREMELY STRICT RULES: Output ONLY a single raw JSON object. NO markdown, NO text. Action mappings -> Add: {{\"intent\": \"add\", \"summary\": \"X\", \"date\": \"YYYY-MM-DD\", \"time\": \"HH:MM:00\"}}. Delete: {{\"intent\": \"delete\", \"summary\": \"X\"}}. Read: {{\"intent\": \"read\"}}.\nUser: {text_query}"
            res = client.models.generate_content(model='gemma-3-4b-it', contents=prompt).text
            import re
            match = re.search(r'\{.*\}', res, re.DOTALL)
            if match: 
                return process_calendar_intent(json.loads(match.group()))
        except: 
            return speech_queue.put("I'm having trouble connecting to my calendar brain.")

    # 3. Todo commands
    if any(k in query_lower.split() for k in ["todo", "task", "list", "buy", "remind", "finish", "delete", "cancel", "to-do", "tasks", "lists"]):
        try:
            prompt = f"{sys_aw}EXTREMELY STRICT RULES: Output ONLY a single raw JSON object. NO markdown, NO conversational text. Action mappings -> Add: {{\"intent\": \"add\", \"task\": \"...\"}}. Delete: {{\"intent\": \"delete\", \"task\": \"...\"}}. Read: {{\"intent\": \"read\"}}. Clear: {{\"intent\": \"clear\"}}.\nUser: {text_query}"
            res = client.models.generate_content(model='gemma-3-4b-it', contents=prompt).text
            import re
            match = re.search(r'\{.*\}', res, re.DOTALL)
            if match: 
                return process_todo_intent(json.loads(match.group()))
        except: 
            return speech_queue.put("I had a brain freeze managing your tasks.")

    # 4. Multimodal Vision
    vision_keywords = ["what is this", "what am i holding", "what is in front", "what is with me", "look at this"]
    if any(k in query_lower for k in vision_keywords):
        if latest_frame is not None:
            try:
                rgb_image = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
                prompt = f"{sys_aw}Identify the main object I am holding or showing you. Tell me exactly what it is, and then give me two quick, fascinating facts about it. Keep your response conversational, concise, and under 3 sentences."
                
                res = client.models.generate_content(model='gemini-2.5-flash', contents=[pil_image, prompt])
                return speech_queue.put(res.text.strip())
            except Exception as e: 
                return speech_queue.put("I'm having trouble focusing my eyes right now.")
        else: 
            return speech_queue.put("My camera feed is currently blind.")

    # 5. Default Chat fallback
    try:
        res = client.models.generate_content(model='gemma-3-4b-it', contents=f"{sys_aw}Keep responses brief and conversational (1-2 sentences).\nUser: {text_query}")
        speech_queue.put(res.text.strip())
    except: 
        speech_queue.put("I am having trouble connecting to my brain right now.")

def audio_callback(recognizer, audio):
    global listening_for_command, is_speaking
    if is_speaking: return
    try:
        text = recognizer.recognize_google(audio).lower()
        if listening_for_command:
            text = text.replace("i am listening", "").strip()
            if not text: return
            
            if recognized_user is None: 
                speech_queue.put("User is not recognised.")
            else: 
                ask_gemini(text)
                
            listening_for_command = False
        elif WAKE_WORD in text:
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
        pass

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
        recognizer.adjust_for_ambient_noise(source, duration=1.5 if is_recalibrating else 3)
        recognizer.energy_threshold += 300
        if not is_recalibrating: 
            print(f"microphone ready. say '{WAKE_WORD}'")
            
    return recognizer.listen_in_background(microphone, audio_callback, phrase_time_limit=8)

if __name__ == "__main__":
    print("starting intelli-mirror core...")
    
    website_path = os.path.abspath("website/index.html")
    print(f"launching browser at {website_path}")
    webbrowser.open(f"file://{website_path}")

    send_to_ui({"ai_state": "idle", "ai_text": "Ready! Say 'Hey Mirror'", "todos": get_todos()})
    
    stop_listening = start_listening(False)
    
    try:
        while True:
            # --- Handle Admin Approval Event ---
            if approval_event.is_set():
                enroll_user(approved_username)
                approved_username = None
                pending_approval = False
                reload_ai_model = True # Tells the vision thread to fetch the newly trained model
                approval_event.clear()
                speech_queue.put("Enrollment complete. Welcome to the system.")
                
            try:
                # blocks until there is speech in the queue
                speak(speech_queue.get_nowait())
                last_interaction_time = time.time()
                last_calibration_time = time.time()
            except queue.Empty: 
                pass 
            
            # sleep if we wait too long
            if listening_for_command and not is_speaking and (time.time() - last_interaction_time) > TIMEOUT_SECONDS:
                listening_for_command = False
                send_to_ui({"ai_state": "idle", "ai_text": "Say 'Hey Mirror'"})
                speech_queue.put("Going to sleep.")
            
            # recalibrate mic periodically 
            if not listening_for_command and not is_speaking and (time.time() - last_calibration_time) > CALIBRATION_INTERVAL:
                stop_listening(wait_for_stop=False)
                stop_listening = start_listening(True)
                last_calibration_time = time.time()
                
            time.sleep(0.1) 
            
    except KeyboardInterrupt: 
        print("stopping mirror...")
        stop_listening(wait_for_stop=False)