# enrolls faces for the ML notebook pipeline
import cv2
import numpy as np
import pickle
import os
import argparse
import time
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# setup paths
PROFILES_DIR = Path("face_profiles")
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

PROFILES_JSON = PROFILES_DIR / "profiles.pkl"  
FACE_DATA_FILE = PROFILES_DIR / "face_data.pkl"

# model weights
YUNET_PATH = "yunet.onnx"
SFACE_PATH = "sface.onnx"

FACE_TIMEOUT = 10  # auto logout after 10s
CAPTURED_SIZE = (100, 100) # used for step 1 in the notebook

# global state for the local web server
SHARED_STATE = {
    "user": None,
    "last_seen": 0,
}

# handles api requests from the frontend
class FaceAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {}
        time_diff = time.time() - SHARED_STATE["last_seen"]
        
        # if we saw them recently, return the user
        if SHARED_STATE["user"] and (time_diff < FACE_TIMEOUT):
            response["user"] = SHARED_STATE["user"]
        else:
            response["user"] = None
            
        self.wfile.write(json.dumps(response).encode())

    
    def log_message(self, format, *args):
        pass

def load_profiles():
    if PROFILES_JSON.exists():
        with open(PROFILES_JSON, "rb") as f:
            return pickle.load(f)
    return {"id_to_name": {}, "name_to_id": {}}

def save_profiles(profiles):
    with open(PROFILES_JSON, "wb") as f:
        pickle.dump(profiles, f)

def get_ai_tools(w=640, h=480):
    if not os.path.exists(YUNET_PATH): 
        return None, None
    detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (w, h), 0.9, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "") if os.path.exists(SFACE_PATH) else None
    return detector, recognizer

def enroll_mode(name):
    profiles = load_profiles()
    
    # assign a new id if they don't exist
    if name not in profiles["name_to_id"]:
        new_id = len(profiles["name_to_id"])
        profiles["name_to_id"][name] = new_id
        profiles["id_to_name"][new_id] = name
    
    person_id = profiles["name_to_id"][name]
    
    cap = cv2.VideoCapture(0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    detector, recognizer = get_ai_tools(w, h)
    if detector is None:
        print("error: yunet.onnx is missing. download it first.")
        return

    print(f"\nenrolling {name}...")
    print("look at the camera. taking 150 pics...")
    
    all_faces, all_labels = [], []
    # load existing data so we don't overwrite other people
    if FACE_DATA_FILE.exists():
        with open(FACE_DATA_FILE, "rb") as f:
            all_faces, all_labels = pickle.load(f)

    collected = 0
    while collected < 150:
        ret, frame = cap.read()
        if not ret: 
            continue
        frame = cv2.flip(frame, 1) # mirror effect
        
        _, faces = detector.detect(frame)
        if faces is not None:
            for face in faces:
                # sface alignment makes the ML steps more accurate
                if recognizer:
                    face_aligned = recognizer.alignCrop(frame, face)
                    face_gray = cv2.cvtColor(face_aligned, cv2.COLOR_BGR2GRAY)
                    face_resized = cv2.resize(face_gray, CAPTURED_SIZE)
                else:
                    # manual crop fallback if sface isn't there
                    coords = face[:4].astype(int)
                    face_crop = frame[max(0,coords[1]):coords[1]+coords[3], max(0,coords[0]):coords[0]+coords[2]]
                    face_gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                    face_resized = cv2.resize(face_gray, CAPTURED_SIZE)

                all_faces.append(face_resized)
                all_labels.append(person_id)
                collected += 1
                
                # draw the box and text
                coords = face[:4].astype(int)
                cv2.rectangle(frame, (coords[0], coords[1]), (coords[0]+coords[2], coords[1]+coords[3]), (0, 255, 255), 2)
                cv2.putText(frame, f"Capturing: {collected}/150", (coords[0], coords[1]-10), 0, 0.7, (0, 255, 255), 2)
                break # just grab the first face it sees
                
        cv2.imshow("Enrollment scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    cap.release()
    cv2.destroyAllWindows()
    
    # save everything
    if collected >= 150:
        with open(FACE_DATA_FILE, "wb") as f:
            pickle.dump((all_faces, all_labels), f)
        save_profiles(profiles)
        print(f"done! enrolled {name} with 150 samples.")
        print("next step: go open train_face_model.ipynb and train the model!")
    else:
        print("enrollment canceled or incomplete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--enroll", action="store_true")
    args = parser.parse_args()
    
    if args.enroll:
        name = input("\nEnter name: ").strip()
        if name: 
            enroll_mode(name)
    else:
        print("run this script with the --enroll flag to add a new face.")