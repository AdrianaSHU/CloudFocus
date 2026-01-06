import cv2
import mediapipe as mp
import time
import math
import numpy as np
import requests
import atexit
import sys
import signal
import os

# --- 1. Raspberry Pi Runtime Check ---
import tflite_runtime.interpreter as tflite


# --- 2. Service Warmup ---
time.sleep(5)

print(" Starting CloudFocus Edge AI System...")

# --- 3. SenseHat Safety & Manager ---
try:
    from sense_hat_manager import SenseHatManager
    sense_manager = SenseHatManager()
except:
    class MockSense:
        def set_status(self, s): pass
        def get_sensor_data(self): return {"temperature": 0, "humidity": 0}
        def clear(self): pass
    sense_manager = MockSense()

# --- 4. Configuration ---
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
EAR_THRESHOLD = 0.30
EAR_CONSEC_FRAMES = 25

# Model Settings
TFLITE_MODEL_PATH = 'Model/rafdb_fusion.tflite' 
EMOTION_LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']
FOCUSED_EMOTIONS = ['Neutral', 'Happy', 'Sad', 'Angry', 'Disgust', 'Surprise']
EMOTION_BUFFER = 150

# Cloud Settings
DJANGO_API_URL = "https://cloudfocus-d8frducfd6fjgdbx.uksouth-01.azurewebsites.net/api/log_focus/"
USER_API_KEY = "4bd67f2e-ee6f-4342-ba43-a1c2a96875fe"
TRANSMIT_INTERVAL = 30

# --- 5. Cleanup Handler ---
def perform_cleanup(signum=None, frame=None):
    print("\n Cleaning up resources...")
    sense_manager.clear()
    try:
        cap.release()
    except: 
        pass
    sys.exit(0)

atexit.register(perform_cleanup)
signal.signal(signal.SIGTERM, perform_cleanup)
signal.signal(signal.SIGINT, perform_cleanup)

# --- 6. Initialization ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Load Model
try:
    interpreter = tflite.Interpreter(model_path=TFLITE_MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    MODEL_H = input_details[0]['shape'][1]
    MODEL_W = input_details[0]['shape'][2]
    print(f"✅ Model Loaded: {MODEL_W}x{MODEL_H}")
except Exception as e:
    print(f"❌ Model Error: {e}")
    sys.exit(1)

# --- 7. Helpers ---
LANDMARKS_LEFT = [362, 385, 387, 263, 373, 380]
LANDMARKS_RIGHT = [33, 160, 158, 133, 153, 144]

def euclidean_dist(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def calculate_ear(landmarks, indices, shape):
    try:
        coords = [(landmarks[i].x * shape[1], landmarks[i].y * shape[0]) for i in indices]
        v1 = euclidean_dist(coords[1], coords[5])
        v2 = euclidean_dist(coords[2], coords[4])
        h = euclidean_dist(coords[0], coords[3])
        return (v1 + v2) / (2.0 * h)
    except: return 0.0

def send_data(status, emotion, sensor):
    try:
        payload = {
            'status': status,
            'emotion_detected': emotion,
            'temperature': sensor.get("temperature", 0),
            'humidity': sensor.get("humidity", 0)
        }
        requests.post(DJANGO_API_URL, json=payload, headers={'API-Key': USER_API_KEY}, timeout=2)
    except: pass

# --- 8. Main Loop ---
cap = None
ear_counter = 0
ear_smoothed = 0.0
last_transmit = 0.0
emotion_buffer = []

print(" System Ready. Waiting for camera...")

while True:
    # A. Camera Reconnection Logic
    if cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        if not cap.isOpened():
            sense_manager.clear()
            time.sleep(2) 
            continue
        else:
            print("✅ Camera Connected!")

    # B. Read Frame
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Camera stream lost. Retrying...")
        cap.release()
        cap = None
        sense_manager.clear()
        time.sleep(1)
        continue

    # C. Define time for loop
    current_time = time.time()

    # D. Processing
    ih, iw, _ = frame.shape
    current_emotion = "Scanning..."
    drowsy_alert = False
    final_status = "NO FACE"
    confidence_score = 0.0

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        lms = results.multi_face_landmarks[0].landmark

        # Drowsiness
        left_ear = calculate_ear(lms, LANDMARKS_LEFT, (ih, iw))
        right_ear = calculate_ear(lms, LANDMARKS_RIGHT, (ih, iw))
        avg_ear = (left_ear + right_ear) / 2.0
        ear_smoothed = 0.3 * avg_ear + 0.7 * ear_smoothed

        if ear_smoothed < EAR_THRESHOLD:
            ear_counter += 1
            if ear_counter >= EAR_CONSEC_FRAMES: drowsy_alert = True
        else:
            ear_counter = 0

        # Emotion
        xs = [lm.x for lm in lms]; ys = [lm.y for lm in lms]
        x1, x2 = int(min(xs)*iw), int(max(xs)*iw)
        y1, y2 = int(min(ys)*ih), int(max(ys)*ih)
        pad = 20
        x1, y1 = max(0, x1-pad), max(0, y1-pad)
        x2, y2 = min(iw, x2+pad), min(ih, y2+pad)

        if x2 > x1 and y2 > y1:
            roi = cv2.resize(rgb[y1:y2, x1:x2], (MODEL_W, MODEL_H))
            
            # RAW INPUT (0-255)
            input_data = np.expand_dims(roi, axis=0).astype(np.float32)
            
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            preds = interpreter.get_tensor(output_details[0]['index'])[0]
            
            idx = np.argmax(preds)
            current_emotion = EMOTION_LABELS[idx]
            confidence_score = preds[idx] * 100

        # Status Logic
        emotion_buffer.append(current_emotion)
        if len(emotion_buffer) > EMOTION_BUFFER: 
            emotion_buffer.pop(0)
        stable_emotion = max(set(emotion_buffer), key=emotion_buffer.count)

        if drowsy_alert: final_status = "DROWSY"
        elif stable_emotion in FOCUSED_EMOTIONS: final_status = "FOCUSED"
        elif stable_emotion == "No Face": final_status = "NO FACE"
        else: final_status = "DISTRACTED"

    # E. Feedback (LEDs + Cloud)
    sense_manager.set_status(final_status)

    if (current_time - last_transmit) > TRANSMIT_INTERVAL:
        sens = sense_manager.get_sensor_data()
        print(f"📡 {final_status} | {current_emotion} ({confidence_score:.1f}%)")
        send_data(final_status, current_emotion, sens)
        last_transmit = current_time

    # F. Display (Standard Check)
    if "DISPLAY" in os.environ:
        cv2.rectangle(frame, (0, 0), (280, 120), (0, 0, 0), -1)
        col = (0, 255, 0) if final_status == "FOCUSED" else (0, 0, 255)
        cv2.putText(frame, f"STATUS: {final_status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
        cv2.putText(frame, f"Emo: {current_emotion} ({confidence_score:.0f}%)", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"EAR: {ear_smoothed:.2f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow("CloudFocus", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break