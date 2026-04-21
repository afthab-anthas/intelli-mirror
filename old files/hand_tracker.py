import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import math
import os
import urllib.request

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # Remove pyautogui delay for snappier response

# ── Screen dimensions & Camera Mapping ─────────────────────────────────────────
SCREEN_W, SCREEN_H = pyautogui.size()
FRAME_R = 0  # Cropped margin for precise edge-to-edge screen mapping

# ── Dynamic Smoothing (Friction) ───────────────────────────────────────────────
SMOOTHING_FREE = 7      # Snappy movement when hovering
SMOOTHING_DRAG = 14     # Heavy, stable friction when dragging a widget

prev_x, prev_y = 0, 0
curr_x, curr_y = 0, 0

# ── Sticky Pinch Thresholds (Hysteresis) ───────────────────────────────────────
PINCH_GRAB_DIST = 0.045  # Must pinch tightly to grab
PINCH_DROP_DIST = 0.085  # Must open fingers noticeably wider to release

# ── Model Setup ────────────────────────────────────────────────────────────────
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = "hand_landmarker.task"

def download_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading MediaPipe hand tracking model, please wait…")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Download complete.")

# ── Finger Chains & Helpers ────────────────────────────────────────────────────
FINGER_CHAINS = {
    "Thumb":  (1,  2,  3,  4), "Index":  (5,  6,  7,  8),
    "Middle": (9,  10, 11, 12), "Ring":   (13, 14, 15, 16), "Pinky":  (17, 18, 19, 20),
}

def dist(p1, p2):
    return math.hypot(p2.x - p1.x, p2.y - p1.y)

def hand_center(lm):
    x = sum(p.x for p in lm) / len(lm)
    y = sum(p.y for p in lm) / len(lm)
    return x, y

def finger_curl_ratios(lm):
    curls = {}
    for name, (b, j1, j2, tip) in FINGER_CHAINS.items():
        seg1, seg2, seg3 = dist(lm[b], lm[j1]), dist(lm[j1], lm[j2]), dist(lm[j2], lm[tip])
        chain_len = seg1 + seg2 + seg3 + 1e-6
        straight = dist(lm[b], lm[tip])
        curls[name] = 1.0 - min(straight / chain_len, 1.0)
    return curls

def draw_finger_bars(image, curls, h, w):
    bar_w, bar_max_h, gap = 18, 70, 6
    names, colors = ["Th", "Idx", "Mid", "Rng", "Pky"], [(0, 200, 255), (0, 255, 100), (255, 180, 0), (255, 80, 160), (80, 160, 255)]
    start_x, base_y = w - (bar_w + gap) * 5 - 10, h - 12

    for i, (name, key) in enumerate(zip(names, FINGER_CHAINS.keys())):
        curl, bx = curls[key], start_x + i * (bar_w + gap)
        filled_h = int(curl * bar_max_h)
        cv2.rectangle(image, (bx, base_y - bar_max_h), (bx + bar_w, base_y), (50, 50, 50), cv2.FILLED)
        if filled_h > 0:
            cv2.rectangle(image, (bx, base_y - filled_h), (bx + bar_w, base_y), colors[i], cv2.FILLED)
        cv2.rectangle(image, (bx, base_y - bar_max_h), (bx + bar_w, base_y), (200, 200, 200), 1)
        cv2.putText(image, name, (bx, base_y - bar_max_h - 4), cv2.FONT_HERSHEY_PLAIN, 0.9, (220, 220, 220), 1)

# ── Main Loop ──────────────────────────────────────────────────────────────────
def main():
    global prev_x, prev_y, curr_x, curr_y

    download_model()
    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=1, min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6, min_tracking_confidence=0.6,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("═══════════════════════════════════════════")
    print("  Magic Mirror – Hand Cursor Control Active")
    print("  🖐  Move HAND      → cursor follows")
    print("  🤏  Pinch tightly  → GRAB WIDGET")
    print("  🖐  Open wide      → DROP WIDGET")
    print("═══════════════════════════════════════════")

    mouse_held = False                 

    while True:
        success, image = cap.read()
        if not success: continue

        image = cv2.flip(image, 1)
        h, w, _ = image.shape

        cv2.rectangle(image, (FRAME_R, FRAME_R), (w - FRAME_R, h - FRAME_R), (180, 0, 255), 2)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        results = detector.detect(mp_image)

        if results.hand_landmarks:
            lm = results.hand_landmarks[0]
            
            # ── 1. Dynamic Cursor Smoothing ─────────────────────────────────
            px, py = hand_center(lm)
            fx, fy = px * w, py * h  

            x_mapped = int((fx - FRAME_R) / (w - 2 * FRAME_R) * SCREEN_W)
            y_mapped = int((fy - FRAME_R) / (h - 2 * FRAME_R) * SCREEN_H)
            x_mapped = max(0, min(SCREEN_W - 1, x_mapped))
            y_mapped = max(0, min(SCREEN_H - 1, y_mapped))

            # Apply heavy friction if holding, light friction if hovering
            active_smoothing = SMOOTHING_DRAG if mouse_held else SMOOTHING_FREE
            
            curr_x = prev_x + (x_mapped - prev_x) / active_smoothing
            curr_y = prev_y + (y_mapped - prev_y) / active_smoothing

            try: pyautogui.moveTo(int(curr_x), int(curr_y))
            except Exception: pass

            prev_x, prev_y = curr_x, curr_y
            cv2.circle(image, (int(fx), int(fy)), 10, (0, 255, 80), cv2.FILLED)

            # ── 2. Sticky Pinch Detection (Hysteresis) ─────────────────────
            thumb_tip = lm[4]
            min_dist = min(dist(thumb_tip, lm[tip_idx]) for tip_idx in [8, 12, 16, 20])

            if not mouse_held and min_dist < PINCH_GRAB_DIST:
                pyautogui.mouseDown(button="left")
                mouse_held = True
                print("GRABBED (Locked)")

            elif mouse_held and min_dist > PINCH_DROP_DIST:
                pyautogui.mouseUp(button="left")
                mouse_held = False
                print("DROPPED (Released)")

            # ── Visual Feedback ────────────────────────────────────────────
            if mouse_held:
                cv2.circle(image, (int(fx), int(fy)), 22, (0, 165, 255), cv2.FILLED)
                cv2.putText(image, "PINCH LOCKED", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)
            else:
                cv2.putText(image, "OPEN", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 80), 2)
            
            draw_finger_bars(image, finger_curl_ratios(lm), h, w)

        else:
            if mouse_held:
                pyautogui.mouseUp(button="left")
                mouse_held = False
                print("Hand lost – MOUSE UP")
            cv2.putText(image, "No hand detected", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 80), 2)

        cv2.imshow("Magic Mirror – Hand Cursor Control", image)
        if cv2.waitKey(1) & 0xFF == ord("q"): break

    if mouse_held: pyautogui.mouseUp(button="left")
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__": main()