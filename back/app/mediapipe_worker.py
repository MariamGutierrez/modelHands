import mediapipe as mp
import cv2
import numpy as np

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False,
                       max_num_hands=1,
                       min_detection_confidence=0.5,
                       min_tracking_confidence=0.5)

def extract_landmarks_from_frame(frame_bgr):
    # frame_bgr: numpy array BGR (OpenCV)
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    if not results.multi_hand_landmarks:
        return None
    lm = results.multi_hand_landmarks[0]
    h, w, _ = frame_bgr.shape
    landmarks = []
    for i, p in enumerate(lm.landmark):
        landmarks.append({
            "id": i,
            "x": p.x,
            "y": p.y,
            "z": p.z,
            "visibility": 1.0  # MediaPipe hands no da visibility, leave 1.0
        })
    return landmarks
