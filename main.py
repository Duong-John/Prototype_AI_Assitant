import sys
import time
import select
import threading
import evdev
import re
import numpy as np
import cv2

from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import pyqtSignal, QObject, Qt

from enum import Enum

sys.path.append('./face')
sys.path.append('./eye')
sys.path.append('./audio')
sys.path.append('./brain')
sys.path.append('./tools')

from face import Prototype_1FaceUI
from eye import Prototype_1Eye
from audio import Prototype_1Audio
from brain import AIBuddyBrain
from web_search import perform_web_search_ddgs

class AgentState(Enum):
    IDLE = 1
    LISTENING = 2
    THINKING = 3
    SPEAKING = 4

class SignalRouter(QObject):
    frame_signal = pyqtSignal(np.ndarray)

class YoloDebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prototype_1 Eye - YOLO Monitor")
        self.resize(640, 480)
        self.label = QLabel(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_frame(self, frame):
        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qt_img).scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio))

# ---------------------------------------------------------
# HARDWARE KEY MONITOR
# ---------------------------------------------------------
# class HardwareKeyMonitor:
#     def __init__(self):
#         self.space_pressed = False
#         self.running = True
#         self.devices = {}
#         for path in evdev.list_devices():
#             dev = evdev.InputDevice(path)
#             if evdev.ecodes.EV_KEY in dev.capabilities():
#                 self.devices[dev.fd] = dev
#         self.thread = threading.Thread(target=self._monitor_loop, daemon=True)

#     def start(self):
#         self.thread.start()

#     def _monitor_loop(self):
#         while self.running:
#             r, w, x = select.select(self.devices.keys(), [], [], 0.1)
#             for fd in r:
#                 for event in self.devices[fd].read():
#                     if event.type == evdev.ecodes.EV_KEY:
#                         if event.code == evdev.ecodes.KEY_SPACE and event.value == 1:
#                             self.space_pressed = True

#     def stop(self):
#         self.running = False


# ---------------------------------------------------------
# AI AGENT LOOP (HANDS-FREE)
# ---------------------------------------------------------
class AgentLoopThread(threading.Thread):
    def __init__(self, ui_instance, eye_instance, audio_instance, brain_instance):
        super().__init__(daemon=True)
        self.ui = ui_instance
        self.eye = eye_instance
        self.audio = audio_instance
        self.brain = brain_instance
        self.is_running = True
        self.state = AgentState.IDLE 

    def _motion_handler(self, motion_type):
        if self.state != AgentState.IDLE:
            return 
            
        self.state = AgentState.SPEAKING
        self.ui.update_emotion_signal.emit("happy")
        
        import random
        greetings = [
            "I see you moving around over there!",
            "Hello! I see you waving.",
            "Whoa, quite energetic today, aren't we?",
            "I detect some movement. Hi there!"
        ]
        self.audio.speak(random.choice(greetings))
        self.ui.update_emotion_signal.emit("normal")
        self.state = AgentState.IDLE

    def run(self):
        self.eye.start()

        self.state = AgentState.SPEAKING
        self.ui.update_emotion_signal.emit("normal")
        self.audio.speak("Prototype 1 hands-free system is online.")
        self.state = AgentState.IDLE
        
        print("\n" + "="*60)
        print(" PROTOTYPE_1 IS FULLY ONLINE. (HANDS-FREE MODE ACTIVE)")
        print(" SAY 'HEY PROTOTYPE' TO WAKE UP. PRESS [ESC] TO QUIT UI.")
        print("="*60 + "\n")

        while self.is_running:
            self.state = AgentState.IDLE
            self.audio.wait_for_wakeword()
            
            self.ui.update_emotion_signal.emit("happy")
            
            session_active = True
            while session_active and self.is_running:
                session_active = self._handle_user_interaction()
            
            print("\n[SYSTEM] Conversation timeout. Returning to sleep mode...")
            
            time.sleep(0.05)

    def _vision_tool_executor(self, specific_query="Describe the scene"):
        self.ui.update_emotion_signal.emit("sad") 
        self.audio.speak("Analyzing visual data.")
        return self.eye.analyze_scene_sync(query=specific_query)

    def _web_search_executor(self, search_query):
        self.ui.update_emotion_signal.emit("normal") 
        self.audio.speak("Accessing global network.")
        return perform_web_search_ddgs(search_query)

    def _handle_user_interaction(self):
        self.state = AgentState.LISTENING
        
        user_text = self.audio.listen_dynamic(silence_threshold=1.5, max_wait_time=8.0)
        
        if not user_text:
            self.state = AgentState.IDLE
            self.ui.update_emotion_signal.emit("normal")
            return False

        self.state = AgentState.THINKING
        vision_state = self.eye.get_vision_state()
        self.brain.update_environment_state("user_identity", vision_state["user_identity"])
        self.brain.update_environment_state("visible_objects", vision_state["visible_objects"])
        
        response = self.brain.process_user_input(
            user_text=user_text, 
            vision_tool_callback=self._vision_tool_executor,
            search_tool_callback=self._web_search_executor
        )
        
        if response:
            self.state = AgentState.SPEAKING
            emotion_tag = "normal"
            match = re.search(r"\[(normal|happy|sad)\]", response, re.IGNORECASE)
            
            if match:
                emotion_tag = match.group(1).lower()
                clean_text = re.sub(r"\[.*?\]", "", response).strip()
            else:
                clean_text = response

            self.ui.update_emotion_signal.emit(emotion_tag)
            self.audio.speak(clean_text)
             
        self.eye.deep_vision_context = ""
        self.ui.update_emotion_signal.emit("normal")

        self.state = AgentState.IDLE
        return True

    def stop(self):
        self.is_running = False
        self.eye.stop()
        print("\n[SYSTEM] Agent Loop Shutdown Complete.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    print("="*60)
    print("      Prototype_1 SYSTEM INITIALIZING (PROTOTYPE 1.0.3)     ")
    print("="*60)
    
    ui = Prototype_1FaceUI()
    debug_ui = YoloDebugWindow()
    router = SignalRouter()
    router.frame_signal.connect(debug_ui.update_frame)

    eye = Prototype_1Eye(
        known_faces_dir="./eye/known_faces", 
        gaze_callback=ui.update_gaze_signal.emit,
        frame_callback=router.frame_signal.emit
    )
    
    audio = Prototype_1Audio()
    brain = AIBuddyBrain()
    
    agent_thread = AgentLoopThread(ui, eye, audio, brain)
    app.aboutToQuit.connect(agent_thread.stop)
    
    eye.motion_callback = lambda m: threading.Thread(target=agent_thread._motion_handler, args=(m,), daemon=True).start()
    
    agent_thread.start()

    ui.show()
    debug_ui.show()
    
    sys.exit(app.exec_())