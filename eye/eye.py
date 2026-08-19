import cv2
import face_recognition
import os
import numpy as np
import base64
import requests
import threading
from ultralytics import YOLO
import collections 
import time        

class Prototype_1Eye:
    def __init__(self, known_faces_dir="known_faces", gaze_callback=None, frame_callback=None):
        print("[Prototype_1 EYE] Initializing Background Vision System...")
        self.known_faces_dir = known_faces_dir
        self.gaze_callback = gaze_callback 
        self.frame_callback = frame_callback 
        
        self.current_user = "Unknown"
        self.detected_objects = set()
        self.deep_vision_context = ""
        
        self.is_running = False
        self.camera_thread = None
        self.current_frame = None
        
        self.filtered_cx = None
        self.filtered_cy = None

        self.x_history = collections.deque(maxlen=15)
        self.last_motion_time = time.time()
        
        self._load_models()

    def _load_models(self):
        print("[Prototype_1 EYE] Loading YOLOv10-nano...")
        self.yolo_model = YOLO("yolov10n.pt") 

        print("[Prototype_1 EYE] Loading Biometrics (Known Faces)...")
        self.known_face_encodings = []
        self.known_face_names = []
        
        if os.path.exists(self.known_faces_dir):
            for filename in os.listdir(self.known_faces_dir):
                if filename.endswith((".jpg", ".png")):
                    filepath = os.path.join(self.known_faces_dir, filename)
                    image = face_recognition.load_image_file(filepath)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        name = os.path.splitext(filename)[0].capitalize()
                        self.known_face_names.append(name)

    def _camera_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Prototype_1 EYE: ERROR] Cannot open camera.")
            self.is_running = False
            return

        process_this_frame = True

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
                
            self.current_frame = frame.copy()
            frame_h, frame_w, _ = frame.shape
            current_frame_objects = set()

            # --- A. OBJECT DETECTION (YOLO) ---
            results = self.yolo_model(frame, stream=True, verbose=False)
            largest_yolo_area = 0
            largest_yolo_center = None
            
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0])
                    class_name = self.yolo_model.names[cls_id]
                    current_frame_objects.add(class_name)
                    
                    area = (x2 - x1) * (y2 - y1)
                    if area > largest_yolo_area:
                        largest_yolo_area = area
                        largest_yolo_center = ((x1 + x2) / 2, (y1 + y2) / 2)

            self.detected_objects = current_frame_objects

            # --- B. FACE RECOGNITION ---
            detected_face_center = None
            if process_this_frame:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                detected_user = "Unknown"
                
                if face_locations:
                    top, right, bottom, left = face_locations[0]
                    detected_face_center = ((left + right) * 2, (top + bottom) * 2)

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            detected_user = self.known_face_names[best_match_index]
                
                self.current_user = detected_user if face_locations else "No one visible"

            process_this_frame = not process_this_frame

            # ---------------------------------------------------------
            # C. GAZE TRACKING (WITH EMA LOW-PASS FILTER)
            # ---------------------------------------------------------
            target_found = False
            raw_cx, raw_cy = 0, 0

            # Ưu tiên 1: Mặt người | Ưu tiên 2: Đồ vật to nhất
            if detected_face_center:
                raw_cx, raw_cy = detected_face_center
                target_found = True
            elif largest_yolo_center:
                raw_cx, raw_cy = largest_yolo_center
                target_found = True

            if target_found:
                if self.filtered_cx is None:
                    self.filtered_cx, self.filtered_cy = raw_cx, raw_cy
                else:
                    alpha = 0.15 
                    self.filtered_cx = alpha * raw_cx + (1 - alpha) * self.filtered_cx
                    self.filtered_cy = alpha * raw_cy + (1 - alpha) * self.filtered_cy

                # ---------------------------------------------------------
                # TURBULANCE DETECTION
                # ---------------------------------------------------------
                target_norm_x = -((self.filtered_cx / frame_w) * 2 - 1.0)
                self.x_history.append(target_norm_x)
                
                if time.time() - self.last_motion_time > 10.0 and len(self.x_history) == 15:
                    hist_list = list(self.x_history)
                    max_x = max(hist_list)
                    min_x = min(hist_list)
                    
                    if max_x - min_x > 0.35:
                        direction_changes = 0
                        # Đếm số lần đảo chiều
                        for i in range(1, len(hist_list) - 1):
                            prev_diff = hist_list[i] - hist_list[i-1]
                            next_diff = hist_list[i+1] - hist_list[i]
                            if prev_diff * next_diff < 0:
                                direction_changes += 1
                                
                        if direction_changes >= 2:
                            print("\n[Prototype_1 EYE] Rapid motion detected!")
                            self.last_motion_time = time.time()
                            if self.motion_callback:
                                self.motion_callback("wave")

            else:
                if self.filtered_cx is not None:
                    center_x, center_y = frame_w / 2, frame_h / 2
                    alpha_drift = 0.05 # Trôi về giữa rất chậm
                    self.filtered_cx = alpha_drift * center_x + (1 - alpha_drift) * self.filtered_cx
                    self.filtered_cy = alpha_drift * center_y + (1 - alpha_drift) * self.filtered_cy

            target_norm_x, target_norm_y = 0.0, 0.0
            if self.filtered_cx is not None:
                target_norm_x = -((self.filtered_cx / frame_w) * 2 - 1.0)
                target_norm_y = (self.filtered_cy / frame_h) * 2 - 1.0

            if self.gaze_callback:
                self.gaze_callback(target_norm_x, target_norm_y)

            if self.frame_callback:
                self.frame_callback(frame.copy())

        cap.release()

    def get_vision_state(self):
        objects_str = ", ".join(self.detected_objects) if self.detected_objects else "None"
        return {
            "user_identity": self.current_user,
            "visible_objects": objects_str,
            "deep_vision_context": self.deep_vision_context
        }

    def analyze_scene_sync(self, query="What exactly is the person doing or holding? Be concise."):
        if self.current_frame is None:
            return "Camera frame is not available."

        print(f"\n[DEEP VISION] Querying MiniCPM-V: '{query}'")
        _, buffer = cv2.imencode('.jpg', self.current_frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        payload = {
            "model": "minicpm-v",
            "messages": [{"role": "user", "content": query, "images": [img_base64]}],
            "stream": False
        }

        try:
            response = requests.post("http://localhost:11434/api/chat", json=payload)
            self.deep_vision_context = response.json().get('message', {}).get('content', '').strip()
            return self.deep_vision_context
        except Exception as e:
            return "Error connecting to deep vision module."

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.camera_thread = threading.Thread(target=self._camera_loop)
            self.camera_thread.start()

    def stop(self):
        self.is_running = False
        if self.camera_thread:
            self.camera_thread.join()
        print("[Prototype_1 EYE] Vision System Shutdown.")