import os

MAIN_PY = r"c:\Users\VEDANT RAJU BORKAR\OneDrive\Desktop\mytest\PythonProject\main.py"

with open(MAIN_PY, "r", encoding='utf-8') as f:
    code = f.read()

# 1. IMPORTS & GESTURE SYSTEM
imports_replace = """from collections import defaultdict
import cv2
import mediapipe as mp
import numpy as np
import threading
import time

# ─── MediaPipe Setup ────────────────────────────────────────────────────────
mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles  = mp.solutions.drawing_styles

# ─── Gesture Config ─────────────────────────────────────────────────────────
GESTURES = {
    "fist":         ("Fist / Closed",      (230, 230, 230), (30,  30,  30 )),
    "thumb_only":   ("Thumbs Up! 👍",       (180,  60, 180), (255, 255, 255)),
    "index_only":   ("Front Motion ➡",     (200,  80,  20), (255, 255, 255)),
    "peace":        ("Victory / Peace ✌",  ( 30, 160,  30), (255, 255, 255)),
    "three_up":     ("Three Signal 🤟",     (30,  200, 210), (255, 255, 255)),
    "four_up":      ("Four Alert ✋",        ( 20, 120, 220), (255, 255, 255)),
    "open_palm":    ("STOP / Full Open 🖐",  ( 20,  20, 220), (255, 255, 255)),
    "unknown":      ("...",                 ( 50,  50,  50), (200, 200, 200)),
}

GLOBAL_GESTURE = "unknown"
GESTURE_LOCK = threading.Lock()
THREAD_RUNNING = True

def get_finger_states(landmarks, handedness_label):
    lm = landmarks.landmark
    tips = [4, 8, 12, 16, 20]
    pips = [3, 6, 10, 14, 18]
    states = []
    if handedness_label == "Right":
        thumb_up = lm[tips[0]].x < lm[pips[0]].x
    else:
        thumb_up = lm[tips[0]].x > lm[pips[0]].x
    states.append(thumb_up)
    for i in range(1, 5):
        states.append(lm[tips[i]].y < lm[pips[i]].y)
    return states

def classify_gesture(states):
    thumb, index, middle, ring, pinky = states
    count = sum(states)
    if count == 0: return "fist"
    if count == 1 and thumb: return "thumb_only"
    if count == 1 and index: return "index_only"
    if count == 2 and index and middle: return "peace"
    if count == 3 and index and middle and ring: return "three_up"
    if count == 4 and index and middle and ring and pinky: return "four_up"
    if count == 5: return "open_palm"
    return "unknown"

def draw_overlay(frame, gesture_key, alpha=0.35):
    label, color, txt_color = GESTURES.get(gesture_key, GESTURES["unknown"])
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    bar_h = 70
    cv2.rectangle(frame, (0, h - bar_h), (w, h), color, -1)
    font = cv2.FONT_HERSHEY_DUPLEX
    text_size = cv2.getTextSize(label, font, 1.2, 2)[0]
    tx = (w - text_size[0]) // 2
    ty = h - bar_h + (bar_h + text_size[1]) // 2 - 4
    cv2.putText(frame, label, (tx, ty), font, 1.2, txt_color, 2, cv2.LINE_AA)
    return frame

def draw_finger_indicators(frame, states):
    names = ["T", "I", "M", "R", "P"]
    colors = [(180, 60, 180), (0, 140, 255), (0, 200, 0), (0, 200, 200), (255, 100, 0)]
    h, w = frame.shape[:2]
    r, gap = 18, 12
    total_w = 5 * (2 * r + gap) - gap
    start_x = (w - total_w) // 2
    y = 36
    for i, (up, name, col) in enumerate(zip(states, names, colors)):
        cx = start_x + i * (2 * r + gap) + r
        fill = col if up else (40, 40, 40)
        cv2.circle(frame, (cx, y), r, fill, -1)
        cv2.circle(frame, (cx, y), r, (220, 220, 220), 1)
        cv2.putText(frame, name, (cx - 7, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return frame

def gesture_worker():
    global GLOBAL_GESTURE, THREAD_RUNNING
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    with mp_hands.Hands(
        static_image_mode=False, max_num_hands=1,
        min_detection_confidence=0.7, min_tracking_confidence=0.6) as hands:
        while THREAD_RUNNING:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)
            gesture_key = "unknown"
            states = [False] * 5
            if result.multi_hand_landmarks:
                for hand_lm, hand_info in zip(result.multi_hand_landmarks, result.multi_handedness):
                    mp_drawing.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                                              mp_styles.get_default_hand_landmarks_style(),
                                              mp_styles.get_default_hand_connections_style())
                    label = hand_info.classification[0].label if hasattr(hand_info.classification[0], 'label') else "Right"
                    states = get_finger_states(hand_lm, label)
                    gesture_key = classify_gesture(states)
            
            with GESTURE_LOCK:
                GLOBAL_GESTURE = gesture_key
            
            draw_overlay(frame, gesture_key)
            draw_finger_indicators(frame, states)
            cv2.imshow("Hand Gesture Detector - AstraVanguard Secondary Controls", frame)
            
            # Non-blocking waitKey 
            if cv2.waitKey(1) & 0xFF == ord('q'):
                pass
                
    cap.release()
    cv2.destroyAllWindows()

# --- Compatibility Patch for arcade.Sprite ---"""
code = code.replace("from collections import defaultdict\n\n# --- Compatibility Patch for arcade.Sprite ---", imports_replace)


# 2. INIT
init_original = """        # Input
        self.keys_pressed: Set[int] = set()
        self.mouse_held   = False
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2"""
init_replace = """        # Input
        self.keys_pressed: Set[int] = set()
        self.mouse_held   = False
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2
        
        # Gestures
        self.last_handled_gesture = "unknown"
        self.gesture_fire = False
        self.gesture_move_up = False"""
code = code.replace(init_original, init_replace)

# 3. PLAYER MOVEMENT
move_original = """        if arcade.key.UP in self.keys_pressed or arcade.key.W in self.keys_pressed:
            iy += 1"""
move_replace = """        if arcade.key.UP in self.keys_pressed or arcade.key.W in self.keys_pressed or getattr(self, "gesture_move_up", False):
            iy += 1"""
code = code.replace(move_original, move_replace)

# 4. FIRE
fire_original = """    def fire_weapon(self):
        if not self.mouse_held:
            return"""
fire_replace = """    def fire_weapon(self):
        if not self.mouse_held and not getattr(self, "gesture_fire", False):
            return"""
code = code.replace(fire_original, fire_replace)

# 5. HANDLE GESTURE LOGIC & ON_UPDATE
update_original = """    # ── main update ──────────────────────────────────
    def on_update(self, delta_time: float):
        self.frame_count += 1"""
update_replace = """    def handle_gesture_controls(self):
        global GLOBAL_GESTURE
        with GESTURE_LOCK:
            cg = GLOBAL_GESTURE
            
        edge = (cg != self.last_handled_gesture)
        self.last_handled_gesture = cg

        # Continuous controls
        self.gesture_fire = (cg == "open_palm")
        self.gesture_move_up = (cg == "index_only")

        # Edge-triggered controls
        if edge and cg != "unknown" and cg != "fist":
            if cg == "thumb_only":
                if self.state == GameState.PLAYING:
                    self.state = GameState.PAUSED
                elif self.state == GameState.PAUSED:
                    self.state = GameState.PLAYING
            elif cg == "three_up" and self.state == GameState.PLAYING:
                if self.player.dash():
                    self.achievements.dash_count += 1
                    if self.achievements.dash_count >= 50:
                        self.achievements.unlock(AchievementID.DODGER)
            elif cg == "peace" and self.state == GameState.PLAYING:
                self.player.toggle_shield()
            elif cg == "four_up" and self.state == GameState.PLAYING:
                self.player.aim_assist = not self.player.aim_assist
                self.settings.aim_assist = self.player.aim_assist

    # ── main update ──────────────────────────────────
    def on_update(self, delta_time: float):
        self.frame_count += 1
        self.handle_gesture_controls()"""
code = code.replace(update_original, update_replace)

# 6. MAIN THREAD
main_original = """def main():
    settings = GameSettings.load()
    window   = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=False)
    window.background_color = arcade.color.BLACK
    window.show_view(MenuView(settings))
    arcade.run()

if __name__ == "__main__":
    main()"""

main_replace = """def main():
    global THREAD_RUNNING
    t = threading.Thread(target=gesture_worker, daemon=True)
    t.start()
    
    settings = GameSettings.load()
    window   = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=False)
    window.background_color = arcade.color.BLACK
    window.show_view(MenuView(settings))
    arcade.run()
    
    THREAD_RUNNING = False

if __name__ == "__main__":
    main()"""
code = code.replace(main_original, main_replace)

with open(MAIN_PY, "w", encoding='utf-8') as f:
    f.write(code)

print("Patch applied.")
