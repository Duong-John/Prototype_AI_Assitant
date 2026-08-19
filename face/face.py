import sys
import random
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QBrush, QPainterPath
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

class Prototype_1FaceUI(QWidget):
    update_gaze_signal = pyqtSignal(float, float) 
    update_emotion_signal = pyqtSignal(str)       

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prototype_1 Eye - Face UI")
        
        self.resize(800, 480) 
        self.setStyleSheet("background-color: black;")

        self.current_gaze_x = 0.0
        self.current_gaze_y = 0.0
        self.target_gaze_x = 0.0
        self.target_gaze_y = 0.0
        
        self.max_gaze_offset = 300

        self.top_cut = 0.0
        self.bot_cut = 0.0
        
        self.emotion_target_top = 0.0
        self.emotion_target_bot = 0.0
        self.is_blinking = False

        self.update_gaze_signal.connect(self.set_gaze)
        self.update_emotion_signal.connect(self.set_emotion)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_physics)
        self.timer.start(16)
        
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.start_blink)
        self.blink_timer.start(random.randint(2000, 6000))

    def start_blink(self):
        self.is_blinking = True
        QTimer.singleShot(150, self.end_blink)
        self.blink_timer.setInterval(random.randint(2000, 6000))

    def end_blink(self):
        self.is_blinking = False

    def set_gaze(self, x, y):
        self.target_gaze_x = max(-1.0, min(1.0, x * 1.3))
        self.target_gaze_y = max(-1.0, min(1.0, y * 1.3))

    def set_emotion(self, emotion):
        if emotion == "normal":
            self.emotion_target_top = 0
            self.emotion_target_bot = 0
        elif emotion == "happy":
            self.emotion_target_top = 0
            self.emotion_target_bot = 40
        elif emotion == "sad":
            self.emotion_target_top = 40
            self.emotion_target_bot = 0

    def update_physics(self):
        gaze_smoothness = 0.1 
        self.current_gaze_x += (self.target_gaze_x - self.current_gaze_x) * gaze_smoothness
        self.current_gaze_y += (self.target_gaze_y - self.current_gaze_y) * gaze_smoothness
        
        if self.is_blinking:
            target_top = 280
            target_bot = 0
            cut_smoothness = 0.6
        else:
            target_top = self.emotion_target_top
            target_bot = self.emotion_target_bot
            cut_smoothness = 0.15

        self.top_cut += (target_top - self.top_cut) * cut_smoothness
        self.bot_cut += (target_bot - self.bot_cut) * cut_smoothness
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.black)

        eye_w = 160
        eye_h = 280
        eye_spacing = 300
        center_x = self.width() / 2
        center_y = self.height() / 2
        Prototype_1_blue = QColor("#42a5f5")
        
        gaze_offset_x = self.current_gaze_x * self.max_gaze_offset
        gaze_offset_y = self.current_gaze_y * self.max_gaze_offset

        self.draw_true_geometry_eye(
            painter, cx=center_x - eye_spacing/2 + gaze_offset_x, cy=center_y + gaze_offset_y, 
            w=eye_w, h=eye_h, color=Prototype_1_blue
        )
        self.draw_true_geometry_eye(
            painter, cx=center_x + eye_spacing/2 + gaze_offset_x, cy=center_y + gaze_offset_y, 
            w=eye_w, h=eye_h, color=Prototype_1_blue
        )

    def draw_true_geometry_eye(self, painter, cx, cy, w, h, color):
        painter.save()
        painter.translate(cx, cy)
        
        base_path = QPainterPath()
        base_path.addRoundedRect(-w/2, -h/2, w, h, 80, 80)
        
        visible_y = -h/2 + self.top_cut
        visible_h = max(0, h - self.top_cut - self.bot_cut)
        
        cut_box = QPainterPath()
        cut_box.addRect(-w, visible_y, w*2, visible_h)
        
        final_eye_path = base_path.intersected(cut_box)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(final_eye_path)
        painter.restore()